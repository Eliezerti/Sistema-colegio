"""Exercise real corrections and directory removal against isolated financial data."""
import base64
import csv
import io
import json
import unittest
from datetime import date

from colegio.administration import COLUMNS
from colegio.db import ValidationError, charges, generate_month, initialize, synchronize_monthly_charges
from colegio.documents import load_document, school_birth_date, school_month, render_pdf
from colegio.lifecycle import roster_for_year
from colegio.maintenance import review_database
from colegio.server import mutate, snapshot


class StudentAdminTests(unittest.TestCase):
    def setUp(self):
        from tests.test_billing_start import BillingStartTests
        BillingStartTests.setUp(self)

    def student(self, **overrides):
        from tests.test_billing_start import BillingStartTests
        return BillingStartTests.student(self, **overrides)

    def correction(self, sid, **overrides):
        row = self.db.execute('SELECT * FROM students WHERE id=?', (sid,)).fetchone()
        data = {'id':sid, 'billing_start':'2026-10', 'previous_start':row['billing_start'],
                'reason':'Inscripción de octubre; septiembre se cargó por error', 'confirmed':True,
                'charge_ids':sorted(c['id'] for c in charges(self.db,sid) if c['period']=='2026-09')}
        data.update(overrides)
        with self.db:
            return mutate(self.db,'correct-billing-start',data,self.user)

    def directory(self, endpoint, sid, **overrides):
        data = {'id':sid, 'reason':'Corrección del directorio',
                'confirmation':'RECUPERAR' if endpoint.startswith('restore-') else 'ELIMINAR' if endpoint=='delete-grade' else 'ARCHIVAR'}
        data.update(overrides)
        with self.db:
            return mutate(self.db,endpoint,data,self.user)

    def test_unknown_birth_and_document_formatting(self):
        created = self.student(birth_date='')
        doc = load_document(self.db,'enrollment',created['document_id'])
        self.assertEqual(doc['student']['birth_date'],'')
        self.assertEqual(school_birth_date(''),'Pendiente')
        self.assertEqual(school_birth_date('0001-01-01'),'Pendiente')
        self.assertEqual(school_birth_date('2015-04-23'),'23 ABR. 2015')
        self.assertEqual(school_month('2026-10'),'OCT. 2026')
        self.assertTrue(render_pdf('enrollment',doc).startswith(b'%PDF'))
        for birth in ('0001-01-01','1800-01-01','2027-01-01','bad'):
            with self.assertRaises(ValidationError):
                self.student(birth_date=birth)

    def test_import_can_leave_birth_empty(self):
        row = ['Ana','V-123','','','','Importado','','','Primaria A','2026','100','10','','','activo','','']
        output = io.StringIO();writer=csv.writer(output,delimiter=';')
        writer.writerow(COLUMNS);writer.writerow(row)
        data={'filename':'alumnos.csv','content':base64.b64encode(output.getvalue().encode()).decode(),'preview':True}
        with self.db:
            result=mutate(self.db,'import-roster',data,self.user)
        self.assertEqual(result['errors'],[])
        data.update(preview=False,confirmed_hash=result['hash'],confirmed_month=result['billing_default'])
        with self.db:
            mutate(self.db,'import-roster',data,self.user)
        self.assertEqual(self.db.execute('SELECT birth_date FROM students').fetchone()[0],'')

    def test_correct_september_to_october_without_recreating_cancelled_debt(self):
        created = self.student(billing_start='2026-09')
        old_doc = load_document(self.db,'enrollment',created['document_id'])
        result = self.correction(created['id'])
        self.assertEqual(result['cancelled'],1)
        self.assertEqual([(c['period'],c['amount']) for c in charges(self.db)], [('2026-10',9000),('2026-11',9000)])
        self.assertEqual(self.db.execute("SELECT cancelled FROM charges WHERE period='2026-09'").fetchone()[0],1)
        self.assertEqual(load_document(self.db,'enrollment',created['document_id']),old_doc)
        self.assertEqual(load_document(self.db,'enrollment',result['document_id'])['student']['billing_start'],'2026-10')
        initialize(self.path)
        with self.db:
            synchronize_monthly_charges(self.db)
            self.assertEqual(generate_month(self.db,{'period':'2026-09','school_year':2026},1)['created'],0)
        self.assertEqual(len(charges(self.db)),2)
        entry=self.db.execute("SELECT details FROM audit WHERE action='cancel-charge'").fetchone()
        self.assertIn('octubre',json.loads(entry[0])['reason'])
        self.assertTrue(review_database(self.db)['ok'])

    def test_partial_payment_blocks_correction_without_changing_money(self):
        created=self.student(billing_start='2026-09')
        with self.db:
            mutate(self.db,'payments',{'student_id':created['id'],'amount':'10','currency':'USD',
                'paid_on':'2026-11-15','method':'Efectivo','request_key':'admin-payment'},self.user)
        before=[dict(r) for r in self.db.execute('SELECT * FROM payments')]
        ledger=charges(self.db)
        with self.assertRaisesRegex(ValidationError,'pagos aplicados'):
            self.correction(created['id'])
        self.assertEqual(charges(self.db),ledger)
        self.assertEqual([dict(r) for r in self.db.execute('SELECT * FROM payments')],before)
        self.assertEqual(self.db.execute('SELECT billing_start FROM students').fetchone()[0],'2026-09')

    def test_correction_also_works_after_regular_edit_restored_october(self):
        created=self.student(billing_start='2026-09')
        # A regular profile edit preserves previous charges, so September remains.
        self.student(id=created['id'],billing_start='2026-10')
        self.assertEqual(len(charges(self.db)),3)
        self.correction(created['id'],billing_start='2026-10')
        self.assertEqual([c['period'] for c in charges(self.db)],['2026-10','2026-11'])

    def test_active_agreement_blocks_correction(self):
        created=self.student(billing_start='2026-09')
        # Use the normal agreement workflow, against the fixed November clock.
        from unittest.mock import patch
        with patch('colegio.lifecycle.local_today',return_value=date(2026,11,15)), self.db:
            total=sum(c['balance'] for c in charges(self.db) if c['overdue'])
            mutate(self.db,'payment-plans',{'student_id':created['id'],'expected_total':total,
                'installments':[{'amount':f'{total/100:.2f}','due_date':'2026-12-15'}]},self.user)
        with self.assertRaisesRegex(ValidationError,'convenio'):
            self.correction(created['id'])
        self.assertEqual(len(charges(self.db)),3)

    def test_stale_or_unconfirmed_correction_is_rejected(self):
        created=self.student(billing_start='2026-09')
        for data in ({'charge_ids':[]},{'previous_start':'2026-08'},{'confirmed':False},{'billing_start':'2026-09'}, {'reason':''}):
            with self.assertRaises(ValidationError):
                self.correction(created['id'],**data)
        self.assertEqual(len(charges(self.db)),3)

    def test_archive_keeps_money_documents_and_stops_new_months(self):
        created=self.student(billing_start='2026-09')
        with self.db:
            mutate(self.db,'payments',{'student_id':created['id'],'amount':'10','currency':'USD',
                'paid_on':'2026-11-15','method':'Efectivo','request_key':'archive-payment'},self.user)
        before=charges(self.db)
        payments=[dict(r) for r in self.db.execute('SELECT * FROM payments')]
        doc=load_document(self.db,'enrollment',created['document_id'])
        self.directory('archive-student',created['id'])
        row=self.db.execute('SELECT * FROM students').fetchone()
        self.assertEqual((row['archived'],row['status']),(1,'inactive'))
        with self.db:
            synchronize_monthly_charges(self.db,date(2026,12,15))
        self.assertEqual(charges(self.db),before)
        self.assertEqual([dict(r) for r in self.db.execute('SELECT * FROM payments')],payments)
        self.assertEqual(load_document(self.db,'enrollment',created['document_id']),doc)
        self.assertEqual(roster_for_year(self.db,2026)['students'],[])
        self.assertGreater(snapshot(self.db,self.user)['students'][0]['balance'],0)
        self.directory('restore-student',created['id'])
        self.assertEqual(tuple(self.db.execute('SELECT archived,status FROM students').fetchone()),(0,'inactive'))
        self.assertTrue(review_database(self.db)['ok'])

    def test_representative_in_use_is_protected_and_can_be_restored(self):
        created=self.student()
        with self.assertRaisesRegex(ValidationError,'alumnos vinculados'):
            self.directory('archive-guardian',1)
        self.directory('archive-student',created['id'])
        self.directory('archive-guardian',1)
        with self.assertRaises(ValidationError):
            self.student(name='Nuevo hermano')
        self.directory('restore-student',created['id'])
        with self.assertRaises(ValidationError):
            self.student(id=created['id'],status='active')
        self.directory('restore-guardian',1)
        self.student(id=created['id'],status='active')
        self.assertEqual(self.db.execute('SELECT archived FROM guardians').fetchone()[0],0)

    def test_new_previous_month_requires_confirmation(self):
        created=self.student()
        with self.assertRaisesRegex(ValidationError,'confirma expresamente'):
            self.student(id=created['id'],billing_start='2026-09')
        self.assertEqual(len(charges(self.db)),1)
        self.student(id=created['id'],billing_start='2026-09',billing_change_confirmed=True)
        self.assertEqual(len(charges(self.db)),3)

    def test_admin_only_and_confirmation_required(self):
        created=self.student()
        for endpoint in ('archive-student','archive-guardian','restore-student','restore-guardian','delete-grade','correct-billing-start'):
            for role in ('cashier','reader'):
                with self.assertRaises(PermissionError), self.db:
                    mutate(self.db,endpoint,{'id':created['id']},{'id':1,'role':role})
        for data in ({'confirmation':''},{'reason':''}):
            with self.assertRaises(ValidationError):
                self.directory('archive-student',created['id'],**data)
        self.assertEqual(self.db.execute('SELECT archived FROM students').fetchone()[0],0)

    def test_delete_unused_grade_and_protect_linked_grade(self):
        with self.db:
            extra=mutate(self.db,'grades',{'name':'Sobrante','capacity':30},self.user)['id']
        self.directory('delete-grade',extra)
        self.assertIsNone(self.db.execute('SELECT * FROM grades WHERE id=?',(extra,)).fetchone())
        created=self.student()
        with self.assertRaisesRegex(ValidationError,'alumnos vinculados'):
            self.directory('delete-grade',1)
        self.directory('archive-student',created['id'])
        with self.assertRaises(ValidationError):
            self.directory('delete-grade',1)

    def test_schema_nine_upgrade_preserves_existing_records(self):
        self.student(billing_start='2026-09')
        before=charges(self.db)
        with self.db:
            self.db.execute('ALTER TABLE students DROP COLUMN archived')
            self.db.execute('ALTER TABLE guardians DROP COLUMN archived')
            self.db.execute('PRAGMA user_version=9')
        initialize(self.path)
        self.assertEqual(charges(self.db),before)
        self.assertEqual(self.db.execute('SELECT archived FROM students').fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT archived FROM guardians').fetchone()[0],0)
