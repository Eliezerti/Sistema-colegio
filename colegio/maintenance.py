"""Read-only integrity checks; never repair or recalculate financial records."""
from .db import local_today


def review_database(db):
    if not db.in_transaction: db.execute('BEGIN')
    errors = []
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
    )
    for message,sql in checks:
        if db.execute(sql).fetchone(): errors.append(message)
    return {'ok':not errors,'checked_on':local_today().isoformat(),'errors':errors,
        'journal_mode':db.execute('PRAGMA journal_mode').fetchone()[0],
        'synchronous':db.execute('PRAGMA synchronous').fetchone()[0],
        'counts':{t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
                  for t in ('students','guardians','charges','payments','expenses','users')},
        'message':'Verificación completada; no se modificaron datos. Una verificación no sustituye los respaldos.'}
