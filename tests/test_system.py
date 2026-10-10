from contextlib import closing
import http.client
import json
import base64
import csv
import io
import subprocess
import sys
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from colegio.db import initialize, money, valid_rate, ValidationError, local_today, connect
from colegio.administration import COLUMNS, parse_import
from colegio.server import SchoolServer
from colegio.storage import DataLock, daily_backup
from colegio.restore import restore
from colegio.branding import SCHOOL_PROFILE, LOGO_FILE, SCHEMA_VERSION


class MoneyTests(unittest.TestCase):
    def test_exact_cents_and_invalid_inputs(self):
        self.assertEqual(money('0.29'), 29)
        self.assertEqual(money('100.10'), 10010)
        for value in ('NaN','Infinity','-1','1.001','text',None):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                money(value)
        for value in ('0','-2','NaN','1.0000001'):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                valid_rate(value)


class SystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'colegio.sqlite3'
        initialize(self.path)
        self.server = SchoolServer(('127.0.0.1',0),str(self.path))
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.cookie = self.csrf = ''
        self.year = local_today().year - 2
        self.request('setup', {'name':'Directora','username':'admin','password':'Una-clave-segura'})
        self.csrf = self.request('session')['user']['csrf']
        self.request('confirm-rate', {'rate_date':local_today().isoformat(),'rate':'100'})
        self.request('settings', dict(SCHOOL_PROFILE,school_name='Colegio Prueba',school_year=self.year,due_day=10,start_month=9))
        self.grade = self.request('grades', {'name':'Primaria A','capacity':2})['id']
        self.guardian = self.request('guardians', {'name':'Representante Uno','document':'V-123','phone':'04120000000'})['id']
        self.student = self.request('students', self.student_data())['id']

    def test_directory_downloads_are_authenticated_filtered_and_do_not_issue_financial_documents(self):
        before = self.request('state')
        for kind in ('students', 'guardians', 'employees'):
            report = self.request('directory/'+kind)
            self.assertEqual(report['count'], len(before[kind]))
            pdf = self.request('directory/'+kind+'.pdf')
            self.assertTrue(pdf.startswith(b'%PDF-1.4'))
            self.assertIn(b'J-50835934-8', pdf)
        self.assertEqual(self.request('directory/students?search=inexistente')['count'], 0)
        self.assertEqual(self.request(f'directory/students?grade={self.grade}')['count'], 1)
        self.request('directory/students?grade=999', status=400)
        report = self.request('daily-report')
        self.assertEqual(report['payment_count'], 0)
        self.assertEqual(report['overdue_usd'], before['summary']['overdue'])
        self.assertTrue(self.request('daily-report.pdf').startswith(b'%PDF-1.4'))
        after = self.request('state')
        self.assertEqual(after['payments'], before['payments'])
        self.assertEqual(after['charges'], before['charges'])
        self.assertEqual(after['enrollments'], before['enrollments'])
        self.request('logout', {})
        self.request('directory/students.pdf', status=401)
        self.request('daily-report.pdf', status=401)

    def test_daily_payments_keep_receipt_identity_and_voided_rows_leave_totals(self):
        payment = self.request('payments', self.payment(amount='10', paid_on=local_today().isoformat()))['id']
        self.request('grades', {'id': self.grade, 'name': 'Grado cambiado', 'capacity': 2})
        self.request('guardians', {'id': self.guardian, 'name': 'Representante cambiado', 'document': 'V-123'})
        self.request('students', self.student_data(id=self.student, name='Alumno cambiado'))
        report = self.request('daily-report')
        row = report['sections'][0]['lines'][0]
        self.assertIn('Alumno Uno', row[2])
        self.assertIn('Primaria A', row[2])
        self.assertEqual(row[3], 'Representante Uno')
        self.assertIn('Alumno cambiado', report['sections'][1]['lines'][0][1])
        self.assertEqual(report['income_usd'], 1000)
        self.request('void-payment', {'id': payment, 'reason': 'Prueba de anulación'})
        report = self.request('daily-report')
        self.assertEqual(report['income_usd'], 0)
        self.assertEqual(report['payment_count'], 0)
        self.assertIn('Anulado', report['sections'][0]['lines'][0][-1])

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self,path,data=None,status=200,csrf=True,origin=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=10)
        headers={'Cookie':self.cookie}
        if data is not None:
            headers['Content-Type']='application/json'
            if csrf: headers['X-CSRF-Token']=self.csrf
            if origin: headers['Origin']=origin
        conn.request('GET' if data is None else 'POST','/api/'+path,json.dumps(data) if data is not None else None,headers)
        response=conn.getresponse()
        cookie=response.getheader('Set-Cookie')
        if cookie:self.cookie=cookie.split(';')[0]
        body=response.read()
        self.assertEqual(response.status,status,body.decode(errors='replace'))
        kind=response.getheader('Content-Type')
        conn.close()
        return json.loads(body) if 'application/json' in kind else body

    def student_data(self,**overrides):
        data={'name':'Alumno Uno','document':'A-001','birth_date':'2015-01-01','guardian_id':self.guardian,
          'grade_id':self.grade,'school_year':self.year,'monthly_fee':'50','discount':10,'status':'active',
          'enrollment_start':f'{self.year}-09-01','enrollment_end':f'{self.year+1}-08-31'}
        data.update(overrides)
        data['billing_start']=overrides.get('billing_start',data['enrollment_start'][:7])
        return data

    def generate(self,month='01'):
        return self.request('generate',{'period':f'{self.year+1}-{month}','school_year':self.year})

    def payment(self,amount='22.50',currency='USD',key='one',**overrides):
        data={'student_id':self.student,'amount':amount,'currency':currency,'paid_on':f'{self.year+1}-02-10',
              'method':'Transferencia','reference':'ref-'+key,'request_key':key}
        data.update(overrides)
        return data

    def test_multicurrency_partial_allocations_idempotency_void_and_frozen_receipt(self):
        self.assertEqual(self.generate()['created'],0)
        self.assertEqual(self.generate()['created'],0)
        self.assertEqual(self.generate('02')['created'],0)
        on=f'{self.year+1}-02-10'
        self.request('rates',{'rate_date':on,'rate':'100.125'})
        data=self.payment(amount='2252.81',currency='VES')
        result=self.request('payments',data)
        self.assertFalse(result['duplicate'])
        self.assertEqual(self.request('payments',data)['id'],result['id'])
        self.request('payments',dict(data,amount='1'),status=400)
        state=self.request('state')
        self.assertEqual(state['students'][0]['balance'],51750)
        self.assertEqual(state['charges'][0]['paid'],2250)
        self.request('rates',{'rate_date':on,'rate':'200','rate_change_confirmed':True})
        self.request('students',self.student_data(id=self.student,name='Nombre actualizado'))
        receipt=self.request('receipt/'+str(result['id']))
        self.assertEqual(receipt['payment']['exchange_rate'],'100.125')
        self.assertEqual(receipt['payment']['student_name'],'Alumno Uno')
        self.assertEqual(self.request('payments',data)['id'],result['id'])
        second=self.request('payments',self.payment(amount='40',key='two'))['id']
        state=self.request('state')
        self.assertEqual([c['paid'] for c in state['charges']],[4500,1750]+[0]*10)
        self.assertEqual(state['students'][0]['balance'],47750)
        self.request('void-payment',{'id':second,'reason':'Corrección del cobro'})
        self.assertEqual(self.request('state')['students'][0]['balance'],51750)
        self.request('cancel-charge',{'id':state['charges'][0]['id'],'reason':'No procede'},status=400)
        self.request('payments',self.payment(amount='517.50',key='three'))
        self.assertEqual(self.request('state')['students'][0]['balance'],0)
        self.assertEqual(self.request('state')['summary']['overdue'],0)

    def test_failed_payment_rolls_back_missing_rate_overpay_and_future(self):
        self.generate()
        self.request('payments',self.payment(currency='VES'),status=400)
        self.request('payments',self.payment(amount='541'),status=400)
        self.request('payments',self.payment(paid_on='2099-01-01'),status=400)
        state=self.request('state')
        self.assertEqual(len(state['payments']),0)
        self.assertEqual(state['students'][0]['balance'],54000)
        self.request('rates',{'rate_date':f'{self.year+1}-02-10','rate':'100'})
        self.request('payments',self.payment(amount='0.01',currency='VES'),status=400)
        self.assertEqual(self.request('state')['students'][0]['balance'],54000)

    def test_academic_year_enrollment_discount_and_capacity(self):
        self.generate('01')
        self.request('generate',{'period':f'{self.year}-01','school_year':self.year},status=400)
        second=self.request('students',self.student_data(name='Alumno Dos',document='A-002',enrollment_start=f'{self.year+1}-03-01',discount=100))['id']
        self.assertEqual(self.generate('02')['created'],0)
        self.assertEqual(self.generate('03')['created'],0)
        self.request('students',self.student_data(document='A-003'),status=400)
        state=self.request('state')
        self.assertEqual(next(s for s in state['students'] if s['id']==second)['balance'],0)
        self.request('students',self.student_data(id=self.student,status='inactive'))
        self.assertEqual(self.generate('04')['created'],0)
        self.request('collections', {'student_id':self.student,'note':'Se llamó al representante','promised_on':f'{self.year+1}-05-01'})
        self.assertEqual(self.request('state')['collections'][0]['note'],'Se llamó al representante')

    def test_security_roles_csrf_origins_and_login(self):
        self.request('rates',{'rate_date':'2020-01-01','rate':'1'},status=403,csrf=False)
        self.request('grades',{'name':'Injected','capacity':1},status=403,origin='https://other.example')
        self.request('users',{'name':'Lector','username':'reader','password':'Otra-clave-segura','role':'reader'})
        self.request('logout',{})
        self.request('state',status=401)
        self.request('login',{'username':'reader','password':'wrong'},status=401)
        self.request('login',{'username':'reader','password':'Otra-clave-segura'})
        self.csrf=self.request('session')['user']['csrf']
        self.request('state',status=428)
        self.request('confirm-rate',{'rate_date':local_today().isoformat()})
        self.request('rates',{'rate_date':'2020-01-01','rate':'1'},status=403)
        for endpoint in ('import-roster','close-cash','reopen-cash','guardian-documents'):
            self.request(endpoint,{},status=403)
        self.request('backup',status=403)
        self.assertEqual(self.request('state')['users'],[])
        self.assertEqual(self.request('state')['audit'],[])

    def test_concurrent_payment_retries_create_one_receipt(self):
        self.generate()
        payment = self.payment(amount='540',key='concurrent-request')
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.request('payments',payment), range(2)))
        self.assertEqual(results[0]['id'],results[1]['id'])
        state = self.request('state')
        self.assertEqual(len(state['payments']),1)
        self.assertEqual(state['students'][0]['balance'],0)

    def test_siblings_automatic_codes_and_frozen_enrollment_pdf(self):
        first = self.request('students', self.student_data(id=self.student, document='', monthly_fee='100', discount=10))
        sibling = self.request('students', self.student_data(name='Hermano Dos', document=''))
        self.assertNotEqual(first['student_code'], sibling['student_code'])
        self.assertEqual(first['student_code'], 'AL-000001')
        document = self.request('enrollment/'+str(first['document_id']))
        self.assertEqual(document['student']['net_fee'], 9000)
        self.assertEqual(document['student']['guardian_id'], self.guardian)
        self.request('students', self.student_data(id=self.student, name='Nombre cambiado', monthly_fee='200'))
        self.assertEqual(self.request('enrollment/'+str(first['document_id']))['student']['name'], 'Alumno Uno')
        self.assertEqual(self.request('enrollment/'+str(first['document_id']))['student']['net_fee'], 9000)
        pdf = self.request('enrollment/'+str(first['document_id'])+'.pdf')
        self.assertTrue(pdf.startswith(b'%PDF-1.4'))
        self.assertIn(b'AL-000001', pdf)
        self.generate()
        receipt = self.request('payments',self.payment())['id']
        self.assertTrue(self.request(f'receipt/{receipt}.pdf').startswith(b'%PDF-1.4'))

    def test_rate_checkpoint_login_reader_and_date_change(self):
        self.request('logout', {})
        self.request('login', {'username':'admin','password':'Una-clave-segura'})
        self.csrf=self.request('session')['user']['csrf']
        self.request('state', status=428)
        self.request('grades', {'name':'Blocked','capacity':20}, status=428)
        self.assertEqual(self.request('rate-gate')['today'],local_today().isoformat())
        self.request('backup')  # Backup remains accessible at the checkpoint.
        self.request('confirm-rate', {'rate_date':'2000-01-01','rate':'123','rate_change_confirmed':True},status=400)
        self.request('confirm-rate', {'rate_date':local_today().isoformat(),'rate':'123','rate_change_confirmed':True},csrf=False,status=403)
        self.request('confirm-rate', {'rate_date':local_today().isoformat(),'rate':'123','rate_change_confirmed':True})
        self.assertTrue(self.request('state')['students'])
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE sessions SET rate_confirmed_on='2000-01-01'")
        self.request('state',status=428)
        self.request('expenses', {'concept':'Bloqueado'},status=428)

    def test_consolidated_payroll_banks_rounding_and_frozen_plan(self):
        position=self.request('positions',{'name':'Docente'})['id']
        lines=[]
        for i in range(15):
            emp=self.request('employees',{'name':f'Empleado {i:02}', 'document':f'V-{i+100}',
                'position_id':position,'salary':'120','bank':'Banco Prueba',
                'bank_account':'01020000000012345678','account_holder':f'Titular {i:02}',
                'holder_document':f'V-{i+100}','account_type':'Corriente'})['id']
            lines.append({'employee_id':emp,'amount':'120.01' if i==0 else '120'})
        on=local_today().isoformat()
        self.request('rates', {'rate_date':on,'rate':'100.125'})
        data={'name':'Pago quincenal','pay_date':on,'lines':lines}
        plan=self.request('payroll-plans',data)['id']
        frozen=self.request('payroll-plan/'+str(plan))
        self.assertEqual(len(frozen['lines']),15)
        self.assertEqual(frozen['lines'][0]['amount_ves'],1201600)
        self.assertEqual(frozen['total_usd'],180001)
        self.assertEqual(frozen['total_ves'],18022600)
        self.assertEqual(frozen['lines'][0]['bank_account'],'01020000000012345678')
        self.assertEqual(len(self.request('state')['expenses']),0)
        self.assertEqual(self.request('state')['employees'][0]['salary'],12000)
        self.request('rates', {'rate_date':on,'rate':'200','rate_change_confirmed':True})
        self.request('positions',{'id':position,'name':'Profesor'})
        self.assertTrue(all(e['position']=='Profesor' for e in self.request('state')['employees']))
        self.assertEqual(self.request('payroll-plan/'+str(plan))['rate'],'100.125')
        self.assertEqual(self.request('payroll-plan/'+str(plan))['lines'][0]['position'],'Docente')
        pdf=self.request(f'payroll-plan/{plan}.pdf')
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertIn(b'Empleado 14',pdf)
        self.assertIn(b'/Count 3',pdf)  # 15 detailed employees span 3 pages with headers.
        self.request('payroll-plans',dict(data,lines=[lines[0],lines[0]]),status=400)
        self.request('payroll-plans',dict(data,pay_date='2000-01-01'),status=400)
        self.request('employees',{'name':'Inválido','document':'V-x','position_id':position,'salary':'120','bank_account':'123'},status=400)

    def test_additive_upgrade_preserves_old_records_and_balances(self):
        self.request('employees',{'name':'Empleado anterior','document':'V-ant','position':'Secretaría','salary':'155.50'})
        self.generate()
        receipt=self.request('payments',self.payment())['id']
        with closing(sqlite3.connect(self.path)) as db, db:
            before=db.execute('SELECT COUNT(*),SUM(amount) FROM payments').fetchone()
            db.execute('DROP TABLE enrollment_documents')
            db.execute('DROP TABLE payroll_plans')
            db.execute('DROP TABLE monthly_assessments')
            db.execute('DROP INDEX students_code')
            db.execute('ALTER TABLE students DROP COLUMN student_code')
            db.execute('ALTER TABLE sessions DROP COLUMN rate_confirmed_on')
            for column in ('position_id','bank','bank_account','account_holder','holder_document','account_type'):
                db.execute(f'ALTER TABLE employees DROP COLUMN {column}')
            db.execute('DROP TABLE positions')
            db.execute('PRAGMA user_version=0')
        initialize(self.path)
        initialize(self.path)
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute('SELECT COUNT(*),SUM(amount) FROM payments').fetchone(),before)
            self.assertEqual(db.execute('SELECT student_code FROM students').fetchone()[0],'AL-000001')
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)
            employee=db.execute('SELECT position,position_id,salary,bank_account FROM employees').fetchone()
            self.assertEqual(employee[0],'Secretaría')
            self.assertIsNotNone(employee[1])
            self.assertEqual(employee[2],15550)
            self.assertEqual(employee[3],'')
        self.request('state',status=428)
        self.request('confirm-rate', {'rate_date':local_today().isoformat(),'rate':'100'})
        self.assertEqual(self.request('state')['students'][0]['balance'],51750)
        self.assertEqual(self.request(f'receipt/{receipt}')['payment']['amount'],2250)

    def test_automatic_debts_from_enrollment_and_missing_month_on_reopen(self):
        # No explicit generation: a previous enrollment already has all 12 months.
        state=self.request('state')
        self.assertEqual(len(state['charges']),12)
        self.assertEqual(state['students'][0]['balance'],54000)
        self.assertEqual(state['students'][0]['overdue'],54000)
        receipt=self.request('payments',self.payment())['id']
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('DELETE FROM monthly_assessments')
            db.execute('DELETE FROM charges WHERE period=?',(f'{self.year+1}-01',))
            db.execute('UPDATE charges SET amount=4000 WHERE period=?',(f'{self.year}-12',))
        with ThreadPoolExecutor(max_workers=2) as pool:
            states=list(pool.map(lambda _:self.request('state'),range(2)))
        for state in states:
            self.assertEqual(len(state['charges']),12)
            self.assertEqual(state['students'][0]['balance'],51250)
            self.assertEqual(state['payments'][0]['id'],receipt)
            self.assertEqual(state['payments'][0]['amount'],2250)
        csv=self.request('export?type=arrears').decode('utf-8-sig')
        self.assertIn(f'{self.year+1}-01',csv)
        self.assertEqual(self.request('receipt/'+str(receipt))['payment']['student_name'],'Alumno Uno')

    def test_fiscal_identity_and_png_are_in_new_frozen_documents(self):
        first = self.request('payments', self.payment())['id']
        original = self.request(f'receipt/{first}')
        for key, value in SCHOOL_PROFILE.items():
            self.assertEqual(original['settings'][key], value)
        self.request('settings', {'school_name':'Nombre comercial editable','school_year':self.year,
            'due_day':10,'start_month':9,'legal_name':'Razón social actualizada, C.A.',
            'rif':'J-12345678-9','fiscal_address':'Dirección fiscal actualizada'})
        second = self.request('payments', self.payment(key='fiscal-second'))['id']
        self.assertEqual(self.request(f'receipt/{first}'), original)
        self.assertEqual(self.request(f'receipt/{second}')['settings']['legal_name'], 'Razón social actualizada, C.A.')
        for kind, target in (('receipt',first), ('enrollment',1)):
            pdf = self.request(f'{kind}/{target}.pdf')
            self.assertIn(b'/Subtype /Image', pdf)
            self.assertIn(b'/Predictor 15', pdf)
            self.assertIn(b'ALEJANDRO VON HUMBOLDT, C.A.', pdf)
            self.assertIn(b'RIF: J-50835934-8', pdf)
            self.assertIn(b'local Nro. 16-46', pdf)
        self.assertIn(b'Direcci', self.request(f'receipt/{second}.pdf'))

    def test_v3_branding_upgrade_preserves_finances_and_issued_receipts(self):
        receipt = self.request('payments', self.payment())['id']
        with closing(sqlite3.connect(self.path)) as db, db:
            historical = json.loads(db.execute('SELECT receipt_snapshot FROM payments WHERE id=?',(receipt,)).fetchone()[0])
            historical['school'] = {'school_name':'Colegio antes de actualizar','rif':'RIF anterior','address':'Dirección anterior'}
            frozen = json.dumps(historical,ensure_ascii=False)
            db.execute('UPDATE payments SET receipt_snapshot=? WHERE id=?',(frozen,receipt))
            db.execute("DELETE FROM settings WHERE key IN ('legal_name','fiscal_address','logo')")
            db.execute("UPDATE settings SET value='04120001234' WHERE key='phone'")
            db.execute('PRAGMA user_version=3')
            tables = ('students','guardians','charges','payments','allocations','monthly_assessments','employees','expenses')
            before = {t:db.execute(f'SELECT * FROM {t}').fetchall() for t in tables}
        initialize(self.path)
        initialize(self.path)
        with closing(sqlite3.connect(self.path)) as db, db:
            after = {t:db.execute(f'SELECT * FROM {t}').fetchall() for t in tables}
            self.assertEqual(after, before)
            settings = dict(db.execute('SELECT key,value FROM settings'))
            self.assertEqual(settings['phone'],'04120001234')
            self.assertEqual(settings['school_year'],str(self.year))
            self.assertEqual(settings['school_name'],'Colegio Prueba')
            for key,value in SCHOOL_PROFILE.items():
                self.assertEqual(settings[key],value)
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)
            self.assertEqual(db.execute('SELECT receipt_snapshot FROM payments WHERE id=?',(receipt,)).fetchone()[0],frozen)
            db.execute("UPDATE settings SET value='Cambio manual' WHERE key='legal_name'")
        initialize(self.path)
        self.assertEqual(self.request('state')['settings']['legal_name'],'Cambio manual')
        old_pdf = self.request(f'receipt/{receipt}.pdf')
        self.assertIn(b'Colegio antes de actualizar',old_pdf)
        self.assertNotIn(b'ALEJANDRO VON HUMBOLDT',old_pdf)

    def test_public_logo_has_binary_png_content_type(self):
        conn = http.client.HTTPConnection('127.0.0.1',self.server.server_port)
        conn.request('GET','/'+LOGO_FILE)
        response = conn.getresponse()
        self.assertEqual(response.status,200)
        self.assertEqual(response.getheader('Content-Type'),'image/png')
        self.assertEqual(response.read(),(Path(__file__).resolve().parent.parent/'static'/LOGO_FILE).read_bytes())
        conn.close()

    def test_receipt_paper_can_change_without_changing_the_saved_payment(self):
        payment=self.request('payments',self.payment())['id']
        before=self.request(f'receipt/{payment}')
        small=self.request(f'receipt/{payment}.pdf?paper=half-letter')
        full=self.request(f'receipt/{payment}.pdf?paper=a4')
        self.assertTrue(b'/MediaBox [0 0 612 396]' in small,'Debe ser media carta real')
        self.assertTrue(b'/MediaBox [0 0 595 842]' in full,'Debe conservar A4 como opción')
        self.assertEqual(self.request(f'receipt/{payment}'),before)
        self.request(f'receipt/{payment}.pdf?paper=invalid',status=400)

    def test_missing_past_month_uses_old_tariff_before_student_edit(self):
        on=f'{self.year+1}-06'
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('DELETE FROM monthly_assessments WHERE period=?',(on,))
            db.execute('DELETE FROM charges WHERE period=?',(on,))
        self.request('students',self.student_data(id=self.student,monthly_fee='100',discount=0,status='inactive'))
        state=self.request('state')
        self.assertEqual(next(c['amount'] for c in state['charges'] if c['period']==on),4500)
        self.assertEqual(state['students'][0]['balance'],54000)
        self.assertEqual(state['students'][0]['status'],'inactive')

    def test_expenses_csv_backup_and_restore(self):
        on=f'{self.year+1}-02-10'
        self.request('rates',{'rate_date':on,'rate':'100'})
        expense=self.request('expenses',{'concept':'=formula','category':'Materiales','amount':'1234.56','currency':'VES','spent_on':on})['id']
        state=self.request('state')
        self.assertEqual(state['expenses'][0]['amount'],1235)
        exported=self.request('export?type=expenses').decode('utf-8-sig')
        self.assertIn("'=formula",exported)
        self.request('void-expense',{'id':expense,'reason':'Error de registro'})
        backup=Path(self.temp.name)/'descargado.sqlite3'
        backup.write_bytes(self.request('backup'))
        with closing(sqlite3.connect(backup)) as db, db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],0)
        other=Path(self.temp.name)/'restauracion'
        restored=restore(backup,other)
        with closing(sqlite3.connect(restored)) as db, db:
            self.assertEqual(db.execute('SELECT name FROM students').fetchone()[0],'Alumno Uno')
        restore(backup,other)
        self.assertTrue(list((other/'backups').glob('antes-restauracion-*.sqlite3')))
        with DataLock(other):
            with self.assertRaises(RuntimeError):restore(backup,other)
        daily_backup(restored)
        daily_backup(restored)
        self.assertEqual(len(list((other/'backups').glob('colegio-*.sqlite3'))),1)


    def test_receipt_grade_is_frozen_and_legacy_grade_uses_historical_enrollment(self):
        first=self.request('payments',self.payment())['id']
        self.assertEqual(self.request(f'receipt/{first}')['payment']['grade_name'],'Primaria A')
        second_grade=self.request('grades',{'name':'Segundo B','capacity':30})['id']
        self.request('students',self.student_data(id=self.student,grade_id=second_grade))
        self.assertEqual(self.request(f'receipt/{first}')['payment']['grade_name'],'Primaria A')
        for paper in ('a4','half-letter'):
            self.assertIn(b'Primaria A',self.request(f'receipt/{first}.pdf?paper={paper}'))
        with closing(sqlite3.connect(self.path)) as db, db:
            frozen=json.loads(db.execute('SELECT receipt_snapshot FROM payments WHERE id=?',(first,)).fetchone()[0])
            frozen['person'].pop('grade_name');frozen['person'].pop('student_school_year')
            old=json.dumps(frozen)
            db.execute('UPDATE payments SET receipt_snapshot=? WHERE id=?',(old,first))
        self.assertEqual(self.request(f'receipt/{first}')['payment']['grade_name'],'Primaria A')
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute('SELECT receipt_snapshot FROM payments WHERE id=?',(first,)).fetchone()[0],old)
            db.execute('DELETE FROM enrollment_documents WHERE student_id=?',(self.student,))
        self.assertEqual(self.request(f'receipt/{first}')['payment']['grade_name'],'')
        self.assertIn(b'Grado no registrado',self.request(f'receipt/{first}.pdf'))

    def roster_file(self,records):
        defaults=dict(zip(COLUMNS,['Representante Nuevo','V-444','04120000001','','',
            'Alumno Importado','','2016-01-01','Primaria A',str(self.year),'50','10',
            f'{self.year}-09-01',f'{self.year+1}-08-31','activo','',f'{self.year}-09']))
        out=io.StringIO();writer=csv.DictWriter(out,fieldnames=COLUMNS,delimiter=';');writer.writeheader()
        for record in records: writer.writerow(dict(defaults,**record))
        return {'filename':'alumnos.csv','content':base64.b64encode(out.getvalue().encode('utf-8-sig')).decode()}

    def test_import_preview_atomic_commit_duplicates_capacity_and_historical_debt(self):
        data=self.roster_file([{}]);before=self.request('state')
        preview=self.request('import-roster',dict(data,preview=True))
        self.assertEqual(preview['errors'],[]);self.assertEqual(preview['students'],1)
        self.assertEqual(preview['new_balance'],54000)
        after=self.request('state');self.assertEqual(after['students'],before['students'])
        self.assertEqual(after['guardians'],before['guardians'])
        self.request('import-roster',data,status=400)
        saved=self.request('import-roster',dict(data,confirmed_hash=preview['hash'],confirmed_month=preview['billing_default']))
        self.assertEqual(saved['students'],1)
        self.assertEqual(len(self.request('state')['students']),2)
        again=self.request('import-roster',dict(data,preview=True))
        self.assertTrue(again['errors']);self.request('import-roster',dict(data,confirmed_hash=preview['hash'],confirmed_month=preview['billing_default']),status=400)
        # One valid row followed by an invalid row never partially imports.
        self.request('grades',{'id':self.grade,'name':'Primaria A','capacity':10})
        bad=self.roster_file([{'alumno_nombre':'Otro alumno','representante_cedula':'V-555'},
            {'alumno_nombre':'Alumno errado','representante_cedula':'V-666','grado':'No existe'}])
        count=len(self.request('state')['students']);p=self.request('import-roster',dict(bad,preview=True))
        self.assertEqual(p['students'],1);self.assertEqual(p['errors'][0]['row'],3)
        self.request('import-roster',dict(bad,confirmed_hash=p['hash'],confirmed_month=p['billing_default']),status=400)
        self.assertEqual(len(self.request('state')['students']),count)
        capacity=self.roster_file([{'alumno_nombre':'Uno nuevo'},{'alumno_nombre':'Dos nuevos'}])
        self.request('grades',{'id':self.grade,'name':'Primaria A','capacity':3})
        p=self.request('import-roster',dict(capacity,preview=True));self.assertEqual(len(p['errors']),1)

    def test_excel_template_numeric_dates_shared_siblings_and_formula_rejection(self):
        import zipfile
        raw=self.request('import-template?format=xlsx')
        with zipfile.ZipFile(io.BytesIO(raw)) as z: files={name:z.read(name) for name in z.namelist()}
        vals=['Representante Nuevo','V-444','04120000001','','','Alumno Importado','','42370',
            'Primaria A',str(self.year),'50.00','10',f'{self.year}-09-01',f'{self.year+1}-08-31','activo','',f'{self.year}-09']
        cells=''.join(f'<c r="{chr(65+i)}2" t="inlineStr"><is><t>{value}</t></is></c>' if i!=7 else f'<c r="H2"><v>{value}</v></c>' for i,value in enumerate(vals))
        files['xl/worksheets/sheet1.xml']=files['xl/worksheets/sheet1.xml'].replace(b'</sheetData>',('<row r="2">'+cells+'</row></sheetData>').encode())
        def excel():
            buffer=io.BytesIO()
            with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
                for name,payload in files.items(): z.writestr(name,payload)
            return {'filename':'alumnos.xlsx','content':base64.b64encode(buffer.getvalue()).decode()}
        p=self.request('import-roster',dict(excel(),preview=True));self.assertEqual(p['errors'],[])
        records,_=parse_import(excel());self.assertEqual(records[0]['nacimiento'],'2016-01-01')
        files['xl/worksheets/sheet1.xml']=files['xl/worksheets/sheet1.xml'].replace(b'<v>42370</v>',b'<f>1+1</f><v>42370</v>')
        self.request('import-roster',dict(excel(),preview=True),status=400)
        self.request('grades',{'id':self.grade,'name':'Primaria A','capacity':5})
        data=self.roster_file([{}, {'alumno_nombre':'Hermano Importado','nacimiento':'2018-01-01'}])
        p=self.request('import-roster',dict(data,preview=True));self.assertEqual(p['guardians'],1)
        self.request('import-roster',dict(data,confirmed_hash=p['hash'],confirmed_month=p['billing_default']))
        siblings=self.request('state')['students']
        self.assertEqual(len({s['student_code'] for s in siblings}),3)
        self.assertEqual(len(self.request('state')['guardians']),2)

    def cash_data(self,on,**extra):
        return dict(closed_on=on,preview_hash=self.request('cash-preview?date='+on)['preview_hash'],
            opening_USD='0',opening_VES='0',counted_USD='0',counted_VES='0',**extra)

    def test_cash_close_native_currency_counting_freeze_blocking_reopening_and_stale_preview(self):
        on=local_today().isoformat()
        first=self.request('payments',self.payment(amount='10',paid_on=on,method='Efectivo'))['id']
        self.request('payments',self.payment(amount='1000',currency='VES',key='bs',paid_on=on))
        self.request('expenses',{'concept':'Gasto','category':'Operación','spent_on':on,'amount':'3','currency':'USD','method':'Efectivo'})
        data=self.cash_data(on);data['counted_USD']='7'
        closed=self.request('close-cash',data)['id'];doc=self.request(f'cash-close/{closed}')
        self.assertEqual(doc['income_usd'],2000);self.assertEqual(doc['expense_usd'],300)
        self.assertEqual(doc['counts'][0]['expected'],700);self.assertEqual(doc['counts'][0]['difference'],0)
        self.assertEqual(next(r for r in doc['lines'] if r['currency']=='VES')['income'],100000)
        self.assertIn(b'/FontFile2',self.request(f'cash-close/{closed}.pdf'))
        self.request('payments',self.payment(amount='1',key='new',paid_on=on),status=400)
        self.request('void-payment',{'id':first,'reason':'Corrección'},status=400)
        self.request('expenses',{'concept':'Gasto','category':'Operación','spent_on':on,'amount':'1','currency':'USD'},status=400)
        self.assertTrue(self.request('payments',self.payment(amount='10',paid_on=on,method='Efectivo'))['duplicate'])
        self.request('close-cash',data,status=400)
        self.request('reopen-cash',{'id':closed,'reason':'Corregir referencia'})
        self.request('void-payment',{'id':first,'reason':'Corrección'})
        historical=self.request(f'cash-close/{closed}')
        self.assertEqual(historical['lines'],doc['lines']);self.assertTrue(historical['reopened_at'])
        # Changed movements must be reviewed again before signing a close.
        stale=self.cash_data(on)
        self.request('payments',self.payment(amount='1',key='after',paid_on=on))
        self.request('close-cash',stale,status=400)
        fresh=self.cash_data(on);self.request('close-cash',fresh,status=400) # Negative cash: supply the opening fund.
        fresh.update(opening_USD='3',counted_USD='0');self.request('close-cash',fresh)

    def test_guardian_account_all_children_solvency_and_immutable_documents(self):
        other=self.request('students',self.student_data(name='Hermano Dos',document='A-002'))['id']
        account=self.request('guardian-account/'+str(self.guardian))
        self.assertEqual(len(account['students']),2);self.assertEqual(account['balance'],108000)
        docid=self.request('guardian-documents',{'guardian_id':self.guardian,'kind':'account'})['id']
        frozen=self.request(f'guardian-document/{docid}')
        self.request('guardian-documents',{'guardian_id':self.guardian,'kind':'solvency'},status=400)
        self.request('payments',self.payment(amount='540'))
        self.request('payments',dict(self.payment(amount='540',key='brother'),student_id=other))
        self.assertEqual(self.request('guardian-account/'+str(self.guardian))['balance'],0)
        certificate=self.request('guardian-documents',{'guardian_id':self.guardian,'kind':'solvency'})['id']
        self.assertEqual(self.request(f'guardian-document/{certificate}')['balance'],0)
        self.assertEqual(self.request(f'guardian-document/{docid}'),frozen)
        for target in (docid,certificate): self.assertIn(b'/FontFile2',self.request(f'guardian-document/{target}.pdf'))
        self.request('charges',{'student_id':other,'period':'Extra','concept':'Inscripción','amount':'1','due_date':local_today().isoformat()})
        self.request('guardian-documents',{'guardian_id':self.guardian,'kind':'solvency'},status=400)
        self.assertEqual(self.request(f'guardian-document/{certificate}')['balance'],0)

    def test_financial_backups_secondary_destination_failure_and_durability_pragmas(self):
        with closing(connect(self.path)) as db, db:
            self.assertEqual(db.execute('PRAGMA journal_mode').fetchone()[0],'wal')
            self.assertEqual(db.execute('PRAGMA synchronous').fetchone()[0],2)
        secondary=tempfile.TemporaryDirectory();self.addCleanup(secondary.cleanup)
        second=Path(secondary.name)/'second-folder'
        self.request('settings',{'school_name':'Colegio Prueba','school_year':self.year,'due_day':10,'backup_directory':str(second)})
        self.request('payments',self.payment())
        status=self.request('backup-status');self.assertTrue(status['secondary_at'])
        with closing(sqlite3.connect(status['local_path'])) as db, db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM payments').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],0)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        self.assertTrue((second/Path(status['local_path']).name).exists())
        # A second destination failure cannot roll back a successfully committed payment.
        for p in second.iterdir():p.unlink()
        second.rmdir();second.write_text('Not a folder')
        result=self.request('payments',self.payment(key='second'))
        self.assertTrue(result['backup_warning']);self.assertEqual(len(self.request('state')['payments']),2)
        self.assertTrue(self.request('backup-status')['secondary_error'])
        bad={'school_name':'Colegio Prueba','school_year':self.year,'due_day':10,'backup_directory':str(self.path.parent/'backups')}
        self.request('settings',bad,status=400)

    def test_process_killed_during_and_after_payment_preserves_atomicity(self):
        script=r"""
import json,sqlite3,sys
from colegio.db import record_payment
phase=sys.argv[2]
class Connection(sqlite3.Connection):
    def execute(self,sql,*args):
        result=super().execute(sql,*args)
        if phase=='during' and sql.startswith('INSERT INTO allocations'):
            print('checkpoint',flush=True);input()
        return result
with sqlite3.connect(sys.argv[1],factory=Connection) as db:
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
    record_payment(db,json.loads(sys.argv[3]),1)
    db.commit();print('checkpoint',flush=True);input()
"""
        for phase in ('during','after'):
            process=subprocess.Popen([sys.executable,'-u','-c',script,str(self.path),phase,json.dumps(self.payment(amount='70'))],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                self.assertEqual(process.stdout.readline().strip(),'checkpoint')
                process.kill();process.wait(timeout=10)
            finally:
                if process.poll() is None:process.kill();process.wait(timeout=10)
                process.stdin.close();process.stdout.close();process.stderr.close()
            with closing(connect(self.path)) as db, db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertEqual(db.execute('SELECT COUNT(*) FROM payments').fetchone()[0],0 if phase=='during' else 1)
                self.assertEqual(db.execute('SELECT COALESCE(SUM(amount),0) FROM allocations').fetchone()[0],0 if phase=='during' else 7000)


    def test_rate_large_change_requires_explicit_confirmation_and_no_writes(self):
        on=local_today().isoformat()
        result=self.request('rates',{'rate_date':on,'rate':'1000'},status=409)
        self.assertTrue(result['requires_rate_confirmation'])
        self.assertEqual(self.request('rate-gate')['rate'],'100')
        self.request('rates',{'rate_date':on,'rate':'110'}) # Exactly 10% is permitted.
        self.request('rates',{'rate_date':on,'rate':'90'},status=409)
        self.request('rates',{'rate_date':on,'rate':'90','rate_change_confirmed':True})
        self.assertEqual(self.request('rate-gate')['rate'],'90')

    def test_duplicate_reference_warning_requires_reason_and_retries_remain_idempotent(self):
        first=self.request('payments',self.payment(reference='000ABC'))['id']
        repeated=self.payment(key='other',reference=' 000abc ')
        self.request('payments',repeated,status=400)
        self.request('payments',dict(repeated,duplicate_reference_confirmed=True),status=400)
        allowed=dict(repeated,duplicate_reference_confirmed=True,duplicate_reason='Dos pagos del mismo comprobante, verificados')
        second=self.request('payments',allowed)['id'];self.assertNotEqual(first,second)
        self.assertTrue(self.request('payments',allowed)['duplicate'])
        self.assertEqual(len(self.request('state')['payments']),2)
        self.assertTrue(any(a['action']=='duplicate-reference-confirmed' for a in self.request('state')['audit']))

    def test_bulk_year_promotions_repeaters_withdrawals_preserve_finances_and_archive(self):
        self.request('grades',{'id':self.grade,'name':'Primaria A','capacity':5})
        repeat=self.request('students',self.student_data(name='Repitente',document='A-002'))['id']
        withdraw=self.request('students',self.student_data(name='Retirado',document='A-003'))['id']
        next_grade=self.request('grades',{'name':'Segundo B','capacity':10})['id']
        receipt=self.request('payments',self.payment())['id'];before=self.request('state')
        roster=self.request('year-roster?year='+str(self.year))
        data={'source_year':self.year,'target_year':self.year+1,'roster_hash':roster['preview_hash'],
            'closed_on':f'{self.year+1}-08-31','enrollment_start':f'{self.year+1}-09-01','enrollment_end':f'{self.year+2}-08-31',
            'lines':[{'student_id':self.student,'action':'promote','grade_id':next_grade,'monthly_fee':'60'},
                {'student_id':repeat,'action':'repeat','grade_id':next_grade,'monthly_fee':'50'},
                {'student_id':withdraw,'action':'withdraw','grade_id':next_grade,'monthly_fee':'50'}]}
        preview=self.request('transition-year',dict(data,preview=True));self.assertEqual(preview['errors'],[])
        self.assertEqual(self.request('state')['students'],before['students'])
        self.request('transition-year',data,status=400)
        result=self.request('transition-year',dict(data,confirmed_hash=preview['hash']))
        state=self.request('state');by_id={s['id']:s for s in state['students']}
        self.assertEqual(by_id[self.student]['grade_id'],next_grade)
        self.assertEqual(by_id[self.student]['billing_start'],data['enrollment_start'][:7])
        self.assertEqual(by_id[repeat]['grade_id'],self.grade);self.assertEqual(by_id[repeat]['school_year'],self.year+1)
        self.assertEqual(by_id[withdraw]['school_year'],self.year);self.assertEqual(by_id[withdraw]['status'],'inactive')
        self.assertEqual(state['payments'],before['payments'])
        with closing(sqlite3.connect(self.path)) as db, db:
            for charge in before['charges']:
                row=db.execute('SELECT amount,period FROM charges WHERE id=?',(charge['id'],)).fetchone()
                self.assertEqual(row,(charge['amount'],charge['period']))
        self.assertEqual(self.request(f'receipt/{receipt}')['payment']['grade_name'],'Primaria A')
        doc=self.request(f"year-transition/{result['id']}")
        self.assertEqual(doc['lines'][0]['source']['school_year'],self.year)
        self.assertTrue(self.request(f"year-transition/{result['id']}.pdf").startswith(b'%PDF'))
        self.request('transition-year',dict(data,confirmed_hash=preview['hash']),status=400)

    def test_bulk_year_capacity_and_stale_preview_abort_without_partial_changes(self):
        target=self.request('grades',{'name':'Segundo B','capacity':1})['id']
        other=self.request('students',self.student_data(name='Otro',document='A-002'))['id']
        roster=self.request('year-roster?year='+str(self.year))
        data={'source_year':self.year,'target_year':self.year+1,'roster_hash':roster['preview_hash'],
            'closed_on':f'{self.year+1}-08-31','enrollment_start':f'{self.year+1}-09-01','enrollment_end':f'{self.year+2}-08-31',
            'lines':[{'student_id':sid,'action':'promote','grade_id':target,'monthly_fee':'50'} for sid in (self.student,other)]}
        preview=self.request('transition-year',dict(data,preview=True));self.assertTrue(preview['errors'])
        self.request('transition-year',dict(data,confirmed_hash=preview['hash']),status=400)
        self.assertTrue(all(s['school_year']==self.year for s in self.request('state')['students']))
        self.request('grades',{'id':target,'name':'Segundo B','capacity':3})
        preview=self.request('transition-year',dict(data,preview=True))
        self.request('students',self.student_data(id=self.student,notes='Cambió la matrícula'))
        self.request('transition-year',dict(data,confirmed_hash=preview['hash']),status=400)

    def test_payment_plan_existing_debt_installments_and_void_recalculate_compliance(self):
        before=self.request('state');debt=before['students'][0]['overdue'];on=local_today().isoformat()
        data={'student_id':self.student,'expected_total':debt,'installments':[{'due_date':on,'amount':'270'},{'due_date':on,'amount':'270'}]}
        self.request('payment-plans',dict(data,installments=[{'due_date':on,'amount':'1'}]),status=400)
        target=self.request('payment-plans',data)['id']
        state=self.request('state');self.assertEqual(state['charges'],before['charges']);self.assertEqual(state['students'][0]['balance'],54000)
        self.request('payment-plans',data,status=400)
        payment=self.request('payments',self.payment(amount='300'))['id']
        plan=self.request('state')['payment_plans'][0]
        self.assertEqual([r['paid'] for r in plan['installments']],[27000,3000]);self.assertEqual(plan['balance'],24000)
        self.request('void-payment',{'id':payment,'reason':'Corregir transferencia'})
        plan=self.request('state')['payment_plans'][0];self.assertEqual(plan['paid'],0);self.assertEqual(plan['balance'],54000)
        self.assertTrue(self.request(f'payment-plan/{target}.pdf').startswith(b'%PDF'))
        self.request('cancel-plan',{'id':target,'reason':'Rehacer fechas'})
        self.assertTrue(self.request('state')['payment_plans'][0]['cancelled'])
        self.assertEqual(self.request('state')['students'][0]['balance'],54000)

    def test_thermal_ticket_physical_sizes_and_same_saved_receipt(self):
        payment=self.request('payments',self.payment())['id'];before=self.request(f'receipt/{payment}')
        for paper,width in (('ticket-58','164.409'),('ticket-80','226.772')):
            pdf=self.request(f'receipt/{payment}.pdf?paper={paper}')
            self.assertIn(('/MediaBox [0 0 '+width+' ').encode(),pdf)
            self.assertIn(b'Primaria A',pdf);self.assertIn(b'/FontFile2',pdf)
        self.assertEqual(self.request(f'receipt/{payment}'),before)

    def test_local_password_reset_requires_closed_application_and_preserves_data(self):
        from colegio.reset_password import reset_password
        from colegio.db import check_password
        with DataLock(self.path.parent):
            with self.assertRaises(RuntimeError):reset_password(self.path.parent,'admin','Nueva-clave-segura')
        reset_password(self.path.parent,'admin','Nueva-clave-segura')
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertTrue(check_password('Nueva-clave-segura',db.execute("SELECT password FROM users WHERE username='admin'").fetchone()[0]))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM students').fetchone()[0],1)
        self.assertTrue(list((self.path.parent/'backups').glob('recuperacion-clave-*.sqlite3')))


if __name__=='__main__':
    unittest.main()
