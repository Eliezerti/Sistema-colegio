"""Upgrade the actually delivered schema-13 fixture, including approved duplicates."""
from contextlib import closing
from datetime import date
from pathlib import Path
from unittest.mock import patch
import hashlib,json,shutil,sqlite3,subprocess,sys,tempfile,time,unittest
from colegio.db import connect,initialize
from colegio.audit_chain import adopt_restored,portable_status,local_status
from colegio.backup_inspection import probe_backup
from colegio.administration import cash_summary
from colegio.server import snapshot
from colegio.directory_reports import daily_report
from colegio.monthly_report import report

FIXTURES=Path(__file__).parent/'fixtures/cashea'


class CasheaInvoiceMigrationTests(unittest.TestCase):
    def fixture(self,directory):
        m=json.loads((FIXTURES/'manifest-schema13.json').read_text());source=FIXTURES/m['filename']
        self.assertEqual(m['schema'],13);self.assertTrue(m['fictional']);self.assertTrue(m['commit'].startswith('e3ba2d6'))
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),m['sha256'])
        p=Path(directory)/'colegio.sqlite3';shutil.copyfile(source,p);adopt_restored(p);return p

    def verify(self,path):
        with closing(connect(path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],14)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())
            self.assertTrue(portable_status(db)['ok']);self.assertTrue(local_status(db)['ok'])
            from colegio.maintenance import review_database
            self.assertTrue(review_database(db)['ok'])

    def test_delivered_13_preserves_manual_numbers_duplicates_snapshots_totals_chain_and_verified_rollback(self):
        with tempfile.TemporaryDirectory() as temp:
            p=self.fixture(temp)
            with closing(connect(p)) as db:
                payments=[tuple(r) for r in db.execute('SELECT * FROM payments ORDER BY id')]
                orders=[dict(r) for r in db.execute('SELECT * FROM cashea_orders ORDER BY id')]
                audit=[tuple(r) for r in db.execute('SELECT * FROM audit ORDER BY id')]
                links=[tuple(r) for r in db.execute('SELECT * FROM audit_links ORDER BY audit_id')]
            initialize(p);initialize(p);self.verify(p)
            copies=list((p.parent/'backups').glob('antes-numero-cashea-*.sqlite3'));self.assertEqual(len(copies),1)
            meta=json.loads(copies[0].with_suffix('.migration.json').read_text())
            self.assertEqual(hashlib.sha256(copies[0].read_bytes()).hexdigest(),meta['sha256']);self.assertEqual(probe_backup(copies[0])['schema'],13)
            golden=json.loads((FIXTURES/'referencia-schema13.json').read_text())
            with closing(connect(p)) as db:
                self.assertEqual(payments,[tuple(r) for r in db.execute('SELECT * FROM payments ORDER BY id')])
                self.assertEqual(orders,[{k:v for k,v in dict(r).items() if k!='invoice_origin'} for r in db.execute('SELECT * FROM cashea_orders ORDER BY id')])
                self.assertEqual([r[0] for r in db.execute('SELECT invoice_origin FROM cashea_orders')],['manual','manual'])
                self.assertEqual(db.execute("SELECT value FROM settings WHERE key='cashea_invoice_origin'").fetchone()[0],'recibo')
                self.assertEqual(audit,[tuple(r) for r in db.execute('SELECT * FROM audit ORDER BY id')][:len(audit)])
                self.assertEqual(links,[tuple(r) for r in db.execute('SELECT * FROM audit_links ORDER BY audit_id')][:len(links)])
                with patch('colegio.server.local_today',return_value=date(2026,10,27)):s=snapshot(db,dict(id=1,role='admin',name='Auditor FICTICIO'))
                self.assertEqual(s['summary'],golden['summary']);self.assertEqual(cash_summary(db,'2026-10-27'),golden['cash'])
                for actual,expected in ((daily_report(s),golden['daily']),(report(db,s,'2026-10'),golden['monthly'])):
                    # Compare all money, rows and sections; exclude only the added preference and emission clock.
                    actual=json.loads(json.dumps(actual));actual['school'].pop('cashea_invoice_origin')
                    actual.pop('issued_at',None);expected.pop('issued_at',None)
                    self.assertEqual(actual,expected)
            with closing(sqlite3.connect(copies[0])) as saved:
                self.assertEqual(saved.execute('PRAGMA user_version').fetchone()[0],13)
                self.assertEqual(payments,saved.execute('SELECT * FROM payments ORDER BY id').fetchall())

    def test_failed_backup_ddl_or_verification_leaves_schema13_intact(self):
        for stage in ('backup','column_created','before_commit'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as temp:
                p=self.fixture(temp)
                with closing(connect(p)) as db:before=list(db.iterdump())
                def fail(at):
                    if at==stage:raise OSError('Fallo ficticio de migración')
                target='colegio.storage.consistent_backup' if stage=='backup' else 'colegio.cashea_invoice_schema.checkpoint'
                with patch(target,side_effect=OSError('Disco FICTICIO lleno') if stage=='backup' else fail):
                    with self.assertRaises(OSError):initialize(p)
                with closing(connect(p)) as db:self.assertEqual(list(db.iterdump()),before)

    def test_live_secondary_backup_encrypted_and_missing_keys_fail_before_ddl(self):
        from tests.crypto_helpers import configure,PASSWORD
        from colegio.backup_crypto import CryptoError,MAGIC
        for configured in (False,True):
            with self.subTest(configured=configured),tempfile.TemporaryDirectory() as temp,tempfile.TemporaryDirectory() as second:
                p=self.fixture(temp)
                if configured:configure(p.parent)
                with closing(connect(p)) as db,db:db.execute("UPDATE settings SET value=? WHERE key='backup_directory'",(second,))
                if not configured:
                    with self.assertRaises(CryptoError):initialize(p)
                    with closing(connect(p)) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],13)
                    self.assertEqual(list(Path(second).iterdir()),[])
                else:
                    initialize(p);self.verify(p)
                    copies=list(Path(second).glob('*.aulabak'));self.assertEqual(len(copies),1)
                    self.assertTrue(copies[0].read_bytes().startswith(MAGIC));self.assertEqual(probe_backup(copies[0],PASSWORD)['schema'],13)

    def test_readonly_restore_and_conversion_upgrade_private_copies_without_touching_source_or_old_destination(self):
        from colegio.read_only import open_copy
        from colegio.backup_export import write_encrypted
        from tests.crypto_helpers import configure,PASSWORD
        from tests.restore_helpers import approved_restore
        with tempfile.TemporaryDirectory() as temp,tempfile.TemporaryDirectory() as second:
            p=self.fixture(temp);configure(p.parent)
            with closing(connect(p)) as db,db:db.execute("UPDATE settings SET value=? WHERE key='backup_directory'",(second,))
            before=hashlib.sha256(p.read_bytes()).hexdigest()
            with open_copy(p) as viewer:
                with closing(viewer.connect_view()) as db:
                    self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],14)
                    self.assertEqual(db.execute('SELECT invoice_origin FROM cashea_orders LIMIT 1').fetchone()[0],'manual')
            cipher=p.parent/'nueva.aulabak';write_encrypted(p,cipher,p.parent);self.assertEqual(probe_backup(cipher,PASSWORD)['schema'],14)
            restored=approved_restore(p,p.parent/'restaurada');self.verify(restored)
            self.assertEqual(list(Path(second).iterdir()),[]);self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),before)

    def test_real_process_termination_at_five_boundaries_is_atomic_and_restartable(self):
        child='''
import sys,time
from pathlib import Path
from colegio import cashea_invoice_schema
from colegio.db import initialize
def pause(stage):
 if stage==sys.argv[2]:
  Path(sys.argv[3]).write_text(stage)
  while True:time.sleep(.1)
cashea_invoice_schema.checkpoint=pause
initialize(sys.argv[1])
'''
        for stage in ('backup_verified','column_created','before_commit','after_commit','verified'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as temp:
                p=self.fixture(temp);marker=Path(temp)/'paused'
                proc=subprocess.Popen([sys.executable,'-c',child,str(p),stage,str(marker)])
                try:
                    deadline=time.monotonic()+25
                    while not marker.exists() and proc.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                    self.assertTrue(marker.exists(),(stage,proc.poll()))
                finally:
                    if proc.poll() is None:proc.kill()
                    proc.wait(timeout=10)
                with closing(sqlite3.connect(p)) as db:
                    version=db.execute('PRAGMA user_version').fetchone()[0];self.assertIn(version,(13,14))
                    self.assertEqual('invoice_origin' in [r[1] for r in db.execute('PRAGMA table_info(cashea_orders)')],version==14)
                    self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())
                initialize(p);self.verify(p)


if __name__=='__main__':unittest.main()
