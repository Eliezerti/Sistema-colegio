"""Fictional credentials for isolated tests only. No production bypasses."""
from colegio.backup_keys import prepare,confirm

PASSWORD='FICTICIO-respaldo-seguro-2026'


def configure(directory,password=PASSWORD):
    pending,recovery=prepare(directory,password);confirm(directory,pending)
    return recovery
