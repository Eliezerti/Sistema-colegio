"""Explicit administrative reset with an immutable backup before any deletion."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from .db import ValidationError, audit, check_password, next_record_id
from .storage import consistent_backup


TABLES = ('salary_receipts', 'allocations', 'collection_notes', 'payment_plans',
          'guardian_documents', 'year_transitions', 'enrollment_documents', 'payroll_plans',
          'cash_closures', 'monthly_assessments', 'payments', 'expenses', 'charges', 'students',
          'employees', 'positions', 'grades', 'guardians', 'exchange_rates', 'audit', 'sessions')
CONFIRMATION = 'VACIAR REGISTROS'


def reset_preview(db):
    digest = hashlib.sha256()
    counts = {}
    for table in TABLES:
        if table == 'sessions':
            continue  # Authentication renewal should not invalidate a financial review.
        digest.update(table.encode())
        count = 0
        for row in db.execute(f'SELECT * FROM {table} ORDER BY rowid'):
            digest.update(json.dumps(tuple(row), ensure_ascii=False).encode())
            count += 1
        counts[table] = count
    for key, value in db.execute('SELECT key,value FROM settings ORDER BY key'):
        digest.update(json.dumps((key, value), ensure_ascii=False).encode())
    return {'counts': counts, 'preview_hash': digest.hexdigest(), 'confirmation': CONFIRMATION}


def reset_records(db, data, user):
    if user['role'] != 'admin':
        raise PermissionError('Solo administración puede vaciar los registros del colegio.')
    if data.get('confirmation') != CONFIRMATION:
        raise ValidationError('Escribe VACIAR REGISTROS para confirmar.')
    password = data.get('password')
    saved = db.execute('SELECT password FROM users WHERE id=?', (user['id'],)).fetchone()
    if not isinstance(password, str) or len(password) > 256 or not saved or not check_password(password, saved[0]):
        raise PermissionError('La contraseña del administrador no es correcta.')
    preview = reset_preview(db)
    if data.get('preview_hash') != preview['preview_hash']:
        raise ValidationError('Los registros cambiaron. Revisa nuevamente el resumen antes de vaciar.')
    path = Path(db.execute('PRAGMA database_list').fetchone()[2])
    name = f'antes-vaciar-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite3'
    backup = path.parent / 'backups' / name
    try:
        consistent_backup(path, backup)
        secondary = db.execute("SELECT value FROM settings WHERE key='backup_directory'").fetchone()
        if secondary and secondary[0]:
            consistent_backup(path, Path(secondary[0]) / name)
    except Exception as error:
        raise ValidationError('No se pudo completar el respaldo previo. No se ha vaciado la base; revisa el disco y el segundo destino.') from error
    for table in ('payments', 'expenses', 'students'):
        floor = next_record_id(db, table)-1
        db.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                   ('id_floor_'+table, str(floor)))
    for table in TABLES:
        db.execute(f'DELETE FROM {table}')
    if db.execute('PRAGMA foreign_key_check').fetchone():
        raise ValidationError('No se pudo validar el vaciado. No se guardaron los cambios.')
    audit(db, user['id'], 'reset_records', {'counts': preview['counts'], 'backup': str(backup)})
    return {'ok': True, 'backup_path': str(backup), 'counts': preview['counts']}
