"""Independent PDF parser/rasterizer checks. Test-only pypdf and PyMuPDF."""
import copy
import io
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fitz
from pypdf import PdfReader
from colegio.invoice_layout import example_template,sample,render,paper_preset

PT=72/25.4

class IndependentInvoicePDFTests(unittest.TestCase):
    def template(self,preset='media_vertical'):
        layout=example_template();layout['paper']=paper_preset(preset)
        layout['fields']=layout['fields'][:1];layout['details']['visible']=False
        layout['fields'][0].update(x_mm=5,y_mm=5,width_mm=100,height_mm=15)
        return layout

    def test_exact_page_and_all_text_inside_declared_box_including_accents(self):
        for preset,size,box in (('media_vertical',(396,612),(5,5,105,20)),
                ('carta_arriba',(612,792),(195.9,5,210.9,105)),
                ('carta_abajo',(612,792),(195.9,144.7,210.9,244.7))):
            for font in ('sans','mono'):
                for bold,italic in ((False,False),(True,True)):
                    with self.subTest(preset=preset,font=font,bold=bold,italic=italic):
                        layout=self.template(preset);layout['fields'][0].update(font=font,bold=bold,italic=italic)
                        data=sample();data['fecha']='ÁÑQgy · Muñoz Peña'
                        raw=render(layout,data,[])['pdf'];reader=PdfReader(io.BytesIO(raw))
                        self.assertEqual(len(reader.pages),1)
                        self.assertEqual(tuple(float(n) for n in reader.pages[0].mediabox),(0,0,*size))
                        self.assertIn(data['fecha'],reader.pages[0].extract_text())
                        self.assertNotIn('/XObject',reader.pages[0]['/Resources'])
                        with fitz.open(stream=raw,filetype='pdf') as document:
                            spans=[span for block in document[0].get_text('dict')['blocks'] for line in block.get('lines',[]) for span in line['spans']]
                            self.assertEqual(len(spans),1)
                            expected=[n*PT for n in box];actual=spans[0]['bbox']
                            self.assertGreaterEqual(actual[0],expected[0]-.01);self.assertGreaterEqual(actual[1],expected[1]-.01)
                            self.assertLessEqual(actual[2],expected[2]+.01);self.assertLessEqual(actual[3],expected[3]+.01)
                            self.assertEqual(spans[0]['text'],data['fecha'])

    def test_offsets_scale_and_top_bottom_have_independent_pdf_coordinates(self):
        for preset,box in (('media_vertical',(10,10,80,25)),('carta_arriba',(190.9,10,205.9,80)),('carta_abajo',(190.9,149.7,205.9,219.7))):
            layout=self.template(preset);layout['fields'][0].update(x_mm=10,y_mm=10,width_mm=70,height_mm=15)
            printer=dict(name='Impresora ficticia',x_tenths=10,y_tenths=-10,scale=1,margin_mm=5)
            raw=render(layout,sample(),[],printer)['pdf']
            with fitz.open(stream=raw,filetype='pdf') as document:
                actual=document[0].get_text('dict')['blocks'][0]['lines'][0]['spans'][0]['bbox']
                self.assertGreaterEqual(actual[0],(box[0]+1)*PT-.01);self.assertGreaterEqual(actual[1],(box[1]-1)*PT-.01)
                self.assertLessEqual(actual[2],(box[2]+1)*PT+.01);self.assertLessEqual(actual[3],(box[3]-1)*PT+.01)
            # Scale is a printer adjustment, never a replacement for the page size.
            printer['scale']=.99
            raw=render(layout,sample(),[],printer)['pdf'];reader=PdfReader(io.BytesIO(raw))
            self.assertEqual(tuple(float(n) for n in reader.pages[0].mediabox)[2:],(396,612) if preset=='media_vertical' else (612,792))
            with fitz.open(stream=raw,filetype='pdf') as document:
                span=document[0].get_text('dict')['blocks'][0]['lines'][0]['spans'][0]
                self.assertAlmostEqual(span['size'],9.9,places=3)


if __name__=='__main__':unittest.main(verbosity=2)
