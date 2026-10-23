"""Offboarding must preserve paid history and make empty-record deletion reviewable."""
from contextlib import closing
import json
import subprocess
import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from colegio.db import connect, local_today
from tests.restore_helpers import approved_restore as restore
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

    def error_deletion(self, target, **overrides):
        preview = self.request(f'student-deletion-preview/{target}')
        data = dict(kind='student', id=target, preview_hash=preview['preview_hash'],
                    student_code_confirmation=preview['student_code'], password='Una-clave-segura',
                    confirmation='BORRAR FICHA', reason='Matrícula duplicada ficticia')
        data.update(overrides)
        return data

    def duplicate(self):
        return self.request('students', self.student_data(name='Matrícula equivocada', document='A-duplicada'))['id']

    def test_error_deletion_removes_active_duplicate_and_unpaid_charges_only(self):
        paid = self.request('payments', self.payment())['id']
        original_receipt = self.request(f'receipt/{paid}.pdf')
        reference = self.request('state')
        cash = self.request('cash-preview')
        duplicate = self.duplicate()
        preview = self.request(f'student-deletion-preview/{duplicate}')
        self.assertTrue(preview['can_delete'])
        self.assertFalse(preview['archived'])
        self.assertGreater(preview['balance'], 0)
        self.assertGreater(preview['counts']['Cargos, incluidos pagados o anulados'], 0)
        self.assertFalse(self.preview('student', duplicate)['can_delete'])
        self.request('delete-error-student', self.error_deletion(duplicate))
        after = self.request('state')
        for key in ('students', 'guardians', 'charges', 'payments', 'expenses', 'summary', 'enrollments'):
            self.assertEqual(reference[key], after[key], key)
        self.assertEqual(cash, self.request('cash-preview'))
        self.assertEqual(original_receipt, self.request(f'receipt/{paid}.pdf'))
        self.request(f'student-deletion-preview/{duplicate}', status=400)
        with closing(connect(self.path)) as db:
            for table in ('charges', 'enrollment_documents', 'monthly_assessments'):
                self.assertEqual(db.execute(f'SELECT COUNT(*) FROM {table} WHERE student_id=?', (duplicate,)).fetchone()[0], 0)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())
            from colegio.maintenance import review_database
            self.assertTrue(review_database(db)['ok'])
        fresh = self.request('students', self.student_data(name='Nueva matrícula', document='A-nueva'))
        self.assertGreater(fresh['id'], duplicate)

    def test_error_deletion_requires_password_code_confirmation_csrf_and_fresh_review(self):
        duplicate = self.duplicate()
        for overrides, status in (({'password':'incorrecta'},403), ({'password':'', 'demo':True},403),
                                  ({'student_code_confirmation':'AL-equivocado'},400),
                                  ({'confirmation':'BORRAR'},400), ({'kind':'guardian'},400),
                                  ({'preview_hash':'anterior'},400), ({'reason':''},400)):
            with self.subTest(overrides=overrides):
                self.request('delete-error-student', self.error_deletion(duplicate, **overrides), status=status)
        data = self.error_deletion(duplicate)
        self.request('delete-error-student', data, status=403, csrf=False)
        self.request('charges', {'student_id':duplicate, 'period':local_today().strftime('%Y-%m'),
                                'concept':'Cargo ficticio', 'amount':'3', 'due_date':local_today().isoformat()})
        self.request('delete-error-student', data, status=400)
        self.assertTrue(self.request(f'student-deletion-preview/{duplicate}')['can_delete'])

    def test_error_deletion_never_removes_paid_voided_or_financially_documented_students(self):
        duplicate = self.duplicate()
        old = self.error_deletion(duplicate)
        paid = self.request('payments', self.payment(student_id=duplicate))['id']
        self.request('delete-error-student', old, status=400)
        self.request('void-payment', {'id':paid, 'reason':'Anulación ficticia'})
        self.assertFalse(self.request(f'student-deletion-preview/{duplicate}')['can_delete'])
        self.request('delete-error-student', self.error_deletion(duplicate), status=400)
        self.assertTrue(self.request(f'receipt/{paid}.pdf').startswith(b'%PDF'))
        self.request('guardian-documents', {'guardian_id':self.guardian, 'kind':'account'})
        self.assertFalse(self.request(f'student-deletion-preview/{self.student}')['can_delete'])
        self.request('delete-error-student', self.error_deletion(self.student), status=400)

    def test_error_deletion_backup_failure_preserves_duplicate_and_all_charges(self):
        duplicate = self.duplicate()
        before = self.request('state')
        data = self.error_deletion(duplicate)
        with patch('colegio.institution_archive.consistent_backup', side_effect=OSError('Disco lleno ficticio')):
            self.request('delete-error-student', data, status=400)
        for key in ('students', 'charges', 'payments', 'enrollments'):
            self.assertEqual(before[key], self.request('state')[key])

    def test_error_deletion_backup_restores_duplicate_and_full_ledger(self):
        duplicate = self.duplicate()
        before = self.request('state')
        result = self.request('delete-error-student', self.error_deletion(duplicate))
        restored = Path(self.temp.name)/'restaurada'/'colegio.sqlite3'
        restore(Path(result['backup_path']), restored.parent)
        with closing(connect(restored)) as db:
            self.assertIsNotNone(db.execute('SELECT id FROM students WHERE id=?', (duplicate,)).fetchone())
            self.assertEqual(len(before['charges']), db.execute('SELECT COUNT(*) FROM charges WHERE cancelled=0').fetchone()[0])
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())
            from colegio.audit_chain import local_status
            self.assertTrue(local_status(db)['ok'])

    def test_error_deletion_second_destination_failure_and_foreign_allocations_block_deletion(self):
        duplicate = self.duplicate()
        data = self.error_deletion(duplicate)
        with tempfile.TemporaryDirectory() as destination:
            self.request('backup-directory', {'backup_directory':destination})
            with patch('colegio.backup_export.write_encrypted', side_effect=OSError('USB ficticio lleno')):
                self.request('delete-error-student', data, status=400)
            self.assertTrue(self.request(f'student-deletion-preview/{duplicate}')['can_delete'])
            self.request('backup-directory', {'backup_directory':''})
        paid = self.request('payments', self.payment())['id']
        with closing(connect(self.path)) as db, db:
            # Damaged imported link: never infer safety only from payments.student_id.
            charge = db.execute('SELECT id FROM charges WHERE student_id=? ORDER BY id LIMIT 1', (duplicate,)).fetchone()[0]
            db.execute('UPDATE allocations SET charge_id=? WHERE payment_id=?', (charge, paid))
        preview = self.request(f'student-deletion-preview/{duplicate}')
        self.assertIn('Abonos aplicados a los cargos', preview['blockers'])
        self.request('delete-error-student', self.error_deletion(duplicate), status=400)

    def test_error_deletion_real_process_termination_keeps_complete_or_intact_record(self):
        from colegio.storage import consistent_backup
        from colegio.audit_chain import adopt_restored, local_status
        from colegio.db import initialize
        duplicate = self.duplicate()
        data = self.error_deletion(duplicate)
        script = '''import json,os,sys
from colegio.db import connect
import colegio.audit_chain as chain
import colegio.institution_archive as archive
stage=sys.argv[2]
original=archive.audit
def before_audit(*args,**kwargs):
    if stage=='after_delete': os._exit(71)
    return original(*args,**kwargs)
archive.audit=before_audit
chain.checkpoint=lambda point: os._exit(71) if point==stage else None
with connect(sys.argv[1]) as db:
    db.execute('BEGIN IMMEDIATE')
    user=dict(db.execute('SELECT * FROM users WHERE id=1').fetchone())
    preview=archive.record_preview(db,'student',json.loads(sys.argv[3])['id'],user,created_by_error=True)
    data=json.loads(sys.argv[3]);data['preview_hash']=preview['preview_hash']
    archive.archive_action(db,'delete-error-student',data,user)
'''
        for stage in ('after_delete', 'before_commit', 'after_commit', 'after_head'):
            with self.subTest(stage=stage):
                target = self.path.parent/stage/'colegio.sqlite3'
                consistent_backup(self.path, target); adopt_restored(target)
                process = subprocess.run([sys.executable, '-c', script, str(target), stage, json.dumps(data)],
                                         capture_output=True, timeout=30)
                self.assertEqual(process.returncode, 71, process.stderr.decode())
                initialize(target)
                with closing(connect(target)) as db:
                    expected = int(stage in ('after_delete', 'before_commit'))
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM students WHERE id=?', (duplicate,)).fetchone()[0], expected)
                    count = db.execute('SELECT COUNT(*) FROM charges WHERE student_id=?', (duplicate,)).fetchone()[0]
                    self.assertEqual(bool(count), bool(expected))
                    self.assertTrue(local_status(db)['ok'])
                    self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())

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
        for overrides,status in (({'password':'incorrecta'},403),({'password':'','demo':True},403),({'confirmation':'BORRAR'},400),({'preview_hash':'stale'},400)):
            self.request('delete-unused-record',self.deletion('guardian',target,**overrides),status=status)
        secondary_workspace=tempfile.TemporaryDirectory()
        self.addCleanup(secondary_workspace.cleanup)
        secondary=Path(secondary_workspace.name)
        self.request('backup-directory',{'backup_directory':str(secondary)})
        result=self.request('delete-unused-record',self.deletion('guardian',target))
        backup=Path(result['backup_path'])
        self.assertTrue(backup.is_file())
        self.assertTrue((secondary/(backup.stem+'.aulabak')).is_file())
        from colegio.backup_inspection import probe_backup
        self.assertEqual(probe_backup(secondary/(backup.stem+'.aulabak'),'FICTICIO-respaldo-seguro-2026')['integrity'],'ok')
        self.assertFalse(list(secondary.glob('*.sqlite3')))
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
            for endpoint in ('delete-unused-record',):
                self.request(endpoint,data,status=403)
            self.request('logout',{})
