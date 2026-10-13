"""Child verifier launched under a real standard Windows user, not patched environment paths."""
import argparse
import json
import os
import subprocess
import urllib.request
from pathlib import Path

from windows_upgrade import start_and_check, execute


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--root', required=True)
    parser.add_argument('--expected-sid', required=True); args=parser.parse_args()
    root=Path(args.root)
    if os.name!='nt' or not (root/'disposable-b1-only.txt').exists():
        raise RuntimeError('No se autorizó el área ficticia de prueba.')
    sid=subprocess.check_output(['powershell.exe','-NoProfile','-Command',
        '[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value'],text=True).strip()
    assert sid==args.expected_sid, 'No se ejecutó con la nueva identidad de Windows.'
    data=Path(os.environ['LOCALAPPDATA'])/'AulaColegio'
    assert not data.exists(), 'La segunda cuenta ya tiene datos.'
    directory=Path(os.environ['LOCALAPPDATA'])/'Programs'/'AulaB1'
    execute(root/'installer.exe','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',f'/DIR={directory}','/TASKS=')
    assert (directory/'Aula.exe').exists()
    assert not data.exists()
    session=start_and_check(directory/'Aula.exe', True)
    assert session['school']['school_name']=='Mi colegio'
    assert (data/'colegio.sqlite3').exists()
    import hashlib
    digest=hashlib.sha256((data/'colegio.sqlite3').read_bytes()).hexdigest()
    execute(directory/'unins000.exe','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
    assert hashlib.sha256((data/'colegio.sqlite3').read_bytes()).hexdigest()==digest
    (root/'other-account-result.json').write_text(json.dumps(dict(sid=sid,localappdata=str(data.parent),
        data_path=str(data),installed_as_standard_user=True,first_start=True,uninstall_preserved_data=True),indent=2))


if __name__=='__main__': main()
