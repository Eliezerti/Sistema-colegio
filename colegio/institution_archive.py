"""Administrative offboarding and deletion of unused records; financial history survives."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from .db import ValidationError, audit, charges, check_password, integer, next_record_id, required
from .storage import consistent_backup

KINDS = {'student': 'students', 'guardian': 'guardians'}
ARCHIVE_ACTIONS = {'delete-unused-record', 'delete-error-student'}


def admin_only(user):
    if user['role'] != 'admin':
        raise PermissionError('Solo Administración puede gestionar el archivo de la institución.')


def references(value, kind, target, context=''):
    """Recognize typed IDs in existing document snapshots, never compare names."""
    contexts = {'student': {'student', 'students', 'source'},
                'guardian': {'guardian'}}[kind]
    if isinstance(value, dict):
        if value.get(kind+'_id') == target or (context in contexts and value.get('id') == target):
            return True
        return any(references(v, kind, target, k) for k, v in value.items())
    if isinstance(value, list):
        return any(references(v, kind, target, context) for v in value)
    return False


def record_preview(db, kind, target, user, *, created_by_error=False):
    admin_only(user)
    if kind not in KINDS:
        raise ValidationError('Tipo de ficha inválido.')
    if created_by_error and kind != 'student':
        raise ValidationError('Esta corrección solo permite eliminar un alumno creado por error.')
    target = integer(target, 1, 2147483647)
    record = db.execute(f'SELECT * FROM {KINDS[kind]} WHERE id=?', (target,)).fetchone()
    if not record:
        raise ValidationError('La ficha ya no existe. Actualiza el archivo.')
    record = dict(record)
    counts, blocked, digest = {}, [], hashlib.sha256()
    digest.update(json.dumps(record, sort_keys=True, ensure_ascii=False).encode())

    def linked(table, column, label, protect=True):
        linked_rows = list(db.execute(f'SELECT * FROM {table} WHERE {column}=? ORDER BY rowid', (target,)))
        counts[label] = len(linked_rows)
        digest.update(json.dumps([tuple(r) for r in linked_rows], ensure_ascii=False).encode())
        if linked_rows and protect:
            blocked.append(label)

    if kind == 'student':
        linked('charges', 'student_id', 'Cargos, incluidos pagados o anulados', protect=not created_by_error)
        linked('payments', 'student_id', 'Pagos y recibos, incluidos anulados')
        linked('payment_plans', 'student_id', 'Convenios')
        linked('collection_notes', 'student_id', 'Seguimientos')
        linked('enrollment_documents', 'student_id', 'Constancias de matrícula', protect=False)
        linked('monthly_assessments', 'student_id', 'Evaluaciones de mensualidad', protect=False)
        # A positive assessment is history even if a damaged record lost its charge link.
        if not created_by_error and db.execute('SELECT 1 FROM monthly_assessments WHERE student_id=? AND (amount>0 OR charge_id IS NOT NULL)', (target,)).fetchone():
            blocked.append('Evaluaciones de mensualidad con importe')
        if created_by_error:
            allocations = [tuple(r) for r in db.execute('''SELECT a.* FROM allocations a
                JOIN charges c ON c.id=a.charge_id WHERE c.student_id=?
                ORDER BY a.payment_id,a.charge_id''', (target,))]
            counts['Abonos aplicados a los cargos'] = len(allocations)
            digest.update(json.dumps(allocations).encode())
            if allocations:
                blocked.append('Abonos aplicados a los cargos')
    elif kind == 'guardian':
        linked('students', 'guardian_id', 'Alumnos vinculados, incluidos archivados')
    # These documents have JSON snapshots rather than relational foreign keys.
    for table, label in (('guardian_documents', 'Documentos familiares'),
                         ('year_transitions', 'Actas de pase de año'),
                         ('enrollment_documents', 'Constancias vinculadas')):
        if kind == 'student' and table == 'enrollment_documents':
            continue  # Own, nonfinancial enrollment copies are explicitly included in the deletion preview.
        found = []
        for row in db.execute(f'SELECT id,snapshot_json FROM {table} ORDER BY id'):
            try:
                document = json.loads(row['snapshot_json'])
            except (ValueError, TypeError):
                # Unknown history must not be treated as an unused record.
                raise ValidationError('No se pudo revisar un documento histórico. Verifica los datos antes de borrar.')
            if references(document, kind, target):
                found.append(tuple(row))
        counts[label] = len(found)
        digest.update(json.dumps(found, ensure_ascii=False).encode())
        if found:
            blocked.append(label)
    archived = bool(record['archived'])
    balance = sum(c['balance'] for c in charges(db, target)) if kind == 'student' else None
    if not archived and not created_by_error:
        blocked.insert(0, 'Primero debes archivar esta ficha')
    result = {'kind': kind, 'id': target, 'name': record['name'], 'archived': archived,
              'balance': balance, 'counts': counts, 'blockers': blocked, 'can_delete': not blocked}
    if created_by_error:
        result.update(created_by_error=True, student_code=record['student_code'],
                      grade_name=db.execute('SELECT name FROM grades WHERE id=?', (record['grade_id'],)).fetchone()[0],
                      guardian_name=db.execute('SELECT name FROM guardians WHERE id=?', (record['guardian_id'],)).fetchone()[0])
    digest.update(json.dumps(result, sort_keys=True, ensure_ascii=False).encode())
    result['preview_hash'] = digest.hexdigest()
    return result


def archive_action(db, endpoint, data, user, *, demo=False):
    admin_only(user)
    if endpoint not in ARCHIVE_ACTIONS:
        raise ValidationError('Operación de archivo inválida.')
    created_by_error = endpoint == 'delete-error-student'
    preview = record_preview(db, data.get('kind'), data.get('id'), user, created_by_error=created_by_error)
    if not preview['can_delete']:
        if created_by_error:
            raise ValidationError('No se puede eliminar esta ficha: ' + '; '.join(preview['blockers']) +
                                  '. Revisa que hayas elegido la matrícula equivocada.')
        raise ValidationError('Esta ficha conserva historial o vínculos. Usa Archivar; un saldo de $0 no autoriza borrar movimientos.')
    if data.get('preview_hash') != preview['preview_hash']:
        raise ValidationError('La ficha cambió. Revisa nuevamente el detalle antes de borrar.')
    if data.get('confirmation') != 'BORRAR FICHA':
        raise ValidationError('Escribe BORRAR FICHA para confirmar.')
    if created_by_error and data.get('student_code_confirmation') != preview['student_code']:
        raise ValidationError('Escribe el código del alumno que deseas eliminar; revisa que sea la ficha equivocada.')
    reason = required(data, 'reason', 500)
    password = data.get('password')
    saved = db.execute('SELECT password FROM users WHERE id=?', (user['id'],)).fetchone()
    if not demo and (not isinstance(password, str) or len(password)>256 or not saved or not check_password(password, saved[0])):
        raise PermissionError('La contraseña del Administrador no es correcta.')
    path = Path(db.execute('PRAGMA database_list').fetchone()[2])
    name = f'antes-borrar-ficha-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite3'
    backup = path.parent/'backups'/name
    try:
        consistent_backup(path, backup)
        secondary = db.execute("SELECT value FROM settings WHERE key='backup_directory'").fetchone()
        if secondary and secondary[0]:
            from .backup_export import write_encrypted
            write_encrypted(backup,Path(secondary[0])/(Path(name).stem+'.aulabak'),path.parent)
    except Exception as error:
        raise ValidationError('No se completó el respaldo previo. No se borró la ficha; revisa las carpetas de copias.') from error
    kind, target = preview['kind'], preview['id']
    table = KINDS[kind]
    for sequence in ([table, 'enrollment_documents'] if kind == 'student' else [table]):
        floor = next_record_id(db, sequence)-1
        db.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                   ('id_floor_'+sequence, str(floor)))
    if kind == 'student':
        db.execute('DELETE FROM monthly_assessments WHERE student_id=?', (target,))
        db.execute('DELETE FROM enrollment_documents WHERE student_id=?', (target,))
        if created_by_error:
            db.execute('DELETE FROM charges WHERE student_id=?', (target,))
    db.execute(f'DELETE FROM {table} WHERE id=?', (target,))
    if db.execute('PRAGMA foreign_key_check').fetchone():
        raise ValidationError('No se pudo validar el borrado. Los cambios se revertirán.')
    audit(db, user['id'], endpoint, {'kind': kind, 'id': target, 'name': preview['name'],
          'reason': reason, 'counts': preview['counts'], 'backup': str(backup)})
    return {'saved': True, 'id': target, 'backup_path': str(backup)}
