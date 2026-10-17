"""Real HTTP fiscal-form workflow; fictional records, no bank/SENIAT access."""
import base64
import copy
import hashlib
import http.client
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from colegio.db import connect,local_today,ValidationError
from colegio.invoice_layout import example_template


class InvoiceTests(unittest.TestCase):
    def setUp(self):
        from tests.test_system import SystemTests
        from colegio.invoices import defaults
        self.f=SystemTests();self.f.setUp();self.on=local_today().isoformat();self.month=self.on[:7]
        self.config=dict(defaults(),enabled=True,reviewed=True)
        self.f.request('invoice-config',dict(config=self.config))
        self.lot_data=dict(name='Lote FICTICIO',invoice_from='000001',invoice_to='000003',control_from='000101',control_to='000103',active=True,
            issuer=dict(name='Colegio FICTICIO',rif='J-FICTICIO',address='Dirección ficticia',printer_name='Imprenta FICTICIA',printer_rif='',authorization='NO VERIFICADO',printed_on='',notes='Prueba automatizada'))
        self.lot=self.f.request('invoice-batch',self.lot_data)['id']
        self.layout=example_template();self.layout['calibrated']=True
        self.template=self.f.request('invoice-template',dict(layout=self.layout))
        self.printer=dict(name='Impresora FICTICIA',x_tenths=0,y_tenths=0,scale=1,margin_mm=5)
        self.profile=self.f.request('invoice-profile',dict(profile=self.printer))['id']

    def tearDown(self):self.f.tearDown()

    def pay(self,key='invoice',amount='10'):
        return self.f.request('payments',self.f.payment(key=key,amount=amount,paid_on=self.on))['id']

    def body(self,pid):
        result=self.f.request('invoice-source?payment_id='+str(pid))
        result['client']['address']='Dirección FICTICIA';result.update(batch_id=self.lot,template_version_id=self.template['version_id'],profile_id=self.profile)
        return result

    def draft(self,pid=None):
        body=self.body(pid or self.pay());identifier=self.f.request('invoice-draft',body)['id']
        return identifier,body

    def issue_data(self,identifier,number=1):
        detail=self.f.request('invoice-detail?id='+str(identifier))
        return dict(id=identifier,confirmed_hash=detail['draft_hash'],invoice_number=str(number).zfill(6),control_number=str(number+100).zfill(6),numbers_confirmed=True)

    def issue(self,identifier,number=1,**extra):return self.f.request('invoice-issue',dict(self.issue_data(identifier,number),**extra))

    def test_calibration_and_drafts_do_not_consume_numbers_or_alter_receipt_totals(self):
        pid=self.pay();before=self.f.request('state')['summary'];receipt=self.f.request('receipt/'+str(pid)+'.pdf')
        result=self.f.request('invoice-test',dict(layout=self.layout,profile=self.printer,include_background=True))
        self.assertIn(b'NO CONSUME',base64.b64decode(result['pdf_base64']))
        identifier,_=self.draft(pid);preview=self.f.request('invoice-preview',dict(id=identifier))
        self.assertIn(b'NO CONSUME',base64.b64decode(preview['pdf_base64']))
        book=self.f.request('invoice-book');self.assertEqual(book['batches'][0]['proposal']['invoice'],'000001');self.assertFalse(book['sales'])
        with closing(connect(self.f.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM invoices WHERE invoice_key IS NOT NULL').fetchone()[0],0)
        self.assertEqual(self.f.request('receipt/'+str(pid)+'.pdf'),receipt);self.assertEqual(self.f.request('state')['summary'],before)

    def test_issue_immutable_reprint_exact_even_after_template_profile_changes_and_no_scan(self):
        from colegio.branding import logo_bytes,LOGO_FILE
        self.layout['background']='data:image/png;base64,'+base64.b64encode(logo_bytes(LOGO_FILE)).decode()
        self.template=self.f.request('invoice-template',dict(id=self.template['id'],layout=self.layout))
        pid=self.pay();before=self.f.request('state')['summary'];receipt=self.f.request('receipt/'+str(pid)+'.pdf')
        identifier,body=self.draft(pid);self.issue(identifier,include_background=True)
        first=self.f.request('invoice-print',dict(id=identifier));raw=base64.b64decode(first['pdf_base64'])
        self.assertNotIn(b'/Scan',raw);self.assertIn(b'/MediaBox [0 0 396 612]',raw)
        self.layout['fields'][0]['x_mm']=12
        self.f.request('invoice-template',dict(id=self.template['id'],layout=self.layout))
        self.f.request('invoice-profile',dict(id=self.profile,profile=dict(self.printer,x_tenths=10)))
        self.f.request('invoice-print',dict(id=identifier),status=400)
        second=self.f.request('invoice-print',dict(id=identifier,reprint_confirmed=True,reason='Reimpresión FICTICIA de comprobación'))
        self.assertEqual(first['pdf_base64'],second['pdf_base64']);self.assertTrue(second['reprint'])
        self.f.request('invoice-edit-draft',dict(body,id=identifier,confirmed_hash='no'),status=400)
        with closing(connect(self.f.path)) as db:
            with self.assertRaises(sqlite3.IntegrityError):db.execute("UPDATE invoices SET snapshot_json='{}' WHERE id=?",(identifier,))
            db.rollback()
        report=self.f.request('invoice-sales');self.assertEqual(report['totals'],{'USD':1000});self.assertEqual(report['records'][0]['invoice'],'000001')
        csv=self.f.request('invoice-sales.csv');self.assertTrue(csv.startswith(b'\xef\xbb\xbf'));self.assertIn(b"'000001",csv)
        self.assertNotIn(b'Alumno Uno',csv);self.assertNotIn(b'A-001',csv);self.assertTrue(self.f.request('invoice-sales.pdf').startswith(b'%PDF'))
        self.assertEqual(self.f.request('state')['summary'],before);self.assertEqual(self.f.request('receipt/'+str(pid)+'.pdf'),receipt)
        self.assertTrue(self.f.request('maintenance-review')['ok'])

    def test_ranges_confirmation_duplicate_exhaustion_and_damaged_sheets_remain_accounted(self):
        d,_=self.draft();data=self.issue_data(d)
        self.f.request('invoice-issue',dict(data,numbers_confirmed=False),status=400)
        self.f.request('invoice-issue',dict(data,invoice_number='000004'),status=400)
        self.issue(d);d2,_=self.draft(self.pay('second'))
        self.f.request('invoice-issue',self.issue_data(d2),status=400)
        self.f.request('invoice-damaged',dict(batch_id=self.lot,issued_on=self.on,invoice_number='000002',control_number='000102',numbers_confirmed=True,reason='Hoja FICTICIA dañada en prueba'))
        self.issue(d2,3)
        self.assertEqual(self.f.request('invoice-book')['batches'][0]['proposal']['warning'],'Lote agotado')
        self.f.request('invoice-void',dict(id=d,reason='Anulación FICTICIA de prueba'))
        self.f.request('invoice-issue',self.issue_data(d),status=400)
        rows=self.f.request('invoice-sales')['records'];self.assertEqual([r['state'] for r in rows],['void','damaged','issued'])
        with closing(connect(self.f.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(DISTINCT control_key) FROM invoices WHERE control_key IS NOT NULL').fetchone()[0],3)
            with self.assertRaises(sqlite3.IntegrityError):db.execute('DELETE FROM invoices WHERE id=?',(d,))
            db.rollback()

    def test_jump_needs_reason_and_administrator_can_account_older_damaged_sheet(self):
        first,_=self.draft();self.issue(first)
        third,_=self.draft(self.pay('third'))
        self.f.request('invoice-issue',self.issue_data(third,3),status=400)
        self.issue(third,3,gap_confirmed=True,gap_reason='Salto FICTICIO revisado con soporte')
        self.assertEqual(self.f.request('invoice-book')['pending']['invoice_numbers'],2)
        self.f.request('invoice-damaged',dict(batch_id=self.lot,issued_on=self.on,invoice_number='000002',control_number='000102',numbers_confirmed=True,prior_gap_confirmed=True,reason='Regularización FICTICIA de hoja anterior'))
        self.assertEqual(self.f.request('invoice-book')['pending']['invoice_numbers'],0)

    def test_template_versions_export_import_restore_and_unverified_import_cannot_emit(self):
        exported=self.f.request('invoice-template.json?version_id='+str(self.template['version_id']))
        exported['name']='Importada FICTICIA'
        imported=self.f.request('invoice-import-template',dict(json=json.dumps(exported)))
        view=self.f.request('invoice-template?version_id='+str(imported['version_id']));self.assertFalse(view['layout']['calibrated'])
        self.layout['fields'][0]['x_mm']=13
        changed=self.f.request('invoice-template',dict(id=self.template['id'],layout=self.layout))
        restored=self.f.request('invoice-template-restore',dict(version_id=self.template['version_id']))
        self.assertGreater(restored['version_id'],changed['version_id'])
        view=self.f.request('invoice-template?version_id='+str(restored['version_id']))
        self.assertEqual(view['layout']['fields'][0]['x_mm'],10);self.assertEqual(len(view['history']),3)
        with closing(connect(self.f.path)) as db:
            with self.assertRaises(sqlite3.IntegrityError):db.execute("UPDATE invoice_template_versions SET layout_json='{}'")
            db.rollback()
        self.template=imported;identifier,_=self.draft()
        self.f.request('invoice-issue',self.issue_data(identifier),status=400)

    def test_month_close_blocks_invoice_changes_and_print_is_logged_without_changing_frozen_relation(self):
        first,_=self.draft();self.issue(first);second,body=self.draft(self.pay('pending'))
        period=self.f.request('accounting-report');self.assertEqual(period['income'][0]['invoice'],'000001')
        self.f.request('month-close',dict(period=self.month,confirmed_hash=period['preview_hash'],confirmed_pending=True))
        frozen=self.f.request('accounting-report')
        self.f.request('invoice-draft',body,status=400)
        self.f.request('invoice-edit-draft',dict(body,id=second,confirmed_hash=self.f.request('invoice-detail?id='+str(second))['draft_hash']),status=400)
        self.f.request('invoice-issue',self.issue_data(second,2),status=400)
        self.f.request('invoice-void',dict(id=first,reason='Anulación FICTICIA no permitida'),status=400)
        self.f.request('invoice-damaged',dict(batch_id=self.lot,issued_on=self.on,invoice_number='000002',control_number='000102',numbers_confirmed=True,reason='Hoja FICTICIA en mes cerrado'),status=400)
        self.f.request('invoice-print',dict(id=first));self.assertEqual(self.f.request('accounting-report'),frozen)

    def test_invalid_totals_unknown_fields_tax_activation_and_stale_draft_are_rejected(self):
        pid=self.pay();body=self.body(pid)
        body['items'][0]['unit_price']='9.99';self.f.request('invoice-draft',body,status=400)
        body=self.body(pid);body['client']['student_document']='NO';self.f.request('invoice-draft',body,status=400)
        self.f.request('invoice-config',dict(config=dict(self.config,iva_enabled=True)),status=400)
        identifier,body=self.draft(pid)
        self.f.request('invoice-edit-draft',dict(body,id=identifier,confirmed_hash='stale'),status=400)
        self.f.request('invoice-issue',dict(self.issue_data(identifier),confirmed_hash='stale'),status=400)
        with closing(connect(self.f.path)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM invoices WHERE invoice_key IS NOT NULL').fetchone()[0],0)

    def client(self,username):
        session={'cookie':'','csrf':''}
        def call(route,data=None):
            connection=http.client.HTTPConnection('127.0.0.1',self.f.server.server_port,timeout=20)
            connection.request('GET' if data is None else 'POST','/api/'+route,json.dumps(data) if data is not None else None,
                {'Cookie':session['cookie'],'X-CSRF-Token':session['csrf'],'Content-Type':'application/json'})
            response=connection.getresponse();raw=response.read();cookie=response.getheader('Set-Cookie')
            if cookie:session['cookie']=cookie.split(';')[0]
            status=response.status;connection.close();return status,json.loads(raw)
        self.assertEqual(call('login',dict(username=username,password='FICTICIO-clave-segura'))[0],200)
        session['csrf']=call('session')[1]['user']['csrf']
        self.assertEqual(call('confirm-rate',dict(rate_date=self.on,rate='100'))[0],200)
        return call

    def test_two_real_cashier_sessions_cannot_issue_the_same_preprinted_number(self):
        for username in ('caja-fiscal-a','caja-fiscal-b'):
            self.f.request('users',dict(username=username,name=username,role='cashier',password='FICTICIO-clave-segura'))
        pids=[self.pay('cashier-a'),self.pay('cashier-b')];clients=[self.client(name) for name in ('caja-fiscal-a','caja-fiscal-b')];issues=[]
        for client,pid in zip(clients,pids):
            body=self.body(pid);status,result=client('invoice-draft',body);self.assertEqual(status,200,result)
            identifier=result['id'];status,detail=client('invoice-detail?id='+str(identifier));self.assertEqual(status,200)
            issues.append(dict(id=identifier,confirmed_hash=detail['draft_hash'],invoice_number='000001',control_number='000101',numbers_confirmed=True))
        def emit(index):return clients[index]('invoice-issue',issues[index])[0]
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sorted(pool.map(emit,(0,1))),[200,400])
        with closing(connect(self.f.path)) as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM invoices WHERE state='issued'").fetchone()[0],1)

    def test_portable_cipher_restores_exact_pdf_template_prints_and_opens_read_only(self):
        from tests.crypto_helpers import configure,PASSWORD
        from tests.restore_helpers import approved_restore
        from colegio.backup_export import write_encrypted
        from colegio.backup_inspection import probe_backup
        from colegio.read_only import open_copy
        from colegio.storage import consistent_backup
        identifier,_=self.draft();self.issue(identifier);printed=self.f.request('invoice-print',dict(id=identifier))
        cipher=self.f.path.parent/'factura-portatil.aulabak'
        snapshot=self.f.path.parent/'invoice-consistent.sqlite3';consistent_backup(self.f.path,snapshot)
        with tempfile.TemporaryDirectory(prefix='aula-fiscal-claves-ficticias-') as keys:
            recovery=configure(keys);write_encrypted(snapshot,cipher,keys)
        self.assertFalse(Path(keys).exists());digest=hashlib.sha256(cipher.read_bytes()).hexdigest()
        for credential,kind in ((PASSWORD,'password'),(recovery,'recovery')):
            with self.subTest(kind=kind):
                self.assertEqual(probe_backup(cipher,credential,kind)['schema'],16)
                target=approved_restore(cipher,self.f.path.parent/('invoice-'+kind),credential=credential,credential_kind=kind)
                with closing(connect(target)) as db:
                    self.assertEqual(db.execute('SELECT pdf_base64 FROM invoices WHERE id=?',(identifier,)).fetchone()[0],printed['pdf_base64'])
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM invoice_print_events').fetchone()[0],1)
                    from colegio.maintenance import review_database
                    self.assertTrue(review_database(db)['ok'])
                with open_copy(cipher,credential,kind) as viewer:
                    with closing(viewer.connect_view()) as db:
                        self.assertEqual(db.execute('SELECT pdf_base64 FROM invoices').fetchone()[0],printed['pdf_base64'])
                        with self.assertRaises(sqlite3.OperationalError):db.execute('DELETE FROM invoices')
                    temporary=Path(viewer.db_path).parent
                self.assertFalse(temporary.exists());self.assertEqual(hashlib.sha256(cipher.read_bytes()).hexdigest(),digest)

    def test_restore_older_backup_twice_never_frees_known_printed_numbers(self):
        from tests.crypto_helpers import PASSWORD
        from tests.restore_helpers import approved_restore
        from colegio.backup_export import write_encrypted
        from colegio.storage import consistent_backup
        from colegio.invoices import batch,next_numbers,numbers,preferences
        identifier,_=self.draft();cipher=self.f.path.parent/'antes-emitir.aulabak'
        snapshot=self.f.path.parent/'antes-emitir.sqlite3';consistent_backup(self.f.path,snapshot)
        write_encrypted(snapshot,cipher,self.f.path.parent);self.issue(identifier)
        target=self.f.path.parent/'restore-with-known-invoices';target.mkdir()
        consistent_backup(self.f.path,target/'colegio.sqlite3')
        for attempt in range(2):
            restored=approved_restore(cipher,target,credential=PASSWORD)
            with closing(connect(restored)) as db:
                lot=batch(db,self.lot);self.assertEqual(next_numbers(db,lot)['invoice'],'000002')
                self.assertFalse(preferences(db)['reviewed'])
                with self.assertRaisesRegex(ValidationError,'restauración'):
                    numbers(db,lot,dict(invoice_number='000001',control_number='000101',numbers_confirmed=True))
