"""Schema 15: auditable monthly closures and informational income flags."""
from contextlib import closing
from pathlib import Path
VERSION=15
TABLES=('accounting_closures','income_annotations')
DDL=(
'''CREATE TABLE accounting_closures(id INTEGER PRIMARY KEY,period TEXT NOT NULL,snapshot_json TEXT NOT NULL,
 preview_hash TEXT NOT NULL,closed_by INTEGER NOT NULL REFERENCES users(id),closed_at TEXT NOT NULL,
 reopened_by INTEGER REFERENCES users(id),reopened_at TEXT,reopen_reason TEXT NOT NULL DEFAULT '')''',
'''CREATE UNIQUE INDEX accounting_active_month ON accounting_closures(period) WHERE reopened_at IS NULL''',
'''CREATE TABLE income_annotations(id INTEGER PRIMARY KEY,payment_id INTEGER UNIQUE REFERENCES payments(id),
 other_id INTEGER UNIQUE REFERENCES other_income(id),special_taxpayer INTEGER NOT NULL DEFAULT 0 CHECK(special_taxpayer IN (0,1)),
 foreign_currency INTEGER NOT NULL DEFAULT 0 CHECK(foreign_currency IN (0,1)),
 CHECK((payment_id IS NOT NULL)+(other_id IS NOT NULL)=1))''')
REQUIRED={'accounting_closures':{'id','period','snapshot_json','preview_hash','closed_by','closed_at','reopened_by','reopened_at','reopen_reason'},
 'income_annotations':{'id','payment_id','other_id','special_taxpayer','foreign_currency'}}

def verify_layout(db):
    for table,columns in REQUIRED.items():
        if not columns<={r[1] for r in db.execute('PRAGMA table_info('+table+')')}:raise ValueError('Falta una tabla o columna del cierre mensual.')

def checkpoint(stage):
    """Real process-termination test seam."""

def migrate(path,*,new=False):
    from .db import connect,audit
    from .schema import verify,install_triggers_missing
    from .audit_chain import path_lock,local_status
    from .income_schema import reversal_snapshot
    path=Path(path).resolve()
    with path_lock(path),closing(connect(path)) as db:
        version=db.execute('PRAGMA user_version').fetchone()[0]
        if version>VERSION:raise ValueError('Esta base requiere una versión más reciente.')
        if version==VERSION:verify_layout(db);local_status(db,recover=True);return
        if version!=14:raise ValueError('Completa primero la actualización al esquema 14.')
        verify(db)
        populated=bool(db.execute('SELECT 1 FROM users LIMIT 1').fetchone() or db.execute('SELECT 1 FROM audit LIMIT 1').fetchone())
        try:
            db.execute('BEGIN IMMEDIATE');previous=reversal_snapshot(path,before=14,after=15) if not new else None;checkpoint('backup_verified')
            for n,sql in enumerate(DDL):db.execute(sql);checkpoint('object_'+str(n))
            install_triggers_missing(db);verify_layout(db);db.execute('PRAGMA user_version=15')
            if populated:audit(db,None,'accounting-schema',dict(schema_before=14,schema_after=15,previous_backup=previous))
            verify(db);checkpoint('before_commit');db.commit();checkpoint('after_commit')
        except BaseException:db.rollback();raise
        verify(db);state=local_status(db,recover=True)
        if not state['ok']:raise ValueError(state['message'])
