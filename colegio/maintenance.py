"""Read-only integrity checks; never repair or recalculate financial records."""
from .db import local_today

SEQUENCES = ('payments', 'expenses', 'students', 'guardians', 'employees', 'enrollment_documents')


def sequence_review(db):
    """Report gaps above the reserved floor without expanding large ID ranges."""
    result = []
    for table in SEQUENCES:
        row = db.execute('SELECT value FROM settings WHERE key=?', ('id_floor_'+table,)).fetchone()
        try:
            floor = int(row[0]) if row else 0
            if floor < 0 or (row is not None and str(floor) != str(row[0])):
                raise ValueError()
        except (ValueError, TypeError):
            result.append({'table': table, 'ok': False, 'reserved_until': None, 'gaps': [],
                           'message': 'No se pudo comprobar el límite de numeración reservado.'})
            continue
        gaps = []
        for record_id, previous in db.execute(f'''SELECT id,COALESCE(LAG(id) OVER (ORDER BY id),0)
                                                  FROM {table} ORDER BY id'''):
            start = max(previous+1, floor+1)
            if record_id > start:
                gaps.append({'from': start, 'to': record_id-1})
        result.append({'table': table, 'ok': not gaps, 'reserved_until': floor, 'gaps': gaps})
    return result


def review_database(db):
    if not db.in_transaction: db.execute('BEGIN')
    from .audit_chain import local_status
    audit = local_status(db)
    errors = [] if audit['ok'] else [audit['message']]
    integrity = [r[0] for r in db.execute('PRAGMA integrity_check')]
    if integrity != ['ok']: errors.append('La integridad SQLite requiere revisión técnica.')
    if db.execute('PRAGMA foreign_key_check').fetchone():
        errors.append('Existen referencias a registros inexistentes.')
    checks = (
        ('Un cobro no coincide con sus aplicaciones.', '''SELECT p.id FROM payments p LEFT JOIN allocations a ON a.payment_id=p.id
            GROUP BY p.id HAVING p.amount<>COALESCE(SUM(a.amount),0)'''),
        ('Un cargo tiene pagos válidos superiores a su importe.', '''SELECT c.id FROM charges c JOIN allocations a ON a.charge_id=c.id
            JOIN payments p ON p.id=a.payment_id WHERE p.voided=0 GROUP BY c.id HAVING SUM(a.amount)>c.amount'''),
        ('Un cargo cancelado conserva pagos válidos.', '''SELECT c.id FROM charges c JOIN allocations a ON a.charge_id=c.id
            JOIN payments p ON p.id=a.payment_id WHERE c.cancelled=1 AND p.voided=0 LIMIT 1'''),
        ('Una aplicación pertenece a otro alumno.', '''SELECT p.id FROM allocations a JOIN payments p ON p.id=a.payment_id
            JOIN charges c ON c.id=a.charge_id WHERE p.student_id<>c.student_id LIMIT 1'''),
        ('Una mensualidad calculada difiere de su cargo.', '''SELECT m.student_id FROM monthly_assessments m JOIN charges c ON c.id=m.charge_id
            WHERE m.amount<>c.amount OR m.student_id<>c.student_id OR m.period<>c.period LIMIT 1'''),
        ('Existen cargos repetidos para el mismo alumno, período y concepto.', '''SELECT student_id FROM charges
            GROUP BY student_id,period,concept HAVING COUNT(*)>1 LIMIT 1'''),
    )
    for message,sql in checks:
        if db.execute(sql).fetchone(): errors.append(message)
    payments = db.execute('SELECT COALESCE(SUM(amount),0) FROM payments WHERE voided=0').fetchone()[0]
    allocations = db.execute('''SELECT COALESCE(SUM(a.amount),0) FROM allocations a
                                JOIN payments p ON p.id=a.payment_id WHERE p.voided=0''').fetchone()[0]
    if payments != allocations:
        errors.append('El total de cobros válidos no coincide con sus aplicaciones.')
    sequences = sequence_review(db)
    labels = dict(zip(SEQUENCES, ('recibos', 'egresos', 'alumnos', 'representantes', 'personal', 'constancias')))
    for sequence in sequences:
        if not sequence['ok']:
            errors.append('Revisa la numeración de '+labels[sequence['table']]+': '+
                          ('hay saltos sin reserva registrada.' if sequence['reserved_until'] is not None
                           else 'no se pudo comprobar la reserva.'))
    return {'audit':audit, 'ok':not errors,'checked_on':local_today().isoformat(),'errors':errors,
        'financial': {'valid_payments': payments, 'valid_allocations': allocations}, 'sequences': sequences,
        'journal_mode':db.execute('PRAGMA journal_mode').fetchone()[0],
        'synchronous':db.execute('PRAGMA synchronous').fetchone()[0],
        'counts':{t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
                  for t in ('students','guardians','charges','payments','expenses','users')},
        'message':'Verificación completada; no se modificaron datos. Una verificación no sustituye los respaldos.'}
