"""Filtered directory reports; PDF and print preview share the same cells."""
from datetime import datetime, timedelta, timezone

from .db import ValidationError, integer
from .documents import AdministrativePDF, amount, school_month


TITLES = {'students': 'Alumnos y matrículas', 'guardians': 'Representantes',
          'employees': 'Personal del colegio'}


def directory_report(state, kind, query):
    if kind not in TITLES:
        raise ValidationError('Listado inexistente.')
    search = query.get('search', [''])[0]
    if len(search) > 200:
        raise ValidationError('La búsqueda admite hasta 200 caracteres.')
    archived = query.get('archived', ['0'])[0]
    if archived not in ('0', '1'):
        raise ValidationError('Filtro de archivados inválido.')
    grade = query.get('grade', [''])[0]
    grade = integer(grade, 1, 2147483647) if grade else None
    if grade and kind != 'students':
        raise ValidationError('Este listado no se filtra por grado.')
    grade_name = next((g['name'] for g in state['grades'] if g['id'] == grade), None)
    if grade and grade_name is None:
        raise ValidationError('El grado seleccionado no existe.')
    records = [r for r in state[kind] if (not grade or r['grade_id'] == grade)
               and (kind == 'employees' or not r.get('archived') or archived == '1')
               and (not search or any(search.lower() in str(r.get(k) or '').lower()
                    for k in ('name', 'document', 'student_code', 'guardian_name', 'phone', 'position')))]
    lines = []
    for n, r in enumerate(records, 1):
        status = 'Archivado' if r.get('archived') else ('Activo' if r.get('status') == 'active' else 'Inactivo')
        if kind == 'students':
            net = (r['monthly_fee'] * (100-r['discount']) + 50)//100
            lines.append([str(n), r['name']+'\n'+r['student_code'],
                r['grade_name']+f"\n{r['school_year']}–{r['school_year']+1}", r['guardian_name'],
                amount(net), school_month(r.get('billing_start') or r['enrollment_start'][:7]),
                status, amount(r['balance'])])
        elif kind == 'guardians':
            children = [s for s in state['students'] if s['guardian_id'] == r['id']]
            lines.append([str(n), r['name']+'\n'+r['document']+('\nArchivado' if r.get('archived') else ''),
                '\n'.join(filter(None, [r['phone'], r['email']])) or '—', r['address'] or '—',
                '\n'.join(s['name']+' · '+s['grade_name']+(' (archivado)' if s.get('archived') else '')
                          for s in children) or 'Sin alumnos vinculados'])
        else:
            lines.append([str(n), r['name']+'\n'+r['document'], r['position'], r['phone'] or '—',
                '\n'.join(filter(None, [r['bank'], r['bank_account']])) or 'Sin datos bancarios',
                amount(r['salary']), status])
    headings, widths = {
        'students': (['N.º', 'Alumno / código', 'Grado / año', 'Representante', 'Mensualidad',
                      'Cobrar desde', 'Estado', 'Saldo USD'], [26, 150, 108, 157, 85, 83, 65, 84]),
        'guardians': (['N.º', 'Representante / cédula', 'Contacto', 'Dirección', 'Alumnos / grado'],
                      [26, 180, 140, 170, 242]),
        'employees': (['N.º', 'Empleado / cédula', 'Cargo', 'Teléfono', 'Banco / cuenta', 'Salario USD', 'Estado'],
                      [26, 180, 125, 100, 168, 89, 70]),
    }[kind]
    filters = ['Búsqueda: '+search] if search else []
    if grade_name:
        filters.append('Grado: '+grade_name)
    if kind != 'employees':
        filters.append('Incluye archivados' if archived == '1' else 'Sin fichas archivadas')
    now = datetime.now(timezone(timedelta(hours=-4)))
    return {'kind': kind, 'title': TITLES[kind], 'school': state['settings'], 'issued_on': state['today'],
            'issued_at': now.strftime('%d/%m/%Y · %H:%M'), 'operator': state['user']['name'],
            'filter_label': ' · '.join(filters) or 'Todos los registros', 'count': len(lines),
            'count_label': f"{len(lines)} {'registro' if len(lines) == 1 else 'registros'}",
            'headings': headings, 'widths': widths, 'lines': lines,
            'note': 'Los importes se expresan en USD. El saldo corresponde a los cargos registrados al emitir el listado.'
                    if kind == 'students' else 'Salarios de referencia; este listado no acredita pagos de nómina.'
                    if kind == 'employees' else 'Alumnos vinculados según el directorio al emitir este listado.'}


class DirectoryPDF(AdministrativePDF):
    """Landscape letterhead with quiet rules, page numbers and split long rows."""
    def __init__(self, data):
        self.data = data
        super().__init__(data['title'], data['school'], landscape=True)

    def shade(self, y, height, color):
        self.commands.append(f'{color} rg 42 {self.h-y-height} {self.w-84} {height} re f')

    def rule(self, y):
        self.commands.append(f'0.85 0.89 0.91 RG 0.5 w 42 {self.h-y} m {self.w-42} {self.h-y} l S')

    def new_page(self):
        super().new_page()
        self.text(42, self.y, f"{self.data['count_label']} · Emitido: {self.data['issued_at']}", 9)
        self.y += 17
        for line in self.wrap(self.data['filter_label'], self.w-84, 8):
            self.text(42, self.y, line, 8); self.y += 12
        self.y += 8
        self.text(42, self.h-35, 'Listado administrativo · '+self.data['issued_at'], 8)

    def directory_table(self, section=None):
        data = section or self.data
        widths = data['widths']

        def draw(cells, height, header=False, shaded=False):
            if header or shaded:
                self.shade(self.y, height, '0.92 0.95 0.94' if header else '0.97 0.98 0.98')
            x = 42
            for cell, width in zip(cells, widths):
                for i, line in enumerate(cell):
                    self.text(x+6, self.y+15+i*12, line, 9, header)
                x += width
            self.y += height
            self.rule(self.y)

        headings = [self.wrap(v, w-12, 9) for v, w in zip(data['headings'], widths)]
        header_height = 12*max(map(len, headings))+12

        def header():
            if section:
                self.line(section['title'], True)
            draw(headings, header_height, header=True)

        self.ensure(header_height+70)
        header()
        for index, row in enumerate(data['lines']):
            cells = [self.wrap(v, w-12, 9) for v, w in zip(row, widths)]
            length = max(map(len, cells))
            offset = 0
            while offset < length:
                remaining = int((self.h-65-self.y-12)//12)
                if remaining < 1 or (offset == 0 and length > remaining and length <= 12):
                    self.new_page(); header()
                    remaining = int((self.h-65-self.y-12)//12)
                take = min(length-offset, remaining)
                if take < 1:
                    raise ValidationError('El membrete ocupa demasiado espacio; reduce la dirección del colegio.')
                draw([cell[offset:offset+take] for cell in cells], take*12+12, shaded=index%2 == 1)
                offset += take
        self.y += 18
        if not data['lines']:
            self.line(data.get('empty_message', 'No hay registros con los filtros seleccionados.'))
        if not section:
            self.line(self.data['note'])
            self.line('Generado por: '+self.data['operator'])


def directory_pdf(data):
    pdf = DirectoryPDF(data)
    pdf.directory_table()
    return pdf.output()


def daily_report(state, payment_people=None):
    """Today's dated payments and current outstanding arrears, with separate currencies."""
    today = state['today']
    payments = [p for p in state['payments'] if p['paid_on'] == today]
    valid = [p for p in payments if not p['voided']]
    debtors = sorted((s for s in state['students'] if s['overdue'] > 0),
                     key=lambda s: (-s['overdue'], s['name']))
    student_map = {s['id']: s for s in state['students']}
    collected_usd = sum(p['received_amount'] for p in valid if p['currency'] == 'USD')
    collected_ves = sum(p['received_amount'] for p in valid if p['currency'] == 'VES')
    income = sum(p['amount'] for p in valid)
    overdue = sum(s['overdue'] for s in debtors)
    summaries = [('Recibido en dólares', amount(collected_usd)),
                 ('Recibido en bolívares', amount(collected_ves, 'Bs')),
                 ('Total cobrado · equivalente USD', amount(income)),
                 ('Deuda vencida actual · USD', amount(overdue))]
    payment_lines = []
    for n, p in enumerate(payments, 1):
        current = student_map[p['student_id']]
        person = payment_people.get(p['id'], {}) if payment_people is not None else {
            'student_name': p['student_name'], 'grade_name': current['grade_name'],
            'guardian_name': current['guardian_name']}
        payment_lines.append([str(n), f"R-{p['id']:06d}",
            person.get('student_name', p['student_name'])+'\n'+(person.get('grade_name') or 'Grado no registrado'),
            person.get('guardian_name', current['guardian_name']), p['method']+'\n'+(p['reference'] or 'Sin referencia'),
            amount(p['received_amount'], 'Bs' if p['currency'] == 'VES' else 'USD'),
            amount(p['amount'])+'\n'+('Anulado' if p['voided'] else 'Válido')])
    debtor_lines = []
    for n, s in enumerate(debtors, 1):
        days = max((c['days_overdue'] for c in state['charges']
                    if c['student_id'] == s['id'] and c['overdue']), default=0)
        debtor_lines.append([str(n), s['name']+'\n'+s['student_code']+('\nArchivado' if s.get('archived') else ''),
            s['grade_name'], s['guardian_name']+'\n'+(s['guardian_phone'] or 'Sin teléfono'),
            amount(s['overdue']), f'{days} días'])
    now = datetime.now(timezone(timedelta(hours=-4)))
    day_label = datetime.strptime(today, '%Y-%m-%d').strftime('%d/%m/%Y')
    return {'title': 'Reporte diario de cobros y morosidad', 'school': state['settings'],
        'issued_on': today, 'issued_at': now.strftime('%d/%m/%Y · %H:%M'), 'operator': state['user']['name'],
        'filter_label': f'Cobros del {day_label} · Morosidad actual al emitir el reporte',
        'count_label': f"{len(valid)} {'cobro válido' if len(valid) == 1 else 'cobros válidos'} · "
                       f"{len(debtors)} {'alumno' if len(debtors) == 1 else 'alumnos'} con deuda vencida",
        'summaries': summaries, 'payment_count': len(valid), 'debtor_count': len(debtors),
        'received_usd': collected_usd, 'received_ves': collected_ves, 'income_usd': income, 'overdue_usd': overdue,
        'sections': [
            {'title': 'Cobros del día', 'headings': ['N.º', 'Recibo', 'Alumno / grado', 'Representante',
                'Método / referencia', 'Recibido', 'Equivalente USD / estado'],
             'widths': [26, 76, 163, 144, 122, 117, 110], 'lines': payment_lines,
             'empty_message': 'No hay cobros con fecha de hoy.'},
            {'title': 'Morosidad actual', 'headings': ['N.º', 'Alumno / código', 'Grado',
                'Representante / contacto', 'Vencido USD', 'Mayor atraso'],
             'widths': [26, 180, 115, 240, 105, 92], 'lines': debtor_lines,
             'empty_message': 'No hay alumnos con deuda vencida.'}],
        'note': 'Los totales incluyen cobros válidos; las anulaciones se muestran y se excluyen de los totales. '
                'Cada pago conserva su conversión original. La morosidad incluye cargos vencidos pendientes '
                'al generar el reporte, también de fichas archivadas.'}


def daily_pdf(data):
    pdf = DirectoryPDF(data)
    for label, value in data['summaries']:
        pdf.line(label+': '+value, True)
    pdf.y += 10
    for section in data['sections']:
        pdf.directory_table(section)
    pdf.line(data['note'])
    pdf.line('Generado por: '+data['operator'])
    return pdf.output()
