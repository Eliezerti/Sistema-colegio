"""Additive schema 13. Verified local reversal snapshot before the first DDL."""
from contextlib import closing
from pathlib import Path
from datetime import datetime,timezone
import os
import uuid

VERSION=13
TABLES=('school_accounts','payment_accounts','expense_accounts','income_categories',
        'other_income','cash_deposits','cash_deposit_payments')
DDL=(
'''CREATE TABLE school_accounts(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,
 bank TEXT NOT NULL DEFAULT '',currency TEXT NOT NULL CHECK(currency IN ('USD','VES')),
 kind TEXT NOT NULL CHECK(kind IN ('bank','cash')),last4 TEXT NOT NULL DEFAULT ''
 CHECK(last4='' OR last4 GLOB '[0-9][0-9][0-9][0-9]'),active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 CHECK(kind<>'cash' OR (bank='' AND last4='')))''',
'''CREATE TABLE payment_accounts(payment_id INTEGER PRIMARY KEY REFERENCES payments(id),
 account_id INTEGER NOT NULL REFERENCES school_accounts(id),bcv_rate TEXT NOT NULL DEFAULT '')''',
'''CREATE TABLE expense_accounts(expense_id INTEGER PRIMARY KEY REFERENCES expenses(id),
 account_id INTEGER NOT NULL REFERENCES school_accounts(id),bcv_rate TEXT NOT NULL DEFAULT '')''',
'''CREATE TABLE income_categories(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)))''',
'''CREATE TABLE other_income(id INTEGER PRIMARY KEY,concept TEXT NOT NULL,category_id INTEGER NOT NULL REFERENCES income_categories(id),
 received_on TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>0),currency TEXT NOT NULL CHECK(currency IN ('USD','VES')),
 received_amount INTEGER NOT NULL CHECK(received_amount>0),exchange_rate TEXT NOT NULL,bcv_rate TEXT NOT NULL DEFAULT '',
 account_id INTEGER NOT NULL REFERENCES school_accounts(id),method TEXT NOT NULL,reference TEXT NOT NULL DEFAULT '',
 support TEXT NOT NULL,created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,request_key TEXT NOT NULL UNIQUE,request_fingerprint TEXT NOT NULL,
 voided INTEGER NOT NULL DEFAULT 0 CHECK(voided IN (0,1)),void_reason TEXT NOT NULL DEFAULT '')''',
'''CREATE TABLE cash_deposits(id INTEGER PRIMARY KEY,deposited_on TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>0),
 currency TEXT NOT NULL CHECK(currency IN ('USD','VES')),account_id INTEGER NOT NULL REFERENCES school_accounts(id),
 reference TEXT NOT NULL,support TEXT NOT NULL,difference INTEGER NOT NULL,difference_reason TEXT NOT NULL DEFAULT '',
 created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,request_key TEXT NOT NULL UNIQUE,request_fingerprint TEXT NOT NULL,
 voided INTEGER NOT NULL DEFAULT 0 CHECK(voided IN (0,1)),void_reason TEXT NOT NULL DEFAULT '')''',
'''CREATE TABLE cash_deposit_payments(deposit_id INTEGER NOT NULL REFERENCES cash_deposits(id),
 payment_id INTEGER NOT NULL REFERENCES payments(id),amount INTEGER NOT NULL CHECK(amount>0),PRIMARY KEY(deposit_id,payment_id))''')

REQUIRED={
 'school_accounts':{'id','name','bank','currency','kind','last4','active'},
 'payment_accounts':{'payment_id','account_id','bcv_rate'},'expense_accounts':{'expense_id','account_id','bcv_rate'},
 'income_categories':{'id','name','active'},'other_income':{'id','concept','category_id','received_on','amount','currency','received_amount','exchange_rate','bcv_rate','account_id','method','support','request_key','request_fingerprint','voided'},
 'cash_deposits':{'id','deposited_on','amount','currency','account_id','reference','support','difference','difference_reason','request_key','request_fingerprint','voided'},
 'cash_deposit_payments':{'deposit_id','payment_id','amount'}}


def verify_layout(db):
    for table,columns in REQUIRED.items():
        if not columns <= {r[1] for r in db.execute('PRAGMA table_info('+table+')')}:
            raise ValueError('Falta una tabla o columna del libro de ingresos. No se modificó la base.')


def checkpoint(stage):
    """A test child can be killed here; no environment or runtime bypass."""


def reversal_snapshot(path,*,before=12,after=13):
    from .storage import consistent_backup
    from .backup_inspection import inspect_copy,file_hash
    from .backup_keys import status
    from .clock_guard import atomic_json
    cipher=status(path.parent)
    if cipher['configured'] and not cipher['ready']:
        raise ValueError('Desbloquea el cifrado antes de actualizar esta base.')
    folder=path.parent/'.aula-migrations'/('schema-'+str(after))
    for candidate in (folder.parent,folder):
        if candidate.is_symlink() or (hasattr(candidate,'is_junction') and candidate.is_junction()):
            raise ValueError('La carpeta privada de reversión no puede estar enlazada.')
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    identifier=uuid.uuid4().hex
    saved=folder/(identifier+'.sqlite3')
    consistent_backup(path,saved);saved.chmod(0o600)
    inspected=inspect_copy(saved)
    digest=file_hash(saved)
    if inspected['summary']['schema']!=before or file_hash(saved)!=digest:
        raise ValueError('No se verificó la copia previa del esquema '+str(before)+'.')
    encrypted=False
    if cipher['configured']:
        from .backup_export import write_encrypted
        target=folder/(identifier+'.aulabak')
        result=write_encrypted(saved,target,path.parent,preserve_schema=True)
        if not result['encrypted'] or not result['verified']:
            raise ValueError('No se verificó el respaldo cifrado previo.')
        # Only this operation's private temporary, after verified cipher publication.
        saved.unlink();saved=target;encrypted=True
    record=dict(schema_before=before,schema_after=after,backup=saved.name,sha256=file_hash(saved),
        plaintext_sha256=digest,encrypted=encrypted,created_at=datetime.now(timezone.utc).isoformat(),
        purpose='Reversión privada de la migración de ingresos; conservar con la versión anterior')
    atomic_json(folder/(identifier+'.json'),record)
    return record


def migrate(path,*,new=False):
    from .db import connect,audit
    from .audit_chain import path_lock,local_status
    from .schema import verify,install_triggers_missing
    path=Path(path).resolve()
    with path_lock(path),closing(connect(path)) as db:
        version=db.execute('PRAGMA user_version').fetchone()[0]
        if version>15:raise ValueError('Esta base requiere una versión más reciente.')
        if version in (VERSION,14,15):
            verify_layout(db)
            # Preserve existing consultation when the local audit head is bad;
            # require()/SQLite guards continue to block every business write.
            local_status(db,recover=True)
            return
        if version!=12:raise ValueError('Completa primero la actualización al esquema 12.')
        verify(db)
        populated=bool(db.execute('SELECT 1 FROM users LIMIT 1').fetchone() or db.execute('SELECT 1 FROM audit LIMIT 1').fetchone())
        try:
            db.execute('BEGIN IMMEDIATE')
            previous=reversal_snapshot(path) if not new else None
            checkpoint('backup_verified')
            for index,sql in enumerate(DDL):
                db.execute(sql)
                checkpoint('table_'+str(index))
            install_triggers_missing(db)
            verify_layout(db)
            db.execute('PRAGMA user_version=13')
            if populated:
                audit(db,None,'income-schema',dict(schema_before=12,schema_after=13,previous_backup=previous,
                    existing_money_unchanged=True))
            verify(db);checkpoint('before_commit')
            db.commit();checkpoint('after_commit')
        except BaseException:
            db.rollback();raise
        status=local_status(db,recover=True)
        if not status['ok']:raise ValueError(status['message'])
        verify(db)
