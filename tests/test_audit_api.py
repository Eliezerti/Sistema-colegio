"""Administrator audit exports and read-only recovery gates."""
import json
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from colegio.db import connect, audit, local_today


class AuditAPITests(unittest.TestCase):
    def setUp(self):
        from tests.test_system import SystemTests
        self.f = SystemTests('test_security_roles_csrf_origins_and_login')
        self.f.setUp()

    def tearDown(self):
        self.f.tearDown()

    def test_admin_filtered_csv_pdf_and_permission_denial_for_cashier_reader(self):
        f = self.f
        f.request('guardians', {'id':1, 'name':'Ana editada', 'document':'V-123', 'phone':'04120000000','email':'','address':''})
        data = f.request('audit?search=edit-values')
        self.assertTrue(data['status']['ok'])
        self.assertTrue(any('Ana editada' in r['details'] for r in data['entries']))
        self.assertIn(b'edit-values', f.request('audit.csv?search=edit-values'))
        self.assertTrue(f.request('audit.pdf?search=edit-values').startswith(b'%PDF'))
        f.request('audit?from=fecha-mala', status=400)
        for role in ('cashier','reader'):
            f.request('users', {'name':role,'username':role,'password':'Una-clave-segura','role':role})
            f.request('logout', {})
            f.request('login', {'username':role,'password':'Una-clave-segura'})
            f.csrf=f.request('session')['user']['csrf']
            for endpoint in ('audit','audit.csv','audit.pdf'): f.request(endpoint,status=403)
            f.request('logout', {})
            f.request('login', {'username':'admin','password':'Una-clave-segura'})
            f.csrf=f.request('session')['user']['csrf']
            f.request('confirm-rate',{'rate_date':local_today().isoformat(),'rate':'100'})

    def test_corrupt_audit_blocks_mutations_but_allows_login_state_export_and_local_backup(self):
        f=self.f
        with closing(sqlite3.connect(f.path)) as db, db:
            db.execute('DROP TRIGGER audit_guard_audit_update')
            db.execute("UPDATE audit SET details='alterado' WHERE id=1")
        before=None
        with closing(connect(f.path)) as db: before=db.execute('SELECT COUNT(*) FROM charges').fetchone()[0]
        state=f.request('state');self.assertFalse(state['audit_status']['ok'])
        f.request('grades', {'name':'Impedir','capacity':30}, status=409)
        f.request('generate', {'period':'2027-01'}, status=409)
        f.request('payments',f.payment(),status=409)
        self.assertFalse(f.request('maintenance-review')['ok'])
        self.assertFalse(f.request('audit')['status']['ok'])
        self.assertTrue(f.request('audit.pdf').startswith(b'%PDF'))
        f.request('logout',{})
        f.request('login',{'username':'admin','password':'Una-clave-segura'})
        f.csrf=f.request('session')['user']['csrf']
        self.assertFalse(f.request('rate-gate')['audit_status']['ok'])
        self.assertFalse(f.request('state')['audit_status']['ok'])
        with closing(connect(f.path)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM charges').fetchone()[0],before)
        result=f.request('backup-now',{})
        self.assertTrue(Path(result['local_path']).exists())

    def test_csv_formula_injection_is_escaped_and_secrets_redacted(self):
        from colegio.audit_reports import csv_bytes, report
        with closing(connect(self.f.path)) as db, db:
            db.execute("UPDATE users SET name='=HYPERLINK(\"malicioso\")' WHERE id=1")
            audit(db,1,'=HYPERLINK("malicioso")',{'password':'no-exportar','bank_account':'0123456789','visible':'bien'})
        with closing(connect(self.f.path)) as db:
            data=report(db,{'search':['HYPERLINK']},{'name':'Prueba'})
            content=csv_bytes(data)
        self.assertIn(b"'=HYPERLINK",content)
        self.assertNotIn(b'no-exportar',content)
        self.assertNotIn(b'0123456789',content)

    def test_old_mixed_actor_details_do_not_prevent_admin_state_and_exports(self):
        with closing(connect(self.f.path)) as db,db:
            audit(db,None,'detalle-antiguo',{'actor':'Cuenta antigua','responsable':None,'dato':'conservar'})
        self.assertTrue(self.f.request('state')['audit_status']['ok'])
        result=self.f.request('audit?search=detalle-antiguo')
        self.assertEqual(len(result['entries']),1)
        self.assertIn('conservar',result['entries'][0]['details'])
        self.assertTrue(self.f.request('audit.pdf?search=detalle-antiguo').startswith(b'%PDF'))
