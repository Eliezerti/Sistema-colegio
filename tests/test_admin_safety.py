from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import test_system
from colegio.db import connect, local_today, ValidationError


class AdministrativeSafetyTests(unittest.TestCase):
    setUp = test_system.SystemTests.setUp
    tearDown = test_system.SystemTests.tearDown
    request = test_system.SystemTests.request
    student_data = test_system.SystemTests.student_data
    payment = test_system.SystemTests.payment

    def salary_data(self, **changes):
        on = local_today().isoformat()
        position = self.request('positions', {'name':'Docente de prueba'})['id']
        employee = self.request('employees', {'name':'Ana Docente', 'document':'V-789', 'salary':'120',
            'position_id':position, 'status':'active', 'bank':'Banco Prueba', 'bank_account':'01020000000012345678'})['id']
        data = dict(concept='Sueldo docente', category='Nómina', employee_id=employee, spent_on=on,
                    amount='12000', currency='VES', method='Transferencia', reference='NOM-1',
                    period_start=on[:7]+'-01', period_end=on, entry_time='07:00', exit_time='13:00',
                    salary_notes='Período revisado con el empleado')
        data.update(changes)
        return data

    def test_salary_receipt_freezes_period_hours_bank_amount_and_void_status(self):
        data = self.salary_data()
        result = self.request('expenses', data)
        doc = self.request('salary-receipt/'+str(result['salary_receipt_id']))
        self.assertEqual(doc['expense']['amount'],12000)
        self.assertEqual(doc['expense']['received_amount'],1200000)
        self.assertEqual((doc['entry_time'],doc['exit_time']),('07:00','13:00'))
        self.assertEqual((doc['period_start'],doc['period_end']),(data['period_start'],data['period_end']))
        with closing(connect(self.path)) as db, db:
            db.execute("UPDATE employees SET name='Nuevo nombre',bank='Otro banco',salary=20000 WHERE id=?",(data['employee_id'],))
            db.execute("UPDATE settings SET value='Nuevo nombre fiscal' WHERE key='legal_name'")
        self.assertEqual(self.request('salary-receipt/'+str(result['salary_receipt_id'])),doc)
        pdf = self.request('salary-receipt/'+str(result['salary_receipt_id'])+'.pdf')
        self.assertTrue(pdf.startswith(b'%PDF'));self.assertIn(b'/FontFile2',pdf)
        self.request('void-expense',{'id':result['id'],'reason':'Corrección de sueldo'})
        voided = self.request('salary-receipt/'+str(result['salary_receipt_id']))
        self.assertTrue(voided['expense']['voided'])
        self.assertEqual(voided['expense']['void_reason'],'Corrección de sueldo')
        self.assertEqual(voided['employee']['name'],'Ana Docente')

    def test_salary_invalid_fields_and_document_failure_rollback_the_expense(self):
        data = self.salary_data()
        for invalid in (dict(entry_time='25:00'),dict(exit_time=''),dict(period_start='2099-01-01'),dict(employee_id='')):
            self.request('expenses',{**data,**invalid},status=400)
        with patch('colegio.server.issue_salary_receipt',side_effect=ValidationError('No se pudo emitir')):
            self.request('expenses',data,status=400)
        self.assertEqual(self.request('state')['expenses'],[])
        self.assertEqual(self.request('state')['summary']['expenses'],0)

    def test_old_salary_expense_can_get_one_receipt_without_paying_twice(self):
        data = self.salary_data()
        expense = self.request('expenses',{**data,'category':'Operación'})['id']
        with closing(connect(self.path)) as db, db:
            db.execute("UPDATE expenses SET category='Nómina' WHERE id=?",(expense,))
        receipt = self.request('salary-receipts',{**data,'expense_id':expense})['id']
        repeated = self.request('salary-receipts',{**data,'expense_id':expense,'entry_time':'08:00'})['id']
        self.assertEqual(receipt,repeated)
        self.assertEqual(self.request('salary-receipt/'+str(receipt))['entry_time'],'07:00')
        self.assertEqual(len(self.request('state')['expenses']),1)

    def reset_data(self):
        return dict(preview_hash=self.request('reset-preview')['preview_hash'],confirmation='VACIAR REGISTROS',password='Una-clave-segura')

    def test_reset_requires_password_phrase_fresh_review_and_admin(self):
        data = self.reset_data()
        self.request('reset-records',{**data,'password':'Incorrecta'},status=403)
        self.request('reset-records',{**data,'confirmation':'VACIAR'},status=400)
        self.request('guardians',{'name':'Otro representante','document':'V-456'})
        self.request('reset-records',data,status=400)
        with closing(connect(self.path)) as db, db:db.execute("UPDATE users SET role='cashier' WHERE username='admin'")
        self.request('reset-preview',status=403)
        self.request('reset-records',data,status=403)
        with closing(connect(self.path)) as db, db:self.assertEqual(db.execute('SELECT COUNT(*) FROM students').fetchone()[0],1)
        self.assertFalse(list((self.path.parent/'backups').glob('antes-vaciar-*')))

    def test_reset_preserves_verified_backup_users_identity_and_receipt_numbers(self):
        payment = self.request('payments',self.payment(amount='1'))['id']
        expense = self.request('expenses',{'concept':'Prueba','category':'Operación','spent_on':local_today().isoformat(),'amount':'1','currency':'USD'})['id']
        prior = self.request('state'); result = self.request('reset-records',self.reset_data())
        backup = Path(result['backup_path']);self.assertTrue(backup.is_file())
        with closing(sqlite3.connect(backup)) as db, db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM payments').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM students').fetchone()[0],1)
        self.request('state',status=401)
        self.request('login',{'username':'admin','password':'Una-clave-segura'})
        self.csrf=self.request('session')['user']['csrf']
        self.request('confirm-rate',{'rate_date':local_today().isoformat(),'rate':'100'})
        fresh=self.request('state')
        for key in ('students','guardians','payments','employees','expenses','grades','positions'):
            self.assertEqual(fresh[key],[],key)
        self.assertEqual(fresh['settings']['school_name'],prior['settings']['school_name'])
        self.assertEqual(fresh['settings']['rif'],prior['settings']['rif'])
        self.assertEqual(len(fresh['users']),len(prior['users']))
        self.grade=self.request('grades',{'name':'Nuevo grado','capacity':30})['id']
        self.guardian=self.request('guardians',{'name':'Nuevo representante','document':'V-999'})['id']
        old_student=self.student;self.student=self.request('students',self.student_data())['id']
        self.assertGreater(self.student,old_student)
        self.assertGreater(self.request('payments',self.payment(amount='1',key='new-after-reset'))['id'],payment)
        self.assertGreater(self.request('expenses',{'concept':'Nuevo','category':'Operación','spent_on':local_today().isoformat(),'amount':'1','currency':'USD'})['id'],expense)

    def test_reset_backup_failure_and_late_error_leave_financial_records_intact(self):
        self.request('payments',self.payment(amount='1'))
        data=self.reset_data()
        with patch('colegio.reset_records.consistent_backup',side_effect=OSError('Sin espacio')):
            self.request('reset-records',data,status=400)
        self.assertEqual(self.reset_data()['preview_hash'],data['preview_hash'])
        with patch('colegio.reset_records.audit',side_effect=ValidationError('Error al finalizar')):
            self.request('reset-records',data,status=400)
        self.assertEqual(self.reset_data()['preview_hash'],data['preview_hash'])
        self.assertEqual(len(self.request('state')['payments']),1)

    def test_reset_external_backup_failure_prevents_deletion(self):
        external=tempfile.TemporaryDirectory();self.addCleanup(external.cleanup)
        directory=Path(external.name)
        settings=self.request('state')['settings']
        self.request('settings',{**settings,'backup_directory':str(directory)})
        from colegio.storage import consistent_backup
        def fail_external(source,destination):
            if Path(destination).parent==directory:raise OSError('USB no disponible')
            return consistent_backup(source,destination)
        with patch('colegio.reset_records.consistent_backup',side_effect=fail_external):
            self.request('reset-records',self.reset_data(),status=400)
        self.assertEqual(len(self.request('state')['students']),1)
        backup=next((self.path.parent/'backups').glob('antes-vaciar-*'))
        with closing(sqlite3.connect(backup)) as db, db:self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_demo_endpoints_cannot_enter_or_erase_production(self):
        self.request('demo-login',{},status=403)
        self.request('demo-presence',{'token':'incorrecto','client':'tab','action':'close'},status=403)
        self.request('demo-exit',{},status=403)
        self.assertEqual(len(self.request('state')['students']),1)
