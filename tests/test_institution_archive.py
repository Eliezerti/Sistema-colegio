"""Offboarding must preserve paid history and make empty-record deletion reviewable."""
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from colegio.db import connect, local_today
from colegio.restore import restore
from tests import test_system as system


class InstitutionArchiveTests(unittest.TestCase):
    setUp=system.SystemTests.setUp
    tearDown=system.SystemTests.tearDown
    request=system.SystemTests.request
    student_data=system.SystemTests.student_data
    payment=system.SystemTests.payment

    def action(self, endpoint, target, **extra):
        return self.request(endpoint, dict(id=target,reason='Corrección de prueba',
            confirmation='RECUPERAR' if endpoint.startswith('restore-') else 'ARCHIVAR',**extra))

    def preview(self,kind,target):
        return self.request(f'archive-preview/{kind}/{target}')

    def deletion(self,kind,target,**overrides):
        data=dict(kind=kind,id=target,preview_hash=self.preview(kind,target)['preview_hash'],
                  password='Una-clave-segura',confirmation='BORRAR FICHA',reason='Ficha duplicada de prueba')
        data.update(overrides)
        return data

    def empty_guardian(self):
        target=self.request('guardians',{'name':'Ficha sin alumnos','document':'V-vacia'})['id']
        self.action('archive-guardian',target)
        return target

    def test_fully_paid_student_is_archived_not_deleted_and_receipts_survive(self):
        amount=self.request('state')['students'][0]['balance']/100
        paid=self.request('payments',self.payment(amount=str(amount)))['id']
        before=self.request(f'receipt/{paid}')
        self.action('archive-student',self.student)
        preview=self.preview('student',self.student)
        self.assertEqual(preview['balance'],0)
        self.assertFalse(preview['can_delete'])
        self.request('delete-unused-record',self.deletion('student',self.student),status=400)
        self.assertEqual(before,self.request(f'receipt/{paid}'))
        self.assertTrue(self.request(f'receipt/{paid}.pdf').startswith(b'%PDF'))
        self.assertEqual(self.request('state')['students'][0]['archived'],1)
        self.action('restore-student',self.student)
        self.assertEqual(self.request('state')['students'][0]['status'],'inactive')

    def test_unused_guardian_requires_review_password_and_verified_recoverable_copies(self):
        target=self.empty_guardian()
        preview=self.preview('guardian',target)
        self.assertTrue(preview['can_delete'])
        for overrides,status in (({'password':'incorrecta'},403),({'confirmation':'BORRAR'},400),({'preview_hash':'stale'},400)):
            self.request('delete-unused-record',self.deletion('guardian',target,**overrides),status=status)
        secondary_workspace=tempfile.TemporaryDirectory()
        self.addCleanup(secondary_workspace.cleanup)
        secondary=Path(secondary_workspace.name)
        self.request('backup-directory',{'backup_directory':str(secondary)})
        result=self.request('delete-unused-record',self.deletion('guardian',target))
        backup=Path(result['backup_path'])
        self.assertTrue(backup.is_file())
        self.assertTrue((secondary/backup.name).is_file())
        with closing(sqlite3.connect(backup)) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('SELECT name FROM guardians WHERE id=?',(target,)).fetchone()[0],'Ficha sin alumnos')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],0)
        self.assertFalse(any(g['id']==target for g in self.request('state')['guardians']))
        recreated=self.request('guardians',{'name':'Nueva ficha','document':'V-vacia'})['id']
        self.assertGreater(recreated,target)
        self.assertEqual(self.request('state')['students'][0]['guardian_id'],self.guardian)
        entry=next(a for a in self.request('state')['audit'] if a['action']=='delete-unused-record')
        self.assertNotIn('Una-clave-segura',entry['details'])
        self.assertNotIn('password',entry['details'])

    def test_unused_student_deletes_only_own_constancias_and_does_not_reuse_codes(self):
        future=local_today().year+1
        created=self.request('students',self.student_data(name='Ficha de prueba',document='A-vacia',
            school_year=future,enrollment_start=f'{future}-09-01',enrollment_end=f'{future+1}-08-31',
            billing_start=f'{future}-09',status='inactive',monthly_fee='0'))
        before=self.request('state')
        self.action('archive-student',created['id'])
        self.assertTrue(self.preview('student',created['id'])['can_delete'])
        result=self.request('delete-unused-record',self.deletion('student',created['id']))
        after=self.request('state')
        self.assertEqual(before['charges'],after['charges'])
        self.assertEqual(before['payments'],after['payments'])
        self.assertFalse(any(s['id']==created['id'] for s in after['students']))
        self.assertTrue(any(e['student_id']==self.student for e in after['enrollments']))
        new=self.request('students',self.student_data(name='Otra prueba',document='A-nueva',
            status='inactive',monthly_fee='0'))
        self.assertGreater(new['id'],created['id'])
        self.assertGreater(new['document_id'],created['document_id'])
        self.assertNotEqual(new['student_code'],created['student_code'])
        restored=Path(self.temp.name)/'otra-pc'/'colegio.sqlite3'
        restore(Path(result['backup_path']),restored.parent)
        with closing(connect(restored)) as db:
            self.assertIsNotNone(db.execute('SELECT id FROM students WHERE id=?',(created['id'],)).fetchone())
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],system.SCHEMA_VERSION)
            self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())

    def test_guardian_links_remain_protected_even_when_children_are_archived_and_paid(self):
        self.action('archive-student',self.student)
        self.action('archive-guardian',self.guardian)
        self.assertFalse(self.preview('guardian',self.guardian)['can_delete'])
        self.request('delete-unused-record',self.deletion('guardian',self.guardian),status=400)
        self.assertEqual(len(self.request('state')['guardians']),1)

    def test_historical_family_document_protects_reassigned_representative(self):
        document=self.request('guardian-documents',{'guardian_id':self.guardian,'kind':'account'})['id']
        frozen=self.request(f'guardian-document/{document}')
        other=self.request('guardians',{'name':'Otro representante','document':'V-otro'})['id']
        self.request('students',self.student_data(id=self.student,guardian_id=other))
        self.action('archive-guardian',self.guardian)
        preview=self.preview('guardian',self.guardian)
        self.assertEqual(preview['counts']['Alumnos vinculados, incluidos archivados'],0)
        self.assertIn('Documentos familiares',preview['blockers'])
        self.request('delete-unused-record',self.deletion('guardian',self.guardian),status=400)
        self.assertEqual(self.request(f'guardian-document/{document}'),frozen)

    def test_employee_offboarding_preserves_paid_and_voided_expenses(self):
        employee=self.request('employees',{'name':'Personal de prueba','document':'V-emp','position':'Docente','salary':'100'})['id']
        expense=self.request('expenses',{'employee_id':employee,'concept':'Sueldo de prueba','category':'Nómina',
            'currency':'USD','amount':'100','spent_on':local_today().isoformat(),'method':'Efectivo',
            'period_start':local_today().isoformat(),'period_end':local_today().isoformat(),
            'entry_time':'08:00','exit_time':'16:00'})['id']
        before=self.request('state')['expenses']
        self.action('archive-employee',employee)
        self.assertFalse(self.preview('employee',employee)['can_delete'])
        self.request('void-expense',{'id':expense,'reason':'Anulación de prueba'})
        self.request('delete-unused-record',self.deletion('employee',employee),status=400)
        self.assertEqual(self.request('state')['expenses'][0]['amount'],before[0]['amount'])
        self.assertEqual(self.request('directory/employees')['count'],0)
        self.assertEqual(self.request('directory/employees?archived=1')['count'],1)
        self.action('restore-employee',employee)
        self.assertEqual(self.request('directory/employees')['count'],1)

    def test_empty_employee_can_be_deleted_but_saved_payroll_plan_blocks_another(self):
        first=self.request('employees',{'name':'Sin movimientos','document':'V-empty','position':'Docente','salary':'0'})['id']
        self.action('archive-employee',first)
        self.request('delete-unused-record',self.deletion('employee',first))
        second=self.request('employees',{'name':'Con relación','document':'V-new','position':'Docente','salary':'0'})['id']
        self.assertGreater(second,first)
        self.request('payroll-plans',{'name':'Relación guardada','pay_date':local_today().isoformat(),
            'lines':[{'employee_id':second,'amount':'0'}]})
        self.action('archive-employee',second)
        self.assertIn('Relaciones de pago',self.preview('employee',second)['blockers'])
        self.request('delete-unused-record',self.deletion('employee',second),status=400)

    def test_failed_local_or_second_backup_never_deletes(self):
        target=self.empty_guardian()
        data=self.deletion('guardian',target)
        with patch('colegio.institution_archive.consistent_backup',side_effect=OSError('Disco lleno')):
            self.request('delete-unused-record',data,status=400)
        self.assertTrue(self.preview('guardian',target)['can_delete'])
        blocked=Path(self.temp.name)/'archivo-no-carpeta'
        blocked.write_text('no es carpeta')
        with closing(connect(self.path)) as db, db:
            db.execute("UPDATE settings SET value=? WHERE key='backup_directory'",(str(blocked),))
        self.request('delete-unused-record',data,status=400)
        self.assertTrue(self.preview('guardian',target)['can_delete'])

    def test_permissions_csrf_and_stale_preview_are_enforced_on_server(self):
        target=self.empty_guardian()
        data=self.deletion('guardian',target)
        self.request('delete-unused-record',data,status=403,csrf=False)
        self.request('guardians',{'id':target,'name':'Ficha editada','document':'V-vacia'})
        self.request('delete-unused-record',data,status=400)
        for role in ('cashier','reader'):
            self.request('users',{'name':role,'username':role,'role':role,'password':'Clave-del-perfil'})
        self.request('logout',{})
        for role in ('cashier','reader'):
            self.request('login',{'username':role,'password':'Clave-del-perfil'})
            self.csrf=self.request('session')['user']['csrf']
            self.request('confirm-rate',{'rate_date':local_today().isoformat(),'rate':'100'})
            self.request(f'archive-preview/guardian/{target}',status=403)
            for endpoint in ('delete-unused-record','archive-employee','restore-employee'):
                self.request(endpoint,data,status=403)
            self.request('logout',{})
