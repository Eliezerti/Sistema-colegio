import re
import unittest
from colegio.branding import SCHOOL_PROFILE
from colegio.documents import render_pdf


def document(currency='VES', rows=1, voided=False, notes=''):
    return {'settings':dict(SCHOOL_PROFILE,school_name='Colegio'), 'payment':{
        'id':31,'paid_on':'2026-10-06','guardian_name':'Ana Pérez','guardian_document':'V-12345678',
        'guardian_phone':'04121234567','guardian_address':'','student_name':'Sofía Pérez',
        'student_code':'AL-000001','student_document':'AL-000001','currency':currency,
        'received_amount':rows*100000 if currency=='VES' else rows*1000,'amount':rows*1000,
        'exchange_rate':'100','method':'Transferencia','reference':'TR-001','operator':'Administración',
        'voided':voided,'void_reason':'Corrección del pago' if voided else '', 'notes':notes},
        'allocations':[{'concept':f'Mensualidad detalle {i:02d}','period':'2026-09','amount':1000} for i in range(rows)]}


class ReceiptLayoutTests(unittest.TestCase):
    def test_manual_charge_period_is_printed_without_treating_it_as_a_date(self):
        data=document()
        data['allocations'][0]['period']='Inscripcion inicial'
        pdf=render_pdf('receipt',data)
        self.assertTrue(b'Inscripcion inicial' in pdf,'El texto del periodo manual debe conservarse')

    def test_regular_receipts_keep_money_and_signatures_on_one_portrait_page(self):
        for currency in ('USD','VES'):
            with self.subTest(currency=currency):
                pdf=render_pdf('receipt',document(currency))
                self.assertTrue(b'/MediaBox [0 0 595 842]' in pdf,'El recibo debe usar A4 vertical')
                self.assertTrue(b'/FontFile2' in pdf,'El PDF debe incorporar la tipografía')
                self.assertIn(b'/Count 1 ',pdf)
                self.assertIn(b'USD 10,00',pdf)
                if currency=='VES':
                    self.assertIn(b'Bs 1.000,00',pdf)
                    self.assertIn(b'Tasa BCV aplicada: Bs 100 por USD',pdf)
                else:
                    self.assertNotIn(b'Tasa BCV aplicada:',pdf)
                self.assertIn(b'Firma de administraci',pdf)
                self.assertIn(b'Firma del representante',pdf)

    def test_long_voided_receipt_repeats_status_and_keeps_all_rows_and_notes(self):
        notes=('Observaciones de un pago con muchos conceptos. '*40)+'\nFIN DE OBSERVACIONES'
        pdf=render_pdf('receipt',document(rows=40,voided=True,notes=notes))
        pages=int(re.search(rb'/Count (\d+)',pdf).group(1))
        self.assertGreater(pages,1)
        for i in range(40):
            self.assertTrue(f'Mensualidad detalle {i:02d}'.encode() in pdf,f'Falta el concepto {i}')
        self.assertTrue(b'FIN DE OBSERVACIONES' in pdf,'Las observaciones finales deben conservarse')
        self.assertIn(b'Bs 40.000,00',pdf)
        self.assertIn(b'USD 400,00',pdf)
        self.assertGreaterEqual(pdf.count(b'(ANULADO)'),pages)
        self.assertGreater(pdf.count(b'(DESCRIPCI'),1)
        self.assertEqual(pdf.count(b'(R-000031)'),pages)
        self.assertIn(b'Firma del representante',pdf)


if __name__=='__main__':
    unittest.main()
