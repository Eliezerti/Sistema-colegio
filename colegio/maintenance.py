"""Read-only integrity checks; never repair or recalculate financial records."""
from .db import local_today

SEQUENCES = ('payments', 'expenses', 'students', 'guardians', 'enrollment_documents')


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
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='school_accounts'").fetchone():
        checks += (
            ('Una cuenta de cobro no coincide con moneda o método.',"""SELECT p.id FROM payment_accounts a JOIN payments p ON p.id=a.payment_id JOIN school_accounts s ON s.id=a.account_id
                WHERE p.currency<>s.currency OR (p.method='Efectivo')<>(s.kind='cash') LIMIT 1"""),
            ('Una cuenta de egreso no coincide con su moneda.',"""SELECT e.id FROM expense_accounts a JOIN expenses e ON e.id=a.expense_id JOIN school_accounts s ON s.id=a.account_id WHERE e.currency<>s.currency LIMIT 1"""),
            ('Un depósito válido usa un cobro anulado o de otra moneda/método.',"""SELECT d.id FROM cash_deposit_payments a JOIN cash_deposits d ON d.id=a.deposit_id JOIN payments p ON p.id=a.payment_id
                WHERE d.voided=0 AND (p.voided=1 OR p.method<>'Efectivo' OR p.currency<>d.currency OR p.paid_on>d.deposited_on) LIMIT 1"""),
            ('Los depósitos cubren más efectivo que el recibo original.',"""SELECT p.id FROM cash_deposit_payments a JOIN cash_deposits d ON d.id=a.deposit_id JOIN payments p ON p.id=a.payment_id
                WHERE d.voided=0 GROUP BY p.id HAVING SUM(a.amount)>p.received_amount LIMIT 1"""),
            ('La diferencia de un depósito no coincide con sus aplicaciones.',"""SELECT d.id FROM cash_deposits d LEFT JOIN cash_deposit_payments a ON a.deposit_id=d.id
                GROUP BY d.id HAVING d.difference<>d.amount-COALESCE(SUM(a.amount),0) LIMIT 1"""),
        )
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='reconciliation_links'").fetchone():
        checks += (("Los vínculos superan el importe bancario.","""SELECT b.id FROM bank_movements b JOIN reconciliation_links l ON l.movement_id=b.id WHERE l.voided=0 GROUP BY b.id HAVING SUM(l.amount)>b.amount LIMIT 1"""),
            ("Una clasificación activa está repetida.","""SELECT movement_id FROM bank_classifications WHERE voided=0 GROUP BY movement_id HAVING COUNT(*)>1 LIMIT 1"""),
            ("Un movimiento clasificado conserva vínculos activos.","""SELECT c.id FROM bank_classifications c JOIN reconciliation_links l ON l.movement_id=c.movement_id WHERE c.voided=0 AND l.voided=0 LIMIT 1"""))
        for column,table,join,account,amount,direction in (
                ('payment_id','payments','JOIN payment_accounts a ON a.payment_id=p.id','a.account_id','p.received_amount','credit'),
                ('expense_id','expenses','JOIN expense_accounts a ON a.expense_id=p.id','a.account_id','p.received_amount','debit'),
                ('other_id','other_income','','p.account_id','p.received_amount','credit'),
                ('deposit_id','cash_deposits','','p.account_id','p.amount','credit')):
            checks += (("Un vínculo bancario no coincide con moneda, cuenta, sentido o estado.",
                "SELECT l.id FROM reconciliation_links l JOIN bank_movements b ON b.id=l.movement_id JOIN "+table+" p ON p.id=l."+column+" "+join+" WHERE l.voided=0 AND (p.voided=1 OR b.currency<>p.currency OR b.account_id<>"+account+" OR b.direction<>'"+direction+"') LIMIT 1"),
                ("La conciliación supera el importe del libro.","SELECT p.id FROM "+table+" p JOIN reconciliation_links l ON l."+column+"=p.id WHERE l.voided=0 GROUP BY p.id HAVING SUM(l.amount)>"+amount+" LIMIT 1"))
    for message,sql in checks:
        if db.execute(sql).fetchone(): errors.append(message)
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='accounting_closures'").fetchone():
        import json
        from .income_book import signature
        for row in db.execute('SELECT period,snapshot_json,preview_hash FROM accounting_closures'):
            try:
                content=json.loads(row['snapshot_json'])
                if content['period']!=row['period'] or signature(content)!=row['preview_hash']:raise ValueError()
            except (ValueError,TypeError,KeyError):
                errors.append('No se pudo verificar una foto de cierre mensual.');break
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='invoices'").fetchone():
        from .invoices import review_records
        errors.extend(review_records(db))
    payments = db.execute('SELECT COALESCE(SUM(amount),0) FROM payments WHERE voided=0').fetchone()[0]
    allocations = db.execute('''SELECT COALESCE(SUM(a.amount),0) FROM allocations a
                                JOIN payments p ON p.id=a.payment_id WHERE p.voided=0''').fetchone()[0]
    if payments != allocations:
        errors.append('El total de cobros válidos no coincide con sus aplicaciones.')
    sequences = sequence_review(db)
    labels = dict(zip(SEQUENCES, ('recibos', 'egresos', 'alumnos', 'representantes', 'constancias')))
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
