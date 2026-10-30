"""Explicit future assessments around the unchanged payment engine. Integer cents only."""
import calendar
import hashlib
import json
from datetime import date, timedelta

from .db import (ValidationError, assess_month, audit, charges, convert_received,
                 integer, local_today, record_payment, required, valid_period)

LIMIT_KEY = 'advance_months_limit'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def month_after(first, offset=1):
    index = first.year * 12 + first.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)


def options(db, student_id):
    sid = integer(student_id, 1, 2147483647)
    pupil = db.execute('SELECT * FROM students WHERE id=?', (sid,)).fetchone()
    if not pupil:
        raise ValidationError('Selecciona un alumno existente.')
    config = dict(db.execute('SELECT key,value FROM settings'))
    limit = integer(config.get(LIMIT_KEY, '3'), 0, 12)
    today = local_today().replace(day=1)
    pending = [dict(c, future=False) for c in charges(db, sid) if c['balance'] > 0]
    future = []
    start = date(pupil['school_year'], int(config['start_month']), 1)
    end = date(pupil['school_year'] + 1, int(config['start_month']), 1) - timedelta(days=1)
    fee = (pupil['monthly_fee'] * (100 - pupil['discount']) + 50) // 100
    if (pupil['status'] == 'active' and not pupil['archived']
            and pupil['school_year'] == int(config['school_year'])):
        for offset in range(1, limit + 1):
            first = month_after(today, offset)
            period = first.strftime('%Y-%m')
            last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
            if (not start <= first <= end or first.isoformat() > pupil['enrollment_end']
                    or last.isoformat() < pupil['enrollment_start']
                    or period < (pupil['billing_start'] or pupil['enrollment_start'][:7])):
                continue
            assessed = db.execute('SELECT amount FROM monthly_assessments WHERE student_id=? AND period=?',
                                  (sid, period)).fetchone()
            existing = db.execute("SELECT id FROM charges WHERE student_id=? AND period=? AND concept='Mensualidad'",
                                  (sid, period)).fetchone()
            if existing or assessed and assessed['amount']:
                continue
            amount = assessed['amount'] if assessed else fee
            due = first.replace(day=min(int(config['due_day']), last.day)).isoformat()
            future.append(dict(id='future:' + period, student_id=sid, period=period,
                concept='Mensualidad', amount=amount, balance=amount, paid=0, due_date=due,
                future=True, assessed=bool(assessed), overdue=False))
    result = dict(student_id=sid, pending=pending, future=future, fee=fee, limit=limit,
                  today=today.strftime('%Y-%m'))
    # Includes enrollment, tariff/discount and calendar so a stale form cannot silently freeze new terms.
    result['quote'] = digest(dict(options=result, pupil=dict(pupil), calendar={
        k:config.get(k) for k in ('school_year', 'start_month', 'due_day', LIMIT_KEY)}))
    return result


def selection(db, data, *, check_quote=False):
    periods = data.get('advance_periods', [])
    if (not isinstance(periods, list) or len(periods) > 12
            or any(not isinstance(p, str) for p in periods)
            or len(set(periods)) != len(periods)):
        raise ValidationError('Selecciona los meses por adelantado una sola vez y en orden.')
    for period in periods:
        valid_period(period)
    value = options(db, data.get('student_id'))
    if periods:
        if check_quote and data.get('advance_quote') != value['quote']:
            raise ValidationError('La tarifa, el calendario o el saldo cambió. Abre de nuevo el cobro y revisa los meses.')
        available = [c['period'] for c in value['future']]
        if any(p not in available for p in periods):
            raise ValidationError('Mes no disponible: revisa el máximo por adelantado, el ciclo vigente, el inicio de cobro y el fin de matrícula.')
        if periods != available[:len(periods)]:
            raise ValidationError('Selecciona meses consecutivos desde el primero disponible, sin saltar mensualidades.')
    return value, [c for c in value['future'] if c['period'] in periods]


def pending_with_future(db, data, *, check_quote=False):
    value, future = selection(db, data, check_quote=check_quote)
    pending = sorted(value['pending'] + [c for c in future if c['balance']],
                     key=lambda c:(c['due_date'], c['id'] if isinstance(c['id'], int) else 2147483648))
    return value, future, pending


def materialize(db, student_id, future, user_id):
    pupil = db.execute('SELECT * FROM students WHERE id=?', (student_id,)).fetchone()
    due = int(db.execute("SELECT value FROM settings WHERE key='due_day'").fetchone()[0])
    mapping, evaluated = {}, []
    for item in future:
        _, assessed = assess_month(db, pupil, date.fromisoformat(item['period'] + '-01'), due)
        row = db.execute('SELECT charge_id,amount FROM monthly_assessments WHERE student_id=? AND period=?',
                         (student_id, item['period'])).fetchone()
        if row['amount'] != item['amount']:
            raise ValidationError('Cambió la mensualidad. Revisa nuevamente antes de cobrar.')
        mapping[item['id']] = row['charge_id']
        if assessed:
            evaluated.append(dict(period=item['period'], amount=row['amount'], charge_id=row['charge_id']))
    if evaluated:
        audit(db, user_id, 'advance-months-prepared', dict(student_id=student_id, months=evaluated))
    return mapping, evaluated


def mark_new_receipt(db, payment_id, *, periods=None, selection_hash=None):
    row = db.execute('SELECT paid_on,receipt_snapshot FROM payments WHERE id=?', (payment_id,)).fetchone()
    frozen = json.loads(row['receipt_snapshot'])
    changed = False
    for line in frozen['allocations']:
        if line['concept'] == 'Mensualidad' and line['period'] > row['paid_on'][:7]:
            line['concept'] = f"Mensualidad {line['period']} (pagada por adelantado)"
            line['paid_in_advance'] = True
            changed = True
    if periods:
        frozen['advance_periods_prepared'] = periods
        frozen['advance_selection_hash'] = selection_hash
        changed = True
    if changed:
        db.execute('UPDATE payments SET receipt_snapshot=? WHERE id=?',
                   (json.dumps(frozen, ensure_ascii=False), payment_id))


def receive(db, data, user_id):
    prior = db.execute('SELECT id,receipt_snapshot FROM payments WHERE request_key=?',
                       (str(data.get('request_key', '')),)).fetchone()
    fingerprint = digest(dict(periods=data.get('advance_periods', []), charge_ids=data.get('charge_ids')))
    if prior:
        frozen = json.loads(prior['receipt_snapshot'])
        if (frozen.get('advance_periods_prepared', []) != data.get('advance_periods', [])
                or frozen.get('advance_selection_hash', fingerprint) != fingerprint):
            raise ValidationError('La clave de pago ya se usó con otros meses. No se registró otro cobro.')
        return record_payment(db, data, user_id)
    value, future, pending = pending_with_future(db, data, check_quote=True)
    if future:
        amount, _, _, _ = convert_received(db, data, data.get('paid_on'))
        remaining, covered = amount, []
        for charge in pending:
            if not remaining:
                break
            covered.append(charge['id'])
            remaining -= min(remaining, charge['balance'])
        expected = [c['id'] for c in future if c['balance']]
        selected = data.get('charge_ids')
        if any(i not in covered for i in expected) or selected != covered:
            raise ValidationError('El importe debe cubrir primero los cargos más antiguos y alcanzar el último mes seleccionado. Revisa la selección consecutiva.')
        if not expected:
            raise ValidationError('Beca completa: registra la evaluación sin cobro; no se necesita un pago ni un recibo.')
        materialize(db, value['student_id'], future, user_id)
    result = record_payment(db, data, user_id)
    mark_new_receipt(db, result['id'], periods=data.get('advance_periods'), selection_hash=fingerprint)
    return result


def prepare_waived(db, data, user_id):
    from .audit_chain import require
    from .clock_guard import require_database_clock
    require(db)
    require_database_clock(db)
    key = digest(required(data, 'request_key', 100))
    body = digest(data)
    for row in db.execute("SELECT details,user_id FROM audit WHERE action='advance-waiver' ORDER BY id DESC"):
        prior = json.loads(row['details'])
        if prior.get('request') == key:
            if row['user_id'] != user_id or prior.get('body') != body:
                raise ValidationError('La clave de evaluación ya se usó con otros datos o usuario.')
            return dict(prior['result'], assessed=0, duplicate=True)
    value, future = selection(db, data, check_quote=True)
    if not future or any(c['amount'] for c in future) or value['pending']:
        raise ValidationError('Esta acción es solo para meses con beca completa y sin deuda anterior. Los demás meses se preparan al cobrar.')
    _, evaluated = materialize(db, value['student_id'], future, user_id)
    result = dict(prepared=True, assessed=len(evaluated), duplicate=not evaluated, no_payment=True)
    audit(db, user_id, 'advance-waiver', dict(student_id=value['student_id'],
        periods=data['advance_periods'], request=key, body=body, result=result))
    return result


def paid_by_charge(db):
    return {r['charge_id']:r['amount'] for r in db.execute("""SELECT a.charge_id,SUM(a.amount) AS amount
        FROM allocations a JOIN payments p ON p.id=a.payment_id JOIN charges c ON c.id=a.charge_id
        WHERE p.voided=0 AND c.concept='Mensualidad' AND c.period>substr(p.paid_on,1,7)
        GROUP BY a.charge_id""")}


def decorate(entries, advanced):
    for entry in entries:
        received = advanced.get(entry['id'], 0)
        if received:
            entry['advance_paid'] = received
            entry['advance_label'] = 'Pagado por adelantado' if received >= entry['amount'] else 'Abono por adelantado'
    return entries


def payment_totals(db):
    return {r['payment_id']:r['amount'] for r in db.execute("""SELECT a.payment_id,SUM(a.amount) AS amount
        FROM allocations a JOIN payments p ON p.id=a.payment_id JOIN charges c ON c.id=a.charge_id
        WHERE p.voided=0 AND c.concept='Mensualidad' AND c.period>substr(p.paid_on,1,7)
        GROUP BY a.payment_id""")}
