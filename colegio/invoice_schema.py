"""Schema 16, additive and reversible; no fiscal numbers or seed records."""
from contextlib import closing
from pathlib import Path

VERSION=16
TABLES=('invoice_preferences','invoice_batches','invoice_templates','invoice_template_versions',
        'invoice_printer_profiles','invoices','invoice_print_events')
IMMUTABLE=('payment_id','batch_id','template_version_id','issued_on','invoice_number','control_number',
    'invoice_key','control_key','profile_json','snapshot_json','pdf_base64','pdf_sha256','created_by','created_at','issued_by','issued_at')
DDL=(
'''CREATE TABLE invoice_preferences(id INTEGER PRIMARY KEY CHECK(id=1),payload_json TEXT NOT NULL,
 saved_by INTEGER NOT NULL REFERENCES users(id),saved_at TEXT NOT NULL)''',
'''CREATE TABLE invoice_batches(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,
 invoice_from TEXT NOT NULL,invoice_to TEXT NOT NULL,control_from TEXT NOT NULL,control_to TEXT NOT NULL,
 active INTEGER NOT NULL CHECK(active IN(0,1)),data_json TEXT NOT NULL,
 saved_by INTEGER NOT NULL REFERENCES users(id),saved_at TEXT NOT NULL)''',
'''CREATE UNIQUE INDEX invoice_active_batch ON invoice_batches(active) WHERE active=1''',
'''CREATE TABLE invoice_templates(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,current_version_id INTEGER,
 saved_by INTEGER NOT NULL REFERENCES users(id),saved_at TEXT NOT NULL,
 FOREIGN KEY(current_version_id,id) REFERENCES invoice_template_versions(id,template_id))''',
'''CREATE TABLE invoice_template_versions(id INTEGER PRIMARY KEY,template_id INTEGER NOT NULL REFERENCES invoice_templates(id),
 revision INTEGER NOT NULL CHECK(revision>0),layout_json TEXT NOT NULL,layout_hash TEXT NOT NULL,
 saved_by INTEGER NOT NULL REFERENCES users(id),saved_at TEXT NOT NULL,
 UNIQUE(template_id,revision),UNIQUE(id,template_id))''',
'''CREATE TABLE invoice_printer_profiles(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,profile_json TEXT NOT NULL,
 saved_by INTEGER NOT NULL REFERENCES users(id),saved_at TEXT NOT NULL)''',
'''CREATE TABLE invoices(id INTEGER PRIMARY KEY,payment_id INTEGER REFERENCES payments(id),
 batch_id INTEGER REFERENCES invoice_batches(id),template_version_id INTEGER REFERENCES invoice_template_versions(id),
 issued_on TEXT NOT NULL,state TEXT NOT NULL CHECK(state IN('draft','issued','void','damaged')),
 invoice_number TEXT NOT NULL DEFAULT '',control_number TEXT NOT NULL DEFAULT '',
 invoice_key TEXT UNIQUE,control_key TEXT UNIQUE,profile_json TEXT NOT NULL DEFAULT '{}',
 snapshot_json TEXT NOT NULL,pdf_base64 TEXT NOT NULL DEFAULT '',pdf_sha256 TEXT NOT NULL DEFAULT '',
 created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,
 issued_by INTEGER REFERENCES users(id),issued_at TEXT,
 voided_by INTEGER REFERENCES users(id),voided_at TEXT,void_reason TEXT NOT NULL DEFAULT '',
 CHECK((state='draft' AND invoice_key IS NULL AND control_key IS NULL AND invoice_number='' AND control_number='' AND pdf_base64='')
 OR (state='damaged' AND payment_id IS NULL AND batch_id IS NOT NULL AND invoice_key IS NOT NULL AND control_key IS NOT NULL AND pdf_base64='')
 OR (state IN('issued','void') AND payment_id IS NOT NULL AND batch_id IS NOT NULL AND template_version_id IS NOT NULL
 AND invoice_key IS NOT NULL AND control_key IS NOT NULL AND pdf_base64<>'' AND length(pdf_sha256)=64 AND issued_by IS NOT NULL AND issued_at IS NOT NULL)))''',
'''CREATE UNIQUE INDEX invoice_unique_payment ON invoices(payment_id) WHERE state='issued' ''',
'''CREATE INDEX invoice_payment_all ON invoices(payment_id)''',
'''CREATE INDEX invoice_period ON invoices(issued_on,id)''',
'''CREATE TABLE invoice_print_events(id INTEGER PRIMARY KEY,invoice_id INTEGER NOT NULL REFERENCES invoices(id),
 pdf_sha256 TEXT NOT NULL,reason TEXT NOT NULL,printed_by INTEGER NOT NULL REFERENCES users(id),printed_at TEXT NOT NULL)''',
'''CREATE TRIGGER invoice_frozen BEFORE UPDATE ON invoices WHEN OLD.state<>'draft' AND NOT (
 OLD.state='issued' AND NEW.state='void' AND '''+' AND '.join('NEW.'+col+' IS OLD.'+col for col in IMMUTABLE)+'''
 AND NEW.voided_by IS NOT NULL AND NEW.voided_at IS NOT NULL AND length(NEW.void_reason)>=10)
 BEGIN SELECT RAISE(ABORT,'La factura emitida es inmutable.'); END''',
'''CREATE TRIGGER invoice_no_delete BEFORE DELETE ON invoices
 BEGIN SELECT RAISE(ABORT,'No se borran facturas ni hojas contabilizadas.'); END''',
)
for _table in ('invoice_template_versions','invoice_print_events'):
    for _op in ('UPDATE','DELETE'):
        DDL+=(f'''CREATE TRIGGER {_table}_no_{_op.lower()} BEFORE {_op} ON {_table}
        BEGIN SELECT RAISE(ABORT,'El historial de facturas es inmutable.'); END''',)

REQUIRED={
 'invoice_preferences':{'id','payload_json','saved_by','saved_at'},
 'invoice_batches':{'id','name','invoice_from','invoice_to','control_from','control_to','active','data_json'},
 'invoice_templates':{'id','name','current_version_id'},
 'invoice_template_versions':{'id','template_id','revision','layout_json','layout_hash'},
 'invoice_printer_profiles':{'id','name','profile_json'},
 'invoices':{'id',*IMMUTABLE,'state','voided_by','voided_at','void_reason'},
 'invoice_print_events':{'id','invoice_id','pdf_sha256','reason','printed_by','printed_at'}}
GUARDS={'invoice_active_batch','invoice_unique_payment','invoice_frozen','invoice_no_delete',
 'invoice_template_versions_no_update','invoice_template_versions_no_delete',
 'invoice_print_events_no_update','invoice_print_events_no_delete'}


def verify_layout(db):
    for table,columns in REQUIRED.items():
        if not columns<={r[1] for r in db.execute('PRAGMA table_info('+table+')')}:
            raise ValueError('Falta una tabla o columna de facturas.')
    present={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type IN ('trigger','index')")}
    if not GUARDS<=present:raise ValueError('Falta una protección de numeración o inmutabilidad de facturas.')


def checkpoint(stage):
    """Test children are really terminated at these boundaries."""


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
        if version!=15:raise ValueError('Completa primero la actualización al esquema 15.')
        verify(db)
        populated=bool(db.execute('SELECT 1 FROM users LIMIT 1').fetchone() or db.execute('SELECT 1 FROM audit LIMIT 1').fetchone())
        try:
            db.execute('BEGIN IMMEDIATE');previous=reversal_snapshot(path,before=15,after=16) if not new else None;checkpoint('backup_verified')
            for index,sql in enumerate(DDL):db.execute(sql);checkpoint('object_'+str(index))
            install_triggers_missing(db);verify_layout(db);db.execute('PRAGMA user_version=16')
            if populated:audit(db,None,'invoice-schema',dict(schema_before=15,schema_after=16,previous_backup=previous))
            verify(db);checkpoint('before_commit');db.commit();checkpoint('after_commit')
        except BaseException:db.rollback();raise
        verify(db);state=local_status(db,recover=True)
        if not state['ok']:raise ValueError(state['message'])
