"""Schema 14: confidential statements, allocations and review history."""
from contextlib import closing
from pathlib import Path
VERSION=14
TABLES=('statement_profiles','statement_imports','bank_movements','reconciliation_links','bank_classifications')
DDL=(
'''CREATE TABLE statement_profiles(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,profile_json TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'NO VERIFICADO',updated_by INTEGER NOT NULL REFERENCES users(id),updated_at TEXT NOT NULL)''',
'''CREATE TABLE statement_imports(id INTEGER PRIMARY KEY,account_id INTEGER NOT NULL REFERENCES school_accounts(id),
 file_sha256 TEXT NOT NULL,filename TEXT NOT NULL,profile_json TEXT NOT NULL,rows_count INTEGER NOT NULL,
 imported_by INTEGER NOT NULL REFERENCES users(id),imported_at TEXT NOT NULL,review_reason TEXT NOT NULL DEFAULT '',UNIQUE(account_id,file_sha256))''',
'''CREATE TABLE bank_movements(id INTEGER PRIMARY KEY,import_id INTEGER NOT NULL REFERENCES statement_imports(id),
 account_id INTEGER NOT NULL REFERENCES school_accounts(id),movement_on TEXT NOT NULL,direction TEXT NOT NULL CHECK(direction IN ('credit','debit')),
 amount INTEGER NOT NULL CHECK(amount>0),currency TEXT NOT NULL CHECK(currency IN ('USD','VES')),reference TEXT NOT NULL,
 description TEXT NOT NULL,bank_id TEXT NOT NULL,fingerprint TEXT NOT NULL,source_row INTEGER NOT NULL,UNIQUE(import_id,source_row))''',
'''CREATE UNIQUE INDEX bank_movement_identity ON bank_movements(account_id,bank_id) WHERE bank_id<>'' ''',
'''CREATE INDEX bank_movement_fingerprint ON bank_movements(account_id,fingerprint)''',
'''CREATE TABLE reconciliation_links(id INTEGER PRIMARY KEY,movement_id INTEGER NOT NULL REFERENCES bank_movements(id),
 payment_id INTEGER REFERENCES payments(id),expense_id INTEGER REFERENCES expenses(id),other_id INTEGER REFERENCES other_income(id),
 deposit_id INTEGER REFERENCES cash_deposits(id),amount INTEGER NOT NULL CHECK(amount>0),reason TEXT NOT NULL,
 created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,voided INTEGER NOT NULL DEFAULT 0 CHECK(voided IN (0,1)),void_reason TEXT NOT NULL DEFAULT '',
 CHECK((payment_id IS NOT NULL)+(expense_id IS NOT NULL)+(other_id IS NOT NULL)+(deposit_id IS NOT NULL)=1))''',
'''CREATE INDEX bank_link_movement ON reconciliation_links(movement_id,voided)''',
'''CREATE TABLE bank_classifications(id INTEGER PRIMARY KEY,movement_id INTEGER NOT NULL REFERENCES bank_movements(id),
 category TEXT NOT NULL,support TEXT NOT NULL,reason TEXT NOT NULL,created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,
 voided INTEGER NOT NULL DEFAULT 0 CHECK(voided IN (0,1)),void_reason TEXT NOT NULL DEFAULT '')''')
REQUIRED={'statement_profiles':{'id','profile_json','status'},'statement_imports':{'id','account_id','file_sha256','profile_json','rows_count','imported_by','imported_at'},
 'bank_movements':{'id','import_id','account_id','movement_on','direction','amount','currency','reference','description','bank_id','fingerprint','source_row'},
 'reconciliation_links':{'id','movement_id','payment_id','expense_id','other_id','deposit_id','amount','reason','voided'},
 'bank_classifications':{'id','movement_id','category','support','reason','voided'}}

def verify_layout(db):
    for table,columns in REQUIRED.items():
        if not columns<={r[1] for r in db.execute('PRAGMA table_info('+table+')')}:
            raise ValueError('Falta una tabla o columna de conciliación bancaria.')

def checkpoint(stage):
    """Process-termination test seam, never an environment bypass."""

def migrate(path,*,new=False):
    from .db import connect,audit
    from .schema import verify,install_triggers_missing
    from .audit_chain import path_lock,local_status
    from .income_schema import reversal_snapshot
    path=Path(path).resolve()
    with path_lock(path),closing(connect(path)) as db:
        version=db.execute('PRAGMA user_version').fetchone()[0]
        if version>16:raise ValueError('Esta base requiere una versión más reciente.')
        if version in (VERSION,15,16):
            verify_layout(db);local_status(db,recover=True);return
        if version!=13:raise ValueError('Completa primero la actualización al esquema 13.')
        verify(db)
        populated=bool(db.execute('SELECT 1 FROM users LIMIT 1').fetchone() or db.execute('SELECT 1 FROM audit LIMIT 1').fetchone())
        try:
            db.execute('BEGIN IMMEDIATE')
            previous=reversal_snapshot(path,before=13,after=14) if not new else None
            checkpoint('backup_verified')
            for n,sql in enumerate(DDL):db.execute(sql);checkpoint('object_'+str(n))
            install_triggers_missing(db);verify_layout(db);db.execute('PRAGMA user_version=14')
            if populated:audit(db,None,'bank-schema',dict(schema_before=13,schema_after=14,previous_backup=previous))
            verify(db);checkpoint('before_commit');db.commit();checkpoint('after_commit')
        except BaseException:db.rollback();raise
        verify(db)
        state=local_status(db,recover=True)
        if not state['ok']:raise ValueError(state['message'])
