import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from colegio.demo import DemoWorkspace, MARKER
from colegio.db import local_today


class DemoWorkspaceTests(unittest.TestCase):
    def test_cleanup_only_removes_our_marked_sessions_and_never_an_active_one(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            other=root/'prueba-otras';other.mkdir();(other/'datos.txt').write_text('conservar')
            abandoned=root/'prueba-abandonada';abandoned.mkdir()
            (abandoned/'.aula-pruebas').write_text(MARKER);(abandoned/'colegio.sqlite3').write_bytes(b'prueba')
            with DemoWorkspace(root) as active:
                self.assertFalse(abandoned.exists());self.assertTrue(other.exists())
                (active/'datos.txt').write_text('temporal')
                with self.assertRaises(RuntimeError):
                    with DemoWorkspace(root):pass
                self.assertTrue(active.exists())
            self.assertFalse(active.exists());self.assertEqual((other/'datos.txt').read_text(),'conservar')


class DemoProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()
        self.temporary=self.root/'temporal';self.temporary.mkdir()
        self.real=self.root/'colegio-real';self.real.mkdir()
        self.real_data=self.real/'colegio.sqlite3';self.real_data.write_bytes(b'DATOS REALES: NO MODIFICAR')
        self.process=None;self.log=None;self.cookie=self.csrf=''
        self.cwd=Path(__file__).resolve().parent.parent

    def tearDown(self):
        if self.process and self.process.poll() is None:
            self.process.terminate();self.process.wait(timeout=8)
        if self.log:self.log.close()
        self.assertEqual(self.real_data.read_bytes(),b'DATOS REALES: NO MODIFICAR')
        self.temp.cleanup()

    def start(self):
        if self.log:self.log.close()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]
        env=dict(os.environ,TMPDIR=str(self.temporary),TEMP=str(self.temporary),TMP=str(self.temporary))
        self.log=(self.root/'server.log').open('w')
        self.process=subprocess.Popen([sys.executable,'-u','-m','colegio.server','--demo','--port',str(self.port)],
            cwd=self.cwd,env=env,stdout=self.log,stderr=self.log)
        self.cookie=self.csrf=''
        for _ in range(100):
            if self.process.poll() is not None:self.fail((self.root/'server.log').read_text())
            try:
                session=self.request('session');break
            except OSError:time.sleep(.05)
        else:self.fail('No inició el servidor de pruebas')
        self.assertTrue(session['demo']);self.assertFalse(session['needs_setup'])
        self.token=session['demo_token']
        self.request('demo-login',{})
        self.assertTrue(self.cookie.startswith('school_demo_session='))
        session=self.request('session');self.csrf=session['user']['csrf']
        self.assertEqual(session['user']['role'],'admin')
        self.request('confirm-rate',{'rate_date':local_today().isoformat(),'rate':'100'})
        state=self.request('state');self.path=Path(state['backup']['data_path'])
        self.assertEqual(state['students'],[]);self.assertEqual(state['employees'],[]);self.assertEqual(state['payments'],[])
        self.assertTrue(self.path.is_relative_to(self.temporary))
        return state

    def request(self,path,data=None,status=200,origin=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
        headers={'Cookie':self.cookie,'X-CSRF-Token':self.csrf}
        if data is not None:headers['Content-Type']='application/json'
        if origin:headers['Origin']=origin
        connection.request('GET' if data is None else 'POST','/api/'+path,json.dumps(data) if data is not None else None,headers)
        response=connection.getresponse();payload=response.read()
        cookie=response.getheader('Set-Cookie')
        if cookie:self.cookie=cookie.split(';')[0]
        self.assertEqual(response.status,status,payload.decode(errors='replace'))
        kind=response.getheader('Content-Type');connection.close()
        return json.loads(payload) if 'application/json' in kind else payload

    def add_salary(self):
        position=self.request('positions',{'name':'Docente'})['id']
        employee=self.request('employees',{'name':'Empleado de prueba','document':'V-123','position_id':position,'salary':'120'})['id']
        on=local_today().isoformat()
        return self.request('expenses',dict(employee_id=employee,category='Nómina',concept='Sueldo de prueba',
            spent_on=on,amount='12000',currency='VES',method='Transferencia',period_start=on[:7]+'-01',
            period_end=on,entry_time='07:00',exit_time='13:00'))

    def test_admin_salary_is_isolated_marked_and_deleted_on_explicit_close(self):
        state=self.start();payment=self.add_salary();folder=self.path.parent
        receipt=self.request('salary-receipt/'+str(payment['salary_receipt_id']))
        self.assertTrue(receipt['demo']);self.assertTrue(receipt['school']['legal_name'].startswith('PRUEBA SIN VALIDEZ'))
        pdf=self.request('salary-receipt/'+str(payment['salary_receipt_id'])+'.pdf')
        self.assertTrue(pdf.startswith(b'%PDF'));self.assertIn(b'PRUEBA SIN VALIDEZ',pdf)
        self.request('backup',status=403)
        self.request('reset-preview',status=403)
        self.request('reset-records',{},status=400)
        self.request('settings',{**state['settings'],'backup_directory':str(self.real)},status=400)
        self.assertFalse((folder/'backups').exists())
        self.request('demo-exit',{})
        self.assertEqual(self.process.wait(timeout=8),0);self.assertFalse(folder.exists())
        self.start();self.assertEqual(self.request('state')['expenses'],[])

    def test_forced_kill_is_cleaned_before_the_next_empty_session(self):
        self.start();self.add_salary();abandoned=self.path.parent
        self.process.kill();self.process.wait(timeout=5)
        self.assertTrue(abandoned.exists())
        self.start();self.assertFalse(abandoned.exists());self.assertEqual(self.request('state')['expenses'],[])

    def test_close_waits_for_last_tab_and_refresh_reopens_the_lease(self):
        self.start();folder=self.path.parent
        def presence(client,action):self.request('demo-presence',dict(token=self.token,client=client,action=action))
        presence('primera','alive');presence('segunda','alive');presence('primera','close')
        time.sleep(5.5);self.assertIsNone(self.process.poll())
        presence('segunda','close');presence('segunda','alive')
        time.sleep(5.5);self.assertIsNone(self.process.poll())
        self.request('demo-presence',dict(token='incorrecto',client='segunda',action='close'),status=403)
        self.request('demo-presence',dict(token=self.token,client='segunda',action='close'),status=403,origin='https://otro.example')
        presence('segunda','close');self.assertEqual(self.process.wait(timeout=8),0);self.assertFalse(folder.exists())

    def test_demo_rejects_a_production_data_directory_before_opening_it(self):
        result=subprocess.run([sys.executable,'-m','colegio.server','--demo','--data-dir',str(self.real)],
                              cwd=self.cwd,capture_output=True,text=True,timeout=5)
        self.assertNotEqual(result.returncode,0);self.assertIn('--demo no admite --data-dir',result.stderr)
        self.assertEqual(list(self.real.iterdir()),[self.real_data])
