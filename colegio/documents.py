"""Frozen administrative documents and dependency-free, printable PDF output."""
import json
import textwrap
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from .db import ValidationError, audit, integer, money, required, valid_date, local_today
from .branding import pdf_logo
from .pdf_fonts import embed_fonts, text_width


def converted(cents, rate):
    return int((Decimal(cents) * Decimal(rate)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def amount(cents, currency='USD'):
    value = f'{cents // 100:,}.{cents % 100:02d}'.translate(str.maketrans({',':'.', '.':','}))
    return f'{currency} {value}'


def enrollment(db, student_id, user_id):
    row = db.execute('''SELECT s.*,g.name AS guardian_name,g.document AS guardian_document,
        g.phone AS guardian_phone,g.email AS guardian_email,g.address AS guardian_address,
        gr.name AS grade_name FROM students s JOIN guardians g ON g.id=s.guardian_id
        JOIN grades gr ON gr.id=s.grade_id WHERE s.id=?''', (student_id,)).fetchone()
    data = {'student': dict(row), 'school': dict(db.execute('SELECT key,value FROM settings'))}
    data['student']['net_fee'] = (row['monthly_fee'] * (100-row['discount']) + 50)//100
    return store(db, 'enrollment_documents', data, user_id, student_id)


def store(db, table, data, user_id, student_id=None):
    created = datetime.now(timezone.utc).isoformat()
    data['created_at'] = created
    data['issued_on'] = local_today().isoformat()
    data['operator'] = db.execute('SELECT name FROM users WHERE id=?', (user_id,)).fetchone()[0]
    fields, values = 'snapshot_json,created_at,created_by', [json.dumps(data, ensure_ascii=False), created, user_id]
    if student_id is not None:
        fields += ',student_id'
        values.append(student_id)
    result = db.execute(f'INSERT INTO {table}({fields}) VALUES({",".join("?" for _ in values)})', values)
    audit(db, user_id, table, {'id': result.lastrowid})
    return result.lastrowid


def payroll(db, data, user_id):
    on = valid_date(data.get('pay_date'))
    rate = db.execute('SELECT rate FROM exchange_rates WHERE rate_date=?', (on,)).fetchone()
    if not rate:
        raise ValidationError('Registra la tasa BCV de la fecha de la nómina primero.')
    source = data.get('lines')
    if not isinstance(source, list) or not 1 <= len(source) <= 500:
        raise ValidationError('Selecciona entre 1 y 500 empleados.')
    lines, seen = [], set()
    for item in source:
        if not isinstance(item, dict):
            raise ValidationError('Detalle de nómina inválido.')
        employee_id = integer(item.get('employee_id'), 1, 2147483647)
        if employee_id in seen:
            raise ValidationError('El empleado está repetido en la nómina.')
        seen.add(employee_id)
        emp = db.execute("SELECT * FROM employees WHERE id=? AND status='active'", (employee_id,)).fetchone()
        if not emp:
            raise ValidationError('Selecciona empleados activos existentes.')
        usd = money(item.get('amount'))
        lines.append(dict(emp, amount_usd=usd, amount_ves=converted(usd, rate['rate'])))
    frozen = {'name': required(data, 'name'), 'pay_date': on, 'rate': rate['rate'], 'lines': lines,
              'school': dict(db.execute('SELECT key,value FROM settings')),
              'total_usd': sum(r['amount_usd'] for r in lines), 'total_ves': sum(r['amount_ves'] for r in lines)}
    return {'id': store(db, 'payroll_plans', frozen, user_id)}


def load_document(db, kind, target):
    table = {'enrollment': 'enrollment_documents', 'payroll-plan': 'payroll_plans'}[kind]
    row = db.execute(f'SELECT snapshot_json FROM {table} WHERE id=?', (target,)).fetchone()
    if not row:
        raise ValidationError('Documento inexistente.')
    return dict(json.loads(row[0]), id=target)


class PDF:
    """Small vector PDF writer: WinAnsi fonts, wrapping and repeating table headings."""
    def __init__(self, title, school, landscape=False):
        self.w, self.h = (842, 595) if landscape else (595, 842)
        self.title, self.school, self.pages = title, school, []
        self.logo = pdf_logo(school.get('logo', ''))
        self.new_page()

    def text(self, x, y, value, size=10, bold=False, color='0.10 0.18 0.32'):
        raw = str(value).encode('cp1252', errors='replace')
        escaped = ''.join(f'\\{b:03o}' if b<32 or b>126 else ('\\'+chr(b) if chr(b) in '()\\' else chr(b)) for b in raw)
        self.commands.append(f'BT {color} rg /{"F2" if bold else "F1"} {size} Tf 1 0 0 1 {x} {self.h-y} Tm ({escaped}) Tj ET')

    def box(self, x, y, w, h, fill=None):
        if fill:
            self.commands.append(f'{fill} rg {x} {self.h-y-h} {w} {h} re f')
        self.commands.append(f'0.18 0.27 0.45 RG 0.6 w {x} {self.h-y-h} {w} {h} re S')

    def new_page(self):
        self.commands = []
        self.pages.append(self.commands)
        self.box(24, 24, self.w-48, self.h-48)
        if self.logo:
            w, h, _ = self.logo
            height, width = 78, 78*w/h
            self.commands.append(f'q {width:.3f} 0 0 {height} 38 {self.h-36-height} cm /Logo Do Q')
        else:
            self.box(38, 36, 40, 40, '0.94 0.96 0.99')
            self.box(46, 44, 12, 22)
            self.box(58, 44, 12, 22)
        x = 126 if self.logo else 90
        width = self.w-x-45
        name_lines = self.wrap(self.school.get('legal_name') or self.school.get('school_name','Colegio'), width, 14)
        for i, line in enumerate(name_lines):
            self.text(x, 49+i*18, line, 14, True)
        header_y = 49+len(name_lines)*18
        if self.school.get('rif'):
            self.text(x, header_y, 'RIF: '+self.school['rif'], 10, True)
            header_y += 15
        address = self.school.get('fiscal_address') or self.school.get('address','')
        for line in self.wrap('Domicilio fiscal: '+address if address else '', width, 9):
            self.text(x, header_y, line, 9)
            header_y += 12
        contact = ' | '.join(str(self.school.get(k,'')) for k in ('phone','email','website') if self.school.get(k))
        for line in self.wrap(contact, width, 8):
            if line:
                self.text(x, header_y, line, 8)
                header_y += 11
        self.y = max(126 if self.logo else 100, header_y+12)
        self.box(38, self.y, self.w-76, 27, '0.94 0.96 0.99')
        self.text(46, self.y+18, self.title, 12, True)
        self.text(self.w-97, self.h-35, f'Página {len(self.pages)}', 8)
        self.y += 42

    @staticmethod
    def wrap(value, width, size=10):
        result = []
        for line in str(value).splitlines() or ['']:
            result.extend(textwrap.wrap(line, max(1, int(width/(size*.56)))) or [''])
        return result

    def ensure(self, height):
        if self.y+height > self.h-65:
            self.new_page()
            return True
        return False

    def line(self, value, bold=False):
        for line in self.wrap(value, self.w-90):
            self.ensure(17)
            self.text(44, self.y, line, 10, bold)
            self.y += 17

    def table(self, headings, rows, widths):
        def draw(values, header=False):
            cells = [self.wrap(v, width-10, 9) for v, width in zip(values, widths)]
            height = max(len(c) for c in cells)*12+12
            if self.ensure(height) and not header:
                draw(headings, True)
            x = 38
            for cell, width in zip(cells, widths):
                self.box(x, self.y, width, height, '0.94 0.96 0.99' if header else None)
                for i, line in enumerate(cell):
                    self.text(x+5, self.y+15+i*12, line, 9, header)
                x += width
            self.y += height
        draw(headings, True)
        for row in rows:
            draw(row)
        self.y += 23

    def signature(self, left, right, operator):
        self.ensure(90)
        self.y += 32
        width = (self.w-110)/2
        for x, label in ((44,left),(66+width,right)):
            self.commands.append(f'0.35 0.44 0.56 RG 0.5 w {x} {self.h-self.y} m {x+width} {self.h-self.y} l S')
            self.text(x+4, self.y+16, label, 9)
        self.y += 44
        self.line('Registrado por: '+operator)

    def total(self, value):
        lines = self.wrap(value, self.w-100, 12)
        self.ensure(28+18*len(lines))
        height = 14+18*len(lines)
        self.box(38, self.y, self.w-76, height, '0.94 0.96 0.99')
        for i, line in enumerate(lines):
            self.text(46, self.y+21+i*18, line, 12, True)
        self.y += height+24

    def output(self):
        objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'',
                   b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
                   b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>']
        if getattr(self, 'embedded_fonts', False):
            embed_fonts(objects)
        kids = []
        logo_resources = ''
        if self.logo:
            w, h, stream = self.logo
            logo_index = len(objects)+1
            objects.append((f'<< /Type /XObject /Subtype /Image /Width {w} /Height {h} '
                f'/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode '
                f'/DecodeParms << /Predictor 15 /Colors 3 /BitsPerComponent 8 /Columns {w} >> '
                f'/Length {len(stream)} >>\nstream\n').encode()+stream+b'\nendstream')
            logo_resources = f' /XObject << /Logo {logo_index} 0 R >>'
        for commands in self.pages:
            index = len(objects)+1
            kids.append(f'{index} 0 R')
            objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.w} {self.h}] /Resources << /Font << /F1 3 0 R /F2 4 0 R >>{logo_resources} >> /Contents {index+1} 0 R >>'.encode())
            stream = '\n'.join(commands).encode('ascii')
            objects.append(f'<< /Length {len(stream)} >>\nstream\n'.encode()+stream+b'\nendstream')
        objects[1] = f'<< /Type /Pages /Count {len(kids)} /Kids [{" ".join(kids)}] >>'.encode()
        output = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n'); offsets = [0]
        for i, obj in enumerate(objects, 1):
            offsets.append(len(output)); output.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
        start = len(output)
        output.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
        for offset in offsets[1:]:
            output.extend(f'{offset:010d} 00000 n \n'.encode())
        output.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode())
        return bytes(output)


def period_label(value):
    months = ('enero','febrero','marzo','abril','mayo','junio','julio','agosto',
              'septiembre','octubre','noviembre','diciembre')
    try:
        year, month = str(value).split('-')
        if len(year)==4 and year.isascii() and year.isdigit() and len(month)==2 and 1 <= int(month) <= 12:
            return f'{months[int(month)-1].capitalize()} {year}'
    except (ValueError, TypeError):
        pass
    return str(value)


def receipt_student_details(payment):
    name = payment['student_name']
    code = 'Código: '+payment.get('student_code',payment['student_document'])
    grade = payment.get('grade_name')
    if grade:
        name += ' · '+grade
    else:
        code += ' | Grado no registrado'
    return name,code


class ReceiptPDF(PDF):
    """Portrait payment stationery with quiet rules and a prominent received amount."""
    ink = '0.14 0.20 0.29'
    muted = '0.40 0.46 0.53'
    blue = '0.09 0.25 0.40'
    embedded_fonts = True

    def __init__(self, data):
        self.payment = data['payment']
        super().__init__('Comprobante de pago', data['settings'])

    @staticmethod
    def wrap(value, width, size=10):
        # Use the bundled font's real glyph widths, including long unbroken codes.
        # Bold metrics leave enough room for both regular and bold text.
        result = []
        for source in str(value).splitlines() or ['']:
            line = ''
            for word in source.split():
                candidate = line+' '+word if line else word
                if text_width(candidate,size,True)<=width:
                    line = candidate
                    continue
                if line:
                    result.append(line)
                    line = ''
                for character in word:
                    if line and text_width(line+character,size,True)>width:
                        result.append(line)
                        line = ''
                    line += character
            result.append(line)
        return result

    def rule(self, x, y, width):
        self.commands.append(f'0.85 0.89 0.93 RG 0.6 w {x} {self.h-y} m {x+width} {self.h-y} l S')

    def shade(self, x, y, width, height, color='0.95 0.97 0.98'):
        self.commands.append(f'{color} rg {x} {self.h-y-height} {width} {height} re f')

    def paragraph(self, value, x, y, width, size=10, bold=False, color=None):
        for line in self.wrap(value, width, size):
            self.text(x, y, line, size, bold, color or self.ink)
            y += size+4
        return y

    def label(self, value, x, y):
        self.text(x, y, value.upper(), 8, True, self.muted)

    def new_page(self):
        self.commands = []
        self.pages.append(self.commands)
        left, width = 42, self.w-84
        if self.logo:
            w, h, _ = self.logo
            self.commands.append(f'q {64*w/h:.3f} 0 0 64 42 {self.h-104} cm /Logo Do Q')
            x = 120
        else:
            x = left
        y = self.paragraph(self.school.get('legal_name') or self.school.get('school_name','Colegio'),
                           x, 53, self.w-x-42, 12, True, self.blue)
        if self.school.get('rif'):
            self.text(x, y, 'RIF: '+self.school['rif'], 9, True, self.muted)
            y += 15
        address = self.school.get('fiscal_address') or self.school.get('address','')
        if address:
            y = self.paragraph('Domicilio fiscal: '+address, x, y, self.w-x-42, 8.5, color=self.muted)
        contact = ' | '.join(str(self.school.get(k,'')) for k in ('phone','email','website') if self.school.get(k))
        if contact:
            y = self.paragraph(contact, x, y, self.w-x-42, 8, color=self.muted)
        y = max(120, y+14)
        self.rule(left, y, width)
        self.text(left, y+30, self.title, 19, True, self.blue)
        self.text(self.w-143, y+29, f"R-{self.payment['id']:06d}", 13, True, self.blue)
        on = datetime.fromisoformat(self.payment['paid_on']).strftime('%d/%m/%Y')
        self.text(left, y+48, 'Fecha de pago: '+on, 9, color=self.muted)
        if self.payment['voided']:
            self.text(self.w-143, y+48, 'ANULADO', 9, True, '0.65 0.23 0.22')
        self.y = y+77
        self.rule(left, self.h-47, width)
        self.text(left, self.h-32, 'Comprobante administrativo. No sustituye una factura fiscal.', 7.5, color=self.muted)
        self.text(self.w-89, self.h-32, f'Página {len(self.pages)}', 7.5, color=self.muted)

    def parties(self):
        p = self.payment
        name, code = receipt_student_details(p)
        columns = [('Representante legal',p['guardian_name'],'Cédula: '+p['guardian_document'],p.get('guardian_phone','')),
                   ('Alumno / grado',name,code,'')]
        sizes = []
        for _, name, document, phone in columns:
            sizes.append(21+len(self.wrap(name,238,11))*15+len(self.wrap(document,238,9))*13+
                         (len(self.wrap(phone,238,9))*13 if phone else 0))
        self.ensure(max(sizes)+12)
        bottom = self.y
        for x, (label,name,document,phone) in zip((42,315),columns):
            self.label(label,x,self.y)
            y = self.paragraph(name,x,self.y+21,238,11,True)
            y = self.paragraph(document,x,y+1,238,9,color=self.muted)
            if phone:
                y = self.paragraph(phone,x,y,238,9,color=self.muted)
            bottom = max(bottom,y)
        self.y = bottom+17
        if p.get('guardian_address'):
            self.flow('Dirección del representante: '+p['guardian_address'],9,self.muted)
            self.y += 12

    def flow(self, value, size=10, color=None, bold=False):
        for line in self.wrap(value,self.w-84,size):
            self.ensure(size+5)
            self.text(42,self.y,line,size,bold,color or self.ink)
            self.y += size+5

    def allocations(self, rows):
        self.ensure(74)
        self.label('Conceptos abonados',42,self.y)
        self.y += 16
        def header():
            self.shade(42,self.y,self.w-84,27,'0.96 0.97 0.98')
            self.label('Descripción',52,self.y+17)
            self.label('Período',335,self.y+17)
            self.label('Aplicado · USD',454,self.y+17)
            self.y += 27
        header()
        for row in rows:
            descriptions = self.wrap(row['concept'],273,10)
            periods = self.wrap(period_label(row['period']),105,9)
            height = max(len(descriptions)*14,len(periods)*13)+22
            if self.ensure(height+10):
                header()
            y = self.y+19
            for i, line in enumerate(descriptions):
                self.text(52,y+i*14,line,10,color=self.ink)
            for i, line in enumerate(periods):
                self.text(335,y+i*13,line,9,color=self.muted)
            value = amount(row['amount'])
            self.text(self.w-52-text_width(value,10,True),y,value,10,True,self.ink)
            self.y += height
            self.rule(42,self.y,self.w-84)
        self.y += 28

    def payment_summary(self):
        p = self.payment
        reference = self.wrap(p.get('reference',''),225,10) if p.get('reference') else []
        height = max(124 if p['currency']=='VES' else 106,76+len(reference)*14)
        self.ensure(height+15)
        top = self.y
        self.label('Método de pago',42,top+12)
        self.text(42,top+33,p['method'],12,True,self.ink)
        if reference:
            self.label('Referencia / comprobante',42,top+63)
            for i, line in enumerate(reference):
                self.text(42,top+83+i*14,line,10,color=self.ink)
        x, width = 311, 242
        self.shade(x,top,width,height)
        self.label('Importe recibido · '+('Bolívares' if p['currency']=='VES' else 'USD'),x+17,top+23)
        value = amount(p['received_amount'],'Bs' if p['currency']=='VES' else 'USD')
        size = min(23, int(208/(max(1,len(value))*.56)))
        self.text(x+17,top+56,value,size,True,self.blue)
        self.rule(x+17,top+71,width-34)
        self.text(x+17,top+89,'Total aplicado en USD',8.5,color=self.muted)
        applied = amount(p['amount'])
        self.text(self.w-59-text_width(applied,10,True),top+89,applied,10,True,self.blue)
        if p['currency']=='VES':
            self.text(x+17,top+111,f"Tasa BCV aplicada: Bs {p['exchange_rate']} por USD",8,color=self.muted)
        self.y += height+27

    def render(self, data):
        p = self.payment
        if p['voided']:
            self.flow('COMPROBANTE ANULADO',11,'0.65 0.23 0.22',True)
            self.flow(p['void_reason'],9,'0.65 0.23 0.22')
            self.y += 15
        self.parties()
        self.allocations(data['allocations'])
        self.payment_summary()
        if p['notes']:
            self.ensure(35)
            self.label('Observaciones',42,self.y)
            self.y += 18
            self.flow(p['notes'],9,self.muted)
        self.ensure(100)
        self.y += 44
        for x, label in ((42,'Firma de administración'),(315,'Firma del representante')):
            self.rule(x,self.y,238)
            self.text(x,self.y+17,label,8.5,color=self.muted)
        self.y += 43
        self.flow('Registrado por: '+p['operator'],8,self.muted)
        return self.output()


class HalfLetterReceiptPDF(ReceiptPDF):
    """Readable half-letter landscape stationery, continuing instead of clipping."""
    def __init__(self, data):
        self.payment, self.school = data['payment'], data['settings']
        self.w, self.h, self.pages = 612, 396, []
        self.title = 'Comprobante de pago'
        self.logo = pdf_logo(self.school.get('logo',''))
        self.new_page()

    def new_page(self):
        self.commands = []
        self.pages.append(self.commands)
        x = 26
        if self.logo:
            w,h,_ = self.logo
            self.commands.append(f'q {42*w/h:.3f} 0 0 42 26 {self.h-62} cm /Logo Do Q')
            x = 78
        y = self.paragraph(self.school.get('legal_name') or self.school.get('school_name','Colegio'),x,28,350,11,True,self.blue)
        if self.school.get('rif'):
            self.text(x,y,'RIF: '+self.school['rif'],8,True,self.muted)
            y += 12
        address = self.school.get('fiscal_address') or self.school.get('address','')
        if address:
            y = self.paragraph('Domicilio fiscal: '+address,x,y,350,7.5,color=self.muted)
        contact = ' | '.join(str(self.school.get(k,'')) for k in ('phone','email','website') if self.school.get(k))
        if contact:
            y = self.paragraph(contact,x,y,350,7.5,color=self.muted)
        self.label(self.title,448,28)
        self.text(448,44,f"R-{self.payment['id']:06d}",12,True,self.blue)
        on = datetime.fromisoformat(self.payment['paid_on']).strftime('%d/%m/%Y')
        self.text(448,59,'Fecha: '+on,8,color=self.muted)
        if self.payment['voided']:
            self.text(448,72,'ANULADO',8,True,'0.65 0.23 0.22')
        self.y = max(74,y+3)
        self.rule(26,self.y,560)
        self.y += 13
        self.rule(26,374,560)
        self.text(26,386,'Comprobante administrativo. No sustituye una factura fiscal.',7,color=self.muted)
        self.text(539,386,f'Página {len(self.pages)}',7,color=self.muted)

    def ensure(self, height):
        if self.y+height>366:
            self.new_page()
            return True
        return False

    def flow(self,value,size=8.5,color=None,bold=False):
        for line in self.wrap(value,560,size):
            self.ensure(size+3)
            self.text(26,self.y,line,size,bold,color or self.ink)
            self.y += size+3

    def parties(self):
        p = self.payment
        name, code = receipt_student_details(p)
        contact = ' | Teléfono: '+p['guardian_phone'] if p.get('guardian_phone') else ''
        columns = [('Representante legal',p['guardian_name'],'Cédula: '+p['guardian_document']+contact,''),
                   ('Alumno / grado',name,code,'')]
        heights = [14+len(self.wrap(name,264,10))*14+len(self.wrap(document,264,8))*12+
                   (len(self.wrap(phone,264,8))*12 if phone else 0) for _,name,document,phone in columns]
        self.ensure(max(heights)+6)
        bottom = self.y
        for x,(label,name,document,phone) in zip((26,322),columns):
            self.label(label,x,self.y)
            y = self.paragraph(name,x,self.y+15,264,10,True)
            y = self.paragraph(document,x,y,264,8,color=self.muted)
            if phone:
                y = self.paragraph(phone,x,y,264,8,color=self.muted)
            bottom = max(bottom,y)
        self.y = bottom+5
        if p.get('guardian_address'):
            self.flow('Dirección del representante: '+p['guardian_address'],8,self.muted)
            self.y += 3

    def allocations(self,rows):
        self.ensure(52)
        self.label('Conceptos abonados',26,self.y)
        self.y += 11
        def header():
            self.shade(26,self.y,560,19,'0.96 0.97 0.98')
            for x,value in ((34,'Descripción'),(343,'Período'),(492,'Aplicado · USD')):
                self.label(value,x,self.y+13)
            self.y += 19
        header()
        for row in rows:
            descriptions = self.wrap(row['concept'],296,9)
            periods = self.wrap(period_label(row['period']),133,8)
            height = max(len(descriptions)*12,len(periods)*11)+10
            if self.ensure(height+5):
                header()
            for i,line in enumerate(descriptions):
                self.text(34,self.y+14+i*12,line,9,color=self.ink)
            for i,line in enumerate(periods):
                self.text(343,self.y+14+i*11,line,8,color=self.muted)
            value = amount(row['amount'])
            self.text(578-text_width(value,9,True),self.y+14,value,9,True,self.ink)
            self.y += height
            self.rule(26,self.y,560)
        self.y += 10

    def payment_summary(self):
        p = self.payment
        reference = self.wrap(p.get('reference',''),268,8) if p.get('reference') else []
        height = max(80 if p['currency']=='VES' else 69,53+len(reference)*11)
        self.ensure(height+6)
        top = self.y
        self.label('Método de pago',26,top+11)
        self.text(26,top+26,p['method'],10,True,self.ink)
        if reference:
            self.label('Referencia / comprobante',26,top+44)
            for i,line in enumerate(reference):
                self.text(26,top+58+i*11,line,8,color=self.ink)
        self.shade(322,top,264,height)
        self.label('Importe recibido · '+('Bolívares' if p['currency']=='VES' else 'USD'),335,top+16)
        value = amount(p['received_amount'],'Bs' if p['currency']=='VES' else 'USD')
        self.text(335,top+39,value,18,True,self.blue)
        self.rule(335,top+49,238)
        self.text(335,top+62,'Total aplicado en USD',8,color=self.muted)
        applied = amount(p['amount'])
        self.text(573-text_width(applied,9,True),top+62,applied,9,True,self.blue)
        if p['currency']=='VES':
            self.text(335,top+74,f"Tasa BCV aplicada: Bs {p['exchange_rate']} por USD",7.5,color=self.muted)
        self.y += height+8

    def render(self,data):
        p = self.payment
        if p['voided']:
            self.flow('ANULADO: '+p['void_reason'],8.5,'0.65 0.23 0.22',True)
            self.y += 5
        self.parties()
        self.allocations(data['allocations'])
        self.payment_summary()
        if p['notes']:
            self.ensure(25)
            self.label('Observaciones',26,self.y)
            self.y += 13
            self.flow(p['notes'],8,self.muted)
        self.ensure(61)
        self.y += 23
        for x,label in ((26,'Firma de administración'),(322,'Firma del representante')):
            self.rule(x,self.y,264)
            self.text(x,self.y+11,label,8,color=self.muted)
        self.y += 27
        self.flow('Registrado por: '+p['operator'],7.5,self.muted)
        return self.output()


class TicketReceiptPDF(ReceiptPDF):
    def __init__(self,data,width):
        self.payment=data['payment'];self.school=data['settings'];self.w=width
        self.logo=pdf_logo(self.school.get('logo',''));self.pages=[]
        self.h=1100
        self.measured=False
        self.new_page()

    def new_page(self):
        self.commands=[];self.pages.append(self.commands);self.y=12
        if self.logo:
            w,h,_=self.logo;self.commands.append(f'q {34*w/h:.3f} 0 0 34 {(self.w-34*w/h)/2:.3f} {self.h-46} cm /Logo Do Q');self.y=59
        for value,size,bold in ((self.school.get('legal_name') or self.school.get('school_name','Colegio'),9,True),
            ('RIF: '+self.school.get('rif',''),7.5,False),(self.school.get('fiscal_address') or self.school.get('address',''),7,False),
            (f"COMPROBANTE R-{self.payment['id']:06d}",9,True),(datetime.fromisoformat(self.payment['paid_on']).strftime('%d/%m/%Y'),8,False)):
            for line in self.wrap(value,self.w-18,size):
                self.text(9,self.y,line,size,bold);self.y+=size+3
        if self.payment['voided']:
            self.text(9,self.y,'COMPROBANTE ANULADO',8,True);self.y+=14
        self.rule(9,self.y,self.w-18);self.y+=15

    def ticket_line(self,value,bold=False,size=8):
        for line in self.wrap(value,self.w-18,size):
            if self.y+size+4>self.h-34:self.new_page()
            self.text(9,self.y,line,size,bold);self.y+=size+4

    def render(self,data):
        p=self.payment
        self.ticket_line('REPRESENTANTE',True);self.ticket_line(p['guardian_name'])
        self.ticket_line('Cédula: '+p['guardian_document'])
        self.ticket_line('ALUMNO / GRADO',True)
        name,code=receipt_student_details(p);self.ticket_line(name);self.ticket_line(code)
        if p.get('guardian_address'):self.ticket_line('Dirección: '+p['guardian_address'],size=7.5)
        self.y+=6;self.ticket_line('CONCEPTOS ABONADOS',True)
        for row in data['allocations']:
            self.ticket_line(row['concept']+' · '+period_label(row['period']))
            self.ticket_line('Aplicado: '+amount(row['amount']),True)
        self.y+=6;self.ticket_line('Método: '+p['method'])
        if p['reference']:self.ticket_line('Referencia: '+p['reference'])
        self.ticket_line('RECIBIDO: '+amount(p['received_amount'],'Bs' if p['currency']=='VES' else 'USD'),True,9)
        self.ticket_line('Total aplicado: '+amount(p['amount']),True)
        if p['currency']=='VES':self.ticket_line('BCV: Bs '+p['exchange_rate']+' por USD',size=7.5)
        if p['notes']:self.ticket_line('Observaciones: '+p['notes'],size=7.5)
        if p['voided']:self.ticket_line('Motivo de anulación: '+p['void_reason'],size=7.5)
        self.y+=12;self.ticket_line('Firma de administración:');self.y+=12;self.ticket_line('Firma del representante:')
        self.ticket_line('Registrado por: '+p['operator'],size=7)
        self.ticket_line('Comprobante administrativo. No sustituye una factura fiscal.',size=7)
        if len(self.pages)==1 and not self.measured:
            self.h=max(220,self.y+40)
            self.measured=True;self.pages=[];self.new_page()
            return self.render(data)
        return self.output()


class AdministrativePDF(PDF):
    embedded_fonts = True
    wrap = staticmethod(ReceiptPDF.wrap)

    def new_page(self):
        self.commands=[]; self.pages.append(self.commands)
        x=42
        if self.logo:
            w,h,_=self.logo
            self.commands.append(f'q {60*w/h:.3f} 0 0 60 42 {self.h-96} cm /Logo Do Q')
            x=115
        y=48
        for line in self.wrap(self.school.get('legal_name') or self.school.get('school_name','Colegio'),self.w-x-42,12):
            self.text(x,y,line,12,True); y+=17
        for value in ('RIF: '+self.school.get('rif',''),self.school.get('fiscal_address') or self.school.get('address','')):
            for line in self.wrap(value,self.w-x-42,8):
                self.text(x,y,line,8); y+=12
        self.y=max(115,y+20)
        for line in self.wrap(self.title,self.w-84,12):
            self.text(42,self.y,line,12,True); self.y+=18
        self.y+=12
        self.text(self.w-100,self.h-35,f'Página {len(self.pages)}',8)


def administrative_pdf(kind,data):
    is_cash=kind=='cash-close'
    title='CIERRE DE CAJA' if is_cash else ('CONSTANCIA DE SOLVENCIA' if data['kind']=='solvency' else 'ESTADO DE CUENTA POR REPRESENTANTE')
    pdf=AdministrativePDF(f"{title} · {'C' if is_cash else 'D'}-{data['id']:06d}",data['school'])
    pdf.line('Fecha de emisión: '+data['issued_on'])
    if is_cash:
        pdf.line('Fecha cerrada: '+data['closed_on'],True)
        if data.get('reopened_at'): pdf.line('CIERRE REABIERTO: '+data['reopen_reason'],True)
        pdf.table(['Método / moneda','Ingresos recibidos','Egresos pagados','Neto'],
            [[f"{r['method']} / {r['currency']}",amount(r['income'],r['currency']),amount(r['expense'],r['currency']),signed_amount(r['net'],r['currency'])] for r in data['lines']],
            [150,123,123,123])
        pdf.line('Los importes anteriores son montos reales por moneda; no se suman dólares y bolívares.')
        pdf.table(['Efectivo','Fondo inicial','Esperado','Contado','Diferencia'],
            [[r['currency'],amount(r['opening'],r['currency']),amount(r['expected'],r['currency']),amount(r['counted'],r['currency']),signed_amount(r['difference'],r['currency'])] for r in data['counts']],
            [75,111,111,111,111])
        pdf.total(f"Equivalente USD: ingresos {amount(data['income_usd'])} | egresos {amount(data['expense_usd'])}")
        pdf.line('Arqueo: fondo inicial + ingresos en efectivo - egresos en efectivo. Transferencias, tarjetas y egresos sin método no forman parte del efectivo.')
        pdf.line('Observaciones: '+(data['notes'] or 'Sin observaciones.'))
        pdf.table(['Movimiento / referencia','Método','Moneda / recibido','Estado'],
            [[f"{'R' if r['type']=='income' else 'E'}-{r['id']:06d}\n{r['reference']}",r['method'],amount(r['received_amount'],r['currency']),'Anulado' if r['voided'] else 'Válido'] for r in data['movements']],
            [190,119,130,80])
    else:
        g=data['guardian']
        pdf.line(f"Representante: {g['name']} | Cédula: {g['document']}",True)
        if g['phone']: pdf.line('Contacto: '+g['phone'])
        pdf.table(['Alumno / código','Grado / sección','Año escolar'],
            [[f"{s['name']}\n{s['student_code']}",s['grade_name'],f"{s['school_year']}–{s['school_year']+1}"] for s in data['students']],
            [220,200,99])
        if data['kind']=='solvency':
            pdf.line('Se hace constar que los alumnos vinculados a este representante no presentan saldo pendiente en los cargos registrados al emitir este documento.',True)
            pdf.line('El corte incluye las mensualidades calculadas hasta el mes de emisión y cualquier cargo futuro ya registrado. No acredita períodos futuros que aún no estén cargados ni pagos externos sin registrar.')
            pdf.total('SALDO PENDIENTE: USD 0,00')
        else:
            pdf.total(f"Saldo pendiente: {amount(data['balance'])} | Vencido: {amount(data['overdue'])}")
            pdf.table(['Alumno / grado','Concepto / período / vence','Cargo USD','Abono USD','Saldo USD'],
                [[f"{c['student_name']}\n{c['grade_name']}",f"{c['concept']}\n{c['period']} / {c['due_date']}",amount(c['amount']),amount(c['paid']),amount(c['balance'])] for c in data['charges']],
                [150,140,76,76,77])
            pdf.line('Incluye cargos activos, pendientes y pagados, incluso períodos futuros ya preparados. La deuda vencida se calcula al emitir el documento.')
            pdf.table(['Recibo / alumno','Fecha / método','Recibido','Aplicado USD / estado'],
                [[f"R-{p['id']:06d}\n{p['student_name']}",f"{p['paid_on']}\n{p['method']}",amount(p['received_amount'],p['currency']),f"{amount(p['amount'])}\n{'Anulado' if p['voided'] else 'Válido'}"] for p in data['payments']],
                [169,120,110,120])
    pdf.line('Documento administrativo. Conserva los datos y el corte de su fecha de emisión.')
    pdf.signature('Firma de administración','Revisado por' if is_cash else 'Sello del colegio',data['operator'])
    return pdf.output()


def signed_amount(cents,currency):
    return ('- ' if cents<0 else '')+amount(abs(cents),currency)


def render_pdf(kind, data, paper='a4'):
    if kind == 'salary-receipt':
        e, employee = data['expense'], data['employee']
        received_label = amount(e['received_amount'], 'Bs' if e['currency']=='VES' else 'USD')
        pdf = AdministrativePDF(f"RECIBO DE SUELDO · E-{e['id']:06d}", data['school'])
        if e['voided']:
            pdf.line('RECIBO ANULADO: '+e['void_reason'], True)
        pdf.line('Fecha del pago: '+e['spent_on'], True)
        pdf.line('Empleado: '+employee['name'], True)
        pdf.line('Cédula: '+employee['document']+' | Cargo: '+employee['position'])
        pdf.table(['Período pagado: desde','Hasta','Entrada','Salida'],
                  [[data['period_start'],data['period_end'],data['entry_time'],data['exit_time']]], [175,174,85,85])
        pdf.line('Concepto: '+e['concept'])
        pdf.total('Importe recibido: '+received_label)
        pdf.line('Equivalente USD: '+amount(e['amount'])+(' | Tasa aplicada: Bs '+e['exchange_rate']+' por USD' if e['currency']=='VES' else ''))
        pdf.line('Método: '+e['method']+' | Referencia: '+(e['reference'] or 'Sin referencia'))
        if e['method']=='Transferencia':
            pdf.line('Banco registrado: '+(employee['bank'] or 'No registrado'))
            pdf.line('Cuenta registrada: '+(employee['bank_account'] or 'No registrada'))
            pdf.line('Titular: '+(employee['account_holder'] or employee['name'])+' | Cédula: '+(employee['holder_document'] or employee['document']))
        pdf.line('Horario informado para el período: entrada '+data['entry_time']+' y salida '+data['exit_time']+'.')
        pdf.line('Yo, '+employee['name']+', titular de la cédula '+employee['document']+', declaro haber recibido '+
                 received_label+' por el sueldo correspondiente al período del '+
                 data['period_start']+' al '+data['period_end']+'.')
        if data['notes']:
            pdf.line('Observaciones: '+data['notes'])
        pdf.line('La conformidad de recepción se acredita con la firma del empleado.')
        pdf.signature('Pagado por administración','Recibí conforme · Firma del empleado',data['operator'])
        pdf.line('Fecha de firma: ____________________    Huella: ____________________')
        return pdf.output()
    if kind in ('year-transition','payment-plan'):
        title='ACTA DE PASE DE AÑO' if kind=='year-transition' else 'CONVENIO DE PAGO'
        pdf=AdministrativePDF(f"{title} · {data['id']:06d}",data['school'])
        pdf.line('Fecha de emisión: '+data['issued_on'])
        if kind=='year-transition':
            pdf.line(f"Año {data['source_year']}–{data['source_year']+1} al {data['target_year']}–{data['target_year']+1}",True)
            pdf.line(f"Cierre del curso: {data['closed_on']} | Matrícula nueva: {data['enrollment_start']} al {data['enrollment_end']}")
            labels={'promote':'Avanza','repeat':'Repite','withdraw':'Retirado','skip':'Sin cambios'}
            pdf.table(['Alumno / código','Decisión','Grado anterior','Nuevo grado'],
                [[r['student_name']+'\n'+r['source']['student_code'],labels[r['action']],r['source_grade'],r['target_grade'] if r['action'] in ('promote','repeat') else '—'] for r in data['lines']],
                [175,85,125,134])
            pdf.line('Se conservan la matrícula anterior en esta acta, las constancias emitidas, los cargos, pagos, abonos y recibos. Los retirados quedan inactivos en el año anterior.')
        else:
            if data.get('cancelled'):pdf.line('CONVENIO CANCELADO: '+data['cancel_reason'],True)
            s=data['student'];pdf.line(s['name']+' | '+s['grade_name'],True)
            pdf.line('Representante: '+s['guardian_name']+' | '+s['guardian_document'])
            pdf.total('Deuda original convenida: '+amount(data['total']))
            pdf.table(['Cuota','Vencimiento','Importe USD'],[[r['number'],r['due_date'],amount(r['amount'])] for r in data['installments']],[85,220,214])
            pdf.line('Condiciones: '+data['notes'])
            pdf.line('El convenio organiza deuda existente; no crea cargos nuevos ni acredita pagos. Conserva sus condiciones originales. La mora se mantiene según los cargos hasta saldarlos.')
        pdf.signature('Firma de administración','Dirección' if kind=='year-transition' else 'Representante legal',data['operator'])
        return pdf.output()
    if kind in ('cash-close','guardian-document'):
        return administrative_pdf(kind,data)
    if kind == 'enrollment':
        s = data['student']; pdf = PDF(f"CONSTANCIA DE MATRÍCULA · M-{data['id']:06d}", data['school'])
        pdf.line('Fecha de emisión: '+data.get('issued_on', data['created_at'][:10]))
        for line in (f"Alumno: {s['name']}", f"Código único: {s['student_code']} | Cédula: {s['document'] if s['document']!=s['student_code'] else 'Sin cédula propia'}",
                     f"Nacimiento: {s['birth_date']}", f"Grado / sección: {s['grade_name']} | Año escolar: {s['school_year']}–{s['school_year']+1}",
                     f"Representante: {s['guardian_name']} | Cédula: {s['guardian_document']}",
                     f"Contacto: {s['guardian_phone']} | {s['guardian_email']}", f"Dirección: {s['guardian_address']}",
                     f"Matrícula: {s['enrollment_start']} al {s['enrollment_end']} | Estado: {'Activo' if s['status']=='active' else 'Inactivo'}"):
            pdf.line(line)
        pdf.y += 12
        pdf.table(['Mensualidad base USD','Descuento','Mensualidad final USD'],
                  [[amount(s['monthly_fee']), f"{s['discount']} %", amount(s['net_fee'])]], [180,120,219])
        pdf.line('La tarifa se aplica a cargos nuevos. Los cargos existentes conservan su importe.')
        pdf.line('Observaciones: '+s['notes'])
    elif kind == 'payroll-plan':
        pdf = PDF(f"RELACIÓN DE PAGO · N-{data['id']:06d}", data['school'], True)
        pdf.line(f"{data['name']} | Fecha de pago: {data['pay_date']} | BCV: Bs {data['rate']} por USD", True)
        pdf.line('Preparación de nómina. Este documento no registra egresos ni acredita pagos realizados.')
        pdf.table(['Empleado / cédula / cargo','Banco / tipo / cuenta','Titular / cédula','USD','Bs a pagar'],
            [[f"{r['name']}\n{r['document']}\n{r['position']}",f"{r['bank'] or 'BANCO PENDIENTE'}\n{r['account_type']}\n{r['bank_account'] or 'CUENTA PENDIENTE'}",
              f"{r['account_holder'] or r['name']}\n{r['holder_document'] or r['document']}",amount(r['amount_usd']),amount(r['amount_ves'],'Bs')] for r in data['lines']],
            [210,200,160,86,110])
        pdf.total(f"TOTAL PROPUESTO: {amount(data['total_usd'])} | {amount(data['total_ves'],'Bs')}")
    else:
        if paper not in ('a4','half-letter','ticket-58','ticket-80'):
            raise ValidationError('Formato de recibo inválido. Selecciona media carta o A4.')
        if paper=='half-letter':
            return HalfLetterReceiptPDF(data).render(data)
        if paper.startswith('ticket-'):
            return TicketReceiptPDF(data,round(int(paper.split('-')[1])*72/25.4,3)).render(data)
        return ReceiptPDF(data).render(data)
    pdf.signature('Preparado por administración' if kind=='payroll-plan' else 'Firma de administración',
                  'Aprobado por' if kind=='payroll-plan' else 'Firma del representante legal',
                  data.get('operator', data.get('payment',{}).get('operator','')))
    return pdf.output()
