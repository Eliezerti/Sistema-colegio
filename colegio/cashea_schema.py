"""Additive schema 13: Cashea coverage is distinct from money received."""
from contextlib import closing
from datetime import datetime
from pathlib import Path
import json

VERSION = 13
TABLES = ('cashea_orders','cashea_allocations','cashea_settlements','cashea_settlement_orders','cashea_requests')
SEQUENCES = ('cashea_orders','cashea_settlements')
DEFAULTS = {'cashea_settlement_day':'2','cashea_invoice_required':'1',
            'cashea_commission_percent':'0','cashea_grace_days':'0'}
DDL = (
'''CREATE TABLE cashea_orders(
 id INTEGER PRIMARY KEY,code TEXT NOT NULL UNIQUE,student_id INTEGER NOT NULL REFERENCES students(id),
 ordered_on TEXT NOT NULL,total_amount INTEGER NOT NULL CHECK(total_amount>0),initial_percent TEXT NOT NULL,
 initial_amount INTEGER NOT NULL CHECK(initial_amount>=0),financed_amount INTEGER NOT NULL CHECK(financed_amount>=0),
 invoice_number TEXT NOT NULL,invoice_key TEXT NOT NULL,reference TEXT NOT NULL DEFAULT '',expected_on TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('por_liquidar','liquidada','anulada')),void_reason TEXT NOT NULL DEFAULT '',voided_on TEXT,
 payment_id INTEGER UNIQUE REFERENCES payments(id),commission_bps INTEGER NOT NULL CHECK(commission_bps BETWEEN 0 AND 10000),
 commission_amount INTEGER NOT NULL CHECK(commission_amount>=0),expected_amount INTEGER NOT NULL CHECK(expected_amount>=0),
 snapshot_json TEXT NOT NULL,created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,
 CHECK(initial_amount+financed_amount=total_amount),CHECK(commission_amount+expected_amount=financed_amount),
 CHECK((initial_amount=0 AND payment_id IS NULL) OR initial_amount>0))''',
'''CREATE TABLE cashea_allocations(order_id INTEGER NOT NULL REFERENCES cashea_orders(id),
 charge_id INTEGER NOT NULL REFERENCES charges(id),amount INTEGER NOT NULL CHECK(amount>0),PRIMARY KEY(order_id,charge_id))''',
'''CREATE TABLE cashea_settlements(id INTEGER PRIMARY KEY,code TEXT NOT NULL UNIQUE,received_on TEXT NOT NULL,
 currency TEXT NOT NULL CHECK(currency IN ('USD','VES')),received_amount INTEGER NOT NULL CHECK(received_amount>=0),
 exchange_rate TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>=0),reference TEXT NOT NULL,reference_key TEXT NOT NULL,
 method TEXT NOT NULL DEFAULT 'Transferencia' CHECK(method='Transferencia'),gross_amount INTEGER NOT NULL CHECK(gross_amount>0),
 expected_amount INTEGER NOT NULL CHECK(expected_amount>=0),difference INTEGER NOT NULL,gross_difference INTEGER NOT NULL,
 reason TEXT NOT NULL DEFAULT '',voided INTEGER NOT NULL DEFAULT 0 CHECK(voided IN (0,1)),
 void_reason TEXT NOT NULL DEFAULT '',voided_on TEXT,created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,
 snapshot_json TEXT NOT NULL,CHECK(difference=amount-expected_amount),CHECK(gross_difference=amount-gross_amount))''',
'''CREATE TABLE cashea_settlement_orders(settlement_id INTEGER NOT NULL REFERENCES cashea_settlements(id),
 order_id INTEGER NOT NULL REFERENCES cashea_orders(id),expected_amount INTEGER NOT NULL CHECK(expected_amount>=0),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),PRIMARY KEY(settlement_id,order_id))''',
'''CREATE TABLE cashea_requests(request_key TEXT PRIMARY KEY,action TEXT NOT NULL,user_id INTEGER NOT NULL REFERENCES users(id),
 body_hash TEXT NOT NULL,response_json TEXT NOT NULL,created_at TEXT NOT NULL)''',
'''CREATE UNIQUE INDEX cashea_one_active_settlement ON cashea_settlement_orders(order_id) WHERE active=1''',
'''CREATE UNIQUE INDEX cashea_bank_reference ON cashea_settlements(received_on,currency,reference_key) WHERE voided=0''',
'''CREATE INDEX cashea_order_pending ON cashea_orders(state,expected_on)''',
'''CREATE INDEX cashea_order_student ON cashea_orders(student_id)''',
'''CREATE INDEX cashea_order_invoice ON cashea_orders(invoice_key)''',
'''CREATE INDEX cashea_allocation_charge ON cashea_allocations(charge_id)''',
'''CREATE INDEX cashea_received ON cashea_settlements(received_on)''',
)


def checkpoint(stage):
    """Real process-termination test boundary; no environment bypass."""


def migrate(path, *, new=False):
    from .db import connect,audit
    from .schema import verify,install_triggers_missing
    from .audit_chain import path_lock
    from .storage import consistent_backup
    from .backup_inspection import file_hash
    path=Path(path).resolve()
    with path_lock(path),closing(connect(path)) as db:
        version=db.execute('PRAGMA user_version').fetchone()[0]
        if version==VERSION:
            verify(db);return
        if version!=12:raise ValueError('Cashea requiere una base íntegra de esquema 12 antes de actualizar.')
        verify(db)
        backup=None
        try:
            db.execute('BEGIN IMMEDIATE')
            if not new:
                backup=path.parent/'backups'/f'antes-cashea-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite3'
                consistent_backup(path,backup)
                backup.chmod(0o600)
                with closing(connect(backup)) as saved:verify(saved)
                digest=file_hash(backup)
                if not digest or file_hash(backup)!=digest:raise ValueError('El respaldo previo de Cashea no se pudo verificar.')
                (backup.with_suffix('.migration.json')).write_text(json.dumps({'schema_before':12,'schema_after':13,'sha256':digest,'backup':backup.name}),encoding='utf-8')
                secondary=db.execute("SELECT value FROM settings WHERE key='backup_directory'").fetchone()
                if secondary and secondary[0]:
                    from .backup_export import write_cashea_migration_backup
                    write_cashea_migration_backup(backup,Path(secondary[0])/(backup.stem+'.aulabak'),path.parent)
            checkpoint('backup_verified')
            for sql in DDL:db.execute(sql)
            install_triggers_missing(db)
            checkpoint('tables_created')
            for key,value in DEFAULTS.items():db.execute('INSERT OR IGNORE INTO settings VALUES(?,?)',(key,value))
            for table in SEQUENCES:db.execute('INSERT OR IGNORE INTO settings VALUES(?,?)',('id_floor_'+table,'0'))
            db.execute('PRAGMA user_version=13')
            if not new:audit(db,None,'cashea-schema',{'schema_before':12,'schema_after':13,'backup':str(backup)})
            verify(db);checkpoint('before_commit');db.commit();checkpoint('after_commit')
        except BaseException:
            db.rollback();raise
        db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        checkpoint('verified')
