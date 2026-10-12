"""Read-only backup warnings; never create, remove or restore a backup."""
import json
import socket
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .db import ValidationError, audit

CLOUD_KEY = 'backup_cloud_declaration'


def cloud_declaration(value, directory):
    """A manual destination classification, never evidence of a cloud upload."""
    try:
        declaration = json.loads(value or '{}')
        if (isinstance(declaration, dict) and directory and declaration.get('directory') == directory
                and declaration.get('computer') == socket.gethostname()):
            user_id = declaration.get('confirmed_by')
            timestamp = datetime.fromisoformat(declaration.get('confirmed_at', ''))
            if type(user_id) is int and user_id > 0 and timestamp.tzinfo is not None:
                return declaration
    except (TypeError, ValueError):
        pass
    return {}


def declare_cloud_destination(db, user, data, status):
    if user['role'] != 'admin':
        raise PermissionError('Solo administración puede declarar el destino de las copias.')
    directory = status.get('secondary_directory', '')
    if not directory or data.get('directory') != directory:
        raise ValidationError('La carpeta de respaldo cambió. Revisa Configuración y vuelve a intentarlo.')
    if data.get('declared') is False:
        declaration = {}
    else:
        if data.get('reviewed') is not True:
            raise ValidationError('Confirma que revisaste la copia en la nube y su sincronización.')
        codes = {entry['code'] for entry in status.get('alerts', [])}
        if codes & {'secondary_unconfirmed', 'secondary_stale', 'secondary_failed', 'configuration_unknown'}:
            raise ValidationError('Crea una copia reciente en esta carpeta y verifica su subida antes de confirmar.')
        declaration = {'directory': directory, 'computer': socket.gethostname(), 'confirmed_by': user['id'],
                       'confirmed_at': datetime.now(timezone.utc).isoformat()}
    previous = db.execute('SELECT value FROM settings WHERE key=?', (CLOUD_KEY,)).fetchone()
    before = cloud_declaration(previous[0] if previous else '', directory)
    if declaration:
        db.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                   (CLOUD_KEY, json.dumps(declaration, ensure_ascii=False)))
    else:
        db.execute('DELETE FROM settings WHERE key=?', (CLOUD_KEY,))
    audit(db, user['id'], 'backup_cloud_declaration', {'before': before, 'after': declaration,
                                                   'upload_checked_by_aula': False})
    return {'saved': True}


def describe_backup(database, status, *, now=None, disk_relation=None):
    result = dict(status)
    now = now or datetime.now(timezone.utc)
    alerts = []
    try:
        with closing(sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)) as db:
            settings = dict(db.execute('SELECT key,value FROM settings WHERE key IN (?,?)',
                                       ('backup_directory', CLOUD_KEY)))
        directory = settings.get('backup_directory', '')
    except sqlite3.Error:
        directory = None
        settings = {}
        alerts.append({'code': 'configuration_unknown', 'message':
            'No se pudo comprobar la segunda carpeta de respaldos. Pide al administrador que la revise.'})
    # A timestamp belonging to the old destination does not validate a new one.
    if directory is not None and directory != result.get('secondary_directory', ''):
        result.pop('secondary_at', None)
        result.pop('secondary_error', None)
        for key in ('secondary_encrypted','secondary_path','secondary_sha256','secondary_key_id'):result.pop(key,None)
    result['secondary_directory'] = directory or ''
    declaration = cloud_declaration(settings.get(CLOUD_KEY), directory)
    result['cloud_declared'] = bool(declaration)
    result['cloud_declaration'] = declaration
    for key, code, prefix in (('local_error', 'local_failed', 'Falló el último respaldo local.'),
                              ('secondary_error', 'secondary_failed', 'Falló la última copia al segundo destino.'),
                              ('retention_error', 'retention_failed', 'Revisa la conservación de respaldos.'),
                              ('secondary_retention_error', 'secondary_retention_failed', 'Revisa la conservación de copias en el segundo destino.')):
        if result.get(key):
            alerts.append({'code': code, 'message': prefix + ' ' + str(result[key])})
    if directory == '':
        alerts.append({'code': 'secondary_missing', 'message':
            'No hay una segunda carpeta de respaldos configurada. Las copias de este disco también pueden perderse si el disco falla.'})
    elif directory:
        relation = disk_relation or {'status': 'unknown'}
        if relation.get('status') == 'same':
            alerts.append({'code': 'same_disk', 'message':
                'La segunda carpeta está en el mismo disco que la base. Esta copia no protege si ese disco falla. Usa otro dispositivo o verifica la sincronización en la aplicación de nube.'})
        elif relation.get('status') != 'different' and not declaration:
            alerts.append({'code': 'disk_unknown', 'message':
                'No se pudo comprobar si la segunda carpeta está en otro disco. Una carpeta distinta puede estar en el mismo disco; pide al administrador que lo revise.'})
        try:
            external = datetime.fromisoformat(result.get('secondary_at', ''))
            if external.tzinfo is None or external > now:
                raise ValueError('Unconfirmed timestamp')
        except (ValueError, TypeError):
            alerts.append({'code': 'secondary_unconfirmed', 'message':
                'No hay una copia escrita y confirmada en la segunda carpeta. Revisa el destino y crea un respaldo ahora.'})
        else:
            if now - external > timedelta(days=3):
                alerts.append({'code': 'secondary_stale', 'message':
                    'La última copia escrita en la segunda carpeta tiene más de 3 días. Revisa el USB o la carpeta y crea un respaldo ahora.'})
    result['alerts'] = alerts
    result['checked_at'] = now.isoformat()
    return result
