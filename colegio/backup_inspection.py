"""Read snapshots on a disposable copy; never open SQLite on the supplied USB/file."""
import hashlib
import json
import shutil
import sqlite3
import tempfile
from contextlib import closing, contextmanager
from pathlib import Path

from .branding import SCHEMA_VERSION

SEQUENCES = ('payments', 'expenses', 'students', 'guardians', 'enrollment_documents')
REQUIRED = {
    'settings': {'key','value'}, 'users': {'id','username','name','password','role'},
    'students': {'id','name','guardian_id'}, 'guardians': {'id','name'}, 'grades': {'id'},
    'charges': {'id','student_id','amount','cancelled'},
    'payments': {'id','student_id','amount','paid_on','method','reference','currency',
                 'received_amount','exchange_rate','receipt_snapshot','request_key','voided','created_at'},
    'expenses': {'id','amount','spent_on','currency','received_amount','voided'},
    'allocations': {'payment_id','charge_id','amount'}, 'audit': {'user_id','action','details','created_at'},
    'sessions': {'token'}, 'exchange_rates': {'rate_date','rate'},
}


class NewerSchemaError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',',':'),
                      default=lambda v: {'blob_hex':v.hex()} if isinstance(v,bytes) else str(v))


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path):
    digest=hashlib.sha256()
    with open(path,'rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''): digest.update(block)
    return digest.hexdigest()


@contextmanager
def readonly(path, *, immutable=True):
    uri=Path(path).resolve().as_uri()+'?mode=ro'+('&immutable=1' if immutable else '')
    with closing(sqlite3.connect(uri,uri=True)) as db:
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        yield db


def validate(db):
    version=db.execute('PRAGMA user_version').fetchone()[0]
    if version>SCHEMA_VERSION:
        raise NewerSchemaError(f'Este respaldo usa el esquema {version}; Aula admite hasta {SCHEMA_VERSION}. Actualiza Aula antes de restaurarlo.')
    if [r[0] for r in db.execute('PRAGMA integrity_check')]!=['ok']:
        raise ValueError('El respaldo tiene errores de integridad. No se reemplazará la base.')
    if db.execute('PRAGMA foreign_key_check').fetchone():
        raise ValueError('El respaldo contiene referencias inválidas. No se reemplazará la base.')
    tables={r['name'] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    for table,expected in REQUIRED.items():
        if table not in tables or not expected <= {r['name'] for r in db.execute(f'PRAGMA table_info("{table}")')}:
            raise ValueError('El archivo no es un respaldo compatible de Aula.')
    if version>=13:
        from .income_schema import verify_layout
        verify_layout(db)
    if version>=14:
        from .bank_schema import verify_layout as verify_bank
        verify_bank(db)
    if version>=15:
        from .month_schema import verify_layout as verify_month
        verify_month(db)
    if version>=16:
        from .invoice_schema import verify_layout as verify_invoice
        verify_invoice(db)
    return version,tables


def inspect_copy(path):
    with readonly(path) as db:
        version,tables=validate(db)
        records={}
        for table in sorted(tables-{'sessions'}):
            # Quote names read from the schema, not supplied SQL.
            quoted='"'+table.replace('"','""')+'"'
            records[table]=[dict(r) for r in db.execute(f'SELECT * FROM {quoted}')]
            records[table].sort(key=canonical)
        settings={r['key']:r['value'] for r in records['settings']}
        floors={}
        for table in SEQUENCES:
            floor=int(settings.get('id_floor_'+table,'0'))
            if floor<0 or floor>=2147483647: raise ValueError('No se pudo comprobar un correlativo del respaldo.')
            floors[table]=max([floor,*[r['id'] for r in records.get(table,[])]])
        payments=records['payments']
        last=max(payments,key=lambda p:p['id'],default=None)
        paid={}
        valid=[p for p in payments if not p['voided']]
        for p in valid: paid[p['currency']]=paid.get(p['currency'],0)+p['received_amount']
        valid_ids={p['id'] for p in valid}
        applied={}
        for a in records['allocations']:
            if a['payment_id'] in valid_ids: applied[a['charge_id']]=applied.get(a['charge_id'],0)+a['amount']
        balance=sum(c['amount']-applied.get(c['id'],0) for c in records['charges'] if not c['cancelled'])
        from .audit_chain import portable_status
        audit_status=portable_status(db)
        if not audit_status['ok']:raise ValueError(audit_status['message'])
        summary={'retired_counts':{t:len(records.get(t,[])) for t in ('employees','positions','payroll_plans','salary_receipts') if t in records},'audit':audit_status,'schema':version,'integrity':'ok','references':'ok','students':len(records['students']),
            'payments':len(payments),'valid_payments':len(valid),'voided_payments':len(payments)-len(valid),
            'income_usd':sum(p['amount'] for p in valid),'received':paid,'balance_usd':balance,
            'last_payment':({'id':last['id'],'receipt':f"R-{last['id']:06d}",'paid_on':last['paid_on'],
                             'created_at':last['created_at']} if last else None),
            'created_at':None,'creation_note':'No se conoce una fecha fiable de creación de este respaldo.',
            'floors':floors}
        return {'summary':summary,'records':records,'floors':floors}


@contextmanager
def staged_backup(source,credential=None,credential_kind='password',*,temporary_root=None):
    source=Path(source).resolve()
    if not source.is_file(): raise ValueError('Selecciona un archivo de respaldo existente.')
    wal=source.with_name(source.name+'-wal')
    if wal.exists() and wal.stat().st_size:
        raise ValueError('El archivo tiene un WAL asociado. Selecciona un respaldo completo creado por Aula, no una base activa.')
    from .backup_temporary import private_root
    with tempfile.TemporaryDirectory(prefix='aula-revisar-respaldo-',dir=temporary_root or private_root()) as temporary:
        copy=Path(temporary)/'copia.sqlite3'
        shutil.copyfile(source,copy)  # No SQLite handle or sidecar is created at the source.
        source_hash=file_hash(copy)
        from .backup_crypto import decrypt,MAGIC,MAX_DATABASE,MAX_HEADER
        with copy.open('rb') as saved:prefix=saved.read(8)
        encrypted=prefix.startswith(b'AULABK')
        if encrypted:
            if copy.stat().st_size>MAX_DATABASE+MAX_HEADER+60:raise ValueError('El respaldo supera 512 MB.')
            data,header=decrypt(copy.read_bytes(),credential,credential_kind)
            copy.write_bytes(data)
        result=inspect_copy(copy)
        result['summary']['unencrypted']=not encrypted
        # This is an observed PC timestamp, not a certified cloud creation date.
        yield copy,result,source_hash


def probe_backup(source,credential=None,credential_kind='password'):
    with staged_backup(source,credential,credential_kind) as (_,data,digest):
        return dict(data['summary'],sha256=digest)
