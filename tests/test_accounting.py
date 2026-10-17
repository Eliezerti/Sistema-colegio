from contextlib import closing
import unittest
from colegio.db import connect,local_today

class AccountingTests(unittest.TestCase):
    def setUp(self):
        from tests.test_system import SystemTests
        self.f=SystemTests();self.f.setUp();self.on=local_today().isoformat();self.period=self.on[:7];self.bank=self.f.school_accounts[('USD','bank')]
    def tearDown(self):self.f.tearDown()
    def pay(self,key='month',method='Transferencia'):
        data=self.f.payment(amount='10',paid_on=self.on,key=key,reference='FICTICIO-'+key,method=method)
        return self.f.request('payments',data)['id'],data
    def report(self):return self.f.request('accounting-report?month='+self.period)
    def close(self):
        report=self.report();return self.f.request('month-close',dict(period=self.period,confirmed_hash=report['preview_hash'],confirmed_pending=True))
    def test_close_stale_hash_pending_flags_exports_and_frozen_report(self):
        pid,_=self.pay();before=self.f.request('state?history=1')['summary'];report=self.report()
        self.f.request('month-close',dict(period=self.period,confirmed_hash='bad',confirmed_pending=True),status=400)
        self.f.request('month-close',dict(period=self.period,confirmed_hash=report['preview_hash']),status=400)
        self.f.request('month-annotation',dict(source='P'+str(pid),special_taxpayer=True,foreign_currency=True))
        self.f.request('month-close',dict(period=self.period,confirmed_hash=report['preview_hash'],confirmed_pending=True),status=400)
        closed=self.close();saved=self.report();self.assertTrue(saved['closed']);self.assertEqual(saved['closure']['id'],closed['id'])
        self.assertEqual(saved['totals']['income_usd'],1000);self.assertTrue(saved['income'][0]['special_taxpayer']);self.assertEqual(saved['income'][0]['ves_equivalent'],100000)
        self.assertEqual(self.f.request('state?history=1')['summary'],before)
        csv=self.f.request('accounting-report.csv?month='+self.period);self.assertTrue(csv.startswith(b'\xef\xbb\xbf'));self.assertIn(b'R-000001',csv)
        self.assertTrue(self.f.request('accounting-report.pdf?month='+self.period).startswith(b'%PDF'))
        with closing(connect(self.f.path)) as db:
            student=dict(db.execute('SELECT * FROM students WHERE id=?',(self.f.student,)).fetchone())
            self.assertNotIn(student['document'],csv.decode('utf-8'));self.assertNotIn(student['name'],csv.decode('utf-8'));self.assertNotIn('birth_date',csv.decode('utf-8'))
            from colegio.audit_chain import local_status
            self.assertTrue(local_status(db)['ok'])
        self.assertTrue(self.f.request('maintenance-review')['ok'])
        self.assertNotIn('id_floor_payments',saved['school']);self.assertNotIn('backup_directory',saved['school'])
        self.f.request('rates',dict(rate_date=self.on,rate='101'))
        self.assertEqual(self.report(),saved,'The closed relation is a frozen snapshot, including rates and annotations')
    def test_closed_month_blocks_http_writes_but_confirmed_retry_is_unchanged(self):
        pid,retry=self.pay();cash,_=self.pay('cash','Efectivo')
        eid=self.f.request('expenses',dict(concept='Ficticio egreso',category='Operación',amount='1',currency='USD',method='Transferencia',account_id=self.bank,spent_on=self.on))['id']
        category=self.f.request('income-category',dict(name='Ficticio aporte'))['id']
        other=dict(concept='Aporte ficticio',category_id=category,received_on=self.on,amount='1',currency='USD',method='Transferencia',account_id=self.bank,reference='AP',support='Soporte ficticio',request_key='other')
        oid=self.f.request('income-other',other)['id']
        deposit=dict(deposited_on=self.on,account_id=self.bank,currency='USD',amount='5',reference='FICTICIO-DEP',support='Planilla ficticia',request_key='dep',payments=[dict(payment_id=cash,amount='5')])
        did=self.f.request('income-deposit',deposit)['id'];self.close();before=self.f.request('state?history=1')['summary']
        cases=[('payments',dict(retry,request_key='new')),('void-payment',dict(id=pid,reason='Prueba ficticia de anulación')),
            ('expenses',dict(concept='Ficticio',category='Operación',amount='1',currency='USD',method='Efectivo',spent_on=self.on)),('void-expense',dict(id=eid,reason='Prueba ficticia de anulación')),
            ('income-other',dict(other,request_key='new-other')),('income-void-other',dict(id=oid,reason='Prueba ficticia de anulación')),
            ('income-deposit',dict(deposit,request_key='new-dep')),('income-void-deposit',dict(id=did,reason='Prueba ficticia de anulación')),
            ('income-assign',dict(kind='payments',ids=[pid],account_id=self.bank,reason='Prueba ficticia de asignación')),
            ('month-annotation',dict(source='P'+str(pid),special_taxpayer=False,foreign_currency=True))]
        for endpoint,data in cases:
            with self.subTest(endpoint=endpoint):self.f.request(endpoint,data,status=400)
        self.assertTrue(self.f.request('payments',retry)['duplicate']);self.assertEqual(self.f.request('state?history=1')['summary'],before)
    def test_closed_month_blocks_import_links_classification_and_reopening_requires_role_reason(self):
        from tests.test_bank_book import BankBookTests
        b=BankBookTests();b.f=self.f;b.on=self.on;b.bank=self.bank;b.profile=dict(delimiter=';',encoding='utf-8-sig',decimal='.',date_format='%Y-%m-%d',columns=dict(date='Fecha',amount='Importe',reference='Referencia',description='Descripción',bank_id='ID'))
        pid,_=self.pay();b.imported([[self.on,'10','FICTICIO-month','Ficticio','M1']])
        cid=self.close()['id'];self.f.request('bank-auto',{},status=400)
        self.f.request('bank-link',dict(links=[dict(movement_id=1,source='P'+str(pid),amount='10')],reason='Prueba ficticia de cruce'),status=400)
        self.f.request('bank-classify',dict(movement_id=1,category='Otro',support='Ficticio',reason='Prueba ficticia de clasificación'),status=400)
        data=b.data([[self.on,'1','x','Ficticio','M2']]);preview=self.f.request('bank-preview',data);self.f.request('bank-import',dict(data,confirmed_hash=preview['file_sha256']),status=400)
        self.f.request('month-reopen',dict(id=cid,reason='corto'),status=400)
        self.f.request('users',dict(username='caja-mes',name='Caja ficticia',role='cashier',password='FICTICIO-clave-segura'))
        self.f.request('logout',{});self.f.request('login',dict(username='caja-mes',password='FICTICIO-clave-segura'));self.f.csrf=self.f.request('session')['user']['csrf'];self.f.request('confirm-rate',dict(rate_date=self.on,rate='100'))
        self.f.request('month-reopen',dict(id=cid,reason='No permitido a Caja'),status=403);self.f.request('month-close',{},status=403)
        self.assertTrue(self.report()['closed'])
        self.f.request('logout',{});self.f.request('login',dict(username='admin',password='Una-clave-segura'));self.f.csrf=self.f.request('session')['user']['csrf'];self.f.request('confirm-rate',dict(rate_date=self.on,rate='100'))
        self.f.request('month-reopen',dict(id=cid,reason='Revisión ficticia autorizada del mes'));self.assertFalse(self.report()['closed']);self.assertEqual(self.f.request('bank-auto',{})['linked'],1)
    def test_missing_historical_usd_rate_is_unknown_and_signed_csv_does_not_change_money(self):
        pid,_=self.pay()
        with closing(connect(self.f.path)) as db,db:db.execute("UPDATE payment_accounts SET bcv_rate='' WHERE payment_id=?",(pid,))
        result=self.report();self.assertEqual(result['pending']['missing_rates'],1);self.assertIsNone(result['income'][0]['ves_equivalent']);self.assertIn('NO VERIFICADO',result['income'][0]['verification'])
        from colegio.accounting import decimal_amount
        self.assertEqual(decimal_amount(-150),'-1.50');self.assertEqual(decimal_amount(-1),'-0.01')
    def test_totals_daily_monthly_and_debt_identical_after_close_reopen(self):
        self.pay();before=self.f.request('state?history=1')['summary'];monthly=self.f.request('monthly-report?month='+self.period);daily=self.f.request('daily-report');cid=self.close()['id']
        relation=self.report();self.assertEqual(relation['totals']['income_usd'],monthly['income_usd']);self.assertEqual(relation['totals']['net_usd'],monthly['net_usd'])
        self.f.request('month-reopen',dict(id=cid,reason='Revisión ficticia sin movimientos'))
        self.assertEqual(self.f.request('state?history=1')['summary'],before)
        self.assertEqual(self.f.request('monthly-report?month='+self.period)['summaries'],monthly['summaries']);self.assertEqual(self.f.request('daily-report')['summaries'],daily['summaries'])

    def test_closed_reconciled_book_restores_and_opens_without_origin_keyring(self):
        """Combined new records survive portable recovery, not only empty schemas."""
        import hashlib,sqlite3,tempfile
        from pathlib import Path
        from tests.test_bank_book import BankBookTests
        from tests.crypto_helpers import configure,PASSWORD
        from tests.restore_helpers import approved_restore
        from colegio.accounting import report
        from colegio.audit_chain import local_status
        from colegio.backup_export import write_encrypted
        from colegio.backup_inspection import probe_backup
        from colegio.maintenance import review_database
        from colegio.read_only import open_copy
        from colegio.income_schema import TABLES as income_tables
        from colegio.bank_schema import TABLES as bank_tables
        from colegio.month_schema import TABLES as month_tables
        pid,_=self.pay()
        b=BankBookTests();b.f=self.f;b.on=self.on;b.bank=self.bank
        b.profile=dict(delimiter=';',encoding='utf-8-sig',decimal='.',date_format='%Y-%m-%d',columns=dict(date='Fecha',amount='Importe',reference='Referencia',description='Descripción',bank_id='ID'))
        b.imported([[self.on,'10','FICTICIO-month','Ficticio conciliado','PORTABLE-1'],[self.on,'2','APORTE','Ficticio clasificado','PORTABLE-2']])
        self.assertEqual(self.f.request('bank-auto',{})['linked'],1)
        self.f.request('bank-classify',dict(movement_id=2,category='Préstamo o aporte',support='Soporte ficticio',reason='Clasificación ficticia para recuperación'))
        self.f.request('month-annotation',dict(source='P'+str(pid),special_taxpayer=True,foreign_currency=False))
        self.close();saved=self.report()
        with closing(connect(self.f.path)) as db:
            expected={table:[tuple(r) for r in db.execute('SELECT * FROM '+table)] for table in (*income_tables,*bank_tables,*month_tables)}
        # Independent, disposable keyring disappears before either credential is used.
        cipher=self.f.path.parent/'portable-closed-book.aulabak'
        with tempfile.TemporaryDirectory(prefix='aula-claves-ficticias-') as keys:
            recovery=configure(keys);write_encrypted(self.f.path,cipher,keys)
        self.assertFalse(Path(keys).exists())
        digest=hashlib.sha256(cipher.read_bytes()).hexdigest()
        for credential,kind in ((PASSWORD,'password'),(recovery,'recovery')):
            with self.subTest(credential_kind=kind):
                from colegio.branding import SCHEMA_VERSION
                self.assertEqual(probe_backup(cipher,credential,kind)['schema'],SCHEMA_VERSION)
                target=self.f.path.parent/('recuperado-'+kind)
                restored=approved_restore(cipher,target,credential=credential,credential_kind=kind)
                with closing(connect(restored)) as db:
                    self.assertEqual(report(db,self.period),saved)
                    for table,rows in expected.items():self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM '+table)],rows,table)
                    self.assertTrue(local_status(db)['ok']);self.assertTrue(review_database(db)['ok'])
                    self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())
                with open_copy(cipher,credential,kind) as viewer:
                    with closing(viewer.connect_view()) as db:
                        self.assertEqual(report(db,self.period),saved)
                        self.assertEqual(db.execute('SELECT COUNT(*) FROM reconciliation_links WHERE voided=0').fetchone()[0],1)
                        with self.assertRaises(sqlite3.OperationalError):db.execute('DELETE FROM accounting_closures')
                    temporary=Path(viewer.db_path).parent
                self.assertFalse(temporary.exists());self.assertEqual(hashlib.sha256(cipher.read_bytes()).hexdigest(),digest)
