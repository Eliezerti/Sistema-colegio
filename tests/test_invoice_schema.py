"""Published-source data -> schema 16, verified reversal and real process kills."""
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from colegio.db import connect,initialize
from colegio.invoice_schema import TABLES,migrate
from colegio.audit_chain import local_status


class InvoiceSchemaTests(unittest.TestCase):
    def old(self,directory):
        from tests.test_month_schema import MonthSchemaTests
        from colegio.month_schema import migrate as month_migrate
        path=MonthSchemaTests().old(directory);month_migrate(path);return path

    def test_cipher_reversal_preserves_all_old_rows_totals_and_chain(self):
        from tests.crypto_helpers import configure,PASSWORD
        from colegio.backup_inspection import inspect_copy,staged_backup,probe_backup
        from colegio.administration import cash_summary
        with tempfile.TemporaryDirectory() as d:
            path=self.old(d);recovery=configure(d);old=inspect_copy(path)['records']
            with closing(connect(path)) as db:before=cash_summary(db,'2025-09-20')
            initialize(path);initialize(path)
            with closing(connect(path)) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],16)
                self.assertEqual(cash_summary(db,'2025-09-20'),before)
                self.assertTrue(local_status(db)['ok'])
                for table in TABLES:self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
            after=inspect_copy(path)['records']
            for table,rows in old.items():
                if table not in ('audit','audit_links','audit_meta'):self.assertEqual(after[table],rows,table)
            self.assertEqual(after['audit_meta'][0]['chain_id'],old['audit_meta'][0]['chain_id'])
            self.assertEqual(after['audit_meta'][0]['baseline'],old['audit_meta'][0]['baseline'])
            self.assertEqual(after['audit_meta'][0]['head_id'],old['audit_meta'][0]['head_id']+1)
            for table in ('audit','audit_links'):
                self.assertTrue(all(row in after[table] for row in old[table]),table)
            folder=Path(d)/'.aula-migrations/schema-16';self.assertFalse(list(folder.glob('*.sqlite3')))
            copies=list(folder.glob('*.aulabak'));self.assertEqual(len(copies),1)
            for credential,kind in ((PASSWORD,'password'),(recovery,'recovery')):
                with staged_backup(copies[0],credential,kind) as (_,inspection,_):
                    self.assertEqual(inspection['summary']['schema'],15)
                    self.assertEqual(inspection['records'],old)
            self.assertEqual(probe_backup(path)['schema'],16)

    def test_unavailable_cipher_stops_before_copy_and_missing_immutability_is_rejected(self):
        from tests.crypto_helpers import configure
        from colegio.backup_keys import folder,NAME
        from colegio.invoice_schema import verify_layout
        with tempfile.TemporaryDirectory() as d:
            path=self.old(d);configure(d);(folder(d)/NAME).write_text('{}',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Desbloquea el cifrado'):migrate(path)
            self.assertFalse((Path(d)/'.aula-migrations/schema-16').exists())
            with closing(connect(path)) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],15)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'colegio.sqlite3';initialize(path)
            with closing(connect(path)) as db,db:
                db.execute('DROP TRIGGER invoice_frozen')
                with self.assertRaisesRegex(ValueError,'protección'):verify_layout(db)

    def test_real_kill_is_wholly_15_or_16_and_chain_recovers(self):
        for stage in ('backup_verified','object_5','before_commit','audit_after_commit','after_commit'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as d:
                path=self.old(d);marker=Path(d)/'kill'
                code='''import sys,time
from pathlib import Path
from colegio import invoice_schema,audit_chain
from colegio.db import initialize
def stop(name):
 if name==sys.argv[2]:
  Path(sys.argv[3]).write_text(name)
  while True:time.sleep(1)
invoice_schema.checkpoint=stop
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
                    version=db.execute('PRAGMA user_version').fetchone()[0];self.assertIn(version,(15,16))
                    self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                    self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())
                    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    self.assertEqual(set(TABLES)&tables,set(TABLES) if version==16 else set())
                initialize(path)
                with closing(connect(path)) as db:self.assertTrue(local_status(db)['ok'])
