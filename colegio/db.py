import calendar
import hashlib
import json
import secrets
import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from .branding import SCHEMA_VERSION, SCHOOL_PROFILE


class ValidationError(ValueError):
    pass


class RateConfirmationRequired(ValidationError):
    def __init__(self,old,new):
        self.old,self.new=old,new
        super().__init__(f'La tasa cambia más del 10 %: de Bs {old} a Bs {new} por USD. Revisa el valor antes de confirmarlo.')


def local_today():
    return datetime.now(timezone(timedelta(hours=-4))).date()


def money(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount > Decimal('999999999'):
            raise ValidationError('Importe fuera de rango.')
        if amount != amount.quantize(Decimal('0.01')):
            raise ValidationError('Usa como máximo dos decimales.')
        return int(amount * 100)
    except (InvalidOperation, TypeError):
        raise ValidationError('Importe inválido.')


def required(data, key, limit=200):
    value = str(data.get(key, '')).strip()
    if not value or len(value) > limit:
        raise ValidationError(f'El campo {key} es obligatorio (máximo {limit} caracteres).')
    return value


def valid_date(value):
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError:
        raise ValidationError('Fecha inválida; usa AAAA-MM-DD.')


def integer(value, minimum, maximum):
    try:
        result = int(value)
        if str(result) != str(value) or not minimum <= result <= maximum:
            raise ValueError()
        return result
    except (ValueError, TypeError):
        raise ValidationError(f'Usa un entero entre {minimum} y {maximum}.')


def hash_password(password):
    if not isinstance(password, str) or not 10 <= len(password) <= 256:
        raise ValidationError('La contraseña debe tener entre 10 y 256 caracteres.')
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 300000).hex()
    return f'{salt}${digest}'


def valid_rate(value):
    try:
        rate = Decimal(str(value))
        if not rate.is_finite() or rate <= 0 or rate > 1000000 or rate != rate.quantize(Decimal('0.000001')):
            raise ValueError()
        return str(rate)
    except (InvalidOperation, ValueError):
        raise ValidationError('Tasa BCV inválida; usa hasta seis decimales y un valor positivo.')


def convert_received(db, data, on):
    currency = data.get('currency', 'USD')
    received = money(data.get('amount'))
    if currency not in ('USD', 'VES'):
        raise ValidationError('Moneda inválida.')
    rate = '1'
    amount = received
    if currency == 'VES':
        row = db.execute('SELECT rate FROM exchange_rates WHERE rate_date=?', (on,)).fetchone()
        if not row:
            raise ValidationError('Registra primero la tasa BCV para la fecha de la operación.')
        rate = row['rate']
        amount = int((Decimal(received) / Decimal(rate)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    if received <= 0 or amount <= 0:
        raise ValidationError('El equivalente en dólares debe ser al menos 0,01 USD.')
    return amount, currency, received, rate


def check_password(password, stored):
    salt, expected = stored.split('$')
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 300000).hex()
    return secrets.compare_digest(expected, actual)


def connect(path):
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA synchronous=FULL')
    db.execute('PRAGMA busy_timeout=30000')
    return db


def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db, db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS year_transitions(id INTEGER PRIMARY KEY,
                snapshot_json TEXT NOT NULL,created_at TEXT NOT NULL,created_by INTEGER NOT NULL REFERENCES users(id));
            CREATE TABLE IF NOT EXISTS payment_plans(id INTEGER PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES students(id),snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,created_by INTEGER NOT NULL REFERENCES users(id),
                cancelled INTEGER NOT NULL DEFAULT 0,cancel_reason TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
          name TEXT NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','cashier','reader')));
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),
          csrf TEXT NOT NULL,expires INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS exchange_rates(rate_date TEXT PRIMARY KEY,rate TEXT NOT NULL,source TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS collection_notes(id INTEGER PRIMARY KEY,student_id INTEGER NOT NULL REFERENCES students(id),
          note TEXT NOT NULL,promised_on TEXT,created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS guardians(id INTEGER PRIMARY KEY,name TEXT NOT NULL,document TEXT UNIQUE NOT NULL,
          phone TEXT NOT NULL DEFAULT '',email TEXT NOT NULL DEFAULT '',address TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS grades(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,capacity INTEGER NOT NULL DEFAULT 30);
        CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY,name TEXT NOT NULL,document TEXT UNIQUE NOT NULL,
          birth_date TEXT NOT NULL,guardian_id INTEGER NOT NULL REFERENCES guardians(id),
          grade_id INTEGER NOT NULL REFERENCES grades(id),school_year INTEGER NOT NULL,
          monthly_fee INTEGER NOT NULL CHECK(monthly_fee>=0),discount INTEGER NOT NULL CHECK(discount BETWEEN 0 AND 100),
          status TEXT NOT NULL CHECK(status IN ('active','inactive')),notes TEXT NOT NULL DEFAULT '',
          enrollment_start TEXT NOT NULL,enrollment_end TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS charges(id INTEGER PRIMARY KEY,student_id INTEGER NOT NULL REFERENCES students(id),
          period TEXT NOT NULL,concept TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>0),due_date TEXT NOT NULL,
          cancelled INTEGER NOT NULL DEFAULT 0,UNIQUE(student_id,period,concept));
        CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY,student_id INTEGER NOT NULL REFERENCES students(id),
          amount INTEGER NOT NULL CHECK(amount>0),paid_on TEXT NOT NULL,method TEXT NOT NULL,reference TEXT NOT NULL DEFAULT '',
          notes TEXT NOT NULL DEFAULT '',created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,
          voided INTEGER NOT NULL DEFAULT 0,void_reason TEXT NOT NULL DEFAULT '',
          request_key TEXT UNIQUE NOT NULL,currency TEXT NOT NULL,received_amount INTEGER NOT NULL,exchange_rate TEXT NOT NULL,
          receipt_snapshot TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS allocations(payment_id INTEGER NOT NULL REFERENCES payments(id),
          charge_id INTEGER NOT NULL REFERENCES charges(id),amount INTEGER NOT NULL CHECK(amount>0),PRIMARY KEY(payment_id,charge_id));
        CREATE TABLE IF NOT EXISTS employees(id INTEGER PRIMARY KEY,name TEXT NOT NULL,document TEXT UNIQUE NOT NULL,
          position TEXT NOT NULL,phone TEXT NOT NULL DEFAULT '',salary INTEGER NOT NULL CHECK(salary>=0),
          status TEXT NOT NULL CHECK(status IN ('active','inactive')));
        CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY,concept TEXT NOT NULL,category TEXT NOT NULL,
          amount INTEGER NOT NULL CHECK(amount>0),spent_on TEXT NOT NULL,reference TEXT NOT NULL DEFAULT '',
          employee_id INTEGER REFERENCES employees(id),created_by INTEGER NOT NULL REFERENCES users(id),
          voided INTEGER NOT NULL DEFAULT 0,void_reason TEXT NOT NULL DEFAULT '',
          currency TEXT NOT NULL,received_amount INTEGER NOT NULL,exchange_rate TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),
          action TEXT NOT NULL,details TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS charges_student ON charges(student_id);
        CREATE INDEX IF NOT EXISTS payments_student ON payments(student_id);
        CREATE INDEX IF NOT EXISTS allocations_charge ON allocations(charge_id);
        ''')
        defaults = {'school_name': 'U.E.C. Alejandro Von Humboldt', 'currency': 'USD', 'due_day': '10', 'start_month': '9',
                    'school_year': str(local_today().year if local_today().month >= 9 else local_today().year - 1), 'address': '', 'phone': '', 'rif': '', 'email': '', 'website': ''}
        defaults.update(legal_name='', fiscal_address='', logo='')
        db.executemany('INSERT OR IGNORE INTO settings VALUES(?,?)', defaults.items())
        # Additive upgrades preserve IDs, balances and historical receipts.
        additions = {
            'sessions': {'rate_confirmed_on': "TEXT NOT NULL DEFAULT ''"},
            'students': {'student_code': "TEXT NOT NULL DEFAULT ''"},
            'employees': {'position_id': 'INTEGER REFERENCES positions(id)',
                'bank': "TEXT NOT NULL DEFAULT ''", 'bank_account': "TEXT NOT NULL DEFAULT ''",
                'account_holder': "TEXT NOT NULL DEFAULT ''", 'holder_document': "TEXT NOT NULL DEFAULT ''",
                'account_type': "TEXT NOT NULL DEFAULT ''"}}
        db.execute('CREATE TABLE IF NOT EXISTS positions(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL)')
        for table, columns in additions.items():
            existing = {r['name'] for r in db.execute(f'PRAGMA table_info({table})')}
            for name, definition in columns.items():
                if name not in existing:
                    db.execute(f'ALTER TABLE {table} ADD COLUMN {name} {definition}')
        for student in db.execute("SELECT id FROM students WHERE student_code='' ").fetchall():
            db.execute('UPDATE students SET student_code=? WHERE id=?', (f"AL-{student['id']:06d}", student['id']))
        db.execute('CREATE UNIQUE INDEX IF NOT EXISTS students_code ON students(student_code)')
        for employee in db.execute('SELECT id,position FROM employees WHERE position_id IS NULL').fetchall():
            db.execute('INSERT OR IGNORE INTO positions(name) VALUES(?)', (employee['position'],))
            db.execute('UPDATE employees SET position_id=(SELECT id FROM positions WHERE name=?) WHERE id=?',
                       (employee['position'], employee['id']))
        db.executescript("""
            CREATE TABLE IF NOT EXISTS enrollment_documents(id INTEGER PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES students(id),snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,created_by INTEGER NOT NULL REFERENCES users(id));
            CREATE TABLE IF NOT EXISTS payroll_plans(id INTEGER PRIMARY KEY,snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,created_by INTEGER NOT NULL REFERENCES users(id));
            CREATE TABLE IF NOT EXISTS monthly_assessments(
                student_id INTEGER NOT NULL REFERENCES students(id),period TEXT NOT NULL,
                amount INTEGER NOT NULL CHECK(amount>=0),charge_id INTEGER REFERENCES charges(id),
                assessed_at TEXT NOT NULL,PRIMARY KEY(student_id,period));
        """)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS guardian_documents(id INTEGER PRIMARY KEY,
                snapshot_json TEXT NOT NULL,created_at TEXT NOT NULL,
                created_by INTEGER NOT NULL REFERENCES users(id));
            CREATE TABLE IF NOT EXISTS cash_closures(id INTEGER PRIMARY KEY,
                closed_on TEXT NOT NULL,snapshot_json TEXT NOT NULL,created_at TEXT NOT NULL,
                created_by INTEGER NOT NULL REFERENCES users(id),reopened_at TEXT,
                reopen_reason TEXT NOT NULL DEFAULT '');
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_cash_close
                ON cash_closures(closed_on) WHERE reopened_at IS NULL;
        ''')
        if 'method' not in {r['name'] for r in db.execute('PRAGMA table_info(expenses)')}:
            db.execute("ALTER TABLE expenses ADD COLUMN method TEXT NOT NULL DEFAULT 'No especificado'")
        db.execute("INSERT OR IGNORE INTO settings VALUES('backup_directory','')")
        if db.execute('PRAGMA user_version').fetchone()[0] < 4:
            # Apply the owner's fiscal identity once, without altering issued snapshots
            # or operational settings. Later manual edits survive every restart.
            db.executemany('UPDATE settings SET value=? WHERE key=?', [(v,k) for k,v in SCHOOL_PROFILE.items()])
            db.execute("UPDATE settings SET value='U.E.C. Alejandro Von Humboldt' WHERE key='school_name' AND value='Mi colegio'")
            audit(db, None, 'school-profile', SCHOOL_PROFILE)
        db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')



def audit(db, user_id, action, details):
    db.execute('INSERT INTO audit(user_id,action,details,created_at) VALUES(?,?,?,?)',
               (user_id, action, json.dumps(details, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))


BALANCES = '''SELECT c.*,COALESCE((SELECT SUM(a.amount) FROM allocations a JOIN payments p ON p.id=a.payment_id
    WHERE a.charge_id=c.id AND p.voided=0),0) AS paid FROM charges c WHERE c.cancelled=0'''


def charges(db, student_id=None):
    query = BALANCES
    params = []
    if student_id is not None:
        query += ' AND c.student_id=?'
        params.append(student_id)
    rows = [dict(r) for r in db.execute(query + ' ORDER BY due_date,c.id', params)]
    today = local_today().isoformat()
    for row in rows:
        row['balance'] = row['amount'] - row['paid']
        row['overdue'] = row['balance'] > 0 and row['due_date'] < today
    return rows


def assess_month(db, student, first, due_day):
    """Assess once, including full scholarships and previously cancelled charges."""
    period = first.strftime('%Y-%m')
    if db.execute('SELECT 1 FROM monthly_assessments WHERE student_id=? AND period=?',
                  (student['id'], period)).fetchone():
        return 0, 0
    existing = db.execute("SELECT id,amount FROM charges WHERE student_id=? AND period=? AND concept='Mensualidad'",
                          (student['id'], period)).fetchone()
    created = 0
    amount = (student['monthly_fee'] * (100 - student['discount']) + 50) // 100
    charge_id = None
    if existing:
        charge_id, amount = existing['id'], existing['amount']
    elif amount:
        day = min(due_day, calendar.monthrange(first.year, first.month)[1])
        result = db.execute('''INSERT INTO charges(student_id,period,concept,amount,due_date)
            VALUES(?,?,?,?,?)''', (student['id'], period, 'Mensualidad', amount, first.replace(day=day).isoformat()))
        charge_id, created = result.lastrowid, 1
    db.execute('INSERT INTO monthly_assessments VALUES(?,?,?,?,?)',
               (student['id'], period, amount, charge_id, datetime.now(timezone.utc).isoformat()))
    return created, 1


def synchronize_monthly_charges(db, today=None):
    """Bring active enrollments through this month; caller owns the transaction."""
    today = today or local_today()
    settings = dict(db.execute('SELECT key,value FROM settings'))
    start_month, due_day = int(settings['start_month']), int(settings['due_day'])
    created = assessed = 0
    for student in db.execute("SELECT * FROM students WHERE status='active'").fetchall():
        start = max(date.fromisoformat(student['enrollment_start']), date(student['school_year'], start_month, 1))
        academic_end = date(student['school_year'] + 1, start_month, 1) - timedelta(days=1)
        end = min(date.fromisoformat(student['enrollment_end']), academic_end, today)
        if start > end:
            continue
        first = start.replace(day=1)
        while first <= end:
            new_charges, new_assessments = assess_month(db, student, first, due_day)
            created += new_charges
            assessed += new_assessments
            first = date(first.year + (first.month == 12), first.month % 12 + 1, 1)
    if assessed:
        audit(db, None, 'automatic_monthly_charges', {'through': today.strftime('%Y-%m'),
              'created': created, 'assessed': assessed})
    return {'created': created, 'assessed': assessed}


def generate_month(db, data, user_id):
    period = required(data, 'period', 7)
    try:
        first = date.fromisoformat(period + '-01')
    except ValueError:
        raise ValidationError('Período inválido; usa AAAA-MM.')
    settings = dict(db.execute('SELECT key,value FROM settings'))
    school_year = integer(data.get('school_year', settings['school_year']), 2000, 2100)
    start_month = int(settings['start_month'])
    start = date(school_year, start_month, 1)
    end = date(school_year + 1, start_month, 1)
    if not start <= first < end:
        raise ValidationError('El período no corresponde al año escolar seleccionado.')
    due_day = int(settings['due_day'])
    created = 0
    month_end = first.replace(day=calendar.monthrange(first.year, first.month)[1]).isoformat()
    for student in db.execute("""SELECT * FROM students WHERE status='active' AND school_year=?
      AND enrollment_start<=? AND enrollment_end>=?""", (school_year, month_end, first.isoformat())).fetchall():
        new_charges, _ = assess_month(db, student, first, due_day)
        created += new_charges
    audit(db, user_id, 'generate_month', {'period': period, 'created': created})
    return {'created': created}


def record_payment(db, data, user_id):
    student_id = integer(data.get('student_id'), 1, 2147483647)
    paid_on = valid_date(data.get('paid_on'))
    if paid_on > local_today().isoformat():
        raise ValidationError('La fecha del pago no puede ser futura.')
    method = required(data, 'method')
    if method not in ('Efectivo', 'Transferencia', 'Tarjeta', 'Otro'):
        raise ValidationError('Método de pago inválido.')
    request_key = required(data, 'request_key', 100)
    existing = db.execute('SELECT * FROM payments WHERE request_key=?', (request_key,)).fetchone()
    reference, notes = str(data.get('reference', ''))[:200], str(data.get('notes', ''))[:1000]
    if existing:
        if (existing['student_id'], existing['received_amount'], existing['currency'], existing['paid_on'], existing['method'], existing['reference'], existing['notes']) != (student_id, money(data.get('amount')), data.get('currency', 'USD'), paid_on, method, reference, notes):
            raise ValidationError('La clave de pago ya se usó con otros datos.')
        return {'id': existing['id'], 'duplicate': True}
    reference_key=''.join(reference.upper().split())
    repeated=[r['id'] for r in db.execute("SELECT id,reference FROM payments WHERE voided=0 AND reference<>''")
        if reference_key and ''.join(r['reference'].upper().split())==reference_key]
    if repeated:
        if data.get('duplicate_reference_confirmed') not in (True,'on'):
            raise ValidationError('La referencia ya aparece en otro pago válido. Revisa los recibos y confirma con un motivo si corresponde registrarla otra vez.')
        duplicate_reason=required(data,'duplicate_reason',500)
    amount, currency, received, rate = convert_received(db, data, paid_on)
    pending = [c for c in charges(db, student_id) if c['balance'] > 0]
    total = sum(c['balance'] for c in pending)
    if amount > total:
        raise ValidationError('El pago supera la deuda. Crea primero el cargo correspondiente al anticipo.')
    person = db.execute('''SELECT s.name AS student_name,s.document AS student_document,s.student_code,
       gr.name AS grade_name,s.school_year AS student_school_year,g.name AS guardian_name,
       g.document AS guardian_document,g.address AS guardian_address,g.phone AS guardian_phone
       FROM students s JOIN guardians g ON g.id=s.guardian_id JOIN grades gr ON gr.id=s.grade_id
       WHERE s.id=?''', (student_id,)).fetchone()
    receipt_snapshot = json.dumps({'person': dict(person), 'school': dict(db.execute('SELECT key,value FROM settings')),
                                  'operator': db.execute('SELECT name FROM users WHERE id=?', (user_id,)).fetchone()[0]}, ensure_ascii=False)
    result = db.execute('''INSERT INTO payments(student_id,amount,paid_on,method,reference,notes,created_by,created_at,request_key,currency,received_amount,exchange_rate,receipt_snapshot)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''', (student_id, amount, paid_on, method, reference,
      notes, user_id, datetime.now(timezone.utc).isoformat(), request_key, currency, received, rate, receipt_snapshot))
    remaining = amount
    for charge in pending:
        allocated = min(remaining, charge['balance'])
        db.execute('INSERT INTO allocations VALUES(?,?,?)', (result.lastrowid, charge['id'], allocated))
        remaining -= allocated
        if remaining == 0:
            break
    audit(db, user_id, 'payment', {'id': result.lastrowid, 'amount': amount, 'student_id': student_id})
    if repeated: audit(db,user_id,'duplicate-reference-confirmed',{'payment_id':result.lastrowid,'prior_ids':repeated,'reason':duplicate_reason})
    return {'id': result.lastrowid, 'duplicate': False}
