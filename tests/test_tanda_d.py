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

class LocalLoginTests(unittest.TestCase):
    def test_admin_recovers_during_attack_without_weakening_throttle_or_other_user(self):
        from tests.test_system import SystemTests
        from colegio.local_login import issue
        f=SystemTests();f.setUp()
        try:
            f.request('users',dict(name='Caja',username='caja',password='Otra-clave-ficticia',role='cashier'))
            for _ in range(5):f.request('login',dict(username='admin',password='incorrecta'),status=401)
            f.request('login',dict(username='admin',password='Una-clave-segura'),status=429)
            f.request('login',dict(username='caja',password='Otra-clave-ficticia'))
            with self.assertRaises(ValueError):issue(f.path.parent,'caja','Otra-clave-ficticia')
            with self.assertRaises(ValueError):issue(f.path.parent,'admin','incorrecta')
            code=issue(f.path.parent,'admin','Una-clave-segura')
            f.request('login',dict(username='admin',password='Una-clave-segura',local_unlock_code='0'*32),status=429)
            # Ordinary slots can be saturated without occupying the local recovery slot.
            f.server.login_limiter.checks.acquire();f.server.login_limiter.checks.acquire()
            try:f.request('login',dict(username='admin',password='Una-clave-segura',local_unlock_code=code))
            finally:f.server.login_limiter.checks.release();f.server.login_limiter.checks.release()
            f.csrf=f.request('session')['user']['csrf']
            f.request('confirm-rate',dict(rate_date=local_today().isoformat(),rate='100'))
            with closing(connect(f.path)) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE action='local_login_unlocked'").fetchone()[0],1)
                from colegio.audit_chain import local_status
                self.assertTrue(local_status(db)['ok'])
            for _ in range(5):f.request('login',dict(username='admin',password='incorrecta'),status=401)
            f.request('login',dict(username='admin',password='Una-clave-segura',local_unlock_code=code),status=429)
        finally:f.tearDown()

    def test_code_expiration_is_monotonic_and_restart_invalidates_grant(self):
        from tests.test_system import SystemTests
        from colegio.local_login import issue,consume,begin_instance
        f=SystemTests();f.setUp()
        try:
            with patch('colegio.local_login.time.monotonic',return_value=100):
                code=issue(f.path.parent,'admin','Una-clave-segura')
            with patch('time.time',return_value=0),patch('colegio.local_login.time.monotonic',return_value=221):
                self.assertFalse(consume(f.path.parent,f.server.login_instance,'admin',code))
            code=issue(f.path.parent,'admin','Una-clave-segura')
            identifier=begin_instance(f.path.parent)
            self.assertFalse(consume(f.path.parent,identifier,'admin',code))
        finally:f.tearDown()

class PrincipalTests(unittest.TestCase):
    def test_projection_keeps_complete_totals_and_bounds_history(self):
        from tests.test_system import SystemTests
        from colegio.state_view import principal
        f=SystemTests();f.setUp()
        try:
            f.request('payments',f.payment())
            before=f.request('state')
            projected=principal(before)
            self.assertEqual(projected['summary'],before['summary'])
            self.assertFalse(projected['history_loaded'])
            self.assertEqual(projected['counts']['charges'],len(before['charges']))
            self.assertEqual(projected['charges'],[])
            # The real endpoint defaults to principal; explicit history is complete.
            actual=f.request('state?history=0')
            self.assertFalse(actual['history_loaded'])
            self.assertEqual(actual['summary'],before['summary'])
            self.assertEqual(actual['dashboard']['income'],sum(p['amount'] for p in before['payments'] if not p['voided'] and p['paid_on']==before['today']))
            self.assertEqual(before['charges'],f.request('state')['charges'])
        finally:f.tearDown()

class BackupLevelsTests(unittest.TestCase):
    def test_levels_are_bounded_and_permanent_copies_never_rotated(self):
        from colegio.backup_tiers import retain_levels
        from colegio.backup_crypto import MAGIC
        from datetime import timedelta
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);source=directory/'verified.aulabak';source.write_bytes(MAGIC+b'fictional-ciphertext')
            permanent=directory/'aula-cierre-2026-2027-unica.aulabak';permanent.write_bytes(source.read_bytes())
            for n in range(26):retain_levels(source,directory,today=date(2020+n//12,n%12+1,1))
            for n in range(62):retain_levels(source,directory,today=date(2023,1,1)+timedelta(days=n))
            self.assertEqual(len(list(directory.glob('aula-diario-*.aulabak'))),60)
            self.assertEqual(len(list(directory.glob('aula-mensual-*.aulabak'))),24)
            self.assertEqual(permanent.read_bytes(),source.read_bytes())
            self.assertTrue(all(p.read_bytes().startswith(MAGIC) for p in directory.glob('*.aulabak')))
            # A broken retention ledger must never authorize deletion.
            (directory/'.aula-backup-history.json').write_text('corrupto')
            before={p.name for p in directory.glob('*.aulabak')}
            with self.assertRaises(OSError):retain_levels(source,directory,today=date(2023,4,1))
            self.assertTrue(before<={p.name for p in directory.glob('*.aulabak')})

    def test_permanent_year_copy_decrypts_and_preserves_financial_totals(self):
        from tests.test_system import SystemTests
        from colegio.backup_tiers import preserve_year
        from colegio.backup_inspection import probe_backup
        f=SystemTests();f.setUp()
        try:
            f.request('payments',f.payment())
            before=f.request('state');path=preserve_year(f.path,f.year)
            result=probe_backup(path,'FICTICIO-respaldo-seguro-2026')
            self.assertEqual(result['balance_usd'],before['summary']['pending'])
            self.assertFalse(result['unencrypted'])
            self.assertEqual(before['summary'],f.request('state')['summary'])
        finally:f.tearDown()

    def test_external_probe_reminder_requires_explicit_success_and_expires_after_35_days(self):
        from colegio.backup_probe_record import record,reminder
        from datetime import datetime,timedelta,timezone
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'colegio.sqlite3'
            self.assertTrue(reminder(path)['due'])
            record(path,'ficticio')
            now=datetime.now(timezone.utc)
            self.assertFalse(reminder(path,now=now)['due'])
            self.assertTrue(reminder(path,now=now+timedelta(days=36))['due'])
            self.assertTrue(reminder(path,now=now-timedelta(days=1))['due'])

class MonthlyReportsTests(unittest.TestCase):
    def test_monthly_money_voids_grade_totals_csv_pdf_and_existing_reports_unchanged(self):
        from tests.test_system import SystemTests
        from colegio.monthly_report import report,csv_bytes,pdf_bytes
        from colegio.server import snapshot
        f=SystemTests();f.setUp()
        try:
            f.request('payments',f.payment(amount='10',key='monthly-usd',paid_on=local_today().isoformat()))
            second=f.request('payments',f.payment(amount='20',key='monthly-void',paid_on=local_today().isoformat()))['id']
            f.request('payments',f.payment(amount='500',key='monthly-ves',currency='VES',paid_on=local_today().isoformat()))
            f.request('void-payment',dict(id=second,reason='=Motivo ficticio de anulación'))
            f.request('expenses',dict(concept='Gasto de prueba',category='Servicios',amount='3',currency='USD',
                spent_on=local_today().isoformat(),method='Efectivo'))
            before=f.request('state');cash=f.request('cash-preview');daily=f.request('daily-report')
            data=f.request('monthly-report?month='+local_today().strftime('%Y-%m'))
            self.assertEqual(data['income_usd'],1500)
            self.assertEqual(data['expenses_usd'],300)
            self.assertEqual(data['net_usd'],1200)
            self.assertEqual(sum(r['overdue'] for r in daily['arrears_by_grade']),before['summary']['overdue'])
            self.assertEqual([r['number'] for r in data['annulments']],['R-'+str(second).zfill(6)])
            self.assertEqual(sum(r['income_usd'] for r in data['balances']),1500)
            encoded=csv_bytes(data)
            self.assertTrue(encoded.startswith(b'\xef\xbb\xbf'))
            self.assertIn(b"'=Motivo",encoded)
            for private in ('Alumno Uno','AL-000001','V-123','04120000000'):
                self.assertNotIn(private.encode(),encoded)
            self.assertTrue(pdf_bytes(data).startswith(b'%PDF'))
            self.assertTrue(f.request('monthly-report.pdf').startswith(b'%PDF'))
            self.assertTrue(f.request('monthly-report.csv').startswith(b'\xef\xbb\xbf'))
            self.assertEqual(cash,f.request('cash-preview'))
            self.assertEqual(before['summary'],f.request('state')['summary'])
            self.assertEqual(daily['summaries'],f.request('daily-report')['summaries'])
        finally:f.tearDown()

class FirstStartCalendarTests(unittest.TestCase):
    def test_calendar_validation_rolls_back_and_derives_year_for_selected_month(self):
        from tests.test_system import SystemTests
        import threading
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'colegio.sqlite3';initialize(path)
            self.server=SchoolServer(('127.0.0.1',0),str(path))
            self.cookie=self.csrf=''
            thread=threading.Thread(target=self.server.serve_forever);thread.start()
            request=lambda route,body,status=200:SystemTests.request(self,route,body,status=status)
            try:
                body=dict(name='Administración ficticia',username='admin',password='FICTICIO-primera-clave',start_month=13,due_day=31)
                request('setup',body,400)
                with closing(connect(path)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM users').fetchone()[0],0)
                with patch('colegio.server.local_today',return_value=date(2027,1,15)):
                    request('setup',dict(body,start_month=1))
                with closing(connect(path)) as db:
                    settings=dict(db.execute('SELECT key,value FROM settings'))
                    self.assertEqual((settings['school_year'],settings['start_month'],settings['due_day']),('2027','1','31'))
                    self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],12)
                    from colegio.audit_chain import local_status
                    self.assertTrue(local_status(db)['ok'])
            finally:self.server.shutdown();thread.join();self.server.server_close()
