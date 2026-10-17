"""Monthly income relation and server-side locked periods; no tax calculation."""
from datetime import datetime,timezone
from decimal import Decimal
import csv,hashlib,io,json
from .db import ValidationError,audit,integer,required,valid_period,local_today
from .income_rules import equivalents,IncomeError
from .income_book import signature

ACTIONS={'month-close','month-reopen','month-annotation'}

def active(db,period):
    return db.execute('SELECT * FROM accounting_closures WHERE period=? AND reopened_at IS NULL',(period,)).fetchone()

def ensure_open(db,on):
    if active(db,on[:7]):raise ValidationError('Ese mes está cerrado. Administración debe reabrirlo con motivo antes de modificar el libro.')

def flags(db,source):
    prefix=source[:1];identifier=integer(source[1:],1,2147483647)
    if prefix not in ('P','O'):raise ValidationError('Selecciona un recibo P o un ingreso O.')
    column='payment_id' if prefix=='P' else 'other_id'
    row=db.execute('SELECT special_taxpayer,foreign_currency FROM income_annotations WHERE '+column+'=?',(identifier,)).fetchone()
    return dict(special_taxpayer=bool(row[0]) if row else False,foreign_currency=bool(row[1]) if row else False)

def live_report(db,period):
    period=valid_period(period)
    if period>local_today().isoformat()[:7]:raise ValidationError('Selecciona un mes actual o anterior.')
    records=[];expenses=[];groups={};totals=dict(income_usd=0,expenses_usd=0)
    account_names=dict(db.execute('SELECT id,name FROM school_accounts'))
    specs=(('P','payments','paid_on','payment_accounts','payment_id'),('O','other_income','received_on',None,'other_id'),('E','expenses','spent_on','expense_accounts','expense_id'))
    for prefix,table,on,join,key in specs:
        sql='SELECT p.*,a.account_id,a.bcv_rate FROM '+table+' p LEFT JOIN '+join+' a ON a.'+key+'=p.id' if join else 'SELECT p.* FROM '+table+' p'
        for row in db.execute(sql+' WHERE substr(p.'+on+',1,7)=? ORDER BY p.'+on+',p.id',(period,)):
            row=dict(row);account_id=row.get('account_id');bcv=row.get('bcv_rate') or (row['exchange_rate'] if row['currency']=='VES' else '')
            usd=ves=None
            if bcv:
                try:converted=equivalents(row['received_amount'],row['currency'],bcv);usd,ves=converted['usd'],converted['ves']
                except IncomeError:bcv=''
            concept=row.get('concept','')
            if prefix=='P':
                parts=[]
                for c in db.execute('SELECT DISTINCT c.period,c.concept,g.name AS grade FROM allocations a JOIN charges c ON c.id=a.charge_id JOIN students s ON s.id=c.student_id JOIN grades g ON g.id=s.grade_id WHERE a.payment_id=? ORDER BY c.period,c.id',(row['id'],)):
                    label='Mensualidad '+c['period']+' – '+c['grade'] if c['concept']=='Mensualidad' else c['concept']+' – '+c['grade']
                    parts.append(label)
                concept='; '.join(parts)
            item=dict(source=prefix+str(row['id']),date=row[on],receipt='R-'+str(row['id']).zfill(6) if prefix=='P' else '',invoice='',
                concept=concept,account_id=account_id,account=account_names.get(account_id,'Sin cuenta asignada'),method=row['method'],reference=row['reference'],currency=row['currency'],
                original_amount=row['received_amount'],bcv_rate=bcv,usd_equivalent=usd,ves_equivalent=ves,recorded_usd=row['amount'],
                verification='Tasa histórica conservada' if bcv else 'NO VERIFICADO · falta tasa BCV histórica',voided=bool(row['voided']),void_reason=row['void_reason'])
            if prefix!='E':item.update(flags(db,item['source']))
            (expenses if prefix=='E' else records).append(item)
            if not row['voided']:
                direction='expenses' if prefix=='E' else 'income';totals[direction+'_usd']+=row['amount']
                k=(row['currency'],row['method'],account_id)
                group=groups.setdefault(k,dict(currency=k[0],method=k[1],account=item['account'],account_id=account_id,income=0,expenses=0))
                group[direction]+=row['received_amount']
    totals['net_usd']=totals['income_usd']-totals['expenses_usd']
    from .bank_book import banks,ledger,used
    bs=[b for b in banks(db) if b['on'].startswith(period)];ls=[l for l in ledger(db) if l['on'].startswith(period)];ub,ul=used(db)
    classified={str(r[0]):r[1] for r in db.execute('SELECT movement_id,category FROM bank_classifications WHERE voided=0')}
    recon={}
    for row in bs:
        key=(row['account'],row['currency']);g=recon.setdefault(key,dict(account=account_names.get(key[0],'Sin cuenta'),currency=key[1],bank_credit=0,bank_debit=0,book_credit=0,book_debit=0,linked=0,classified=0))
        g['bank_'+row['direction']]+=row['amount'];g['linked']+=ub.get(row['id'],0)
        if row['id'] in classified:g['classified']+=row['amount']
    for row in ls:
        key=(row['account'],row['currency']);g=recon.setdefault(key,dict(account=account_names.get(key[0],'Sin cuenta'),currency=key[1],bank_credit=0,bank_debit=0,book_credit=0,book_debit=0,linked=0,classified=0))
        g['book_'+row['direction']]+=row['amount']
    for row in recon.values():row['difference']=(row['bank_credit']-row['bank_debit'])-(row['book_credit']-row['book_debit'])
    pending=dict(unassigned=sum(not r['account_id'] for r in (*records,*expenses) if not r['voided']),missing_rates=sum(not r['bcv_rate'] for r in (*records,*expenses) if not r['voided']),
        bank_unlinked=sum(1 for b in bs if b['id'] not in classified and b['amount']>ub.get(b['id'],0)),book_unlinked=sum(1 for l in ls if l['amount']>ul.get(l['id'],0)),
        unrecorded_tuition=sum(1 for b in bs if classified.get(b['id'])=='Mensualidad no registrada'))
    return dict(period=period,school={k:v for k,v in db.execute('SELECT key,value FROM settings') if k in ('school_name','institution_type','legal_name','rif','fiscal_address','address','phone','email','logo')},income=records,expenses=expenses,totals=totals,groups=list(groups.values()),reconciliation=list(recon.values()),pending=pending,
        note='Informe administrativo para revisión del contador. IVA e IGTF no se calculan. Factura vacía: módulo de facturas pendiente. Equivalencias NO VERIFICADAS quedan vacías; no se inventan tasas. Depósitos de efectivo son traslados, no ingresos. Diferencia bancaria por fecha original de cada lado; puede atravesar meses. Sin documentos ni fechas de nacimiento de menores.')

def report(db,period):
    period=valid_period(period);closed=active(db,period)
    if closed:
        result=json.loads(closed['snapshot_json'])
        if result.get('period')!=period or signature(result)!=closed['preview_hash']:raise ValidationError('No se pudo verificar la foto del cierre mensual; revisa el respaldo y la bitácora.')
        result['closure']=dict(id=closed['id'],closed_at=closed['closed_at'],closed_by=closed['closed_by']);result['closed']=True
    else:result=live_report(db,period);result['closure']=None;result['closed']=False
    result['preview_hash']=signature({k:v for k,v in result.items() if k not in ('preview_hash','closure','closed')})
    return result

def action(db,endpoint,data,user):
    if user['role']!='admin':raise PermissionError('Solo Administración cierra, reabre o marca información del libro.')
    uid=user['id']
    if endpoint=='month-annotation':
        source=required(data,'source',30);flags(db,source);prefix=source[0];identifier=int(source[1:]);table,on,column=('payments','paid_on','payment_id') if prefix=='P' else ('other_income','received_on','other_id')
        row=db.execute('SELECT '+on+' FROM '+table+' WHERE id=?',(identifier,)).fetchone()
        if not row:raise ValidationError('Ingreso inexistente.')
        from .administration import ensure_open_day
        ensure_open_day(db,row[0]);values=[]
        for key in ('special_taxpayer','foreign_currency'):
            if type(data.get(key)) is not bool:raise ValidationError('Marca explícitamente las opciones informativas.')
            values.append(int(data[key]))
        db.execute('INSERT INTO income_annotations('+column+',special_taxpayer,foreign_currency) VALUES(?,?,?) ON CONFLICT('+column+') DO UPDATE SET special_taxpayer=excluded.special_taxpayer,foreign_currency=excluded.foreign_currency',(identifier,*values))
        audit(db,uid,endpoint,dict(source=source,special_taxpayer=bool(values[0]),foreign_currency=bool(values[1]),informational_only=True));return dict(saved=True)
    if endpoint=='month-close':
        period=valid_period(data.get('period'))
        if active(db,period):raise ValidationError('El mes ya está cerrado.')
        result=live_report(db,period);digest=signature(result)
        if data.get('confirmed_hash')!=digest:raise ValidationError('Cambió el libro. Revisa nuevamente el resumen antes de cerrar.')
        if any(result['pending'].values()) and data.get('confirmed_pending') is not True:raise ValidationError('Revisa y confirma los pendientes antes de cerrar.')
        identifier=db.execute('INSERT INTO accounting_closures(period,snapshot_json,preview_hash,closed_by,closed_at) VALUES(?,?,?,?,?)',(period,json.dumps(result,ensure_ascii=False),digest,uid,datetime.now(timezone.utc).isoformat())).lastrowid
        audit(db,uid,endpoint,dict(id=identifier,period=period,preview_hash=digest,pending=result['pending']));return dict(id=identifier,closed=True)
    if endpoint=='month-reopen':
        identifier=integer(data.get('id'),1,2147483647);why=required(data,'reason',1000)
        if len(why)<10:raise ValidationError('Explica el motivo con al menos diez caracteres.')
        row=db.execute('SELECT period FROM accounting_closures WHERE id=? AND reopened_at IS NULL',(identifier,)).fetchone()
        if not row:raise ValidationError('Cierre inexistente o ya reabierto.')
        db.execute('UPDATE accounting_closures SET reopened_by=?,reopened_at=?,reopen_reason=? WHERE id=?',(uid,datetime.now(timezone.utc).isoformat(),why,identifier));audit(db,uid,endpoint,dict(id=identifier,period=row[0],reason=why));return dict(reopened=True)
    raise ValidationError('Operación inexistente.')

def decimal_amount(value):return '' if value is None else ('-' if value<0 else '')+f'{abs(value)//100}.{abs(value)%100:02d}'

def csv_bytes(data):
    out=io.StringIO(newline='');writer=csv.writer(out,delimiter=';')
    def line(values):writer.writerow(["'"+str(v) if str(v).lstrip().startswith(('=','+','-','@')) else str(v) for v in values])
    line(['Relación mensual de ingresos',data['period'],'Cerrado' if data['closed'] else 'Abierto'])
    line(['Origen','Fecha','Recibo','Factura','Concepto','Cuenta','Método','Referencia','Moneda','Importe original','Tasa BCV','USD equivalente','Bs equivalente','USD registrado','Sujeto pasivo especial','Pagado en divisas','Estado','Verificación'])
    for r in (*data['income'],*data['expenses']):line([r['source'],r['date'],r['receipt'],r['invoice'],r['concept'],r['account'],r['method'],r['reference'],r['currency'],decimal_amount(r['original_amount']),r['bcv_rate'],decimal_amount(r['usd_equivalent']),decimal_amount(r['ves_equivalent']),decimal_amount(r['recorded_usd']),'Sí' if r.get('special_taxpayer') else 'No','Sí' if r.get('foreign_currency') else 'No','Anulado' if r['voided'] else 'Válido',r['verification']])
    line([]);line(['Totales válidos por moneda, método y cuenta']);line(['Moneda','Método','Cuenta','Ingreso','Egreso','Neto'])
    for r in data['groups']:line([r['currency'],r['method'],r['account'],decimal_amount(r['income']),decimal_amount(r['expenses']),decimal_amount(r['income']-r['expenses'])])
    line([]);line(['Conciliación por cuenta y moneda']);line(['Cuenta','Moneda','Créditos banco','Débitos banco','Créditos libro','Débitos libro','Diferencia neta','Importe vinculado','Importe clasificado'])
    for r in data['reconciliation']:line([r['account'],r['currency'],*[decimal_amount(r[k]) for k in ('bank_credit','bank_debit','book_credit','book_debit','difference','linked','classified')]])
    line([]);line([data['note']]);return ('\ufeff'+out.getvalue()).encode('utf-8')

def pdf_bytes(data,user):
    from .directory_reports import daily_pdf
    from .documents import amount
    cols=['Origen / fecha','Recibo / factura','Concepto / cuenta','Método / referencia','Original / BCV','USD / Bs','Estado / opciones']
    def rows(items):
        return [[r['source']+'\n'+r['date'],r['receipt']+'\n'+r['invoice'],r['concept']+'\n'+r['account'],r['method']+'\n'+r['reference'],amount(r['original_amount'],r['currency'])+'\n'+(r['bcv_rate'] or 'NO VERIFICADO'),
            (amount(r['usd_equivalent'])+'\n'+amount(r['ves_equivalent'],'VES')) if r['bcv_rate'] else 'NO VERIFICADO',('Anulado' if r['voided'] else 'Válido')+(' · Especial' if r.get('special_taxpayer') else '')+(' · Divisas' if r.get('foreign_currency') else '')] for r in items]
    layout=dict(title='Relación mensual de ingresos',school=data['school'],issued_on=local_today().isoformat(),issued_at=datetime.now(timezone.utc).isoformat(),operator=user['name'],
        filter_label=data['period']+' · '+('CERRADO · foto conservada' if data['closed'] else 'ABIERTO · datos actuales'),count_label='Sin datos personales de menores',
        summaries=[('Ingresos válidos · USD conservado',amount(data['totals']['income_usd'])),('Egresos válidos · USD conservado',amount(data['totals']['expenses_usd'])),('Neto · USD conservado',amount(data['totals']['net_usd']))],
        sections=[dict(title='Ingresos',headings=cols,widths=[80,90,180,110,100,100,98],lines=rows(data['income'])),dict(title='Egresos',headings=cols,widths=[80,90,180,110,100,100,98],lines=rows(data['expenses'])),
            dict(title='Totales válidos por moneda, método y cuenta',headings=['Moneda','Método','Cuenta','Ingreso','Egreso'],widths=[70,130,258,150,150],lines=[[r['currency'],r['method'],r['account'],amount(r['income'],r['currency']),amount(r['expenses'],r['currency'])] for r in data['groups']]),
            dict(title='Diferencia neta banco contra libro',headings=['Cuenta','Moneda','Banco neto','Libro neto','Diferencia'],widths=[258,65,145,145,145],lines=[[r['account'],r['currency'],amount(r['bank_credit']-r['bank_debit'],r['currency']),amount(r['book_credit']-r['book_debit'],r['currency']),amount(r['difference'],r['currency'])] for r in data['reconciliation']])],note=data['note'])
    return daily_pdf(layout)
