import re
import unittest
from colegio.branding import SCHOOL_PROFILE
from colegio.documents import render_pdf, receipt_student_details


def document(currency='VES', rows=1, voided=False, notes=''):
    return {'settings':dict(SCHOOL_PROFILE,school_name='Colegio'), 'payment':{
        'id':31,'paid_on':'2026-10-06','guardian_name':'Ana Pérez','guardian_document':'V-12345678',
        'guardian_phone':'04121234567','guardian_address':'','student_name':'Sofía Pérez',
        'student_code':'AL-000001','student_document':'AL-000001','grade_name':'Primero / A','currency':currency,
        'received_amount':rows*100000 if currency=='VES' else rows*1000,'amount':rows*1000,
        'exchange_rate':'100','method':'Transferencia','reference':'TR-001','operator':'Administración',
        'voided':voided,'void_reason':'Corrección del pago' if voided else '', 'notes':notes},
        'allocations':[{'concept':f'Mensualidad detalle {i:02d}','period':'2026-09','amount':1000} for i in range(rows)]}


class ReceiptLayoutTests(unittest.TestCase):
    def test_student_document_and_internal_code_are_never_printed_in_any_receipt_format(self):
        for code in ('AL-000001', None, ''):
            for paper in ('a4', 'half-letter', 'letter-pair', 'ticket-58', 'ticket-80'):
                with self.subTest(code=code, paper=paper):
                    data = document()
                    data['payment']['student_document'] = 'CE-199998887771'
                    data['payment']['student_code'] = code
                    pdf = render_pdf('receipt', data, paper)
                    self.assertNotIn(b'CE-199998887771', pdf)
                    self.assertIn(b'V-12345678', pdf, 'Se conserva la identificación del representante')
                    self.assertNotIn(b'AL-000001', pdf)
                    self.assertNotIn(b'interno no registrado', pdf)
                    self.assertIn(b'R-000031', pdf)
                    self.assertIn(b'USD 10,00', pdf)

    def test_legacy_receipt_without_internal_code_does_not_substitute_school_document(self):
        data = document()
        data['payment'].pop('student_code')
        data['payment']['student_document'] = 'CE-199998887771'
        original = dict(data['payment'])
        name, detail = receipt_student_details(data['payment'])
        self.assertEqual(name, 'Sofía Pérez · Primero / A')
        self.assertEqual(detail, '')
        for paper in ('a4', 'half-letter', 'ticket-58', 'ticket-80'):
            with self.subTest(paper=paper):
                self.assertNotIn(b'CE-199998887771', render_pdf('receipt', data, paper))
        self.assertEqual(data['payment'], original, 'No se modifica la información histórica')

    def test_missing_grade_keeps_an_honest_hint_without_school_identifiers(self):
        data = document()
        data['payment'].pop('grade_name')
        name, detail = receipt_student_details(data['payment'])
        self.assertEqual(name, 'Sofía Pérez')
        self.assertEqual(detail, 'Grado no registrado')
        for paper in ('a4', 'half-letter', 'ticket-58', 'ticket-80'):
            with self.subTest(paper=paper):
                pdf = render_pdf('receipt', data, paper)
                self.assertIn(b'Grado no registrado', pdf)
                self.assertNotIn(b'AL-000001', pdf)
                self.assertIn(b'R-000031', pdf)

    def test_half_letter_has_true_half_sheet_dimensions_and_complete_single_page(self):
        for currency in ('USD','VES'):
            with self.subTest(currency=currency):
                data=document(currency)
                data['payment']['guardian_address']='Calle 48, sector Centro, Barquismeto.'
                pdf=render_pdf('receipt',data,'half-letter')
                for value in (b'/MediaBox [0 0 396 612]',b'/Count 1 ',b'USD 10,00',
                              b'Firma del representante',b'Registrado por:',b'RIF: J-50835934-8'):
                    self.assertTrue(value in pdf,f'Falta en el recibo media carta: {value!r}')

    def test_default_half_letter_keeps_three_concepts_balance_reference_and_notes_on_one_page(self):
        for currency in ('USD', 'VES'):
            data = document(currency, rows=3, notes='Pago ficticio para revisión de impresión.')
            data['payment'].update(balance_before=8000, balance_after=5000,
                                   guardian_address='Calle 48, sector Centro, Barquismeto.')
            pdf = render_pdf('receipt', data)
            self.assertIn(b'/MediaBox [0 0 396 612]', pdf)
            self.assertIn(b'/Count 1 ', pdf)
            for value in (b'R-000031', b'Ana', b'Primero / A', b'TR-001',
                          b'USD 30,00', b'USD 50,00', b'Firma del representante'):
                self.assertIn(value, pdf)
            for row in data['allocations']:
                self.assertIn(row['concept'].encode(), pdf)
            self.assertNotIn(b'AL-000001', pdf)

    def test_half_letter_continuations_preserve_all_concepts_status_and_money(self):
        pdf=render_pdf('receipt',document(rows=40,voided=True,notes='FIN DE OBSERVACIONES'),'half-letter')
        pages=int(re.search(rb'/Count (\d+)',pdf).group(1))
        self.assertGreater(pages,1)
        for i in range(40):
            self.assertTrue(f'Mensualidad detalle {i:02d}'.encode() in pdf,f'Falta el concepto {i}')
        for value in (b'FIN DE OBSERVACIONES',b'USD 400,00',b'Firma del representante'):
            self.assertTrue(value in pdf,f'Falta información: {value!r}')
        self.assertEqual(pdf.count(b'/MediaBox [0 0 396 612]'),pages)
        self.assertEqual(pdf.count(b'(ANULADO)'),pages)

    def test_letter_pair_keeps_two_complete_unscaled_copies_without_mutating_document(self):
        import copy
        data = document(rows=3, notes='Pago ficticio para ambas copias.')
        data['payment'].update(balance_before=8000, balance_after=5000)
        before = copy.deepcopy(data)
        pdf = render_pdf('receipt', data, 'letter-pair')
        self.assertIn(b'/MediaBox [0 0 792 612]', pdf)
        self.assertIn(b'/Count 1 ', pdf)
        self.assertIn(b'q 1 0 0 1 396 0 cm', pdf)
        self.assertEqual(pdf.count(b'ORIGINAL'),1)
        self.assertEqual(pdf.count(b'COPIA'),1)
        for text in (b'(R-000031)', b'(TR-001)', b'(Firma del representante)'):
            self.assertEqual(pdf.count(text), 2)
        for row in data['allocations']:
            self.assertEqual(pdf.count(row['concept'].encode()), 2)
        self.assertEqual(data, before)

    def test_letter_pair_continues_without_dropping_long_receipt_details(self):
        data = document(rows=40, voided=True, notes='FIN DE AMBAS COPIAS')
        pdf = render_pdf('receipt', data, 'letter-pair')
        self.assertGreater(int(re.search(rb'/Count (\d+)', pdf).group(1)), 1)
        for row in data['allocations']:
            self.assertEqual(pdf.count(row['concept'].encode()), 2)
        self.assertEqual(pdf.count(b'FIN DE AMBAS COPIAS'), 2)

    def test_manual_charge_period_is_printed_without_treating_it_as_a_date(self):
        data=document()
        data['allocations'][0]['period']='Inscripcion inicial'
        pdf=render_pdf('receipt',data)
        self.assertTrue(b'Inscripcion inicial' in pdf,'El texto del periodo manual debe conservarse')

    def test_regular_receipts_keep_money_and_signatures_on_one_portrait_page(self):
        for currency in ('USD','VES'):
            with self.subTest(currency=currency):
                pdf=render_pdf('receipt',document(currency),'a4')
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
        pdf=render_pdf('receipt',document(rows=40,voided=True,notes=notes),'a4')
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
