"""Encrypted daily/monthly retention and permanent school-year preservation."""
import hashlib
import os
from pathlib import Path
import secrets
import shutil
import tempfile

from .backup_crypto import MAGIC
from .backup_retention import retain_backups
from .db import local_today


def copy_cipher(source, destination):
    source,destination=Path(source),Path(destination)
    with source.open('rb') as saved:
        if saved.read(len(MAGIC)) != MAGIC:
            raise ValueError('Los niveles del segundo destino requieren una copia cifrada de Aula.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    handle,name=tempfile.mkstemp(prefix='.aula-nivel-',suffix='.tmp',dir=destination.parent)
    os.close(handle)
    try:
        shutil.copyfile(source,name)
        def digest(path):
            with Path(path).open('rb') as saved:return hashlib.file_digest(saved,'sha256').digest()
        if digest(source)!=digest(name):raise OSError('La copia por niveles no coincide con el respaldo verificado.')
        with open(name,'r+b') as saved:saved.flush();os.fsync(saved.fileno())
        os.replace(name,destination)
    finally:Path(name).unlink(missing_ok=True)
    return destination


def retain_levels(source, directory, *, today=None):
    directory=Path(directory);today=today or local_today()
    paths=[]
    for label,stamp,pattern,limit in (
        ('diario',today.isoformat(),'aula-diario-????-??-??.aulabak',60),
        ('mensual',today.strftime('%Y-%m'),'aula-mensual-????-??.aulabak',24)):
        path=directory/f'aula-{label}-{stamp}.aulabak'
        created=not path.exists()
        if created:copy_cipher(source,path)
        retain_backups(directory,path,pattern,limit,created=created)
        paths.append(str(path))
    return paths


def preserve_year(database, source_year):
    """Verified snapshot immediately before a reviewed year transition; never rotated."""
    from contextlib import closing
    from .db import connect
    from .storage import consistent_backup
    from .backup_export import write_encrypted
    database=Path(database)
    name=f'aula-cierre-{source_year}-{source_year+1}-{secrets.token_hex(8)}.aulabak'
    directory=database.parent/'backups'/'cierres-permanentes'
    directory.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='aula-cierre-',dir=database.parent) as temp:
        plain=Path(temp)/'cierre.sqlite3';consistent_backup(database,plain)
        result=write_encrypted(plain,directory/name,database.parent)
    with closing(connect(database)) as db:
        row=db.execute("SELECT value FROM settings WHERE key='backup_directory'").fetchone()
    if row and row[0]:copy_cipher(result['path'],Path(row[0])/'cierres-permanentes'/name)
    return result['path']
