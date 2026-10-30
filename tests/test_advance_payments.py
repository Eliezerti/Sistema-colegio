"""Real HTTP and SQLite coverage, only temporary fictional pupils and receipts."""
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from datetime import datetime, timedelta, timezone
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from colegio.db import connect, local_today, synchronize_monthly_charges
from tests import test_cashea as cashea_tests


class AdvancePaymentTests(unittest.TestCase):
    def setUp(self):
        for target in ('colegio.db.local_today', 'colegio.server.local_today',
                       'colegio.cashea.local_today', 'colegio.administration.local_today',
                       'colegio.advance_payments.local_today', __name__ + '.local_today'):
            mocked = patch(target, return_value=date(2026, 10, 30))
            mocked.start()
            self.addCleanup(mocked.stop)
        cashea_tests.CasheaTests.setUp(self)
    tearDown = cashea_tests.CasheaTests.tearDown
    request = cashea_tests.CasheaTests.request
    student_data = cashea_tests.CasheaTests.student_data
    payment = cashea_tests.CasheaTests.payment
    new_student = cashea_tests.CasheaTests.new_student
    order_data = cashea_tests.CasheaTests.order_data
    order = cashea_tests.CasheaTests.order
    cancel = cashea_tests.CasheaTests.cancel

    def prepare(self, **overrides):
        today = local_today()
        year = today.year if today.month >= 9 else today.year - 1
        self.request('settings', dict(school_name='Colegio FICTICIO', school_year=year,
                     due_day=10, start_month=9, advance_months_limit=3))
        self.grade = self.request('grades', dict(name='Grado de anticipos FICTICIO', capacity=30))['id']
        return self.new_student(monthly_fee='40', **overrides)

    def choices(self, sid):
        return self.request(f'payment-options?student_id={sid}')

    def settle_current(self, sid):
        value = next(s for s in self.request('state')['students'] if s['id'] == sid)
        if value['balance']:
            self.request('payments', dict(student_id=sid, amount=f"{value['balance']/100:.2f}",
                paid_on=local_today().isoformat(), method='Efectivo', currency='USD', request_key=f'current-{sid}'))

    def advance_data(self, sid, count=1, amount=None, **overrides):
        value = self.choices(sid)
        future = value['future'][:count]
        total = sum(c['balance'] for c in value['pending'] + future)
        return dict(dict(student_id=sid, amount=amount or f'{total/100:.2f}', currency='USD',
            method='Efectivo', paid_on=local_today().isoformat(), request_key=f'advance-{sid}-{count}',
            advance_periods=[c['period'] for c in future], advance_quote=value['quote'],
            charge_ids=[c['id'] for c in value['pending'] + future if c['balance']]), **overrides)

    def test_october_30_november_once_snapshot_reports_cash_and_day_one(self):
        sid = self.prepare()
        self.settle_current(sid)
        data = self.advance_data(sid)
        self.assertEqual(data['paid_on'], '2026-10-30')
        self.assertEqual(data['advance_periods'], ['2026-11'])
        before = self.request('cash-preview')['income_usd']
        result = self.request('payments', data)
        receipt = self.request(f"receipt/{result['id']}")
        self.assertEqual(receipt['payment']['paid_on'], '2026-10-30')
        self.assertEqual(receipt['allocations'][0]['concept'], 'Mensualidad 2026-11 (pagada por adelantado)')
        student = next(s for s in self.request('state')['students'] if s['id'] == sid)
        self.assertEqual((student['balance'], student['overdue']), (0, 0))
        self.assertEqual(self.request('cash-preview')['income_usd'], before + 4000)
        self.assertEqual(self.request('daily-report')['advance_income_usd'], 4000)
        monthly = self.request('monthly-report?month=2026-10')
        self.assertEqual(monthly['advance_income_usd'], 4000)
        self.assertNotIn('Grado de anticipos FICTICIO', [g['grade'] for g in monthly['pending_by_grade']])
        self.assertIn(b'Cobrado por adelantado', self.request('monthly-report.csv?month=2026-10'))
        family = self.request(f'guardian-account/{self.guardian}')
        self.assertEqual(next(c for c in family['charges'] if c['student_id'] == sid and c['period'] == '2026-11')['advance_label'], 'Pagado por adelantado')
        pdf = self.request(f"receipt/{result['id']}.pdf")
        self.assertIn(b'/MediaBox [0 0 396 612]', pdf)
        self.assertEqual(self.request('payments', data), dict(id=result['id'], duplicate=True))
        with closing(connect(self.path)) as db, db:
            old = dict(db.execute('SELECT * FROM payments WHERE id=?', (result['id'],)).fetchone())
            sync = synchronize_monthly_charges(db, date(2026, 11, 1))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM charges WHERE student_id=? AND period='2026-11'", (sid,)).fetchone()[0], 1)
            self.assertEqual(dict(db.execute('SELECT * FROM payments WHERE id=?', (result['id'],)).fetchone()), old)
        self.assertTrue(self.request('maintenance-review')['ok'])

    def test_two_months_partial_oldest_and_void_retains_prepared_month(self):
        sid = self.prepare()
        data = self.advance_data(sid, count=2, amount='100')  # October 40 + November 40 + December 20.
        result = self.request('payments', data)
        receipt = self.request(f"receipt/{result['id']}")
        self.assertEqual([a['amount'] for a in receipt['allocations']], [4000, 4000, 2000])
        self.request('void-payment', dict(id=result['id'], reason='Corrección FICTICIA'))
        options = self.choices(sid)
        self.assertEqual([c['period'] for c in options['pending']], ['2026-10', '2026-11', '2026-12'])
        self.assertEqual(len([c for c in options['future'] if c['period'] in ['2026-11', '2026-12']]), 0)
        self.assertEqual(self.request('daily-report').get('advance_income_usd', 0), 0)
        self.assertTrue(self.request('maintenance-review')['ok'])

    def test_limits_calendar_billing_start_and_nonconsecutive_rejected_without_writes(self):
        sid = self.prepare()
        self.settle_current(sid)
        original = self.choices(sid)
        invalid = [dict(advance_periods=['2026-12']), dict(advance_periods=['2027-02']),
                   dict(advance_periods=['2027-09']), dict(advance_periods=['2026-11', '2026-11'])]
        with closing(connect(self.path)) as db:
            before = db.execute('SELECT COUNT(*) FROM monthly_assessments WHERE student_id=?', (sid,)).fetchone()[0]
        for extra in invalid:
            self.request('payments', self.advance_data(sid, **extra), status=400)
        with closing(connect(self.path)) as db, db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM monthly_assessments WHERE student_id=?', (sid,)).fetchone()[0], before)
            db.execute("UPDATE students SET billing_start='2026-12',enrollment_end='2026-12-15' WHERE id=?", (sid,))
        self.assertEqual([c['period'] for c in self.choices(sid)['future']], ['2026-12'])
        with closing(connect(self.path)) as db, db:
            db.execute("UPDATE students SET enrollment_end='2026-10-31' WHERE id=?", (sid,))
        self.assertEqual(self.choices(sid)['future'], [])

    def test_previous_debt_cannot_be_skipped_and_underfunded_future_is_not_created(self):
        sid = self.prepare()
        data = self.advance_data(sid, amount='20')
        self.request('payments', data, status=400)
        data = self.advance_data(sid, amount='50', charge_ids=['future:2026-11'])
        self.request('payments', data, status=400)
        self.assertEqual(self.choices(sid)['future'][0]['period'], '2026-11')

    def test_tariff_quote_stale_then_frozen_through_day_one(self):
        sid = self.prepare()
        self.settle_current(sid)
        stale = self.advance_data(sid)
        with closing(connect(self.path)) as db, db:
            db.execute('UPDATE students SET monthly_fee=5000,discount=10 WHERE id=?', (sid,))
        self.request('payments', stale, status=400)
        value = self.advance_data(sid)
        self.assertEqual(value['amount'], '45.00')
        self.request('payments', value)
        with closing(connect(self.path)) as db, db:
            db.execute('UPDATE students SET monthly_fee=9900,discount=0 WHERE id=?', (sid,))
            synchronize_monthly_charges(db, date(2026, 11, 1))
            self.assertEqual(db.execute("SELECT amount FROM charges WHERE student_id=? AND period='2026-11'", (sid,)).fetchone()[0], 4500)

    def test_full_scholarship_assessed_without_payment_number_and_repeat(self):
        sid = self.prepare()
        self.settle_current(sid)
        with closing(connect(self.path)) as db, db:
            db.execute('UPDATE students SET discount=100 WHERE id=?', (sid,))
        before = len(self.request('state')['payments'])
        data = self.advance_data(sid, request_key='FICTICIO-beca-completa')
        result = self.request('prepare-advance', data)
        self.assertTrue(result['no_payment'])
        self.assertEqual(self.request('prepare-advance', data)['assessed'], 0)
        self.assertEqual(len(self.request('state')['payments']), before)
        with closing(connect(self.path)) as db, db:
            self.assertEqual(db.execute("SELECT amount,charge_id FROM monthly_assessments WHERE student_id=? AND period='2026-11'", (sid,)).fetchone()[:], (0, None))
            db.execute('UPDATE students SET discount=0 WHERE id=?', (sid,))
            synchronize_monthly_charges(db, date(2026, 11, 1))
            self.assertFalse(db.execute("SELECT 1 FROM charges WHERE student_id=? AND period='2026-11'", (sid,)).fetchone())

    def test_cashea_preview_no_write_then_prepares_same_assessment(self):
        sid = self.prepare()
        self.settle_current(sid)
        months = self.advance_data(sid)
        data = self.order_data(student_id=sid, total='40', initial_received='16', initial_percent='40',
            advance_periods=months['advance_periods'], charge_ids=months['charge_ids'])
        preview = self.request('cashea-preview', data)
        self.assertEqual(self.choices(sid)['future'][0]['period'], '2026-11')
        self.assertEqual(preview['financed_amount'], 2400)
        data['preview_hash'] = preview['preview_hash']
        result = self.request('cashea-order', data)
        self.assertEqual(result['invoice_number'], f"R-{result['payment_id']:06d}")
        self.assertEqual(self.request('cashea-order', data), result)
        student = next(s for s in self.request('state')['students'] if s['id'] == sid)
        self.assertEqual(student['balance'], 0)
        self.assertEqual(self.request('daily-report')['advance_income_usd'], 1600)
        self.cancel('cashea-void-order', result['id'])
        self.assertEqual(next(s for s in self.request('state')['students'] if s['id'] == sid)['balance'], 4000)
        self.assertTrue(self.request('maintenance-review')['ok'])

    def test_changed_request_key_data_atomic_failure_and_historical_snapshots(self):
        sid = self.prepare()
        self.settle_current(sid)
        with closing(connect(self.path)) as db:
            historic = [tuple(r) for r in db.execute('SELECT * FROM payments ORDER BY id')]
        data = self.advance_data(sid)
        with patch('colegio.advance_payments.record_payment', side_effect=ValueError('Fallo FICTICIO')):
            self.request('payments', data, status=400)
        self.assertEqual(self.choices(sid)['future'][0]['period'], '2026-11')
        self.request('payments', data)
        self.request('payments', dict(data, advance_periods=['2026-12']), status=400)
        with closing(connect(self.path)) as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM payments ORDER BY id')][:len(historic)], historic)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_cashier_can_advance_cannot_change_limit_or_prepare_mass_and_reader_csrf(self):
        sid = self.prepare()
        self.settle_current(sid)
        for role in ('cashier', 'reader'):
            self.request('users', dict(name=f'Perfil FICTICIO {role}', username=role, role=role,
                         password='FICTICIO-perfil-seguro'))
        self.request('logout', {})
        self.request('login', dict(username='cashier', password='FICTICIO-perfil-seguro'))
        self.csrf = self.request('session')['user']['csrf']
        self.request('confirm-rate', dict(rate_date=local_today().isoformat(), rate='100'))
        data = self.advance_data(sid)
        self.request('payments', data, csrf=False, status=403)
        self.request('settings', dict(advance_months_limit=12), status=403)
        self.request('generate', dict(period='2026-11', school_year=2026), status=403)
        self.request('payments', data)
        self.request('logout', {})
        self.request('login', dict(username='reader', password='FICTICIO-perfil-seguro'))
        self.csrf = self.request('session')['user']['csrf']
        self.request('confirm-rate', dict(rate_date=local_today().isoformat()))
        self.request('payments', self.advance_data(sid), status=403)
        self.request('prepare-advance', self.advance_data(sid), status=403)

    def test_ves_partial_uses_existing_rate_rounding_and_limit_zero_blocks_new_months(self):
        sid = self.prepare()
        self.settle_current(sid)
        data = self.advance_data(sid, amount='1250', currency='VES')
        result = self.request('payments', data)
        payment = self.request(f"receipt/{result['id']}")['payment']
        self.assertEqual((payment['received_amount'], payment['exchange_rate'], payment['amount']), (125000, '100', 1250))
        self.request('settings', dict(school_name='Colegio FICTICIO', school_year=2026,
                     due_day=10, start_month=9, advance_months_limit=0))
        self.assertEqual(self.choices(sid)['future'], [])
        self.assertEqual(self.choices(sid)['pending'][0]['balance'], 2750)
        self.assertEqual(self.request('payments', data)['id'], result['id'])
        self.request('settings', dict(school_name='Colegio FICTICIO', school_year=2026,
                     due_day=10, start_month=9, advance_months_limit=13), status=400)

    def test_concurrent_identical_requests_make_one_payment_and_month(self):
        sid = self.prepare()
        self.settle_current(sid)
        data = self.advance_data(sid)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _:self.request('payments', data), range(2)))
        self.assertEqual(results[0]['id'], results[1]['id'])
        self.assertEqual(sum(not r['duplicate'] for r in results), 1)
        with closing(connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM monthly_assessments WHERE student_id=? AND period='2026-11'", (sid,)).fetchone()[0], 1)
        self.assertTrue(self.request('maintenance-review')['ok'])

    def test_clock_changes_after_prepare_and_payment_before_commit_roll_back_everything(self):
        sid = self.prepare()
        self.settle_current(sid)
        data = self.advance_data(sid)
        from colegio.advance_payments import record_payment
        clock = self.server.clock
        original = clock.now
        def moved(db, payment, user_id):
            result = record_payment(db, payment, user_id)
            clock.now = lambda:datetime.now(timezone.utc) + timedelta(days=60)
            return result
        try:
            with patch('colegio.advance_payments.record_payment', side_effect=moved):
                self.request('payments', data, status=428)
        finally:
            clock.now = original
        with closing(connect(self.path)) as db:
            self.assertFalse(db.execute("SELECT 1 FROM monthly_assessments WHERE student_id=? AND period='2026-11'", (sid,)).fetchone())
            self.assertFalse(db.execute('SELECT 1 FROM payments WHERE request_key=?', (data['request_key'],)).fetchone())

    def test_actual_process_exit_after_preparation_leaves_no_future_charge_payment_or_audit(self):
        sid = self.prepare()
        self.settle_current(sid)
        data = self.advance_data(sid)
        with closing(connect(self.path)) as db:
            audit_before = [tuple(r) for r in db.execute('SELECT * FROM audit ORDER BY id')]
        script = '''
import json,os,sys
from colegio.db import connect
from colegio import advance_payments as advance
from colegio import db as ledger
from datetime import date
advance.local_today=ledger.local_today=lambda:date(2026,10,30)
db=connect(sys.argv[1]);db.execute('BEGIN IMMEDIATE')
def stop(*args,**kwargs):os._exit(73)
advance.record_payment=stop
advance.receive(db,json.loads(sys.argv[2]),1)
'''
        child = subprocess.run([sys.executable, '-c', script, str(self.path), json.dumps(data)],
                               capture_output=True, timeout=20)
        self.assertEqual(child.returncode, 73, child.stderr.decode(errors='replace'))
        with closing(connect(self.path)) as db:
            self.assertFalse(db.execute("SELECT 1 FROM monthly_assessments WHERE student_id=? AND period='2026-11'", (sid,)).fetchone())
            self.assertFalse(db.execute("SELECT 1 FROM charges WHERE student_id=? AND period='2026-11'", (sid,)).fetchone())
            self.assertFalse(db.execute('SELECT 1 FROM payments WHERE request_key=?', (data['request_key'],)).fetchone())
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM audit ORDER BY id')], audit_before)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])


if __name__ == '__main__':
    unittest.main()
