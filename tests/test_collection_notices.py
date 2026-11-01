"""Only fictional families. Notice preparation must not mutate financial history."""
from contextlib import closing
from datetime import date, datetime, timezone
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from colegio import collection_notices as notices
from colegio.audit_chain import local_status
from colegio.db import ValidationError, connect, initialize
from colegio.server import mutate, snapshot


class NoticeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'colegio.sqlite3';initialize(self.path)
        self.db=connect(self.path);self.addCleanup(self.db.close)
        for target in ('colegio.db.local_today','colegio.server.local_today','colegio.collection_notices.local_today'):
            p=patch(target,return_value=date(2026,11,1));p.start();self.addCleanup(p.stop)
        self.admin=dict(id=1,role='admin',name='Administradora FICTICIA')
        self.cashier=dict(id=2,role='cashier',name='Caja FICTICIA')
        self.reader=dict(id=3,role='reader',name='Consulta FICTICIA')
        with self.db:
            self.db.executemany('INSERT INTO users(id,username,name,password,role) VALUES(?,?,?,?,?)',
                [(u['id'],u['role'],u['name'],'FICTICIO-no-login',u['role']) for u in (self.admin,self.cashier,self.reader)])
            self.db.execute("INSERT INTO guardians(id,name,document,phone) VALUES(1,'MARÍA DE PRUEBA FICTICIA','V-FICTICIO','0424-000-0000')")
            self.db.execute("INSERT INTO grades(id,name,capacity) VALUES(1,'Grado FICTICIO',30)")
            self.db.execute("UPDATE settings SET value='2026' WHERE key='school_year'")
            self.db.execute("UPDATE settings SET value='1' WHERE key='start_month'")
            self.db.execute("UPDATE settings SET value='Colegio FICTICIO' WHERE key='school_name'")
            for sid,name in ((1,'DANIEL DE PRUEBA FICTICIO'),(2,'HERMANA VON PRUEBA FICTICIA')):
                self.db.execute('''INSERT INTO students(id,name,document,student_code,birth_date,guardian_id,grade_id,
                    school_year,monthly_fee,discount,status,enrollment_start,enrollment_end,billing_start)
                    VALUES(?,?,?,?, '',1,1,2026,4000,0,'active','2026-01-01','2026-12-31','2026-01')''',
                    (sid,name,f'AL-{sid:06d}',f'AL-{sid:06d}'))

    def add_months(self,count=1,sid=1,amount=4000):
        with self.db:
            for month in range(11-count,11):
                self.db.execute("INSERT INTO charges(student_id,period,concept,amount,due_date) VALUES(?,?,'Mensualidad',?,?)",
                    (sid,f'2026-{month:02d}',amount,f'2026-{month:02d}-10'))

    def preview(self,**data):return notices.preview(self.db,dict(student_id=1,**data))

    def config(self,**values):
        value=notices.settings(self.db);value.update(values)
        return {k:value[k] for k in ('emojis','cashea','payment_details','templates')}

    def write(self,route,data,user=None):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            return mutate(self.db,route,data,user or self.admin)

    def mark_data(self,**changes):
        value=self.preview(siblings='1')
        return dict(dict(student_id=1,type=value['type'],variant=value['variant'],siblings=True,
            student_ids=value['student_ids'],message=value['text'],request_key='FICTICIO-notice-one'),**changes)

    def finance(self):
        tables=('charges','payments','allocations','monthly_assessments','expenses','cashea_orders','cashea_allocations','cash_closures')
        return {t:[tuple(r) for r in self.db.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in tables}

    def test_all_five_templates_one_three_eight_months_limit_and_complete_total(self):
        for count in (1,3,8):
            with self.db:self.db.execute('DELETE FROM charges')
            self.add_months(count)
            for kind in notices.TYPES:
                with self.subTest(count=count,kind=kind):
                    value=self.preview(type=kind,variant=0,cashea='0')
                    self.assertIn(notices.money_text(count*4000),value['text'])
                    self.assertIn('Octubre 2026' if count<7 else 'Marzo 2026',value['text'])
                    self.assertNotIn('presenta un saldo vencido',value['text'])
                    self.assertNotIn('se le informa',value['text'])
                    if count==8:
                        self.assertIn('y 2 meses más',value['text'])
                        self.assertNotIn('Octubre 2026:',value['text'])
                    if kind=='brief':
                        detail=notices.detail_text(notices.debt_context(self.db,1)['groups'],True)
                        self.assertNotIn('\n',detail)

    def test_venezuelan_amount_rate_rounding_and_missing_today_rate(self):
        self.add_months(amount=26000)
        self.assertNotIn('Bs ',self.preview()['text'])
        with self.db:
            self.db.execute("INSERT INTO exchange_rates VALUES('2026-10-31','889.26','FICTICIO')")
        self.assertNotIn('Bs ',self.preview()['text'])
        with self.db:
            self.db.execute("INSERT INTO exchange_rates VALUES('2026-11-01','889.26','FICTICIO')")
        text=self.preview()['text']
        self.assertIn('USD 260,00',text);self.assertIn('Bs 231.207,60',text);self.assertIn('889,26',text)
        self.assertIn('tasa del día del pago',text)
        self.assertEqual(notices.rate_text('8.8926E2'),'889,26')
        self.assertEqual(notices.rate_text('0.000001'),'0,000001')

    def test_concepts_partial_balance_canceled_and_future_are_handled_without_financial_writes(self):
        self.add_months()
        with self.db:
            self.db.execute("INSERT INTO charges(student_id,period,concept,amount,due_date) VALUES(1,'2026-10','Transporte',2500,'2026-10-20')")
            self.db.execute("INSERT INTO charges(student_id,period,concept,amount,due_date) VALUES(1,'2026-12','Mensualidad',4000,'2026-12-10')")
            self.db.execute("INSERT INTO charges(student_id,period,concept,amount,due_date,cancelled) VALUES(1,'2026-09','Actividad',9999,'2026-09-10',1)")
        before=self.finance();value=self.preview()
        self.assertIn('Transporte: USD 25,00',value['text']);self.assertIn('USD 65,00',value['text'])
        self.assertNotIn('Diciembre',value['text']);self.assertNotIn('Actividad',value['text'])
        self.assertEqual(self.finance(),before)

    def test_full_cashea_coverage_never_becomes_a_false_notice(self):
        self.add_months()
        from colegio.cashea import preview,create_order
        data=dict(student_id=1,ordered_on='2026-10-31',total='40',initial_percent='0',initial_received='0',
            initial_currency='USD',initial_method='Efectivo',request_key='FICTICIO-cashea-covered')
        with patch('colegio.cashea.local_today',return_value=date(2026,11,1)),self.db:
            self.db.execute('BEGIN IMMEDIATE');data['preview_hash']=preview(self.db,data,self.admin)['preview_hash'];create_order(self.db,data,self.admin)
        self.assertFalse(self.preview()['eligible']);self.assertNotIn('USD 40,00',self.preview()['text'])

    def test_cashea_payment_details_emojis_and_unavailable_module(self):
        self.add_months()
        config=self.config(payment_details='CUENTA FICTICIA: texto libre {sin interpretar}',emojis=True,cashea=True)
        self.write('collection-notice-settings',config)
        self.assertIn('Cashea',self.preview()['text']);self.assertNotIn('CUENTA FICTICIA',self.preview()['text'])
        text=self.preview(payment='1',cashea='0')['text']
        self.assertNotIn('Cashea',text);self.assertIn('texto libre {sin interpretar}',text)
        self.assertNotIn('comisión',self.preview()['text']);self.assertNotIn('%',self.preview()['text'])
        self.write('collection-notice-settings',self.config(emojis=False))
        self.assertNotIn('👋',self.preview(type='near')['text'])
        self.assertEqual(notices.limit_emojis('👋🙂✅❤️',True),'👋🙂')
        self.assertEqual(notices.limit_emojis('👩🏽\u200d🏫 🇻🇪 1️⃣ texto',False),'   texto')
        with patch.object(notices,'CASHEA_AVAILABLE',False):
            self.assertFalse(notices.settings(self.db)['cashea']);self.assertNotIn('Cashea',self.preview(cashea='1')['text'])

    def test_greeting_uses_utc_minus_four_boundaries(self):
        for hour,expected in ((0,'Buenas noches'),(4,'Buenas noches'),(5,'Buenos días'),(11,'Buenos días'),
                              (12,'Buenas tardes'),(18,'Buenas tardes'),(19,'Buenas noches'),(23,'Buenas noches')):
            local=datetime(2026,11,1,hour,tzinfo=notices.TZ)
            self.assertEqual(notices.greeting(local.astimezone(timezone.utc)),expected)

    def test_title_names_particles_complete_names_and_rotation(self):
        self.assertEqual(notices.title_name(' EDLEANA  VASQUEZ '),'Edleana  Vasquez')
        self.assertEqual(notices.title_name('MARÍA DE LA CRUZ VON PRUEBA'),'María de la Cruz von Prueba')
        self.assertEqual(notices.title_name("ANA-MARÍA O'NEILL"),"Ana-María O'Neill")
        self.add_months()
        texts=[self.preview(type='near',variant=i)['text'] for i in (0,1,2,0)]
        self.assertEqual(len(set(texts)),3);self.assertEqual(texts[0],texts[3])
        self.assertIn('Daniel de Prueba Ficticio',texts[0]);self.assertIn('María de Prueba Ficticia',texts[0])

    def test_siblings_only_same_family_and_total_all_members(self):
        self.add_months(3);self.add_months(1,sid=2,amount=5000)
        own=self.preview();family=self.preview(siblings='1')
        self.assertNotIn('Hermana von Prueba Ficticia',own['text'])
        self.assertIn('Hermana von Prueba Ficticia',family['text']);self.assertIn('USD 170,00',family['text'])
        self.assertEqual(family['student_ids'],[1,2])

    def test_age_selection_exact_boundaries_and_manual_choice(self):
        self.add_months()
        for days,expected in ((1,'near'),(30,'near'),(31,'cordial'),(60,'cordial'),(61,'late')):
            from datetime import timedelta
            with self.db:self.db.execute('UPDATE charges SET due_date=?',((date(2026,11,1)-timedelta(days=days)).isoformat(),))
            self.assertEqual(self.preview()['type'],expected)
            self.assertEqual(self.preview(type='agreement')['type'],'agreement')

    def test_phones_and_encoded_whatsapp_text(self):
        for value in ('0424 123-4567','+58 (424) 123-4567','584241234567','00584241234567','4241234567'):
            self.assertEqual(notices.normalize_phone(value),'584241234567')
        self.assertEqual(notices.normalize_phone('(0212) 123-4567'),'582121234567')
        for value in ('','0424123','12345678901234','+1 424 1234567','0424abc1234567','+584241234567 ext 2','589991234567'):
            self.assertIsNone(notices.normalize_phone(value),value)
        text='Hola María 👋\nSeptiembre: USD 40,00 & Bs 10.000,00'
        link=notices.whatsapp_url('04241234567',text)
        self.assertEqual(parse_qs(urlsplit(link).query)['text'],[text]);self.assertIn('%0A',link)
        self.assertIsNone(notices.whatsapp_url('inválido',text))

    def test_unknown_markers_formats_and_original_restore(self):
        self.add_months();original=self.config();bad=copy.deepcopy(original)
        for text in ('{desconocido} {meses} {total_usd}','{alumno.__class__} {meses} {total_usd}',
                     '{meses!r} {total_usd}','{meses:>10} {total_usd}','{meses','Sin detalle'):
            bad['templates']['near'][0]=text
            with self.assertRaises(ValidationError):self.write('collection-notice-settings',bad)
        custom=self.config();custom['templates']['near'][0]='Texto propio {representante}\n{meses}\n{total_usd}'
        self.write('collection-notice-settings',custom)
        self.assertTrue(self.preview(type='near',variant=0)['text'].startswith('Texto propio'))
        self.write('collection-notice-settings',original)
        self.assertEqual(notices.settings(self.db)['templates'],notices.DEFAULT_TEMPLATES)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM settings WHERE key LIKE 'collection_notice_%'").fetchone()[0],0)

    def test_mark_is_manual_idempotent_audited_and_has_no_financial_side_effect(self):
        self.add_months();self.add_months(sid=2)
        before=self.finance();data=self.mark_data()
        self.preview();self.assertEqual(self.db.execute('SELECT COUNT(*) FROM collection_notes').fetchone()[0],0)
        result=self.write('collection-notice-mark',data,self.cashier)
        retry=self.write('collection-notice-mark',data,self.cashier)
        self.assertEqual(result['note_ids'],retry['note_ids']);self.assertTrue(retry['duplicate'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM collection_notes').fetchone()[0],2)
        self.assertEqual(self.finance(),before)
        last=self.preview()['last_notice'];self.assertEqual(last['days'],0);self.assertEqual(last['operator'],self.cashier['name'])
        event=json.loads(self.db.execute("SELECT details FROM audit WHERE action='collection_notice_sent'").fetchone()[0])
        self.assertEqual(event['student_ids'],[1,2]);self.assertNotIn('message',event)
        self.assertNotIn(data['message'],json.dumps(event,ensure_ascii=False));self.assertTrue(local_status(self.db)['ok'])
        with self.assertRaises(ValidationError):self.write('collection-notice-mark',dict(data,message='Otro texto'),self.cashier)

    def test_settings_preview_and_mark_permissions_and_audit_privacy(self):
        self.add_months();config=self.config(payment_details='PAGO FICTICIO confidencial')
        before=self.finance()
        for user in (self.cashier,self.reader):
            for route in ('collection-notice-settings','collection-notice-template-preview'):
                with self.assertRaises(PermissionError):self.write(route,config,user)
        with self.assertRaises(PermissionError):self.write('collection-notice-mark',self.mark_data(),self.reader)
        count=self.db.execute('SELECT COUNT(*) FROM settings').fetchone()[0]
        example=self.write('collection-notice-template-preview',config)
        self.assertTrue(example['fictional']);self.assertIn('FICTICIO',example['text'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM settings').fetchone()[0],count)
        self.write('collection-notice-settings',config)
        audit='\n'.join(r[0] for r in self.db.execute('SELECT details FROM audit'))
        self.assertNotIn('PAGO FICTICIO confidencial',audit)
        self.assertEqual(self.finance(),before);self.assertTrue(local_status(self.db)['ok'])

    def test_new_database_seeds_no_notice_settings_or_notes(self):
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM settings WHERE key LIKE 'collection_notice_%'").fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM collection_notes').fetchone()[0],0)
        self.assertEqual(self.db.execute('PRAGMA user_version').fetchone()[0],14)
        self.assertFalse(notices.preview(self.db,dict(student_id=1))['eligible'])

    def test_audit_failure_rolls_back_all_family_notes(self):
        self.add_months();self.add_months(sid=2);before=self.finance()
        with patch.object(notices,'audit',side_effect=RuntimeError('Fallo FICTICIO de bitácora')):
            with self.assertRaises(RuntimeError):self.write('collection-notice-mark',self.mark_data())
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM collection_notes').fetchone()[0],0)
        self.assertEqual(self.finance(),before);self.assertTrue(local_status(self.db)['ok'])

    def test_partial_payment_only_lists_remaining_overdue_amount(self):
        from colegio.db import record_payment
        self.add_months()
        with self.db:
            record_payment(self.db,dict(student_id=1,paid_on='2026-10-30',amount='10',currency='USD',
                method='Efectivo',reference='FICTICIO',request_key='FICTICIO-parcial'),self.admin['id'])
        before=self.finance();text=self.preview()['text']
        self.assertIn('Octubre 2026: USD 30,00',text);self.assertNotIn('USD 40,00',text)
        self.assertEqual(self.finance(),before)


class NoticeHTTPTests(unittest.TestCase):
    def setUp(self):
        from tests.test_system import SystemTests
        self.f=SystemTests();self.f.setUp();self.addCleanup(self.f.tearDown)

    def test_http_csrf_concurrent_idempotency_reports_and_read_only_preview(self):
        from concurrent.futures import ThreadPoolExecutor
        f=self.f;before=f.request('state');daily=f.request('daily-report');cash=f.request('cash-preview')
        value=f.request(f'collection-notice?student_id={f.student}')
        data=dict(student_id=f.student,type=value['type'],variant=value['variant'],siblings=False,
            student_ids=value['student_ids'],message=value['text'],request_key='FICTICIO-concurrente')
        f.request('collection-notice-mark',data,csrf=False,status=403)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:f.request('collection-notice-mark',data),range(2)))
        self.assertEqual(results[0]['note_ids'],results[1]['note_ids'])
        self.assertEqual(sorted(r['duplicate'] for r in results),[False,True])
        after=f.request('state')
        for key in ('summary','payments','charges','expenses','cash_closures','cashea_cash'):
            self.assertEqual(before[key],after[key],key)
        self.assertEqual(f.request('cash-preview'),cash)
        for key in ('income_usd','overdue_usd','payment_count'):
            self.assertEqual(f.request('daily-report')[key],daily[key])
        self.assertEqual(len(after['collections']),1)
        self.assertEqual(f.request(f'collection-notice?student_id={f.student}')['last_notice']['days'],0)
        from colegio.storage import consistent_backup
        from colegio.read_only import open_copy
        import http.client,threading,hashlib
        copy=f.path.parent/'FICTICIO-consulta.sqlite3';consistent_backup(f.path,copy)
        original=hashlib.sha256(copy.read_bytes()).hexdigest()
        with open_copy(copy) as server:
            thread=threading.Thread(target=server.serve_forever);thread.start()
            client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
            try:
                client.request('GET','/?view_token='+server.launch);response=client.getresponse()
                cookie=response.getheader('Set-Cookie').split(';')[0];response.read();self.assertEqual(response.status,303)
                client.request('GET',f'/api/collection-notice?student_id={f.student}',headers={'Cookie':cookie})
                response=client.getresponse();body=json.loads(response.read());self.assertEqual(response.status,200)
                self.assertEqual(body['text'],value['text'])
                client.request('POST','/api/collection-notice-mark',json.dumps(data),
                    {'Cookie':cookie,'Content-Type':'application/json'})
                response=client.getresponse();response.read();self.assertEqual(response.status,403)
            finally:client.close();server.shutdown();thread.join()
        self.assertEqual(hashlib.sha256(copy.read_bytes()).hexdigest(),original)


if __name__=='__main__':unittest.main()
