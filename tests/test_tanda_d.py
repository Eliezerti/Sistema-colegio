"""Tanda D contracts: privacy, startup calendar and unchanged historical expenses."""
from contextlib import closing
from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from colegio.db import initialize,connect,local_today
from colegio.server import SchoolServer,snapshot

class CleanupTests(unittest.TestCase):
    def test_default_school_year_uses_current_date(self):
        for today,expected in ((date(2027,1,2),'2026'),(date(2027,9,1),'2027')):
            with self.subTest(today=today),tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'colegio.sqlite3'
                with patch('colegio.db.local_today',return_value=today):initialize(path)
                with closing(connect(path)) as db:
                    self.assertEqual(dict(db.execute('SELECT key,value FROM settings'))['school_year'],expected)

    def test_floors_private_for_every_profile_and_preserved_in_database(self):
        from tests.test_system import SystemTests
        f=SystemTests();f.setUp()
        try:
            with closing(connect(f.path)) as db:
                before=dict(db.execute("SELECT key,value FROM settings WHERE key LIKE 'id_floor_%'"))
                for role in ('admin','cashier','reader'):
                    data=snapshot(db,{'id':1,'role':role,'name':'Prueba'})
                    self.assertFalse(any(k.startswith('id_floor_') for k in data['settings']))
                self.assertEqual(before,dict(db.execute("SELECT key,value FROM settings WHERE key LIKE 'id_floor_%'")))
        finally:f.tearDown()

    def test_historical_payroll_expense_preserved_but_new_rejected(self):
        from tests.test_system import SystemTests
        f=SystemTests();f.setUp()
        try:
            body=dict(concept='Gasto ficticio',category='Operación',spent_on=local_today().isoformat(),
                amount='12.34',currency='USD',method='Efectivo')
            expense=f.request('expenses',body)['id']
            with closing(connect(f.path)) as db,db:
                db.execute("UPDATE expenses SET category='Nómina' WHERE id=?",(expense,))
            before=f.request('state');cash=f.request('cash-preview');daily=f.request('daily-report')
            for category in ('Nómina',' NOMINA ','nómina'):
                f.request('expenses',dict(body,category=category),status=400)
            after=f.request('state')
            self.assertEqual(before['summary'],after['summary'])
            self.assertEqual(before['expenses'],after['expenses'])
            self.assertEqual(cash,f.request('cash-preview'))
            self.assertEqual(daily['summaries'],f.request('daily-report')['summaries'])
        finally:f.tearDown()

    def test_installer_has_explicit_user_guides_and_preserves_internal_sources(self):
        root=Path(__file__).resolve().parents[1]
        recipe=(root/'packaging/Aula.iss').read_text()
        self.assertNotIn('docs\\*.html',recipe)
        self.assertNotIn('retiro-personal-inventario',recipe)
        self.assertTrue((root/'docs/retiro-personal-inventario.md').is_file())
        self.assertIn('retiro-personal-inventario.html',(root/'packaging/retired-files.iss').read_text())
