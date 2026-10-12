import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from colegio.clock_guard import ClockGuard, ClockConfirmationRequired, ClockInputError
from colegio.db import connect, initialize, local_today, synchronize_monthly_charges


class ClockGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'colegio.sqlite3'
        initialize(self.path)
        self.current = datetime(2026,10,11,14,tzinfo=timezone.utc)
        self.tick = 100.0
        self.guard = ClockGuard(self.path, now=lambda:self.current, monotonic=lambda:self.tick)

    def move(self, seconds, elapsed=0):
        self.current += timedelta(seconds=seconds)
        self.tick += elapsed
        return self.guard.snapshot()

    def test_backward_and_future_jump_are_persistent(self):
        self.guard.require()
        status = self.move(-180)
        self.assertEqual(status['pending']['reason'], 'backwards')
        with self.assertRaises(ClockConfirmationRequired):
            self.guard.require()
        reopened = ClockGuard(self.path, now=lambda:self.current, monotonic=lambda:self.tick)
        self.assertEqual(reopened.snapshot()['pending']['id'],status['pending']['id'])

    def test_offline_seven_days_boundary_and_running_monotonic_time(self):
        status = self.move(7*86400)
        self.assertFalse(status['blocked'])
        self.assertFalse(self.move(3600, elapsed=3600)['blocked'])
        self.assertTrue(self.move(121)['blocked'])

    def test_offline_jump_over_threshold_blocks_before_first_operation(self):
        self.guard.close()
        self.current += timedelta(days=7,seconds=1)
        reopened = ClockGuard(self.path, now=lambda:self.current)
        self.assertEqual(reopened.snapshot()['pending']['reason'],'forward')

    def test_small_ntp_change_allowed_even_at_midnight_but_larger_rollback_blocks(self):
        self.guard.require()
        self.assertFalse(self.move(-60)['blocked'])
        self.current = datetime(2026,10,12,4,0,30,tzinfo=timezone.utc)
        self.guard = ClockGuard(self.path, now=lambda:self.current, monotonic=lambda:self.tick)
        self.guard.require()
        self.assertFalse(self.move(-60)['blocked'])
        self.assertTrue(self.move(-120)['blocked'])

    def test_midnight_is_persisted_even_before_thirty_seconds(self):
        self.current = datetime(2026,10,12,3,59,59,tzinfo=timezone.utc)
        self.guard.require()
        self.move(2,elapsed=2)
        data=json.loads(self.guard.path.read_text())
        self.assertEqual(data['last_seen'],self.current.isoformat())

    def confirmation(self, user=None, **changes):
        status=self.guard.snapshot()
        data=dict(pending_id=status['pending']['id'],observed_at=status['current_time'],reviewed=True)
        data.update(changes)
        with closing(connect(self.path)) as db:
            db.execute("INSERT OR IGNORE INTO users(id,username,name,password,role) VALUES(1,'admin','Administración','unused','admin')")
            db.commit()
            db.execute('BEGIN IMMEDIATE')
            return self.guard.confirm(db,user or {'id':1,'role':'admin'},data)

    def test_admin_confirmation_is_audited_and_reanchors_clock(self):
        self.guard.require();self.move(-3600)
        result=self.confirmation()
        self.assertFalse(result['blocked'])
        with closing(connect(self.path)) as db:
            row=db.execute("SELECT user_id,details FROM audit WHERE action='clock_confirmation'").fetchone()
        self.assertEqual(row[0],1)
        self.assertEqual(json.loads(row[1])['confirmed_time'],self.current.isoformat())
        self.assertFalse(self.guard.require()['blocked'])

    def test_cashier_and_reader_cannot_confirm(self):
        self.guard.require();self.move(3600)
        for role in ('cashier','reader'):
            with self.assertRaises(PermissionError):
                self.confirmation({'id':1,'role':role})
        self.assertTrue(self.guard.snapshot()['blocked'])

    def test_confirmation_requires_review_and_current_displayed_date(self):
        self.guard.require();self.move(3600)
        with self.assertRaises(ClockInputError):self.confirmation(reviewed=False)
        with self.assertRaises(ClockInputError):self.confirmation(pending_id='old')
        with self.assertRaises(ClockInputError):self.confirmation(observed_at=(self.current-timedelta(minutes=3)).isoformat())
        self.assertTrue(self.guard.snapshot()['blocked'])

    def test_corrupted_control_blocks_and_preserves_original_on_confirmation(self):
        self.guard.path.write_text('{damaged')
        self.guard=ClockGuard(self.path,now=lambda:self.current)
        self.assertTrue(self.guard.snapshot()['blocked'])
        self.guard.close()
        self.assertEqual(self.guard.path.read_text(),'{damaged')
        self.confirmation()
        self.assertEqual(next(self.path.parent.glob('clock-status-invalid-*')).read_text(),'{damaged')

    def test_persistence_failure_blocks_and_audit_failure_does_not_unlock(self):
        self.guard.require();self.tick+=31
        with patch('colegio.clock_guard.atomic_json',side_effect=OSError('Disk unavailable')):
            self.assertTrue(self.guard.snapshot()['blocked'])
        with patch('colegio.db.audit',side_effect=sqlite3.OperationalError('Audit unavailable')):
            with self.assertRaises(sqlite3.OperationalError):self.confirmation()
        self.assertTrue(self.guard.snapshot()['blocked'])

    def test_metadata_publish_failure_after_audit_stays_blocked(self):
        self.guard.require();self.move(3600)
        with patch('colegio.clock_guard.atomic_json',side_effect=OSError('Cannot publish control')):
            with self.assertRaises(OSError):self.confirmation()
        self.assertTrue(self.guard.snapshot()['blocked'])

    def test_history_without_control_needs_admin_review_even_if_date_looks_normal(self):
        self.guard.path.unlink()
        with closing(connect(self.path)) as db,db:
            db.execute("INSERT INTO audit(action,details,created_at) VALUES('fixture','{}',?)",(self.current.isoformat(),))
        reopened=ClockGuard(self.path,now=lambda:self.current,history=True)
        self.assertEqual(reopened.snapshot()['pending']['reason'],'initial_review')

    def test_confirmation_caps_future_sessions_without_extending_shorter_expirations(self):
        self.guard.require();self.move(3600)
        short=int(self.current.timestamp())+60
        with closing(connect(self.path)) as db,db:
            db.execute("INSERT INTO users(id,username,name,password,role) VALUES(1,'admin','Administración','unused','admin')")
            db.execute("INSERT INTO sessions(token,user_id,csrf,expires) VALUES('long',1,'a',9999999999)")
            db.execute("INSERT INTO sessions(token,user_id,csrf,expires) VALUES('short',1,'b',?)",(short,))
        self.confirmation()
        with closing(connect(self.path)) as db:
            sessions=dict(db.execute('SELECT token,expires FROM sessions'))
        self.assertEqual(sessions['long'],int(self.current.timestamp())+12*3600)
        self.assertEqual(sessions['short'],short)


