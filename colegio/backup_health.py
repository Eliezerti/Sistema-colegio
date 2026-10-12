"""Read-only backup warnings; never create, remove or restore a backup."""
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path


def describe_backup(database, status, *, now=None, disk_relation=None):
    result = dict(status)
    now = now or datetime.now(timezone.utc)
    alerts = []
    try:
        with closing(sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)) as db:
            row = db.execute("SELECT value FROM settings WHERE key='backup_directory'").fetchone()
        directory = row[0] if row else ''
    except sqlite3.Error:
        directory = None
        alerts.append({'code': 'configuration_unknown', 'message':
            'No se pudo comprobar la segunda carpeta de respaldos. Pide al administrador que la revise.'})
    # A timestamp belonging to the old destination does not validate a new one.
    if directory is not None and directory != result.get('secondary_directory', ''):
        result.pop('secondary_at', None)
        result.pop('secondary_error', None)
    result['secondary_directory'] = directory or ''
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
        elif relation.get('status') != 'different':
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
