"""Published source fixture, exact money and actual process termination for schema 13."""
from contextlib import closing
from pathlib import Path
import hashlib,json,shutil,sqlite3,subprocess,sys,tempfile,time,unittest
from colegio.db import connect,initialize
from colegio.audit_chain import adopt_restored,portable_status,local_status
from colegio.branding import SCHEMA_VERSION
from colegio.income_schema import TABLES
from colegio.backup_inspection import probe_backup,staged_backup

ROOT=Path(__file__).parent/'fixtures/income'


class IncomeSchemaTests(unittest.TestCase):
    def fixture(self,directory):
        meta=json.loads((ROOT/'manifest.json').read_text());source=ROOT/meta['filename']
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),meta['sha256']);self.assertTrue(meta['fictional'])
        self.assertEqual(meta['commit'],'cfbad62338849cd2089de6fd58c1c43ee115f772')
        path=Path(directory)/'colegio.sqlite3';shutil.copyfile(source,path);adopt_restored(path);return path

    def test_published_schema_12_money_history_cipher_reversal_and_repeat(self):
        from tests.crypto_helpers import configure,PASSWORD
        from colegio.administration import cash_summary
        with tempfile.TemporaryDirectory() as d:
            path=self.fixture(d);recovery=configure(d)
            preserved=('payments','allocations','charges','expenses','students','guardians','settings')
            with closing(connect(path)) as db:
                before={t:[tuple(r) for r in db.execute('SELECT * FROM '+t)] for t in preserved}
                history=[tuple(r) for r in db.execute('SELECT * FROM audit')];links=[tuple(r) for r in db.execute('SELECT * FROM audit_links')]
                reference=cash_summary(db,'2025-09-20')
            initialize(path);initialize(path)
            with closing(connect(path)) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)
                self.assertEqual(before,{t:[tuple(r) for r in db.execute('SELECT * FROM '+t)] for t in preserved})
                self.assertEqual(cash_summary(db,'2025-09-20'),reference)
                self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM audit')][:len(history)],history)
                self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM audit_links')][:len(links)],links)
                self.assertTrue(local_status(db)['ok']);self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())
                for table in TABLES:self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
            folder=Path(d)/'.aula-migrations/schema-13'
            ciphers=list(folder.glob('*.aulabak'));self.assertEqual(len(ciphers),1);self.assertFalse(list(folder.glob('*.sqlite3')))
            for credential,kind in ((PASSWORD,'password'),(recovery,'recovery')):
                with staged_backup(ciphers[0],credential,kind) as (previous,inspection,_):
                    self.assertEqual(inspection['summary']['schema'],12)
                    with closing(sqlite3.connect(previous)) as db:
                        self.assertEqual(before['payments'],[tuple(r) for r in db.execute('SELECT * FROM payments')])
                        self.assertTrue(portable_status(db)['ok'])
            self.assertEqual(probe_backup(path)['schema'],SCHEMA_VERSION)

    def test_real_kill_before_and_after_commit_complete_or_intact(self):
        for stage in ('backup_verified','table_3','before_commit','audit_after_commit','after_commit'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as d:
                path=self.fixture(d);marker=Path(d)/'kill-point'
                code='''import sys,time
from pathlib import Path
from colegio import income_schema,audit_chain
from colegio.db import initialize
stage=sys.argv[2]
def stop(name):
 if name==stage:
  Path(sys.argv[3]).write_text(name)
  while True:time.sleep(1)
income_schema.checkpoint=stop
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
                    version=db.execute('PRAGMA user_version').fetchone()[0];self.assertIn(version,(12,13))
                    self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())
                    names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    self.assertEqual(set(TABLES)&names,set(TABLES) if version==13 else set())
                initialize(path)
                with closing(connect(path)) as db:self.assertTrue(local_status(db)['ok'])
