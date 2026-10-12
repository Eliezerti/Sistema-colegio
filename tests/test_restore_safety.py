"""A1 exercises actual SQLite, real killed processes and production startup ordering."""
import base64
import csv
import io
import json
import os
import sqlite3
import subprocess
import sys
import time
import unittest
from urllib.parse import urlsplit
from urllib.request import url2pathname
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from colegio.backup_inspection import SEQUENCES, file_hash, probe_backup
from colegio.db import connect, record_payment, next_record_id
from colegio.restore import preview_restore, restore, last_restore, LOSS, UNKNOWN, ReviewRequired
from colegio.restore_journal import PENDING, RecoveryRequired, finish_pending
from colegio.server import open_school, SchoolServer
from colegio.storage import consistent_backup, DataLock
from tests import test_recovery as fixtures
from tests.restore_helpers import approved_restore


class RestoreSafetyTests(unittest.TestCase):
    setUp=fixtures.RecoveryTests.setUp
    tearDown=fixtures.RecoveryTests.tearDown

    def current(self):
        consistent_backup(self.backup,self.target)

    def second_payment(self,key='later',paid_on='2025-09-19'):
        with closing(connect(self.target)) as db,db:
            return record_payment(db,{'student_id':1,'amount':'10','currency':'USD','paid_on':paid_on,
                'method':'Efectivo','reference':'REF-'+key,'request_key':key},1)['id']

    def test_future_schema_99_rejected_without_destination_change(self):
        self.current();before=self.target.read_bytes()
        with closing(connect(self.backup)) as db,db:db.execute('PRAGMA user_version=99')
        with self.assertRaisesRegex(ValueError,'esquema 99'):preview_restore(self.backup,self.directory)
        self.assertEqual(before,self.target.read_bytes())
        self.assertFalse((self.directory/PENDING).exists())
        with closing(connect(self.target)) as db,db:db.execute('PRAGMA user_version=99')
        future_bytes=self.target.read_bytes()
        with patch('colegio.server.initialize') as init:
            with self.assertRaisesRegex(ValueError,'esquema 99'):
                with open_school(self.target,0):pass
            init.assert_not_called()
        self.assertEqual(self.target.read_bytes(),future_bytes)

    def test_no_review_no_restore_and_review_becomes_stale(self):
        self.current();self.second_payment()
        review=preview_restore(self.backup,self.directory)
        self.assertEqual(review['confirmation'],LOSS)
        with self.assertRaises(ReviewRequired):restore(self.backup,self.directory)
        with closing(connect(self.target)) as db,db:db.execute("UPDATE students SET name='Nombre modificado' WHERE id=1")
        with self.assertRaises(ReviewRequired):
            restore(self.backup,self.directory,preview_hash=review['preview_hash'],confirmation=LOSS)
        with closing(connect(self.target)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM payments').fetchone()[0],2)

    def test_content_identity_backdated_payment_void_reversal_and_floor_preservation(self):
        self.current();second=self.second_payment()
        with closing(connect(self.target)) as db,db:
            db.execute("UPDATE payments SET voided=1,void_reason='Anulación ficticia' WHERE id=1")
            for i,table in enumerate(SEQUENCES):
                db.execute('INSERT INTO settings VALUES(?,?)',('id_floor_'+table,str(10+i)))
        review=preview_restore(self.backup,self.directory)
        self.assertEqual(review['comparison']['payment_changes'],2)
        self.assertIsNone(review['backup']['created_at'])
        self.assertTrue(any(d['action']=='Anulación se revierte' for d in review['comparison']['details']))
        approved_restore(self.backup,self.directory)
        with closing(connect(self.target)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],10)
            for i,table in enumerate(SEQUENCES):self.assertEqual(next_record_id(db,table),11+i)
            event=json.loads(db.execute("SELECT details FROM audit WHERE action='restore-backup'").fetchone()[0])
            self.assertEqual(event['payment_changes'],2)
        self.assertEqual(len(json.loads((self.directory/'restauraciones.json').read_text())),1)
        self.assertGreater(self.second_payment('after-restore'),second)

    def test_same_id_with_other_request_key_or_reference_is_a_difference(self):
        self.current()
        with closing(connect(self.target)) as db,db:
            db.execute("UPDATE payments SET request_key='other-identity',reference='OTHER' WHERE id=1")
        review=preview_restore(self.backup,self.directory)
        self.assertEqual(review['comparison']['payment_changes'],1)
        self.assertEqual(review['comparison']['details'][0]['number'],'R-000001')

    def test_exact_loss_reports_and_previous_snapshot_are_preserved_without_secrets(self):
        self.current();self.second_payment()
        with closing(connect(self.target)) as db,db:
            db.execute("UPDATE users SET password='PASSWORD-DO-NOT-EXPORT' WHERE id=1")
            db.execute("INSERT INTO employees(id,name,document,position,salary,status,bank_account) VALUES(1,'Docente ficticio','V-EMP','Docente',10000,'active','01020000000098765432')")
            db.execute("""INSERT INTO expenses(id,concept,category,amount,spent_on,employee_id,created_by,
                         currency,received_amount,exchange_rate,method,reference)
                         VALUES(1,'Gasto ficticio','Operación',200,'2025-09-19',1,1,'VES',20000,'100','Transferencia','EG-REF')""")
        approved_restore(self.backup,self.directory)
        event=last_restore(self.directory)
        self.assertEqual(len(event['reports']),2)
        csv_file=next(Path(p) for p in event['reports'] if p.endswith('.csv'))
        pdf=next(Path(p) for p in event['reports'] if p.endswith('.pdf')).read_bytes()
        rows=list(csv.DictReader(io.StringIO(csv_file.read_text(encoding='utf-8-sig')),delimiter=';'))
        payment=next(r for r in rows if r['Correlativo']=='R-000002')
        self.assertEqual((payment['Alumno / persona'],payment['Importe USD'],payment['Moneda recibida'],payment['Referencia']),
                         ('Alumno de prueba','10.00','USD','REF-later'))
        self.assertTrue(any(r['Correlativo']=='E-000001' for r in rows))
        for secret in (b'PASSWORD-DO-NOT-EXPORT',b'01020000000098765432'):
            self.assertNotIn(secret,pdf);self.assertNotIn(secret,csv_file.read_bytes())
        self.assertTrue(pdf.startswith(b'%PDF'))
        with closing(connect(event['previous_backup'])) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM payments').fetchone()[0],2)

    def test_probe_never_opens_original_sqlite_or_writes_origin_and_cleans_temp_on_error(self):
        original_hash=file_hash(self.backup);files=set(self.root.iterdir())
        real_connect=sqlite3.connect;opened=[]
        def tracked(path,*args,**kwargs):
            self.assertNotIn(str(self.backup),str(path))
            opened.append(str(path));return real_connect(path,*args,**kwargs)
        with patch('colegio.backup_inspection.sqlite3.connect',side_effect=tracked):
            result=probe_backup(self.backup)
        self.assertEqual(result['payments'],1);self.assertEqual(result['balance_usd'],5000)
        self.assertEqual(file_hash(self.backup),original_hash);self.assertEqual(set(self.root.iterdir()),files)
        paths=[Path(url2pathname(urlsplit(p).path)) for p in opened]
        self.assertTrue(all(not p.exists() for p in paths))
        with closing(connect(self.backup)) as db,db:db.execute('PRAGMA user_version=99')
        import tempfile
        real_temporary=tempfile.TemporaryDirectory;temporaries=[]
        def tracked_temporary(*args,**kwargs):
            result=real_temporary(*args,**kwargs);temporaries.append(Path(result.name));return result
        with patch('colegio.backup_inspection.tempfile.TemporaryDirectory',side_effect=tracked_temporary):
            with self.assertRaises(ValueError):probe_backup(self.backup)
        self.assertTrue(temporaries)
        self.assertTrue(all(not p.exists() for p in temporaries))
        self.assertEqual(set(self.root.iterdir()),files)

    def test_corrupt_backup_invalid_references_and_corrupt_current_do_not_invent_zero(self):
        self.current();before=self.target.read_bytes()
        bad=self.root/'bad.sqlite3';bad.write_bytes(b'bad')
        with self.assertRaises(sqlite3.Error):preview_restore(bad,self.directory)
        self.assertEqual(self.target.read_bytes(),before)
        with closing(sqlite3.connect(self.backup)) as db,db:db.execute('UPDATE students SET guardian_id=999')
        with self.assertRaisesRegex(ValueError,'referencias'):probe_backup(self.backup)
        # Restore a valid source for the separate damaged-current case.
        consistent_backup(self.root/'original.sqlite3',self.backup)
        self.target.write_bytes(b'DAMAGED-CURRENT')
        review=preview_restore(self.backup,self.directory)
        self.assertEqual(review['confirmation'],UNKNOWN)
        self.assertIsNone(review['current'])
        self.assertIsNone(review['comparison']['payment_changes'])
        with self.assertRaises(ReviewRequired):
            restore(self.backup,self.directory,preview_hash=review['preview_hash'],confirmation=UNKNOWN)
        approved_restore(self.backup,self.directory)
        self.assertEqual(probe_backup(self.target)['payments'],1)
        self.assertEqual(Path(last_restore(self.directory)['original_files'],'colegio.sqlite3').read_bytes(),b'DAMAGED-CURRENT')

    def test_unreadable_pending_record_blocks_all_startup_without_touching_anything(self):
        self.current()
        previous=self.directory/'backups'/'antes-restauracion-segura.sqlite3'
        consistent_backup(self.target,previous)
        (self.directory/PENDING).write_text('{"truncated":')
        originals={p:p.read_bytes() for p in (self.target,previous,self.directory/PENDING)}
        with patch('colegio.server.initialize') as init,patch('colegio.server.synchronize_monthly_charges') as monthly:
            with self.assertRaisesRegex(RecoveryRequired,'no abrió la base'):
                with open_school(self.target,0):pass
            init.assert_not_called();monthly.assert_not_called()
        with self.assertRaises(RecoveryRequired):SchoolServer(('127.0.0.1',0),str(self.target))
        for p,data in originals.items():self.assertEqual(p.read_bytes(),data)

    def test_real_process_kills_before_sidecars_between_sidecars_and_replace_and_after_replace(self):
        for stage in ('before_sidecars','after_sidecars','after_replace','after_commit'):
            with self.subTest(stage=stage):
                directory=self.root/stage;directory.mkdir();target=directory/'colegio.sqlite3'
                consistent_backup(self.backup,target)
                # A process exits without SQLite cleanup, leaving a committed WAL payment.
                writer="""import os,sys
from colegio.db import connect,record_payment
db=connect(sys.argv[1])
db.execute('PRAGMA journal_mode=WAL')
record_payment(db,{'student_id':1,'amount':'10','currency':'USD','paid_on':'2025-09-19','method':'Efectivo','reference':'WAL-2','request_key':'WAL-2'},1)
db.commit()
os._exit(0)
"""
                subprocess.run([sys.executable,'-c',writer,str(target)],check=True,timeout=10)
                self.assertTrue(target.with_name(target.name+'-wal').exists())
                marker=self.root/(stage+'.ready')
                child="""import sys,time
from pathlib import Path
from colegio.restore import preview_restore,restore
import colegio.restore_journal as journal
def stop_at(stage):
 if stage==sys.argv[3]:
  Path(sys.argv[4]).write_text(stage)
  while True:time.sleep(.02)
journal.checkpoint=stop_at
review=preview_restore(sys.argv[1],sys.argv[2])
restore(sys.argv[1],sys.argv[2],preview_hash=review['preview_hash'],confirmation=review['confirmation'])
"""
                process=subprocess.Popen([sys.executable,'-c',child,str(self.backup),str(directory),stage,str(marker)],
                                          stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                try:
                    deadline=time.monotonic()+15
                    while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                    self.assertTrue(marker.exists(),process.communicate(timeout=1)[1].decode() if process.poll() is not None else 'No alcanzó etapa')
                    process.kill();process.communicate(timeout=5)
                    self.assertNotEqual(process.returncode,0)
                finally:
                    if process.poll() is None:process.kill();process.communicate()
                self.assertTrue((directory/PENDING).exists())
                import colegio.server as server
                original_init=server.initialize;original_monthly=server.synchronize_monthly_charges
                events=[]
                def initialize_checked(path):
                    self.assertFalse((directory/PENDING).exists());events.append('initialize');return original_init(path)
                def monthly_checked(db):
                    self.assertFalse((directory/PENDING).exists());events.append('monthly');return original_monthly(db)
                with patch('colegio.server.initialize',side_effect=initialize_checked),patch('colegio.server.synchronize_monthly_charges',side_effect=monthly_checked):
                    with open_school(target,0):pass
                self.assertEqual(events[:2],['initialize','monthly'])
                with closing(connect(target)) as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM payments').fetchone()[0],1)
                    self.assertGreater(next_record_id(db,'payments'),2)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE action='restore-backup'").fetchone()[0],1)
                event=last_restore(directory)
                with closing(connect(event['previous_backup'])) as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM payments').fetchone()[0],2)
                self.assertEqual(len(json.loads((directory/'restauraciones.json').read_text())),1)
