"""Real HTTP sales, settlements and invariants, exclusively fictional temporary data."""
from contextlib import closing
from decimal import Decimal
import json,re,sqlite3,unittest
from unittest.mock import patch
from pathlib import Path

from colegio.db import connect,local_today
from colegio.cashea import expected_date
from tests import test_system as system


class CasheaTests(unittest.TestCase):
    tearDown=system.SystemTests.tearDown
    request=system.SystemTests.request
    student_data=system.SystemTests.student_data
    payment=system.SystemTests.payment

    def setUp(self):
        system.SystemTests.setUp(self)
        self.number=0
        self.request('grades',dict(id=self.grade,name='Primaria A',capacity=30))
        self.sid=self.new_student()

    def new_student(self,**overrides):
        today=local_today();year=today.year if today.month>=9 else today.year-1
        return self.request('students',self.student_data(name='Alumno FICTICIO Cashea',document='',birth_date='',
            school_year=year,enrollment_start=f'{year}-09-01',enrollment_end=f'{year+1}-08-31',
            billing_start=today.strftime('%Y-%m'),monthly_fee=overrides.pop('monthly_fee','130'),discount=0,**overrides))['id']

    def order_data(self,**overrides):
        self.number+=1
        return dict(dict(student_id=self.sid,ordered_on=local_today().isoformat(),total='130',initial_percent='60',
            initial_received='78',initial_currency='USD',initial_method='Efectivo',invoice_number=f'F-FICTICIA-{self.number}',
            request_key=f'cashea-venta-ficticia-{self.number}'),**overrides)

    def order(self,**overrides):
        data=self.order_data(**overrides)
        data['preview_hash']=self.request('cashea-preview',data)['preview_hash']
        return self.request('cashea-order',data),data

    def settlement(self,ids,**overrides):
        self.number+=1
        book=self.request('cashea')
        expected=sum(o['expected_amount'] for o in book['orders'] if o['id'] in ids)
        data=dict(order_ids=ids,received_on=local_today().isoformat(),currency='USD',amount=format(Decimal(expected)/100,'.2f'),
            reference=f'BANCO-FICTICIO-{self.number}',request_key=f'cashea-liquidacion-ficticia-{self.number}')
        data.update(overrides)
        data['preview_hash']=self.request('cashea-settlement-preview',data)['preview_hash']
        return self.request('cashea-settlement',data),data

    def cancel(self,route,target,**overrides):
        self.number+=1
        return self.request(route,dict(id=target,reason='Corrección FICTICIA',request_key=f'cashea-anulacion-ficticia-{self.number}',**overrides))

    def config(self,**overrides):
        self.number+=1
        data=self.request('cashea')['settings'];data.update(overrides);data['request_key']=f'cashea-ajustes-ficticios-{self.number}'
        return self.request('cashea-settings',data)

    def cashea_student(self):return next(s for s in self.request('state')['students'] if s['id']==self.sid)

    def test_130_78_52_covers_student_without_counting_finance_as_cash(self):
        order,data=self.order()
        self.assertEqual(self.cashea_student()['balance'],0);self.assertEqual(self.cashea_student()['overdue'],0)
        cash=self.request('cash-preview');self.assertEqual(cash['income_usd'],7800)
        self.assertEqual(cash['cashea']['financed'],5200)
        state=self.request('state');self.assertEqual(state['summary']['income'],7800)
        self.assertEqual(self.request('daily-report')['income_usd'],7800)
        receipt=self.request(f"receipt/{order['payment_id']}")
        self.assertEqual(receipt['payment']['amount'],7800)
        self.assertEqual(receipt['payment']['balance_after'],0)
        self.assertEqual(receipt['payment']['cashea']['financed_amount'],5200)
        pdf=self.request(f"cashea-order/{order['id']}.pdf")
        self.assertIn(b'/MediaBox [0 0 396 612]',pdf)
        self.assertEqual(len(re.findall(rb'/Type /Page\b',pdf)),1)
        self.assertEqual(self.request('cashea-order',data),order)
        self.assertTrue(self.request('maintenance-review')['ok'])

    def test_zero_initial_creates_no_receipt_and_financing_is_not_overdue(self):
        before=len(self.request('state')['payments'])
        order,_=self.order(initial_received='0',initial_percent='0')
        self.assertIsNone(order['payment_id']);self.assertEqual(len(self.request('state')['payments']),before)
        self.assertEqual(self.cashea_student()['balance'],0)
        self.assertEqual(self.request('cash-preview')['income_usd'],0)
        self.assertEqual(self.request('cashea')['pending'],13000)
        self.assertFalse(self.request(f'student-deletion-preview/{self.sid}')['can_delete'])
        self.cancel('cashea-void-order',order['id'])
        self.assertEqual(self.cashea_student()['balance'],13000)
        self.assertFalse(self.request(f'student-deletion-preview/{self.sid}')['can_delete'])

    def test_hundred_percent_initial_needs_no_settlement_but_can_be_cancelled(self):
        order,_=self.order(initial_received='130',initial_percent='100')
        self.assertEqual(self.request('cashea')['pending'],0)
        self.cancel('cashea-void-order',order['id'])
        self.assertEqual(self.cashea_student()['balance'],13000)

    def test_rounding_and_multiple_charges_never_lose_cents(self):
        sid=self.new_student(monthly_fee='133.33')
        order,_=self.order(student_id=sid,total='133.33',initial_received='66.67',initial_percent='50')
        doc=self.request(f"cashea-order/{order['id']}")
        self.assertEqual((doc['initial_amount'],doc['financed_amount']),(6667,6666))

    def test_multiple_charge_financing_uses_same_fifo_as_initial(self):
        # SystemTests owns an older fictional enrollment with twelve USD 45 charges.
        original=self.__dict__['student']
        order,_=self.order(student_id=original)
        with closing(connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT SUM(amount) FROM cashea_allocations WHERE order_id=?',(order['id'],)).fetchone()[0],5200)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM cashea_allocations WHERE order_id=?',(order['id'],)).fetchone()[0],2)

    def test_existing_payment_plan_counts_financing_and_annulment_restores_it(self):
        original=next(s for s in self.request('state')['students'] if s['id']==self.student)
        total=original['overdue']
        plan=self.request('payment-plans',dict(student_id=self.student,expected_total=total,
            installments=[dict(amount=format(Decimal(total)/100,'.2f'),due_date=local_today().isoformat())]))
        order,_=self.order(student_id=self.student)
        current=next(p for p in self.request('state')['payment_plans'] if p['id']==plan['id'])
        self.assertEqual(current['balance'],total-13000)
        self.cancel('cashea-void-order',order['id'])
        current=next(p for p in self.request('state')['payment_plans'] if p['id']==plan['id'])
        self.assertEqual(current['balance'],total)

    def test_missing_historical_rate_future_sale_and_cashea_overdue_alert_with_grace(self):
        from datetime import timedelta
        today=local_today();yesterday=(today-timedelta(days=1)).isoformat()
        self.request('cashea-preview',self.order_data(ordered_on=yesterday,initial_received='7800',initial_currency='VES'),status=400)
        self.request('cashea-preview',self.order_data(ordered_on=(today+timedelta(days=1)).isoformat()),status=400)
        order,_=self.order(ordered_on=(today-timedelta(days=8)).isoformat(),expected_on=yesterday,initial_received='0')
        self.assertEqual(self.request('cashea')['overdue_count'],1)
        self.assertEqual(self.cashea_student()['overdue'],0)
        self.config(cashea_grace_days='2')
        self.assertEqual(self.request('cashea')['overdue_count'],0)

    def test_strict_next_wednesday_edit_and_configuration_do_not_reprice_history(self):
        self.assertEqual(expected_date('2026-10-27'),'2026-10-28')
        self.assertEqual(expected_date('2026-10-28'),'2026-11-04')
        self.assertEqual(expected_date('2026-10-29'),'2026-11-04')
        order,_=self.order()
        before=self.request(f"cashea-order/{order['id']}")
        self.config(cashea_settlement_day='4',cashea_grace_days='2',cashea_commission_percent='2')
        self.assertEqual(self.request(f"cashea-order/{order['id']}")['commission_amount'],before['commission_amount'])
        changed=expected_date(local_today().isoformat(),4)
        self.cancel('cashea-order-date',order['id'],expected_on=changed)
        self.assertEqual(self.request(f"cashea-order/{order['id']}")['expected_on'],changed)

    def test_exact_partial_batch_settlement_and_idempotency(self):
        first,_=self.order();second,_=self.order(student_id=self.new_student(),initial_received='0')
        result,data=self.settlement([first['id']])
        self.assertEqual(result['amount'],5200)
        self.assertEqual(self.request('cashea-settlement',data),result)
        states={o['id']:o['state'] for o in self.request('cashea')['orders']}
        self.assertEqual(states[first['id']],'liquidada');self.assertEqual(states[second['id']],'por_liquidar')
        self.assertEqual(self.request('cash-preview')['income_usd'],13000)
        self.assertEqual(self.request('state')['summary']['income'],13000)
        self.request('cashea-settlement',dict(data,amount='53'),status=400)
        self.assertTrue(self.request('maintenance-review')['ok'])

    def test_ves_initial_and_bank_settlement_keep_original_currency_and_rate(self):
        order,_=self.order(initial_received='7800',initial_currency='VES',initial_method='Pago móvil')
        result,_=self.settlement([order['id']],currency='VES',amount='5200')
        self.assertEqual(result['amount'],5200)
        cash=self.request('cash-preview');self.assertEqual(cash['income_usd'],13000)
        self.assertFalse(any(r['method']=='Efectivo' for r in cash['lines']))
        daily=self.request('daily-report');self.assertEqual(daily['received_ves'],1300000)

    def test_commission_and_unexpected_difference_require_reason_and_no_expense(self):
        self.config(cashea_commission_percent='2')
        order,_=self.order()
        doc=self.request(f"cashea-order/{order['id']}")
        self.assertEqual((doc['commission_amount'],doc['expected_amount']),(104,5096))
        data=dict(order_ids=[order['id']],received_on=local_today().isoformat(),currency='USD',amount='50.96',reference='BANCO-COMISION-FICTICIA',request_key='cashea-comision-ficticia')
        data['preview_hash']=self.request('cashea-settlement-preview',data)['preview_hash']
        self.request('cashea-settlement',data,status=400)
        result,_=self.settlement([order['id']],amount='50.96',reason='Comisión FICTICIA del 2 %')
        self.assertEqual((result['difference'],result['gross_difference']),(0,-104))
        self.assertEqual(self.request('state')['expenses'],[])

    def test_annulment_order_and_settlement_keep_snapshots_and_restore_balance(self):
        order,_=self.order()
        receipt=self.request(f"receipt/{order['payment_id']}")
        self.request('void-payment',dict(id=order['payment_id'],reason='Intento FICTICIO'),status=400)
        result,_=self.settlement([order['id']])
        self.request('cashea-void-order',dict(id=order['id'],reason='Intento',request_key='cashea-void-forbidden'),status=400)
        self.cancel('cashea-void-settlement',result['id'])
        self.assertEqual(self.cashea_student()['balance'],0)
        self.cancel('cashea-void-order',order['id'])
        self.assertEqual(self.cashea_student()['balance'],13000)
        after=self.request(f"receipt/{order['payment_id']}")
        self.assertTrue(after['payment']['voided'])
        self.assertEqual(receipt['allocations'],after['allocations'])
        self.assertEqual(receipt['payment']['cashea'],after['payment']['cashea'])
        self.assertTrue(self.request('maintenance-review')['ok'])

    def test_close_keeps_only_initial_in_physical_cash_and_blocks_annulments(self):
        order,_=self.order();settlement,_=self.settlement([order['id']])
        preview=self.request('cash-preview')
        result=self.request('close-cash',dict(closed_on=local_today().isoformat(),preview_hash=preview['preview_hash'],
            opening_USD='0',counted_USD='78',opening_VES='0',counted_VES='0',notes='Cierre FICTICIO Cashea'))
        doc=self.request(f"cash-close/{result['id']}")
        self.assertEqual(doc['counts'][0]['expected'],7800)
        self.assertEqual(doc['income_usd'],13000)
        self.assertTrue(self.request(f"cash-close/{result['id']}.pdf").startswith(b'%PDF'))
        self.request('cashea-void-settlement',dict(id=settlement['id'],reason='FICTICIO',request_key='cashea-cerrada-anulacion'),status=400)

    def test_invoice_duplicates_need_explicit_review_and_reason(self):
        order,data=self.order()
        other=self.order_data(student_id=self.new_student(),invoice_number=data['invoice_number'])
        self.request('cashea-preview',other,status=400)
        other.update(invoice_duplicate_confirmed=True,invoice_reason='Duplicado revisado FICTICIO')
        other['preview_hash']=self.request('cashea-preview',other)['preview_hash']
        self.request('cashea-order',other)

    def test_stale_review_invalid_input_missing_rate_and_wrong_idempotency_body(self):
        data=self.order_data();data['preview_hash']=self.request('cashea-preview',data)['preview_hash']
        self.request('payments',self.payment(student_id=self.sid,amount='1',paid_on=local_today().isoformat()))
        self.request('cashea-order',data,status=400)
        for overrides in ({'initial_received':'131'},{'invoice_number':''},{'total':'NaN'},{'initial_received':'1.001'},{'initial_currency':'EUR'},{'initial_method':'Cashea'}):
            with self.subTest(overrides=overrides):self.request('cashea-preview',self.order_data(**overrides),status=400)

    def test_documents_exports_and_solvency_have_coverage_without_minor_identifiers(self):
        order,_=self.order()
        account=self.request(f'guardian-account/{self.guardian}')
        self.assertTrue(any('Pagada con Cashea' in c.get('cashea_label','') for c in account['charges']))
        for ext in ('csv','pdf','xlsx'):
            content=self.request(f'cashea-report.{ext}?type=sales')
            self.assertTrue(content.startswith(b'\xef\xbb\xbf' if ext=='csv' else b'%PDF' if ext=='pdf' else b'PK'))
            if ext=='csv':
                self.assertIn(b'AL-',content);self.assertNotIn(b'birth_date',content);self.assertNotIn(b'A-001',content)
        monthly=self.request('monthly-report?month='+local_today().strftime('%Y-%m'))
        self.assertEqual(monthly['cashea']['financed'],5200)
        self.assertEqual(monthly['cashea']['pending'],5200)
        pending=self.request('cashea-report.csv?type=pending').decode('utf-8-sig')
        self.assertTrue(pending.startswith('Semana;Órdenes;Financiado USD;Neto esperado USD;Vencidas'))
        import io,zipfile
        with zipfile.ZipFile(io.BytesIO(self.request('cashea-report.xlsx?type=pending'))) as archive:
            self.assertIn(b'Semana',archive.read('xl/worksheets/sheet1.xml'))

    def test_monthly_cut_uses_reception_and_void_dates_not_current_status(self):
        from colegio.cashea import cutoff_summary
        order,_=self.order();settlement,_=self.settlement([order['id']])
        with closing(connect(self.path)) as db,db:
            # Move only disposable test rows to explicit historical business dates.
            db.execute("UPDATE cashea_orders SET ordered_on='2026-01-01',expected_on='2026-01-07' WHERE id=?",(order['id'],))
            db.execute("UPDATE cashea_settlements SET received_on='2026-02-01' WHERE id=?",(settlement['id'],))
            jan=cutoff_summary(db,'2026-01-01','2026-01-31');self.assertEqual(jan['pending'],5200);self.assertEqual(jan['received'],0)
            feb=cutoff_summary(db,'2026-02-01','2026-02-28');self.assertEqual(feb['pending'],0);self.assertEqual(feb['received'],5200)
            db.execute("UPDATE cashea_settlements SET voided=1,voided_on='2026-03-01',void_reason='FICTICIO' WHERE id=?",(settlement['id'],))
            self.assertEqual(cutoff_summary(db,'2026-02-01','2026-02-28')['received'],5200)
            self.assertEqual(cutoff_summary(db,'2026-03-01','2026-03-31')['pending'],5200)
