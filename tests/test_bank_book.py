from contextlib import closing
from datetime import timedelta
import base64,csv,io,json,unittest
from colegio.db import connect,local_today

class BankBookTests(unittest.TestCase):
    def setUp(self):
        from tests.test_system import SystemTests
        self.f=SystemTests();self.f.setUp();self.on=local_today().isoformat();self.bank=self.f.school_accounts[('USD','bank')]
        self.profile=dict(delimiter=';',encoding='utf-8-sig',decimal='.',date_format='%Y-%m-%d',columns=dict(date='Fecha',amount='Importe',reference='Referencia',description='Descripción',bank_id='ID'))
    def tearDown(self):self.f.tearDown()
    def data(self,rows,**extra):
        out=io.StringIO(newline='');writer=csv.writer(out,delimiter=';');writer.writerow(['Fecha','Importe','Referencia','Descripción','ID']);writer.writerows(rows)
        return dict(account_id=self.bank,filename='ficticio.csv',file_base64=base64.b64encode(out.getvalue().encode('utf-8-sig')).decode(),profile=self.profile,**extra)
    def imported(self,rows,**extra):
        data=self.data(rows,**extra);review=self.f.request('bank-preview',data);return self.f.request('bank-import',dict(data,confirmed_hash=review['file_sha256'])),data,review
    def pay(self,amount='10',ref='000012',key='p',**extra):return self.f.request('payments',self.f.payment(amount=amount,reference=ref,key=key,paid_on=self.on,**extra))['id']
    def test_profile_preview_import_idempotency_overlap_and_conflicting_bank_identity(self):
        identifier=self.f.request('bank-profile',dict(name='Provincial ficticio NO VERIFICADO',profile=self.profile))['id']
        self.assertEqual(self.f.request('bank-book')['profiles'][0]['status'],'NO VERIFICADO')
        row=[self.on,'10.00','000012','CONFIDENCIAL-FICTICIO-EXTRACTO','A-1'];result,data,review=self.imported([row]);self.assertEqual(result['imported'],1)
        self.assertTrue(self.f.request('bank-import',dict(data,confirmed_hash=review['file_sha256']))['duplicate'])
        extra=[self.on,'5.00','9','FICTICIO-OTRO','A-2'];result,_,_=self.imported([row,extra]);self.assertEqual(result['duplicate_ids_skipped'],1);self.assertEqual(result['imported'],1)
        data=self.data([[self.on,'11.00','000012','CORREGIDO','A-1']]);p=self.f.request('bank-preview',data);self.assertTrue(p['overlaps'][0]['conflict'])
        self.f.request('bank-import',dict(data,confirmed_hash=p['file_sha256']),status=400)
        with closing(connect(self.f.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM bank_movements').fetchone()[0],2)
            audit=' '.join(r[0] for r in db.execute('SELECT details FROM audit'))
            self.assertNotIn('CONFIDENCIAL-FICTICIO-EXTRACTO',audit);self.assertNotIn('A-1',audit)
    def test_unique_exact_reference_zeros_date_tolerance_and_totals_unchanged(self):
        pid=self.pay();before=self.f.request('state?history=1')['summary'];receipt=self.f.request('receipt/'+str(pid)+'.pdf')
        day=(local_today()-timedelta(days=3)).isoformat();self.imported([[day,'10.00','12','Ficticio','B1']])
        self.assertTrue(self.f.request('bank-book?month='+day[:7])['bank_pending'][0]['proposal']['unique'])
        self.assertEqual(self.f.request('bank-auto',dict(month=day[:7]))['linked'],1)
        self.assertEqual(self.f.request('bank-auto',dict(month=day[:7]))['linked'],0)
        self.assertEqual(self.f.request('state?history=1')['summary'],before);self.assertEqual(self.f.request('receipt/'+str(pid)+'.pdf'),receipt)
        self.f.request('void-payment',dict(id=pid,reason='Prueba ficticia de anulación'),status=400)
        self.f.request('income-assign',dict(kind='payments',ids=[pid],account_id=self.bank,reason='Prueba ficticia de reasignación'),status=400)
        link=self.f.request('bank-book')['links'][0];self.f.request('bank-unlink',dict(id=link['id'],reason='Prueba ficticia de retiro de vínculo'))
        self.f.request('void-payment',dict(id=pid,reason='Anulación ficticia luego de revisar'))
    def test_many_receipts_one_deposit_and_partial_many_deposits(self):
        p1=self.pay('10','1','p1');p2=self.pay('20','2','p2')
        self.imported([[self.on,'15.00','x','Ficticio','C1'],[self.on,'15.00','y','Ficticio','C2']])
        links=[dict(movement_id=1,source='P'+str(p1),amount='10'),dict(movement_id=1,source='P'+str(p2),amount='5'),dict(movement_id=2,source='P'+str(p2),amount='15')]
        self.assertEqual(self.f.request('bank-link',dict(links=links,reason='Revisión ficticia de planilla agrupada'))['linked'],3)
        self.f.request('bank-link',dict(links=[links[0]],reason='No debe permitir doble cobertura'),status=400)
        view=self.f.request('bank-book');self.assertFalse(view['bank_pending']);self.assertFalse(view['ledger_pending']);self.assertEqual(view['totals'][0]['linked'],3000)
    def test_possible_duplicate_without_id_needs_explicit_review_and_corrupt_import_is_atomic(self):
        self.imported([[self.on,'1.00','1','Ficticio','']])
        data=self.data([[self.on,'1.00','1','Ficticio',''],[self.on,'2.00','2','Otro','']]);p=self.f.request('bank-preview',data)
        self.f.request('bank-import',dict(data,confirmed_hash=p['file_sha256']),status=400)
        self.f.request('bank-import',dict(data,confirmed_hash=p['file_sha256'],accepted_duplicate_rows=[2],reason='Son movimientos ficticios distintos confirmados'))
        bad=self.data([[self.on,'3.333','3','Inválido','']]);self.f.request('bank-preview',bad,status=400)
        with closing(connect(self.f.path)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM bank_movements').fetchone()[0],3)
    def test_ambiguity_missing_reference_and_outside_tolerance_never_auto_link(self):
        self.pay('10','3','p1');self.pay('10','3','p2',duplicate_reference_confirmed=True,duplicate_reason='Referencia repetida ficticia revisada');self.pay('7','','p3');self.pay('4','4','p4')
        self.imported([[self.on,'10','003','Ambiguo','D1'],[self.on,'7','','Sin referencia','D2'],[(local_today()-timedelta(days=4)).isoformat(),'4','4','Fuera de tolerancia','D3']])
        self.assertEqual(self.f.request('bank-auto',{})['linked'],0)
        self.assertEqual(len(self.f.request('bank-book')['links']),0)
    def test_debits_expenses_and_classifications_remain_separate_from_income(self):
        expense=self.f.request('expenses',dict(concept='Egreso ficticio',category='Operación',spent_on=self.on,amount='2',currency='USD',method='Transferencia',account_id=self.bank))['id']
        before=self.f.request('state?history=1')['summary'];self.imported([[self.on,'-2','E','Ficticio','E1'],[self.on,'3','AP','Ficticio','E2']])
        self.f.request('bank-link',dict(links=[dict(movement_id=1,source='E'+str(expense),amount='2')],reason='Revisión ficticia del egreso con soporte'))
        self.f.request('void-expense',dict(id=expense,reason='No se permite anular conciliado'),status=400)
        classified=self.f.request('bank-classify',dict(movement_id=2,category='Préstamo o aporte',support='Contrato ficticio',reason='Clasificación ficticia revisada'))
        self.assertEqual(self.f.request('state?history=1')['summary'],before)
        self.f.request('bank-classify',dict(movement_id=2,category='Otro',support='Ficticio',reason='No duplicar clasificación'),status=400)
        self.f.request('bank-unclassify',dict(id=classified['id'],reason='Revisión ficticia de clasificación anterior'))
    def test_ves_original_cents_and_cash_deposit_not_double_counted(self):
        vesbank=self.f.school_accounts[('VES','bank')];self.f.request('rates',dict(rate_date=self.on,rate='100'))
        pid=self.pay('1000.01','VES001','ves',currency='VES')
        data=self.data([[self.on,'1000.01','VES001','Ficticio','VES1']]);data['account_id']=vesbank;p=self.f.request('bank-preview',data);self.f.request('bank-import',dict(data,confirmed_hash=p['file_sha256']))
        self.assertEqual(self.f.request('bank-auto',{})['linked'],1)
        cash=self.pay('5','CASH','cash',method='Efectivo');dep=self.f.request('income-deposit',dict(deposited_on=self.on,account_id=self.bank,currency='USD',amount='5',reference='PLANILLA',support='Ficticio planilla',request_key='planilla',payments=[dict(payment_id=cash,amount='5')]))['id']
        self.imported([[self.on,'5','PLANILLA','Ficticio','USD1']]);self.assertEqual(self.f.request('bank-auto',{})['linked'],1)
        self.f.request('income-void-deposit',dict(id=dep,reason='No anular depósito conciliado'),status=400)
    def test_cashier_and_reader_never_receive_statements_or_write(self):
        self.imported([[self.on,'1','1','Confidencial ficticio','F1']])
        for role in ('cashier','reader'):self.f.request('users',dict(username=role,name='Ficticio '+role,password='FICTICIO-clave-segura',role=role))
        for role in ('cashier','reader'):
            self.f.request('logout',{});self.f.request('login',dict(username=role,password='FICTICIO-clave-segura'));self.f.csrf=self.f.request('session')['user']['csrf'];self.f.request('confirm-rate',dict(rate_date=self.on,rate='100'))
            report=self.f.request('bank-book');self.assertEqual(set(report),{'month','totals'})
            for endpoint in ('bank-profile','bank-preview','bank-import','bank-auto','bank-link','bank-classify','bank-unlink','bank-unclassify'):self.f.request(endpoint,{},status=403)

    def test_auto_is_scoped_to_reviewed_month_not_entire_history(self):
        past=(local_today().replace(day=1)-timedelta(days=1)).isoformat()
        current=self.pay('3','NOW','now')
        previous=self.f.request('payments',self.f.payment(amount='4',reference='PAST',key='past',paid_on=past))['id']
        self.imported([[self.on,'3','NOW','Ficticio actual','S1'],[past,'4','PAST','Ficticio anterior','S2']])
        self.assertEqual(self.f.request('bank-auto',dict(month=self.on[:7]))['linked'],1)
        links=self.f.request('bank-book')['links'];self.assertEqual([r['payment_id'] for r in links],[current])
        self.assertEqual(self.f.request('bank-auto',dict(month=past[:7]))['linked'],1)

    def test_cash_other_income_is_not_an_impossible_bank_pending(self):
        category=self.f.request('income-category',dict(name='Ficticio aporte'))['id']
        ids={}
        for method,kind in (('Efectivo','cash'),('Transferencia','bank')):
            ids[kind]=self.f.request('income-other',dict(concept='Ficticio '+kind,category_id=category,received_on=self.on,amount='3',currency='USD',method=method,account_id=self.f.school_accounts[('USD',kind)],reference='FICTICIO-'+kind,support='Soporte ficticio',request_key='FICTICIO-'+kind))['id']
        before=self.f.request('state?history=1')['summary']
        pending=self.f.request('bank-book')['ledger_pending']
        self.assertEqual([r['id'] for r in pending],['O'+str(ids['bank'])])
        self.assertEqual(self.f.request('state?history=1')['summary'],before)
