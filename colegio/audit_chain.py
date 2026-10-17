"""Versioned audit chain, SQLite runtime guards and crash-safe local head control.

Hashes detect alteration, not an attacker who controls Windows and every copy.
"""
import hashlib
import json
import os
import sqlite3
import uuid
import threading
import weakref
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from .clock_guard import atomic_json

ZERO = '0' * 64
VERSION = 11
PROTECTED = ('audit', 'audit_links', 'audit_meta')
# Session polling/expiry is deliberately absent. Settings secrets are redacted below.
SECRET_FIELDS = {'password', 'token', 'csrf', 'request_key', 'receipt_snapshot', 'snapshot_json'}
HASH_FIELDS = {'logo'}
PRIVATE_FIELDS = {'bank', 'bank_account', 'bank_document', 'account_holder', 'holder_document'}


class AuditUnavailable(ValueError):
    pass


_LOCKS = weakref.WeakValueDictionary()
_LOCKS_GUARD = threading.Lock()


def path_lock(path):
    key = os.path.normcase(str(Path(path).resolve()))
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _LOCKS[key] = lock
        return lock


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      default=lambda v: {'blob': v.hex()} if isinstance(v, bytes) else str(v))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def checkpoint(stage):
    """Real child-process fault injection boundary; no environment bypass."""


def controls(path):
    path = Path(path)
    return path.with_name(path.name+'.audit-head.json'), path.with_name(path.name+'.audit-pending.json')


def atomic(path, value):
    atomic_json(path, {'value': value, 'sha256': digest(value)})


def load(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if digest(data['value']) != data['sha256']:
        raise ValueError('Control alterado')
    return data['value']


def portable_status(db):
    """Verify only SQL content, usable on read-only snapshots on another PC."""
    try:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'audit_links', 'audit_meta'} <= tables:
            if db.execute('PRAGMA user_version').fetchone()[0] >= VERSION:
                raise ValueError('Faltan las huellas de la bitácora.')
            return {'ok': True, 'legacy': True, 'message': 'Bitácora antigua sin cadena de huellas.'}
        meta = db.execute('SELECT chain_id,baseline,head_id,head_hash FROM audit_meta WHERE id=1').fetchone()
        if not meta or db.execute('SELECT COUNT(*) FROM audit_meta').fetchone()[0] != 1:
            raise ValueError('Falta el control de la cadena.')
        expected = trigger_definitions(db)
        actual = dict(db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'"))
        normalize = lambda sql: ' '.join(sql.split()).rstrip(';')
        if any(name not in actual or normalize(actual[name]) != normalize(sql) for name,sql in expected.items()):
            raise ValueError('Falta una protección de escritura o fue modificada.')
        chain_id, baseline, head_id, head_hash = meta
        if not isinstance(chain_id,str) or len(chain_id)!=32 or baseline<0 or head_id<0:
            raise ValueError('El control de la cadena es inválido.')
        previous, last, count = ZERO, 0, 0
        for row in db.execute('''SELECT a.id,a.user_id,a.action,a.details,a.created_at,
                l.previous_hash,l.row_hash,l.legacy FROM audit a LEFT JOIN audit_links l ON l.audit_id=a.id ORDER BY a.id'''):
            record = list(row[:5])
            expected = digest({'version': 1, 'chain_id': chain_id, 'baseline': baseline, 'previous': previous, 'row': record})
            if row[5] != previous or row[6] != expected or row[7] != int(row[0] <= baseline):
                raise ValueError('Una operación o su huella fue alterada.')
            previous, last, count = expected, row[0], count+1
        if count != db.execute('SELECT COUNT(*) FROM audit_links').fetchone()[0] or (last, previous) != (head_id, head_hash):
            raise ValueError('Faltan operaciones al final de la bitácora.')
        return {'ok': True, 'legacy': False, 'head': {'chain_id': chain_id, 'id': last, 'hash': previous},
                'count': count, 'baseline': baseline,
                'message': 'Cadena comprobada. Los registros anteriores a la migración se protegen desde esa revisión.'}
    except (sqlite3.Error, ValueError, TypeError, IndexError) as error:
        return {'ok': False, 'message': 'No se pudo comprobar la bitácora. '+str(error)}


def local_status(db, *, recover=False):
    path = db.execute('PRAGMA database_list').fetchone()[2]
    with path_lock(path):
        return _local_status(db, recover=recover)


def _local_status(db, *, recover=False):
    status = portable_status(db)
    if not status['ok'] or status.get('legacy'):
        return status
    path = db.execute('PRAGMA database_list').fetchone()[2]
    if not path:
        return status
    head, pending = controls(path)
    try:
        if pending.exists():
            intent = load(pending)
            if status['head'] not in (intent['before'], intent['after']):
                raise ValueError('La operación pendiente no coincide con la base.')
            if recover:
                atomic(head, status['head'])
                pending.unlink()
            else:
                raise ValueError('Hay un control pendiente de completar. Cierra y abre Aula.')
        if load(head) != status['head']:
            raise ValueError('La última operación no coincide con el control separado.')
    except (OSError, ValueError, KeyError, TypeError) as error:
        return dict(status, ok=False, message='No se pudo comprobar la bitácora. '+str(error))
    return status


def require(db):
    if getattr(db, '_audit_checked', False):
        return
    status = local_status(db)
    if not status['ok']:
        raise AuditUnavailable(status['message']+' Se mantienen la consulta y los respaldos; no se guardarán cambios.')
    db._audit_checked = db.in_transaction
    db._audit_expected_before = status.get('head') if db.in_transaction else None


def sanitize(details):
    if isinstance(details, dict):
        result = {}
        for key, value in details.items():
            if key.lower() in SECRET_FIELDS or any(part in key.lower() for part in
                    ('password', 'contraseña', 'secret', 'recovery_key', 'private_key')):
                continue
            if key in PRIVATE_FIELDS:
                result[key] = 'Dato privado modificado'
            elif key in HASH_FIELDS:
                result[key] = ({part: {'sha256': digest(content)} for part, content in value.items()}
                               if isinstance(value, dict) else {'sha256': digest(value)})
            else:
                result[key] = sanitize(value)
        return result
    if isinstance(details, (list, tuple)):
        return [sanitize(value) for value in details]
    return details


def append(db, user_id, action, details):
    # Historical initialization is completed before installing the guarded schema.
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='audit_meta'").fetchone():
        db.execute('INSERT INTO audit(user_id,action,details,created_at) VALUES(?,?,?,?)',
                   (user_id, action, canonical(sanitize(details)), datetime.now(timezone.utc).isoformat()))
        return
    if not db.in_transaction: db.execute('BEGIN IMMEDIATE')
    require(db)
    db._audit_dirty = True
    details = dict(details) if isinstance(details,dict) else {'detalle':details}
    if user_id is not None:
        actor = db.execute('SELECT id,name,username,role FROM users WHERE id=?',(user_id,)).fetchone()
        if actor: details['responsable'] = dict(zip(('id','nombre','usuario','perfil'),actor))
    meta = db.execute('SELECT chain_id,head_hash,baseline FROM audit_meta WHERE id=1').fetchone()
    db._audit_authorized = True
    try:
        cursor = db.execute('INSERT INTO audit(user_id,action,details,created_at) VALUES(?,?,?,?)',
                           (user_id, action, canonical(sanitize(details)), datetime.now(timezone.utc).isoformat()))
        row = db.execute('SELECT id,user_id,action,details,created_at FROM audit WHERE id=?', (cursor.lastrowid,)).fetchone()
        hashed = digest({'version': 1, 'chain_id': meta[0], 'baseline': meta[2], 'previous': meta[1], 'row': list(row)})
        db.execute('INSERT INTO audit_links VALUES(?,?,?,0)', (row[0], meta[1], hashed))
        db.execute('UPDATE audit_meta SET head_id=?,head_hash=? WHERE id=1', (row[0], hashed))
    finally:
        db._audit_authorized = False


class AuditConnection(sqlite3.Connection):
    def prepare_audit(self):
        self._write_locked = False
        self._savepoints = []
        path = super().execute('PRAGMA database_list').fetchone()[2]
        self._head_lock = path_lock(path) if path else threading.RLock()
        self._audit_authorized = False
        self._audit_checked = False
        self._audit_dirty = False
        self._audit_expected_before = None
        self.audit_user = None
        self._edits = []
        self.create_function('aula_audit_write', 0, lambda: int(self._audit_authorized))
        def allowed():
            require(self)
            self._audit_dirty = True
            return 1
        self.create_function('aula_data_write', 0, allowed)
        def edited(table, old, new):
            old, new = json.loads(old), json.loads(new)
            if table == 'settings':
                key = new['key']
                if any(part in key.lower() for part in ('password', 'secret', 'recovery', 'security_notice')):
                    return 0
            changes = {k: {'anterior': old.get(k), 'nuevo': new[k]} for k in new
                       if new[k] != old.get(k) and k not in SECRET_FIELDS}
            if table in ('bank_movements','statement_imports','bank_classifications','invoice_preferences','invoice_batches','invoice_templates','invoice_template_versions','invoice_printer_profiles','invoices') and changes:
                changes = {'huella_del_registro': {'anterior': digest(old), 'nuevo': digest(new)}}
            changes = sanitize(changes)
            if changes:
                self._edits.append({'tabla': table, 'registro': new.get('id', new.get('key', new.get('rate_date'))),
                                    'cambios': changes})
            return 0
        self.create_function('aula_record_edit', 3, edited)

    def _acquire_write(self):
        if not self._write_locked:
            self._head_lock.acquire()
            self._write_locked = True

    def _release_write(self):
        if self._write_locked:
            self._write_locked = False
            self._head_lock.release()

    def execute(self, sql, *args):
        words = sql.strip().rstrip(';').split()
        operation = words[0].upper() if words else ''
        upper = [word.upper() for word in words]
        # Keep the SQLite writer and local control publication in the SAME critical
        # section. SQLite alone releases its writer at COMMIT, slightly too early.
        if operation in ('COMMIT','END'):
            self.commit(); return super().cursor()
        if operation == 'ROLLBACK' and 'TO' not in upper:
            self.rollback(); return super().cursor()
        savepoint = None
        if operation == 'SAVEPOINT':
            savepoint = {'name':words[1].strip('"').lower(), 'edits':len(self._edits),
                'dirty':self._audit_dirty, 'checked':self._audit_checked,
                'before':self._audit_expected_before, 'outer':not self.in_transaction}
        if operation == 'RELEASE' and self._savepoints:
            name = words[-1].strip('"').lower()
            frame = next((f for f in reversed(self._savepoints) if f['name']==name),None)
            if frame and frame['outer']:
                self.commit(); return super().cursor()  # RELEASE outer == COMMIT.
        if operation in ('INSERT','UPDATE','DELETE','REPLACE','CREATE','ALTER','DROP','SAVEPOINT') or (
                operation=='BEGIN' and ('IMMEDIATE' in upper or 'EXCLUSIVE' in upper)):
            self._acquire_write()
        try:
            result = super().execute(sql, *args)
            if savepoint: self._savepoints.append(savepoint)
            if operation in ('RELEASE','ROLLBACK') and self._savepoints:
                name = words[-1].strip('"').lower()
                for index in range(len(self._savepoints)-1,-1,-1):
                    frame = self._savepoints[index]
                    if frame['name'] != name: continue
                    if operation == 'ROLLBACK':
                        del self._edits[frame['edits']:]
                        self._audit_dirty,self._audit_checked = frame['dirty'],frame['checked']
                        self._audit_expected_before = frame['before']
                        del self._savepoints[index+1:]
                    else: del self._savepoints[index:]
                    break
            return result
        finally:
            if not self.in_transaction: self._release_write()

    def executemany(self, sql, parameters):
        self._acquire_write()
        try:
            return super().executemany(sql, parameters)
        finally:
            if not self.in_transaction: self._release_write()

    def executescript(self, sql):
        if super().execute("SELECT 1 FROM sqlite_master WHERE name='audit_meta'").fetchone():
            raise AuditUnavailable('Usa la escritura transaccional protegida de Aula; no scripts que confirmen cambios por separado.')
        self._acquire_write()
        try:
            return super().executescript(sql)  # Only the existing pre-A4 initializer.
        finally:
            if not self.in_transaction: self._release_write()

    def commit(self):
        try:
            return self._commit_audit()
        finally:
            self._savepoints.clear()
            self._release_write()

    def _commit_audit(self):
        if not self.in_transaction:
            return super().commit()
        if not self._audit_dirty:
            return super().commit()
        for edit in self._edits:
            append(self, self.audit_user, 'edit-values', edit)
        self._edits.clear()
        status = portable_status(self)
        if not status['ok']:
            self.rollback()
            raise AuditUnavailable(status['message'])
        path = self.execute('PRAGMA database_list').fetchone()[2]
        head, pending = controls(path) if path else (None, None)
        intent = None
        if head and not status.get('legacy'):
            try:
                before = load(head)
                if before != self._audit_expected_before:
                    raise ValueError('El control cambió durante la operación.')
                if before != status['head']:
                    intent = {'before': before, 'after': status['head']}
                    atomic(pending, intent)
            except (OSError, ValueError, KeyError) as error:
                self.rollback()
                raise AuditUnavailable('No se pudo guardar el control de la bitácora.') from error
        checkpoint('before_commit')
        super().commit()
        checkpoint('after_commit')
        if intent:
            atomic(head, intent['after'])
            checkpoint('after_head')
            pending.unlink()
        self._audit_checked = False
        self._audit_dirty = False
        self._audit_expected_before = None

    def rollback(self):
        self._savepoints.clear()
        self._edits.clear()
        self._audit_checked = False
        self._audit_dirty = False
        self._audit_expected_before = None
        try:
            return super().rollback()
        finally:
            self._release_write()

    def close(self):
        try:
            return super().close()
        finally:
            self._release_write()

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.rollback()
        else:
            try:
                self.commit()
            except BaseException:
                self.rollback()
                raise
        return False


def trigger_definitions(db):
    definitions = {}
    for table in PROTECTED:
        for operation in ('INSERT', 'UPDATE', 'DELETE'):
            allow = 'aula_audit_write()=0' if table != 'audit' or operation == 'INSERT' else '1'
            definitions[f'audit_guard_{table}_{operation.lower()}'] = f'''CREATE TRIGGER audit_guard_{table}_{operation.lower()} BEFORE {operation} ON {table}
                WHEN {allow} BEGIN SELECT RAISE(ABORT,'La bitácora está protegida.'); END'''
    # Guard EVERY application table except session bookkeeping. This also covers future
    # callers that forget the HTTP gate, including automatic monthly generation.
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for table in tables:
        if table in (*PROTECTED, 'sessions'):
            continue
        for operation in ('INSERT', 'UPDATE', 'DELETE'):
            definitions[f'audit_data_{table}_{operation.lower()}'] = f'''CREATE TRIGGER audit_data_{table}_{operation.lower()} BEFORE {operation} ON "{table}"
                BEGIN SELECT CASE WHEN aula_data_write()=0 THEN RAISE(ABORT,'Revisa la bitácora.') END; END'''
        columns = [r[1] for r in db.execute(f'PRAGMA table_info("{table}")')]
        def object_sql(prefix):
            return 'json_object('+','.join("'"+c+"',"+prefix+'."'+c+'"' for c in columns)+')'
        definitions[f'audit_edit_{table}'] = f'''CREATE TRIGGER audit_edit_{table} AFTER UPDATE ON "{table}" BEGIN
            SELECT aula_record_edit('{table}',{object_sql('OLD')},{object_sql('NEW')}); END'''

    return definitions


def install_triggers(db):
    for sql in trigger_definitions(db).values():
        db.execute(sql)


def migrate(path, *, new=False):
    """Add companion tables without rewriting original rows; verified reversible snapshot."""
    path = Path(path).resolve()
    with path_lock(path), closing(sqlite3.connect(path)) as db:
        db.row_factory = sqlite3.Row
        if db.execute('PRAGMA user_version').fetchone()[0] >= VERSION:
            local_status(db, recover=True)
            return
        # No other connection may write between the verified snapshot and DDL.
        db.execute('BEGIN IMMEDIATE')
        folder = path.parent/'backups'
        if not new: folder.mkdir(exist_ok=True)
        backup = folder/('antes-bitacora-'+uuid.uuid4().hex+'.sqlite3')
        try:
            backup_hash = None
            if not new:
                with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as source, closing(sqlite3.connect(backup)) as copy:
                    source.backup(copy)
                    copy.execute('PRAGMA journal_mode=DELETE')
                    if [r[0] for r in copy.execute('PRAGMA integrity_check')] != ['ok'] or copy.execute('PRAGMA foreign_key_check').fetchone():
                        raise ValueError('El respaldo previo no pasó la revisión.')
                with open(backup,'r+b') as saved:
                    saved.flush(); os.fsync(saved.fileno())
                from .backup_inspection import file_hash
                backup_hash = file_hash(backup)
                if file_hash(backup) != backup_hash:
                    raise ValueError('No se pudo verificar la copia previa.')
            if not new:
                atomic(backup.with_suffix('.migration.json'), {'sha256': backup_hash, 'schema_before': 10,
                      'backup': backup.name, 'purpose': 'Reversión de la migración de bitácora'})
            checkpoint('migration_backup')
            db.execute('CREATE TABLE audit_links(audit_id INTEGER PRIMARY KEY REFERENCES audit(id),previous_hash TEXT NOT NULL,row_hash TEXT NOT NULL,legacy INTEGER NOT NULL)')
            db.execute('CREATE TABLE audit_meta(id INTEGER PRIMARY KEY CHECK(id=1),chain_id TEXT NOT NULL,baseline INTEGER NOT NULL,head_id INTEGER NOT NULL,head_hash TEXT NOT NULL)')
            chain_id, previous, last = uuid.uuid4().hex, ZERO, 0
            baseline = db.execute('SELECT COALESCE(MAX(id),0) FROM audit').fetchone()[0]
            for row in db.execute('SELECT id,user_id,action,details,created_at FROM audit ORDER BY id').fetchall():
                hashed = digest({'version': 1, 'chain_id': chain_id, 'baseline': baseline, 'previous': previous, 'row': list(row)})
                db.execute('INSERT INTO audit_links VALUES(?,?,?,1)', (row[0], previous, hashed))
                previous, last = hashed, row[0]
            db.execute('INSERT INTO audit_meta VALUES(1,?,?,?,?)', (chain_id, last, last, previous))
            install_triggers(db)
            db.execute(f'PRAGMA user_version={VERSION}')
            checkpoint('migration_ddl')
            if not portable_status(db)['ok']:
                raise ValueError('No se pudo verificar la migración.')
            head, pending = controls(path)
            # Same replay protocol as normal transactions, but an absent/legacy SQL
            # chain proves the pre-commit side of a migration interruption.
            atomic(pending, {'before': None, 'after': portable_status(db)['head']})
            db.commit()
            checkpoint('migration_commit')
            atomic(head, portable_status(db)['head'])
            pending.unlink()

        except BaseException:
            db.rollback()
            raise


def adopt_restored(path):
    """Only called after the A1 confirmed manifest verified and published this file."""
    with path_lock(path), closing(sqlite3.connect(path)) as db:
        status = portable_status(db)
        if not status['ok']:
            raise AuditUnavailable(status['message'])
        if not status.get('legacy'):
            head, pending = controls(path)
            atomic(head, status['head'])
            pending.unlink(missing_ok=True)
