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
            sale=dict(student_id=target,ordered_on=today.isoformat(),total='130',initial_percent='60',initial_received='78',initial_currency='USD',initial_method='Efectivo',request_key='cashea-upgrade-sale-one')
            sale['preview_hash']=client.request('cashea-preview',sale)['preview_hash'];order=client.request('cashea-order',sale)
            assert order==client.request('cashea-order',sale)
            assert order['invoice_number']==f"R-{order['payment_id']:06d}" and order['invoice_origin']=='recibo'
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
            ves=dict(sale,student_id=old_student,total='40',initial_percent='40',initial_received='1600',initial_currency='VES',initial_method='Pago móvil',request_key='cashea-native-ves-initial')
            ves['preview_hash']=client.request('cashea-preview',ves)['preview_hash'];native=client.request('cashea-order',ves)
            actual=client.request(f"receipt/{native['payment_id']}")['payment']
            assert (actual['currency'],actual['received_amount'],actual['exchange_rate'],actual['amount'])==('VES',160000,'100',1600)
            assert native['invoice_number']==f"R-{native['payment_id']:06d}"
            assert client.request('maintenance-review')['ok']
            # Exercise the new module from the INSTALLED executable, not the checkout.
            advance_student=client.request('students',dict(pupil,name='Alumno anticipo FICTICIO',monthly_fee='40'))['id']
            client.request('payments',dict(student_id=advance_student,paid_on=today.isoformat(),
                amount='40',currency='USD',method='Efectivo',request_key='native-advance-current'))
            options=client.request(f'payment-options?student_id={advance_student}')
            assert not options['pending'] and options['future'],'Debe ofrecer próximos meses del ciclo vigente.'
            future=options['future'][0]
            advance=dict(student_id=advance_student,paid_on=today.isoformat(),amount='40',currency='USD',
                method='Efectivo',request_key='native-advance-future',advance_periods=[future['period']],
                advance_quote=options['quote'],charge_ids=[future['id']])
            income=client.request('cash-preview')['income_usd']
            paid=client.request('payments',advance)
            assert client.request('payments',advance)==dict(id=paid['id'],duplicate=True)
            detail=client.request(f"receipt/{paid['id']}")
            assert detail['allocations'][0]['concept']==f"Mensualidad {future['period']} (pagada por adelantado)"
            assert detail['payment']['paid_on']==today.isoformat()
            assert client.request('cash-preview')['income_usd']==income+4000
            actual=client.request('state?history=1')
            student=next(s for s in actual['students'] if s['id']==advance_student)
            assert student['balance']==student['overdue']==0
            assert len([c for c in actual['charges'] if c['student_id']==advance_student and c['period']==future['period']])==1
            pdf=client.request(f"receipt/{paid['id']}.pdf")
            assert b'/MediaBox [0 0 396 612]' in pdf and b'/Count 1 ' in pdf
            (Path(os.environ['RUNNER_TEMP'])/'aula-native-anticipo.pdf').write_bytes(pdf)
            options=client.request(f'payment-options?student_id={advance_student}')
            future_cashea=options['future'][0]
            sale_advance=dict(sale,student_id=advance_student,total='40',initial_percent='40',initial_received='16',
                request_key='native-advance-cashea',advance_periods=[future_cashea['period']],charge_ids=[future_cashea['id']])
            sale_advance['preview_hash']=client.request('cashea-preview',sale_advance)['preview_hash']
            future_order=client.request('cashea-order',sale_advance)
            assert future_order['invoice_number']==f"R-{future_order['payment_id']:06d}"
            assert client.request('maintenance-review')['ok']
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
            advance_payment=True,advance_cashea=True,advance_receipt_single_page=True,
            invoice_from_receipt=True,ves_initial_original=160000,ves_initial_equivalent=1600,initial_usd=7800,financed_usd=5200,received_ves=520000,settlement_usd=5200,student_balance=0,maintenance=True,uninstall_keeps_data=True)
        (Path(os.environ['RUNNER_TEMP'])/'cashea-upgrade.json').write_text(json.dumps(result,indent=2))
        print('PASS CASHEA WINDOWS: actualización real 1.0.73 → '+args.version+', datos y PDF histórico idénticos, CA/R/CL, VES, saldo y mora cero, integridad y desinstalación conservadora.',flush=True)
        print('PASS ANTICIPO INSTALADO: cobro futuro y Cashea desde Aula.exe instalado, recibo real de una página, reintento único, caja y bitácora correctos.',flush=True)
    finally:
        if data.exists():shutil.rmtree(data)


if __name__=='__main__':main()
