"""Kill actual child processes; checkpoints are injected only inside disposable tests."""
import json
import subprocess
import sys
import time
import unittest
from contextlib import closing
from pathlib import Path

from colegio.db import connect
from colegio.storage import consistent_backup
from colegio.backup_inspection import probe_backup


def kill_at(test, script, arguments, marker):
    process = subprocess.Popen([sys.executable, '-u', '-c', script, *map(str, arguments), str(marker)],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic()+25
        while not marker.exists() and process.poll() is None and time.monotonic()<deadline:
            time.sleep(.02)
        if not marker.exists():
            if process.poll() is None: process.kill()
            _, error = process.communicate(timeout=10)
            test.fail('El proceso no alcanzó el punto de corte: '+error.decode(errors='replace'))
        process.kill()
        process.communicate(timeout=10)
        test.assertNotEqual(process.returncode, 0)
    finally:
        if process.poll() is None: process.kill(); process.communicate(timeout=10)


class OperationKillTests(unittest.TestCase):
    def setUp(self):
        from tests.test_system import SystemTests
        self.f = SystemTests('test_process_killed_during_and_after_payment_preserves_atomicity')
        self.f.setUp()

    def tearDown(self):
        self.f.tearDown()

    def test_local_backup_kills_during_copy_before_publish_and_after_publish(self):
        f = self.f
        target = f.path.parent/'published.sqlite3'
        old = f.path.parent/'old.sqlite3'
        consistent_backup(f.path, old)
        f.request('payments', f.payment(amount='10'))
        script = r'''
import os,sqlite3,sys,time
from pathlib import Path
import colegio.storage as storage
stage=sys.argv[3];marker=Path(sys.argv[4])
def pause():
 marker.write_text(stage)
 while True:time.sleep(.02)
original_connect=sqlite3.connect
class Connection(sqlite3.Connection):
 def backup(self,target,**kw):
  def progress(status,remaining,total):
   if stage=='during_copy' and remaining>0:pause()
  return super().backup(target,pages=1,progress=progress,**kw)
storage.sqlite3.connect=lambda *a,**kw:original_connect(*a,factory=Connection,**kw)
original_replace=os.replace
def replace(source,target):
 if stage=='before_publish':pause()
 original_replace(source,target)
 if stage=='after_publish':pause()
storage.os.replace=replace
storage.consistent_backup(sys.argv[1],sys.argv[2])
'''
        for stage in ('during_copy', 'before_publish', 'after_publish'):
            with self.subTest(stage=stage):
                target.write_bytes(old.read_bytes())
                marker = f.path.parent/(stage+'.ready')
                kill_at(self, script, [f.path, target, stage], marker)
                summary = probe_backup(target)
                self.assertEqual(summary['payments'], 1 if stage=='after_publish' else 0)
                self.assertEqual(summary['integrity'], 'ok')
                with closing(connect(f.path)) as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM payments').fetchone()[0], 1)
                    self.assertEqual(db.execute('SELECT SUM(amount) FROM allocations').fetchone()[0], 1000)

    def test_unused_record_kills_after_backup_during_delete_and_after_commit(self):
        f = self.f
        script = r'''
import sqlite3,sys,time
from pathlib import Path
from colegio.audit_chain import AuditConnection
import colegio.institution_archive as archive
stage=sys.argv[3];marker=Path(sys.argv[4])
def pause():
 marker.write_text(stage)
 while True:time.sleep(.02)
class Connection(AuditConnection):
 def execute(self,sql,*a):
  result=super().execute(sql,*a)
  if stage=='during_delete' and sql.startswith('DELETE FROM guardians'):pause()
  return result
original=archive.consistent_backup
def backup(*a):
 original(*a)
 if stage=='after_backup':pause()
archive.consistent_backup=backup
db=sqlite3.connect(sys.argv[1],factory=Connection);db.prepare_audit();db.row_factory=sqlite3.Row
db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
user={'id':1,'role':'admin'};target=int(sys.argv[2]);review=archive.record_preview(db,'guardian',target,user)
archive.archive_action(db,'delete-unused-record',dict(kind='guardian',id=target,preview_hash=review['preview_hash'],
 password='Una-clave-segura',confirmation='BORRAR FICHA',reason='Ficha ficticia B1'),user)
db.commit()
if stage=='after_commit':pause()
'''
        for stage in ('after_backup', 'during_delete', 'after_commit'):
            with self.subTest(stage=stage):
                target = f.request('guardians', dict(name='Ficha ficticia '+stage, document='V-'+stage))['id']
                f.request('archive-guardian', dict(id=target, reason='Prueba B1', confirmation='ARCHIVAR'))
                previous = set((f.path.parent/'backups').glob('antes-borrar-ficha-*.sqlite3'))
                marker = f.path.parent/(stage+'.ready')
                kill_at(self, script, [f.path, target, stage], marker)
                backups = set((f.path.parent/'backups').glob('antes-borrar-ficha-*.sqlite3'))-previous
                self.assertEqual(len(backups), 1)
                copy = backups.pop()
                self.assertEqual(probe_backup(copy)['integrity'], 'ok')
                with closing(connect(copy)) as db:
                    self.assertTrue(db.execute('SELECT 1 FROM guardians WHERE id=?', (target,)).fetchone())
                with closing(connect(f.path)) as db:
                    present = bool(db.execute('SELECT 1 FROM guardians WHERE id=?', (target,)).fetchone())
                    self.assertEqual(present, stage!='after_commit')
                    self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                    self.assertEqual(list(db.execute('PRAGMA foreign_key_check')), [])
                    from colegio.audit_chain import local_status
                    self.assertTrue(local_status(db)['ok'])
                    events = [json.loads(r[0]) for r in db.execute("SELECT details FROM audit WHERE action='delete-unused-record'")]
                    self.assertEqual(any(e['id']==target for e in events), stage=='after_commit')

    def test_encrypted_tier_process_kills_leave_previous_or_complete_copy(self):
        from colegio.backup_crypto import MAGIC
        root=self.f.path.parent
        source=root/'cipher-source.aulabak';destination=root/'cipher-published.aulabak'
        old=MAGIC+b'previous-complete-ciphertext';new=MAGIC+b'new-complete-ciphertext'*10000
        source.write_bytes(new)
        script=r'''
import sys,time
from pathlib import Path
import colegio.backup_tiers as tiers
stage=sys.argv[3];marker=Path(sys.argv[4])
def pause():
 marker.write_text(stage)
 while True:time.sleep(.02)
original_copy=tiers.shutil.copyfile
original_replace=tiers.os.replace
def copy(source,target):
 if stage=='during_copy':
  with open(source,'rb') as saved,open(target,'wb') as output:output.write(saved.read(64));output.flush()
  pause()
 return original_copy(source,target)
def replace(source,target):
 if stage=='before_publish':pause()
 result=original_replace(source,target)
 if stage=='after_publish':pause()
 return result
tiers.shutil.copyfile=copy;tiers.os.replace=replace
tiers.copy_cipher(sys.argv[1],sys.argv[2])
'''
        for stage in ('during_copy','before_publish','after_publish'):
            with self.subTest(stage=stage):
                destination.write_bytes(old);marker=root/('tier-kill-'+stage)
                kill_at(self,script,[source,destination,stage],marker)
                self.assertEqual(destination.read_bytes(),new if stage=='after_publish' else old)
                self.assertEqual(source.read_bytes(),new)
