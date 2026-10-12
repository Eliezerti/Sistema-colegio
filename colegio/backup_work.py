"""Owned temporary jobs, cleaned on next locked startup after process termination."""
import json
import re
import secrets
import shutil
from contextlib import contextmanager
from pathlib import Path

from .clock_guard import atomic_json


def clean_job(job):
    if job.is_symlink() or not re.fullmatch('job-[a-f0-9]{32}',job.name):return
    try:
        marker=json.loads((job/'owner.json').read_text())
        if marker['version']!=1 or marker['purpose']!='Aula encrypted backup temporary' or marker['id']!=job.name[4:]:return
        destination=Path(marker['destination'])
        if not destination.is_absolute():return
    except (OSError,ValueError,KeyError,TypeError):return # Unknown files never authorize deletion.
    # Published .aulabak, original SQLite and A1 preservation files are never matched.
    remote_clean=True
    try:
        if not destination.is_dir():remote_clean=False
        for path in destination.glob('.aula-cipher-'+marker['id']+'-*.tmp'):
            if path.is_symlink() or not path.is_file():continue
            with path.open('rb') as source:prefix=source.read(8)
            if not prefix or prefix==b'AULABK01':path.unlink()
    except OSError:remote_clean=False # An unplugged USB cannot prevent working locally.
    finally:
        # Plaintext resides only here, under the owner's data permissions.
        if remote_clean:shutil.rmtree(job)
        else:
            for child in job.iterdir():
                if child.name=='owner.json':continue
                if child.is_dir() and not child.is_symlink():shutil.rmtree(child)
                else:child.unlink()


def cleanup_work(directory):
    """Caller holds main DataLock at startup; no live job for these data can exist."""
    root=Path(directory)/'.backup-crypto'/'work'
    if root.is_dir() and not root.is_symlink():
        for job in root.glob('job-*'):
            if job.is_dir():clean_job(job)


@contextmanager
def job_space(directory,destination):
    root=Path(directory)/'.backup-crypto'/'work'
    if root.is_symlink() or (hasattr(root,'is_junction') and root.is_junction()):
        raise ValueError('Los temporales de respaldo no pueden estar enlazados a otra carpeta.')
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    identifier=secrets.token_hex(16);job=root/('job-'+identifier);job.mkdir(mode=0o700)
    atomic_json(job/'owner.json',{'version':1,'purpose':'Aula encrypted backup temporary','id':identifier,
                                'destination':str(Path(destination).resolve())})
    try:yield job,identifier
    finally:clean_job(job)
