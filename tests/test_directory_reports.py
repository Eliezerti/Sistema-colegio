import re
import unittest

from colegio.db import ValidationError
from colegio.directory_reports import directory_pdf, directory_report


def directory_state():
    return {'settings': {'school_name': 'Colegio de prueba', 'legal_name': 'Colegio de Prueba, C.A.',
                         'rif': 'J-12345678-9', 'fiscal_address': 'Calle de prueba'},
            'today': '2026-10-10', 'user': {'name': 'Administración'},
            'grades': [{'id': 1, 'name': 'Primero A'}, {'id': 2, 'name': 'Segundo A'}],
            'students': [dict(id=i, name=name, document=f'V-{i}', student_code=f'AL-{i:06d}',
                guardian_name='Ana Pérez', guardian_id=1, grade_id=grade, grade_name='Primero A',
                school_year=2026, monthly_fee=10000, discount=10, billing_start='2026-10',
                enrollment_start='2026-09-01', status='active', archived=archived, balance=9000)
                for i, name, grade, archived in [(1, 'Alumno Uno', 1, 0), (2, 'Alumno Dos', 2, 0),
                                                (3, 'Alumno Archivado', 1, 1)]],
            'guardians': [dict(id=1, name='Ana Pérez', document='V-123', phone='04121234567',
                              email='ana@example.test', address='Dirección de prueba', archived=0)],
            'employees': [dict(id=1, name='Docente Uno', document='V-456', phone='04129876543',
                position='Docente', bank='Banco de prueba', bank_account='01020000000012345678',
                salary=12000, status='active')]}


class DirectoryReportsTests(unittest.TestCase):
    def test_filter_matches_visible_directory_and_keeps_exact_discounted_amounts(self):
        data = directory_state()
        report = directory_report(data, 'students', {'search': ['ana pérez'], 'grade': ['1']})
        self.assertEqual(report['count'], 1)
        self.assertEqual(report['lines'][0][4], 'USD 90,00')
        self.assertEqual(report['lines'][0][5], 'OCT. 2026')
        self.assertEqual(report['lines'][0][-1], 'USD 90,00')
        self.assertEqual(directory_report(data, 'students', {'archived': ['1']})['count'], 3)
        self.assertEqual(directory_report(data, 'students', {'search': ['AL-000002']})['count'], 1)
        self.assertEqual(directory_report(data, 'students', {'search': ['inexistente']})['count'], 0)
        self.assertEqual(directory_report(data, 'employees', {'search': ['docente']})['count'], 1)
        self.assertEqual(data['students'][0]['monthly_fee'], 10000)

    def test_guardian_children_and_employee_bank_account_keep_all_digits(self):
        data = directory_state()
        guardian = directory_report(data, 'guardians', {})
        self.assertIn('Alumno Archivado · Primero A (archivado)', guardian['lines'][0][-1])
        employee = directory_report(data, 'employees', {})
        self.assertIn('01020000000012345678', employee['lines'][0][4])
        self.assertEqual(employee['lines'][0][5], 'USD 120,00')
        for kind in ('students', 'guardians', 'employees'):
            report = directory_report(data, kind, {})
            self.assertEqual(sum(report['widths']), 758)
            self.assertEqual(len(report['headings']), len(report['lines'][0]))
            pdf = directory_pdf(report)
            self.assertTrue(pdf.startswith(b'%PDF-1.4'))
            self.assertIn(b'/MediaBox [0 0 842 595]', pdf)
            self.assertIn(b'/FontFile2', pdf)
            self.assertIn(b'J-12345678-9', pdf)

    def test_multipage_pdf_preserves_every_student_and_repeats_headers(self):
        data = directory_state()
        base = data['students'][0]
        data['students'] = [dict(base, id=i, name=f'Alumno {i:04d}', student_code=f'AL-{i:06d}')
                            for i in range(150)]
        pdf = directory_pdf(directory_report(data, 'students', {}))
        pages = int(re.search(rb'/Count (\d+)', pdf).group(1))
        self.assertGreater(pages, 1)
        self.assertEqual(pdf.count(b'(Alumno / c'), pages)
        for i in range(150):
            self.assertIn(f'AL-{i:06d}'.encode(), pdf)
        self.assertIn(b'Generado por:', pdf)

    def test_single_large_guardian_row_can_continue_without_losing_linked_children(self):
        data = directory_state()
        base = data['students'][0]
        data['students'] = [dict(base, id=i, name=f'Hijo {i:04d}') for i in range(150)]
        pdf = directory_pdf(directory_report(data, 'guardians', {}))
        self.assertGreater(int(re.search(rb'/Count (\d+)', pdf).group(1)), 1)
        for i in range(150):
            self.assertIn(f'Hijo {i:04d}'.encode(), pdf)

    def test_bad_filters_rejected_and_empty_list_is_a_real_document(self):
        data = directory_state()
        for kind, query in [('unknown', {}), ('students', {'grade': ['999']}),
                            ('students', {'archived': ['yes']}), ('students', {'search': ['a'*201]}),
                            ('guardians', {'grade': ['1']})]:
            with self.subTest(kind=kind, query=query), self.assertRaises(ValidationError):
                directory_report(data, kind, query)
        pdf = directory_pdf(directory_report(data, 'students', {'search': ['inexistente']}))
        self.assertIn(b'No hay registros', pdf)


if __name__ == '__main__':
    unittest.main()
