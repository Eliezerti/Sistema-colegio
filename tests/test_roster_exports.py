"""Export/import round trips use fictional records and isolated SQLite files."""
import base64
import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from colegio.administration import EXPORT_COLUMNS, export_roster, parse_import
from colegio.db import ValidationError, connect, initialize, local_today
from colegio.documents import load_document
from colegio.server import mutate, snapshot


class RosterExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.user={'id':1,'name':'Administración de prueba','role':'admin'}
        self.source=self.database('source');self.target=self.database('target')
        self.month=local_today().strftime('%Y-%m')
        self.year=local_today().year-(local_today().month<9)
        for db in (self.source,self.target):
            db.execute('UPDATE settings SET value=? WHERE key=?',(str(self.year),'school_year'))
        grade=mutate(self.source,'grades',{'name':'Primero A','capacity':30},self.user)['id']
        guardian=mutate(self.source,'guardians',{'name':'+Representante de prueba',
            'document':'V-12345678','phone':'+584121234567','email':'ana@example.test',
            'address':"'=Dirección literal"},self.user)['id']
        common={'guardian_id':guardian,'grade_id':grade,'monthly_fee':'125.50','discount':10,
            'school_year':self.year,'enrollment_start':f'{self.year}-09-01',
            'enrollment_end':f'{self.year+1}-08-31','billing_start':self.month,'birth_date':'',
            'notes':"'Observación de prueba"}
        self.active=mutate(self.source,'students',dict(common,name='A Alumno activo',status='active'),
                           self.user,import_code='AL-000045')['id']
        mutate(self.source,'students',dict(common,name='B Alumno inactivo',status='inactive',document='V-9876543'),
               self.user,import_code='AL-000001')
        archived_guardian=mutate(self.source,'guardians',{'name':'Representante archivado','document':'V-555'},self.user)['id']
        mutate(self.source,'students',dict(common,name='C Alumno archivado',guardian_id=archived_guardian,status='inactive'),
               self.user,import_code='AL-000046',import_archived=True)
        self.source.execute('UPDATE guardians SET archived=1 WHERE id=?',(archived_guardian,))
        self.source.commit();self.target.commit()

    def database(self,name):
        path=Path(self.temp.name)/f'{name}.sqlite3';initialize(path);db=connect(path)
        self.addCleanup(db.close)
        db.execute("INSERT INTO users(id,username,name,password,role) VALUES(1,'test','Prueba','unused','admin')")
        db.commit();return db

    def payload(self,raw,extension):
        return {'filename':f'students.{extension}','content':base64.b64encode(raw).decode()}

    def import_data(self,payload,commit=True):
        preview=mutate(self.target,'import-roster',dict(payload,preview=True),self.user)
        if not commit:return preview
        self.assertEqual(preview['errors'],[])
        return mutate(self.target,'import-roster',dict(payload,confirmed_hash=preview['hash'],
                       confirmed_month=preview['billing_default']),self.user)

    def test_csv_and_excel_preserve_roster_codes_fees_dates_contacts_and_archive_states(self):
        source=snapshot(self.source,self.user)
        for extension in ('csv','xlsx'):
            with self.subTest(extension=extension):
                self.target=self.database('target-'+extension)
                self.target.execute('UPDATE settings SET value=? WHERE key=?',(str(self.year),'school_year'))
                payload=self.payload(export_roster(source,extension=='xlsx'),extension)
                preview=self.import_data(payload,False)
                self.assertEqual(preview['errors'],[]);self.assertEqual(preview['grades'],1)
                self.assertEqual(preview['students'],3);self.assertEqual(preview['guardians'],2)
                self.assertEqual(snapshot(self.target,self.user)['students'],[])
                self.assertEqual(snapshot(self.target,self.user)['grades'],[])
                self.import_data(payload);target=snapshot(self.target,self.user)
                for a,b in zip(source['students'],target['students']):
                    for field in ('name','document','student_code','birth_date','monthly_fee','discount',
                                  'school_year','enrollment_start','enrollment_end','billing_start','status','notes','archived'):
                        self.assertEqual(a[field],b[field],field)
                for a,b in zip(source['guardians'],target['guardians']):
                    for field in ('name','document','phone','email','address','archived'):
                        self.assertEqual(a[field],b[field],field)
                self.assertEqual(target['grades'][0]['capacity'],30)
                self.assertEqual(len(target['charges']),1)
                self.assertEqual(target['charges'][0]['amount'],11295)
                for enrollment in target['enrollments']:
                    doc=load_document(self.target,'enrollment',enrollment['id'])
                    student=next(s for s in target['students'] if s['id']==enrollment['student_id'])
                    self.assertEqual(doc['student']['student_code'],student['student_code'])
                duplicate=self.import_data(payload,False);self.assertTrue(duplicate['errors'])
                self.assertEqual(len(snapshot(self.target,self.user)['students']),3)

    def test_exported_saldo_is_informative_and_never_creates_payments(self):
        mutate(self.source,'payments',{'student_id':self.active,'amount':'10','currency':'USD',
               'paid_on':local_today().isoformat(),'method':'Efectivo','request_key':'roster-export-test'},self.user)
        source=snapshot(self.source,self.user)
        preview=self.import_data(self.payload(export_roster(source),'csv'),False)
        self.assertEqual(preview['source_balance'],source['students'][0]['balance'])
        self.assertEqual(preview['new_balance'],preview['source_balance']+1000)
        self.import_data(self.payload(export_roster(source),'csv'))
        self.assertEqual(snapshot(self.target,self.user)['payments'],[])
        # A accumulated balance can exceed the limit for a single charge.
        rows=list(csv.reader(io.StringIO(export_roster(source).decode('utf-8-sig')),delimiter=';'))
        rows[1][-1]='2000000000.00';out=io.StringIO();csv.writer(out,delimiter=';').writerows(rows)
        other=self.database('large-reference');previous=self.target;self.target=other
        preview=self.import_data(self.payload(out.getvalue().encode(),'csv'),False)
        self.assertEqual(preview['errors'],[]);self.assertEqual(preview['source_balance'],200000000000)
        self.assertEqual(preview['new_balance'],11295);self.target=previous

    def test_invalid_batch_rolls_back_auto_created_grades_and_guardians(self):
        raw=export_roster(snapshot(self.source,self.user)).decode('utf-8-sig')
        rows=list(csv.reader(io.StringIO(raw),delimiter=';'));rows[2][17]=rows[1][17]
        out=io.StringIO();csv.writer(out,delimiter=';').writerows(rows)
        payload=self.payload(out.getvalue().encode(),'csv');preview=self.import_data(payload,False)
        self.assertTrue(preview['errors'])
        with self.assertRaises(ValidationError):
            mutate(self.target,'import-roster',dict(payload,confirmed_hash=preview['hash'],confirmed_month=preview['billing_default']),self.user)
        state=snapshot(self.target,self.user)
        for field in ('students','guardians','grades','charges','enrollments'):
            self.assertEqual(state[field],[],field)

    def test_existing_grade_capacity_is_not_silently_overwritten(self):
        mutate(self.target,'grades',{'name':'Primero A','capacity':1},self.user)
        preview=self.import_data(self.payload(export_roster(snapshot(self.source,self.user)),'csv'),False)
        self.assertEqual(preview['errors'],[])
        self.assertEqual(preview['grades'],0)
        self.assertEqual(snapshot(self.target,self.user)['grades'][0]['capacity'],1)

    def test_conflicting_parent_archive_states_block_the_entire_batch(self):
        rows=list(csv.reader(io.StringIO(export_roster(snapshot(self.source,self.user)).decode('utf-8-sig')),delimiter=';'))
        rows[2][19:21]=['1','1']
        out=io.StringIO();csv.writer(out,delimiter=';').writerows(rows)
        payload=self.payload(out.getvalue().encode(),'csv');preview=self.import_data(payload,False)
        self.assertEqual(len(preview['errors']),1)
        self.assertIn('representante tiene estados',preview['errors'][0]['message'])
        with self.assertRaises(ValidationError):
            mutate(self.target,'import-roster',dict(payload,confirmed_hash=preview['hash'],confirmed_month=preview['billing_default']),self.user)
        state=snapshot(self.target,self.user)
        self.assertEqual(state['students'],[]);self.assertEqual(state['guardians'],[]);self.assertEqual(state['grades'],[])

    def test_old_nine_column_listing_reports_missing_data_without_guessing_a_fee(self):
        raw='Alumno;Codigo;Documento;Grado;Ano escolar;Representante;Telefono;Estado;Saldo USD\n'
        raw+='Alumno;AL-000001;AL-000001;Primero;2026;Representante;04121234567;active;200.00\n'
        with self.assertRaisesRegex(ValidationError,'listado antiguo de 9 columnas'):
            self.import_data(self.payload(raw.encode(),'csv'),False)
        self.assertEqual(snapshot(self.target,self.user)['students'],[])

    def test_excel_cells_remain_text_and_csv_formula_protection_is_reversible(self):
        state=snapshot(self.source,self.user)
        excel=export_roster(state,True)
        with zipfile.ZipFile(io.BytesIO(excel)) as z:
            sheet=z.read('xl/worksheets/sheet1.xml')
            self.assertIn(b'+584121234567',sheet);self.assertNotIn(b'<f>',sheet)
        records,_=parse_import(self.payload(excel,'xlsx'))
        self.assertEqual(records[0]['representante_nombre'],'+Representante de prueba')
        raw=export_roster(state);self.assertEqual(next(csv.reader(io.StringIO(raw.decode('utf-8-sig')),delimiter=';')),list(EXPORT_COLUMNS))
        self.assertIn(b"'+584121234567",raw)
        records,_=parse_import(self.payload(raw,'csv'))
        self.assertEqual(records[0]['representante_direccion'],"'=Dirección literal")
        self.assertEqual(records[0]['observaciones'],"'Observación de prueba")

    def test_legacy_unknown_birth_and_maximum_literal_note_can_be_reimported(self):
        self.source.execute("UPDATE students SET birth_date='0001-01-01', notes=? WHERE id=?",("'"+'x'*1999,self.active))
        state=snapshot(self.source,self.user)
        for extension in ('csv','xlsx'):
            payload=self.payload(export_roster(state,extension=='xlsx'),extension)
            records,_=parse_import(payload)
            self.assertEqual(records[0]['nacimiento'],'')
            self.assertEqual(len(records[0]['observaciones']),2000)
            self.assertEqual(self.import_data(payload,False)['errors'],[])


if __name__=='__main__':unittest.main()
