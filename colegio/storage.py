"""Exclusive process ownership and consistent local backups on Windows/Linux."""
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path


class DataLock:
    def __init__(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.file = (directory / '.aula.lock').open('a+b')
        self.file.seek(0)
        if not self.file.read(1):
            self.file.write(b'0')
            self.file.flush()
        self.file.seek(0)
        try:
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
    with closing(sqlite3.connect(source)) as src, closing(sqlite3.connect(destination)) as dst:
        src.backup(dst)
        dst.execute('PRAGMA journal_mode=DELETE')
        with dst:
            dst.execute('DELETE FROM sessions')
        if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('El respaldo no superó la verificación de integridad.')


def daily_backup(database):
    database = Path(database)
    directory = database.parent / 'backups'
    path = directory / f"colegio-{datetime.now():%Y-%m-%d}.sqlite3"
    if not path.exists():
        consistent_backup(database, path)
    backups = sorted(directory.glob('colegio-????-??-??.sqlite3'))
    for old in backups[:-30]:
        old.unlink()
