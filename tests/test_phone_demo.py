import http.client
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

from colegio.desktop import DesktopHost
from colegio.phone_demo import PhoneDemo, private_address


class PhoneDemoTests(unittest.TestCase):
    def test_real_database_and_public_listeners_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with DesktopHost(temp, port=0) as real:
                with self.assertRaises(ValueError): PhoneDemo(real.server, '127.0.0.1', 0)
            for address in ('0.0.0.0', '8.8.8.8', '100.64.0.1', '::', '127.0.0.1'):
                with self.subTest(address=address), self.assertRaises(ValueError): private_address(address)
            self.assertEqual(private_address('192.168.1.10'), '192.168.1.10')

    def test_pairing_origin_csrf_trial_permissions_and_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'colegio.sqlite3').write_bytes(b'base real que no se debe tocar')
            original=(root/'colegio.sqlite3').read_bytes()
            with DesktopHost(root, demo=True, port=0, demo_root=root/'pruebas') as host:
                trial=host.directory
                with PhoneDemo(host.server, '127.0.0.1', 0) as phone:
                    client=http.client.HTTPConnection('127.0.0.1', phone.server_port, timeout=5)
                    cookies=[]
                    def request(path, data=None, *, origin=None, host_header=None, pin=False):
                        headers={'Host':host_header or phone.host,'Cookie':'; '.join(cookies)}
                        if data is not None:
                            headers.update({'Content-Type':'application/x-www-form-urlencoded' if pin else 'application/json',
                                            'Origin':origin or phone.origin})
                        if not pin and data is not None and 'csrf' in locals_csrf:
                            headers['X-CSRF-Token']=locals_csrf['csrf']
                        body=(urlencode(data) if pin else json.dumps(data)) if data is not None else None
                        client.request('POST' if data is not None else 'GET',path,body,headers)
                        response=client.getresponse();payload=response.read()
                        cookie=response.getheader('Set-Cookie')
                        if cookie:cookies.append(cookie.split(';')[0])
                        return response.status,payload,response.getheader('Set-Cookie')
                    locals_csrf={}
                    try:
                        status,body,_=request('/api/session');self.assertEqual(status,401)
                        self.assertNotIn(host.server.demo_token.encode(),body)
                        self.assertEqual(request('/api/session',host_header='evil.example')[0],403)
                        self.assertEqual(request('/pair',{'pin':phone.pin},pin=True,origin='https://evil.example')[0],403)
                        status,_,cookie=request('/pair',{'pin':phone.pin},pin=True)
                        self.assertEqual(status,303);self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie)
                        status,body,_=request('/api/session');self.assertEqual(status,200)
                        self.assertTrue(json.loads(body)['demo'])
                        self.assertEqual(request('/api/demo-login',{})[0],200)
                        session=json.loads(request('/api/session')[1]);locals_csrf['csrf']=session['user']['csrf']
                        gate=json.loads(request('/api/rate-gate')[1]);today=gate['today']
                        self.assertEqual(request('/api/confirm-rate',{'rate_date':today,'rate':'100'},origin='https://evil.example')[0],403)
                        self.assertEqual(request('/api/confirm-rate',{'rate_date':today,'rate':'100'})[0],200)
                        state=json.loads(request('/api/state')[1]);self.assertEqual(state['students'],[])
                        self.assertEqual(state['user']['role'],'admin')
                        self.assertEqual(request('/api/setup',{})[0],400)
                        self.assertEqual(request('/api/backup')[0],403)
                        self.assertEqual(request('/colegio.sqlite3')[0],404)
                    finally:client.close()
            self.assertFalse(trial.exists())
            self.assertEqual((root/'colegio.sqlite3').read_bytes(),original)

    def test_wrong_pin_is_rate_limited_and_never_reveals_the_correct_code(self):
        with tempfile.TemporaryDirectory() as temp:
            with DesktopHost(temp,demo=True,port=0,demo_root=Path(temp)/'pruebas') as host:
                with PhoneDemo(host.server,'127.0.0.1',0) as phone:
                    client=http.client.HTTPConnection('127.0.0.1',phone.server_port,timeout=5)
                    wrong='111111' if phone.pin!='111111' else '222222'
                    try:
                        for index in range(6):
                            client.request('POST','/pair',urlencode({'pin':wrong}),
                                {'Host':phone.host,'Origin':phone.origin,'Content-Type':'application/x-www-form-urlencoded'})
                            response=client.getresponse();body=response.read()
                            self.assertEqual(response.status,429 if index==5 else 400)
                            self.assertNotIn(phone.pin.encode(),body)
                    finally:client.close()
