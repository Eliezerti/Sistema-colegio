"""Durable, replayable restoration intent. Pending/illegible intent blocks every startup."""
import getpass
import json
import os
import re
import shutil
import sqlite3
from pathlib import Path

from .backup_inspection import file_hash, fingerprint, probe_backup
from .clock_guard import atomic_json, sync_directory

PENDING='.restore-pending.json'
HISTORY='restauraciones.json'


class RecoveryRequired(RuntimeError):
    pass


def sync_file(path):
    with open(path,'r+b') as saved:
        saved.flush();os.fsync(saved.fileno())


def durable_copy(source,destination):
    shutil.copyfile(source,destination);sync_file(destination)


def store_pending(directory,operation):
    atomic_json(Path(directory)/PENDING,{'version':1,'operation':operation,'sha256':fingerprint(operation)})


def fail_closed():
    return RecoveryRequired('Hay una restauración pendiente que no se pudo comprobar. Aula no abrió la base ni generó mensualidades. '
        'Conserva la carpeta de datos y todos sus respaldos. No borres .restore-pending.json, WAL ni SHM. '
        'Solicita ayuda técnica para revisar el registro y la copia antes-restauracion.')


def checked_path(directory,relative):
    if not isinstance(relative,str) or not relative.startswith('backups/') or '\\' in relative:
        raise fail_closed()
    path=(Path(directory)/relative).resolve()
    if Path(directory).resolve() not in path.parents or path.is_symlink(): raise fail_closed()
    return path


def read_pending(directory):
    path=Path(directory)/PENDING
    if not path.exists(): return None
    try:
        value=json.loads(path.read_text(encoding='utf-8'))
        op=value['operation']
        if value['version']!=1 or fingerprint(op)!=value['sha256'] or not re.fullmatch('[a-f0-9]{32}',op['id']): raise ValueError()
        if op['phase'] not in ('prepared','published','completed'): raise ValueError()
        for key in ('candidate','candidate_hash','raw','raw_hashes','previous','previous_hash','event','reports'):
            if key not in op: raise ValueError()
        candidate=checked_path(directory,op['candidate'])
        if file_hash(candidate)!=op['candidate_hash']: raise ValueError()
        probe_backup(candidate)
        if op['previous']:
            previous=checked_path(directory,op['previous'])
            if file_hash(previous)!=op['previous_hash']: raise ValueError()
            probe_backup(previous)
        raw=checked_path(directory,op['raw'])
        for name,digest in op['raw_hashes'].items():
            if name not in ('colegio.sqlite3','colegio.sqlite3-wal','colegio.sqlite3-shm','colegio.sqlite3-journal'): raise ValueError()
            if file_hash(raw/name)!=digest: raise ValueError()
        for relative,digest in op['reports'].items():
            if file_hash(checked_path(directory,relative))!=digest: raise ValueError()
        if op['event']['operation_id']!=op['id']: raise ValueError()
        return op
    except (OSError,ValueError,TypeError,KeyError,AttributeError,sqlite3.Error):
        raise fail_closed() from None


def record_external(directory,event):
    path=Path(directory)/HISTORY
    try:
        history=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
        if not isinstance(history,list) or any(not isinstance(r,dict) for r in history): raise ValueError()
        existing=next((r for r in history if r.get('operation_id')==event['operation_id']),None)
        if existing and existing!=event: raise ValueError()
    except (OSError,ValueError,TypeError): raise fail_closed() from None
    if not existing: atomic_json(path,[*history,event])


def checkpoint(stage):
    """Named boundaries intercepted only by the child-process tests; no environment bypass."""
    pass


def finish_pending(directory):
    """Caller owns DataLock. Replay only a previously confirmed and fully preserved intent."""
    directory=Path(directory).resolve();op=read_pending(directory)
    if op is None: return None
    target=directory/'colegio.sqlite3'
    candidate=checked_path(directory,op['candidate'])
    if op['phase']=='prepared':
        replacement=directory/('.restore-replacement-'+op['id']+'.tmp')
        durable_copy(candidate,replacement)
        checkpoint('before_sidecars')
        for suffix in ('-wal','-shm','-journal'):
            target.with_name(target.name+suffix).unlink(missing_ok=True)
        sync_directory(directory)
        checkpoint('after_sidecars')
        os.replace(replacement,target)
        sync_directory(directory)
        checkpoint('after_replace')
        op['phase']='published';store_pending(directory,op)
    if file_hash(target)!=op['candidate_hash']: raise fail_closed()
    probe_backup(target)
    record_external(directory,op['event'])
    op['phase']='completed';store_pending(directory,op)
    checkpoint('after_commit')
    (directory/PENDING).unlink();sync_directory(directory)
    return op['event']


def windows_actor():
    # Offline operation, not an authenticated Aula administrator session.
    return {'kind':'cuenta del sistema operativo','name':getpass.getuser()}
