"""Exceptional offline, one-use cutover from fictional receipts to production."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .audit_chain import require, local_status
from .branding import SCHEMA_VERSION
from .clock_guard import ClockGuard
from .db import ValidationError, audit, check_password, connect
from .storage import DataLock

MARKER='trial_payments_cleared'
CONFIRMATION='SOLO COBROS DE PRUEBA'


def checkpoint(stage):
    """Process-termination test seam; no environment or runtime bypass."""
    pass


def inspect(db):
    from .restore_journal import PENDING
    source=Path(db.execute('PRAGMA database_list').fetchone()[2])
    if (source.parent/PENDING).exists():raise ValidationError('Hay una restauración pendiente. Abre Aula para resolverla antes de limpiar cobros.')
    if db.execute('PRAGMA user_version').fetchone()[0]!=SCHEMA_VERSION:
        raise ValidationError('Actualiza Aula antes de preparar los recibos. Esta herramienta no migra bases.')
    require(db)
    from .maintenance import review_database
    if not review_database(db)['ok']:
        raise ValidationError('Verificar datos y cobros detectó errores. No se borraron cobros.')
    if db.execute('SELECT 1 FROM settings WHERE key=?',(MARKER,)).fetchone():
        raise ValidationError('Esta base ya preparó sus recibos para producción. No se permite repetir la limpieza.')
    if any(db.execute('SELECT 1 FROM '+table+' LIMIT 1').fetchone() for table in ('payment_accounts','other_income','cash_deposits')):
        raise ValidationError('Hay movimientos del libro de ingresos. No se permite una limpieza automática de sus recibos.')
    documents={'guardian_documents':0,'cash_closures':db.execute('SELECT COUNT(*) FROM cash_closures').fetchone()[0]}
    for row in db.execute('SELECT snapshot_json FROM guardian_documents'):
        try:kind=json.loads(row['snapshot_json'])['kind']
        except (ValueError,KeyError,TypeError):
            raise ValidationError('Hay un documento de representante que no se pudo identificar. No se borró nada.') from None
        if kind not in ('account','solvency'):
            raise ValidationError('Hay un documento distinto de estado de cuenta o solvencia. Requiere revisión; no se borró nada.')
        documents['guardian_documents']+=1
    count,last=db.execute('SELECT COUNT(*),COALESCE(MAX(id),0) FROM payments').fetchone()
    if not count and not any(documents.values()):raise ValidationError('No hay cobros ni documentos de prueba que limpiar. No se cambió el contador.')
    digest=hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest()
    return {'preview_hash':digest,'payments':count,'last_receipt':last,**documents,
            'allocations':db.execute('SELECT COUNT(*) FROM allocations').fetchone()[0],
            'applied_cents':db.execute('SELECT COALESCE(SUM(a.amount),0) FROM allocations a JOIN payments p ON p.id=a.payment_id WHERE p.voided=0').fetchone()[0]}


def database_path(directory):
    path=Path(directory).resolve()/'colegio.sqlite3'
    if not path.is_file():raise ValidationError('No existe una base en esa carpeta. No se creará otra instalación.')
    return path


def preview(directory):
    path=database_path(directory)
    with DataLock(path.parent),closing(connect(path)) as db:
        db.execute('BEGIN')
        return inspect(db)


def clear(directory, *, username, password, preview_hash, confirmation, reason, trial_only, backup_password=None, documents_confirmed=False):
    if confirmation!=CONFIRMATION or trial_only is not True or not isinstance(reason,str) or len(reason.strip())<10:
        raise ValidationError('Confirma que TODOS los cobros son de prueba y escribe el motivo y la frase completa.')
    path=database_path(directory)
    with DataLock(path.parent),closing(connect(path)) as db:
        clock=ClockGuard(path);clock.require()
        db.execute('BEGIN')
        user=db.execute("SELECT id,password FROM users WHERE username=? AND role='admin'",(username.strip().lower(),)).fetchone()
        if not user or not check_password(password,user['password']):
            raise ValidationError('Usuario o contraseña de Administración incorrectos.')
        before=inspect(db)
        if (before['guardian_documents'] or before['cash_closures']) and documents_confirmed is not True:
            raise ValidationError('Confirma también la eliminación de estados de cuenta, solvencias y cierres de caja de prueba.')
        if before['preview_hash']!=preview_hash:raise ValidationError('Los datos cambiaron. Revisa nuevamente antes de limpiar.')
        db.rollback()
        from .backup_export import write_encrypted
        if backup_password is not None:
            from .backup_keys import unlock
            unlock(path.parent,backup_password)
        destination=path.parent/'backups'/('antes-limpiar-cobros-prueba-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.aulabak')
        backup=write_encrypted(path,destination,path.parent)
        if not backup.get('encrypted') or not backup.get('verified'):
            raise ValidationError('No se verificó el respaldo cifrado. No se borraron cobros.')
        checkpoint('after_backup')
        with db:
            db.execute('BEGIN IMMEDIATE')
            if inspect(db)['preview_hash']!=preview_hash:
                raise ValidationError('La base cambió durante el respaldo. No se borraron cobros.')
            db.execute('DELETE FROM guardian_documents')
            db.execute('DELETE FROM cash_closures');checkpoint('after_documents')
            db.execute('DELETE FROM allocations');checkpoint('after_allocations')
            db.execute('DELETE FROM payments');checkpoint('after_payments')
            db.execute("INSERT OR REPLACE INTO settings VALUES('id_floor_payments','0')")
            db.execute('INSERT INTO settings VALUES(?,?)',(MARKER,'1'))
            db.execute('DELETE FROM sessions');checkpoint('after_counter')
            audit(db,user['id'],'trial-payments-cleared',dict(before,reason=reason.strip(),backup=backup,
                first_new_receipt='R-000001',trial_only=True,one_use=True,financial_documents_confirmed=documents_confirmed))
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValidationError('La verificación final falló. Se conservaron los datos anteriores.')
            clock.require();checkpoint('before_commit')
        checkpoint('after_commit')
        if not local_status(db)['ok']:raise RuntimeError('La limpieza terminó, pero se requiere revisar la bitácora antes de abrir Aula.')
        return dict(before,backup=backup,next_receipt='R-000001')


def dialog(directory):
    from tkinter import Tk, simpledialog, messagebox
    root=Tk();root.withdraw()
    try:
        review=preview(directory)
        message=(f"Carpeta: {Path(directory).resolve()}\n\nSe eliminarán {review['payments']} cobros, incluidos los anulados, y sus aplicaciones.\n"
                 f"También se retirarán {review['guardian_documents']} estados de cuenta/solvencias y {review['cash_closures']} cierres de caja de prueba.\n"
                 'Los cargos abonados volverán a quedar pendientes. Se conservan alumnos, representantes, cuentas de acceso, cargos, egresos, tasas, configuración e historial académico.\n\n'
                 'Solo para cobros de prueba, ANTES de comenzar producción. Se puede usar UNA sola vez.\n'
                 'Se guardará un respaldo cifrado verificado y se conservará la bitácora.\n\n¿Confirmas que TODOS esos cobros, estados de cuenta, solvencias y cierres de caja son de prueba?')
        if not messagebox.askyesno('Preparar recibos para producción',message,parent=root,icon='warning'):return
        phrase=simpledialog.askstring('Confirmación',f'Escribe exactamente: {CONFIRMATION}',parent=root)
        if phrase is None:return
        username=simpledialog.askstring('Administración','Usuario de Administración:',parent=root)
        if username is None:return
        password=simpledialog.askstring('Administración','Contraseña actual:',show='*',parent=root)
        if password is None:return
        reason=simpledialog.askstring('Motivo','Motivo de esta limpieza:',initialvalue='Cobros ficticios anteriores al inicio de producción',parent=root)
        if reason is None:return
        from .backup_keys import status
        backup_password=None
        protection=status(directory)
        if not protection.get('configured'):raise ValidationError('Configura y verifica los respaldos cifrados en Aula antes de limpiar los cobros.')
        if not protection.get('ready'):
            backup_password=simpledialog.askstring('Respaldo cifrado','Contraseña del respaldo para verificar la copia previa:',show='*',parent=root)
            if backup_password is None:return
        result=clear(directory,username=username,password=password,preview_hash=review['preview_hash'],
            confirmation=phrase,reason=reason,trial_only=True,backup_password=backup_password,documents_confirmed=True)
        messagebox.showinfo('Recibos preparados','El próximo recibo será R-000001. Abre Aula e inicia sesión nuevamente.\n\nRespaldo cifrado conservado en:\n'+result['backup']['path'],parent=root)
    finally:root.destroy()
