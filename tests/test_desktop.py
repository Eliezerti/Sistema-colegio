from tests.audit_helpers import legacy_fixture
import http.client
import json
import os
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from colegio.desktop import DesktopHost, WindowsInstance, data_directory, read_desktop_config, write_desktop_config
from colegio.db import connect, initialize, hash_password
from colegio.storage import DataLock
from colegio.branding import SCHOOL_NAME, INSTITUTION_TYPE, SCHOOL_PROFILE


class DesktopTests(unittest.TestCase):
    def test_retired_phone_flags_rejected_before_opening_data(self):
        from colegio.desktop import main
        import contextlib
        import io
        for flag in ('--demo-phone', '--self-test-phone'):
            with patch('sys.argv', ['Aula', flag]), patch('colegio.desktop.data_directory') as directory:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    main()
                self.assertEqual(error.exception.code, 2)
                directory.assert_not_called()

    @unittest.skipUnless(os.name=='nt','El mutex y enfoque de ventanas se validan en Windows.')
    def test_windows_mutex_prevents_second_real_instance_and_allows_separate_trial(self):
        with WindowsInstance() as first:
            self.assertTrue(first)
            with WindowsInstance() as second:self.assertFalse(second)
            with WindowsInstance(demo=True) as trial:self.assertTrue(trial)
        with WindowsInstance() as restarted:self.assertTrue(restarted)

    def test_default_path_matches_existing_windows_data_and_client_config_never_creates_db(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'LOCALAPPDATA':temp}):
            directory=data_directory();self.assertEqual(directory,Path(temp)/'AulaColegio')
            for url in ('https://colegio.red.ts.net','http://colegio.red.ts.net',''):
                with self.assertRaises(ValueError):write_desktop_config(directory,'client',url)
            self.assertFalse((directory/'colegio.sqlite3').exists())
            self.assertIsNone(read_desktop_config(directory))

    def test_network_configuration_preserves_records_and_cannot_change_while_serving(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);path=directory/'colegio.sqlite3';initialize(path)
            with closing(connect(path)) as db,db:
                db.execute('INSERT INTO users(name,username,password,role) VALUES(?,?,?,?)',
                           ('Directora','admin',hash_password('Una-clave-segura'),'admin'))
                db.execute("INSERT INTO guardians(name,document) VALUES('Representante real','V-222')")
            write_desktop_config(directory,'primary')
            with DesktopHost(directory,port=0) as host:
                self.assertEqual(host.server.access.origin,'')
                self.assertFalse(host.server.daemon_threads)
                with self.assertRaises(RuntimeError):write_desktop_config(directory,'primary','')
                with self.assertRaises(RuntimeError):DataLock(directory)
                connection=http.client.HTTPConnection('127.0.0.1',host.server.server_port,timeout=5)
                connection.request('GET','/api/session');response=connection.getresponse()
                self.assertEqual(response.status,200);self.assertFalse(json.loads(response.read())['needs_setup']);connection.close()
                thread=host.thread
            self.assertFalse(thread.is_alive())
            with DataLock(directory),closing(connect(path)) as db:
                self.assertEqual(db.execute('PRAGMA quick_check').fetchone()[0],'ok')
                self.assertEqual(db.execute('SELECT name FROM guardians').fetchone()[0],'Representante real')
            self.assertTrue(list((directory/'backups').glob('*.sqlite3')))

    def test_first_local_open_serves_bundled_app_and_never_requires_webview_in_backend(self):
        with tempfile.TemporaryDirectory() as temp:
            with DesktopHost(temp,port=0) as host:
                connection=http.client.HTTPConnection('127.0.0.1',host.server.server_port,timeout=5)
                for route,expected in (('/',b'<title>'),('/aula-app.png',b'\x89PNG'),('/app.js',b'async function api')):
                    connection.request('GET',route);response=connection.getresponse()
                    self.assertEqual(response.status,200);self.assertIn(expected,response.read())
                connection.close()
            with DesktopHost(temp,port=0) as host:self.assertTrue(host.thread.is_alive())

    def test_demo_closes_and_deletes_its_data_without_touching_real_records_or_profiles(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)/'AulaColegio';directory.mkdir();path=directory/'colegio.sqlite3';path.write_bytes(b'no modificar')
            (directory/'escritorio.json').write_text(json.dumps({'version':1,'mode':'client',
                'remote_url':'https://colegio.red.ts.net'}))
            with patch('tempfile.gettempdir',return_value=temp):
                with DesktopHost(directory,demo=True,port=0) as host:
                    disposable=host.directory
                    self.assertNotEqual(disposable,directory);self.assertTrue(host.server.demo)
                    self.assertEqual(host.server.access.origin,'')
                    with closing(connect(disposable/'colegio.sqlite3')) as db:
                        self.assertEqual(db.execute("SELECT role FROM users WHERE username='__prueba__'").fetchone()[0],'admin')
                    (disposable/'webview').mkdir();(disposable/'webview'/'cookies').write_text('temporales')
                self.assertFalse(disposable.exists())
            self.assertEqual(path.read_bytes(),b'no modificar')
            self.assertEqual(read_desktop_config(directory)['mode'],'client')

    def test_invalid_configuration_requires_repair_instead_of_silently_creating_empty_system(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'escritorio.json'
            for value in ('not json','[]','{"version":1,"mode":"client","remote_url":"https://evil.example"}'):
                path.write_text(value)
                with self.assertRaises(ValueError):read_desktop_config(temp)
            self.assertFalse((Path(temp)/'colegio.sqlite3').exists())

    def test_full_institution_name_migration_preserves_fiscal_name_custom_edits_and_old_documents(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'colegio.sqlite3';initialize(path)
            with closing(connect(path)) as db,db:
                settings=dict(db.execute('SELECT key,value FROM settings'))
                self.assertEqual(settings['school_name'],'Mi colegio')
                self.assertEqual(settings['institution_type'],INSTITUTION_TYPE)
                self.assertEqual(settings['legal_name'],'')
                db.executemany('UPDATE settings SET value=? WHERE key=?',[(v,k) for k,v in SCHOOL_PROFILE.items()])
                db.execute("UPDATE settings SET value='Identidad configurada' WHERE key='school_name'")
                db.execute("DELETE FROM settings WHERE key='institution_type'")
                legacy_fixture(db)
                db.execute('PRAGMA user_version=6')
            initialize(path)
            with closing(connect(path)) as db,db:
                self.assertEqual(dict(db.execute('SELECT key,value FROM settings'))['school_name'],'Identidad configurada')
                db.execute("UPDATE settings SET value='Nombre editado por administración' WHERE key='school_name'")
                db.execute("UPDATE settings SET value='Tipo editado' WHERE key='institution_type'")
            initialize(path)
            with closing(connect(path)) as db:
                settings=dict(db.execute('SELECT key,value FROM settings'))
                self.assertEqual(settings['school_name'],'Nombre editado por administración')
                self.assertEqual(settings['institution_type'],'Tipo editado')
                self.assertEqual(settings['legal_name'],SCHOOL_PROFILE['legal_name'])
