"""Audited corrections and reversible directory removal; never erase payments."""
import json

from .db import ValidationError, audit, charges, integer, required, valid_period
from .documents import enrollment


DIRECTORY_ACTIONS = {'archive-student', 'restore-student', 'archive-guardian', 'restore-guardian', 'delete-grade'}


def directory_action(db, endpoint, data, user):
    if endpoint == 'delete-grade':
        target = integer(data.get('id'), 1, 2147483647)
        reason = required(data, 'reason', 500)
        if data.get('confirmation') != 'ELIMINAR':
            raise ValidationError('Escribe ELIMINAR para confirmar.')
        grade = db.execute('SELECT * FROM grades WHERE id=?', (target,)).fetchone()
        if not grade:
            raise ValidationError('El grado ya no existe. Actualiza el directorio.')
        if db.execute('SELECT 1 FROM students WHERE grade_id=?', (target,)).fetchone():
            raise ValidationError('Este grado tiene alumnos vinculados, incluso fichas archivadas. Reasigna sus grados antes de eliminarlo.')
        db.execute('DELETE FROM grades WHERE id=?', (target,))
        audit(db, user['id'], endpoint, {'id':target, 'name':grade['name'], 'reason':reason})
        return {'saved':True, 'id':target}
    table = 'students' if endpoint.endswith('student') else 'guardians'
    target = integer(data.get('id'), 1, 2147483647)
    reason = required(data, 'reason', 500)
    archived = endpoint.startswith('archive-')
    if data.get('confirmation') != ('ARCHIVAR' if archived else 'RECUPERAR'):
        raise ValidationError('Escribe la palabra de confirmación indicada.')
    record = db.execute(f'SELECT * FROM {table} WHERE id=?', (target,)).fetchone()
    if not record or bool(record['archived']) == archived:
        raise ValidationError('La ficha no existe o ya tiene ese estado. Actualiza el directorio.')
    if archived and table == 'guardians' and db.execute(
            'SELECT 1 FROM students WHERE guardian_id=? AND archived=0', (target,)).fetchone():
        raise ValidationError('Este representante tiene alumnos vinculados. Reasigna o archiva sus fichas antes de eliminarlo del directorio.')
    db.execute(f'UPDATE {table} SET archived=?' + (",status='inactive'" if table == 'students' else '') + ' WHERE id=?',
               (int(archived), target))
    audit(db, user['id'], endpoint, {'id':target, 'name':record['name'], 'reason':reason,
                                   'previous_status':record['status'] if table == 'students' else None})
    return {'saved':True, 'id':target}


def correct_billing_start(db, data, user):
    target = integer(data.get('id'), 1, 2147483647)
    reason = required(data, 'reason', 500)
    student = db.execute('SELECT * FROM students WHERE id=?', (target,)).fetchone()
    if not student:
        raise ValidationError('Alumno inexistente.')
    prior = student['billing_start'] or student['enrollment_start'][:7]
    first = valid_period(data.get('billing_start'))
    if data.get('previous_start') != prior:
        raise ValidationError('La matrícula cambió. Vuelve a revisar la corrección.')
    if not prior <= first <= student['enrollment_end'][:7]:
        raise ValidationError('Elige un primer mes igual o posterior al actual, dentro del período del alumno.')
    candidates = [c for c in charges(db, target) if c['concept'] == 'Mensualidad'
                  and student['enrollment_start'][:7] <= c['period'] < first]
    ids = sorted(c['id'] for c in candidates)
    if first == prior and not ids:
        raise ValidationError('No hay mensualidades anteriores que corregir para ese mes.')
    if data.get('charge_ids') != ids:
        raise ValidationError('Los cargos cambiaron. Vuelve a revisar la corrección antes de confirmar.')
    if any(c['paid'] for c in candidates):
        raise ValidationError('Hay pagos aplicados a un mes que deseas anular. Esta corrección no modifica pagos ni recibos; revisa el caso con administración.')
    for plan in db.execute('SELECT snapshot_json FROM payment_plans WHERE student_id=? AND cancelled=0', (target,)):
        if any(c['id'] in ids for c in json.loads(plan[0])['charges']):
            raise ValidationError('Un cargo pertenece a un convenio vigente. Revisa y cancela ese convenio antes de corregirlo.')
    if data.get('confirmed') is not True:
        raise ValidationError('Revisa y confirma los meses que se anularán.')
    for charge in candidates:
        db.execute('UPDATE charges SET cancelled=1 WHERE id=?', (charge['id'],))
        audit(db, user['id'], 'cancel-charge', {'id':charge['id'], 'student_id':target,
              'period':charge['period'], 'amount':charge['amount'], 'reason':reason})
    db.execute('UPDATE students SET billing_start=? WHERE id=?', (first, target))
    audit(db, user['id'], 'correct-billing-start', {'id':target, 'previous_start':prior,
          'billing_start':first, 'charge_ids':ids, 'reason':reason})
    document_id = enrollment(db, target, user['id'])
    return {'saved':True, 'id':target, 'cancelled':len(ids), 'document_id':document_id}
