"""Receipt-origin identifiers and unambiguous original-currency initials, real HTTP."""
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import http.client,json,sqlite3,unittest
from colegio.db import connect,local_today,next_record_id
from tests import test_cashea as flows


class CasheaNumberTests(unittest.TestCase):
    setUp=flows.CasheaTests.setUp
    tearDown=flows.CasheaTests.tearDown
    request=flows.CasheaTests.request
    student_data=flows.CasheaTests.student_data
    new_student=flows.CasheaTests.new_student
    order_data=flows.CasheaTests.order_data
    order=flows.CasheaTests.order
    config=flows.CasheaTests.config
    cancel=flows.CasheaTests.cancel

    def test_40_16_24_receipt_is_invoice_and_retries_keep_one_number(self):
        sale,data=self.order(student_id=self.new_student(monthly_fee='40'),total='40',initial_received='16',initial_percent='40',invoice_number='IGNORAR-CLIENTE')
        doc=self.request(f"cashea-order/{sale['id']}")
        self.assertEqual((doc['total_amount'],doc['initial_amount'],doc['financed_amount']),(4000,1600,2400))
        self.assertEqual(doc['invoice_number'],f"R-{sale['payment_id']:06d}")
        self.assertEqual(doc['invoice_origin'],'recibo')
        self.assertEqual(self.request('cashea-order',data),sale)
        payment=self.request(f"receipt/{sale['payment_id']}")['payment']
        self.assertEqual(payment['cashea']['invoice_number'],doc['invoice_number'])
        for route in (f"cashea-order/{sale['id']}.pdf",'cashea-report.csv?type=sales','cashea-report.pdf?type=sales'):
            self.assertIn(doc['invoice_number'].encode(),self.request(route))
        self.assertTrue(self.request('maintenance-review')['ok'])

    def test_ves_stores_original_rate_equivalent_and_warns_strictly_over_one_percent(self):
        data=self.order_data(total='40',initial_percent='40',initial_received='1600',initial_currency='VES',initial_method='Pago móvil')
        review=self.request('cashea-preview',data)
        self.assertEqual((review['initial_received'],review['initial_rate'],review['initial_amount']),(160000,'100',1600))
        self.assertEqual(review['initial_warning'],'')
        self.assertEqual(self.request('cashea-preview',dict(data,initial_received='1584'))['initial_warning'],'')
        self.assertIn('1 %',self.request('cashea-preview',dict(data,initial_received='1583'))['initial_warning'])
        self.assertIn('1 %',self.request('cashea-preview',dict(data,initial_received='16'))['initial_warning'])
        data['preview_hash']=review['preview_hash'];saved=self.request('cashea-order',data)
        p=self.request(f"receipt/{saved['payment_id']}")['payment']
        self.assertEqual((p['currency'],p['received_amount'],p['exchange_rate'],p['amount']),('VES',160000,'100',1600))
        # The actual amount takes precedence; warnings do not block an informed confirmation.
        order,_=self.order(student_id=self.new_student(),total='40',initial_percent='40',initial_received='1500',initial_currency='VES')
        self.assertEqual(self.request(f"cashea-order/{order['id']}")['initial_amount'],1500)

    def test_zero_initial_uses_order_and_does_not_reserve_receipt(self):
        before=self.request('cashea')['next_receipt_number']
        sale,_=self.order(total='40',initial_percent='0',initial_received='0')
        doc=self.request(f"cashea-order/{sale['id']}")
        self.assertEqual(doc['invoice_number'],sale['code']);self.assertEqual(doc['invoice_label'],'N.º de orden')
        self.assertIsNone(sale['payment_id']);self.assertEqual(self.request('cashea')['next_receipt_number'],before)
        next_sale,_=self.order(total='40',initial_percent='40',initial_received='16')
        self.assertEqual(next_sale['invoice_number'],before)

    def test_manual_requires_number_and_reviewed_duplicates_but_cannot_reuse_receipt_origin(self):
        auto,_=self.order(total='40',initial_percent='40',initial_received='16')
        self.config(cashea_invoice_origin='manual',cashea_invoice_required='0')
        self.request('cashea-preview',self.order_data(invoice_number=''),status=400)
        self.request('cashea-preview',self.order_data(invoice_number=auto['invoice_number'],invoice_duplicate_confirmed=True,invoice_reason='FICTICIO'),status=400)
        first,data=self.order(total='40',initial_received='0',invoice_number='MANUAL-0001')
        other=self.order_data(total='40',initial_received='0',invoice_number='manual-0001')
        self.request('cashea-preview',other,status=400)
        other.update(invoice_duplicate_confirmed=True,invoice_reason='Revisado FICTICIO')
        other['preview_hash']=self.request('cashea-preview',other)['preview_hash']
        second=self.request('cashea-order',other)
        self.assertEqual(self.request(f"cashea-order/{second['id']}")['invoice_origin'],'manual')
        self.assertEqual(self.request(f"cashea-order/{first['id']}")['invoice_number'],'MANUAL-0001')

    def test_void_retains_identifier_unique_index_and_new_receipt_advances(self):
        first,_=self.order(total='40',initial_received='16',initial_percent='40')
        self.cancel('cashea-void-order',first['id'])
        second,_=self.order(total='40',initial_received='16',initial_percent='40')
        self.assertGreater(second['payment_id'],first['payment_id'])
        self.assertEqual(self.request(f"cashea-order/{first['id']}")['invoice_number'],first['invoice_number'])
        self.assertIn(b'portal de Cashea',self.request(f"cashea-order/{first['id']}.pdf"))
        with closing(connect(self.path)) as db:
            with self.assertRaises(sqlite3.IntegrityError),db:
                db.execute('UPDATE cashea_orders SET invoice_key=? WHERE id=?',(first['invoice_number'],second['id']))
        self.assertTrue(self.request('maintenance-review')['ok'])

    def test_other_cashier_receipt_invalidates_prediction_without_altering_old_receipt(self):
        data=self.order_data(total='40',initial_received='16',initial_percent='40')
        reviewed=self.request('cashea-preview',data);data['preview_hash']=reviewed['preview_hash']
        from tests.test_system import SystemTests
        payment=self.request('payments',SystemTests.payment(self,student_id=self.student,amount='1',paid_on=local_today().isoformat()))
        before=self.request(f"receipt/{payment['id']}.pdf")
        self.request('cashea-order',data,status=400)
        data['preview_hash']=self.request('cashea-preview',data)['preview_hash'];sale=self.request('cashea-order',data)
        self.assertNotEqual(sale['invoice_number'],reviewed['invoice_number'])
        self.assertEqual(before,self.request(f"receipt/{payment['id']}.pdf"))

    def test_concurrent_distinct_sales_require_new_review_and_have_unique_real_receipts(self):
        data=[self.order_data(total='40',initial_received='16',initial_percent='40',student_id=sid) for sid in (self.sid,self.new_student())]
        for d in data:d['preview_hash']=self.request('cashea-preview',d)['preview_hash']
        def send(d):
            c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=30)
            c.request('POST','/api/cashea-order',json.dumps(d),{'Cookie':self.cookie,'X-CSRF-Token':self.csrf,'Content-Type':'application/json'})
            r=c.getresponse();result=(r.status,json.loads(r.read()));c.close();return result
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(send,data))
        self.assertEqual(sorted(status for status,_ in results),[200,400])
        retry=data[next(i for i,r in enumerate(results) if r[0]==400)]
        retry['preview_hash']=self.request('cashea-preview',retry)['preview_hash'];self.request('cashea-order',retry)
        orders=self.request('cashea')['orders'];self.assertEqual(len({o['invoice_number'] for o in orders}),2)
        self.assertTrue(all(o['invoice_number']==f"R-{o['payment_id']:06d}" for o in orders))

    def test_settings_origin_invalid_rejected_and_currency_rate_change_invalidates_review(self):
        self.config(cashea_invoice_origin='recibo')
        values=self.request('cashea')['settings'];values.update(cashea_invoice_origin='inventado',request_key='cashea-ajuste-invalido')
        self.request('cashea-settings',values,status=400)
        data=self.order_data(total='40',initial_received='1600',initial_currency='VES',initial_percent='40')
        data['preview_hash']=self.request('cashea-preview',data)['preview_hash']
        self.request('confirm-rate',dict(rate_date=local_today().isoformat(),rate='200',rate_change_confirmed=True))
        self.request('cashea-order',data,status=400)
        self.assertTrue(self.request('cashea-preview',data)['initial_warning'])


if __name__=='__main__':unittest.main()
