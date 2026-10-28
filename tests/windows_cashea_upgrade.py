"""Real installed 1.0.73 -> 1.0.74 upgrade, fictional data on a disposable Windows runner."""
import argparse,hashlib,json,os,shutil,sqlite3,sys
from contextlib import closing
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests.windows_duplicate_upgrade import Client,running
from tests.windows_upgrade import execute,registered_uninstaller
from colegio.db import local_today


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--previous',required=True);parser.add_argument('--version',default='1.0.74');args=parser.parse_args()
    if os.name!='nt' or os.environ.get('GITHUB_ACTIONS')!='true':raise RuntimeError('Solo runner Windows desechable, sin datos existentes.')
    data=Path(os.environ['LOCALAPPDATA'])/'AulaColegio'
    if data.exists():raise RuntimeError('Ya hay datos de Aula; no se modificó nada.')
    folder=Path(os.environ['RUNNER_TEMP'])/'Aula-Actualizar-Cashea'
    arguments=('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',f'/DIR={folder}','/TASKS=')
    today=local_today();year=today.year if today.month>=9 else today.year-1
    password='FICTICIO-validacion-Cashea-2026'
    try:
        execute(Path(args.previous),*arguments)
        with running(folder/'Aula.exe') as client:
            assert client.request('session')['needs_setup']
            client.request('setup',dict(name='Administrador FICTICIO',username='admin',password=password))
            client.csrf=client.request('session')['user']['csrf'];client.request('confirm-rate',dict(rate_date=today.isoformat(),rate='100'))
            grade=client.request('grades',dict(name='Grado FICTICIO',capacity=30))['id']
            guardian=client.request('guardians',dict(name='Representante FICTICIO',document='V-FICTICIO'))['id']
            pupil=dict(name='Alumno FICTICIO',document='',birth_date='',guardian_id=guardian,grade_id=grade,school_year=year,
                monthly_fee='130',discount=0,status='active',billing_start=today.strftime('%Y-%m'),enrollment_start=f'{year}-09-01',enrollment_end=f'{year+1}-08-31')
            old_student=client.request('students',pupil)['id']
            target=client.request('students',dict(pupil,name='Alumno Cashea FICTICIO'))['id']
            receipt=client.request('payments',dict(student_id=old_student,amount='10',currency='USD',paid_on=today.isoformat(),method='Efectivo',request_key='cashea-upgrade-normal-old'))['id']
            before=client.request('state?history=1');original_pdf=client.request(f'receipt/{receipt}.pdf');cash=client.request('cash-preview')
        with closing(sqlite3.connect(data/'colegio.sqlite3')) as db:assert db.execute('PRAGMA user_version').fetchone()[0]==12
        execute(ROOT/'dist'/f'Aula-Colegio-Instalador-{args.version}.exe',*arguments)
        with running(folder/'Aula.exe') as client:
            client.request('login',dict(username='admin',password=password));client.csrf=client.request('session')['user']['csrf']
            client.request('confirm-rate',dict(rate_date=today.isoformat(),rate='100'))
            after=client.request('state?history=1')
            for key in ('students','guardians','grades','charges','payments','expenses','summary','enrollments'):assert before[key]==after[key],key
            assert original_pdf==client.request(f'receipt/{receipt}.pdf');assert cash==client.request('cash-preview')
            sale=dict(student_id=target,ordered_on=today.isoformat(),total='130',initial_percent='60',initial_received='78',initial_currency='USD',initial_method='Efectivo',invoice_number='FACTURA-FICTICIA-001',request_key='cashea-upgrade-sale-one')
            sale['preview_hash']=client.request('cashea-preview',sale)['preview_hash'];order=client.request('cashea-order',sale)
            assert order==client.request('cashea-order',sale)
            state=client.request('state?history=1');student=next(s for s in state['students'] if s['id']==target)
            assert student['balance']==student['overdue']==0
            assert client.request('cash-preview')['income_usd']==8800
            ca=client.request(f"cashea-order/{order['id']}.pdf");assert b'/MediaBox [0 0 396 612]' in ca
            (Path(os.environ['RUNNER_TEMP'])/'cashea-native-CA.pdf').write_bytes(ca)
            batch=dict(order_ids=[order['id']],received_on=today.isoformat(),currency='VES',amount='5200',reference='BANCO-FICTICIO-001',request_key='cashea-upgrade-settlement-one')
            batch['preview_hash']=client.request('cashea-settlement-preview',batch)['preview_hash'];cl=client.request('cashea-settlement',batch)
            assert cl['amount']==5200;assert client.request('cash-preview')['income_usd']==14000
            assert client.request('cashea')['pending']==0;assert client.request('maintenance-review')['ok']
            assert original_pdf==client.request(f'receipt/{receipt}.pdf')
        ledger=data/'colegio.sqlite3'
        with closing(sqlite3.connect(ledger)) as db:
            assert db.execute('PRAGMA user_version').fetchone()[0]==14
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not db.execute('PRAGMA foreign_key_check').fetchone()
        assert list((data/'backups').glob('antes-cashea-*.sqlite3'))
        digest=hashlib.sha256(ledger.read_bytes()).hexdigest()
        execute(registered_uninstaller(folder),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
        assert ledger.is_file() and hashlib.sha256(ledger.read_bytes()).hexdigest()==digest
        result=dict(previous='1.0.73',version=args.version,schema=14,old_receipt_unchanged=True,totals_preserved_before_cashea=True,
            initial_usd=7800,financed_usd=5200,received_ves=520000,settlement_usd=5200,student_balance=0,maintenance=True,uninstall_keeps_data=True)
        (Path(os.environ['RUNNER_TEMP'])/'cashea-upgrade.json').write_text(json.dumps(result,indent=2))
        print('PASS CASHEA WINDOWS: actualización real 1.0.73 → '+args.version+', datos y PDF histórico idénticos, CA/R/CL, VES, saldo y mora cero, integridad y desinstalación conservadora.',flush=True)
    finally:
        if data.exists():shutil.rmtree(data)


if __name__=='__main__':main()
