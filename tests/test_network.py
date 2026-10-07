import http.client
import json
import subprocess
import sys
import tempfile
import unittest
import sqlite3
import time
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tests import test_system
from colegio.db import local_today, initialize, connect, hash_password
from colegio.network import PrivateAccess, private_origin, save_config, load_config
from colegio.server import SchoolServer


ORIGIN='https://colegio.red-prueba.ts.net'
HOST='colegio.red-prueba.ts.net'


class PrivateNetworkConfigTests(unittest.TestCase):
    def test_only_accepts_private_https_origin_without_credentials_or_routes(self):
        self.assertEqual(private_origin(ORIGIN+'/' ),ORIGIN)
        self.assertEqual(private_origin(ORIGIN+':443'),ORIGIN)
        for value in ('http://'+HOST,'https://example.com','https://ts.net','https://maliciousts.net',
                      ORIGIN+':8080',ORIGIN+'/api/',ORIGIN+'?secret=x',ORIGIN+'#fragment',
                      'https://admin:password@'+HOST,'https://a..ts.net','https://a.b.ts.net.evil.example',None):
            with self.subTest(value=value),self.assertRaises(ValueError):private_origin(value)

    def test_config_roundtrip_never_initializes_or_copies_a_database(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);data=directory/'colegio.sqlite3';data.write_bytes(b'conservar')
            path=save_config(directory,ORIGIN);self.assertEqual(load_config(path),ORIGIN)
            self.assertEqual(data.read_bytes(),b'conservar');self.assertFalse((directory/'red.tmp').exists())
            path.write_text('{"version":1,"remote_origin":"https://public.example"}')
            with self.assertRaises(ValueError):load_config(path)

    def test_never_opens_a_public_listener_or_shares_demo_data(self):
        with self.assertRaises(ValueError):SchoolServer(('0.0.0.0',0),'unused.sqlite3',remote_origin=ORIGIN)
        with self.assertRaises(ValueError):SchoolServer(('127.0.0.1',0),'unused.sqlite3',demo=True,remote_origin=ORIGIN)

    def test_cli_refuses_remote_bootstrap_and_network_demo(self):
        root=Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as temp:
            result=subprocess.run([sys.executable,'-m','colegio.server','--data-dir',temp,'--remote-origin',ORIGIN,'--port','0'],
                                  cwd=root,capture_output=True,text=True,timeout=5)
            self.assertNotEqual(result.returncode,0);self.assertIn('Crea primero tu administrador',result.stderr)
        result=subprocess.run([sys.executable,'-m','colegio.server','--demo','--remote-origin',ORIGIN],
                              cwd=root,capture_output=True,text=True,timeout=5)
        self.assertNotEqual(result.returncode,0);self.assertIn('El modo de prueba es local',result.stderr)

    def test_cli_network_config_opens_existing_base_with_secure_remote_login(self):
        root=Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'colegio.sqlite3';initialize(path)
            with closing(connect(path)) as db,db:
                db.execute('INSERT INTO users(username,name,password,role) VALUES(?,?,?,?)',
                           ('admin','Administradora existente',hash_password('Una-clave-segura'),'admin'))
                db.execute("INSERT INTO guardians(name,document) VALUES('Representante existente','V-456')")
            config=save_config(temp,ORIGIN)
            log_path=Path(temp)/'server.log'
            with log_path.open('w') as log:
                process=subprocess.Popen([sys.executable,'-u','-m','colegio.server','--data-dir',temp,
                                          '--network-config',str(config),'--port','0'],cwd=root,stdout=log,stderr=log)
                try:
                    for _ in range(60):
                        output=log_path.read_text()
                        if 'abierto en http://127.0.0.1:' in output:break
                        if process.poll() is not None:self.fail(output)
                        time.sleep(0.05)
                    self.assertIn('abierto en http://127.0.0.1:',output)
                    port=int(output.split('abierto en http://127.0.0.1:',1)[1].split()[0])
                    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
                    try:
                        connection.request('POST','/api/login',json.dumps({'username':'admin','password':'Una-clave-segura'}),
                                           {'Host':HOST,'Origin':ORIGIN,'Content-Type':'application/json'})
                        response=connection.getresponse();payload=response.read()
                        self.assertEqual(response.status,200,payload)
                        cookie=response.getheader('Set-Cookie');self.assertIn('; Secure',cookie)
                        connection.request('GET','/api/session',headers={'Host':HOST,'Cookie':cookie.split(';')[0]})
                        response=connection.getresponse();session=json.loads(response.read())
                        self.assertEqual(response.status,200);self.assertEqual(session['user']['name'],'Administradora existente')
                    finally:connection.close()
                finally:
                    process.terminate()
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
            with closing(connect(path)) as db:
                self.assertEqual(db.execute("SELECT name FROM guardians WHERE document='V-456'").fetchone()[0],'Representante existente')
                self.assertEqual(db.execute('SELECT COUNT(*) FROM users').fetchone()[0],1)


class PrivateNetworkSystemTests(unittest.TestCase):
    tearDown=test_system.SystemTests.tearDown
    request=test_system.SystemTests.request
    student_data=test_system.SystemTests.student_data
    payment=test_system.SystemTests.payment

    def setUp(self):
        test_system.SystemTests.setUp(self)
        self.server.access=PrivateAccess(ORIGIN)

    def remote(self,path,data=None,*,cookie='',csrf='',host=HOST,origin=ORIGIN,status=200,forwarded_proto=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=10)
        headers={'Host':host,'Cookie':cookie,'X-CSRF-Token':csrf}
        if data is not None:
            headers['Content-Type']='application/json'
            if origin is not None:headers['Origin']=origin
        if forwarded_proto:headers['X-Forwarded-Proto']=forwarded_proto
        connection.request('GET' if data is None else 'POST','/api/'+path,json.dumps(data) if data is not None else None,headers)
        response=connection.getresponse();payload=response.read();set_cookie=response.getheader('Set-Cookie')
        self.assertEqual(response.status,status,payload.decode(errors='replace'))
        kind=response.getheader('Content-Type');connection.close()
        return (json.loads(payload) if 'application/json' in kind else payload),set_cookie

    def login(self,username='admin',password='Una-clave-segura',**headers):
        _,cookie=self.remote('login',{'username':username,'password':password},**headers)
        self.assertIn('; Secure',cookie);self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie)
        cookie=cookie.split(';')[0]
        session,_=self.remote('session',cookie=cookie,**headers)
        csrf=session['user']['csrf']
        self.remote('confirm-rate',{'rate_date':local_today().isoformat(),'rate':'100'},cookie=cookie,csrf=csrf,**headers)
        return cookie,csrf

    def test_https_host_and_loopback_rewrite_both_preserve_secure_sessions(self):
        cookie,csrf=self.login()
        state,_=self.remote('state',cookie=cookie)
        self.assertEqual(state['access'],{'mode':'private-network','remote_url':ORIGIN})
        self.assertEqual(state['students'][0]['id'],self.student)
        self.login(host=f'127.0.0.1:{self.server.server_port}',forwarded_proto='https')
        self.login(host=HOST+':443')

    def test_untrusted_hosts_origins_and_missing_csrf_are_blocked(self):
        self.remote('session',host='otro.red-prueba.ts.net',status=403)
        self.remote('login',{'username':'admin','password':'Una-clave-segura'},origin='https://otro.red-prueba.ts.net',status=403)
        self.remote('login',{'username':'admin','password':'Una-clave-segura'},origin='http://'+HOST,status=403)
        cookie,csrf=self.login()
        self.remote('payments',self.payment(),cookie=cookie,csrf='',status=403)
        self.assertEqual(self.request('state')['payments'],[])

    def test_reader_cannot_collect_payments_or_change_school_settings_remotely(self):
        self.request('users',{'name':'Consulta remota','username':'lectura','password':'Consulta-segura','role':'reader'})
        cookie,csrf=self.login('lectura','Consulta-segura')
        state,_=self.remote('state',cookie=cookie);self.assertEqual(state['user']['role'],'reader')
        self.remote('payments',self.payment(),cookie=cookie,csrf=csrf,status=403)
        self.remote('settings',state['settings'],cookie=cookie,csrf=csrf,status=403)
        self.remote('reset-preview',cookie=cookie,status=403)

    def test_two_cashiers_share_balance_and_keep_distinct_operators_and_retries(self):
        users=[]
        for i in (1,2):
            user_id=self.request('users',{'name':f'Caja {i}','username':f'caja{i}','password':'Caja-segura-2026','role':'cashier'})['id']
            cookie,csrf=self.login(f'caja{i}','Caja-segura-2026');users.append((user_id,cookie,csrf))
        before=self.request('state')['students'][0]['balance']
        def collect(i):
            uid,cookie,csrf=users[i]
            data=self.payment(amount='5',key=f'central-caja-{i}',reference=f'REF-{i}')
            result,_=self.remote('payments',data,cookie=cookie,csrf=csrf)
            retried,_=self.remote('payments',data,cookie=cookie,csrf=csrf)
            self.assertTrue(retried['duplicate']);self.assertEqual(result['id'],retried['id'])
            return result['id']
        with ThreadPoolExecutor(max_workers=2) as pool:ids=list(pool.map(collect,(0,1)))
        self.assertEqual(len(set(ids)),2)
        for _,cookie,_ in users:
            state,_=self.remote('state',cookie=cookie)
            self.assertEqual(state['students'][0]['balance'],before-1000)
            self.assertEqual(len(state['payments']),2)
            self.assertEqual({p['operator'] for p in state['payments']},{'Caja 1','Caja 2'})
        # Both committed remote payments are included in the regular verified backup.
        path=self.path.parent/'network-snapshot.sqlite3';path.write_bytes(self.request('backup'))
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM payments').fetchone()[0],2)

    def test_default_local_mode_remains_closed_to_private_proxy_hosts(self):
        self.server.access=PrivateAccess()
        self.remote('session',status=403)
        self.remote('login',{'username':'admin','password':'Una-clave-segura'},host=f'127.0.0.1:{self.server.server_port}',status=403)
        self.assertEqual(self.request('session')['user']['username'],'admin')
