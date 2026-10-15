"""Actual installed executables; run only on a disposable GitHub Windows runner."""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# This verifier is also launched directly as python tests/windows_upgrade.py.
sys.path.insert(0, str(ROOT))
from tests.zero_install import assert_empty_database
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
FINANCIAL_TABLES = ('students', 'guardians', 'grades', 'charges', 'payments', 'allocations', 'enrollment_documents')


def execute(program, *arguments):
    subprocess.run([str(program), *arguments], check=True, timeout=150)


def registered_uninstaller(directory):
    """Inno may allocate a different uninsNNN name when upgrading across versions."""
    import winreg
    key = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{55F5F949-F16B-47B4-964A-D75AF4DF8DE2}_is1'
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_READ | view) as opened:
                command = winreg.QueryValueEx(opened, 'UninstallString')[0]
            path = Path(command.strip().strip('"'))
            if path.parent.resolve()!=directory.resolve() or not path.is_file():
                raise RuntimeError('El desinstalador registrado no corresponde a esta instalación de prueba.')
            return path
        except FileNotFoundError:
            continue
    raise RuntimeError('Windows no registró el desinstalador de la aplicación de prueba.')


def start_and_check(program, needs_setup):
    # Both real releases use the default port; no invented legacy CLI options.
    process = subprocess.Popen([str(program)])
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        deadline = time.monotonic()+75
        while time.monotonic()<deadline:
            if process.poll() is not None: raise RuntimeError('La aplicación terminó antes de abrir.')
            try:
                with opener.open('http://127.0.0.1:8765/api/session', timeout=1) as response:
                    data = json.load(response)
                if data['needs_setup'] != needs_setup: raise RuntimeError('La aplicación abrió otro estado de datos.')
                time.sleep(2)
                if process.poll() is not None: raise RuntimeError('La ventana terminó después de iniciar el servidor.')
                return data
            except OSError:
                time.sleep(.2)
        raise RuntimeError('No se pudo comprobar el inicio del ejecutable instalado.')
    finally:
        # Only the application process created by this test and its child WebViews.
        if process.poll() is None:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False)
            process.wait(timeout=15)


def financial_snapshot(path, columns=None):
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not list(db.execute('PRAGMA foreign_key_check'))
        if columns is None:
            columns = {table: [r[1] for r in db.execute(f'PRAGMA table_info({table})')]
                       for table in FINANCIAL_TABLES}
        records = {table: sorted([list(r) for r in db.execute(f'SELECT '+','.join(names)+f' FROM {table}')],
                                 key=lambda r:json.dumps(r)) for table, names in columns.items()}
        balance = db.execute('''SELECT (SELECT SUM(amount) FROM charges WHERE cancelled=0)-
                         (SELECT SUM(a.amount) FROM allocations a JOIN payments p ON p.id=a.payment_id WHERE p.voided=0)''').fetchone()[0]
        return {'columns': columns, 'records': records, 'balance': balance}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--version', required=True)
    parser.add_argument('--historical-dir', required=True); args = parser.parse_args()
    if os.name!='nt' or os.environ.get('GITHUB_ACTIONS')!='true':
        raise RuntimeError('Esta prueba requiere un runner Windows desechable, sin datos reales.')
    data = Path(os.environ['LOCALAPPDATA'])/'AulaColegio'
    if data.exists(): raise RuntimeError('La cuenta de prueba ya tiene datos; no se modificaron.')
    directory = Path(os.environ['RUNNER_TEMP'])/'Aula-B1-Actualizacion'
    program = directory/'Aula.exe'
    current = ROOT/'dist'/f'Aula-Colegio-Instalador-{args.version}.exe'
    historical = Path(args.historical_dir)/'Aula-Colegio-Instalador-1.0.13.exe'
    digest = hashlib.sha256(historical.read_bytes()).hexdigest()
    assert digest == '9714be7b6edaa03eab71a247c51219de6c425b5cd72d3b7fb7f1fbe23ab08d3c'
    assert digest in historical.with_name(historical.name+'.sha256').read_text(encoding='utf-8-sig')
    arguments = ('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',f'/DIR={directory}', '/TASKS=')
    try:
        execute(current, *arguments)
        assert not data.exists(), 'El instalador creó datos antes de abrir la aplicación.'
        session = start_and_check(program, True)
        assert session['school']['school_name'] == 'Mi colegio'
        database = data/'colegio.sqlite3'
        assert_empty_database(database)
        print('PASS CERO: base instalada sin registros, usuarios ni identidad; pisos cero y bitácora válida.',flush=True)
        before = hashlib.sha256(database.read_bytes()).hexdigest()
        execute(registered_uninstaller(directory),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
        assert hashlib.sha256(database.read_bytes()).hexdigest() == before
        print('PASS B1: instalación sin datos previos, inicio real y desinstalación conserva la base.', flush=True)
        shutil.rmtree(data)

        execute(historical, *arguments)
        data.mkdir(parents=True, exist_ok=True)
        fixture = ROOT/'tests/fixtures/restore/desktop-1.0.13.sqlite3'
        manifest = json.loads((fixture.parent/'manifest.json').read_text())
        expected = next(r for r in manifest if r['tag']=='desktop-1.0.13')
        assert hashlib.sha256(fixture.read_bytes()).hexdigest() == expected['sha256']
        shutil.copyfile(fixture, database)
        original = financial_snapshot(database)
        assert original['balance']==5000
        start_and_check(program, False)
        opened = financial_snapshot(database, original['columns'])
        # The real old version may fill a previously empty internal pupil code on startup.
        # Its committed financial rows/receipt must remain unchanged before taking the upgrade baseline.
        assert opened['balance']==original['balance']
        for table in ('charges','payments','allocations'):
            assert opened['records'][table]==original['records'][table]
        original = opened
        old_backup = data/'backups'/'b1-antes-actualizar.sqlite3'
        old_backup.parent.mkdir(exist_ok=True)
        with closing(sqlite3.connect(database)) as source, closing(sqlite3.connect(old_backup)) as target:
            source.backup(target)
        backup_hash = hashlib.sha256(old_backup.read_bytes()).hexdigest()
        # Upgrade monotonically: 1.0.13 -> 1.0.49 -> current. A historical
        # executable must never open the newer schema 12 as a downgrade test.
        previous = Path(os.environ['RUNNER_TEMP'])/'Aula-B2-Publicado'/'Aula-Colegio-Instalador-1.0.49.exe'
        assert hashlib.sha256(previous.read_bytes()).hexdigest() == '3d4846ab01e76a96c3e3dc738a1945dfde1aa0d3fb845173e7fc18cf3e0ead2b'
        execute(previous, *arguments)
        start_and_check(program, False)
        assert financial_snapshot(database, original['columns']) == original
        execute(current, *arguments)
        start_and_check(program, False)
        assert financial_snapshot(database, original['columns']) == original
        with closing(sqlite3.connect(database)) as db:
            assert db.execute('PRAGMA user_version').fetchone()[0]==12
        assert list((data/'backups').glob('antes-bitacora-*.sqlite3'))
        subprocess.run([sys.executable, str(ROOT/'packaging/bundle_inventory.py'), str(directory),
                        '--output', str(Path(os.environ['RUNNER_TEMP'])/'aula-b2-upgraded.json'), '--verify'], check=True)
        print('PASS B2: actualización real 1.0.49 → '+args.version+' conserva datos y retira recursos anteriores.', flush=True)
        execute(registered_uninstaller(directory),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
        assert financial_snapshot(database, original['columns']) == original
        assert hashlib.sha256(old_backup.read_bytes()).hexdigest() == backup_hash
        result = dict(historical='1.0.13', target=args.version, historical_sha256=digest,
                      balance_usd_cents=original['balance'], schema=12, data_preserved=True, backup_preserved=True)
        (Path(os.environ['RUNNER_TEMP'])/'aula-b1-upgrade.json').write_text(json.dumps(result, indent=2))
        print('PASS B1: actualización real 1.0.13 → '+args.version+', esquema 12, saldo USD 50 y filas/recibo/respaldo conservados.', flush=True)
    finally:
        if data.exists():
            diagnostic = Path(os.environ['RUNNER_TEMP'])/'aula-b1-diagnostic'
            if (data/'logs').exists(): shutil.copytree(data/'logs', diagnostic, dirs_exist_ok=True)
            shutil.rmtree(data)


if __name__=='__main__': main()
