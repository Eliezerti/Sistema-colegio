"""One-use local recovery without relaxing the HTTP password throttle."""
import hashlib
import json
import secrets
import time
from contextlib import closing
from pathlib import Path

from .db import connect, check_password, audit, ValidationError
from .audit_chain import require

INSTANCE = '.login-instance.json'
GRANT = '.login-unlock.json'


def private_json(path, value):
    from .clock_guard import atomic_json
    atomic_json(path, value)


def begin_instance(directory):
    directory = Path(directory)
    (directory / GRANT).unlink(missing_ok=True)
    identifier = secrets.token_hex(32)
    private_json(directory / INSTANCE, {'id': identifier})
    return identifier


def issue(directory, username, password):
    directory = Path(directory)
    username = username.strip().lower()
    try:
        identifier = json.loads((directory / INSTANCE).read_text())['id']
    except (OSError, ValueError, KeyError, TypeError):
        raise ValidationError('Abre Aula en esta PC antes de generar el código.') from None
    # Never initialize/create a database through the recovery tool.
    path = directory / 'colegio.sqlite3'
    if not path.is_file():
        raise ValidationError('No se encuentra la base local de Aula.')
    with closing(connect(path)) as db, db:
        user = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        if not user or user['role'] != 'admin' or not check_password(password, user['password']):
            raise ValidationError('Usuario o contraseña de Administración incorrectos.')
        require(db)
        audit(db, user['id'], 'local_login_unlock_issued', {'username': username, 'valid_seconds': 120})
    code = secrets.token_hex(16)
    private_json(directory / GRANT, {'instance': identifier, 'username': username,
        'digest': hashlib.sha256(code.encode()).hexdigest(), 'issued': time.monotonic()})
    return code


def consume(directory, identifier, username, code):
    if not isinstance(code, str) or len(code) != 32:
        return False
    path = Path(directory) / GRANT
    try:
        grant = json.loads(path.read_text())
        age = time.monotonic() - grant['issued']
        valid = (grant['instance'] == identifier and grant['username'] == username and 0 <= age <= 120
            and secrets.compare_digest(grant['digest'], hashlib.sha256(code.encode()).hexdigest()))
        if valid:
            path.unlink()
        return valid
    except (OSError, ValueError, KeyError, TypeError):
        return False


def main():
    import argparse
    import getpass
    parser = argparse.ArgumentParser(description='Código local de acceso de Aula, válido por dos minutos.')
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--username', required=True)
    args = parser.parse_args()
    print(issue(args.data_dir, args.username, getpass.getpass('Contraseña actual: ')))


if __name__ == '__main__':
    main()
