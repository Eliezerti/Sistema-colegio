"""Geometry and template validation without UI, schema or numbering side effects."""
import base64
import copy
import json
import re
import unittest
from colegio.db import ValidationError
from colegio.invoice_layout import example_template,validate,profile,render,sample,paper_preset,parse_json,point,MM


class InvoiceLayoutTests(unittest.TestCase):
    def setUp(self):
        self.layout=example_template();self.data=sample()
        self.items=[dict(concepto=self.data['concepto'],cantidad='1',precio='100,00',exento='100,00',total='100,00')]

    def test_example_is_unpersisted_uncalibrated_and_exact_portrait_half_letter(self):
        before=copy.deepcopy(self.layout);result=render(self.layout,self.data,self.items)
        self.assertFalse(self.layout['calibrated']);self.assertEqual(self.layout,before)
        self.assertAlmostEqual(result['width_pt'],396);self.assertAlmostEqual(result['height_pt'],612)
        self.assertIn(b'/MediaBox [0 0 396 612]',result['pdf'])
        self.assertEqual(len(re.findall(rb'/Type /Page\b',result['pdf'])),1)
        # X/Y locate the containing box; the text has font-safe internal space.
        self.assertIn(b'1 0 0 1 30.346457 572.853543 Tm (01/01/2026)',result['pdf'])
        self.assertNotIn(b'/Scan',result['pdf'])

    def test_letter_top_and_bottom_keep_size_rotation_and_half_page(self):
        for preset,base_y in (('carta_arriba',396),('carta_abajo',0)):
            with self.subTest(preset=preset):
                self.layout['paper']=paper_preset(preset)
                result=render(self.layout,self.data,self.items)
                self.assertIn(b'/MediaBox [0 0 612 792]',result['pdf'])
                self.assertIn(('q 1 0 0 1 0 '+str(base_y)+' cm').encode(),result['pdf'])
                self.assertIn(b'0 -1 1 0 0 396 cm',result['pdf'])
                corners=next(row['corners_mm'] for row in result['placements'] if row['id']=='fecha')
                self.assertAlmostEqual(corners[0][0],205.9)
                self.assertAlmostEqual(corners[0][1],10+(139.7 if preset.endswith('abajo') else 0))
                self.assertTrue(all(0<=y<=(139.7 if preset.endswith('arriba') else 279.4) for row in result['placements'] for _,y in row['corners_mm']))
                self.assertEqual(len(re.findall(rb'/Type /Page\b',result['pdf'])),1)

    def test_printer_offsets_scale_and_margin_are_explicit_not_auto_fit(self):
        printer=dict(name='Impresora ficticia',x_tenths=10,y_tenths=-10,scale=1,margin_mm=5)
        result=render(self.layout,self.data,self.items,printer)
        self.assertIn(b'q 1 0 0 1 2.834646 2.834646 cm',result['pdf'])
        self.assertEqual(point(self.layout['paper'],profile(printer),10,10),(11,9))
        printer['scale']=.99;result=render(self.layout,self.data,self.items,printer)
        self.assertIn(b'q 0.99 0 0 0.99',result['pdf'])
        printer['x_tenths']=-100
        with self.assertRaisesRegex(ValidationError,'margen imprimible'):render(self.layout,self.data,self.items,printer)

    def test_bad_variables_json_types_duplicate_keys_and_unknown_options_are_rejected(self):
        for value in ('{alumno}','{cliente.__class__}','{cliente!r}','{total:.2f}','{mes'):
            with self.subTest(value=value):
                t=copy.deepcopy(self.layout);t['fields'][0].update(kind='text',text=value)
                with self.assertRaises(ValidationError):validate(t)
        valid=parse_json(json.dumps(self.layout,ensure_ascii=False));self.assertEqual(valid,validate(self.layout))
        with self.assertRaises(ValidationError):parse_json('{"format":"a","format":"b"}')
        for key,value in (('calibrated',1),('grid_mm',float('nan')),('version',True),('script','alert(1)')):
            with self.subTest(key=key):
                t=copy.deepcopy(self.layout);t[key]=value
                with self.assertRaises(ValidationError):validate(t)

    def test_long_text_never_truncates_and_shrink_has_a_legible_floor(self):
        f=self.layout['fields'][0];f.update(kind='text',text='Texto de prueba',width_mm=8,height_mm=3,overflow='error')
        with self.assertRaisesRegex(ValidationError,'no cabe'):render(self.layout,self.data,self.items)
        f.update(width_mm=30,height_mm=5,overflow='shrink',text='Texto de prueba',size_pt=16)
        result=render(self.layout,self.data,self.items);size=result['placements'][0]['size_pt'];self.assertGreaterEqual(size,6);self.assertLess(size,16)
        f.update(max_chars=3)
        with self.assertRaisesRegex(ValidationError,'demasiado largo'):render(self.layout,self.data,self.items)
        f.update(max_chars=300,text='W'*200,width_mm=1,height_mm=2,overflow='shrink')
        with self.assertRaisesRegex(ValidationError,'no cabe'):render(self.layout,self.data,self.items)

    def test_detail_overflow_bad_margin_and_impossible_orientation_stop_printing(self):
        with self.assertRaisesRegex(ValidationError,'más conceptos'):render(self.layout,self.data,self.items*7)
        self.items[0]['concepto']='W'*1000
        with self.assertRaisesRegex(ValidationError,'no cabe'):render(self.layout,self.data,self.items)
        self.layout['fields'][0]['x_mm']=4
        with self.assertRaisesRegex(ValidationError,'margen'):validate(self.layout)
        self.layout=example_template();self.layout['paper']['placement']='top'
        with self.assertRaises(ValidationError):validate(self.layout)
        self.layout['paper']=paper_preset('carta_arriba');self.layout['paper']['rotation']=0
        with self.assertRaisesRegex(ValidationError,'no cabe'):validate(self.layout)

    def test_n_tildes_custom_variables_and_styles_survive_pdf_encoding(self):
        self.data['cliente']='Muñoz Peña Álvarez'
        self.layout['fields'][0].update(kind='text',text='Mes: {mes}; año: {año}',bold=True,italic=True,font='mono',width_mm=100,height_mm=12,uppercase=True)
        result=render(self.layout,self.data,self.items)
        self.assertIn(b'/F8 10 Tf',result['pdf']);self.assertIn(b'\\361',result['pdf']);self.assertIn(b'\\301',result['pdf'])
        self.assertIn(b'MES: ENERO; A',result['pdf'])
        self.assertEqual(result['pdf'],render(self.layout,self.data,self.items)['pdf'])

    def test_scan_can_only_be_embedded_in_a_calibration_test(self):
        from colegio.branding import logo_bytes,LOGO_FILE
        self.layout['background']='data:image/png;base64,'+base64.b64encode(logo_bytes(LOGO_FILE)).decode()
        emitted=render(self.layout,self.data,self.items,include_background=True)
        self.assertNotIn(b'/Scan',emitted['pdf'])
        calibration=render(self.layout,self.data,self.items,calibration=True,include_background=True)
        self.assertIn(b'/Scan',calibration['pdf']);self.assertIn(b'NO CONSUME',calibration['pdf'])
        self.assertNotEqual(emitted['pdf'],calibration['pdf'])
        self.assertEqual(emitted['pdf'],render(self.layout,self.data,self.items)['pdf'])
