"""Cashea exports and PDFs without documents or birth dates of minors."""
import csv,io
from .cashea import NOTE,book,detail
from .db import ValidationError,local_today,valid_date
from .documents import PDF,amount
from .directory_reports import daily_pdf


def signed(cents,currency='USD'):
    return ('-' if cents<0 else '')+amount(abs(cents),currency)


def mark_trial(value,demo):
    if demo:
        value=dict(value,demo=True,school=dict(value['school']))
        school=value['school']
        school['legal_name']='PRUEBA SIN VALIDEZ - '+(school.get('legal_name') or school.get('school_name','Colegio'))
    return value


def document_pdf(db,kind,target,*,demo=False):
    doc=detail(db,kind,target)
    doc=mark_trial(doc,demo)
    pdf=PDF('Comprobante Cashea' if kind=='order' else 'Liquidación Cashea',doc['school'],size=(396,612))
    pdf.line(doc['code']+' · '+doc['state'],True)
    if doc['void_reason']:pdf.line('ANULADO: '+doc['void_reason'],True)
    if kind=='order' and doc['state']=='anulada':pdf.line('Anulada: anular también en el portal de Cashea',True)
    if kind=='order':
        pdf.line('Alumno: '+doc['student']['name'])
        pdf.line('Grado: '+doc['student']['grade_name'])
        pdf.line('Fecha: '+doc['ordered_on'])
        pdf.line(doc['invoice_label']+':')
        pdf.ensure(24);pdf.text(44,pdf.y,doc['invoice_number'] or 'No exigida',14,True);pdf.y+=24
        pdf.table(['Mensualidad','Período','Cubierto USD'],[[c['concept'],c['period'],amount(c['amount'])] for c in doc['charges']],[130,85,105])
        for label,key in (('Total','total_amount'),('Inicial pagada','initial_amount'),('Financiado por Cashea','financed_amount')):pdf.line(label+': '+amount(doc[key]),True)
        pdf.line('Liquidación esperada: '+doc['expected_on'])
        pdf.line('Referencia Cashea: '+(doc['reference'] or 'Sin referencia'))
        pdf.line('Recibo de inicial: '+(f"R-{doc['payment_id']:06d}" if doc['payment_id'] else 'No existe: inicial cero'))
    else:
        pdf.line('Fecha de recepción: '+doc['received_on'])
        pdf.line('Referencia bancaria: '+doc['reference'])
        pdf.line('Recibido: '+amount(doc['received_amount'],doc['currency']))
        pdf.line('Tasa VES/USD: '+doc['exchange_rate'])
        for label,key in (('Financiado bruto','gross_amount'),('Neto esperado','expected_amount'),('Recibido equivalente USD','amount'),('Diferencia contra neto','difference'),('Diferencia contra bruto','gross_difference')):pdf.line(label+': '+signed(doc[key]))
        pdf.line('Motivo: '+(doc['reason'] or 'Sin diferencia'))
        pdf.table(['Orden','Factura','Esperado USD'],[[o['code'],o['invoice_number'],amount(o['expected_amount'])] for o in doc['orders']],[90,125,105])
    pdf.line(NOTE)
    pdf.line('Registrado por: '+doc['operator'])
    return pdf.output()


def report(db,kind,user,query=None):
    if kind not in ('pending','settlements','sales'):raise ValidationError('Selecciona un informe Cashea válido.')
    data=book(db);query=query or {}
    start=valid_date(query.get('start',['2000-01-01'])[0]);end=valid_date(query.get('end',[local_today().isoformat()])[0])
    if start>end or end>local_today().isoformat():raise ValidationError('Revisa las fechas del informe Cashea.')
    if kind=='pending':
        title='Cashea por liquidar por semana'
        headers=['Semana','Órdenes','Financiado USD','Neto esperado USD','Vencidas']
        rows=[[w['week'],str(w['count']),amount(w['financed']),amount(w['expected']),str(w['overdue'])] for w in data['weeks']]
        detail_headers=['Orden','Alumno AL-','Factura','Venta','Esperada','Financiado USD','Neto esperado USD','Vencida']
        details=[[o['code'],o['student_code'],o['invoice_number'],o['ordered_on'],o['expected_on'],amount(o['financed_amount']),amount(o['expected_amount']),'Sí' if o['overdue'] else 'No'] for o in data['orders'] if o['state']=='por_liquidar']
    elif kind=='settlements':
        title='Liquidaciones Cashea recibidas'
        headers=['CL-','Fecha','Referencia','Moneda','Recibido original','Tasa','USD recibido','Neto esperado','Diferencia neto','Diferencia bruto','Motivo','Estado']
        rows=[[s['code'],s['received_on'],s['reference'],s['currency'],amount(s['received_amount'],s['currency']),s['exchange_rate'],amount(s['amount']),amount(s['expected_amount']),signed(s['difference']),signed(s['gross_difference']),s['reason'],'Anulada' if s['voided'] else 'Válida'] for s in data['settlements'] if start<=s['received_on']<=end]
        detail_headers=[];details=[]
    else:
        title='Ventas para Cashea'
        headers=['Orden','Factura','Fecha','Alumno AL-','Total USD','Inicial USD','Financiado USD','Estado']
        rows=[[o['code'],o['invoice_number'],o['ordered_on'],o['student_code'],amount(o['total_amount']),amount(o['initial_amount']),amount(o['financed_amount']),o['state']] for o in data['orders'] if start<=o['ordered_on']<=end]
        detail_headers=[];details=[]
    sections=[dict(title=title,headings=headers,widths=[758//len(headers)]*len(headers),lines=rows)]
    if details:sections.append(dict(title='Detalle de órdenes pendientes',headings=detail_headers,widths=[758//len(detail_headers)]*len(detail_headers),lines=details))
    return dict(title=title,school=dict(db.execute("SELECT key,value FROM settings WHERE key NOT LIKE 'id_floor_%'")),
        issued_on=local_today().isoformat(),issued_at=local_today().isoformat(),operator=user['name'],filter_label=f'{start} a {end}',
        count_label=str(len(rows))+' filas',summaries=[('Cashea pendiente de liquidar',amount(data['pending']))],sections=sections,
        headers=headers,rows=rows,detail_headers=detail_headers,details=details,note=NOTE+' El listado usa AL-, sin cédula, nacimiento ni nombre del menor.')


def export(db,kind,user,extension,query=None,*,demo=False):
    value=mark_trial(report(db,kind,user,query),demo)
    if extension=='pdf':return daily_pdf(value),'application/pdf'
    headers=value['headers'];rows=value['rows']
    if demo:headers=['PRUEBA SIN VALIDEZ · '+headers[0],*headers[1:]]
    def safe(v):
        v=str(v)
        return "'"+v if v.lstrip().startswith(('=','+','-','@')) or v.isdecimal() else v
    if extension=='csv':
        out=io.StringIO(newline='');writer=csv.writer(out,delimiter=';');writer.writerow(headers)
        writer.writerows([[safe(v) for v in row] for row in rows])
        return ('\ufeff'+out.getvalue()).encode('utf-8'),'text/csv; charset=utf-8'
    if extension=='xlsx':
        from .administration import import_template
        return import_template(True,columns=headers,roster_rows=rows,report_title='Cashea'),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    raise ValidationError('Formato Cashea inválido.')
