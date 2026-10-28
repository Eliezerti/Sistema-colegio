"""Retirement contract: actual published schema, exact money, crashes and permissions."""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from colegio.db import initialize,connect,next_record_id
from colegio.schema import COLUMNS,RETIRED
from colegio.audit_chain import adopt_restored,portable_status,local_status
from colegio.administration import cash_summary
from colegio.backup_inspection import probe_backup
from colegio.storage import consistent_backup
from colegio.maintenance import review_database

FIXTURES=Path(__file__).parent/'fixtures/retirement'


class RetirementTests(unittest.TestCase):
    def fixture(self,directory):
        source=FIXTURES/'desktop-1.0.53.sqlite3'
        meta=json.loads((FIXTURES/'manifest.json').read_text())
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),meta['sha256'])
        self.assertTrue(meta['fictional']);self.assertEqual(meta['schema'],11)
        path=Path(directory)/'colegio.sqlite3';shutil.copyfile(source,path);adopt_restored(path)
        return path

    def assert_retired(self,path):
        with closing(connect(path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],14)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertFalse(tables.intersection(RETIRED))
            self.assertEqual(tuple(r[1] for r in db.execute('PRAGMA table_info(expenses)')),COLUMNS)
            self.assertTrue(portable_status(db)['ok']);self.assertTrue(local_status(db)['ok'])
            self.assertFalse(db.execute("SELECT 1 FROM settings WHERE key='id_floor_employees'").fetchone())
            self.assertEqual(next_record_id(db,'expenses'),20)
            self.assertTrue(review_database(db)['ok'])
        raw=path.read_bytes()
        for private in (b'01029999888877776666',b'BANCO-RETIRADO-TEST',b'TITULAR-RETIRADO-TEST'):
            self.assertNotIn(private,raw)
        self.assertFalse((path.parent/'.aula-schema-12').exists())

    def test_published_v11_migration_preserves_cash_expense_rows_chain_and_backups(self):
        with tempfile.TemporaryDirectory() as directory:
            path=self.fixture(directory)
            with closing(connect(path)) as db:
                before=[tuple(r) for r in db.execute('SELECT '+','.join(COLUMNS)+' FROM expenses ORDER BY id')]
                audit=[tuple(r) for r in db.execute('SELECT * FROM audit ORDER BY id')]
                links=[tuple(r) for r in db.execute('SELECT * FROM audit_links ORDER BY audit_id')]
            initialize(path);initialize(path)
            self.assert_retired(path)
            with closing(connect(path)) as db:
                self.assertEqual([tuple(r) for r in db.execute('SELECT '+','.join(COLUMNS)+' FROM expenses ORDER BY id')],before)
                self.assertEqual(cash_summary(db,'2025-09-20'),json.loads((FIXTURES/'cash-reference.json').read_text()))
                from datetime import date
                from colegio.server import snapshot
                with patch('colegio.server.local_today',return_value=date(2025,9,20)):
                    self.assertEqual(snapshot(db,{'id':1,'name':'Administrador ficticio','role':'admin'})['summary'],json.loads((FIXTURES/'report-reference.json').read_text()))
                self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM audit ORDER BY id')][:len(audit)],audit)
                self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM audit_links ORDER BY audit_id')][:len(links)],links)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE action='retire-staff-module'").fetchone()[0],1)
            copy=Path(directory)/'new-backup.sqlite3';consistent_backup(path,copy)
            self.assertEqual(probe_backup(copy)['schema'],14)
            for private in (b'01029999888877776666',b'BANCO-RETIRADO-TEST'):
                self.assertNotIn(private,copy.read_bytes())
            from tests.crypto_helpers import configure
            from colegio.backup_export import write_encrypted
            configure(path.parent);cipher=Path(directory)/'new.aulabak';write_encrypted(copy,cipher,path.parent)
            self.assertEqual(probe_backup(cipher,'FICTICIO-respaldo-seguro-2026')['schema'],14)
            from tests.restore_helpers import approved_restore
            restored=approved_restore(cipher,Path(directory)/'restored',credential='FICTICIO-respaldo-seguro-2026')
            self.assert_retired(restored)

    def test_converting_old_backup_removes_banking_without_changing_source(self):
        from tests.crypto_helpers import configure
        from colegio.backup_export import write_encrypted
        from colegio.backup_crypto import decrypt
        source=FIXTURES/'desktop-1.0.53.sqlite3';before=hashlib.sha256(source.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            configure(Path(directory));target=Path(directory)/'converted.aulabak'
            write_encrypted(source,target,Path(directory))
            raw,_=decrypt(target.read_bytes(),'FICTICIO-respaldo-seguro-2026','password')
            self.assertNotIn(b'01029999888877776666',raw)
            self.assertNotIn(b'BANCO-RETIRADO-TEST',raw)
            self.assertEqual(probe_backup(target,'FICTICIO-respaldo-seguro-2026')['schema'],14)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)

    def test_backup_failure_blocks_all_ddl_and_preserves_previous_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path=self.fixture(directory)
            with closing(sqlite3.connect(path)) as db:before=list(db.iterdump())
            with patch('colegio.storage.consistent_backup',side_effect=OSError('Disco de prueba lleno')):
                with self.assertRaises(OSError):initialize(path)
            with closing(sqlite3.connect(path)) as db:self.assertEqual(list(db.iterdump()),before)
            with closing(sqlite3.connect(path)) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],11)

    def test_actual_process_kills_leave_old_or_complete_database_and_restart_finishes(self):
        child='''
import sys,time
from pathlib import Path
import colegio.schema as schema
from colegio.db import initialize
stage,marker=sys.argv[2:]
def stop(at):
 if at==stage:
  Path(marker).write_text(at)
  while True:time.sleep(.05)
schema.checkpoint=stop
initialize(sys.argv[1])
'''
        for stage in ('backup_verified','expenses_copied','before_commit','after_commit','compacted'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as directory:
                path=self.fixture(directory);marker=Path(directory)/'paused'
                proc=subprocess.Popen([sys.executable,'-c',child,str(path),stage,str(marker)])
                try:
                    deadline=time.monotonic()+20
                    while not marker.exists() and proc.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                    self.assertTrue(marker.exists(),(stage,proc.poll()))
                finally:
                    if proc.poll() is None:proc.kill()
                    proc.wait(timeout=10)
                with closing(sqlite3.connect(path)) as db:
                    self.assertIn(db.execute('PRAGMA user_version').fetchone()[0],(11,12))
                    self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                    self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchone())
                initialize(path);self.assert_retired(path)


class RetiredRouteTests(unittest.TestCase):
    def test_retired_routes_are_clear_for_every_profile_without_state_change(self):
        from tests.test_system import SystemTests
        f=SystemTests();f.setUp()
        try:
            for role in ('cashier','reader'):f.request('users',dict(username=role,name=role,role=role,password='Clave-ficticia-2026'))
            for role in ('admin','cashier','reader'):
                if role!='admin':
                    f.request('logout',{});f.request('login',dict(username=role,password='Clave-ficticia-2026'));f.csrf=f.request('session')['user']['csrf']
                    from colegio.db import local_today
                    f.request('confirm-rate',dict(rate_date=local_today().isoformat(),rate='100'))
                before=f.request('state')
                for route in ('employees','positions','payroll-plans','salary-receipts','archive-employee','restore-employee','reset-records'):
                    result=f.request(route,{},status=410);self.assertIn('retirada',result['error'])
                for route in ('directory/employees','directory/employees.pdf','payroll-plan/1','payroll-plan/1.pdf','salary-receipt/1','salary-receipt/1.pdf','archive-preview/employee/1','reset-preview'):
                    f.request(route,status=410)
                after=f.request('state')
                for key in ('expenses','payments','students','charges'):self.assertEqual(after[key],before[key])
                for key in ('employees','positions','payroll_plans'):self.assertNotIn(key,after)
        finally:f.tearDown()
