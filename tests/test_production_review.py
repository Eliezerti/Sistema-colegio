import base64
import csv
import io
import json
import struct
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

from colegio.administration import COLUMNS, import_template, parse_import
from colegio.branding import pdf_logo
from colegio.db import ValidationError, connect, initialize, record_payment, charges, synchronize_monthly_charges
from colegio.documents import render_pdf
from colegio.maintenance import review_database
from colegio.reset_password import list_administrators
from colegio.server import mutate


def png(red=30,green=100,blue=70,alpha=255):
    def chunk(kind,payload):
        return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
    raw=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(bytes([0,red,green,blue,alpha])))+chunk(b'IEND',b'')
    return 'data:image/png;base64,'+base64.b64encode(raw).decode()


class ProductionReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.path=Path(self.temp.name)/'colegio.sqlite3'
        initialize(self.path);self.db=connect(self.path);self.user={'id':1,'role':'admin'}
        with self.db:
            self.db.execute("INSERT INTO users VALUES(1,'director','Directora','unused','admin')")
            self.db.execute("INSERT INTO guardians(id,name,document) VALUES(1,'Ana','V-123')")
            self.db.execute("INSERT INTO grades VALUES(1,'Primaria A',30)")
            self.db.execute("""INSERT INTO students(id,name,document,student_code,birth_date,guardian_id,grade_id,school_year,
                monthly_fee,discount,status,enrollment_start,enrollment_end)
                VALUES(1,'Sofía','AL-000001','AL-000001','2015-01-01',1,1,2020,10000,0,'active','2020-09-01','2020-10-31')""")
            synchronize_monthly_charges(self.db)

    def tearDown(self): self.db.close();self.temp.cleanup()

    def pay(self,value,key,currency='USD'):
        with self.db:
            return record_payment(self.db,{'student_id':1,'amount':value,'request_key':key,'currency':currency,
                'paid_on':'2020-10-20','method':'Efectivo'},1)['id']

    def test_partial_then_complete_receipts_freeze_balances_and_allocation_details(self):
        first=self.pay('30','partial');original=self.db.execute('SELECT receipt_snapshot FROM payments WHERE id=?',(first,)).fetchone()[0]
        frozen=json.loads(original)
        self.assertEqual((frozen['balance_before'],frozen['balance_after'],frozen['payment_status']),(20000,17000,'partial'))
        self.assertEqual((frozen['allocations'][0]['balance_before'],frozen['allocations'][0]['balance_after']),(10000,7000))
        final=self.pay('170','complete');f=json.loads(self.db.execute('SELECT receipt_snapshot FROM payments WHERE id=?',(final,)).fetchone()[0])
        self.assertEqual((f['balance_before'],f['balance_after'],f['payment_status']),(17000,0,'complete'))
        self.assertEqual(sum(c['balance'] for c in charges(self.db)),0)
        self.assertEqual(self.db.execute('SELECT receipt_snapshot FROM payments WHERE id=?',(first,)).fetchone()[0],original)
        self.assertTrue(review_database(self.db)['ok'])
        self.db.commit()
        for paper in ('half-letter','a4','ticket-80','ticket-58'):
            payment=dict(self.db.execute('SELECT * FROM payments WHERE id=?',(first,)).fetchone(),**frozen['person'],
                balance_before=frozen['balance_before'],balance_after=frozen['balance_after'],operator=frozen['operator'])
            pdf=render_pdf('receipt',{'payment':payment,'settings':frozen['school'],'allocations':frozen['allocations']},paper)
            self.assertIn(b'ABONO',pdf);self.assertIn(b'USD 170,00',pdf)
            if paper=='half-letter':self.assertIn(b'/Count 1 ',pdf)

    def test_ves_rounding_retry_and_rollback_conserve_the_ledger(self):
        with self.db:self.db.execute("INSERT INTO exchange_rates VALUES('2020-10-20','3.2','test')")
        first=self.pay('0.08','round','VES') # USD .025 rounds to .03, half up.
        self.assertEqual(self.db.execute('SELECT amount FROM payments WHERE id=?',(first,)).fetchone()[0],3)
        self.assertEqual(self.pay('0.08','round','VES'),first)
        with self.assertRaises(ValidationError):self.pay('1000','excess')
        self.assertEqual(sum(c['balance'] for c in charges(self.db)),19997)
        with self.assertRaises(RuntimeError),self.db:
            record_payment(self.db,{'student_id':1,'amount':'10','request_key':'rollback','paid_on':'2020-10-20','method':'Efectivo'},1)
            raise RuntimeError('Simulated failure before commit')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM payments').fetchone()[0],1)
        self.assertTrue(review_database(self.db)['ok'])

    def test_review_detects_unallocated_payment_without_modifying_any_record(self):
        payment=self.pay('10','review')
        with self.db:self.db.execute('DELETE FROM allocations WHERE payment_id=?',(payment,))
        before=self.db.total_changes;review=review_database(self.db)
        self.assertFalse(review['ok']);self.assertEqual(before,self.db.total_changes)
        self.assertIn('aplicaciones',review['errors'][0])

    def test_calendar_change_is_rejected_for_registered_enrollments(self):
        with self.assertRaises(ValidationError),self.db:
            mutate(self.db,'settings',{'school_name':'Colegio','school_year':2020,'start_month':8,'due_day':10},self.user)
        self.assertEqual(self.db.execute("SELECT value FROM settings WHERE key='start_month'").fetchone()[0],'9')
        self.assertEqual(len(charges(self.db)),2)

    def test_new_school_is_generic_and_existing_branding_survives_upgrade(self):
        settings=dict(self.db.execute('SELECT key,value FROM settings'))
        self.assertEqual(settings['school_name'],'Mi colegio');self.assertEqual(settings['rif'],'');self.assertEqual(settings['logo'],'')
        with self.db:
            mutate(self.db,'settings',{'school_name':'Colegio personalizado','school_year':2020,'start_month':9,'due_day':10,
                'legal_name':'Colegio personalizado, C.A.','logo':png()},self.user)
            self.db.execute('PRAGMA user_version=7')
        initialize(self.path)
        after=dict(self.db.execute('SELECT key,value FROM settings'))
        self.assertEqual(after['logo'],png());self.assertEqual(after['school_name'],'Colegio personalizado')
        self.assertEqual(len(charges(self.db)),2)

    def test_custom_logo_embeds_rgb_and_refuses_bad_images(self):
        width,height,stream=pdf_logo(png(alpha=0))
        self.assertEqual((width,height),(1,1));self.assertEqual(zlib.decompress(stream),b'\0\xff\xff\xff')
        with self.assertRaises(ValueError):pdf_logo('data:image/png;base64,AAAA')
        with self.assertRaises(ValidationError),self.db:
            mutate(self.db,'settings',{'school_name':'Colegio','school_year':2020,'start_month':9,'due_day':10,'logo':'https://other/logo.png'},self.user)

    def test_upgrade_of_another_legacy_school_never_assigns_humboldt_identity(self):
        with self.db:
            self.db.execute("UPDATE settings SET value='Otro colegio' WHERE key='school_name'")
            self.db.execute("UPDATE settings SET value='J-12345678-9' WHERE key='rif'")
            self.db.execute('PRAGMA user_version=3')
        initialize(self.path)
        profile=dict(self.db.execute('SELECT key,value FROM settings'))
        self.assertEqual(profile['school_name'],'Otro colegio')
        self.assertEqual(profile['rif'],'J-12345678-9')
        self.assertEqual(profile['logo'],'');self.assertEqual(profile['legal_name'],'')

    def test_template_has_empty_import_sheet_and_separate_instructions_examples_grades(self):
        raw=import_template(True,['Primaria A'],{'school_year':'2026','start_month':'9'})
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertEqual(z.read('xl/worksheets/sheet1.xml').count(b'<row '),1)
            self.assertIn(b'Instrucciones',z.read('xl/workbook.xml'))
            self.assertIn(b'representante_cedula',z.read('xl/worksheets/sheet2.xml'))
            self.assertIn(b'Primaria A',z.read('xl/worksheets/sheet4.xml'))
        with self.assertRaises(ValidationError):parse_import({'filename':'empty.xlsx','content':base64.b64encode(raw).decode()})

    def test_import_accepts_local_formats_and_keeps_error_row_numbers(self):
        defaults=['Beatriz','V-999','04120001111','','','Mateo','','23/04/2016','Primaria A','2020','100,50','10','01/09/2020','31/08/2021','activo','','2020-09']
        out=io.StringIO();writer=csv.writer(out,delimiter=';');writer.writerow(COLUMNS);writer.writerow(['']*len(COLUMNS));writer.writerow(defaults)
        data={'filename':'students.csv','content':base64.b64encode(out.getvalue().encode()).decode(),'preview':True}
        with self.db:result=mutate(self.db,'import-roster',data,self.user)
        self.assertEqual(result['errors'],[]);self.assertEqual(result['lines'][0]['row'],3)
        data['content']=base64.b64encode(out.getvalue().replace('100,50','$100').encode()).decode()
        with self.db:result=mutate(self.db,'import-roster',data,self.user)
        self.assertEqual(result['errors'][0]['row'],3);self.assertIn('mensualidad_usd',result['errors'][0]['message'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM students').fetchone()[0],1)

    def test_local_recovery_lists_names_without_revealing_passwords(self):
        self.assertEqual(list_administrators(self.path.parent),[{'username':'director','name':'Directora'}])


if __name__=='__main__':unittest.main()
