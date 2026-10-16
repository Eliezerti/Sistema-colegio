"""Retired private access cannot be activated; local security remains enforced."""
import http.client
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from colegio.network import PrivateAccess, save_config
from colegio.server import SchoolServer, open_school

ORIGIN='https://colegio.red-prueba.ts.net'

class LocalAccessTests(unittest.TestCase):
    def test_remote_activation_rejected_before_touching_data(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'colegio.sqlite3'
            with self.assertRaises(ValueError):
                with open_school(path,0,remote_origin=ORIGIN):pass
            self.assertFalse(path.exists())
            with self.assertRaises(ValueError):save_config(temp,ORIGIN)
            self.assertFalse((Path(temp)/'red.json').exists())
            with self.assertRaises(ValueError):PrivateAccess(ORIGIN)
            with self.assertRaises(ValueError):SchoolServer(('0.0.0.0',0),str(path))
            with self.assertRaises(ValueError):SchoolServer(('127.0.0.1',0),str(path),remote_origin=ORIGIN)

    def test_retired_cli_flags_fail_without_creating_database(self):
        with tempfile.TemporaryDirectory() as temp:
            for flag in ('--remote-origin','--network-config'):
                result=subprocess.run([sys.executable,'-m','colegio.server','--data-dir',temp,flag,ORIGIN],
                    capture_output=True,text=True,timeout=5)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('acceso privado fue retirado',result.stderr)
            self.assertFalse((Path(temp)/'colegio.sqlite3').exists())

    def test_host_origin_and_forwarded_headers_cannot_expand_access(self):
        from tests.test_system import SystemTests
        f=SystemTests();f.setUp()
        try:
            def request(host,origin=None,post=False):
                client=http.client.HTTPConnection('127.0.0.1',f.server.server_port,timeout=5)
                headers={'Host':host,'X-Forwarded-Proto':'https','Content-Type':'application/json'}
                if origin:headers['Origin']=origin
                client.request('POST' if post else 'GET','/api/login' if post else '/api/session',
                    json.dumps({'username':'admin','password':'Una-clave-segura'}) if post else None,headers)
                response=client.getresponse();response.read();status=response.status;client.close();return status
            local='127.0.0.1:'+str(f.server.server_port)
            self.assertEqual(request(local),200)
            self.assertEqual(request('colegio.red-prueba.ts.net'),403)
            self.assertEqual(request(local,ORIGIN,True),403)
            self.assertEqual(request('evil.example'),403)
            self.assertEqual(f.request('session')['user']['username'],'admin')
        finally:f.tearDown()
