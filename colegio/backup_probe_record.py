"""A successful external-copy test is declared explicitly, never inferred as cloud upload."""
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
from .clock_guard import atomic_json

FILE='external-backup-test.json'


def record(database, digest):
    atomic_json(Path(database).parent/FILE,{'version':1,'tested_at':datetime.now(timezone.utc).isoformat(),
        'sha256':digest,'external_declared':True})


def reminder(database, *, now=None):
    now=now or datetime.now(timezone.utc)
    try:
        data=json.loads((Path(database).parent/FILE).read_text())
        tested=datetime.fromisoformat(data['tested_at'])
        if data['version']!=1 or data.get('external_declared') is not True or tested.tzinfo is None:
            raise ValueError()
        days=(now-tested).total_seconds()/86400
        due=days>35 or days<0
        return {'due':due,'tested_at':tested.isoformat(),'message':
            'Hace más de 35 días que no pruebas una copia externa. Usa Probar respaldo con una copia del USB o la nube.' if due else ''}
    except (OSError,ValueError,KeyError,TypeError):
        return {'due':True,'tested_at':None,'message':'Recuerda probar una copia externa del USB o la nube con Probar respaldo.'}
