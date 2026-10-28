"""Published 1.0.73 fixture, rollback copies, money references and real process kills."""
from contextlib import closing
from datetime import date
import hashlib,json,shutil,sqlite3,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch

from colegio.db import connect,initialize
from colegio.audit_chain import adopt_restored,portable_status,local_status
from colegio.storage import consistent_backup
from colegio.backup_inspection import inspect_copy,probe_backup
from colegio.administration import cash_summary
from colegio.server import snapshot
from colegio.monthly_report import report
from colegio.directory_reports import daily_report

FIXTURES=Path(__file__).parent/'fixtures/cashea'


class CasheaMigrationTests(unittest.TestCase):
    def fixture(self,directory):
        meta=json.loads((FIXTURES/'manifest.json').read_text())
        source=FIXTURES/meta['filename']
        self.assertTrue(meta['fictional']);self.assertEqual(meta['schema'],12)
        self.assertEqual(meta['commit'],'324d388')
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),meta['sha256'])
        path=Path(directory)/'colegio.sqlite3';shutil.copyfile(source,path);adopt_restored(path)
        return path

    def verify(self,path):
        with closing(connect(path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],14)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())
            self.assertTrue(portable_status(db)['ok']);self.assertTrue(local_status(db)['ok'])
            from colegio.maintenance import review_database
            self.assertTrue(review_database(db)['ok'])

    def test_published_12_migration_preserves_totals_snapshots_and_chain_with_verified_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            path=self.fixture(directory)
            with closing(connect(path)) as db:
                receipts=[tuple(r) for r in db.execute('SELECT * FROM payments ORDER BY id')]
                audit=[tuple(r) for r in db.execute('SELECT * FROM audit ORDER BY id')]
                links=[tuple(r) for r in db.execute('SELECT * FROM audit_links ORDER BY audit_id')]
            initialize(path);initialize(path);self.verify(path)
            backups=list((path.parent/'backups').glob('antes-cashea-*.sqlite3'));self.assertEqual(len(backups),1)
            self.assertEqual(probe_backup(backups[0])['schema'],12)
            metadata=json.loads(backups[0].with_suffix('.migration.json').read_text())
            self.assertEqual(hashlib.sha256(backups[0].read_bytes()).hexdigest(),metadata['sha256'])
            golden=json.loads((FIXTURES/'referencia-1.0.73.json').read_text())
            with closing(connect(path)) as db:
                self.assertEqual(receipts,[tuple(r) for r in db.execute('SELECT * FROM payments ORDER BY id')])
                self.assertEqual(audit,[tuple(r) for r in db.execute('SELECT * FROM audit ORDER BY id')][:len(audit)])
                self.assertEqual(links,[tuple(r) for r in db.execute('SELECT * FROM audit_links ORDER BY audit_id')][:len(links)])
                self.assertEqual(cash_summary(db,'2026-10-27'),golden['cash'])
                with patch('colegio.server.local_today',return_value=date(2026,10,27)):
                    state=snapshot(db,dict(id=1,role='admin',name='Auditor FICTICIO'))
                self.assertEqual(state['summary'],golden['summary'])
                daily=daily_report(state);self.assertEqual({k:daily[k] for k in golden['daily']},golden['daily'])
                monthly=report(db,state,'2026-10');self.assertEqual({k:monthly[k] for k in golden['monthly']},golden['monthly'])
                self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE action='cashea-schema'").fetchone()[0],1)
            # Reversibility: the unchanged prior snapshot is still a complete schema-12 database.
            with closing(sqlite3.connect(backups[0])) as db:
                self.assertEqual(receipts,db.execute('SELECT * FROM payments ORDER BY id').fetchall())
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],12)

    def test_verified_secondary_migration_backup_is_encrypted_and_keeps_schema12_without_recursion(self):
        from tests.crypto_helpers import configure,PASSWORD
        from colegio.backup_crypto import MAGIC
        with tempfile.TemporaryDirectory() as directory,tempfile.TemporaryDirectory() as second:
            path=self.fixture(directory);configure(path.parent)
            with closing(connect(path)) as db,db:db.execute("UPDATE settings SET value=? WHERE key='backup_directory'",(second,))
            initialize(path);self.verify(path)
            copies=list(Path(second).glob('antes-cashea-*.aulabak'));self.assertEqual(len(copies),1)
            self.assertTrue(copies[0].read_bytes().startswith(MAGIC))
            self.assertEqual(probe_backup(copies[0],PASSWORD)['schema'],12)

    def test_backup_or_ddl_failure_leaves_original_complete(self):
        for target in ('colegio.storage.consistent_backup','colegio.cashea_schema.checkpoint'):
            with self.subTest(target=target),tempfile.TemporaryDirectory() as directory:
                path=self.fixture(directory)
                with closing(connect(path)) as db:before=list(db.iterdump())
                def fail(stage):
                    if stage=='tables_created':raise OSError('Fallo FICTICIO después del DDL')
                with patch(target,side_effect=OSError('Disco FICTICIO lleno') if target.endswith('consistent_backup') else fail):
                    with self.assertRaises(OSError):initialize(path)
                with closing(connect(path)) as db:
                    self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],12)
                    self.assertEqual(list(db.iterdump()),before)

    def test_actual_process_termination_before_and_after_commit_is_atomic(self):
        child='''
import sys,time
from pathlib import Path
from colegio import cashea_schema
from colegio.db import initialize
def pause(stage):
    if stage==sys.argv[2]:
        Path(sys.argv[3]).write_text(stage)
        while True:time.sleep(.1)
cashea_schema.checkpoint=pause
initialize(sys.argv[1])
'''
        for stage in ('backup_verified','tables_created','before_commit','after_commit','verified'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as directory:
                path=self.fixture(directory);marker=Path(directory)/'paused'
                proc=subprocess.Popen([sys.executable,'-c',child,str(path),stage,str(marker)])
                try:
                    deadline=time.monotonic()+25
                    while not marker.exists() and proc.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                    self.assertTrue(marker.exists(),(stage,proc.poll()))
                finally:
                    if proc.poll() is None:proc.kill()
                    proc.wait(timeout=10)
                with closing(sqlite3.connect(path)) as db:
                    version=db.execute('PRAGMA user_version').fetchone()[0]
                    self.assertIn(version,(12,13));self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                    self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE 'cashea_%'").fetchone()[0],5 if version==13 else 0)
                initialize(path);self.verify(path)

    def test_normal_backup_conversion_migrates_12_without_changing_source(self):
        from tests.crypto_helpers import configure,PASSWORD
        from colegio.backup_export import write_encrypted
        with tempfile.TemporaryDirectory() as directory:
            path=self.fixture(directory);configure(path.parent)
            before=hashlib.sha256(path.read_bytes()).hexdigest();cipher=path.parent/'salida.aulabak'
            write_encrypted(path,cipher,path.parent)
            self.assertEqual(probe_backup(cipher,PASSWORD)['schema'],14)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)

    def test_old_copy_with_configured_second_destination_converts_and_opens_without_writing_there(self):
        from tests.crypto_helpers import configure,PASSWORD
        from colegio.backup_export import write_encrypted
        from colegio.read_only import open_copy
        with tempfile.TemporaryDirectory() as directory,tempfile.TemporaryDirectory() as second:
            path=self.fixture(directory);configure(path.parent)
            with closing(connect(path)) as db,db:db.execute("UPDATE settings SET value=? WHERE key='backup_directory'",(second,))
            before=hashlib.sha256(path.read_bytes()).hexdigest()
            cipher=path.parent/'portatil.aulabak'
            write_encrypted(path,cipher,path.parent)
            self.assertEqual(probe_backup(cipher,PASSWORD)['schema'],14)
            origin_files={p.relative_to(path.parent) for p in path.parent.rglob('*')}
            with open_copy(path) as viewer:
                with closing(viewer.connect_view()) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],14)
            self.assertEqual(origin_files,{p.relative_to(path.parent) for p in path.parent.rglob('*')})
            from tests.restore_helpers import approved_restore
            restored=approved_restore(path,path.parent/'restaurada')
            self.assertEqual(probe_backup(restored)['schema'],14)
            self.assertEqual(list(Path(second).iterdir()),[],'La conversión y consulta privadas no publican en el destino de la escuela de origen.')
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)

    def test_live_migration_still_fails_before_ddl_if_configured_secondary_cannot_encrypt(self):
        from colegio.backup_crypto import CryptoError
        with tempfile.TemporaryDirectory() as directory,tempfile.TemporaryDirectory() as second:
            path=self.fixture(directory)
            with closing(connect(path)) as db,db:db.execute("UPDATE settings SET value=? WHERE key='backup_directory'",(second,))
            with closing(connect(path)) as db:before=list(db.iterdump())
            with self.assertRaises(CryptoError):initialize(path)
            with closing(connect(path)) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],12)
                self.assertEqual(list(db.iterdump()),before)
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(list(Path(second).iterdir()),[])


if __name__=='__main__':unittest.main()
