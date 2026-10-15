"""Run under the actual second Windows account with no originating key store."""
from contextlib import closing
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from colegio.backup_inspection import probe_backup
from colegio.restore import preview_restore,restore
from colegio.read_only import open_copy
from colegio.db import connect
from colegio.audit_chain import portable_status

root=Path(sys.argv[1]);metadata=json.loads((root/'credenciales-ficticias.json').read_text(encoding='utf-8'))
assert metadata['fictional'] is True
assert (root/'disposable-b1-only.txt').is_file()
source=root/'solo-archivo.aulabak'
for kind in ('password','recovery'):
    credential=metadata[kind]
    probe=probe_backup(source,credential,kind)
    assert probe['payments']==metadata['payments'] and probe['balance_usd']==metadata['pending']
    target=root/('restaurado-'+kind)
    review=preview_restore(source,target,credential=credential,credential_kind=kind)
    restored=restore(source,target,preview_hash=review['preview_hash'],confirmation=review['confirmation'],
        credential=credential,credential_kind=kind)
    with closing(connect(restored)) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchone()
        assert portable_status(db)['ok']
    with open_copy(source,credential,kind) as viewer:
        with closing(viewer.connect_view()) as db:assert db.execute('SELECT COUNT(*) FROM payments').fetchone()[0]==1
    assert not (target/'.backup-crypto').exists()
    print('PASS D7: solo archivo + '+kind+', Probar respaldo, restauración, consulta y cadena sin almacén de origen.',flush=True)
