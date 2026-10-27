"""Reviewed, replayable restoration. Does not migrate schema or generate tuition."""
import argparse
import json
import os
import shutil
import sqlite3
import tempfile
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .backup_inspection import (SEQUENCES, NewerSchemaError, fingerprint, file_hash,
                                inspect_copy, staged_backup, probe_backup)
from .db import audit, connect
from .restore_journal import (finish_pending, store_pending, sync_file,
                              sync_directory, windows_actor, HISTORY)
from .restore_reports import compare, loss_csv, loss_pdf, table_label
from .storage import DataLock, consistent_backup
from .backup_temporary import private_root

PLAIN='RESTAURAR'
LOSS='RESTAURAR CON PÉRDIDA DE DATOS'
UNKNOWN='RESTAURAR SIN PODER COMPARAR'


class ReviewRequired(ValueError):
    pass


def current_copy(directory,temporary):
    target=directory/'colegio.sqlite3'
    if not target.exists() and not any(target.with_name(target.name+s).exists() for s in ('-wal','-shm','-journal')):
        return 'absent',None
    copy=Path(temporary)/'actual.sqlite3'
    try:
        if not target.is_file(): return 'unreadable',None
        consistent_backup(target,copy)
        return 'readable',inspect_copy(copy)
    except NewerSchemaError: raise
    except (sqlite3.Error,ValueError,RuntimeError): return 'unreadable',None
    # IO/permission failures are not disguised as corruption to bypass comparison.


def make_review(incoming,source_hash,state,current):
    comparison=compare(current,incoming) if current else {'has_loss':False,'counts':{},'details':[],
        'payment_changes':None if state=='unreadable' else 0,'expense_changes':None if state=='unreadable' else 0}
    phrase=UNKNOWN if state=='unreadable' else LOSS if comparison['has_loss'] else PLAIN
    floors={t:max(incoming['floors'][t],current['floors'][t] if current else 0) for t in SEQUENCES}
    result={'backup':incoming['summary'],'current':current['summary'] if current else None,
        'current_state':state,'comparison':comparison,'confirmation':phrase,'floors':floors,
        'comparison_note':'No se pudo comparar' if state=='unreadable' else 'No hay base actual' if state=='absent' else 'Comparación completa',
        'sha256':source_hash,'requires_floor_review':state=='unreadable','unencrypted':incoming['summary'].get('unencrypted',True)}
    result['preview_hash']=fingerprint({'result':result,'current_records':current['records'] if current else None})
    return result


def preview_restore(backup,directory,*,credential=None,credential_kind='password'):
    directory=Path(directory).resolve()
    if Path(backup).resolve()==directory/'colegio.sqlite3': raise ValueError('Selecciona un respaldo distinto de la base activa.')
    with staged_backup(backup,credential,credential_kind) as (_,incoming,digest),DataLock(directory):
        finish_pending(directory)
        with tempfile.TemporaryDirectory(prefix='aula-comparar-',dir=private_root()) as temp:
            state,current=current_copy(directory,temp)
            return make_review(incoming,digest,state,current)


def restore(backup,directory,*,preview_hash=None,confirmation=None,emergency_floors=None,credential=None,credential_kind='password'):
    directory=Path(directory).resolve();target=directory/'colegio.sqlite3'
    if Path(backup).resolve()==target: raise ValueError('Selecciona un respaldo distinto de la base activa.')
    with staged_backup(backup,credential,credential_kind) as (staged,incoming,digest),DataLock(directory):
        finish_pending(directory)
        with tempfile.TemporaryDirectory(prefix='aula-comparar-',dir=private_root()) as temp:
            state,current=current_copy(directory,temp)
            review=make_review(incoming,digest,state,current)
        if confirmation!=review['confirmation'] or preview_hash!=review['preview_hash']:
            raise ReviewRequired('Revisa nuevamente la comparación y escribe '+review['confirmation']+'. No se reemplazó la base.')
        floors=dict(review['floors'])
        if review['requires_floor_review']:
            if not isinstance(emergency_floors,dict) or set(emergency_floors)!=set(SEQUENCES):
                raise ReviewRequired('No se pudieron comprobar los últimos correlativos de la base dañada. Revisa los cinco números antes de recuperar.')
            for table in SEQUENCES:
                value=emergency_floors[table]
                if isinstance(value,bool) or not isinstance(value,int) or not floors[table]<=value<2147483647:
                    raise ReviewRequired('Un correlativo declarado es inválido o menor que el del respaldo.')
                floors[table]=value
        operation_id=uuid.uuid4().hex
        folder=directory/'backups';folder.mkdir(exist_ok=True)
        raw=folder/f'originales-antes-restauracion-{operation_id}';raw.mkdir()
        originals=[target.with_name(target.name+s) for s in ('','-wal','-shm','-journal','.audit-head.json','.audit-pending.json')]
        raw_hashes={}
        for original in originals:
            if original.exists():
                shutil.copy2(original,raw/original.name);sync_file(raw/original.name)
                raw_hashes[original.name]=file_hash(raw/original.name)
        sync_directory(raw)
        previous=folder/f'antes-restauracion-{operation_id}.sqlite3' if state=='readable' else None
        if previous:
            consistent_backup(target,previous)
            old=inspect_copy(previous)
            if fingerprint(old['records'])!=fingerprint(current['records']):
                raise ReviewRequired('La base actual cambió durante la revisión. No se restauró; vuelve a comparar.')
        elif state=='unreadable':
            damaged=folder/f'danado-antes-restauracion-{operation_id}'
            raw.rename(damaged);raw=damaged
        candidate_dir=folder/f'restauracion-{operation_id}';candidate_dir.mkdir()
        candidate=candidate_dir/'candidata.sqlite3'
        consistent_backup(staged,candidate)
        event={'operation_id':operation_id,'action':'restore-backup','at':datetime.now(timezone.utc).isoformat(),
            'actor':windows_actor(),'source_sha256':digest,'source_schema':incoming['summary']['schema'],
            'current_state':state,'comparison_counts':review['comparison']['counts'],
            'payment_changes':review['comparison']['payment_changes'],'expense_changes':review['comparison']['expense_changes'],
            'floors':floors,'floors_declared':bool(emergency_floors),'confirmation':confirmation}
        event['source_encrypted']=not review['unencrypted']
        event['excluded_movements']=[d for d in review['comparison']['details'] if d['type'] in ('payments','expenses','cashea_orders','cashea_settlements')]
        reports={}
        if review['comparison']['has_loss']:
            for extension,payload in [('csv',loss_csv(review['comparison'])),('pdf',loss_pdf(review['comparison'],operation_id))]:
                report=folder/f'antes-restauracion-{operation_id}-perdidas.{extension}'
                with open(report,'xb') as saved:
                    saved.write(payload);saved.flush();os.fsync(saved.fileno())
                reports[report.relative_to(directory).as_posix()]=file_hash(report)
        event['reports']=[str(directory/r) for r in reports]
        event['previous_backup']=str(previous) if previous else None
        event['original_files']=str(raw)
        event['previous_audit_head']=current['summary'].get('audit',{}).get('head') if current else None
        event['source_audit_head']=incoming['summary'].get('audit',{}).get('head')
        event['previous_sha256']=file_hash(previous) if previous else None
        from .audit_chain import adopt_restored
        adopt_restored(candidate)
        # Upgrade only the staged candidate, after A1 approval and original-copy
        # preservation, before publishing any database that can serve requests.
        from .db import initialize
        initialize(candidate,verified_copy=True)
        with closing(connect(candidate)) as db,db:
            db.execute('PRAGMA synchronous=FULL')
            for table,floor in floors.items():
                db.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                           ('id_floor_'+table,str(floor)))
            audit(db,None,'restore-backup',event)
        with closing(sqlite3.connect(candidate)) as compact:
            compact.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            compact.execute('PRAGMA journal_mode=DELETE')
        sync_file(candidate);probe_backup(candidate)
        operation={'id':operation_id,'phase':'prepared','candidate':candidate.relative_to(directory).as_posix(),
            'candidate_hash':file_hash(candidate),'previous':previous.relative_to(directory).as_posix() if previous else None,
            'previous_hash':file_hash(previous) if previous else None,'raw':raw.relative_to(directory).as_posix(),
            'raw_hashes':raw_hashes,'event':event,'reports':reports}
        sync_directory(folder);sync_directory(candidate_dir)
        store_pending(directory,operation)
        finish_pending(directory)
    return target


def last_restore(directory):
    return json.loads((Path(directory)/HISTORY).read_text(encoding='utf-8'))[-1]


def review_text(review):
    def summary(title,s):
        if s is None:return title+': '+review['comparison_note']
        last=s['last_payment'];last_label=f"{last['receipt']} · pago {last['paid_on']} · registrado {last['created_at']}" if last else 'Sin pagos'
        received=' · '.join(f'{currency} {value/100:.2f}' for currency,value in s['received'].items()) or 'Sin cobros válidos'
        cashea=s.get('cashea',{})
        extra=(f"\nCashea: {s['cashea_orders']} órdenes; {s['cashea_settlements']} liquidaciones; pendiente USD {cashea['pending']/100:.2f} (no es caja)." if cashea else '')
        return f"{title}: {s['students']} alumnos; {s['payments']} pagos ({s['voided_payments']} anulados); cobrado USD {s['income_usd']/100:.2f}.\nRecibido por moneda: {received}\nÚltimo pago: {last_label}"+extra
    lines=[summary('Base actual',review['current']),summary('Respaldo',review['backup']),review['backup']['creation_note'],review['backup'].get('audit',{}).get('message','Bitácora antigua sin cadena de huellas.'),
        ('Advertencia: respaldo antiguo sin cifrar.' if review['unencrypted'] else 'Cifrado autenticado y comprobado.')+' No se generan mensualidades al revisarlo.']
    lines.extend(f'{table_label(table)}: {count} registros ausentes o diferentes' for table,count in review['comparison']['counts'].items())
    if review['requires_floor_review']:lines.append('No se pudieron comprobar los correlativos actuales. Debes revisar los últimos números utilizados.')
    return '\n\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description='Revisar y restaurar respaldos con Aula cerrado.')
    parser.add_argument('--data-dir',default=str(Path(__file__).resolve().parent.parent/'data'));parser.add_argument('--backup')
    args=parser.parse_args()
    try:
        if not args.backup:
            import tkinter as tk
            from tkinter.filedialog import askopenfilename
            root=tk.Tk();root.withdraw()
            try:args.backup=askopenfilename(title='Selecciona el respaldo de Aula',filetypes=[('Respaldo de Aula','*.sqlite3 *.aulabak')])
            finally:root.destroy()
            if not args.backup:return
        credential=None;kind='password'
        with open(args.backup,'rb') as saved:encrypted=saved.read(8).startswith(b'AULABK')
        if encrypted:
            from getpass import getpass
            kind='recovery' if input('¿Usar clave de recuperación? Escribe SI, o pulsa Enter para contraseña: ').strip().upper()=='SI' else 'password'
            credential=getpass('Clave de recuperación: ' if kind=='recovery' else 'Contraseña del respaldo: ')
        review=preview_restore(args.backup,args.data_dir,credential=credential,credential_kind=kind);print(review_text(review))
        floors=None
        if review['requires_floor_review']:
            floors={t:int(input(f'Último número usado de {t} (mínimo {review["floors"][t]}): ')) for t in SEQUENCES}
        answer=input('Escribe '+review['confirmation']+' para continuar: ').strip()
        if answer!=review['confirmation']:print('Restauración cancelada.');return
        restore(args.backup,args.data_dir,preview_hash=review['preview_hash'],confirmation=answer,emergency_floors=floors,credential=credential,credential_kind=kind)
        result=last_restore(args.data_dir)
        print('Restauración completa. Informes: '+(', '.join(result['reports']) or 'No hubo diferencias que perder.'))
    except (ValueError,RuntimeError,sqlite3.Error,OSError) as error: raise SystemExit(str(error))


if __name__=='__main__': main()
