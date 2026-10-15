"""Audit integrity, reversible migration and real crash recovery on fictitious data."""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from colegio.db import connect, initialize, audit, hash_password, generate_month
from colegio.audit_chain import (AuditUnavailable, controls, local_status, portable_status,
                                 migrate, append, load, adopt_restored, trigger_definitions, atomic)
from colegio.maintenance import review_database
from colegio.storage import consistent_backup
from colegio.restore import last_restore
from tests.restore_helpers import approved_restore
from tests.audit_helpers import legacy_fixture


class AuditChainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'colegio.sqlite3'
        initialize(self.path)
        with closing(connect(self.path)) as db, db:
            db.execute("INSERT INTO users(id,username,name,password,role) VALUES(1,'admin','Administración',?,'admin')", (hash_password('Una-clave-segura'),))
            db.audit_user = 1
            audit(db, 1, 'inicio', {'prueba': True})

    def tearDown(self):
        self.temp.cleanup()

    def raw_tamper(self, sql):
        with closing(sqlite3.connect(self.path)) as db, db:
            for name, in db.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'audit_guard_%'").fetchall():
                db.execute('DROP TRIGGER "'+name+'"')
            db.execute(sql)

    def test_official_append_and_previous_new_edit_are_in_same_transaction(self):
        with closing(connect(self.path)) as db, db:
            db.audit_user = 1
            db.execute("UPDATE users SET name='Ana' WHERE id=1")
        with closing(connect(self.path)) as db:
            event = db.execute("SELECT user_id,details FROM audit WHERE action='edit-values'").fetchone()
            self.assertEqual(event[0], 1)
            changes = json.loads(event[1])['cambios']['name']
            self.assertEqual(changes, {'anterior': 'Administración', 'nuevo': 'Ana'})
            self.assertTrue(local_status(db)['ok'])

    def test_raw_insert_update_delete_and_link_updates_are_denied(self):
        for sql in ("INSERT INTO audit(action,details,created_at) VALUES('falso','{}','hoy')",
                    "UPDATE audit SET details='{}'", 'DELETE FROM audit',
                    "UPDATE audit_links SET row_hash='0'", 'DELETE FROM audit_meta'):
            with self.subTest(sql=sql), closing(connect(self.path)) as db:
                with self.assertRaises(sqlite3.Error): db.execute(sql)
                db.rollback()
        with closing(sqlite3.connect(self.path)) as db:
            with self.assertRaises(sqlite3.Error): db.execute("INSERT INTO audit(action,details,created_at) VALUES('falso','{}','hoy')")

    def test_removed_guard_is_detected_even_without_changing_audit_rows(self):
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute('DROP TRIGGER audit_guard_audit_insert')
        with closing(connect(self.path)) as db:
            self.assertFalse(local_status(db)['ok'])

    def test_rollback_does_not_leak_edits_or_advance_head(self):
        head = controls(self.path)[0].read_bytes()
        with closing(connect(self.path)) as db:
            db.execute("UPDATE users SET name='No guardar' WHERE id=1")
            audit(db, 1, 'rollback', {})
            db.rollback()
            with db: audit(db, 1, 'después', {})
        with closing(connect(self.path)) as db:
            self.assertFalse(db.execute("SELECT 1 FROM audit WHERE action IN ('rollback','edit-values')").fetchone())
            self.assertTrue(local_status(db)['ok'])
        self.assertNotEqual(head, controls(self.path)[0].read_bytes())

    def test_control_changed_during_edit_aborts_instead_of_overwriting_evidence(self):
        with closing(connect(self.path)) as db:
            db.execute("UPDATE users SET name='No debe guardarse' WHERE id=1")
            head,_=controls(self.path)
            changed=dict(load(head),hash='f'*64)
            atomic(head,changed)
            with self.assertRaises(AuditUnavailable):db.commit()
            self.assertEqual(db.execute('SELECT name FROM users').fetchone()[0],'Administración')
            self.assertEqual(load(head),changed)

    def test_concurrent_writer_and_reader_wait_for_head_publication(self):
        entered, resume = threading.Event(), threading.Event()
        second_started, second_finished = threading.Event(), threading.Event()
        reader_started, reader_finished = threading.Event(), threading.Event()
        first_id = []
        def pause(stage):
            if stage == 'after_commit' and threading.get_ident() == first_id[0]:
                entered.set()
                if not resume.wait(5): raise RuntimeError('La prueba no liberó la publicación')
        def first():
            first_id.append(threading.get_ident())
            with closing(connect(self.path)) as db, db: audit(db,1,'primera',{})
        def second():
            second_started.set()
            try:
                with closing(connect(self.path)) as db, db:
                    db.execute('BEGIN IMMEDIATE')
                    audit(db,1,'segunda',{})
            finally: second_finished.set()
        def reader():
            reader_started.set()
            try:
                with closing(connect(self.path)) as db: return local_status(db)
            finally: reader_finished.set()
        with patch('colegio.audit_chain.checkpoint',side_effect=pause), ThreadPoolExecutor(max_workers=3) as pool:
            one=pool.submit(first)
            self.assertTrue(entered.wait(5))
            two=pool.submit(second); three=pool.submit(reader)
            try:
                self.assertTrue(second_started.wait(2));self.assertTrue(reader_started.wait(2))
                self.assertFalse(second_finished.wait(.2))
                self.assertFalse(reader_finished.wait(.2))
            finally: resume.set()
            one.result(timeout=5);two.result(timeout=5)
            self.assertTrue(three.result(timeout=5)['ok'])
        with closing(connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM audit').fetchone()[0],3)
            self.assertTrue(local_status(db)['ok'])

    def test_savepoint_rollback_and_outer_release_keep_only_committed_edits(self):
        with closing(connect(self.path)) as db:
            db.execute('SAVEPOINT lote')
            db.execute("UPDATE users SET name='Guardar' WHERE id=1")
            db.execute('SAVEPOINT fila')
            db.execute("UPDATE users SET name='Cancelar fila' WHERE id=1")
            audit(db,1,'fila-cancelada',{})
            db.execute('ROLLBACK TO fila');db.execute('RELEASE fila')
            db.execute('RELEASE lote')
            self.assertFalse(db.in_transaction)
            self.assertEqual(db.execute('SELECT name FROM users').fetchone()[0],'Guardar')
            detail=json.loads(db.execute("SELECT details FROM audit WHERE action='edit-values'").fetchone()[0])
            self.assertEqual(detail['cambios']['name'],{'anterior':'Administración','nuevo':'Guardar'})
            self.assertFalse(db.execute("SELECT 1 FROM audit WHERE action='fila-cancelada'").fetchone())
            before=controls(self.path)[0].read_bytes()
            db.execute('SAVEPOINT vista_previa')
            db.execute("UPDATE users SET name='Cancelar lote' WHERE id=1")
            audit(db,1,'lote-cancelado',{})
            db.execute('ROLLBACK TO vista_previa');db.execute('RELEASE vista_previa')
            self.assertEqual(db.execute('SELECT name FROM users').fetchone()[0],'Guardar')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM audit').fetchone()[0],2)
            self.assertEqual(controls(self.path)[0].read_bytes(),before)
            self.assertTrue(local_status(db)['ok'])

    def test_altered_row_and_removed_tail_are_detected(self):
        self.raw_tamper("UPDATE audit SET details='alterado' WHERE id=1")
        with closing(connect(self.path)) as db:
            self.assertFalse(local_status(db)['ok'])
            with self.assertRaises(AuditUnavailable): audit(db, 1, 'nuevo', {})
            with self.assertRaises(AuditUnavailable): generate_month(db, '2026-10', 1)
            self.assertFalse(review_database(db)['ok'])

    def test_coherent_tail_removal_is_detected_by_separate_head(self):
        self.raw_tamper('DELETE FROM audit_links')
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('DELETE FROM audit')
            db.execute("UPDATE audit_meta SET head_id=0,head_hash=?", ('0'*64,))
            for name,sql in trigger_definitions(db).items():
                if name.startswith('audit_guard_'):db.execute(sql)
        with closing(connect(self.path)) as db:
            self.assertTrue(portable_status(db)['ok'])
            self.assertFalse(local_status(db)['ok'])

    def test_missing_or_corrupt_head_is_not_silently_recreated(self):
        head, _ = controls(self.path)
        head.write_text('truncado')
        initialize(self.path)
        self.assertEqual(head.read_text(), 'truncado')
        with closing(connect(self.path)) as db: self.assertFalse(local_status(db)['ok'])
        head.unlink();initialize(self.path)
        self.assertFalse(head.exists())

    def test_unverifiable_audit_keeps_session_bookkeeping_and_consultation(self):
        self.raw_tamper("UPDATE audit SET details='alterado'")
        with closing(connect(self.path)) as db, db:
            db.execute("INSERT INTO sessions(token,user_id,csrf,expires) VALUES('fixture',1,'csrf',9999999999)")
            self.assertEqual(db.execute('SELECT name FROM users').fetchone()[0], 'Administración')
        with closing(connect(self.path)) as db:
            with self.assertRaises(sqlite3.Error): db.execute("UPDATE users SET name='Sin historial' WHERE id=1")
        copy = self.path.parent/'conservar.sqlite3'
        consistent_backup(self.path, copy)
        self.assertTrue(copy.exists(), 'A damaged audit must still be preservable')

    def test_password_tokens_and_banking_data_never_enter_new_details(self):
        with closing(connect(self.path)) as db, db:
            db.execute("UPDATE users SET password=? WHERE id=1", (hash_password('Otra-clave-segura'),))
            audit(db, 1, 'secreto', {'password': 'secreto', 'recovery_key': 'clave', 'token': 'TOKEN', 'bank_account':'0123456789', 'dato':'visible'})
        with closing(connect(self.path)) as db:
            text = '\n'.join(r[0] for r in db.execute('SELECT details FROM audit'))
            for secret in ('secreto', 'clave', 'TOKEN', '0123456789', '$'):
                self.assertNotIn(secret, text)
            self.assertIn('visible', text)

    def test_retired_reset_cannot_erase_original_audit(self):
        from tests.test_system import SystemTests
        f=SystemTests();f.setUp()
        try:
            with closing(connect(f.path)) as db:
                before=[tuple(r) for r in db.execute('SELECT * FROM audit ORDER BY id')]
                links=[tuple(r) for r in db.execute('SELECT * FROM audit_links ORDER BY audit_id')]
            f.request('reset-records', {'confirmation':'VACIAR REGISTROS','password':'Una-clave-segura'},status=410)
            f.request('reset-preview',status=410)
            with closing(connect(f.path)) as db:
                self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM audit ORDER BY id')],before)
                self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM audit_links ORDER BY audit_id')],links)
                self.assertTrue(local_status(db)['ok'])
        finally:f.tearDown()

    def test_restore_crosslinks_current_branch_and_preserves_original_snapshot(self):
        old = self.path.parent/'vieja.sqlite3';consistent_backup(self.path, old)
        with closing(connect(self.path)) as db, db: audit(db, 1, 'posterior', {'dato':'conservar'})
        with closing(connect(self.path)) as db: previous = local_status(db)['head']
        approved_restore(old, self.path.parent)
        event = last_restore(self.path.parent)
        self.assertEqual(event['previous_audit_head'], previous)
        with closing(sqlite3.connect(event['previous_backup'])) as db:
            self.assertTrue(db.execute("SELECT 1 FROM audit WHERE action='posterior'").fetchone())
            self.assertTrue(portable_status(db)['ok'])
        with closing(connect(self.path)) as db: self.assertTrue(local_status(db)['ok'])

    def legacy(self):
        with closing(connect(self.path)) as db, db: legacy_fixture(db)
        for file in controls(self.path): file.unlink(missing_ok=True)

    def original_rows(self):
        with closing(sqlite3.connect(self.path)) as db:
            tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            return {table: list(db.execute('SELECT * FROM "'+table+'" ORDER BY rowid')) for table in tables}

    def test_migration_preserves_every_original_row_and_backup_is_reversible(self):
        self.legacy();before = self.original_rows();migrate(self.path)
        with closing(connect(self.path)) as db:
            for table, rows in before.items(): self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM "'+table+'" ORDER BY rowid')], rows)
            self.assertEqual(local_status(db)['baseline'], 1)
        backup = next((self.path.parent/'backups').glob('antes-bitacora-*.sqlite3'))
        with closing(sqlite3.connect(backup)) as saved, closing(sqlite3.connect(self.path)) as db:
            saved.backup(db)
        self.assertEqual(self.original_rows(), before)
        with closing(sqlite3.connect(self.path)) as db: self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 10)

    def test_failed_ddl_rolls_back_and_keeps_verified_pre_migration_copy(self):
        self.legacy();before = self.original_rows()
        def fail(stage):
            if stage == 'migration_ddl': raise RuntimeError('corte de prueba')
        with patch('colegio.audit_chain.checkpoint', side_effect=fail):
            with self.assertRaises(RuntimeError): migrate(self.path)
        self.assertEqual(self.original_rows(), before)
        self.assertEqual(len(list((self.path.parent/'backups').glob('antes-bitacora-*.sqlite3'))), 1)
        migrate(self.path)
        with closing(connect(self.path)) as db: self.assertTrue(local_status(db)['ok'])

    def test_real_process_termination_resolves_both_commit_sides_and_head_publication(self):
        for stage in ('before_commit','after_commit','after_head'):
            with self.subTest(stage=stage):
                folder = self.path.parent/stage;folder.mkdir()
                target = folder/'colegio.sqlite3';consistent_backup(self.path, target);adopt_restored(target)
                script = '''import os,sys
from colegio.db import connect,audit
import colegio.audit_chain as chain
chain.checkpoint=lambda stage: os._exit(71) if stage==sys.argv[2] else None
with connect(sys.argv[1]) as db:audit(db,1,'interrumpido',{})
'''
                process = subprocess.run([sys.executable,'-c',script,str(target),stage], capture_output=True, timeout=10)
                self.assertEqual(process.returncode, 71, process.stderr.decode())
                initialize(target)
                with closing(connect(target)) as db:
                    self.assertTrue(local_status(db)['ok'])
                    count = db.execute("SELECT COUNT(*) FROM audit WHERE action='interrumpido'").fetchone()[0]
                    self.assertEqual(count, int(stage != 'before_commit'))

    def test_real_migration_process_termination_before_and_after_sql_commit(self):
        for stage in ('migration_backup','migration_ddl','migration_commit'):
            with self.subTest(stage=stage):
                folder = self.path.parent/stage;folder.mkdir();target=folder/'colegio.sqlite3'
                consistent_backup(self.path, target);adopt_restored(target)
                with closing(connect(target)) as db, db: legacy_fixture(db)
                for file in controls(target): file.unlink(missing_ok=True)
                script = '''import os,sys
import colegio.audit_chain as chain
chain.checkpoint=lambda stage: os._exit(72) if stage==sys.argv[2] else None
chain.migrate(sys.argv[1])
'''
                process = subprocess.run([sys.executable,'-c',script,str(target),stage], capture_output=True, timeout=10)
                self.assertEqual(process.returncode, 72, process.stderr.decode())
                initialize(target)
                with closing(connect(target)) as db:
                    self.assertTrue(local_status(db)['ok'])
                    self.assertEqual(db.execute('SELECT name FROM users').fetchone()[0], 'Administración')
                self.assertTrue(list((folder/'backups').glob('antes-bitacora-*.sqlite3')))
