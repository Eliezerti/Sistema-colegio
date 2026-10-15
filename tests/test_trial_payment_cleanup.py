"""Exceptional, explicitly confirmed pre-production cutover; fictional databases only."""
from contextlib import closing
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from colegio.db import connect, next_record_id, ValidationError, BALANCES, local_today
from colegio.audit_chain import local_status
from colegio.storage import DataLock
from colegio.trial_payment_cleanup import preview, clear, CONFIRMATION


class TrialPaymentCleanupTests(unittest.TestCase):
    def setUp(self):
        from tests.test_system import SystemTests
        self.f=SystemTests();self.f.setUp()
        self.f.request('payments',self.f.payment(paid_on=local_today().isoformat()))
        self.f.request('payments',self.f.payment(key='second',amount='10',paid_on=local_today().isoformat()))
        self.f.request('expenses',dict(concept='Gasto ficticio a conservar',category='Operación',spent_on=local_today().isoformat(),amount='7.25',currency='USD',method='Efectivo'))
        self.f.server.shutdown();self.f.server.server_close();self.f.thread.join()
        self.path=self.f.path;self.directory=self.path.parent

    def tearDown(self):self.f.tearDown()

    def apply(self,**extra):
        data=dict(username='admin',password='Una-clave-segura',preview_hash=preview(self.directory)['preview_hash'],
            backup_password='FICTICIO-respaldo-seguro-2026',confirmation=CONFIRMATION,reason='Cobros ficticios de prueba antes de producción',trial_only=True)
        data.update(extra)
        return clear(self.directory,**data)

    def rows(self,table):
        with closing(connect(self.path)) as db:return [tuple(r) for r in db.execute('SELECT * FROM '+table)]

    def test_clear_preserves_masters_charges_other_floors_and_original_audit_and_has_verified_cipher(self):
        with closing(connect(self.path)) as db,db:
            db.execute("INSERT OR REPLACE INTO settings VALUES('id_floor_payments','99')")
            db.execute("INSERT OR REPLACE INTO settings VALUES('id_floor_expenses','17')")
        tables=('users','students','guardians','grades','charges','expenses','exchange_rates','enrollment_documents','payment_plans')
        from colegio.administration import cash_summary
        with closing(connect(self.path)) as db:cash_before=cash_summary(db,local_today().isoformat())
        before={t:self.rows(t) for t in tables};history=self.rows('audit');links=self.rows('audit_links')
        with closing(connect(self.path)) as db:
            expected=db.execute('SELECT SUM(amount) FROM charges WHERE cancelled=0').fetchone()[0]
            other_floors=list(db.execute("SELECT key,value FROM settings WHERE key LIKE 'id_floor_%' AND key!='id_floor_payments'"))
        result=self.apply()
        self.assertEqual(before,{t:self.rows(t) for t in tables})
        self.assertEqual(self.rows('payments'),[]);self.assertEqual(self.rows('allocations'),[]);self.assertEqual(self.rows('sessions'),[])
        self.assertEqual(self.rows('audit')[:len(history)],history);self.assertEqual(self.rows('audit_links')[:len(links)],links)
        with closing(connect(self.path)) as db:
            cash_after=cash_summary(db,local_today().isoformat())
            self.assertEqual(cash_before['income_usd'],3250)
            self.assertEqual(cash_after['income_usd'],0)
            self.assertEqual(cash_before['expense_usd'],cash_after['expense_usd'])
            self.assertEqual(cash_after['expense_usd'],725)
            self.assertEqual(next_record_id(db,'payments'),1)
            self.assertEqual(db.execute("SELECT value FROM settings WHERE key='id_floor_payments'").fetchone()[0],'0')
            self.assertEqual(other_floors,list(db.execute("SELECT key,value FROM settings WHERE key LIKE 'id_floor_%' AND key!='id_floor_payments'")))
            self.assertTrue(local_status(db)['ok']);self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(sum(row['amount']-row['paid'] for row in db.execute(BALANCES)),expected)
        from colegio.backup_inspection import probe_backup
        from tests.crypto_helpers import PASSWORD
        report=probe_backup(Path(result['backup']['path']),PASSWORD)
        self.assertEqual(report['payments'],2)
        self.assertTrue(result['backup']['encrypted']);self.assertTrue(result['backup']['verified'])
        with self.assertRaisesRegex(ValidationError,'ya preparó'):preview(self.directory)
        from colegio.db import record_payment
        with closing(connect(self.path)) as db,db:
            self.assertEqual(record_payment(db,self.f.payment(key='production'),1)['id'],1)
        with closing(connect(self.path)) as db:self.assertTrue(local_status(db)['ok'])

    def test_password_confirmation_stale_review_and_open_app_never_delete(self):
        before=self.rows('payments')
        for extra in ({'password':'incorrecta'},{'username':'no-admin'},{'trial_only':False},
                      {'confirmation':'borrar'},{'preview_hash':'cambió'},{'reason':''}):
            with self.subTest(extra=extra),self.assertRaises(ValidationError):self.apply(**extra)
        with DataLock(self.directory),self.assertRaises(RuntimeError):preview(self.directory)
        self.assertEqual(self.rows('payments'),before)

    def test_backup_failure_and_clock_block_prevent_any_financial_change(self):
        before=self.rows('payments')
        with patch('colegio.backup_export.write_encrypted',side_effect=OSError('Disco no disponible')):
            with self.assertRaises(OSError):self.apply()
        with patch('colegio.trial_payment_cleanup.ClockGuard.require',side_effect=ValidationError('Reloj bloqueado')):
            with self.assertRaises(ValidationError):self.apply()
        self.assertEqual(self.rows('payments'),before)
        with closing(connect(self.path)) as db:self.assertEqual(next_record_id(db,'payments'),3)

    def test_issued_financial_documents_and_pending_restore_require_review_without_deletion(self):
        before=self.rows('payments')
        for table in ('guardian_documents','cash_closures','year_transitions'):
            with self.subTest(table=table):
                with closing(connect(self.path)) as db,db:
                    if table=='cash_closures':
                        db.execute("INSERT INTO cash_closures(closed_on,snapshot_json,created_at,created_by) VALUES('2026-10-15','{}','2026-10-15',1)")
                    else:db.execute(f"INSERT INTO {table}(snapshot_json,created_at,created_by) VALUES('{{}}','2026-10-15',1)")
                with self.assertRaises(ValidationError):preview(self.directory)
                self.assertEqual(self.rows('payments'),before)
                with closing(connect(self.path)) as db,db:db.execute('DELETE FROM '+table)
        pending=self.directory/'.restore-pending.json';pending.write_text('{}')
        with self.assertRaisesRegex(ValidationError,'restauración pendiente'):preview(self.directory)
        pending.unlink()
        self.assertEqual(self.rows('payments'),before)

    def test_real_process_kills_leave_all_old_data_or_a_complete_cutover(self):
        # Each stage gets an isolated exact copy, including independent audit anchors.
        import shutil,tempfile
        from colegio.storage import consistent_backup
        for stage in ('after_backup','after_allocations','after_payments','after_counter','before_commit','after_commit'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as temp:
                target=Path(temp)/'datos';shutil.copytree(self.directory,target)
                consistent_backup(self.path,target/'colegio.sqlite3')
                review=preview(target);ready=target/'ready'
                source="""import time
from pathlib import Path
from colegio import trial_payment_cleanup as m
def point(stage):
 if stage==TARGET:
  Path(READY).write_text('ready')
  time.sleep(60)
m.checkpoint=point
m.clear(DIRECTORY,username='admin',password='Una-clave-segura',preview_hash=DIGEST,confirmation=m.CONFIRMATION,reason='Prueba ficticia de corte de proceso',trial_only=True,backup_password='FICTICIO-respaldo-seguro-2026')
"""
                source='TARGET='+repr(stage)+'\nREADY='+repr(str(ready))+'\nDIRECTORY='+repr(str(target))+'\nDIGEST='+repr(review['preview_hash'])+'\n'+source
                child=subprocess.Popen([sys.executable,'-c',source],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                try:
                    until=time.monotonic()+20
                    while not ready.exists() and child.poll() is None and time.monotonic()<until:time.sleep(.02)
                    if not ready.exists():
                        out,err=child.communicate(timeout=2);self.fail(err.decode(errors='replace'))
                    child.kill();child.communicate(timeout=5)
                    with closing(connect(target/'colegio.sqlite3')) as db:
                        self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                        self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
                        self.assertTrue(local_status(db)['ok'])
                        self.assertEqual(db.execute('SELECT COUNT(*) FROM payments').fetchone()[0],0 if stage=='after_commit' else 2)
                        self.assertEqual(next_record_id(db,'payments'),1 if stage=='after_commit' else 3)
                finally:
                    if child.poll() is None:child.kill();child.communicate()
