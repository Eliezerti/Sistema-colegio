"""Verified, restartable retirement of the former staff tables (schema 12)."""
import os
import sqlite3
from contextlib import closing
from pathlib import Path

VERSION = 12
RETIRED = ('salary_receipts', 'payroll_plans', 'employees', 'positions')
EXPENSE_SQL = '''CREATE TABLE expenses_new(
    id INTEGER PRIMARY KEY,concept TEXT NOT NULL,category TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK(amount>0),spent_on TEXT NOT NULL,
    reference TEXT NOT NULL DEFAULT '',created_by INTEGER NOT NULL REFERENCES users(id),
    voided INTEGER NOT NULL DEFAULT 0,void_reason TEXT NOT NULL DEFAULT '',
    currency TEXT NOT NULL,received_amount INTEGER NOT NULL,exchange_rate TEXT NOT NULL,
    method TEXT NOT NULL DEFAULT 'No especificado')'''
COLUMNS = ('id','concept','category','amount','spent_on','reference','created_by',
           'voided','void_reason','currency','received_amount','exchange_rate','method')


def checkpoint(stage):
    """Test seam: tests terminate an actual child process at these boundaries."""


def verify(db):
    if [r[0] for r in db.execute('PRAGMA integrity_check')] != ['ok']:
        raise ValueError('La base no pasó la revisión de integridad.')
    if db.execute('PRAGMA foreign_key_check').fetchone():
        raise ValueError('La base contiene referencias inválidas.')
    from .audit_chain import portable_status
    status = portable_status(db)
    if not status['ok']:
        raise ValueError(status['message'])


def migrate(path, *, new=False):
    from .db import connect, audit
    from .audit_chain import path_lock, local_status
    from .storage import consistent_backup
    path = Path(path).resolve()
    # The startup DataLock excludes other Aula processes; this lock also excludes
    # writers within this process. Never publish automatic backups during migration.
    with path_lock(path), closing(connect(path)) as db:
        version = db.execute('PRAGMA user_version').fetchone()[0]
        if version > VERSION:
            if version not in (13,14):
                raise ValueError('Esta base requiere una versión más reciente de Aula.')
            return
        work = path.parent / '.aula-schema-12'
        backup = work / 'previa.sqlite3'
        if version < VERSION:
            verify(db)
            work.mkdir(exist_ok=True)
            # Hold SQLite's writer reservation across snapshot and DDL as well
            # as the process lock: no competing writer can change the reference.
            db.execute('PRAGMA foreign_keys=OFF')
            db.execute('PRAGMA secure_delete=ON')
            try:
                db.execute('BEGIN IMMEDIATE')
                if not new:
                    consistent_backup(path, backup)
                    with closing(sqlite3.connect(backup)) as saved:
                        verify(saved)
                    from .backup_inspection import file_hash
                    before_hash = file_hash(backup)
                    if not before_hash or file_hash(backup) != before_hash:
                        raise ValueError('No se pudo verificar el respaldo previo.')
                checkpoint('backup_verified')
                before = [tuple(r) for r in db.execute('SELECT '+','.join(COLUMNS)+' FROM expenses ORDER BY id')]
                db.execute(EXPENSE_SQL)
                db.execute('INSERT INTO expenses_new('+','.join(COLUMNS)+') SELECT '+','.join(COLUMNS)+' FROM expenses')
                checkpoint('expenses_copied')
                for table in ('salary_receipts','payroll_plans'):
                    db.execute('DROP TABLE IF EXISTS '+table)
                db.execute('DROP TABLE expenses')
                db.execute('ALTER TABLE expenses_new RENAME TO expenses')
                for table in ('employees','positions'):
                    db.execute('DROP TABLE IF EXISTS '+table)
                # Replace only the guards whose column layout changed. Other guards
                # and every original audit row/link/head remain intact.
                install_triggers_missing(db)
                for row in db.execute("SELECT key FROM settings WHERE key LIKE 'id_floor_%'").fetchall():
                    if row[0][9:] in RETIRED:
                        db.execute('DELETE FROM settings WHERE key=?', (row[0],))
                for table in ('payments','expenses','students','guardians','enrollment_documents'):
                    db.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',('id_floor_'+table,'0'))
                after = [tuple(r) for r in db.execute('SELECT '+','.join(COLUMNS)+' FROM expenses ORDER BY id')]
                if after != before:
                    raise ValueError('Los egresos cambiaron durante la migración.')
                db.execute('PRAGMA user_version=12')
                if not new:
                    audit(db,None,'retire-staff-module',{'schema_before':version,'schema_after':VERSION,
                          'expense_count':len(after),'expense_totals_preserved':True})
                verify(db)
                checkpoint('before_commit')
                db.commit()  # AuditConnection publishes the pending/head protocol.
                checkpoint('after_commit')
            except BaseException:
                db.rollback()
                raise
            finally:
                db.execute('PRAGMA foreign_keys=ON')
        # Also runs after a kill immediately after COMMIT. Erase freed pages and
        # truncate WAL before allowing a new backup/export or starting the server.
        local_status(db, recover=True)
        db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        if work.exists():
            db.execute('VACUUM')
            db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            verify(db)
            checkpoint('compacted')
            # The verified pre-migration snapshot is for crash rollback only. It
            # contains retired data, so is not exported/retained as a new backup.
            backup.unlink(missing_ok=True)
            work.rmdir()


def install_triggers_missing(db):
    from .audit_chain import trigger_definitions
    present = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    for name, sql in trigger_definitions(db).items():
        if name not in present:
            db.execute(sql)
