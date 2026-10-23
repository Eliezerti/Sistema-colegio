"""Upgrade the real 1.0.71 installer; use only a fresh disposable Windows runner."""
import argparse
from contextlib import contextmanager
import http.cookiejar
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from colegio.db import local_today
from tests.windows_upgrade import execute, registered_uninstaller


class Client:
    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.csrf = ''

    def request(self, route, data=None):
        request = urllib.request.Request('http://127.0.0.1:8765/api/'+route,
            None if data is None else json.dumps(data).encode(),
            {'Content-Type':'application/json', 'X-CSRF-Token':self.csrf})
        with self.opener.open(request, timeout=30) as response:
            raw = response.read()
            return raw if 'application/pdf' in response.headers.get('Content-Type','') else json.loads(raw)


@contextmanager
def running(program):
    process = subprocess.Popen([str(program)])
    client = Client()
    try:
        deadline = time.monotonic()+75
        while True:
            if process.poll() is not None: raise RuntimeError('Aula terminó antes de abrir.')
            try:
                client.request('session'); break
            except OSError:
                if time.monotonic() >= deadline: raise
                time.sleep(.2)
        yield client
    finally:
        if process.poll() is None:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'], check=True,
                           stdout=subprocess.DEVNULL)
            process.wait(timeout=20)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--previous', required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    if os.name != 'nt' or os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Solo se permite en un runner Windows desechable.')
    data = Path(os.environ['LOCALAPPDATA'])/'AulaColegio'
    if data.exists(): raise RuntimeError('Ya hay datos; no se modificó nada.')
    folder = Path(os.environ['RUNNER_TEMP'])/'Aula-Actualizar-duplicados'
    current = ROOT/'dist'/f'Aula-Colegio-Instalador-{args.version}.exe'
    arguments = ('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',f'/DIR={folder}','/TASKS=')
    today = local_today()
    password = 'FICTICIO-duplicados-2026'
    try:
        execute(Path(args.previous), *arguments)
        with running(folder/'Aula.exe') as client:
            assert client.request('session')['needs_setup']
            client.request('setup', {'name':'Administración ficticia','username':'admin','password':password})
            client.csrf = client.request('session')['user']['csrf']
            client.request('confirm-rate', {'rate_date':today.isoformat(),'rate':'100'})
            grade = client.request('grades', {'name':'Grado ficticio','capacity':30})['id']
            guardian = client.request('guardians', {'name':'Representante ficticio','document':'V-FICTICIO'})['id']
            year = today.year if today.month >= 9 else today.year-1
            student = dict(name='Alumno correcto ficticio',document='AL-FICTICIO-A',birth_date='',
                guardian_id=guardian,grade_id=grade,school_year=year,monthly_fee='50',discount=0,
                status='active',billing_start=today.strftime('%Y-%m'),enrollment_start=f'{year}-09-01',
                enrollment_end=f'{year+1}-08-31')
            original = client.request('students',student)['id']
            receipt = client.request('payments',dict(student_id=original,amount='10',currency='USD',
                paid_on=today.isoformat(),method='Efectivo',request_key='upgrade-duplicate-one'))['id']
            duplicate = client.request('students',dict(student,name='Alumno duplicado ficticio',document='AL-FICTICIO-B'))['id']
            before = client.request('state?history=1')
            original_pdf = client.request(f'receipt/{receipt}.pdf')
            cash = client.request('cash-preview')
        execute(current, *arguments)
        with running(folder/'Aula.exe') as client:
            assert not client.request('session')['needs_setup']
            client.request('login', {'username':'admin','password':password})
            client.csrf = client.request('session')['user']['csrf']
            client.request('confirm-rate', {'rate_date':today.isoformat(),'rate':'100'})
            after = client.request('state?history=1')
            for key in ('students','guardians','grades','charges','payments','expenses','summary','enrollments'):
                assert before[key] == after[key], key
            preview = client.request(f'student-deletion-preview/{duplicate}')
            assert preview['can_delete'] and preview['balance'] > 0
            client.request('delete-error-student',dict(kind='student',id=duplicate,preview_hash=preview['preview_hash'],
                password=password,student_code_confirmation=preview['student_code'],confirmation='BORRAR FICHA',
                reason='Duplicado ficticio de validación Windows'))
            after = client.request('state?history=1')
            assert [s['id'] for s in after['students']] == [original]
            assert after['guardians'] == before['guardians']
            for key in ('payments','expenses'): assert after[key] == before[key]
            assert all(c['student_id'] != duplicate for c in after['charges'])
            assert client.request(f'receipt/{receipt}.pdf') == original_pdf
            assert client.request('cash-preview') == cash
            assert client.request('maintenance-review')['ok']
        import hashlib
        ledger = data/'colegio.sqlite3'
        saved_hash = hashlib.sha256(ledger.read_bytes()).hexdigest()
        execute(registered_uninstaller(folder),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
        assert hashlib.sha256(ledger.read_bytes()).hexdigest() == saved_hash
        print('PASS: instalación real 1.0.71, actualización, borrado HTTP en EXE instalado, ficha correcta/recibo/caja íntegros, Verificar datos y desinstalación conserva datos.',flush=True)
    finally:
        # Created by this verifier after checking that no data existed.
        if data.exists(): shutil.rmtree(data)


if __name__ == '__main__': main()
