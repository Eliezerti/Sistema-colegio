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

from colegio.backup_health import CLOUD_KEY, declare_cloud_destination, describe_backup
from colegio.db import ValidationError
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
        return describe_backup(self.path, status, now=self.now, disk_relation={'status':'different'})

    def codes(self, result):
        return [a['code'] for a in result['alerts']]

    def declare_cloud(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT OR IGNORE INTO users(id,name,username,password,role) VALUES(1,'Administrador','admin','test-only','admin')")
            status = describe_backup(self.path, {'secondary_directory': self.destination,
                                    'secondary_at': self.now.isoformat()}, now=self.now)
            declare_cloud_destination(db, {'id': 1, 'role': 'admin'},
                                      {'directory': self.destination, 'reviewed': True}, status)

    def test_cloud_declaration_only_replaces_unknown_disk_warning(self):
        self.configure(self.destination)
        self.declare_cloud()
        status = {'secondary_directory': self.destination, 'secondary_at': self.now.isoformat()}
        result = describe_backup(self.path, status, now=self.now, disk_relation={'status': 'unknown'})
        self.assertEqual(result['alerts'], [])
        self.assertTrue(result['cloud_declared'])
        self.assertEqual(result['cloud_declaration']['confirmed_by'], 1)
        # It never turns the actual Windows inspection into a successful disk result.
        result = describe_backup(self.path, status, now=self.now, disk_relation={'status': 'same'})
        self.assertEqual(self.codes(result), ['same_disk'])

    def test_cloud_declaration_does_not_hide_failure_or_stale_unconfirmed_copies(self):
        self.configure(self.destination)
        self.declare_cloud()
        for extra, expected in (({'local_error': 'Error local'}, 'local_failed'),
                                ({'secondary_error': 'Error externo'}, 'secondary_failed'),
                                ({'retention_error': 'Error de conservación'}, 'retention_failed'),
                                ({'secondary_at': (self.now-timedelta(days=4)).isoformat()}, 'secondary_stale'),
                                ({'secondary_at': ''}, 'secondary_unconfirmed')):
            with self.subTest(expected=expected):
                status = dict(secondary_directory=self.destination, secondary_at=self.now.isoformat())
                status.update(extra)
                result = describe_backup(self.path, status, now=self.now)
                self.assertIn(expected, self.codes(result))
                self.assertNotIn('disk_unknown', self.codes(result))

    def test_cloud_declaration_is_scoped_to_destination_and_corrupt_values_do_not_suppress(self):
        self.configure(self.destination)
        self.declare_cloud()
        self.configure(self.destination+'-new')
        result = describe_backup(self.path, {}, now=self.now)
        self.assertFalse(result['cloud_declared'])
        self.assertIn('disk_unknown', self.codes(result))
        self.configure(self.destination)
        for value in ('{', 'null', '[]', json.dumps({'directory': self.destination})):
            with closing(sqlite3.connect(self.path)) as db, db:
                db.execute('UPDATE settings SET value=? WHERE key=?', (value, CLOUD_KEY))
            self.assertIn('disk_unknown', self.codes(describe_backup(self.path, {}, now=self.now)))

    def test_cloud_confirmation_requires_review_current_path_and_recent_copy(self):
        self.configure(self.destination)
        status = describe_backup(self.path, {}, now=self.now)
        with closing(sqlite3.connect(self.path)) as db:
            for data in ({'directory': self.destination, 'reviewed': True},
                         {'directory': 'other', 'reviewed': True},
                         {'directory': self.destination, 'reviewed': 'true'}):
                with self.subTest(data=data), self.assertRaises(ValidationError):
                    declare_cloud_destination(db, {'id': 1, 'role': 'admin'}, data, status)
            self.assertIsNone(db.execute('SELECT value FROM settings WHERE key=?', (CLOUD_KEY,)).fetchone())

    def test_declaration_from_another_pc_does_not_hide_unknown_disk(self):
        self.configure(self.destination)
        self.declare_cloud()
        with patch('colegio.backup_health.socket.gethostname', return_value='otra-pc'):
            result = describe_backup(self.path, {'secondary_directory': self.destination,
                                     'secondary_at': self.now.isoformat()}, now=self.now)
        self.assertFalse(result['cloud_declared'])
        self.assertIn('disk_unknown', self.codes(result))

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

    def test_same_disk_has_its_own_warning_even_with_recent_successful_copy(self):
        self.configure(self.destination)
        for relation, expected in (({'status':'same'}, 'same_disk'), ({'status':'unknown'}, 'disk_unknown')):
            result = describe_backup(self.path, {'secondary_directory':self.destination,
                'secondary_at':self.now.isoformat()}, now=self.now, disk_relation=relation)
            self.assertEqual(self.codes(result), [expected])

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
        status = response.status
        if response.getheader('Set-Cookie'):
            self.cookie = response.getheader('Set-Cookie').split(';')[0]
        result = json.loads(response.read())
        connection.close()
        self.assertEqual(status, expected, result)
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

    def prepare_cloud_confirmation(self, role='admin'):
        cloud = tempfile.TemporaryDirectory(prefix='aula-cloud-test-')
        self.addCleanup(cloud.cleanup)
        destination = str(Path(cloud.name)/'copies')
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE settings SET value=? WHERE key='backup_directory'", (destination,))
        from tests.crypto_helpers import configure
        if not (self.path.parent/'.backup-crypto'/'keyring.json').exists():configure(self.path.parent)
        self.server.make_backup()
        self.request('login', {'username': role, 'password': 'Prueba-segura-2026'})
        csrf = self.request('session')['user']['csrf']
        self.request('confirm-rate', {'rate': '100', 'rate_date': local_today().isoformat()}, csrf=csrf)
        return destination, csrf

    def test_cloud_declaration_admin_csrf_audit_and_no_schema_or_financial_changes(self):
        destination, csrf = self.prepare_cloud_confirmation()
        with closing(sqlite3.connect(self.path)) as db:
            schema = list(db.execute("SELECT name,sql FROM sqlite_master ORDER BY name"))
            version = db.execute('PRAGMA user_version').fetchone()[0]
            payments = list(db.execute('SELECT * FROM payments'))
        data = {'directory': destination, 'reviewed': True}
        self.request('backup-cloud-declare', data, csrf='', expected=403)
        self.request('backup-cloud-declare', data, csrf=csrf)
        self.assertTrue(self.request('backup-status')['cloud_declared'])
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(list(db.execute("SELECT name,sql FROM sqlite_master ORDER BY name")), schema)
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], version)
            self.assertEqual(list(db.execute('SELECT * FROM payments')), payments)
            entry = db.execute("SELECT user_id,details FROM audit WHERE action='backup_cloud_declaration'").fetchone()
            self.assertIsNotNone(entry[0])
            self.assertFalse(json.loads(entry[1])['upload_checked_by_aula'])
            self.assertEqual(json.loads(entry[1])['before'], {})
        self.request('backup-cloud-declare', {'directory': destination, 'declared': False}, csrf=csrf)
        self.assertFalse(self.request('backup-status')['cloud_declared'])

    def test_cashier_reader_and_demo_cannot_declare_cloud(self):
        for role in ('cashier', 'reader'):
            destination, csrf = self.prepare_cloud_confirmation(role)
            self.request('backup-cloud-declare', {'directory': destination, 'reviewed': True}, csrf=csrf, expected=403)
        destination, csrf = self.prepare_cloud_confirmation()
        self.server.demo = True
        try:
            self.cookie = self.cookie.replace('school_session=', 'school_demo_session=')
            self.request('backup-cloud-declare', {'directory': destination, 'reviewed': True}, csrf=csrf, expected=403)
            self.request('backup-directory', {'backup_directory': ''}, csrf=csrf, expected=403)
        finally:
            self.server.demo = False

    def test_changing_destination_clears_manual_declaration_even_if_reused_later(self):
        destination, csrf = self.prepare_cloud_confirmation()
        self.request('backup-cloud-declare', {'directory': destination, 'reviewed': True}, csrf=csrf)
        settings = {'school_name': 'Mi colegio', 'school_year': local_today().year,
                    'start_month': 9, 'due_day': 10, 'backup_directory': destination+'-new'}
        self.request('settings', settings, csrf=csrf)
        self.assertFalse(self.request('backup-status')['cloud_declared'])
        settings['backup_directory'] = destination
        self.request('settings', settings, csrf=csrf)
        self.assertFalse(self.request('backup-status')['cloud_declared'])
