"""First billed month is independent of academic dates and preserves recorded money."""
import base64
import csv
import io
import tempfile
import unittest
import zipfile
from contextlib import ExitStack
from datetime import date
from pathlib import Path
from unittest.mock import patch

from colegio.administration import COLUMNS, LEGACY_COLUMNS, import_template
from colegio.db import ValidationError, charges, connect, generate_month, initialize, synchronize_monthly_charges
from colegio.documents import load_document
from colegio.server import mutate


class BillingStartTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'colegio.sqlite3'
        initialize(self.path)
        self.db = connect(self.path)
        self.addCleanup(self.db.close)
        self.clock = ExitStack()
        self.addCleanup(self.clock.close)
        for module in ('db','server','administration'):
            self.clock.enter_context(patch('colegio.' + module + '.local_today', return_value=date(2026,11,15)))
        self.user = {'id':1,'role':'admin'}
        with self.db:
            self.db.execute("INSERT INTO users VALUES(1,'admin','Administración','unused','admin')")
            self.db.execute("INSERT INTO guardians(id,name,document) VALUES(1,'Ana','V-123')")
            self.db.execute("INSERT INTO grades VALUES(1,'Primaria A',30)")

    def student(self, **overrides):
        data = {'name':'Sofía','document':'','birth_date':'2015-01-01','guardian_id':1,'grade_id':1,
                'school_year':2026,'monthly_fee':'100','discount':'10','status':'active',
                'enrollment_start':'2026-09-01','enrollment_end':'2027-08-31'}
        data.update(overrides)
        with self.db:
            return mutate(self.db,'students',data,self.user)

    def test_november_registration_does_not_charge_september_or_october(self):
        created = self.student()
        self.assertEqual(created['billing_start'],'2026-11')
        self.assertEqual([(c['period'],c['amount']) for c in charges(self.db)], [('2026-11',9000)])
        with self.db:
            for period in ('2026-09','2026-10'):
                self.assertEqual(generate_month(self.db,{'period':period,'school_year':2026},1)['created'],0)
            self.assertEqual(synchronize_monthly_charges(self.db,date(2026,12,1))['created'],1)
        self.assertEqual([c['period'] for c in charges(self.db)],['2026-11','2026-12'])

    def test_academic_reference_dates_can_be_omitted(self):
        created = self.student(enrollment_start='',enrollment_end='')
        row = dict(self.db.execute('SELECT * FROM students').fetchone())
        self.assertEqual((row['enrollment_start'],row['enrollment_end']),('2026-09-01','2027-08-31'))
        self.assertEqual(created['billing_start'],'2026-11')

    def test_explicit_earlier_month_and_future_month(self):
        first = self.student(billing_start='2026-09')
        second = self.student(name='Hermano',billing_start='2026-12')
        self.assertEqual([c['period'] for c in charges(self.db,first['id'])],['2026-09','2026-10','2026-11'])
        self.assertEqual(charges(self.db,second['id']),[])
        with self.db:
            self.assertEqual(generate_month(self.db,{'period':'2026-11','school_year':2026},1)['created'],0)
            synchronize_monthly_charges(self.db,date(2026,12,1))
        self.assertEqual([c['period'] for c in charges(self.db,second['id'])],['2026-12'])

    def test_editing_preserves_previous_charges_receipts_and_saved_documents(self):
        created = self.student(billing_start='2026-09')
        with self.db:
            receipt = mutate(self.db,'payments',{'student_id':created['id'],'currency':'USD','amount':'10',
                'paid_on':'2026-11-15','method':'Efectivo','request_key':'first-billing-test'},self.user)
        prior = dict(self.db.execute('SELECT * FROM payments').fetchone())
        ledger = charges(self.db)
        enrollment = load_document(self.db,'enrollment',created['document_id'])
        self.student(id=created['id'],billing_start='2026-11')
        self.assertEqual(charges(self.db),ledger)
        self.assertEqual(dict(self.db.execute('SELECT * FROM payments').fetchone()),prior)
        self.assertEqual(load_document(self.db,'enrollment',created['document_id']),enrollment)
        self.assertEqual(enrollment['student']['billing_start'],'2026-09')
        self.assertTrue(receipt['id'])

    def test_invalid_or_outside_month_is_rejected_without_records(self):
        for period in ('2026-13','2026-1','2026-11-01','2026-08','2027-09'):
            with self.assertRaises(ValidationError):
                self.student(billing_start=period)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM students').fetchone()[0],0)
        self.assertEqual(charges(self.db),[])

    def test_schema_upgrade_keeps_original_boundary_and_money(self):
        self.student(billing_start='2026-09')
        ledger = charges(self.db)
        with self.db:
            self.db.execute('ALTER TABLE students DROP COLUMN billing_start')
            self.db.execute('PRAGMA user_version=8')
        initialize(self.path)
        self.assertEqual(self.db.execute('SELECT billing_start FROM students').fetchone()[0],'2026-09')
        self.assertEqual(charges(self.db),ledger)
        with self.db:
            self.assertEqual(synchronize_monthly_charges(self.db)['created'],0)

    def test_import_new_and_legacy_templates_default_to_loading_month(self):
        row = ['Ana','V-123','','','','Importado','','2015-01-01','Primaria A','2026',
               '100','10','2026-09-01','2027-08-31','activo','']
        for headers,tail,expected in ((LEGACY_COLUMNS,[],'2026-11'),(COLUMNS,[''],'2026-11'),
                                     (COLUMNS,['2026-10'],'2026-10')):
            out = io.StringIO()
            writer = csv.writer(out,delimiter=';');writer.writerow(headers);writer.writerow(row+tail)
            data = {'filename':'alumnos.csv','content':base64.b64encode(out.getvalue().encode()).decode(),'preview':True}
            with self.db:
                result = mutate(self.db,'import-roster',data,self.user)
            self.assertEqual(result['errors'],[])
            self.assertEqual(result['lines'][0]['billing_start'],expected)
            self.assertEqual(result['new_balance'],9000 if expected=='2026-11' else 18000)
            self.assertEqual(self.db.execute('SELECT COUNT(*) FROM students').fetchone()[0],0)
            data.update(preview=False,confirmed_hash=result['hash'],confirmed_month=result['billing_default'])
            with self.db:
                saved = mutate(self.db,'import-roster',data,self.user)
            self.assertEqual(saved['lines'][0]['billing_start'],expected)
            self.assertTrue(all(c['period']>=expected for c in charges(self.db)))
            # Start the next format from the same empty fixture, without altering real data.
            with self.db:
                self.db.execute('DELETE FROM enrollment_documents')
                self.db.execute('DELETE FROM monthly_assessments')
                self.db.execute('DELETE FROM charges')
                self.db.execute('DELETE FROM students')

    def test_legacy_excel_and_numeric_first_billing_month(self):
        from xml.etree import ElementTree as ET
        raw=import_template(True,['Primaria A'],{'school_year':'2026','start_month':'9'})
        ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            files={name:archive.read(name) for name in archive.namelist()}
        for legacy in (True,False):
            sheet=ET.fromstring(files['xl/worksheets/sheet1.xml'])
            data=sheet.find(ns+'sheetData')
            if legacy:
                header=data.find(ns+'row')
                header.remove(header[-1])
            row=ET.SubElement(data,ns+'row',{'r':'2'})
            values=['Ana','V-123','','','','Excel','','2015-01-01','Primaria A','2026',
                    '100','10','2026-09-01','2027-08-31','activo','']
            for i,value in enumerate(values):
                cell=ET.SubElement(row,ns+'c',{'r':chr(65+i)+'2','t':'inlineStr'})
                ET.SubElement(ET.SubElement(cell,ns+'is'),ns+'t').text=value
            if not legacy:
                cell=ET.SubElement(row,ns+'c',{'r':'Q2'})
                ET.SubElement(cell,ns+'v').text=str((date(2026,11,1)-date(1899,12,30)).days)
            out=io.BytesIO()
            with zipfile.ZipFile(out,'w') as archive:
                for name,payload in files.items():
                    archive.writestr(name,ET.tostring(sheet) if name=='xl/worksheets/sheet1.xml' else payload)
            with self.db:
                result=mutate(self.db,'import-roster',{'filename':'alumnos.xlsx','content':base64.b64encode(out.getvalue()).decode(),'preview':True},self.user)
            self.assertEqual(result['errors'],[])
            self.assertEqual(result['new_balance'],9000)
            self.assertEqual(result['lines'][0]['billing_start'],'2026-11')

    def test_import_review_expires_when_calendar_month_changes(self):
        out=io.StringIO();writer=csv.writer(out,delimiter=';');writer.writerow(LEGACY_COLUMNS)
        writer.writerow(['Ana','V-123','','','','Importado','','2015-01-01','Primaria A','2026',
                         '100','0','2026-09-01','2027-08-31','activo',''])
        data={'filename':'alumnos.csv','content':base64.b64encode(out.getvalue().encode()).decode(),'preview':True}
        with self.db:
            preview=mutate(self.db,'import-roster',data,self.user)
        data.update(preview=False,confirmed_hash=preview['hash'],confirmed_month=preview['billing_default'])
        with patch('colegio.administration.local_today',return_value=date(2026,12,1)):
            with self.assertRaises(ValidationError):
                with self.db:mutate(self.db,'import-roster',data,self.user)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM students').fetchone()[0],0)


if __name__ == '__main__':
    unittest.main()
