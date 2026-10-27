"""Cashea concurrency, rollback, encrypted restoration and protected read-only views."""
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import hashlib,http.client,json,sqlite3,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from tests import test_cashea as flows
from colegio.db import connect
from colegio.storage import consistent_backup
from colegio.backup_inspection import inspect_copy,probe_backup
from colegio.audit_chain import portable_status


class CasheaIntegrationTests(unittest.TestCase):
    setUp=flows.CasheaTests.setUp
    tearDown=flows.CasheaTests.tearDown
    request=flows.CasheaTests.request
    student_data=flows.CasheaTests.student_data
    new_student=flows.CasheaTests.new_student
    order_data=flows.CasheaTests.order_data
    order=flows.CasheaTests.order
    settlement=flows.CasheaTests.settlement

    def test_concurrent_retry_has_one_order_one_initial_and_one_cached_response(self):
        data=self.order_data();data['preview_hash']=self.request('cashea-preview',data)['preview_hash']
        def send(_):
            conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=30)
            conn.request('POST','/api/cashea-order',json.dumps(data),{'Cookie':self.cookie,'X-CSRF-Token':self.csrf,'Content-Type':'application/json'})
            response=conn.getresponse();status=response.status;result=json.loads(response.read());conn.close();return status,result
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(send,range(4)))
        self.assertEqual({status for status,_ in results},{200})
        self.assertTrue(all(result==results[0][1] for _,result in results))
        with closing(connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM cashea_orders').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM payments').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM cashea_requests').fetchone()[0],1)
            self.assertTrue(portable_status(db)['ok'])

    def test_same_bank_reference_is_rejected_without_liquidating_other_orders(self):
        first,_=self.order();other,_=self.order(student_id=self.new_student())
        self.settlement([first['id']],reference='000123 FICTICIO')
        self.request('cashea-settlement-preview',dict(order_ids=[other['id']],received_on=self.request('state')['today'],currency='USD',amount='52',reference='000123FICTICIO'),status=400)
        self.assertEqual(next(o for o in self.request('cashea')['orders'] if o['id']==other['id'])['state'],'por_liquidar')

    def test_cashier_completes_sale_and_settlement_reader_only_reads_admin_controls_rejected(self):
        from colegio.db import local_today
        from colegio.cashea import ADMIN
        for role in ('cashier','reader'):self.request('users',dict(name=role,username=role,password='FICTICIO-Cashea-permisos',role=role))
        self.request('logout',{});self.request('login',dict(username='cashier',password='FICTICIO-Cashea-permisos'))
        self.csrf=self.request('session')['user']['csrf'];self.request('confirm-rate',dict(rate_date=local_today().isoformat(),rate='100'))
        order,_=self.order();self.settlement([order['id']])
        for endpoint in ADMIN:self.request(endpoint,dict(id=order['id'],reason='FICTICIO',request_key='cashea-caja-prohibida'),status=403)
        self.request('logout',{});self.request('login',dict(username='reader',password='FICTICIO-Cashea-permisos'))
        self.csrf=self.request('session')['user']['csrf'];self.request('confirm-rate',dict(rate_date=local_today().isoformat(),rate='100'))
        self.assertEqual(self.request('cashea')['settlements'][0]['amount'],5200)
        self.assertEqual(self.request('state')['summary']['income'],13000)
        self.request('cashea-order',self.order_data(),status=403)

    def test_restoring_older_copy_preserves_ca_cl_floors_and_reports_excluded_records(self):
        from tests.restore_helpers import approved_restore
        from colegio.db import next_record_id
        old=self.path.parent/'anterior.sqlite3';consistent_backup(self.path,old)
        order,_=self.order();settlement,_=self.settlement([order['id']])
        self.server.shutdown();self.server.server_close();self.thread.join()
        restored=approved_restore(old,self.path.parent)
        with closing(connect(restored)) as db:
            self.assertEqual(next_record_id(db,'cashea_orders'),order['id']+1)
            self.assertEqual(next_record_id(db,'cashea_settlements'),settlement['id']+1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM cashea_orders').fetchone()[0],0)
            self.assertTrue(portable_status(db)['ok'])

    def test_cipher_restore_preserves_coverage_money_floors_and_loss_reports(self):
        from colegio.backup_export import write_encrypted
        from tests.crypto_helpers import PASSWORD
        from tests.restore_helpers import approved_restore
        from colegio.restore_reports import compare,loss_csv
        old=self.path.parent/'antes.sqlite3';consistent_backup(self.path,old)
        order,_=self.order();settlement,_=self.settlement([order['id']])
        cipher=self.path.parent/'cashea.aulabak';write_encrypted(self.path,cipher,self.path.parent)
        summary=probe_backup(cipher,PASSWORD)
        self.assertEqual(summary['cashea_orders'],1);self.assertEqual(summary['cashea_settlements'],1)
        self.assertEqual(summary['income_usd'],13000)
        self.assertEqual(summary['floors']['cashea_orders'],order['id'])
        saved=self.path.parent/'actual.sqlite3';consistent_backup(self.path,saved)
        comparison=compare(inspect_copy(saved),inspect_copy(old));raw=loss_csv(comparison)
        self.assertIn(b'CA-000001',raw);self.assertIn(b'CL-000001',raw)
        restored=approved_restore(cipher,self.path.parent/'restaurada',credential=PASSWORD)
        with closing(connect(restored)) as db:
            from colegio.maintenance import review_database
            from colegio.db import charges
            self.assertTrue(review_database(db)['ok']);self.assertTrue(portable_status(db)['ok'])
            self.assertEqual(sum(c['balance'] for c in charges(db,self.sid)),0)
            self.assertEqual(db.execute('SELECT amount FROM cashea_settlements').fetchone()[0],5200)

    def test_read_only_copy_has_cashea_figures_and_original_is_unchanged(self):
        from colegio.read_only import open_copy
        from colegio.server import snapshot
        from colegio.cashea import book,integrity_errors
        order,_=self.order();self.settlement([order['id']])
        saved=self.path.parent/'consulta.sqlite3';consistent_backup(self.path,saved)
        before=hashlib.sha256(saved.read_bytes()).hexdigest()
        with open_copy(saved) as server:
            with closing(server.connect_view()) as db:
                state=snapshot(db,dict(id=0,name='Consulta',role='reader'))
                self.assertEqual(state['summary']['income'],13000)
                self.assertEqual(book(db)['settlements'][0]['amount'],5200)
                self.assertFalse(integrity_errors(db))
                with self.assertRaises(sqlite3.OperationalError):db.execute('DELETE FROM cashea_orders')
        self.assertEqual(before,hashlib.sha256(saved.read_bytes()).hexdigest())

    def test_real_process_kill_before_commit_rolls_back_initial_coverage_and_request(self):
        # Shutdown HTTP before testing a separate, real writer process against our temporary ledger.
        self.server.shutdown();self.thread.join();self.server.server_close()
        data=self.order_data()
        child='''
import sys,json,time
from pathlib import Path
from contextlib import closing
from colegio.db import connect
from colegio.server import mutate
from colegio import cashea
def pause(stage):
    if stage==sys.argv[2]:
        Path(sys.argv[3]).write_text(stage)
        while True:time.sleep(.1)
cashea.checkpoint=pause
with closing(connect(sys.argv[1])) as db,db:
    user=dict(db.execute("SELECT * FROM users WHERE role='admin'").fetchone())
    data=json.loads(sys.argv[4])
    data['preview_hash']=cashea.preview(db,data,user)['preview_hash']
    mutate(db,'cashea-order',data,user)
'''
        for stage in ('order_created','action_complete'):
            marker=self.path.parent/('paused-'+stage)
            proc=subprocess.Popen([sys.executable,'-c',child,str(self.path),stage,str(marker),json.dumps(data)])
            try:
                deadline=time.monotonic()+20
                while not marker.exists() and proc.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(marker.exists(),(stage,proc.poll()))
            finally:
                if proc.poll() is None:proc.kill()
                proc.wait(timeout=10)
            with closing(connect(self.path)) as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                for table in ('payments','allocations','cashea_orders','cashea_allocations','cashea_requests'):
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0,table)
                self.assertTrue(portable_status(db)['ok'])
