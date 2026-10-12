import http.client
import json
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from colegio.backup_health import describe_backup
from colegio.db import hash_password, initialize, local_today
from colegio.server import SchoolServer
from colegio.storage import automatic_backup, backup_status


class BackupHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'colegio.sqlite3'
        initialize(self.path)
        self.now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
        self.destination = str(Path(self.temp.name) / 'second')

    def configure(self, destination):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT OR REPLACE INTO settings VALUES('backup_directory', ?)", (destination,))

    def describe(self, **status):
        return describe_backup(self.path, status, now=self.now)

    def codes(self, result):
        return [a['code'] for a in result['alerts']]

    def test_missing_destination_warns_even_with_recent_local_backup(self):
        self.assertEqual(self.codes(self.describe(local_at=self.now.isoformat())), ['secondary_missing'])

    def test_external_age_uses_server_time_and_three_day_boundary(self):
        self.configure(self.destination)
        for age, expected in ((timedelta(days=3), []),
                              (timedelta(days=3, seconds=1), ['secondary_stale'])):
            with self.subTest(age=age):
                result = self.describe(secondary_directory=self.destination, secondary_at=(self.now-age).isoformat())
                self.assertEqual(self.codes(result), expected)
        equivalent = (self.now-timedelta(days=3)).astimezone(timezone(timedelta(hours=-4)))
        self.assertEqual(self.codes(self.describe(secondary_directory=self.destination, secondary_at=equivalent.isoformat())), [])

    def test_unknown_external_time_never_claims_a_recent_copy(self):
        self.configure(self.destination)
        for stamp in (None, '', 'not-a-date', '2026-10-11T11:00:00', (self.now+timedelta(days=1)).isoformat()):
            with self.subTest(stamp=stamp):
                self.assertIn('secondary_unconfirmed', self.codes(self.describe(secondary_directory=self.destination, secondary_at=stamp)))

    def test_last_errors_and_changed_destination(self):
        self.configure(self.destination)
        result = self.describe(secondary_directory=self.destination, secondary_at=self.now.isoformat(),
                               local_error='Disco lleno', secondary_error='USB desconectado')
        self.assertEqual(self.codes(result), ['local_failed', 'secondary_failed'])
        result = self.describe(secondary_directory='old-folder', secondary_at=self.now.isoformat(), secondary_error='Old error')
        self.assertEqual(self.codes(result), ['secondary_unconfirmed'])
        self.assertNotIn('secondary_at', result)

    def test_warning_read_does_not_edit_data_or_backup_files(self):
        before = self.path.read_bytes()
        self.describe()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse((self.path.parent/'backups').exists())

    def test_invalid_status_file_warns_and_successful_backup_clears_error(self):
        target = self.path.parent/'backup-status.json'
        for content in ('[1,2]', '{', 'null'):
            target.write_text(content, encoding='utf-8')
            self.assertTrue(backup_status(self.path)['local_error'])
        automatic_backup(self.path)
        self.assertFalse(backup_status(self.path)['local_error'])


class BackupAlertAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'colegio.sqlite3'
        initialize(self.path)
        with closing(sqlite3.connect(self.path)) as db, db:
            for role in ('admin', 'cashier', 'reader'):
                db.execute('INSERT INTO users(name,username,password,role) VALUES(?,?,?,?)',
                           (role, role, hash_password('Prueba-segura-2026'), role))
        self.server = SchoolServer(('127.0.0.1', 0), self.path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.cookie = ''

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, endpoint, data=None, expected=200, csrf=''):
        connection = http.client.HTTPConnection(*self.server.server_address)
        headers = {'Cookie': self.cookie}
        if data is not None:
            headers.update({'Content-Type': 'application/json', 'X-CSRF-Token': csrf})
        connection.request('GET' if data is None else 'POST', '/api/'+endpoint,
                           json.dumps(data) if data is not None else None, headers)
        response = connection.getresponse()
        self.assertEqual(response.status, expected)
        if response.getheader('Set-Cookie'):
            self.cookie = response.getheader('Set-Cookie').split(';')[0]
        result = json.loads(response.read())
        connection.close()
        return result

    def test_authentication_rate_gate_and_roles_keep_existing_permissions(self):
        self.request('rate-gate', expected=401)
        self.request('backup-status', expected=401)
        for role in ('admin', 'cashier', 'reader'):
            with self.subTest(role=role):
                self.request('login', {'username': role, 'password': 'Prueba-segura-2026'})
                gate = self.request('rate-gate')
                self.assertEqual(gate['backup']['alerts'][0]['code'], 'secondary_missing')
                self.request('state', expected=428)
                csrf = self.request('session')['user']['csrf']
                if role in ('admin', 'cashier'):
                    self.request('confirm-rate', {'rate': '100', 'rate_date': local_today().isoformat()}, csrf=csrf)
                else:
                    self.request('confirm-rate', {'rate_date': local_today().isoformat()}, csrf=csrf)
                self.assertTrue(self.request('backup-status')['alerts'])
                if role != 'admin':
                    self.request('backup-now', {}, expected=403, csrf=csrf)
                self.request('backup-now', {}, expected=403)  # CSRF is still mandatory.

    def test_status_write_failure_remains_visible_until_backup_succeeds(self):
        with patch('colegio.server.automatic_backup', side_effect=OSError('Status file unavailable')):
            self.assertTrue(self.server.make_backup()['local_error'])
        status = self.server.backup_status()
        self.assertIn('local_failed', [a['code'] for a in status['alerts']])
        self.server.make_backup()
        self.assertNotIn('local_failed', [a['code'] for a in self.server.backup_status()['alerts']])

    def test_demo_has_no_real_backup_warnings(self):
        self.server.demo = True
        try:
            self.assertEqual(self.server.backup_status()['demo'], True)
            self.assertNotIn('alerts', self.server.backup_status())
        finally:
            self.server.demo = False
