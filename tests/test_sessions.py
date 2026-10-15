from contextlib import closing
import hashlib
import secrets
import threading
import unittest
from unittest.mock import patch

from colegio.db import connect, local_today
from colegio.login_limiter import LoginLimiter
from colegio.sessions import Sessions, token_hash
from colegio.server import SchoolServer
from tests import test_system as fixtures


class SessionLifetimeTests(unittest.TestCase):
    def setUp(self):
        self.tick = 100.0
        self.sessions = Sessions(now=lambda: self.tick)
        self.token = secrets.token_urlsafe(32)
        self.digest = token_hash(self.token)
        self.sessions.issue(self.digest)

    def test_hash_only_and_malformed_cookie_rejected(self):
        self.assertEqual(self.digest, 'sha256:' + hashlib.sha256(self.token.encode()).hexdigest())
        for value in ('', self.digest, 'x' * 1000, 'á' * 43, None):
            self.assertEqual(token_hash(value), '')

    def test_idle_boundary_and_background_reads_do_not_extend(self):
        for offset in (30, 60, 899):
            self.tick = 100 + offset
            self.assertAlmostEqual(self.sessions.status(self.digest, 15)['remaining_seconds'], 900 - offset)
        self.tick = 1000
        self.assertIsNone(self.sessions.status(self.digest, 15))
        self.assertIsNone(self.sessions.touch(self.digest, 15))

    def test_activity_extends_idle_but_not_absolute_lifetime(self):
        self.tick += 899
        self.assertEqual(self.sessions.touch(self.digest, 15)['remaining_seconds'], 900)
        for _ in range(70):
            self.tick += 600
            self.assertIsNotNone(self.sessions.touch(self.digest, 15))
        self.tick = 100 + 12 * 3600
        self.assertIsNone(self.sessions.touch(self.digest, 15))

    def test_wall_clock_changes_do_not_extend_or_expire_sessions(self):
        for wall in (1, 9999999999):
            with patch('time.time', return_value=wall):
                self.tick += 30
                self.assertEqual(self.sessions.status(self.digest, 15)['remaining_seconds'], 900 - (self.tick - 100))

    def test_restart_revocation_and_shorter_configuration(self):
        self.assertIsNone(Sessions().status(self.digest, 15))
        self.tick += 300
        self.assertIsNone(self.sessions.status(self.digest, 5))
        self.sessions.issue(self.digest)
        self.sessions.revoke(self.digest)
        self.assertIsNone(self.sessions.status(self.digest, 60))


class LoginLimiterTests(unittest.TestCase):
    def test_progression_origin_user_isolation_and_success(self):
        tick = [0]
        limiter = LoginLimiter(now=lambda: tick[0])
        for _ in range(4):
            limiter.failure('127.0.0.1', 'uno')
            self.assertEqual(limiter.wait('127.0.0.1', 'uno'), 0)
        for delay in (5, 10, 20, 40, 60, 60):
            limiter.failure('127.0.0.1', 'uno')
            self.assertEqual(limiter.wait('127.0.0.1', 'uno'), delay)
            self.assertEqual(limiter.wait('other', 'uno'), delay)
            self.assertEqual(limiter.wait('127.0.0.1', 'dos'), 0)
            tick[0] += delay
        limiter.success('127.0.0.1', 'uno')
        limiter.failure('127.0.0.1', 'uno')
        self.assertEqual(limiter.wait('127.0.0.1', 'uno'), 0)
        tick[0] += 900
        limiter.wait('127.0.0.1', 'dos')
        self.assertFalse(limiter.accounts)
        self.assertFalse(limiter.origins)

    def test_monotonic_cooldown_and_concurrency_slots_release(self):
        limiter = LoginLimiter(now=lambda: 100)
        for _ in range(5):
            limiter.failure('local', 'uno')
        with patch('time.time', return_value=9999999999):
            self.assertEqual(limiter.wait('local', 'uno'), 5)
        self.assertTrue(limiter.checks.acquire(False))
        self.assertTrue(limiter.checks.acquire(False))
        self.assertFalse(limiter.checks.acquire(False))
        limiter.checks.release()
        self.assertTrue(limiter.checks.acquire(False))
        limiter.checks.release(); limiter.checks.release()


class SessionAPITests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.SystemTests('test_local_password_reset_requires_closed_application_and_preserves_data')
        self.fixture.setUp()
        self.tick = 100.0
        self.fixture.server.sessions.now = lambda: self.tick
        # Re-issue the already authenticated token in the injected time domain.
        self.digest = token_hash(self.fixture.cookie.split('=', 1)[1])
        self.fixture.server.sessions.issue(self.digest)

    def tearDown(self):
        self.fixture.tearDown()

    def test_only_hash_stored_restart_closes_sessions_no_schema_change(self):
        f = self.fixture
        with closing(connect(f.path)) as db:
            stored = db.execute('SELECT token FROM sessions').fetchone()[0]
            self.assertEqual(stored, self.digest)
            self.assertNotIn(f.cookie.split('=', 1)[1], '\n'.join(db.iterdump()))
            schema = db.execute('SELECT name,sql FROM sqlite_master ORDER BY name').fetchall()
        f.server.shutdown();f.server.server_close();f.thread.join()
        f.server = SchoolServer(('127.0.0.1', 0), str(f.path))
        f.thread = threading.Thread(target=f.server.serve_forever, daemon=True);f.thread.start()
        f.request('state', status=401)
        f.request('login', {'username': 'admin', 'password': 'Una-clave-segura'})
        f.csrf = f.request('session')['user']['csrf']
        with closing(connect(f.path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 12)
            self.assertEqual(schema, db.execute('SELECT name,sql FROM sqlite_master ORDER BY name').fetchall())

    def test_background_endpoints_expire_and_cannot_emit_or_mutate_after_timeout(self):
        f = self.fixture
        before = f.request('state')
        for offset in (100, 300, 899):
            self.tick = 100 + offset
            for endpoint in ('session', 'rate-gate', 'backup-status', 'clock-status', 'session-status'):
                f.request(endpoint)
        self.tick = 1000
        for endpoint, data in (('state', None), ('daily-report.pdf', None), ('enrollment/' + str(f.student), None),
                               ('session-activity', {}), ('payments', f.payment()), ('generate', {'period': '2030-01'})):
            f.request(endpoint, data, status=401)
        self.assertIsNone(f.request('session')['user'])
        f.request('login', {'username': 'admin', 'password': 'Una-clave-segura'})
        f.csrf = f.request('session')['user']['csrf']
        f.request('confirm-rate', {'rate_date': local_today().isoformat(), 'rate': '100'})
        after = f.request('state')
        for table in ('students', 'charges', 'payments', 'enrollments'):
            self.assertEqual(before[table], after[table])

    def test_activity_requires_csrf_and_clock_anomaly_does_not_stop_authentication_timer(self):
        f = self.fixture
        self.tick += 899
        f.request('session-activity', {}, status=403, csrf=False)
        self.assertEqual(f.request('session-status')['remaining_seconds'], 1)
        f.request('session-activity', {})
        self.assertEqual(f.request('session-status')['remaining_seconds'], 900)
        with patch.object(f.server.clock, 'require', side_effect=AssertionError('Authentication must not generate data')):
            f.request('session-activity', {})
            f.request('session-status')

    def test_configuration_is_admin_only_bounded_and_audited(self):
        f = self.fixture
        f.request('session-preferences', {'idle_minutes': '10'}, status=403, csrf=False)
        for invalid in ('0', '4', '61', '15.5', None, True):
            f.request('session-preferences', {'idle_minutes': invalid}, status=400)
        f.request('session-preferences', {'idle_minutes': '5'})
        self.assertEqual(f.request('session-status')['idle_minutes'], 5)
        with closing(connect(f.path)) as db:
            detail = db.execute("SELECT details FROM audit WHERE action='session_idle_changed'").fetchone()[0]
            self.assertIn('previous_minutes', detail); self.assertIn('new_minutes', detail)
        f.request('users', {'name': 'Caja', 'username': 'caja', 'password': 'Clave-caja-segura', 'role': 'cashier'})
        f.request('login', {'username': 'caja', 'password': 'Clave-caja-segura'})
        f.csrf = f.request('session')['user']['csrf']
        f.request('session-preferences', {'idle_minutes': '60'}, status=403)
        self.tick += 300
        f.request('state', status=401)

    def test_login_failures_do_not_block_other_account_and_case_is_normalized(self):
        f = self.fixture
        f.request('users', {'name': 'Caja', 'username': 'caja', 'password': 'Clave-caja-segura', 'role': 'cashier'})
        f.server.login_limiter.now = lambda: self.tick
        for _ in range(5):
            f.request('login', {'username': ' ADMIN ', 'password': 'incorrecta'}, status=401)
        f.request('login', {'username': 'admin', 'password': 'Una-clave-segura'}, status=429)
        f.request('login', {'username': 'caja', 'password': 'Clave-caja-segura'})
        self.tick += 5
        f.request('login', {'username': 'admin', 'password': 'Una-clave-segura'})
        self.assertEqual(f.server.login_limiter.wait('127.0.0.1', 'admin'), 0)

    def test_recovery_revokes_every_account_notice_persists_until_each_admin_acknowledges(self):
        from colegio.reset_password import reset_password
        f = self.fixture
        f.request('users', {'name': 'Otro administrador', 'username': 'otro', 'password': 'Clave-otro-segura', 'role': 'admin'})
        f.request('users', {'name': 'Caja', 'username': 'caja', 'password': 'Clave-caja-segura', 'role': 'cashier'})
        admin_cookie = f.cookie
        f.request('login', {'username': 'caja', 'password': 'Clave-caja-segura'})
        cash_cookie = f.cookie
        f.server.shutdown();f.server.server_close();f.thread.join()
        reset_password(f.path.parent, 'admin', 'Nueva-clave-segura')
        with closing(connect(f.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM students').fetchone()[0], 1)
            self.assertNotIn('Nueva-clave-segura', '\n'.join(db.iterdump()))
        f.server = SchoolServer(('127.0.0.1', 0), str(f.path))
        f.thread = threading.Thread(target=f.server.serve_forever, daemon=True);f.thread.start()
        for cookie in (admin_cookie, cash_cookie):
            f.cookie = cookie; f.request('state', status=401)
        f.request('login', {'username': 'admin', 'password': 'Nueva-clave-segura'})
        f.csrf = f.request('session')['user']['csrf']
        notice = f.request('session-status')['recovery_notice']
        self.assertEqual(notice['username'], 'admin')
        f.request('recovery-notice-ack', {'notice_id': notice['id']}, status=403, csrf=False)
        f.request('recovery-notice-ack', {'notice_id': 'wrong'}, status=400)
        f.request('recovery-notice-ack', {'notice_id': notice['id']})
        self.assertIsNone(f.request('session-status')['recovery_notice'])
        f.request('login', {'username': 'otro', 'password': 'Clave-otro-segura'})
        f.csrf = f.request('session')['user']['csrf']
        self.assertEqual(f.request('session-status')['recovery_notice'], notice)
        f.request('login', {'username': 'caja', 'password': 'Clave-caja-segura'})
        f.csrf = f.request('session')['user']['csrf']
        self.assertIsNone(f.request('session-status')['recovery_notice'])
        f.request('recovery-notice-ack', {'notice_id': notice['id']}, status=403)

    def test_failed_recovery_rolls_back_password_sessions_and_notice(self):
        from colegio.reset_password import reset_password
        from colegio.db import check_password
        f = self.fixture
        with patch('colegio.security_notices.record_recovery', side_effect=OSError('Fallo ficticio')):
            with self.assertRaises(OSError):
                reset_password(f.path.parent, 'admin', 'Nueva-clave-segura')
        with closing(connect(f.path)) as db:
            self.assertTrue(check_password('Una-clave-segura', db.execute("SELECT password FROM users WHERE username='admin'").fetchone()[0]))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 1)
            self.assertIsNone(db.execute("SELECT value FROM settings WHERE key='security_password_recovery'").fetchone())
            self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE action='local-admin-password-reset'").fetchone()[0], 0)
        self.assertIsNone(f.request('session-status')['recovery_notice'])
        self.assertTrue(list((f.path.parent / 'backups').glob('recuperacion-clave-*.sqlite3')))

    def test_stale_ack_cannot_hide_new_recovery_and_unreadable_notice_is_explicit(self):
        from colegio.security_notices import record_recovery
        f = self.fixture
        with closing(connect(f.path)) as db, db:
            user = db.execute("SELECT id,username FROM users WHERE username='admin'").fetchone()
            old = record_recovery(db, user)
            new = record_recovery(db, user)
        f.request('recovery-notice-ack', {'notice_id': old['id']}, status=400)
        self.assertEqual(f.request('session-status')['recovery_notice'], new)
        with closing(connect(f.path)) as db, db:
            db.execute("UPDATE settings SET value='{' WHERE key='security_password_recovery'")
        self.assertEqual(f.request('session-status')['recovery_notice'], {'id': '', 'unreadable': True})
        f.request('recovery-notice-ack', {'notice_id': new['id']}, status=400)

    def test_reader_cannot_change_timeout_and_invalid_stored_setting_keeps_default(self):
        f = self.fixture
        with closing(connect(f.path)) as db, db:
            db.execute("INSERT INTO settings(key,value) VALUES('session_idle_minutes','999999')")
        self.assertEqual(f.request('session-status')['idle_minutes'], 15)
        f.request('users', {'name': 'Consulta', 'username': 'consulta', 'password': 'Clave-consulta-segura', 'role': 'reader'})
        f.request('login', {'username': 'consulta', 'password': 'Clave-consulta-segura'})
        f.csrf = f.request('session')['user']['csrf']
        f.request('session-preferences', {'idle_minutes': '60'}, status=403)

    def test_password_check_failure_always_releases_verification_slot(self):
        f = self.fixture
        with patch('colegio.server.check_password', side_effect=OSError('Fallo ficticio de verificación')):
            for _ in range(3):
                f.request('login', {'username': 'admin', 'password': 'Una-clave-segura'}, status=500)
        f.request('login', {'username': 'admin', 'password': 'Una-clave-segura'})
        self.assertEqual(f.server.login_limiter.wait('127.0.0.1', 'admin'), 0)

