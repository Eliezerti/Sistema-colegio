"""Banking privacy through real HTTP requests, including historical documents."""
import json
import unittest
from contextlib import closing

from colegio.db import connect, local_today


class StaffAccessTests(unittest.TestCase):
    def setUp(self):
        from tests.test_system import SystemTests
        self.f = SystemTests('test_security_roles_csrf_origins_and_login')
        self.f.setUp()
        f = self.f
        self.today = local_today().isoformat()
        self.private = dict(bank='Banco PRIVADO anterior', bank_account='01020000000098765432',
                            account_type='Corriente PRIVADA', account_holder='Titular PRIVADO anterior',
                            holder_document='V-TITULAR-PRIVADO')
        self.employee_data = dict(name='Docente visible', document='V-DOCENTE', position='Docente',
                                  salary='120', phone='04125555555', status='active', **self.private)
        self.employee = f.request('employees', self.employee_data)['id']
        self.plan = f.request('payroll-plans', dict(name='Relación histórica', pay_date=self.today,
                              lines=[dict(employee_id=self.employee, amount='120')]))['id']
        self.expense_data = dict(concept='Pago de sueldo ficticio', category='Nómina',
                                 employee_id=self.employee, amount='20', currency='USD',
                                 spent_on=self.today, method='Transferencia', reference='REF-SEGURA',
                                 period_start=self.today, period_end=self.today,
                                 entry_time='07:00', exit_time='15:00')
        result = f.request('expenses', self.expense_data)
        self.expense, self.receipt = result['id'], result['salary_receipt_id']
        for role in ('cashier', 'reader'):
            f.request('users', dict(name=role, username=role, role=role, password='Perfil-seguro-2026'))

    def tearDown(self):
        self.f.tearDown()

    def login(self, role):
        f = self.f
        f.request('logout', {})
        f.request('login', dict(username='admin' if role == 'admin' else role,
                               password='Una-clave-segura' if role == 'admin' else 'Perfil-seguro-2026'))
        f.csrf = f.request('session')['user']['csrf']
        f.request('confirm-rate', dict(rate_date=self.today, rate='100'))

    def assert_private_absent(self, data):
        content = json.dumps(data, ensure_ascii=False).encode() if not isinstance(data, bytes) else data
        for secret in self.private.values():
            self.assertNotIn(secret.encode(), content)
        def keys(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    self.assertNotIn(key, self.private)
                    keys(child)
            elif isinstance(value, list):
                for child in value: keys(child)
        if not isinstance(data, bytes): keys(data)

    def test_admin_receives_complete_current_and_historical_banking_without_data_changes(self):
        f = self.f
        with closing(connect(f.path)) as db:
            before = {table: [tuple(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY id')]
                      for table in ('employees', 'payroll_plans', 'salary_receipts', 'expenses')}
        state = f.request('state')
        employee = next(e for e in state['employees'] if e['id'] == self.employee)
        for key, value in self.private.items(): self.assertEqual(employee[key], value)
        self.assertEqual(state['payroll_plans'][0]['lines'][0]['bank_account'], self.private['bank_account'])
        self.assertEqual(f.request(f'payroll-plan/{self.plan}')['lines'][0]['bank_account'], self.private['bank_account'])
        self.assertEqual(f.request(f'salary-receipt/{self.receipt}')['employee']['bank_account'], self.private['bank_account'])
        for route in (f'payroll-plan/{self.plan}.pdf', f'salary-receipt/{self.receipt}.pdf', 'directory/employees.pdf'):
            self.assertIn(self.private['bank_account'].encode(), f.request(route))
        with closing(connect(f.path)) as db:
            for table, original in before.items():
                self.assertEqual([tuple(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY id')], original)
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 11)

    def test_cashier_and_reader_state_omit_banks_and_saved_lines_active_and_inactive(self):
        f = self.f
        f.request('employees', dict(self.employee_data, name='Docente inactivo', document='V-INACTIVO', status='inactive'))
        for role in ('cashier', 'reader'):
            with self.subTest(role=role):
                self.login(role)
                data = f.request('state?role=admin')
                self.assert_private_absent(data)
                self.assertEqual(len(data['employees']), 2)
                self.assertEqual(data['employees'][0]['salary'], 12000)
                self.assertEqual({e['status'] for e in data['employees']}, {'active', 'inactive'})
                self.assertNotIn('lines', data['payroll_plans'][0])
                self.assertEqual(data['payroll_plans'][0]['total_usd'], 12000)
                self.assertEqual(data['payroll_plans'][0]['total_ves'], 1200000)
                self.assertEqual(data['expenses'][0]['amount'], 2000)
                self.assertEqual(len(data['students']), 1)

    def test_old_bank_documents_denied_even_after_current_employee_bank_changes(self):
        f = self.f
        f.request('employees', dict(self.employee_data, id=self.employee, bank='Banco nuevo',
                                   bank_account='01020000000011111111', account_holder='Titular nuevo'))
        self.assertEqual(f.request(f'salary-receipt/{self.receipt}')['employee']['bank_account'], self.private['bank_account'])
        for role in ('cashier', 'reader'):
            self.login(role)
            for kind, target in (('payroll-plan', self.plan), ('salary-receipt', self.receipt)):
                for suffix in ('', '.pdf'):
                    for identifier in (target, 2147483647):
                        result = f.request(f'{kind}/{identifier}{suffix}?role=admin', status=403)
                        self.assert_private_absent(result)
            f.request('employees', dict(self.employee_data, role='admin'), status=403)
            f.request('salary-receipts', dict(expense_id=self.expense, role='admin'), status=403)
            f.request('backup', status=403)
            f.request(f'archive-preview/employee/{self.employee}', status=403)

    def test_restricted_directory_json_pdf_and_financial_reports_still_work_without_banks(self):
        f = self.f
        for role in ('cashier', 'reader'):
            self.login(role)
            report = f.request('directory/employees?archived=1')
            self.assert_private_absent(report)
            self.assertNotIn('Banco / cuenta', report['headings'])
            self.assertEqual(report['lines'][0][-2], 'USD 120,00')
            self.assertEqual(len(report['lines'][0]), len(report['headings']))
            self.assertEqual(sum(report['widths']), 758)
            for route in ('directory/employees.pdf', 'export?type=expenses', 'daily-report', 'daily-report.pdf', 'cash-preview'):
                self.assert_private_absent(f.request(route))

    def test_cashier_can_record_salary_expense_but_reader_cannot_and_receipt_remains_admin_only(self):
        f = self.f
        self.login('cashier')
        result = f.request('expenses', self.expense_data)
        f.request(f'salary-receipt/{result["salary_receipt_id"]}', status=403)
        self.assert_private_absent(f.request('state'))
        self.assertEqual(f.request('cash-preview')['expense_usd'], 4000)
        self.login('reader')
        f.request('expenses', self.expense_data, status=403)
        self.login('admin')
        receipt = f.request(f'salary-receipt/{result["salary_receipt_id"]}')
        self.assertEqual(receipt['employee']['bank_account'], self.private['bank_account'])
        self.assertEqual(receipt['expense']['amount'], 2000)

    def test_anonymous_and_missing_role_do_not_obtain_bank_information(self):
        from colegio.directory_reports import directory_report
        from tests.test_directory_reports import directory_state
        data = directory_state()
        data['user'].pop('role')
        report = directory_report(data, 'employees', {})
        self.assertNotIn('Banco / cuenta', report['headings'])
        self.assertNotIn('01020000000012345678', json.dumps(report))
        self.f.request('logout', {})
        for route in ('state', f'payroll-plan/{self.plan}', f'salary-receipt/{self.receipt}.pdf', 'directory/employees.pdf'):
            self.f.request(route, status=401)
