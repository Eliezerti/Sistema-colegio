import argparse
import csv
import io
import json
import mimetypes
import secrets
import signal
import sqlite3
import tempfile
import time
import threading
import traceback
import webbrowser
from contextlib import closing, contextmanager
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

from .db import (ValidationError, RateConfirmationRequired, audit, charges, check_password, connect, convert_received,
                 generate_month, hash_password, initialize, integer, money, record_payment,
                 required, valid_date, valid_rate, local_today, synchronize_monthly_charges)
from .db import next_record_id
from .storage import DataLock, consistent_backup, daily_backup, automatic_backup, backup_status
from .administration import (import_roster, import_template, cash_summary, close_cash, reopen_cash,
    ensure_open_day, guardian_account, issue_guardian_document, load_administrative_document)
from .documents import enrollment, payroll, load_document, render_pdf
from .branding import SCHEMA_VERSION, LOGO_FILE
from .lifecycle import roster_for_year, transition_year, create_plan, cancel_plan, plan_status
from .demo import DemoWorkspace
from .salary import details as salary_details, issue_salary_receipt, load_salary_receipt
from .reset_records import reset_preview, reset_records
from .network import PrivateAccess, load_config

ROOT = Path(__file__).resolve().parent.parent


def rows(db, sql, params=()):
    return [dict(row) for row in db.execute(sql, params)]


def snapshot(db, user):
    owns_transaction = not db.in_transaction
    if owns_transaction:
        db.execute('BEGIN IMMEDIATE')
    synchronize_monthly_charges(db)
    if owns_transaction:
        db.commit()
    settings = dict(db.execute('SELECT key,value FROM settings'))
    students = rows(db, '''SELECT s.*,g.name AS guardian_name,g.phone AS guardian_phone,g.email AS guardian_email,
      gr.name AS grade_name FROM students s JOIN guardians g ON g.id=s.guardian_id
      JOIN grades gr ON gr.id=s.grade_id ORDER BY s.name''')
    charge_list = charges(db)
    student_map = {s['id']: s for s in students}
    today = local_today().isoformat()
    for student in students:
        student['balance'] = student['overdue'] = 0
    for charge in charge_list:
        student = student_map[charge['student_id']]
        student['balance'] += charge['balance']
        if charge['overdue']:
            student['overdue'] += charge['balance']
        charge['student_name'] = student['name']
        charge['guardian_name'] = student['guardian_name']
        charge['guardian_phone'] = student['guardian_phone']
        charge['grade_name'] = student['grade_name']
        charge['days_overdue'] = max(0, (local_today() - date.fromisoformat(charge['due_date'])).days) if charge['balance'] else 0
    payments = rows(db, '''SELECT p.*,s.name AS student_name,u.name AS operator FROM payments p
       JOIN students s ON s.id=p.student_id JOIN users u ON u.id=p.created_by ORDER BY p.id DESC''')
    for payment in payments:
        payment.pop('receipt_snapshot', None)
        payment.pop('request_key', None)
    expenses = rows(db, '''SELECT e.*,emp.name AS employee_name,r.id AS salary_receipt_id FROM expenses e
       LEFT JOIN employees emp ON emp.id=e.employee_id LEFT JOIN salary_receipts r ON r.expense_id=e.id
       ORDER BY e.spent_on DESC,e.id DESC''')
    month = today[:7]
    income = sum(p['amount'] for p in payments if not p['voided'] and p['paid_on'].startswith(month))
    outgo = sum(e['amount'] for e in expenses if not e['voided'] and e['spent_on'].startswith(month))
    aging = [0, 0, 0, 0]
    for c in charge_list:
        if c['overdue']:
            d = c['days_overdue']
            aging[0 if d <= 30 else 1 if d <= 60 else 2 if d <= 90 else 3] += c['balance']
    return {'settings': settings, 'today': today, 'user': user, 'students': students,
            'guardians': rows(db, 'SELECT * FROM guardians ORDER BY name'),
            'grades': rows(db, 'SELECT * FROM grades ORDER BY name'),
            'employees': rows(db, 'SELECT * FROM employees ORDER BY name'),
            'positions': rows(db, 'SELECT * FROM positions ORDER BY name'),
            'enrollments': rows(db, 'SELECT id,student_id,created_at FROM enrollment_documents ORDER BY id DESC'),
            'payroll_plans': [dict(json.loads(r['snapshot_json']), id=r['id']) for r in db.execute('SELECT * FROM payroll_plans ORDER BY id DESC LIMIT 30')],
            'charges': charge_list, 'payments': payments, 'expenses': expenses,
            'cash_closures': rows(db,'SELECT id,closed_on,created_at,reopened_at,reopen_reason FROM cash_closures ORDER BY id DESC LIMIT 100'),
            'payment_plans': [plan_status(db,r) for r in db.execute('SELECT * FROM payment_plans ORDER BY id DESC LIMIT 100')],
            'year_transitions': [dict(id=r['id'],source_year=(d:=json.loads(r['snapshot_json']))['source_year'],target_year=d['target_year'],issued_on=d['issued_on']) for r in db.execute('SELECT * FROM year_transitions ORDER BY id DESC LIMIT 30')],
            'guardian_documents': [dict(id=r['id'],kind=(d:=json.loads(r['snapshot_json']))['kind'],
                guardian_id=d['guardian']['id'],guardian_name=d['guardian']['name'],issued_on=d['issued_on'])
                for r in db.execute('SELECT id,snapshot_json FROM guardian_documents ORDER BY id DESC LIMIT 100')],
            'rates': rows(db, 'SELECT * FROM exchange_rates ORDER BY rate_date DESC'),
            'collections': rows(db, '''SELECT c.*,u.name AS operator FROM collection_notes c
                 JOIN users u ON u.id=c.created_by ORDER BY c.id DESC'''),
            'users': rows(db, 'SELECT id,name,username,role FROM users ORDER BY name') if user['role'] == 'admin' else [],
            'audit': rows(db, '''SELECT a.*,u.name AS operator FROM audit a LEFT JOIN users u ON u.id=a.user_id
               ORDER BY a.id DESC LIMIT 300''') if user['role'] == 'admin' else [],
            'summary': {'active_students': sum(s['status'] == 'active' for s in students),
                        'pending': sum(c['balance'] for c in charge_list),
                        'overdue': sum(c['balance'] for c in charge_list if c['overdue']),
                        'debtors': sum(s['overdue'] > 0 for s in students),
                        'income': income, 'expenses': outgo, 'net': income - outgo, 'aging': aging}}


def save_record(db, table, fields, data):
    record_id = data.get('id')
    if record_id is not None:
        record_id = integer(record_id, 1, 2147483647)
        if not db.execute(f'SELECT id FROM {table} WHERE id=?', (record_id,)).fetchone():
            raise ValidationError('Registro inexistente.')
        db.execute(f'UPDATE {table} SET ' + ','.join(f'{k}=?' for k in fields) + ' WHERE id=?',
                   [*fields.values(), record_id])
        return record_id
    if table in ('students', 'expenses'):
        fields = dict(fields, id=next_record_id(db, table))
    result = db.execute(f'INSERT INTO {table}(' + ','.join(fields) + ') VALUES(' + ','.join('?' for _ in fields) + ')', list(fields.values()))
    return result.lastrowid


def mutate(db, endpoint, data, user, *, synchronize=True):
    uid = user['id']
    admin_paths = {'settings','grades','guardians','students','employees','users','password','void-payment','void-expense','cancel-charge','positions','payroll-plans','import-roster','reopen-cash','transition-year','cancel-plan'}
    if user['role'] == 'reader' or (endpoint in admin_paths and user['role'] != 'admin'):
        raise PermissionError('Tu perfil no permite esta operación.')
    # Calculate outstanding months before editing tariffs, dates or student status.
    if synchronize: synchronize_monthly_charges(db)
    batch_record=lambda db,endpoint,data,user: mutate(db,endpoint,data,user,synchronize=False)
    if endpoint=='import-roster': return import_roster(db,data,user,batch_record)
    if endpoint=='close-cash': return close_cash(db,data,user)
    if endpoint=='reopen-cash': return reopen_cash(db,data,user)
    if endpoint=='guardian-documents': return issue_guardian_document(db,data,user)
    if endpoint=='transition-year': return transition_year(db,data,user,batch_record)
    if endpoint=='payment-plans': return create_plan(db,data,user)
    if endpoint=='cancel-plan': return cancel_plan(db,data,user)
    if endpoint in ('payments','expenses'):
        column='paid_on' if endpoint=='payments' else 'spent_on'
        # A retry of an already committed payment still succeeds after closing the day.
        duplicate=endpoint=='payments' and db.execute('SELECT 1 FROM payments WHERE request_key=?',(str(data.get('request_key','')),)).fetchone()
        if not duplicate: ensure_open_day(db,valid_date(data.get(column)))
    if endpoint in ('void-payment','void-expense'):
        table,column=('payments','paid_on') if endpoint=='void-payment' else ('expenses','spent_on')
        prior=db.execute(f'SELECT {column} FROM {table} WHERE id=?',(data.get('id'),)).fetchone()
        if prior: ensure_open_day(db,prior[0])
    if endpoint == 'payroll-plans':
        return payroll(db, data, uid)
    if endpoint == 'salary-receipts':
        return {'id': issue_salary_receipt(db, data.get('expense_id'), data, uid)}
    if endpoint == 'generate':
        return generate_month(db, data, uid)
    if endpoint == 'payments':
        return record_payment(db, data, uid)
    if endpoint == 'collections':
        student_id = integer(data.get('student_id'), 1, 2147483647)
        note = required(data, 'note', 2000)
        promised_on = valid_date(data['promised_on']) if data.get('promised_on') else None
        result = db.execute('INSERT INTO collection_notes(student_id,note,promised_on,created_by,created_at) VALUES(?,?,?,?,?)',
                            (student_id, note, promised_on, uid, datetime.now(timezone.utc).isoformat()))
        audit(db, uid, 'collection', {'id': result.lastrowid, 'student_id': student_id, 'promised_on': promised_on})
        return {'id': result.lastrowid}
    if endpoint == 'rates':
        on = valid_date(data.get('rate_date'))
        rate = valid_rate(data.get('rate'))
        prior=db.execute('SELECT rate FROM exchange_rates WHERE rate_date<=? ORDER BY rate_date DESC LIMIT 1',(on,)).fetchone()
        if prior and abs(Decimal(rate)-Decimal(prior['rate']))>Decimal(prior['rate'])*Decimal('0.10') and data.get('rate_change_confirmed') is not True:
            raise RateConfirmationRequired(prior['rate'],rate)
        db.execute('INSERT INTO exchange_rates(rate_date,rate,source) VALUES(?,?,?) ON CONFLICT(rate_date) DO UPDATE SET rate=excluded.rate,source=excluded.source',
                   (on, rate, 'BCV · registro manual'))
        audit(db, uid, 'rate', {'date': on, 'rate': rate,'previous_rate':prior['rate'] if prior else None,'confirmed_large_change':data.get('rate_change_confirmed') is True})
        return {'rate_date': on}
    if endpoint == 'settings':
        fields = {'school_name': required(data, 'school_name'), 'currency': 'USD',
                  'school_year': str(integer(data.get('school_year'), 2000, 2100)),
                  'start_month': str(integer(data.get('start_month', 9), 1, 12)),
                  'due_day': str(integer(data.get('due_day'), 1, 31))}
        old_start = db.execute("SELECT value FROM settings WHERE key='start_month'").fetchone()[0]
        if fields['start_month'] != old_start and db.execute('SELECT 1 FROM students LIMIT 1').fetchone():
            raise ValidationError('El mes de inicio no puede cambiar con matrículas registradas: alteraría el calendario de las mensualidades. Conserva el mes actual.')
        if 'logo' in data:
            import struct, zlib
            from .branding import pdf_logo
            logo = data['logo']
            if not isinstance(logo,str) or len(logo)>700000:
                raise ValidationError('El logo es demasiado grande. Selecciona otra imagen.')
            try:
                if logo and not pdf_logo(logo): raise ValueError('Formato no permitido.')
            except (ValueError, OSError, struct.error, zlib.error):
                raise ValidationError('Logo inválido. Carga una imagen PNG o JPG desde Configuración.')
            fields['logo'] = logo
        # An omitted optional field must not erase the configured fiscal identity.
        for key, limit in (('address',500), ('phone',100), ('rif',100), ('email',200),
                           ('website',200), ('legal_name',200), ('fiscal_address',500), ('institution_type',100)):
            if key in data:
                fields[key] = str(data[key]).strip()[:limit]
        if 'backup_directory' in data:
            directory=str(data['backup_directory']).strip()
            if directory:
                path=Path(directory)
                live=Path(db.execute('PRAGMA database_list').fetchone()[2]).resolve().parent
                if len(directory)>500 or not path.is_absolute() or path.resolve()==live or live in path.resolve().parents:
                    raise ValidationError('El segundo respaldo debe usar una ruta absoluta fuera de la carpeta de datos de Aula.')
            fields['backup_directory']=directory
        db.executemany('UPDATE settings SET value=? WHERE key=?', [(v, k) for k, v in fields.items()])
        audit(db, uid, 'settings', {k:(bool(v) if k=='logo' else v) for k,v in fields.items()})
        return {'saved': True}
    if endpoint == 'positions':
        fields = {'name': required(data, 'name')}
        if data.get('id'):
            db.execute('UPDATE employees SET position=? WHERE position_id=?', (fields['name'], data['id']))
    elif endpoint == 'grades':
        fields = {'name': required(data, 'name'), 'capacity': integer(data.get('capacity'), 1, 500)}
        if data.get('id') and db.execute("""SELECT 1 FROM students WHERE grade_id=? AND status='active'
           GROUP BY school_year HAVING COUNT(*)>?""", (integer(data['id'], 1, 2147483647), fields['capacity'])).fetchone():
            raise ValidationError('La capacidad no puede ser menor que las matrículas activas de un año escolar.')
    elif endpoint == 'guardians':
        fields = {'name': required(data, 'name'), 'document': required(data, 'document'),
                  'phone': str(data.get('phone', ''))[:100], 'email': str(data.get('email', ''))[:200],
                  'address': str(data.get('address', ''))[:500]}
    elif endpoint == 'students':
        existing = db.execute('SELECT student_code FROM students WHERE id=?', (data.get('id'),)).fetchone() if data.get('id') else None
        next_id = next_record_id(db, 'students')
        code = existing['student_code'] if existing else f'AL-{next_id:06d}'
        # A legacy document may resemble an automatic code; skip it without changing legacy IDs.
        while not existing and db.execute('SELECT id FROM students WHERE document=? OR student_code=?', (code, code)).fetchone():
            next_id += 1
            code = f'AL-{next_id:06d}'
        document = str(data.get('document', '')).strip() or code
        if len(document)>200:
            raise ValidationError('Documento demasiado largo.')
        fields = {'name': required(data, 'name'), 'document': document,
                  'birth_date': valid_date(data.get('birth_date')),
                  'guardian_id': integer(data.get('guardian_id'), 1, 2147483647),
                  'grade_id': integer(data.get('grade_id'), 1, 2147483647),
                  'school_year': integer(data.get('school_year'), 2000, 2100),
                  'monthly_fee': money(data.get('monthly_fee')), 'discount': integer(data.get('discount', 0), 0, 100),
                  'status': data.get('status', 'active'), 'notes': str(data.get('notes', ''))[:2000]}
        if not data.get('id'):
            fields.update(id=next_id, student_code=code)
        fields['enrollment_start'] = valid_date(data.get('enrollment_start'))
        fields['enrollment_end'] = valid_date(data.get('enrollment_end'))
        if fields['enrollment_end'] < fields['enrollment_start']:
            raise ValidationError('El fin de la matrícula debe ser posterior al inicio.')
        settings = dict(db.execute('SELECT key,value FROM settings'))
        academic_start = date(fields['school_year'], int(settings['start_month']), 1).isoformat()
        academic_end = date(fields['school_year'] + 1, int(settings['start_month']), 1).isoformat()
        if not academic_start <= fields['enrollment_start'] <= fields['enrollment_end'] < academic_end:
            raise ValidationError('Las fechas de matrícula deben estar dentro del año escolar seleccionado.')
        if fields['birth_date'] > local_today().isoformat():
            raise ValidationError('La fecha de nacimiento no puede ser futura.')
        grade = db.execute('SELECT capacity FROM grades WHERE id=?', (fields['grade_id'],)).fetchone()
        if not grade:
            raise ValidationError('Selecciona un grado existente.')
        occupied = db.execute("SELECT COUNT(*) FROM students WHERE grade_id=? AND school_year=? AND status='active' AND id<>?",
                              (fields['grade_id'], fields['school_year'], data.get('id', 0))).fetchone()[0]
        if fields['status'] == 'active' and occupied >= grade['capacity']:
            raise ValidationError('El grado alcanzó su capacidad para ese año escolar.')
    elif endpoint == 'employees':
        if data.get('position_id'):
            position = db.execute('SELECT * FROM positions WHERE id=?', (integer(data['position_id'], 1, 2147483647),)).fetchone()
            if not position:
                raise ValidationError('Selecciona un cargo existente.')
        else:
            name = required(data, 'position')  # Compatibility with earlier saved clients.
            db.execute('INSERT OR IGNORE INTO positions(name) VALUES(?)', (name,))
            position = db.execute('SELECT * FROM positions WHERE name=?', (name,)).fetchone()
        account = str(data.get('bank_account', '')).strip()
        if account and (len(account)!=20 or not account.isascii() or not account.isdigit()):
            raise ValidationError('La cuenta bancaria venezolana debe tener 20 dígitos.')
        fields = {'name': required(data, 'name'), 'document': required(data, 'document'),
                  'position': position['name'], 'position_id': position['id'], 'phone': str(data.get('phone', ''))[:100],
                  'salary': money(data.get('salary')), 'status': data.get('status', 'active'),
                  'bank': str(data.get('bank', ''))[:100], 'bank_account': account,
                  'account_holder': str(data.get('account_holder', '')).strip()[:200],
                  'holder_document': str(data.get('holder_document', '')).strip()[:200],
                  'account_type': str(data.get('account_type', ''))[:100]}
    elif endpoint == 'users':
        role = data.get('role')
        if role not in ('admin','cashier','reader'):
            raise ValidationError('Perfil inválido.')
        fields = {'name': required(data, 'name'), 'username': required(data, 'username', 80).lower(),
                  'password': hash_password(data.get('password')), 'role': role}
        if 'id' in data:
            raise ValidationError('Crea usuarios nuevos aquí; usa el cambio de contraseña para cuentas existentes.')
    elif endpoint == 'password':
        target = integer(data.get('user_id'), 1, 2147483647)
        if not db.execute('SELECT id FROM users WHERE id=?', (target,)).fetchone():
            raise ValidationError('Usuario inexistente.')
        db.execute('UPDATE users SET password=? WHERE id=?', (hash_password(data.get('password')), target))
        db.execute('DELETE FROM sessions WHERE user_id=?', (target,))
        audit(db, uid, 'password_changed', {'user_id': target})
        return {'saved': True}
    elif endpoint == 'charges':
        student_id = integer(data.get('student_id'), 1, 2147483647)
        amount = money(data.get('amount'))
        if not amount:
            raise ValidationError('El cargo debe ser mayor a cero.')
        result = db.execute('INSERT INTO charges(student_id,period,concept,amount,due_date) VALUES(?,?,?,?,?)',
                           (student_id, required(data, 'period', 40), required(data, 'concept'), amount, valid_date(data.get('due_date'))))
        audit(db, uid, 'charge', {'id': result.lastrowid, 'student_id': student_id, 'amount': amount})
        return {'id': result.lastrowid}
    elif endpoint in ('void-payment', 'void-expense', 'cancel-charge'):
        target = integer(data.get('id'), 1, 2147483647)
        reason = required(data, 'reason', 500)
        if endpoint == 'cancel-charge':
            charge = next((c for c in charges(db) if c['id'] == target), None)
            if not charge:
                raise ValidationError('Cargo inexistente o ya anulado.')
            for plan in db.execute('SELECT * FROM payment_plans WHERE cancelled=0'):
                if any(c['id']==target for c in json.loads(plan['snapshot_json'])['charges']):
                    raise ValidationError('Este cargo pertenece a un convenio. Cancela primero el convenio con motivo.')
            if charge['paid']:
                raise ValidationError('Anula primero los pagos asociados al cargo.')
            db.execute('UPDATE charges SET cancelled=1 WHERE id=?', (target,))
        else:
            table = 'payments' if endpoint == 'void-payment' else 'expenses'
            result = db.execute(f'UPDATE {table} SET voided=1,void_reason=? WHERE id=? AND voided=0', (reason, target))
            if not result.rowcount:
                raise ValidationError('Registro inexistente o ya anulado.')
        audit(db, uid, endpoint, {'id': target, 'reason': reason})
        return {'saved': True}
    elif endpoint == 'expenses':
        on = valid_date(data.get('spent_on'))
        if on > local_today().isoformat():
            raise ValidationError('La fecha del egreso no puede ser futura.')
        amount, currency, received, rate = convert_received(db, data, on)
        fields = {'concept': required(data, 'concept'), 'category': required(data, 'category'), 'amount': amount,
                  'spent_on': on, 'reference': str(data.get('reference', ''))[:200],
                  'employee_id': integer(data['employee_id'], 1, 2147483647) if data.get('employee_id') else None,
                  'created_by': uid, 'currency': currency, 'received_amount': received, 'exchange_rate': rate}
        method=data.get('method','No especificado')
        if method not in ('Efectivo','Transferencia','Tarjeta','Otro','No especificado'):
            raise ValidationError('Método de pago inválido.')
        fields['method']=method
        if fields['category'] == 'Nómina':
            if not fields['employee_id']:
                raise ValidationError('Selecciona el empleado para emitir su recibo de sueldo.')
            salary_details(data)
        if data.get('id'):
            raise ValidationError('Los egresos se corrigen anulándolos y creando uno nuevo.')
    else:
        raise ValidationError('Operación desconocida.')
    record_id = save_record(db, endpoint, fields, data)
    audit(db, uid, endpoint, {'id': record_id, 'operation': 'update' if data.get('id') else 'create'})
    result = {'id': record_id}
    if endpoint == 'students':
        if synchronize: synchronize_monthly_charges(db)
        result['document_id'] = enrollment(db, record_id, uid)
        result['student_code'] = db.execute('SELECT student_code FROM students WHERE id=?', (record_id,)).fetchone()[0]
    elif endpoint == 'expenses' and fields['category'] == 'Nómina':
        result['salary_receipt_id'] = issue_salary_receipt(db, record_id, data, uid)
    return result


class SchoolServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, db_path, demo=False, remote_origin=''):
        if address[0]!='127.0.0.1':
            raise ValueError('Aula escucha solo en 127.0.0.1. Usa Tailscale Serve para compartir el acceso privado.')
        if demo and remote_origin:
            raise ValueError('El modo de prueba no admite acceso remoto a la base del colegio.')
        self.access=PrivateAccess(remote_origin)
        self.demo = demo
        self.daemon_threads = not demo
        self.demo_stop = threading.Event()
        self.demo_thread = None
        self.backup_stop = threading.Event()
        self.backup_thread = None
        super().__init__(address, Handler)
        self.db_path = db_path
        self.login_attempts = {}
        self.backup_lock=threading.Lock()
        self.backup_stop=threading.Event()
        self.backup_thread=threading.Thread(target=self.backup_loop,daemon=True)
        self.backup_thread.start()
        self.demo_token = secrets.token_urlsafe(32) if demo else ''
        self.demo_clients = {}
        self.demo_clients_lock = threading.Lock()
        self.demo_closed_at = None
        self.demo_stop = threading.Event()
        self.demo_thread = None
        if demo:
            self.demo_thread = threading.Thread(target=self.demo_loop, daemon=True)
            self.demo_thread.start()

    @property
    def cookie_name(self):
        return 'school_demo_session' if self.demo else 'school_session'

    def get_request(self):
        connection, address = super().get_request()
        if self.demo:
            connection.settimeout(15)
        return connection, address

    def demo_presence(self, client, action):
        if not isinstance(client, str) or not 1 <= len(client) <= 80 or action not in ('alive', 'close'):
            raise ValidationError('Identificación de pestaña de prueba inválida.')
        with self.demo_clients_lock:
            if action == 'alive':
                self.demo_clients[client] = time.monotonic()
                self.demo_closed_at = None
            elif client in self.demo_clients:
                del self.demo_clients[client]
                if not self.demo_clients:
                    self.demo_closed_at = time.monotonic()

    def demo_loop(self):
        while not self.demo_stop.wait(0.5):
            now = time.monotonic()
            with self.demo_clients_lock:
                stale = [client for client, last in self.demo_clients.items() if now-last > 600]
                for client in stale:
                    del self.demo_clients[client]
                if stale and not self.demo_clients and self.demo_closed_at is None:
                    self.demo_closed_at = now
                closed = self.demo_closed_at is not None and now-self.demo_closed_at >= 5
            if closed:
                self.shutdown()
                return

    def mark_document(self, document):
        if self.demo:
            document['demo'] = True
            key = 'school' if 'school' in document else 'settings'
            school = dict(document[key])
            school['legal_name'] = 'PRUEBA SIN VALIDEZ - ' + (school.get('legal_name') or school.get('school_name', 'Colegio'))
            document[key] = school
        return document

    def backup_status(self):
        if self.demo:
            return {'demo': True, 'data_path': str(Path(self.db_path).resolve())}
        return backup_status(self.db_path)

    def make_backup(self):
        if self.demo:
            return self.backup_status()
        with self.backup_lock:
            try: return automatic_backup(self.db_path)
            except Exception:
                return {'local_error':'No se pudo completar el respaldo. Revisa el espacio y los permisos de la carpeta de datos.'}

    def backup_loop(self):
        while not self.backup_stop.wait(300): self.make_backup()

    def server_close(self):
        self.demo_stop.set()
        if self.demo_thread:
            self.demo_thread.join(timeout=5)
        self.backup_stop.set()
        if self.backup_thread:
            self.backup_thread.join()
        super().server_close()


class Handler(BaseHTTPRequestHandler):
    server_version = 'ColegioLocal/1.0'

    def log_message(self, fmt, *args):
        # Do not log request bodies, credentials or cookie values.
        print(f'{self.log_date_time_string()} {self.command} {urlsplit(self.path).path} {args[1] if len(args)>1 else ""}')

    def respond(self, status, body, content_type='application/json; charset=utf-8', extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        if isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def session(self, db):
        token = ''
        for part in self.headers.get('Cookie', '').split(';'):
            if part.strip().startswith(self.server.cookie_name+'='):
                token = part.strip().split('=', 1)[1]
        result = db.execute('''SELECT u.id,u.name,u.username,u.role,s.csrf,s.token,s.rate_confirmed_on FROM sessions s
          JOIN users u ON u.id=s.user_id WHERE token=? AND expires>?''', (token, int(time.time()))).fetchone()
        return dict(result) if result else None

    def do_GET(self):
        self.handle_request(False)

    def do_POST(self):
        self.handle_request(True)

    def handle_request(self, post):
        db = None
        try:
            host = self.headers.get('Host', '')
            if not self.server.access.allowed_host(host,self.server.server_port):
                self.respond(403, {'error': 'Dirección de acceso no permitida. Usa la dirección local o el enlace privado configurado.'})
                return
            url = urlsplit(self.path)
            endpoint = url.path.removeprefix('/api/')
            if not post and not url.path.startswith('/api/'):
                assets = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css', '/favicon.svg': 'favicon.svg',
                          '/'+LOGO_FILE: LOGO_FILE, '/mobile.js': 'mobile.js',
                          '/manifest.webmanifest': 'manifest.webmanifest', '/service-worker.js': 'service-worker.js',
                          '/offline.html': 'offline.html', '/icon-mobile-192.png': 'icon-mobile-192.png',
                          '/icon-mobile-512.png': 'icon-mobile-512.png'}
                if url.path not in assets:
                    self.respond(404, {'error': 'Página inexistente.'})
                    return
                file = ROOT / 'static' / assets[url.path]
                content_type = mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
                if file.suffix == '.webmanifest':
                    content_type = 'application/manifest+json'
                if content_type.startswith('text/') or content_type in ('application/javascript','image/svg+xml'):
                    content_type += '; charset=utf-8'
                self.respond(200, file.read_bytes(), content_type)
                return
            db = connect(self.server.db_path)
            if post:
                if not self.server.access.allowed_origin(host,self.headers.get('Origin'),self.server.server_port):
                    raise PermissionError('Origen no permitido.')
                length = int(self.headers.get('Content-Length', '0'))
                maximum=3_000_000 if endpoint in ('import-roster','transition-year','settings') else 65536
                if not 0 < length <= maximum or 'application/json' not in self.headers.get('Content-Type', ''):
                    raise ValidationError('Envía un objeto JSON válido (máximo 64 KB).')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValidationError('Se esperaba un objeto JSON.')
                db.execute('BEGIN IMMEDIATE')
            if post and endpoint == 'demo-presence':
                if not self.server.demo:
                    raise PermissionError('Esta instalación no está en modo prueba.')
                token = data.get('token', '')
                if not isinstance(token, str) or not secrets.compare_digest(token, self.server.demo_token):
                    raise PermissionError('Sesión de prueba inválida.')
                self.server.demo_presence(data.get('client'), data.get('action'))
                self.respond(200, {'ok': True})
                return
            user = self.session(db)
            needs_setup = not db.execute('SELECT 1 FROM users LIMIT 1').fetchone()
            if not post and endpoint == 'session':
                self.respond(200, {'needs_setup': needs_setup, 'user': {k:v for k,v in user.items() if k != 'token'} if user else None,
                                   'school': {k:v for k,v in db.execute('SELECT key,value FROM settings') if k in ('school_name','institution_type','logo')},
                                   'demo': self.server.demo, 'demo_token': self.server.demo_token})
                return
            if post and endpoint in ('setup', 'login', 'demo-login'):
                if endpoint == 'demo-login':
                    if not self.server.demo:
                        raise PermissionError('El acceso de prueba no está disponible en el sistema real.')
                    user_id = self.server.demo_admin_id
                elif endpoint == 'setup':
                    if not needs_setup:
                        raise ValidationError('El administrador ya está configurado.')
                    result = db.execute('INSERT INTO users(username,name,password,role) VALUES(?,?,?,?)',
                                        (required(data, 'username', 80).lower(), required(data, 'name'), hash_password(data.get('password')), 'admin'))
                    user_id = result.lastrowid
                    if 'school_name' in data:
                        db.execute("UPDATE settings SET value=? WHERE key='school_name'",(required(data,'school_name'),))
                    audit(db, user_id, 'setup', {'user_id': user_id})
                else:
                    now = time.time()
                    attempts = [t for t in self.server.login_attempts.get(self.client_address[0], []) if now - t < 60]
                    if len(attempts) >= 10:
                        self.respond(429, {'error': 'Demasiados intentos. Espera un minuto.'})
                        return
                    attempts.append(now)
                    self.server.login_attempts[self.client_address[0]] = attempts
                    found = db.execute('SELECT * FROM users WHERE username=?', (required(data, 'username', 80).lower(),)).fetchone()
                    password = data.get('password', '')
                    if not isinstance(password, str) or len(password) > 256 or not found or not check_password(password, found['password']):
                        self.respond(401, {'error': 'Usuario o contraseña incorrectos.'})
                        return
                    user_id = found['id']
                    self.server.login_attempts[self.client_address[0]] = []
                token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
                db.execute('DELETE FROM sessions WHERE expires<=?', (int(time.time()),))
                db.execute('INSERT INTO sessions(token,user_id,csrf,expires) VALUES(?,?,?,?)', (token, user_id, csrf, int(time.time()) + 12*3600))
                db.commit()
                secure='; Secure' if self.server.access.secure_cookie(host,self.headers.get('Origin'),self.headers.get('X-Forwarded-Proto')) else ''
                self.respond(200, {'ok': True}, extra={'Set-Cookie': f'{self.server.cookie_name}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200{secure}'})
                return
            if not user:
                self.respond(401, {'error': 'Inicia sesión para continuar.'})
                return
            if not post and endpoint == 'rate-gate':
                on = local_today().isoformat()
                rate = db.execute('SELECT rate FROM exchange_rates WHERE rate_date=?', (on,)).fetchone()
                self.respond(200, {'today': on, 'rate': rate['rate'] if rate else '', 'role': user['role'],
                                   'school': {k:v for k,v in db.execute('SELECT key,value FROM settings') if k in ('school_name','institution_type','logo')}})
                return
            if endpoint not in ('confirm-rate','rate-gate','logout','backup','health','demo-exit') and user['rate_confirmed_on'] != local_today().isoformat():
                self.respond(428, {'error': 'Confirma la tasa BCV de hoy antes de continuar.'})
                return
            if post:
                if not secrets.compare_digest(self.headers.get('X-CSRF-Token', ''), user['csrf']):
                    raise PermissionError('Sesión inválida. Recarga la página.')
                if endpoint == 'demo-exit':
                    if not self.server.demo:
                        raise PermissionError('Solo puedes borrar una sesión de prueba.')
                    db.rollback()
                    self.respond(200, {'ok': True})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
                if self.server.demo and endpoint == 'settings' and data.get('backup_directory'):
                    raise ValidationError('Las pruebas no se copian a USB ni a la nube. Deja vacía la segunda carpeta de respaldos.')
                if endpoint == 'backup-now':
                    if user['role']!='admin' or self.server.demo:
                        raise PermissionError('Solo administración puede respaldar los datos reales.')
                    db.commit()
                    status = self.server.make_backup()
                    self.respond(200,status)
                    return
                if endpoint == 'reset-records':
                    if self.server.demo:
                        raise ValidationError('Cierra el modo prueba para borrar sus datos. No se vacía la base real desde aquí.')
                    with self.server.backup_lock:
                        result = reset_records(db, data, user)
                    db.commit()
                    self.respond(200, result)
                    return
                if endpoint == 'confirm-rate':
                    on = local_today().isoformat()
                    if data.get('rate_date') != on:
                        raise ValidationError('Confirma la tasa para la fecha actual.')
                    if user['role'] == 'reader':
                        if not db.execute('SELECT 1 FROM exchange_rates WHERE rate_date=?', (on,)).fetchone():
                            raise ValidationError('Administración o caja debe registrar la tasa de hoy primero.')
                    else:
                        mutate(db, 'rates', {'rate_date': on, 'rate': data.get('rate'),'rate_change_confirmed':data.get('rate_change_confirmed')}, user)
                    db.execute('UPDATE sessions SET rate_confirmed_on=? WHERE token=?', (on, user['token']))
                    audit(db, user['id'], 'confirm_rate', {'date': on})
                    result = {'ok': True}
                elif endpoint == 'logout':
                    db.execute('DELETE FROM sessions WHERE token=?', (user['token'],))
                    result = {'ok': True}
                else:
                    if endpoint in ('import-roster','transition-year') and data.get('preview') is not True and user['role']=='admin':
                        status=self.server.make_backup()
                        if status.get('local_error'): raise ValidationError('No se puede importar sin completar primero un respaldo local.')
                    result = mutate(db, endpoint, data, user)
                db.commit()
                if endpoint in ('payments','expenses','salary-receipts','void-payment','void-expense','close-cash','reopen-cash','settings','guardian-documents','payment-plans','cancel-plan') or (endpoint in ('import-roster','transition-year') and data.get('preview') is not True):
                    status=self.server.make_backup()
                    if status.get('local_error') or status.get('secondary_error'):
                        result['backup_warning']=status.get('local_error') or status.get('secondary_error')
                self.respond(200, result)
                return
            public_user = {k:v for k,v in user.items() if k not in ('token', 'csrf')}
            if endpoint == 'state':
                result=snapshot(db, public_user)
                result['backup']=self.server.backup_status()
                result['demo']=self.server.demo
                result['access']=self.server.access.snapshot()
                self.respond(200, result)
            elif endpoint == 'reset-preview':
                if self.server.demo or user['role'] != 'admin':
                    raise PermissionError('Esta operación solo está disponible para administración en el sistema real.')
                self.respond(200, reset_preview(db))
            elif endpoint=='import-template':
                if user['role']!='admin': raise PermissionError('Solo administración puede importar alumnos.')
                xlsx=parse_qs(url.query).get('format',['csv'])[0]=='xlsx'
                self.respond(200,import_template(xlsx,[r[0] for r in db.execute('SELECT name FROM grades ORDER BY name')],dict(db.execute('SELECT key,value FROM settings'))),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if xlsx else 'text/csv; charset=utf-8',
                    {'Content-Disposition':f'attachment; filename="plantilla-alumnos.{"xlsx" if xlsx else "csv"}"'})
            elif endpoint=='import-guide':
                if user['role']!='admin': raise PermissionError('Solo administración puede importar alumnos.')
                from .import_guide import FIELDS, STEPS
                self.respond(200,{'fields':FIELDS,'steps':STEPS})
            elif endpoint=='cash-preview':
                self.respond(200,cash_summary(db,parse_qs(url.query).get('date',[local_today().isoformat()])[0]))
            elif endpoint=='backup-status':
                self.respond(200,self.server.backup_status())
            elif endpoint=='year-roster':
                if user['role']!='admin': raise PermissionError('Solo administración puede realizar el pase de año.')
                self.respond(200,roster_for_year(db,parse_qs(url.query).get('year',[''])[0]))
            elif endpoint.startswith(('payment-plan/','year-transition/')):
                kind,raw=endpoint.split('/');target=integer(raw.removesuffix('.pdf'),1,2147483647)
                table='payment_plans' if kind=='payment-plan' else 'year_transitions'
                r=db.execute(f'SELECT * FROM {table} WHERE id=?',(target,)).fetchone()
                if not r: raise ValidationError('Documento inexistente.')
                document=dict(json.loads(r['snapshot_json']),id=target)
                self.server.mark_document(document)
                if kind=='payment-plan':document.update(cancelled=r['cancelled'],cancel_reason=r['cancel_reason'])
                if raw.endswith('.pdf'):
                    self.respond(200,render_pdf(kind,document),'application/pdf',{'Content-Disposition':f'attachment; filename="{kind}-{target:06d}.pdf"'})
                else:self.respond(200,document)
            elif endpoint.startswith('guardian-account/'):
                self.respond(200,guardian_account(db,endpoint.split('/')[-1]))
            elif endpoint.startswith(('guardian-document/','cash-close/')):
                kind,raw=endpoint.split('/'); target=integer(raw.removesuffix('.pdf'),1,2147483647)
                document=load_administrative_document(db,kind,target)
                self.server.mark_document(document)
                if raw.endswith('.pdf'):
                    self.respond(200,render_pdf(kind,document),'application/pdf',
                        {'Content-Disposition':f'attachment; filename="{kind}-{target:06d}.pdf"'})
                else: self.respond(200,document)
            elif endpoint.startswith(('enrollment/', 'payroll-plan/', 'salary-receipt/')):
                kind, raw = endpoint.split('/')
                pdf = raw.endswith('.pdf')
                target = integer(raw.removesuffix('.pdf'), 1, 2147483647)
                document = load_salary_receipt(db, target) if kind == 'salary-receipt' else load_document(db, kind, target)
                self.server.mark_document(document)
                if pdf:
                    self.respond(200, render_pdf(kind, document), 'application/pdf',
                                 {'Content-Disposition': f'attachment; filename="{kind}-{target:06d}.pdf"'})
                else:
                    self.respond(200, document)
            elif endpoint.startswith('receipt/'):
                raw = endpoint.split('/')[-1]
                pdf = raw.endswith('.pdf')
                target = integer(raw.removesuffix('.pdf'), 1, 2147483647)
                payment = db.execute('''SELECT p.*,s.name AS student_name,s.document AS student_document,g.name AS guardian_name,
                  g.document AS guardian_document,u.name AS operator FROM payments p JOIN students s ON s.id=p.student_id
                  JOIN guardians g ON g.id=s.guardian_id JOIN users u ON u.id=p.created_by WHERE p.id=?''', (target,)).fetchone()
                if not payment:
                    self.respond(404, {'error': 'Recibo inexistente.'})
                    return
                payment = dict(payment)
                frozen = json.loads(payment.pop('receipt_snapshot'))
                payment.pop('request_key', None)
                payment.update(frozen['person'])
                payment['operator'] = frozen['operator']
                for key in ('balance_before','balance_after','payment_status'):
                    payment[key] = frozen.get(key)
                # Legacy receipts can use the last issued enrollment at payment creation.
                # Never substitute today's grade for an unknown historical grade.
                if not payment.get('grade_name'):
                    prior = db.execute('''SELECT snapshot_json FROM enrollment_documents
                        WHERE student_id=? AND created_at<=? ORDER BY created_at DESC,id DESC LIMIT 1''',
                        (payment['student_id'],payment['created_at'])).fetchone()
                    student = json.loads(prior[0])['student'] if prior else {}
                    payment['grade_name'] = student.get('grade_name','')
                    payment['student_school_year'] = student.get('school_year')
                document = {'payment': payment, 'settings': frozen['school'],
                  'allocations': frozen.get('allocations') or rows(db, '''SELECT a.amount,c.concept,c.period FROM allocations a JOIN charges c
                      ON c.id=a.charge_id WHERE a.payment_id=?''', (target,))}
                self.server.mark_document(document)
                if pdf:
                    paper = parse_qs(url.query).get('paper',['a4'])[0]
                    self.respond(200, render_pdf('receipt', document, paper), 'application/pdf',
                                 {'Content-Disposition': f'attachment; filename="recibo-R-{target:06d}.pdf"'})
                else:
                    self.respond(200, document)
            elif endpoint == 'export':
                state = snapshot(db, public_user)
                kind = parse_qs(url.query).get('type', ['arrears'])[0]
                if kind == 'arrears':
                    entries = [{'Alumno': c['student_name'], 'Representante': c['guardian_name'], 'Telefono': c['guardian_phone'],
                      'Grado': c['grade_name'], 'Concepto': c['concept'], 'Periodo': c['period'], 'Vencimiento': c['due_date'],
                      'Dias': c['days_overdue'], 'Deuda USD': f"{c['balance']/100:.2f}"} for c in state['charges'] if c['overdue']]
                    columns = ['Alumno','Representante','Telefono','Grado','Concepto','Periodo','Vencimiento','Dias','Deuda USD']
                elif kind == 'payments':
                    entries = [{'Recibo': f"R-{p['id']:06}", 'Fecha': p['paid_on'], 'Alumno': p['student_name'], 'Moneda': p['currency'],
                      'Recibido': f"{p['received_amount']/100:.2f}", 'Tasa Bs por USD': p['exchange_rate'], 'Equivalente USD': f"{p['amount']/100:.2f}",
                      'Metodo': p['method'], 'Referencia': p['reference'], 'Estado': 'Anulado' if p['voided'] else 'Valido'} for p in state['payments']]
                    columns = ['Recibo','Fecha','Alumno','Moneda','Recibido','Tasa Bs por USD','Equivalente USD','Metodo','Referencia','Estado']
                elif kind == 'students':
                    entries = [{'Alumno': s['name'], 'Codigo': s['student_code'], 'Documento': s['document'], 'Grado': s['grade_name'], 'Ano escolar': s['school_year'],
                      'Representante': s['guardian_name'], 'Telefono': s['guardian_phone'], 'Estado': s['status'],
                      'Saldo USD': f"{s['balance']/100:.2f}"} for s in state['students']]
                    columns = ['Alumno','Codigo','Documento','Grado','Ano escolar','Representante','Telefono','Estado','Saldo USD']
                elif kind == 'expenses':
                    entries = [{'Fecha': e['spent_on'], 'Concepto': e['concept'], 'Categoria': e['category'], 'Moneda': e['currency'],
                      'Pagado': f"{e['received_amount']/100:.2f}", 'Tasa Bs por USD': e['exchange_rate'],
                      'Equivalente USD': f"{e['amount']/100:.2f}", 'Estado': 'Anulado' if e['voided'] else 'Valido'} for e in state['expenses']]
                    columns = ['Fecha','Concepto','Categoria','Moneda','Pagado','Tasa Bs por USD','Equivalente USD','Estado']
                else:
                    raise ValidationError('Reporte desconocido.')
                buffer = io.StringIO(newline='')
                writer = csv.DictWriter(buffer, fieldnames=columns, delimiter=';')
                writer.writeheader()
                for entry in entries:
                    writer.writerow({k: "'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for k,v in entry.items()})
                self.respond(200, buffer.getvalue().encode('utf-8-sig'), 'text/csv; charset=utf-8',
                             {'Content-Disposition': f'attachment; filename="{kind}-{local_today()}.csv"'})
            elif endpoint == 'backup':
                if self.server.demo:
                    raise PermissionError('Los datos de prueba son temporales y no se exportan como respaldos del colegio.')
                if user['role'] != 'admin':
                    raise PermissionError('Solo administración puede descargar respaldos.')
                with tempfile.TemporaryDirectory() as temp:
                    path = Path(temp) / 'colegio.sqlite3'
                    consistent_backup(self.server.db_path, path)
                    payload = path.read_bytes()
                self.respond(200, payload, 'application/octet-stream',
                             {'Content-Disposition': f'attachment; filename="colegio-{local_today()}.sqlite3"'})
            elif endpoint == 'health':
                self.respond(200, {'ok': db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'})
            elif endpoint == 'maintenance-review':
                if user['role']!='admin': raise PermissionError('Solo administración puede revisar la base.')
                from .maintenance import review_database
                self.respond(200,review_database(db))
            else:
                self.respond(404, {'error': 'Operación inexistente.'})
        except PermissionError as error:
            self.respond(403, {'error': str(error)})
        except RateConfirmationRequired as error:
            self.respond(409,{'error':str(error),'requires_rate_confirmation':True,'old_rate':error.old,'new_rate':error.new})
        except (ValidationError, json.JSONDecodeError, ValueError, TypeError, KeyError) as error:
            self.respond(400, {'error': str(error) if isinstance(error, ValidationError) else 'Datos inválidos.'})
        except sqlite3.IntegrityError:
            self.respond(400, {'error': 'Registro duplicado, referencia inexistente o estado inválido. Revisa los datos.'})
        except Exception:
            traceback.print_exc()
            self.respond(500, {'error': 'No se pudo completar la operación. Consulta el registro del servidor.'})
        finally:
            if db is not None:
                db.close()  # Rolls back uncommitted writes on errors.


@contextmanager
def open_school(path, port, demo=False, remote_origin=''):
    """Own the data lock and resources for both CLI and desktop lifetimes."""
    path=Path(path)
    with DataLock(path.parent):
        if not path.exists() and any((path.parent / 'backups').glob('*.sqlite3')):
            raise SystemExit('No se encuentra la base de datos, pero hay respaldos anteriores. '
                             'Ejecuta Restaurar-respaldo.bat para recuperar tus datos antes de abrir Aula. '
                             'No se ha creado una base vacía.')
        if path.exists():
            with closing(connect(path)) as existing:
                needs_upgrade = existing.execute('PRAGMA user_version').fetchone()[0] < SCHEMA_VERSION
            if needs_upgrade:
                consistent_backup(path, path.parent / 'backups' / f'antes-actualizacion-{datetime.now():%Y%m%d-%H%M%S}.sqlite3')
        initialize(path)
        with closing(connect(path)) as db, db:
            synchronize_monthly_charges(db)
            if remote_origin and not db.execute("SELECT 1 FROM users WHERE role='admin' LIMIT 1").fetchone():
                raise SystemExit('Crea primero tu administrador en esta PC con Iniciar-Aula.bat y luego abre Iniciar-Red.bat. No se ha habilitado el acceso remoto.')
            if demo:
                demo_admin = db.execute('INSERT INTO users(username,name,password,role) VALUES(?,?,?,?)',
                    ('__prueba__', 'Administrador de prueba', hash_password(secrets.token_urlsafe(32)), 'admin')).lastrowid
        if not demo:
            daily_backup(path)
            automatic_backup(path)
        try:
            server = SchoolServer(('127.0.0.1', port), str(path), demo=demo,remote_origin=remote_origin)
        except OSError as error:
            raise SystemExit(f'No se pudo iniciar: {error}. Verifica si el sistema ya está abierto o usa otro puerto.')
        if demo:
            server.demo_admin_id = demo_admin
        try:
            yield server
        finally:
            server.server_close()


def run_server(path, args, demo=False):
    with open_school(path,args.port,demo,args.remote_origin or '') as server:
        print(f'{"MODO PRUEBA" if demo else "Colegio"} abierto en http://127.0.0.1:{server.server_port} · datos: {path}', flush=True)
        print('Mantén esta ventana abierta. Ctrl+C para cerrar de forma segura.', flush=True)
        if args.remote_origin:
            print(f'Acceso privado del colegio y casa: {server.access.origin} (requiere Tailscale Serve activo).',flush=True)
        try:
            if args.open_browser:
                webbrowser.open(f'http://127.0.0.1:{server.server_port}')
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def main():
    parser = argparse.ArgumentParser(description='Administración escolar local o con acceso privado a una PC central Windows.')
    parser.add_argument('--port', type=int)
    parser.add_argument('--data-dir')
    parser.add_argument('--open-browser', action='store_true')
    parser.add_argument('--demo', action='store_true', help='Administrador de prueba con datos temporales y aislados.')
    access=parser.add_mutually_exclusive_group()
    access.add_argument('--remote-origin',help='Enlace HTTPS privado de Tailscale Serve.')
    access.add_argument('--network-config',help='Archivo red.json creado por Configurar-Red.bat.')
    args = parser.parse_args()
    if args.demo and args.data_dir is not None:
        parser.error('--demo no admite --data-dir: nunca se abre una base existente en modo prueba.')
    if args.demo and (args.remote_origin is not None or args.network_config is not None):
        parser.error('El modo de prueba es local y no admite configuración de red.')
    try:
        args.remote_origin=load_config(args.network_config) if args.network_config else PrivateAccess(args.remote_origin or '').origin
    except ValueError as error:
        parser.error(str(error))
    if args.port is None:
        args.port = 8766 if args.demo else 8765
    previous_signal = None
    if threading.current_thread() is threading.main_thread():
        def terminate(*_):
            raise KeyboardInterrupt
        previous_signal = signal.signal(signal.SIGTERM, terminate)
    try:
        if args.demo:
            with DemoWorkspace() as directory:
                run_server(directory / 'colegio.sqlite3', args, demo=True)
            print('Sesión de prueba cerrada. Sus datos temporales fueron eliminados.', flush=True)
        else:
            run_server(Path(args.data_dir or ROOT / 'data').resolve() / 'colegio.sqlite3', args)
    except RuntimeError as error:
        raise SystemExit(str(error))
    finally:
        if previous_signal is not None:
            signal.signal(signal.SIGTERM, previous_signal)


if __name__ == '__main__':
    main()
