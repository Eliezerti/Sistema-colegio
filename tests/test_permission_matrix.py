"""Every discovered desktop API/action has a role contract tested through HTTP."""
import http.client
import json
import unittest

from colegio.db import local_today
from tests.permission_matrix import cases, endpoint_inventory, write_report


class PermissionMatrixTests(unittest.TestCase):
    def test_discovered_endpoints_have_explicit_contracts(self):
        self.assertEqual(endpoint_inventory(), {r['key'] for r in cases()})

    def test_roles_anonymous_and_csrf_match_independent_contract(self):
        from tests.test_system import SystemTests
        f = SystemTests('test_security_roles_csrf_origins_and_login')
        f.setUp()
        records = []
        try:
            for role in ('cashier','reader'):
                f.request('users', dict(name=role, username=role, role=role, password='FICTICIO-perfil-seguro'))
            for role in ('admin','cashier','reader','anonymous'):
                if role != 'admin':
                    f.request('logout', {})
                    if role != 'anonymous':
                        f.request('login', dict(username=role, password='FICTICIO-perfil-seguro'))
                        f.csrf = f.request('session')['user']['csrf']
                        f.request('confirm-rate', dict(rate_date=local_today().isoformat(), rate='100'))
                for case in sorted(cases(), key=lambda c:c['route']=='logout'):
                    route = case['route']
                    method = case['method']
                    public = case['key'] in ('session','setup','login','demo-login','demo-presence')
                    expected = case['success'] if role in case['roles'] else 401 if role=='anonymous' and not public else 403
                    def send(csrf, expected):
                        connection = http.client.HTTPConnection('127.0.0.1', f.server.server_port, timeout=30)
                        headers = {'Cookie': f.cookie if role!='anonymous' else '', 'Content-Type':'application/json'}
                        if csrf: headers['X-CSRF-Token'] = f.csrf
                        connection.request(method, '/api/'+route, json.dumps(case['body']) if method=='POST' else None, headers)
                        response = connection.getresponse(); status = response.status; content=response.read()
                        connection.close()
                        records.append(dict(method=method, route=route, role=role, csrf=bool(csrf), expected=expected, actual=status))
                        self.assertEqual(status, expected, (method, route, role, bool(csrf), content.decode(errors='replace')))
                    with self.subTest(role=role, route=route, method=method):
                        if method=='POST' and not public and role!='anonymous': send(False, 403)
                        send(True, expected)
                    # Logout revokes the current session; relogin is needed for the next profile loop.
                    if route=='logout' and role!='anonymous':
                        f.cookie = ''
                        f.request('login', dict(username='admin', password='Una-clave-segura'))
                        f.csrf = f.request('session')['user']['csrf']
            write_report(records, endpoint_inventory())
        finally:
            f.tearDown()
