import gc
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from colegio.clock_guard import ClockGuard, ClockConfirmationRequired
from colegio.db import connect, initialize, local_today, synchronize_monthly_charges
from colegio.server import open_school
from tests import test_system as fixtures


class ClockStartupTests(unittest.TestCase):
    def test_startup_with_future_clock_does_not_generate_any_monthly_charges(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'colegio.sqlite3';initialize(path)
            today=local_today();year=today.year if today.month>=9 else today.year-1
            with closing(connect(path)) as db,db:
                db.execute("INSERT INTO guardians(id,name,document) VALUES(1,'Representante','V-123')")
                db.execute("INSERT INTO grades(id,name,capacity) VALUES(1,'Primaria',30)")
                db.execute('''INSERT INTO students(id,name,document,student_code,birth_date,guardian_id,grade_id,school_year,
                    monthly_fee,discount,status,enrollment_start,enrollment_end,billing_start)
                    VALUES(1,'Alumno','AL-000001','AL-000001','2015-01-01',1,1,?,10000,0,'active',?,?,?)''',
                    (year,f'{year}-09-01',f'{year+1}-08-31',today.strftime('%Y-%m')))
            current=datetime.now(timezone.utc)
            guard=ClockGuard(path,now=lambda:current);guard.close();del guard;gc.collect()
            with patch('colegio.clock_guard.utc_now',return_value=current+timedelta(days=60)):
                with open_school(path,0) as server:
                    self.assertTrue(server.clock.snapshot()['blocked'])
                    with closing(connect(path)) as db:
                        self.assertEqual(db.execute('SELECT COUNT(*) FROM charges').fetchone()[0],0)
                        with self.assertRaises(ClockConfirmationRequired):synchronize_monthly_charges(db)
            with closing(connect(path)) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM charges').fetchone()[0],0)

    def test_existing_history_bootstrap_and_unchanged_sqlite_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'colegio.sqlite3';initialize(path)
            with closing(connect(path)) as db,db:
                db.execute("INSERT INTO audit(action,details,created_at) VALUES('fixture','{}','2026-10-01T12:00:00+00:00')")
                tables=db.execute('SELECT name,sql FROM sqlite_master ORDER BY name').fetchall()
                version=db.execute('PRAGMA user_version').fetchone()[0]
            guard=ClockGuard(path,now=lambda:datetime(2027,1,1,tzinfo=timezone.utc),history=True)
            self.assertTrue(guard.snapshot()['blocked'])
            with closing(connect(path)) as db:
                self.assertEqual(db.execute('SELECT name,sql FROM sqlite_master ORDER BY name').fetchall(),tables)
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],version)


class ClockEndpointTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.SystemTests();self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.guard=self.fixture.server.clock
        self.base=datetime.now(timezone.utc)
        self.guard.now=lambda:self.base+timedelta(days=60)

    def test_finance_reports_receipts_and_manual_generation_are_blocked(self):
        for endpoint,data in (('state',None),('daily-report',None),('daily-report.pdf',None),
                              ('receipt/1',None),('receipt/1.pdf',None),('export',None),
                              ('payments',self.fixture.payment()),('generate',{'period':local_today().strftime('%Y-%m')})):
            result=self.fixture.request(endpoint,data,status=428)
            self.assertTrue(result['requires_clock_confirmation'])
        with closing(connect(self.fixture.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM payments').fetchone()[0],0)

    def test_admin_confirmation_requires_csrf_then_restores_access(self):
        status=self.fixture.request('clock-status')
        self.guard.now=lambda:self.base
        status=self.fixture.request('clock-status')
        data=dict(pending_id=status['pending']['id'],observed_at=status['current_time'],reviewed=True)
        self.fixture.request('clock-confirm',data,csrf=False,status=403)
        self.fixture.request('clock-confirm',data)
        state=self.fixture.request('state')
        self.assertEqual(state['user']['role'],'admin')
        events=[r for r in state['audit'] if r['action']=='clock_confirmation']
        self.assertEqual(len(events),1)

    def test_cashier_cannot_confirm_and_database_stays_unchanged(self):
        self.fixture.request('clock-status')
        with closing(connect(self.fixture.path)) as db,db:
            db.execute("UPDATE users SET role='cashier' WHERE username='admin'")
        status=self.fixture.request('clock-status')
        self.fixture.request('clock-confirm',dict(pending_id=status['pending']['id'],
            observed_at=status['current_time'],reviewed=True),status=403)
        self.assertTrue(self.fixture.request('clock-status')['blocked'])

    def test_login_limit_uses_monotonic_time_despite_wall_clock_changes(self):
        with patch('colegio.server.time.time',return_value=1):
            for _ in range(5):self.fixture.request('login',{'username':'admin','password':'incorrecta'},status=401)
        with patch('colegio.server.time.time',return_value=9999999999):
            self.fixture.request('login',{'username':'admin','password':'incorrecta'},status=429)

    def test_clock_change_before_payment_commit_rolls_back_payment_and_allocations(self):
        self.guard.now=lambda:self.base
        from colegio.server import record_payment
        def changed_clock(db,data,user_id):
            result=record_payment(db,data,user_id)
            self.guard.now=lambda:self.base+timedelta(days=60)
            return result
        with patch('colegio.server.record_payment',side_effect=changed_clock):
            self.fixture.request('payments',self.fixture.payment(),status=428)
        with closing(connect(self.fixture.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM payments').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM allocations').fetchone()[0],0)


