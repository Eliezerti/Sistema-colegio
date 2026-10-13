"""Independent financial checks, calendar boundaries and five real HTTP cashiers."""
import http.client
import json
import sqlite3
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date
from unittest.mock import patch

from colegio.db import connect, record_payment, charges, local_today, synchronize_monthly_charges
from colegio.maintenance import review_database, sequence_review


class FinancialInvariantTests(unittest.TestCase):
    def setUp(self):
        from tests.test_production_review import ProductionReviewTests
        self.f = ProductionReviewTests('test_review_detects_unallocated_payment_without_modifying_any_record')
        self.f.setUp()

    def tearDown(self):
        self.f.tearDown()

    def test_valid_and_voided_allocations_are_separate_and_review_is_readonly(self):
        first = self.f.pay('10', 'valid')
        second = self.f.pay('20', 'voided')
        with self.f.db:
            self.f.db.execute("UPDATE payments SET voided=1,void_reason='Ficticio' WHERE id=?", (second,))
        before = self.f.db.total_changes
        review = review_database(self.f.db)
        self.assertTrue(review['ok'], review['errors'])
        self.assertEqual(review['financial'], {'valid_payments': 1000, 'valid_allocations': 1000})
        self.assertEqual(self.f.db.total_changes, before)
        self.assertEqual(self.f.db.execute('SELECT SUM(amount) FROM allocations').fetchone()[0], 3000)
        self.assertEqual(self.f.db.execute('SELECT amount FROM payments WHERE id=?', (first,)).fetchone()[0], 1000)

    def test_unallocated_and_overallocated_payments_are_detected_without_repair(self):
        payment = self.f.pay('10', 'mismatch')
        with self.f.db:
            self.f.db.execute('UPDATE allocations SET amount=25000 WHERE payment_id=?', (payment,))
        before = self.f.db.total_changes
        result = review_database(self.f.db)
        self.assertFalse(result['ok'])
        self.assertTrue(any('superiores' in s for s in result['errors']))
        self.assertTrue(any('total de cobros' in s for s in result['errors']))
        self.assertEqual(before, self.f.db.total_changes)

    def test_correlative_gaps_above_floor_fail_but_reserved_numbers_do_not(self):
        db = self.f.db
        with db:
            db.execute("INSERT INTO guardians(id,name,document) VALUES(5,'Ficticio','V-cinco')")
        result = next(r for r in sequence_review(db) if r['table'] == 'guardians')
        self.assertEqual(result['gaps'], [{'from': 2, 'to': 4}])
        with db: db.execute("INSERT INTO settings VALUES('id_floor_guardians','4')")
        self.assertTrue(next(r for r in sequence_review(db) if r['table'] == 'guardians')['ok'])
        with db: db.execute("UPDATE settings SET value='dañado' WHERE key='id_floor_guardians'")
        result = next(r for r in sequence_review(db) if r['table'] == 'guardians')
        self.assertFalse(result['ok']); self.assertIsNone(result['reserved_until'])

    def test_duplicate_charges_detected_in_damaged_fixture(self):
        # A damaged schema is represented only in a disposable copy; never weaken live constraints.
        path = self.f.path.parent / 'damaged.sqlite3'
        self.f.db.commit()
        with closing(sqlite3.connect(path)) as raw:
            self.f.db.backup(raw)
            schema = raw.execute("SELECT sql FROM sqlite_master WHERE name='charges'").fetchone()[0]
            raw.executescript('PRAGMA foreign_keys=OFF; DROP TABLE charges; '+
                             schema.replace(',UNIQUE(student_id,period,concept)', '')+';')
            raw.execute("INSERT INTO charges VALUES(1,1,'2020-09','Mensualidad',10000,'2020-09-10',0)")
            raw.execute("INSERT INTO charges VALUES(2,1,'2020-09','Mensualidad',10000,'2020-09-10',0)")
            raw.commit()
            raw.row_factory = sqlite3.Row
            before = raw.total_changes
            result = review_database(raw)
            self.assertFalse(result['ok'])
            self.assertTrue(any('repetidos' in s for s in result['errors']))
            self.assertEqual(before, raw.total_changes)

    def test_six_decimal_rate_rounds_each_payment_half_up_and_keeps_historical_rate(self):
        db = self.f.db
        with db: db.execute("INSERT INTO exchange_rates VALUES('2020-10-20','36.123456','ficticio')")
        first = self.f.pay('36.30', 'six', 'VES')
        row = dict(db.execute('SELECT * FROM payments WHERE id=?', (first,)).fetchone())
        self.assertEqual(row['amount'], 100)
        self.assertEqual(row['exchange_rate'], '36.123456')
        with db: db.execute("UPDATE exchange_rates SET rate='40.654321' WHERE rate_date='2020-10-20'")
        self.assertEqual(self.f.pay('36.30', 'six', 'VES'), first)
        self.assertEqual(dict(db.execute('SELECT * FROM payments WHERE id=?', (first,)).fetchone()), row)
        self.assertTrue(review_database(db)['ok'])

    def test_early_enrollment_end_keeps_existing_debt_and_does_not_generate_later_months(self):
        db = self.f.db
        first = self.f.pay('10', 'before-close')
        original = db.execute('SELECT receipt_snapshot FROM payments WHERE id=?', (first,)).fetchone()[0]
        with db:
            db.execute("UPDATE students SET enrollment_end='2020-09-30' WHERE id=1")
            result = synchronize_monthly_charges(db, date(2020, 12, 15))
        self.assertEqual(result['created'], 0)
        self.assertEqual([r['period'] for r in charges(db)], ['2020-09', '2020-10'])
        self.assertEqual(sum(r['balance'] for r in charges(db)), 19000)
        self.assertEqual(db.execute('SELECT receipt_snapshot FROM payments WHERE id=?', (first,)).fetchone()[0], original)


class FiveCashierTests(unittest.TestCase):
    def test_five_independent_cashiers_accept_only_payments_within_the_same_debt(self):
        from tests.test_system import SystemTests
        f = SystemTests('test_concurrent_payment_retries_create_one_receipt')
        f.setUp()
        try:
            with closing(connect(f.path)) as db, db:
                db.execute('UPDATE charges SET cancelled=1')
                db.execute("INSERT INTO charges(student_id,period,concept,amount,due_date) VALUES(1,'2020-09','Prueba concurrente',10000,'2020-09-10')")
            port = f.server.server_port
            def request(route, body=None, cookie='', csrf=''):
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=30)
                headers = {'Cookie': cookie, 'X-CSRF-Token': csrf, 'Content-Type': 'application/json'}
                connection.request('GET' if body is None else 'POST', '/api/'+route,
                                   json.dumps(body) if body is not None else None, headers)
                response = connection.getresponse()
                result = (response.status, json.loads(response.read()), response.getheader('Set-Cookie'))
                connection.close()
                return result
            clients = []
            for number in range(5):
                username = 'cashier'+str(number)
                f.request('users', dict(name=username, username=username, password='FICTICIO-clave-segura', role='cashier'))
                status, _, cookie = request('login', dict(username=username, password='FICTICIO-clave-segura'))
                self.assertEqual(status, 200); cookie = cookie.split(';')[0]
                status, data, _ = request('session', cookie=cookie)
                csrf = data['user']['csrf']
                status, _, _ = request('confirm-rate', dict(rate_date=local_today().isoformat(), rate='100'), cookie, csrf)
                self.assertEqual(status, 200)
                clients.append((cookie, csrf))
            barrier = threading.Barrier(5)
            def pay(number):
                cookie, csrf = clients[number]
                barrier.wait(timeout=20)
                return request('payments', f.payment(amount='40', paid_on=local_today().isoformat(),
                               request_key='distinct-'+str(number), reference='REF-'+str(number)), cookie, csrf)[:2]
            with ThreadPoolExecutor(max_workers=5) as pool:
                results = list(pool.map(pay, range(5)))
            self.assertEqual(sorted(status for status, _ in results), [200,200,400,400,400])
            with closing(connect(f.path)) as db:
                self.assertEqual(db.execute('SELECT SUM(amount) FROM payments WHERE voided=0').fetchone()[0], 8000)
                self.assertEqual(db.execute('SELECT SUM(amount) FROM allocations').fetchone()[0], 8000)
                self.assertEqual([r[0] for r in db.execute('SELECT id FROM payments ORDER BY id')], [1,2])
                self.assertEqual(sum(r['balance'] for r in charges(db)), 2000)
                self.assertTrue(review_database(db)['ok'])
        finally:
            f.tearDown()
