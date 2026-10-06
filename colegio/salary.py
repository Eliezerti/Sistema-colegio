"""Signed salary receipts tied to one recorded expense, with frozen payment details."""
import json
import re
from datetime import datetime, timezone

from .db import ValidationError, audit, integer, valid_date


def details(data):
    start, end = valid_date(data.get('period_start')), valid_date(data.get('period_end'))
    if start > end:
        raise ValidationError('El inicio del período de sueldo no puede ser posterior al fin.')
    hours = {}
    for key in ('entry_time', 'exit_time'):
        value = data.get(key)
        if not isinstance(value, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
            raise ValidationError('Completa las horas de entrada y salida con formato HH:MM.')
        hours[key] = value
    return dict(period_start=start, period_end=end, **hours, notes=str(data.get('salary_notes', ''))[:2000])


def issue_salary_receipt(db, expense_id, data, user_id):
    expense_id = integer(expense_id, 1, 2147483647)
    previous = db.execute('SELECT id FROM salary_receipts WHERE expense_id=?', (expense_id,)).fetchone()
    if previous:
        return previous['id']
    period = details(data)
    expense = db.execute('SELECT * FROM expenses WHERE id=?', (expense_id,)).fetchone()
    if not expense or expense['category'] != 'Nómina' or not expense['employee_id']:
        raise ValidationError('El recibo de sueldo requiere un pago de nómina asociado a un empleado.')
    if expense['voided']:
        raise ValidationError('No se puede emitir un recibo nuevo de un pago anulado.')
    employee = db.execute('SELECT * FROM employees WHERE id=?', (expense['employee_id'],)).fetchone()
    operator = db.execute('SELECT name FROM users WHERE id=?', (expense['created_by'],)).fetchone()[0]
    created = datetime.now(timezone.utc).isoformat()
    document = dict(expense=dict(expense), employee=dict(employee), **period,
                    school=dict(db.execute('SELECT key,value FROM settings')), operator=operator,
                    created_at=created, issued_on=expense['spent_on'])
    receipt_id = db.execute('INSERT INTO salary_receipts(expense_id,snapshot_json,created_at,created_by) VALUES(?,?,?,?)',
                          (expense_id, json.dumps(document, ensure_ascii=False), created, user_id)).lastrowid
    audit(db, user_id, 'salary_receipt', {'id': receipt_id, 'expense_id': expense_id})
    return receipt_id


def load_salary_receipt(db, receipt_id):
    row = db.execute('''SELECT r.*,e.voided,e.void_reason FROM salary_receipts r
                        JOIN expenses e ON e.id=r.expense_id WHERE r.id=?''',
                     (integer(receipt_id, 1, 2147483647),)).fetchone()
    if not row:
        raise ValidationError('Recibo de sueldo inexistente.')
    document = dict(json.loads(row['snapshot_json']), id=row['id'])
    document['expense'].update(voided=row['voided'], void_reason=row['void_reason'])
    return document
