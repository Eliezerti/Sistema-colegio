"""Isolated finance rules: no customer database or production route is exercised."""
import unittest
from colegio.income_rules import (Account,Movement,IncomeError,destination,suggested_account,
    proposals,allocation_plan,cash_deposit,equivalents,parse_csv,reference)


class IncomeRulesTests(unittest.TestCase):
    def setUp(self):
        self.bank=Account(1,'Banco ficticio USD','USD',bank='Ejemplo',last4='0042')
        self.cash=Account(2,'Caja efectivo USD','USD',kind='cash')
        self.profile=dict(columns=dict(date='Fecha',amount='Monto',reference='Referencia',description='Concepto'))

    def movement(self,id,amount=1000,reference='000123',on='2026-10-10',**extra):
        return Movement(id,extra.pop('account',1),on,amount,extra.pop('currency','USD'),reference,**extra)

    def test_account_minimal_data_method_currency_and_safe_suggestions(self):
        with self.assertRaises(IncomeError):Account(3,'Cuenta','USD',last4='01020000000000000000')
        self.assertEqual(destination(self.cash,'USD','Efectivo'),2)
        for a,c,m in ((self.bank,'USD','Efectivo'),(self.cash,'USD','Transferencia'),(self.bank,'VES','Transferencia')):
            with self.assertRaises(IncomeError):destination(a,c,m)
        self.assertIsNone(suggested_account([self.bank,self.cash],'USD','Transferencia'))
        self.assertEqual(suggested_account([self.bank,self.cash],'USD','Transferencia',1),1)
        self.assertEqual(suggested_account([self.bank,self.cash],'USD','Efectivo'),2)
        self.assertIsNone(suggested_account([self.cash,Account(3,'Otra caja','USD',kind='cash')],'USD','Efectivo'))
        self.assertFalse(Account(4,'Desactivada','USD',active=False).active)
        with self.assertRaises(IncomeError):destination(Account(4,'Desactivada','USD',active=False),'USD','Transferencia')

    def test_unique_exact_leading_zeros_tolerance_and_no_implicit_currency_conversion(self):
        self.assertEqual(reference(' 000-123 '),'123');self.assertEqual(reference('AB001'),'AB001')
        b=self.movement('b');l=self.movement('l',reference='123',on='2026-10-13')
        self.assertTrue(proposals([b],[l])[0]['unique'])
        for row in (self.movement('l',on='2026-10-14'),self.movement('l',currency='VES'),self.movement('l',account=3),self.movement('l',amount=999),self.movement('l',direction='debit'),self.movement('l',reference='')):
            self.assertFalse(proposals([b],[row])[0]['unique'])

    def test_competing_candidates_on_either_side_are_never_automatic(self):
        b=self.movement('b');l=self.movement('l')
        self.assertFalse(proposals([b],[l,self.movement('l2')])[0]['unique'])
        self.assertTrue(all(not r['unique'] for r in proposals([b,self.movement('b2')],[l])))
        with self.assertRaises(IncomeError):proposals([b,b],[l])
        with self.assertRaises(IncomeError):proposals([b],[l],tolerance_days=True)

    def test_many_to_one_one_to_many_and_previous_partial_coverage(self):
        result=allocation_plan([self.movement('b',3000)],[self.movement('r1',1000),self.movement('r2',2000)],[('b','r1',1000),('b','r2',2000)])
        self.assertEqual(result['bank_remaining'],{'b':0});self.assertEqual(sum(result['ledger_remaining'].values()),0)
        result=allocation_plan([self.movement('b1',1000),self.movement('b2',2000)],[self.movement('r',3000)],[('b1','r',1000),('b2','r',2000)])
        self.assertEqual(result['ledger_remaining'],{'r':0})
        with self.assertRaises(IncomeError):allocation_plan([self.movement('b')],[self.movement('r')],[('b','r',800)],already_bank={'b':300})
        with self.assertRaises(IncomeError):allocation_plan([self.movement('b')],[self.movement('r')],[('b','r',500),('b','r',500)])
        with self.assertRaises(IncomeError):allocation_plan([self.movement('b')],[self.movement('r',currency='VES')],[('b','r',100)])
        with self.assertRaises(IncomeError):allocation_plan([self.movement('b')],[self.movement('r')],[],already_bank={'b':-1})

    def test_cash_deposit_difference_double_coverage_and_original_currency(self):
        rows=[(1,1000,1000,'USD','Efectivo'),(2,500,1000,'USD','Efectivo')]
        self.assertEqual(cash_deposit(self.bank,1500,rows,currency='USD')['difference'],0)
        with self.assertRaises(IncomeError):cash_deposit(self.bank,1499,rows,currency='USD')
        self.assertEqual(cash_deposit(self.bank,1499,rows,currency='USD',reason='Diferencia ficticia a revisar')['difference'],-1)
        for invalid in ([(1,1001,1000,'USD','Efectivo')],rows+rows,[(1,100,100,'USD','Transferencia')],[(1,100,100,'VES','Efectivo')],[]):
            with self.assertRaises(IncomeError):cash_deposit(self.bank,1500,invalid,currency='USD')

    def test_historical_bcv_exact_rounding_and_invalid_values(self):
        self.assertEqual(equivalents(10000,'USD','875.125'),dict(usd=10000,ves=8751250))
        self.assertEqual(equivalents(8751250,'VES','875.125'),dict(usd=10000,ves=8751250))
        self.assertEqual(equivalents(1,'USD','1.5')['ves'],2)
        for rate in (None,True,'NaN','Infinity','0','-1','0.1234567','1000000001'):
            with self.assertRaises(IncomeError):equivalents(1,'VES',rate)
        for value in (True,0,-1,1.2):
            with self.assertRaises(IncomeError):equivalents(value,'USD','100')

    def test_csv_mapping_hash_original_reference_tildes_signed_amounts_and_ambiguous_duplicates(self):
        raw=('Fecha;Monto;Referencia;Concepto\n2026-10-10;10.01;000123;Mensualidad ñ\n2026-10-11;-2.00;0042;Débito\n').encode('utf-8-sig')
        data=parse_csv(raw,self.profile,self.bank)
        self.assertEqual(len(data['file_sha256']),64)
        self.assertEqual(data['rows'][0]['movement'].reference,'000123')
        self.assertEqual(data['rows'][0]['movement'].amount,1001)
        self.assertEqual(data['rows'][1]['movement'].direction,'debit')
        self.assertEqual(data['rows'][1]['description'],'Débito')
        duplicated=raw+raw.decode('utf-8-sig').splitlines()[1].encode()+b'\n'
        self.assertEqual(len(parse_csv(duplicated,self.profile,self.bank)['duplicates']),1)
        self.assertEqual(parse_csv(raw,self.profile,self.bank)['file_sha256'],data['file_sha256'])
        other=Account(4,'Otro banco','USD')
        self.assertNotEqual(data['rows'][0]['fingerprint'],parse_csv(raw,self.profile,other)['rows'][0]['fingerprint'])

    def test_csv_invalid_amounts_dates_headers_mapping_and_corruption(self):
        for raw in (b'',b'Fecha;Monto;Referencia;Concepto\n',b'Fecha;Monto;Referencia;Concepto\n2026-02-30;10;001;X\n',
                    b'Fecha;Monto;Referencia;Concepto\n2026-10-10;1,000.00;001;X\n',b'Fecha;Monto;Referencia;Concepto\n2026-10-10;NaN;001;X\n',
                    b'Fecha;Monto;Referencia;Concepto\n2026-10-10;1.001;001;X\n',b'Fecha;Monto;Referencia;Concepto\n2026-10-10;0;001;X\n',
                    b'Fecha;Monto;Referencia;Concepto\n2026-10-10;10;001\n',b'Fecha;Monto;Monto;Concepto\n',b'\xff\xfe',b'x'*2000001):
            with self.subTest(raw=raw[:100]),self.assertRaises(IncomeError):parse_csv(raw,self.profile,self.bank)
        with self.assertRaises(IncomeError):parse_csv(b'x',dict(columns={}),self.bank)
        with self.assertRaises(IncomeError):parse_csv(b'x',self.profile,self.cash)

    def test_csv_decimal_comma_and_bank_ids_never_guesses_layout(self):
        profile=dict(self.profile,decimal=',',date_format='%d/%m/%Y')
        raw='Fecha;Monto;Referencia;Concepto\n10/10/2026;10,25;0001;Aporte\n'.encode()
        self.assertEqual(parse_csv(raw,profile,self.bank)['rows'][0]['movement'].amount,1025)
        profile=dict(self.profile,columns=dict(self.profile['columns'],bank_id='ID'))
        raw=b'Fecha;Monto;Referencia;Concepto;ID\n2026-10-10;10;001;Aporte;A\n2026-10-10;10;001;Aporte;A\n'
        with self.assertRaisesRegex(IncomeError,'identificador bancario repetido'):parse_csv(raw,profile,self.bank)

    def test_800_students_twelve_months_candidate_index(self):
        ledger=[self.movement('r'+str(n),reference=str(n+1)) for n in range(800*12)]
        bank=[self.movement('b'+str(n),reference=str(n+1)) for n in range(800*12)]
        result=proposals(bank,ledger)
        self.assertEqual(len(result),9600);self.assertTrue(all(r['unique'] for r in result))

    def workbook(self,rows,*,numeric_reference=False,formula=False,epoch1904=False,external=False):
        import io,zipfile
        from xml.sax.saxutils import escape
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><workbookPr date1904="'+str(int(epoch1904))+'"/><sheets><sheet name="Extracto ficticio" sheetId="1" r:id="rId1"/></sheets></workbook>')
            z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"'+(' TargetMode="External"' if external else '')+'/></Relationships>')
            xml=['<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
            for n,row in enumerate([['Fecha','Monto','Referencia','Concepto']]+rows,1):
                xml.append('<row r="'+str(n)+'">')
                for c,value in enumerate(row):
                    ref=chr(65+c)+str(n)
                    if n>1 and (c in (0,1) and isinstance(value,(int,float)) or c==2 and numeric_reference):
                        xml.append('<c r="'+ref+'"><v>'+str(value)+'</v></c>')
                    else:xml.append('<c r="'+ref+'" t="inlineStr"><is><t>'+escape(str(value))+'</t></is>'+('<f>1+1</f>' if formula and n>1 and c==1 else '')+'</c>')
                xml.append('</row>')
            xml.append('</sheetData></worksheet>')
            z.writestr('xl/worksheets/sheet1.xml',''.join(xml))
        return output.getvalue()

    def test_xlsx_actual_import_text_ids_numeric_amount_date_and_hash(self):
        import hashlib
        from colegio.income_rules import parse_statement
        raw=self.workbook([['2026-10-10',10.25,'000123','Mensualidad ñ']])
        result=parse_statement(raw,'ficticio.xlsx',self.profile,self.bank)
        self.assertEqual(result['file_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['rows'][0]['movement'].reference,'000123')
        self.assertEqual(result['rows'][0]['movement'].amount,1025)
        for epoch in (False,True):
            from datetime import date
            serial=(date(2026,10,10)-(date(1904,1,1) if epoch else date(1899,12,30))).days
            raw=self.workbook([[serial,10.25,'000123','Débito ficticio']],epoch1904=epoch)
            result=parse_statement(raw,'ficticio.xlsx',dict(self.profile,decimal=','),self.bank)
            self.assertEqual(result['rows'][0]['movement'].on,'2026-10-10')
            self.assertEqual(result['rows'][0]['movement'].amount,1025)

    def test_xlsx_formulas_external_links_numeric_references_corruption_and_xml_entities_rejected(self):
        from colegio.income_rules import parse_statement
        rows=[['2026-10-10','10','000123','Ficticio']]
        for options in (dict(formula=True),dict(external=True),dict(numeric_reference=True)):
            with self.subTest(options=options),self.assertRaises(IncomeError):parse_statement(self.workbook(rows,**options),'x.xlsx',self.profile,self.bank)
        for raw,name in ((b'not a zip','x.xlsx'),(b'x','x.xls'),(b'x','x.xlsm'),(b'x','x.exe')):
            with self.assertRaises(IncomeError):parse_statement(raw,name,self.profile,self.bank)
        import io,zipfile
        original=self.workbook(rows);out=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(original)) as source,zipfile.ZipFile(out,'w') as target:
            for name in source.namelist():
                data=source.read(name)
                if name.endswith('sheet1.xml'):data=b'<!DOCTYPE x [<!ENTITY a "X">]>'+data
                target.writestr(name,data)
        with self.assertRaises(IncomeError):parse_statement(out.getvalue(),'x.xlsx',self.profile,self.bank)

    def test_ambiguous_candidate_limit_preserves_global_uniqueness_and_counts(self):
        ledger=[self.movement('r'+str(n)) for n in range(800*12)]
        bank=[self.movement('b'+str(n)) for n in range(800*12)]
        result=proposals(bank,ledger)
        self.assertEqual(result[0]['candidate_count'],9600)
        self.assertEqual(len(result[0]['candidates']),50)
        self.assertTrue(result[0]['candidates_truncated'])
        self.assertTrue(all(not r['unique'] for r in result))
        # A single-candidate bank row must not steal an entry that also belongs
        # to a different ambiguous row; the truncated list must not hide rivalry.
        ledger=[self.movement('r1',on='2026-10-07'),self.movement('r2',on='2026-10-13')]
        bank=[self.movement('b1',on='2026-10-04'),self.movement('b2',on='2026-10-10')]
        self.assertTrue(all(not r['unique'] for r in proposals(bank,ledger)))

    def test_account_full_numbers_hidden_in_names_are_rejected(self):
        for data in (dict(name='Cuenta 0102-0000-0000-0000-0000'),dict(name='Cuenta',bank='0102 0000 0000 0000 0000')):
            with self.assertRaises(IncomeError):Account(3,currency='USD',**data)
