"""Actual HTTP write attempts, immutable database, portable crypto and source isolation."""
from contextlib import closing
import hashlib
import http.client
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from colegio.db import connect
from colegio.storage import consistent_backup
from colegio.read_only import open_copy


class ReadOnlyCopyTests(unittest.TestCase):
    def setUp(self):
        from tests.test_system import SystemTests
        self.f=SystemTests();self.f.setUp()
        self.f.request('payments',self.f.payment())
        self.source=self.f.path.parent/'copia.sqlite3'
        consistent_backup(self.f.path,self.source)

    def tearDown(self):self.f.tearDown()

    def read_server(self,source=None,credential=None,kind='password'):
        return open_copy(source or self.source,credential,kind)

    def test_all_business_posts_fail_closed_and_neither_source_nor_temporary_ledger_changes(self):
        from tests.permission_matrix import cases
        source_hash=hashlib.sha256(self.source.read_bytes()).hexdigest()
        origin_files={p.name for p in self.source.parent.iterdir()}
        with self.read_server() as server:
            thread=threading.Thread(target=server.serve_forever);thread.start()
            cookie='';csrf=''
            def request(route,body=None):
                nonlocal cookie
                client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
                client.request('GET' if body is None else 'POST',route,json.dumps(body) if body is not None else None,
                    {'Cookie':cookie,'Content-Type':'application/json','X-CSRF-Token':csrf})
                response=client.getresponse();data=response.read()
                if response.getheader('Set-Cookie'):cookie=response.getheader('Set-Cookie').split(';')[0]
                status=response.status;client.close();return status,data
            try:
                self.assertEqual(request('/?view_token='+server.launch)[0],200)
                status,data=request('/api/session');session=json.loads(data);csrf=session['user']['csrf']
                self.assertEqual(session['user']['role'],'reader')
                self.assertIn('solo lectura',session['read_only']['message'])
                status,data=request('/api/state?history=1');before=json.loads(data)
                self.assertEqual(status,200,data)
                saved_hash=hashlib.sha256(Path(server.db_path).read_bytes()).hexdigest()
                for case in cases():
                    if case['method']=='POST' and case['route'] not in ('logout','session-activity'):
                        with self.subTest(route=case['route']):
                            self.assertEqual(request('/api/'+case['route'],case['body'])[0],403)
                for route in ('nueva-ruta-futura','employees','positions','salary-receipts','payroll-plans'):
                    self.assertEqual(request('/api/'+route,{'amount':'1'})[0],403)
                self.assertEqual(request('/api/session-activity',{})[0],200)
                self.assertEqual(request('/api/health')[0],200)
                self.assertEqual(request('/api/daily-report.pdf')[0],200)
                self.assertEqual(request('/api/receipt/1.pdf')[0],200)
                self.assertEqual(request('/api/backup')[0],403)
                after=json.loads(request('/api/state?history=1')[1])
                self.assertEqual(before['charges'],after['charges'])
                self.assertEqual(before['summary'],after['summary'])
                self.assertEqual(saved_hash,hashlib.sha256(Path(server.db_path).read_bytes()).hexdigest())
                with closing(server.connect_view()) as db:
                    with self.assertRaises(sqlite3.OperationalError):db.execute('DELETE FROM payments')
                temporary=Path(server.db_path).parent
                self.assertNotEqual(temporary,self.source.parent)
                self.assertFalse(list(temporary.glob('*-wal')))
                self.assertEqual(request('/api/logout',{})[0],200)
                self.assertEqual(request('/api/state')[0],401)
            finally:server.shutdown();thread.join()
        self.assertFalse(temporary.exists())
        self.assertEqual(source_hash,hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(origin_files,{p.name for p in self.source.parent.iterdir()})

    def test_cipher_password_recovery_wrong_password_corrupt_and_newer_schema(self):
        from colegio.backup_export import write_encrypted
        from tests.crypto_helpers import configure,PASSWORD
        recovery=configure(self.f.path.parent/'foreign-keys')
        cipher=self.f.path.parent/'portatil.aulabak'
        write_encrypted(self.source,cipher,self.f.path.parent/'foreign-keys')
        import shutil
        shutil.rmtree(self.f.path.parent/'foreign-keys')
        # Only archive + credential remain; the originating Windows key store is absent.
        for credential,kind in ((PASSWORD,'password'),(recovery,'recovery')):
            with self.read_server(cipher,credential,kind) as server:
                with closing(server.connect_view()) as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM payments').fetchone()[0],1)
        with self.assertRaises(ValueError):
            with self.read_server(cipher,'incorrecta'):pass
        corrupt=self.f.path.parent/'corrupta.sqlite3';corrupt.write_bytes(b'archivo corrupto')
        with self.assertRaises((ValueError,sqlite3.Error)):
            with self.read_server(corrupt):pass
        newer=self.f.path.parent/'nueva.sqlite3';newer.write_bytes(self.source.read_bytes())
        with closing(sqlite3.connect(newer)) as db,db:db.execute('PRAGMA user_version=999')
        with self.assertRaises(ValueError):
            with self.read_server(newer):pass

    def test_old_published_copy_migrates_only_private_temporary_and_never_generates_charges(self):
        source=Path(__file__).parent/'fixtures/retirement/desktop-1.0.53.sqlite3'
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        with self.read_server(source) as server:
            with closing(server.connect_view()) as db:
                self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='employees'").fetchone())
                from colegio.server import snapshot
                before=db.execute('SELECT COUNT(*) FROM charges').fetchone()[0]
                snapshot(db,{'id':0,'name':'Consulta','role':'reader'})
                self.assertEqual(db.execute('SELECT COUNT(*) FROM charges').fetchone()[0],before)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),digest)
