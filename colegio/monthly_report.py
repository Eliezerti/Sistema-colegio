"""Monthly operations, currency-separated balances and actual audit-date annulments."""
import calendar
import csv
from datetime import date, datetime, timedelta, timezone
import io
import json

from .db import ValidationError,valid_period
from .documents import amount
from .directory_reports import daily_pdf


def report(db,state,period):
    period=valid_period(period)
    if period>state['today'][:7]:raise ValidationError('Selecciona un mes actual o anterior.')
    year,month=map(int,period.split('-'))
    start=f'{period}-01';end=date(year,month,calendar.monthrange(year,month)[1]).isoformat()
    income=expenses=0
    lines={}
    for table,key,direction in (('payments','paid_on','income'),('expenses','spent_on','expense')):
        for row in state[table]:
            if row['voided'] or row[key]>end:continue
            group=lines.setdefault((row['currency'],row['method']),dict(currency=row['currency'],method=row['method'],
                opening=0,income=0,expense=0,closing=0,income_usd=0,expense_usd=0))
            sign=1 if direction=='income' else -1
            if row[key]<start:group['opening']+=sign*row['received_amount']
            else:
                group[direction]+=row['received_amount'];group[direction+'_usd']+=row['amount']
                if direction=='income':income+=row['amount']
                else:expenses+=row['amount']
            group['closing']+=sign*row['received_amount']
    from .cashea import cash_rows,cutoff_summary
    cashea=cutoff_summary(db,start,end)
    for item in cash_rows(db,end):
        key=(item['currency'],'Transferencia')
        group=lines.setdefault(key,dict(currency=key[0],method=key[1],opening=0,income=0,expense=0,closing=0,income_usd=0,expense_usd=0))
        if item['received_on']<start:group['opening']+=item['received_amount']
        else:
            group['income']+=item['received_amount'];group['income_usd']+=item['amount'];income+=item['amount']
        group['closing']+=item['received_amount']
    student_map={s['id']:s for s in state['students']}
    pending={}
    for charge in state['charges']:
        if charge['balance'] and charge['due_date']<=end:
            grade=student_map[charge['student_id']]['grade_name']
            pending[grade]=pending.get(grade,0)+charge['balance']
    annulments=[]
    names={'void-payment':('Pago','R-'),'void-expense':('Egreso','E-'),'cancel-charge':('Cargo','C-'),
           'cashea-void-order':('Orden Cashea','CA-'),'cashea-void-settlement':('Liquidación Cashea','CL-')}
    for row in db.execute("SELECT id,created_at,action,details FROM audit WHERE action IN ('void-payment','void-expense','cancel-charge','cashea-void-order','cashea-void-settlement') ORDER BY id"):
        try:
            stamp=datetime.fromisoformat(row['created_at']).astimezone(timezone(timedelta(hours=-4)))
            if stamp.strftime('%Y-%m')!=period:continue
            detail=json.loads(row['details']);kind,prefix=names[row['action']]
            annulments.append(dict(audit_id=row['id'],date=stamp.date().isoformat(),kind=kind,
                number=prefix+str(detail['id']).zfill(6),reason=str(detail.get('reason','Sin motivo registrado'))[:500]))
        except (ValueError,KeyError,TypeError):
            raise ValidationError('No se pudo interpretar una anulación de la bitácora.') from None
    balances=[lines[k] for k in sorted(lines)]
    now=datetime.now(timezone(timedelta(hours=-4)))
    return dict(title='Informe mensual de cierre',school=state['settings'],issued_on=state['today'],
        issued_at=now.strftime('%d/%m/%Y · %H:%M'),operator=state['user']['name'],period=period,
        filter_label=f'Movimientos del {start} al {end} · datos disponibles al emitir',
        count_label=f'{period} · importes originales separados por moneda y método',
        income_usd=income,expenses_usd=expenses,net_usd=income-expenses,
        cashea=cashea,balances=balances,pending_by_grade=[{'grade':g,'pending':pending[g]} for g in sorted(pending)],
        annulments=annulments,
        summaries=[('Cobrado del mes · equivalente USD',amount(income)),
            ('Egresos del mes · equivalente USD',amount(expenses)),('Movimiento neto del mes · USD',amount(income-expenses))],
        sections=[
            dict(title='Caja por moneda y método',headings=['Moneda','Método','Saldo previo','Cobrado','Egresos','Saldo al cierre'],
                widths=[65,135,130,130,130,168],lines=[[r['currency'],r['method'],amount(r['opening'],r['currency']),
                    amount(r['income'],r['currency']),amount(r['expense'],r['currency']),amount(r['closing'],r['currency'])] for r in balances]),
            dict(title='Pendiente actual de cargos con vencimiento hasta fin del mes, por grado',
                headings=['Grado','Pendiente USD'],widths=[550,208],lines=[[g,amount(pending[g])] for g in sorted(pending)]),
            dict(title='Anulaciones realizadas durante el mes',headings=['Fecha','Tipo','Número','Motivo'],
                widths=[105,85,110,458],lines=[[r['date'],r['kind'],r['number'],r['reason']] for r in annulments])]+([dict(title='Cashea al corte · financiado no es caja',headings=['Concepto','USD'],widths=[550,208],lines=[[label,amount(cashea[key])] for label,key in (('Vendido en el mes','sold'),('Inicial de ventas del mes','initial'),('Financiado en el mes','financed'),('Liquidaciones recibidas en el mes','received'),('Financiado liquidado en el mes','settled_financed'),('Por liquidar al corte · bruto','pending'),('Por liquidar al corte · neto estimado','expected_pending'))])] if any(cashea[k] for k in ('sold','received','pending')) else []),
        note='Monedas separadas; los equivalentes USD conservan la tasa original. El saldo de caja acumula movimientos válidos '
            'hasta fin del mes, según su estado actual, sin inventar efectivo contado. El pendiente es el saldo actual de cargos '
            'con vencimiento hasta ese corte; no reconstruye una foto histórica. Las anulaciones se seleccionan por la fecha '
            'de la bitácora en Venezuela, aunque el movimiento sea de otro mes. No se incluyen nombres, documentos ni contactos de alumnos.')


def pdf_bytes(data):return daily_pdf(data)


def csv_bytes(data):
    output=io.StringIO(newline='');writer=csv.writer(output,delimiter=';')
    def safe(value):
        text=str(value)
        return "'"+text if text.lstrip().startswith(('=','+','-','@')) else text
    def row(values):writer.writerow([safe(value) for value in values])
    row([data['title'],data['period']]);row(['Emitido',data['issued_at']])
    for label,value in data['summaries']:row([label,value])
    for section in data['sections']:
        row([]);row([section['title']]);row(section['headings'])
        for line in section['lines']:row(line)
    row([]);row([data['note']])
    return ('\ufeff'+output.getvalue()).encode('utf-8')
