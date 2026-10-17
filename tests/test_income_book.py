from contextlib import closing
import unittest
from colegio.db import connect,local_today


class IncomeBookTests(unittest.TestCase):
    def setUp(self):
        from tests.test_system import SystemTests
        self.f=SystemTests();self.f.setUp();self.on=local_today().isoformat()
        self.bank=self.f.school_accounts[('USD','bank')];self.cash=self.f.school_accounts[('USD','cash')]
    def tearDown(self):self.f.tearDown()
    def deposit(self,pid,amount='10',key='dep'):
        return dict(account_id=self.bank,currency='USD',amount=amount,deposited_on=self.on,reference='FICTICIO-001',support='Planilla ficticia guardada en el archivo del colegio',request_key=key,payments=[dict(payment_id=pid,amount=amount)])
    def test_payment_destination_receipt_unchanged_and_retry_does_not_reassign(self):
        data=self.f.payment(amount='10',paid_on=self.on,method='Efectivo');pid=self.f.request('payments',data)['id']
        receipt=self.f.request('receipt/'+str(pid));self.assertNotIn('account_id',receipt['payment'])
        self.f.request('payments',dict(data,account_id=self.bank),status=400)
        self.assertTrue(self.f.request('payments',data)['duplicate'])
        with closing(connect(self.f.path)) as db:self.assertEqual(db.execute('SELECT account_id FROM payment_accounts WHERE payment_id=?',(pid,)).fetchone()[0],self.cash)
    def test_deposit_partial_retry_double_coverage_void_and_linked_payment_guard(self):
        pid=self.f.request('payments',self.f.payment(amount='15',paid_on=self.on,method='Efectivo'))['id']
        data=self.deposit(pid);did=self.f.request('income-deposit',data)['id']
        self.assertTrue(self.f.request('income-deposit',data)['duplicate'])
        self.f.request('income-deposit',dict(data,request_key='other'),status=400)
        self.f.request('void-payment',dict(id=pid,reason='Prueba de anulación ficticia'),status=400)
        self.f.request('income-void-deposit',dict(id=did,reason='Planilla ficticia corregida'))
        self.f.request('void-payment',dict(id=pid,reason='Anulación ficticia posterior'))
        with closing(connect(self.f.path)) as db:
            from colegio.audit_chain import local_status
            self.assertTrue(local_status(db)['ok']);self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())
    def test_bulk_assignment_is_explicit_atomic_and_preserves_receipt(self):
        pid=self.f.request('payments',self.f.payment(amount='10',paid_on=self.on))['id'];before=self.f.request('receipt/'+str(pid)+'.pdf')
        with closing(connect(self.f.path)) as db,db:db.execute('DELETE FROM payment_accounts WHERE payment_id=?',(pid,))
        data=dict(kind='payments',ids=[pid],account_id=self.bank,reason='Revisión explícita de datos ficticios')
        self.assertEqual(self.f.request('income-assign',data)['assigned'],1)
        self.assertEqual(self.f.request('receipt/'+str(pid)+'.pdf'),before)
        self.f.request('income-assign',dict(data,ids=[pid,999999]),status=400)
    def test_other_income_expense_accounts_and_reader_report_privacy(self):
        debt_before=self.f.request('state?history=1')['summary']['pending']
        category=self.f.request('income-category',dict(name='Aportes ficticios'))['id']
        data=dict(concept='Aporte ficticio',category_id=category,received_on=self.on,amount='12.34',currency='USD',method='Transferencia',account_id=self.bank,reference='FICTICIO',support='Documento ficticio sin datos de alumnos',request_key='other')
        identifier=self.f.request('income-other',data)['id'];self.assertTrue(self.f.request('income-other',data)['duplicate'])
        state=self.f.request('state?history=1');self.assertEqual(state['summary']['pending'],debt_before);self.assertEqual(state['summary']['income'],1234)
        with closing(connect(self.f.path)) as db:
            from colegio.administration import cash_summary
            from colegio.monthly_report import report as monthly
            from colegio.directory_reports import daily_report
            self.assertEqual(cash_summary(db,self.on)['income_usd'],1234);self.assertEqual(monthly(db,state,self.on[:7])['income_usd'],1234);self.assertEqual(daily_report(state)['income_usd'],1234)
        report=self.f.request('income-book');self.assertEqual(report['other'][0]['id'],identifier)
        self.assertNotIn('request_key',report['other'][0])
        self.f.request('expenses',dict(concept='Gasto ficticio',category='Operación',spent_on=self.on,amount='1',currency='USD',method='Transferencia',account_id=self.bank))
        self.f.request('users',dict(username='consulta',name='Consulta ficticia',password='FICTICIO-clave-segura',role='reader'))
        self.f.request('logout',{});self.f.request('login',dict(username='consulta',password='FICTICIO-clave-segura'));self.f.csrf=self.f.request('session')['user']['csrf']
        self.f.request('confirm-rate',dict(rate_date=self.on,rate='100'))
        view=self.f.request('income-book');self.assertNotIn('other',view);self.assertNotIn('bank',view['accounts'][0]);self.assertNotIn('last4',view['accounts'][0])
        self.f.request('income-account',dict(name='Prohibida'),status=403);self.f.request('income-deposit',{},status=403)

    def test_totals_cash_daily_monthly_and_arrears_and_cipher_restoration(self):
        from colegio.administration import cash_summary
        from colegio.server import snapshot
        from colegio.monthly_report import report as monthly
        from colegio.directory_reports import daily_report
        from colegio.backup_export import write_encrypted
        from tests.restore_helpers import approved_restore
        from tests.crypto_helpers import PASSWORD
        pid=self.f.request('payments',self.f.payment(amount='15',paid_on=self.on,method='Efectivo'))['id']
        baseline=self.f.request('state?history=1')['summary']
        self.f.request('income-deposit',self.deposit(pid))
        with closing(connect(self.f.path)) as db:
            cash=cash_summary(db,self.on);self.assertEqual(cash['income_usd'],1500);self.assertEqual(cash['expense_usd'],0)
            self.assertEqual({r['method']:r['net'] for r in cash['lines']},{'Efectivo':500,'Transferencia':1000})
            state=snapshot(db,dict(id=1,role='admin',name='Administración ficticia'))
            self.assertEqual(state['summary'],baseline)
            m=monthly(db,state,self.on[:7]);self.assertEqual(m['income_usd'],1500);self.assertEqual(sum(r['closing'] for r in m['balances']),1500)
            self.assertEqual(daily_report(state)['income_usd'],1500)
            from colegio.maintenance import review_database
            self.assertTrue(review_database(db)['ok'])
        cipher=self.f.path.parent/'income-restore.aulabak';write_encrypted(self.f.path,cipher,self.f.path.parent)
        restored=approved_restore(cipher,self.f.path.parent/'restored-income',credential=PASSWORD)
        with closing(connect(restored)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM cash_deposit_payments').fetchone()[0],1)
            self.assertEqual(cash_summary(db,self.on)['income_usd'],1500)

    def test_two_cashiers_cannot_deposit_the_same_cash_twice(self):
        import concurrent.futures,http.client,json
        pid=self.f.request('payments',self.f.payment(amount='10',paid_on=self.on,method='Efectivo'))['id']
        def attempt(key):
            client=http.client.HTTPConnection('127.0.0.1',self.f.server.server_port,timeout=15)
            client.request('POST','/api/income-deposit',json.dumps(self.deposit(pid,key=key)),{'Cookie':self.f.cookie,'X-CSRF-Token':self.f.csrf,'Content-Type':'application/json'})
            response=client.getresponse();response.read();status=response.status;client.close();return status
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sorted(pool.map(attempt,['cashier-a','cashier-b'])),[200,400])
        with closing(connect(self.f.path)) as db:self.assertEqual(db.execute('SELECT SUM(amount) FROM cash_deposits WHERE voided=0').fetchone()[0],1000)
