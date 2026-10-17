"""Schema 14 starts from the published 1.0.71 fixture; real process kills."""
from contextlib import closing
from pathlib import Path
import json,sqlite3,subprocess,sys,tempfile,time,unittest
from colegio.db import initialize,connect
from colegio.branding import SCHEMA_VERSION
from colegio.income_schema import migrate as income_migrate
from colegio.bank_schema import TABLES
from colegio.audit_chain import local_status

class BankSchemaTests(unittest.TestCase):
    def old(self,d):
        from tests.test_income_schema import IncomeSchemaTests
        path=IncomeSchemaTests().fixture(d);income_migrate(path);return path
    def test_verified_cipher_snapshot_13_and_preserved_money_chain(self):
        from tests.crypto_helpers import configure,PASSWORD
        from colegio.backup_inspection import staged_backup,probe_backup
        from colegio.administration import cash_summary
        with tempfile.TemporaryDirectory() as d:
            path=self.old(d);recovery=configure(d)
            with closing(connect(path)) as db:
                before=cash_summary(db,'2025-09-20');history=[tuple(r) for r in db.execute('SELECT * FROM audit')]
                payments=[tuple(r) for r in db.execute('SELECT * FROM payments')]
            initialize(path)
            with closing(connect(path)) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION);self.assertTrue(local_status(db)['ok'])
                self.assertEqual(cash_summary(db,'2025-09-20'),before)
                self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM payments')],payments)
                self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM audit')][:len(history)],history)
                for table in TABLES:self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
            folder=Path(d)/'.aula-migrations/schema-14';self.assertFalse(list(folder.glob('*.sqlite3')))
            saved=list(folder.glob('*.aulabak'));self.assertEqual(len(saved),1)
            for key,kind in ((PASSWORD,'password'),(recovery,'recovery')):
                with staged_backup(saved[0],key,kind) as (copy,inspection,_):self.assertEqual(inspection['summary']['schema'],13)
            self.assertEqual(probe_backup(path)['schema'],SCHEMA_VERSION)
    def test_actual_kill_transaction_head_recovery_and_integrity(self):
        for stage in ('backup_verified','object_3','before_commit','audit_after_commit','after_commit'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as d:
                path=self.old(d);marker=Path(d)/'kill'
                code='''import sys,time
from pathlib import Path
from colegio import bank_schema,audit_chain
from colegio.db import initialize
def stop(name):
 if name==sys.argv[2]:
  Path(sys.argv[3]).write_text(name)
  while True:time.sleep(1)
bank_schema.checkpoint=stop
audit_chain.checkpoint=lambda name:stop('audit_'+name)
initialize(sys.argv[1])
'''
                proc=subprocess.Popen([sys.executable,'-c',code,str(path),stage,str(marker)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                try:
                    deadline=time.monotonic()+20
                    while not marker.exists() and proc.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                    self.assertTrue(marker.exists(),(stage,proc.poll()))
                finally:
                    if proc.poll() is None:proc.kill()
                    proc.wait(timeout=10)
                with closing(sqlite3.connect(path)) as db:
                    version=db.execute('PRAGMA user_version').fetchone()[0];self.assertIn(version,(13,14))
                    self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())
                    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    self.assertEqual(set(TABLES)&tables,set(TABLES) if version==14 else set())
                initialize(path)
                with closing(connect(path)) as db:self.assertTrue(local_status(db)['ok'])
