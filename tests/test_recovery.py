"""Recovery must work when the current database is unreadable."""
import sqlite3
import builtins
import errno
import os
import http.client
import threading
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from colegio.db import connect, initialize, record_payment
from colegio.restore import restore
from colegio.storage import consistent_backup, automatic_backup


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        source=self.root/'original.sqlite3'
        initialize(source)
        with closing(connect(source)) as db, db:
            db.execute("INSERT INTO users(id,username,name,password,role) VALUES(1,'fixture','Administración de prueba','unused','admin')")
            db.execute("INSERT INTO guardians(id,name,document) VALUES(1,'Representante de prueba','V-123')")
            db.execute("INSERT INTO grades(id,name,capacity) VALUES(1,'Primaria',30)")
            db.execute('''INSERT INTO students(id,name,document,student_code,birth_date,guardian_id,grade_id,school_year,
                monthly_fee,discount,status,enrollment_start,enrollment_end)
                VALUES(1,'Alumno de prueba','AL-000001','AL-000001','2015-01-01',1,1,2025,10000,0,'active','2025-09-01','2026-08-31')''')
            db.execute("INSERT INTO charges(student_id,period,concept,amount,due_date) VALUES(1,'2025-09','Mensualidad',10000,'2025-09-10')")
            record_payment(db,{'student_id':1,'amount':'50','currency':'USD','paid_on':'2025-09-20',
                'method':'Transferencia','reference':'TR-REC-01','request_key':'recovery-fixture'},1)
            self.payment=dict(db.execute('SELECT * FROM payments').fetchone())
        self.backup=self.root/'respaldo.sqlite3'
        consistent_backup(source,self.backup)
        self.directory=self.root/'destino'
        self.directory.mkdir()
        self.target=self.directory/'colegio.sqlite3'

    def tearDown(self):
        self.temp.cleanup()

    def test_corrupt_current_database_restores_payment_and_preserves_original_files(self):
        original={'colegio.sqlite3':b'base-corrupta-de-prueba',
                  'colegio.sqlite3-wal':b'wal-original-de-prueba',
                  'colegio.sqlite3-shm':b'shm-original-de-prueba',
                  'colegio.sqlite3-journal':b'journal-original-de-prueba'}
        for name,data in original.items():(self.directory/name).write_bytes(data)
        self.assertEqual(restore(self.backup,self.directory),self.target)
        with closing(connect(self.target)) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(dict(db.execute('SELECT * FROM payments').fetchone()),self.payment)
            self.assertEqual(db.execute('SELECT amount FROM allocations').fetchone()[0],5000)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],0)
        damaged=list((self.directory/'backups').glob('danado-antes-restauracion-*'))
        self.assertEqual(len(damaged),1)
        for name,data in original.items():self.assertEqual((damaged[0]/name).read_bytes(),data)
        for suffix in ('-wal','-shm','-journal'):
            self.assertFalse(self.target.with_name(self.target.name+suffix).exists())
        self.assertFalse(list((self.directory/'backups').glob('antes-restauracion-*.sqlite3')))

    def test_deleted_database_preserves_remaining_files_before_restore(self):
        wal=self.target.with_name(self.target.name+'-wal')
        wal.write_bytes(b'archivo-wal-de-una-base-borrada')
        restore(self.backup,self.directory)
        with closing(connect(self.target)) as db:
            self.assertEqual(dict(db.execute('SELECT * FROM payments').fetchone()),self.payment)
        damaged=list((self.directory/'backups').glob('danado-antes-restauracion-*'))
        self.assertEqual((damaged[0]/wal.name).read_bytes(),b'archivo-wal-de-una-base-borrada')
        self.assertFalse(wal.exists())

    def test_startup_does_not_silently_create_empty_database_after_deletion(self):
        backups=self.directory/'backups';backups.mkdir()
        consistent_backup(self.backup,backups/'colegio-2025-10-01.sqlite3')
        root=Path(__file__).resolve().parent.parent
        result=subprocess.run([sys.executable,'-m','colegio.server','--data-dir',str(self.directory),'--port','0'],
                              cwd=root,capture_output=True,text=True,timeout=5)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('No se encuentra la base de datos',result.stderr)
        self.assertFalse(self.target.exists())

    def test_invalid_incoming_backup_does_not_replace_current_data(self):
        consistent_backup(self.backup,self.target)
        original=self.target.read_bytes()
        invalid=self.root/'invalido.sqlite3';invalid.write_bytes(b'no es una base')
        with self.assertRaises(sqlite3.DatabaseError):restore(invalid,self.directory)
        self.assertEqual(self.target.read_bytes(),original)

    def test_preservation_failure_stops_before_replacing_current_data(self):
        self.target.write_bytes(b'archivo-original-a-conservar')
        with patch('colegio.restore.shutil.copy2',side_effect=PermissionError('Sin permiso de copia')):
            with self.assertRaises(PermissionError):restore(self.backup,self.directory)
        self.assertEqual(self.target.read_bytes(),b'archivo-original-a-conservar')

    def test_windows_writable_sync_backups_include_committed_wal_and_restore(self):
        source=self.root/'original.sqlite3'
        with tempfile.TemporaryDirectory() as external, closing(connect(source)) as db:
            with db:
                db.execute("UPDATE settings SET value=? WHERE key='backup_directory'",(external,))
                db.execute("INSERT INTO sessions(token,user_id,csrf,expires) VALUES('fixture-session',1,'fixture-csrf',9999999999)")
                record_payment(db,{'student_id':1,'amount':'25','currency':'USD','paid_on':'2025-09-21',
                    'method':'Transferencia','reference':'TR-REC-02','request_key':'wal-fixture'},1)
            original=[tuple(r) for r in db.execute('SELECT * FROM payments ORDER BY id')]
            permissions={};calls=[];real_sync=os.fsync

            def tracked_open(*args,**kwargs):
                saved=builtins.open(*args,**kwargs)
                permissions[saved.fileno()]=saved.writable()
                return saved

            def windows_commit(descriptor):
                if not permissions.get(descriptor):
                    raise OSError(errno.EBADF,'Bad file descriptor')
                calls.append(descriptor)
                real_sync(descriptor)

            # Linux accepts read-only fsync; emulate Windows's stricter _commit.
            with patch('colegio.storage.open',new=tracked_open,create=True), patch('colegio.storage.os.fsync',new=windows_commit):
                status=automatic_backup(source)
                self.assertFalse(status.get('local_error'));self.assertFalse(status.get('secondary_error'))
                self.assertEqual(len(calls),2)
                local=Path(status['local_path']);remote=Path(external)/local.name
                for snapshot in (local,remote):
                    with closing(connect(snapshot)) as copy:
                        self.assertEqual([tuple(r) for r in copy.execute('SELECT * FROM payments ORDER BY id')],original)
                        self.assertEqual(copy.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                        self.assertEqual(copy.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],0)
                        self.assertEqual(copy.execute('SELECT SUM(amount) FROM allocations').fetchone()[0],7500)
                restore(remote,self.directory)
            with closing(connect(self.target)) as restored:
                self.assertEqual([tuple(r) for r in restored.execute('SELECT * FROM payments ORDER BY id')],original)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],1)

    def test_sync_failure_preserves_previous_backup_and_active_payments(self):
        source=self.root/'original.sqlite3'
        before=self.backup.read_bytes()
        with patch('colegio.storage.os.fsync',side_effect=OSError(errno.EIO,'Simulated write failure')):
            with self.assertRaises(OSError):consistent_backup(source,self.backup)
        self.assertEqual(self.backup.read_bytes(),before)
        self.assertFalse(list(self.root.glob('.aula-backup-*')))
        with closing(connect(source)) as db:
            self.assertEqual(dict(db.execute('SELECT * FROM payments').fetchone()),self.payment)

    def test_upgrade_startup_under_windows_sync_rules_preserves_saved_payment(self):
        from colegio.server import main, SchoolServer
        consistent_backup(self.backup,self.target)
        with closing(connect(self.target)) as db:
            db.execute('PRAGMA user_version=4')
        permissions={};real_sync=os.fsync;real_serve=SchoolServer.serve_forever

        def tracked_open(*args,**kwargs):
            saved=builtins.open(*args,**kwargs)
            permissions[saved.fileno()]=saved.writable()
            return saved

        def windows_commit(descriptor):
            if not permissions.get(descriptor):raise OSError(errno.EBADF,'Bad file descriptor')
            real_sync(descriptor)

        def serve_once(server):
            worker=threading.Thread(target=real_serve,args=(server,),daemon=True);worker.start()
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
            try:
                conn.request('GET','/api/session');response=conn.getresponse()
                self.assertEqual(response.status,200);response.read()
            finally:
                conn.close();server.shutdown();worker.join(timeout=5)

        with patch('sys.argv',['aula','--data-dir',str(self.directory),'--port','0']), \
             patch('colegio.storage.open',new=tracked_open,create=True), \
             patch('colegio.storage.os.fsync',new=windows_commit), \
             patch.object(SchoolServer,'serve_forever',new=serve_once):
            main()
        previous=list((self.directory/'backups').glob('antes-actualizacion-*.sqlite3'))
        self.assertEqual(len(previous),1)
        with closing(connect(previous[0])) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],4)
            self.assertEqual(dict(db.execute('SELECT * FROM payments').fetchone()),self.payment)
        with closing(connect(self.target)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],5)
            self.assertEqual(dict(db.execute('SELECT * FROM payments').fetchone()),self.payment)

    def test_secondary_sync_failure_keeps_local_and_previous_external_backup(self):
        source=self.root/'original.sqlite3'
        with tempfile.TemporaryDirectory() as external:
            with closing(connect(source)) as db,db:
                db.execute("UPDATE settings SET value=? WHERE key='backup_directory'",(external,))
            first=automatic_backup(source)
            prior=Path(external)/Path(first['local_path']).name;original=prior.read_bytes()
            real_sync=os.fsync;calls=0

            def fail_second(descriptor):
                nonlocal calls
                calls+=1
                if calls==2:raise OSError(errno.EIO,'Simulated USB write failure')
                real_sync(descriptor)

            with patch('colegio.storage.os.fsync',new=fail_second):status=automatic_backup(source)
            self.assertFalse(status.get('local_error'));self.assertTrue(status['secondary_error'])
            self.assertTrue(Path(status['local_path']).is_file())
            self.assertEqual(prior.read_bytes(),original)
            self.assertEqual(list(Path(external).glob('*.sqlite3')),[prior])
            self.assertFalse(list(Path(external).glob('.aula-copy-*')))


if __name__=='__main__':
    unittest.main()
