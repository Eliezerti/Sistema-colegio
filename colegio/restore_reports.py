"""Restoration review and loss reports; never export bank accounts or credentials."""
import csv
import io

from .backup_inspection import fingerprint
from .documents import AdministrativePDF, amount

TABLE_LABELS = {
    'school_accounts':'Cuentas del colegio','payment_accounts':'Cuentas de cobros','expense_accounts':'Cuentas de egresos',
    'income_categories':'Categorías de otros ingresos','other_income':'Otros ingresos','cash_deposits':'Depósitos de efectivo',
    'cash_deposit_payments':'Cobertura de depósitos',
    'settings':'Configuración', 'users':'Usuarios', 'students':'Alumnos',
    'guardians':'Representantes', 'grades':'Grados y secciones', 'charges':'Cargos',
    'payments':'Pagos', 'expenses':'Egresos', 'allocations':'Aplicaciones de pagos',
    'employees':'Personal', 'enrollment_documents':'Constancias de matrícula',
    'exchange_rates':'Tasas BCV', 'monthly_assessments':'Mensualidades generadas',
    'salary_receipts':'Recibos del personal', 'year_transitions':'Pases de año',
    'payment_plans':'Convenios', 'collection_notes':'Seguimientos de cobranza',
    'positions':'Cargos del personal', 'payroll_plans':'Planes del personal',
    'guardian_documents':'Documentos del representante', 'cash_closures':'Cierres de caja',
}


def table_label(table):
    return TABLE_LABELS.get(table,'Otros registros')


def identity(table,row):
    if 'id' in row: return str(row['id'])
    if table=='payment_accounts':return str(row['payment_id'])
    if table=='expense_accounts':return str(row['expense_id'])
    if table=='cash_deposit_payments':return str(row['deposit_id'])+':'+str(row['payment_id'])
    if table=='settings': return row['key']
    if table=='allocations': return f"{row['payment_id']}:{row['charge_id']}"
    if table=='monthly_assessments': return f"{row['student_id']}:{row['period']}"
    if table=='exchange_rates': return row['rate_date']
    return fingerprint(row)


def normalized_records(data):
    # Compare the supported business model on both sides. A removed employee link
    # is not a changed amount or a lost expense. Original files remain untouched.
    from .schema import RETIRED
    result={table:[dict(row) for row in records] for table,records in data['records'].items() if table not in RETIRED}
    for row in result.get('expenses',[]):row.pop('employee_id',None)
    result['settings']=[r for r in result['settings'] if not (r['key'].startswith('id_floor_') and r['key'][9:] in RETIRED)]
    return result


def compare(current,incoming):
    current=dict(current,records=normalized_records(current))
    incoming=dict(incoming,records=normalized_records(incoming))
    details=[];counts={}
    students={r['id']:r['name'] for r in current['records']['students']}
    # Audit history is retained in the verified previous snapshot; sessions are ephemeral.
    for table,rows in current['records'].items():
        if table in ('audit','audit_links','audit_meta','sessions'): continue
        incoming_map={identity(table,r):r for r in incoming['records'].get(table,[])}
        for row in rows:
            if table=='settings' and row['key'].startswith('id_floor_'): continue
            other=incoming_map.get(identity(table,row))
            if other is not None and fingerprint(row)==fingerprint(other): continue
            counts[table]=counts.get(table,0)+1
            action='No está en el respaldo' if other is None else 'Contenido diferente'
            if table in ('payments','expenses'):
                if other and row.get('voided') and not other.get('voided'): action='Anulación se revierte'
                elif other and not row.get('voided') and other.get('voided'): action='Queda anulado'
                prefix='R' if table=='payments' else 'E'
                person=students.get(row.get('student_id'),'') if table=='payments' else ''
                if table=='payments':
                    import json
                    try: person=json.loads(row['receipt_snapshot'])['person'].get('student_name',person)
                    except (ValueError,TypeError,KeyError): pass
                details.append({'type':table,'action':action,'number':f"{prefix}-{row['id']:06d}",
                    'date':row.get('paid_on',row.get('spent_on','')),'person':person,
                    'amount_usd':row['amount'],'currency':row['currency'],'received':row['received_amount'],
                    'method':row.get('method','No especificado'),'reference':row.get('reference',''),
                    'before_state':'Anulado' if row['voided'] else 'Válido',
                    'after_state':('Anulado' if other['voided'] else 'Válido') if other else 'Ausente',
                    'before_hash':fingerprint(row),'after_hash':fingerprint(other) if other else None})
            elif table in ('students','guardians','enrollment_documents'):
                details.append({'type':table,'action':action,'number':str(row.get('student_code') or row['id']),
                    'date':row.get('created_at',''),'person':row.get('name',''),
                    'before_hash':fingerprint(row),'after_hash':fingerprint(other) if other else None})
            else:
                item={'type':table,'action':action,'number':identity(table,row),
                    'date':row.get('due_date',row.get('created_at',row.get('rate_date',''))),
                    'person':students.get(row.get('student_id'),row.get('name','')),
                    'before_hash':fingerprint(row),'after_hash':fingerprint(other) if other else None}
                if table=='charges':
                    item.update(amount_usd=row['amount'],received=row['amount'],currency='USD',method='Cargo',reference=row['period'],
                        before_state='Anulado' if row['cancelled'] else 'Vigente',
                        after_state=('Anulado' if other['cancelled'] else 'Vigente') if other else 'Ausente')
                    if other and row['cancelled'] and not other['cancelled']:item['action']='Anulación se revierte'
                details.append(item)
    return {'has_loss':bool(counts),'counts':counts,'details':details,
            'payment_changes':counts.get('payments',0),'expense_changes':counts.get('expenses',0),
            'date_note':'Comparación por ID, request_key y huella del contenido; no depende de fechas de archivos.'}


HEADERS=['Tipo','Acción','Correlativo','Fecha','Alumno / persona','Importe USD','Moneda recibida',
         'Importe recibido','Método','Referencia','Estado anterior','Estado en respaldo','Huella anterior','Huella en respaldo']


def loss_csv(comparison):
    out=io.StringIO(newline='');writer=csv.writer(out,delimiter=';');writer.writerow(HEADERS)
    for d in comparison['details']:
        values=[table_label(d['type']),d['action'],d['number'],d['date'],d['person'],
            f"{d['amount_usd']/100:.2f}" if 'amount_usd' in d else '',d.get('currency',''),
            f"{d['received']/100:.2f}" if 'received' in d else '',d.get('method',''),d.get('reference',''),
            d.get('before_state',''),d.get('after_state',''),d['before_hash'],d.get('after_hash') or '']
        writer.writerow(["'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v for v in values])
    return out.getvalue().encode('utf-8-sig')


def loss_pdf(comparison,operation_id):
    pdf=AdministrativePDF('INFORME DE PÉRDIDA POR RESTAURACIÓN',{'school_name':'Aula · Revisión de datos'},landscape=True)
    pdf.line('Operación: '+operation_id)
    pdf.line('Registros ausentes o diferentes: '+str(sum(comparison['counts'].values())))
    pdf.line('El estado exacto previo se conserva en antes-restauracion. Este informe no es un recibo.')
    rows=[]
    for d in comparison['details']:
        amounts=(amount(d['amount_usd'])+'\n'+amount(d['received'],d['currency'])) if 'amount_usd' in d else 'Ficha / documento'
        rows.append([d['number']+'\n'+d['date'],d['person'],d['action']+'\n'+d.get('before_state','')+' → '+d.get('after_state',''),
                     amounts,d.get('method','')+'\n'+d.get('reference','')])
    pdf.table(['Correlativo / fecha','Alumno / persona','Cambio al restaurar','USD / recibido','Método / referencia'],rows,[115,170,180,130,165])
    return pdf.output()
