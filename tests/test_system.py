import http.client
import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from colegio.db import initialize, money, valid_rate, ValidationError, local_today
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
        self.request('settings', {'school_name':'Colegio Prueba','school_year':self.year,'due_day':10,'start_month':9})
        self.grade = self.request('grades', {'name':'Primaria A','capacity':2})['id']
        self.guardian = self.request('guardians', {'name':'Representante Uno','document':'V-123','phone':'04120000000'})['id']
        self.student = self.request('students', self.student_data())['id']

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
        return data

    def generate(self,month='01'):
        return self.request('generate',{'period':f'{self.year+1}-{month}','school_year':self.year})

    def payment(self,amount='22.50',currency='USD',key='one',**overrides):
        data={'student_id':self.student,'amount':amount,'currency':currency,'paid_on':f'{self.year+1}-02-10',
              'method':'Transferencia','reference':'ref','request_key':key}
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
        self.request('rates',{'rate_date':on,'rate':'200'})
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
        self.request('confirm-rate', {'rate_date':'2000-01-01','rate':'123'},status=400)
        self.request('confirm-rate', {'rate_date':local_today().isoformat(),'rate':'123'},csrf=False,status=403)
        self.request('confirm-rate', {'rate_date':local_today().isoformat(),'rate':'123'})
        self.assertTrue(self.request('state')['students'])
        with sqlite3.connect(self.path) as db:
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
        self.request('rates', {'rate_date':on,'rate':'200'})
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
        with sqlite3.connect(self.path) as db:
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
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*),SUM(amount) FROM payments').fetchone(),before)
            self.assertEqual(db.execute('SELECT student_code FROM students').fetchone()[0],'AL-000001')
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],4)
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
        with sqlite3.connect(self.path) as db:
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
        with sqlite3.connect(self.path) as db:
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
        with sqlite3.connect(self.path) as db:
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

    def test_missing_past_month_uses_old_tariff_before_student_edit(self):
        on=f'{self.year+1}-06'
        with sqlite3.connect(self.path) as db:
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
        with sqlite3.connect(backup) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],0)
        other=Path(self.temp.name)/'restauracion'
        restored=restore(backup,other)
        with sqlite3.connect(restored) as db:
            self.assertEqual(db.execute('SELECT name FROM students').fetchone()[0],'Alumno Uno')
        restore(backup,other)
        self.assertTrue(list((other/'backups').glob('antes-restauracion-*.sqlite3')))
        with DataLock(other):
            with self.assertRaises(RuntimeError):restore(backup,other)
        daily_backup(restored)
        daily_backup(restored)
        self.assertEqual(len(list((other/'backups').glob('colegio-*.sqlite3'))),1)


if __name__=='__main__':
    unittest.main()
