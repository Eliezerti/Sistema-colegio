"""Offline administrator recovery; requires the application to be closed."""
import argparse
import getpass
from contextlib import closing
from pathlib import Path
from datetime import datetime

from .db import ValidationError, audit, connect, hash_password
from .storage import DataLock, consistent_backup


def list_administrators(directory):
    """Local OS access only; no public endpoint or password disclosure."""
    directory=Path(directory).resolve(); database=directory/'colegio.sqlite3'
    if not database.is_file(): raise ValidationError('No existe una base en esa carpeta. No se creará un sistema vacío.')
    with DataLock(directory),closing(connect(database)) as db:
        return [dict(r) for r in db.execute("SELECT username,name FROM users WHERE role='admin' ORDER BY name")]


def reset_password(directory,username,password):
    directory=Path(directory).resolve();database=directory/'colegio.sqlite3'
    if not database.is_file(): raise ValidationError('No existe la base en esa ruta. No se creará un sistema vacío.')
    hashed=hash_password(password)
    with DataLock(directory),closing(connect(database)) as db:
        user=db.execute("SELECT id FROM users WHERE username=? AND role='admin'",(username.strip().lower(),)).fetchone()
        if not user: raise ValidationError('No existe un administrador con ese usuario.')
        consistent_backup(database,directory/'backups'/f'recuperacion-clave-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite3')
        with db:
            db.execute('UPDATE users SET password=? WHERE id=?',(hashed,user['id']))
            db.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
            audit(db,None,'local-admin-password-reset',{'user_id':user['id']})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',required=True);parser.add_argument('--username')
    args=parser.parse_args()
    try:
        print('Administradores de esta base:')
        for user in list_administrators(args.data_dir): print(f"  {user['username']} · {user['name']}")
        username=args.username or input('Usuario del administrador: ').strip()
        password=getpass.getpass('Nueva contraseña (mínimo 10 caracteres): ')
        if password!=getpass.getpass('Repite la contraseña: '): raise ValidationError('Las contraseñas no coinciden.')
        reset_password(args.data_dir,username,password)
        print('Contraseña restablecida. Puedes abrir Aula e iniciar sesión.')
    except (ValueError,RuntimeError,OSError) as error: raise SystemExit(str(error))


if __name__=='__main__': main()
