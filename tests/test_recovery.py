"""Recovery must work when the current database is unreadable."""
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from colegio.db import connect, initialize, record_payment
from colegio.restore import restore
from colegio.storage import consistent_backup


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


if __name__=='__main__':
    unittest.main()
