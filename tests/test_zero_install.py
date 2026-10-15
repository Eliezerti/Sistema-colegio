"""An installation must contain no preloaded business rows, identity or users."""
import io
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path
from colegio.db import initialize,connect,next_record_id
from colegio.server import open_school
from colegio.administration import import_template
from tests.zero_install import assert_empty_database,SEQUENCES


class ZeroInstallTests(unittest.TestCase):
    def test_first_open_and_reopen_are_empty_and_have_no_default_user(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'colegio.sqlite3'
            for _ in range(2):
                with open_school(path,0):assert_empty_database(path)
            with closing(connect(path)) as db:
                for table in SEQUENCES:self.assertEqual(next_record_id(db,table),1)

    def test_first_actual_student_receipt_and_expense_start_at_one(self):
        from tests.test_system import SystemTests
        f=SystemTests();f.setUp()
        try:
            self.assertEqual(f.student,1)
            self.assertEqual(f.request('payments',f.payment())['id'],1)
            from colegio.db import local_today
            self.assertEqual(f.request('expenses',dict(concept='Gasto temporal',category='Operación',
                spent_on=local_today().isoformat(),amount='1',currency='USD',method='Efectivo'))['id'],1)
            f.request('setup',dict(name='Otro',username='otro',password='Clave-ficticia-2026'),status=400)
        finally:f.tearDown()

    def test_download_template_has_no_example_rows_or_people(self):
        with zipfile.ZipFile(io.BytesIO(import_template(True))) as archive:
            self.assertEqual(archive.read('xl/worksheets/sheet1.xml').count(b'<row '),1)
            self.assertNotIn(b'Ejemplos',archive.read('xl/workbook.xml'))
            for name in archive.namelist():
                raw=archive.read(name)
                for text in (b'Luis P',b'Ana P',b'HUMBOLDT',b'50835934'):
                    self.assertNotIn(text,raw)

    def test_bundle_recipe_has_no_database_or_retired_guide(self):
        root=Path(__file__).resolve().parents[1]
        spec=(root/'packaging/Aula.spec').read_text()
        self.assertNotIn('fixtures',spec)
        self.assertNotIn('sqlite3',spec)
        self.assertFalse((root/'docs/privilegios-personal.html').exists())
        for name in ('salary.py','staff_access.py','reset_records.py'):
            self.assertFalse((root/'colegio'/name).exists())
