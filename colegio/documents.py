"""Frozen administrative documents and dependency-free, printable PDF output."""
import json
import textwrap
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from .db import ValidationError, audit, integer, money, required, valid_date, local_today
from .branding import pdf_logo


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


def render_pdf(kind, data):
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
        p = data['payment']; pdf = PDF(f"COMPROBANTE DE PAGO · R-{p['id']:06d}", data['settings'], True)
        if p['voided']:
            pdf.line('ANULADO · '+p['void_reason'], True)
        pdf.line(f"Fecha: {p['paid_on']} | Representante: {p['guardian_name']} | Cédula: {p['guardian_document']}")
        pdf.line(f"Alumno: {p['student_name']} | Código: {p.get('student_code', p['student_document'])}")
        pdf.line(f"Dirección / teléfono: {p.get('guardian_address','')} | {p.get('guardian_phone','')}")
        pdf.y += 10
        pdf.table(['Descripción','Período','Abono USD'], [[r['concept'],r['period'],amount(r['amount'])] for r in data['allocations']], [456,150,160])
        pdf.line(f"Método: {p['method']} | Referencia: {p['reference'] or '—'}")
        pdf.total(f"RECIBIDO: {amount(p['received_amount'], 'Bs' if p['currency']=='VES' else 'USD')} | TOTAL APLICADO: {amount(p['amount'])}")
        if p['currency']=='VES':
            pdf.line(f"BCV aplicada: Bs {p['exchange_rate']} por USD · {p['paid_on']}")
        pdf.line('Observaciones: '+p['notes'])
        pdf.line('COMPROBANTE ADMINISTRATIVO. No sustituye una factura fiscal.')
    pdf.signature('Preparado por administración' if kind=='payroll-plan' else 'Firma de administración',
                  'Aprobado por' if kind=='payroll-plan' else 'Firma del representante legal',
                  data.get('operator', data.get('payment',{}).get('operator','')))
    return pdf.output()
