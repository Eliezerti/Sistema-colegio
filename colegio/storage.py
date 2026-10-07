"""Exclusive process ownership and consistent local backups on Windows/Linux."""
import os
import json
import shutil
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime
from pathlib import Path


class DataLock:
    def __init__(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.file = (directory / '.aula.lock').open('a+b')
        try:
            # Reading byte 0 of an already locked Windows file raises before
            # msvcrt.locking. Use its size instead, and always close on failure.
            if not os.fstat(self.file.fileno()).st_size:
                self.file.write(b'0')
                self.file.flush()
            self.file.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise RuntimeError('El sistema está abierto con estos datos. Cierra Aula antes de continuar.')

    def close(self):
        if not self.file.closed:
            self.file.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
            self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def consistent_backup(source, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix='.aula-backup-',suffix='.tmp',dir=destination.parent)
    os.close(handle)
    try:
        with closing(sqlite3.connect(Path(source).resolve().as_uri()+'?mode=ro',uri=True)) as src, closing(sqlite3.connect(temporary)) as dst:
            src.backup(dst)
            dst.execute('PRAGMA journal_mode=DELETE')
            dst.execute('PRAGMA synchronous=FULL')
            with dst:
                dst.execute('DELETE FROM sessions')
            if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('El respaldo no superó la verificación de integridad.')
        # Windows _commit (used by os.fsync) requires a writable descriptor.
        with open(temporary,'r+b') as saved:
            saved.flush()
            os.fsync(saved.fileno())
        os.replace(temporary,destination)
    finally:
        if Path(temporary).exists(): Path(temporary).unlink()


def daily_backup(database):
    database = Path(database)
    directory = database.parent / 'backups'
    path = directory / f"colegio-{datetime.now():%Y-%m-%d}.sqlite3"
    if not path.exists():
        consistent_backup(database, path)
    backups = sorted(directory.glob('colegio-????-??-??.sqlite3'))
    for old in backups[:-30]:
        old.unlink()


def backup_status(database):
    database=Path(database)
    try: status=json.loads((database.parent/'backup-status.json').read_text())
    except (OSError,ValueError): status={}
    status['data_path']=str(database.resolve())
    return status


def automatic_backup(database):
    """Copy only a verified snapshot to an optional second folder, never the live WAL database."""
    database=Path(database)
    directory=database.parent/'backups'
    now=datetime.now().astimezone().isoformat()
    path=directory/f'aula-auto-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite3'
    status=backup_status(database)
    try:
        consistent_backup(database,path)
        status.update(local_at=now,local_path=str(path),local_error='')
        for old in sorted(directory.glob('aula-auto-????????-??????-??????.sqlite3'))[:-90]: old.unlink()
    except Exception as error:
        status['local_error']=f'No se pudo guardar el respaldo local: {type(error).__name__}.'
    with closing(sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        r=db.execute("SELECT value FROM settings WHERE key='backup_directory'").fetchone()
        secondary=r[0] if r else ''
    if status.get('secondary_directory')!=secondary:
        status.pop('secondary_at',None);status.pop('secondary_error',None)
    status['secondary_directory']=secondary
    if secondary and not status.get('local_error'):
        handle=None; temporary=None
        try:
            dest=Path(secondary); dest.mkdir(parents=True,exist_ok=True)
            handle,temporary=tempfile.mkstemp(prefix='.aula-copy-',suffix='.tmp',dir=dest)
            os.close(handle); handle=None
            shutil.copyfile(path,temporary)
            with open(temporary,'r+b') as saved:
                saved.flush()
                os.fsync(saved.fileno())
            os.replace(temporary,dest/path.name)
            status.update(secondary_at=now,secondary_error='')
            for old in sorted(dest.glob('aula-auto-????????-??????-??????.sqlite3'))[:-90]: old.unlink()
        except Exception as error:
            status['secondary_error']=f'No se pudo copiar al segundo destino: {type(error).__name__}. Revisa la carpeta o conecta el USB.'
        finally:
            if temporary and Path(temporary).exists(): Path(temporary).unlink()
    elif not secondary:
        for key in ('secondary_at','secondary_error'): status.pop(key,None)
    target=database.parent/'backup-status.json'; temporary=target.with_suffix('.tmp')
    temporary.write_text(json.dumps(status,ensure_ascii=False),encoding='utf-8')
    os.replace(temporary,target)
    return status
