"""Verified encrypted publication; external temporaries contain ciphertext only."""
import hashlib
import os
import tempfile
from pathlib import Path

from .backup_crypto import encrypt,verify_generated,CryptoError
from .backup_keys import reserve
from .backup_inspection import staged_backup,inspect_copy
from .clock_guard import sync_directory
from .backup_work import job_space


def checkpoint(stage):
    """Intercepted only by process-kill tests; no runtime or environment bypass."""
    pass


def write_encrypted(source,destination,directory):
    destination=Path(destination)
    state,nonces=reserve(directory)
    with job_space(directory,destination.parent) as (work,identifier),staged_backup(source,temporary_root=work) as (snapshot,_,digest):
        encoded,keys=encrypt(snapshot.read_bytes(),state,nonces)
        destination.parent.mkdir(parents=True,exist_ok=True)
        handle,name=tempfile.mkstemp(prefix='.aula-cipher-'+identifier+'-',suffix='.tmp',dir=destination.parent)
        try:
            with os.fdopen(handle,'wb') as saved:
                middle=len(encoded)//2
                saved.write(encoded[:middle]);saved.flush();os.fsync(saved.fileno())
                checkpoint('mid_cipher_write')
                saved.write(encoded[middle:]);saved.flush();os.fsync(saved.fileno())
            checkpoint('after_cipher_write')
            with tempfile.TemporaryDirectory(prefix='aula-verificar-cifrado-',dir=work) as local:
                plaintext=verify_generated(Path(name).read_bytes(),keys)
                if hashlib.sha256(plaintext).hexdigest()!=digest:
                    raise CryptoError('La copia descifrada no coincide con la original. No se publicó el respaldo.')
                restored=Path(local)/'verificacion.sqlite3';restored.write_bytes(plaintext)
                checkpoint('during_verify')
                inspect_copy(restored)
            checkpoint('before_publish')
            if destination.exists():raise CryptoError('Ya existe una copia con ese nombre. No se reemplazó el archivo anterior.')
            os.replace(name,destination);sync_directory(destination.parent)
            checkpoint('after_publish')
            return {'path':str(destination),'encrypted':True,'verified':True,'key_id':state['id'],
                    'sha256':hashlib.sha256(encoded).hexdigest()}
        finally:
            Path(name).unlink(missing_ok=True)
