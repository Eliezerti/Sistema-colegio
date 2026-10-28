"""Schema 14: invoice origin without rewriting historical orders or receipts."""
from contextlib import closing
from datetime import datetime
from pathlib import Path
import json

VERSION=14


def checkpoint(stage):
    """Boundary for actual process-termination tests, never a runtime switch."""


def migrate(path, *, new=False, verified_copy=False):
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
        if version!=13:raise ValueError('El ajuste del número Cashea requiere el esquema 13.')
        verify(db)
        backup=None
        try:
            db.execute('BEGIN IMMEDIATE')
            if not new:
                backup=path.parent/'backups'/f'antes-numero-cashea-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite3'
                consistent_backup(path,backup);backup.chmod(0o600)
                with closing(connect(backup)) as saved:verify(saved)
                digest=file_hash(backup)
                if not digest or file_hash(backup)!=digest:raise ValueError('El respaldo previo del número Cashea no se pudo verificar.')
                backup.with_suffix('.migration.json').write_text(json.dumps(dict(schema_before=13,schema_after=14,sha256=digest,backup=backup.name)),encoding='utf-8')
                secondary=db.execute("SELECT value FROM settings WHERE key='backup_directory'").fetchone()
                if secondary and secondary[0] and not verified_copy:
                    from .backup_export import write_cashea_migration_backup
                    write_cashea_migration_backup(backup,Path(secondary[0])/(backup.stem+'.aulabak'),path.parent)
            checkpoint('backup_verified')
            # Old manual values, authorized duplicates and frozen JSON remain byte-identical.
            db.execute("ALTER TABLE cashea_orders ADD COLUMN invoice_origin TEXT NOT NULL DEFAULT 'manual' CHECK(invoice_origin IN ('recibo','manual'))")
            db.execute("CREATE UNIQUE INDEX cashea_receipt_invoice_unique ON cashea_orders(invoice_key) WHERE invoice_origin='recibo'")
            # Rebuild the update-image trigger to include the added column.
            db.execute('DROP TRIGGER IF EXISTS audit_edit_cashea_orders')
            install_triggers_missing(db)
            db.execute("INSERT OR IGNORE INTO settings VALUES('cashea_invoice_origin','recibo')")
            checkpoint('column_created')
            db.execute('PRAGMA user_version=14')
            if not new:audit(db,None,'cashea-invoice-schema',dict(schema_before=13,schema_after=14,backup=str(backup),verified_private_copy=verified_copy))
            verify(db);checkpoint('before_commit');db.commit();checkpoint('after_commit')
        except BaseException:
            db.rollback();raise
        db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        checkpoint('verified')
