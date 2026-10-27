"""Manual Cashea sales and bank settlements. No API, installments or fiscal numbering."""
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
import hashlib,json,re,secrets

from .db import (ValidationError,PAYMENT_METHODS,audit,charges,convert_received,integer,
                 local_today,money,next_record_id,record_payment,required,valid_date)

ACTIONS={'cashea-preview','cashea-settlement-preview','cashea-order','cashea-settlement','cashea-void-order',
         'cashea-void-settlement','cashea-settings','cashea-order-date'}
ADMIN={'cashea-void-order','cashea-void-settlement','cashea-settings'}
NOTE='Valida el tratamiento contable de comisiones y diferencias con tu contador. No se crea un egreso automático. El comprobante no es factura fiscal.'


def checkpoint(stage):
    """Actual child-process crash tests; no runtime bypass or external switch."""


def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def stamp():return datetime.now(timezone.utc).isoformat()


def percent(value):
    try:
        value=Decimal(str(value))
        if not value.is_finite() or not 0<=value<=100 or value!=value.quantize(Decimal('.01')):raise ValueError()
        return format(value,'f'),int(value*100)
    except (InvalidOperation,ValueError,TypeError):raise ValidationError('Usa un porcentaje entre 0 y 100, con hasta dos decimales.') from None


def expected_date(on,weekday=2):
    parsed=date.fromisoformat(on)
    return (parsed+timedelta(days=(weekday-parsed.weekday())%7 or 7)).isoformat()


def text(data,key,limit=200):
    value=data.get(key,'')
    if not isinstance(value,str) or len(value)>limit:raise ValidationError('El campo '+key+' no es válido.')
    return value.strip()


def zero_conversion(db,amount,currency,on):
    received=money(amount)
    if received:return convert_received(db,dict(amount=amount,currency=currency),on)
    if currency not in ('USD','VES'):raise ValidationError('Moneda inválida.')
    row=db.execute('SELECT rate FROM exchange_rates WHERE rate_date=?',(on,)).fetchone()
    if currency=='VES' and not row:raise ValidationError('Registra primero la tasa de la fecha de la operación.')
    return 0,currency,0,row[0] if currency=='VES' else '1'


def settings(db):
    from .cashea_schema import DEFAULTS
    return {key:(db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone() or [value])[0] for key,value in DEFAULTS.items()}


def preview(db,data,user):
    if user['role'] not in ('admin','cashier'):raise PermissionError('Solo Administración o Caja puede registrar una venta Cashea.')
    from .administration import ensure_open_day
    sid=integer(data.get('student_id'),1,2147483647)
    person=db.execute('''SELECT s.id,s.name,s.student_code,g.name AS grade_name FROM students s
        JOIN grades g ON g.id=s.grade_id WHERE s.id=?''',(sid,)).fetchone()
    if not person:raise ValidationError('Selecciona un alumno existente.')
    on=valid_date(data.get('ordered_on'))
    if on>local_today().isoformat():raise ValidationError('La fecha de venta no puede ser futura.')
    ensure_open_day(db,on)
    config=settings(db)
    total=money(data.get('total'))
    if total<=0:raise ValidationError('El total Cashea debe ser positivo.')
    pending=[c for c in charges(db,sid) if c['balance']>0]
    remaining=total;plan=[]
    for charge in pending:
        if not remaining:break
        if charge['concept']!='Mensualidad':raise ValidationError('Hay un cargo anterior de otro concepto. Revísalo y cóbralo por la vía normal antes de usar Cashea.')
        part=min(remaining,charge['balance'])
        plan.append(dict(id=charge['id'],period=charge['period'],concept=charge['concept'],
                         balance_before=charge['balance'],amount=part))
        remaining-=part
    if remaining:raise ValidationError('El total supera la deuda pendiente de mensualidades.')
    selected=data.get('charge_ids')
    if selected is not None and (not isinstance(selected,list) or selected!=[c['id'] for c in plan]):
        raise ValidationError('Selecciona las mensualidades pendientes más antiguas que cubren el total. Revisa nuevamente los cargos.')
    initial,currency,received,rate=zero_conversion(db,data.get('initial_received','0'),data.get('initial_currency','USD'),on)
    if initial>total:raise ValidationError('La inicial no puede superar el total de la venta.')
    method=data.get('initial_method','Efectivo')
    if method not in PAYMENT_METHODS:raise ValidationError('Selecciona el método real de la inicial, no Cashea.')
    initial_percent,_=percent(data.get('initial_percent','0'))
    financed=total-initial
    _,bps=percent(config['cashea_commission_percent'])
    commission=(financed*bps+5000)//10000
    invoice=text(data,'invoice_number',100);invoice_key=''.join(invoice.upper().split())
    if config['cashea_invoice_required']=='1' and not invoice:raise ValidationError('Escribe el número de factura de la venta.')
    duplicates=[r[0] for r in db.execute('SELECT id FROM cashea_orders WHERE invoice_key=? ORDER BY id',(invoice_key,))] if invoice else []
    invoice_reason=text(data,'invoice_reason',500)
    if duplicates and (data.get('invoice_duplicate_confirmed') is not True or not invoice_reason):
        raise ValidationError('La factura ya aparece en otra venta. Revisa el duplicado y confirma con un motivo.')
    expected=valid_date(data.get('expected_on') or expected_date(on,int(config['cashea_settlement_day'])))
    if expected<on:raise ValidationError('La liquidación esperada no puede ser anterior a la venta.')
    result=dict(student=dict(person),ordered_on=on,total_amount=total,initial_percent=initial_percent,
        initial_amount=initial,initial_currency=currency,initial_received=received,initial_rate=rate,
        initial_method=method,initial_reference=text(data,'initial_reference'),financed_amount=financed,
        invoice_number=invoice,invoice_key=invoice_key,invoice_duplicates=duplicates,invoice_reason=invoice_reason,
        reference=text(data,'reference'),expected_on=expected,commission_bps=bps,commission_amount=commission,
        expected_amount=financed-commission,charges=plan,student_balance_before=sum(c['balance'] for c in pending),
        student_balance_after=sum(c['balance'] for c in pending)-total,
        school={k:v for k,v in db.execute('SELECT key,value FROM settings') if k in ('school_name','legal_name','institution_type','rif','address','fiscal_address','phone','email','logo')},
        operator=user['name'],note=NOTE)
    result['preview_hash']=digest(result)
    return result


def create_order(db,data,user):
    value=preview(db,data,user)
    if data.get('preview_hash')!=value['preview_hash']:raise ValidationError('La vista previa cambió. Revisa la venta antes de confirmar.')
    target=next_record_id(db,'cashea_orders');code=f'CA-{target:06d}'
    state='por_liquidar' if value['financed_amount'] else 'liquidada'
    fields=dict(id=target,code=code,student_id=value['student']['id'],ordered_on=value['ordered_on'],
        total_amount=value['total_amount'],initial_percent=value['initial_percent'],initial_amount=value['initial_amount'],
        financed_amount=value['financed_amount'],invoice_number=value['invoice_number'],invoice_key=value['invoice_key'],
        reference=value['reference'],expected_on=value['expected_on'],state=state,commission_bps=value['commission_bps'],
        commission_amount=value['commission_amount'],expected_amount=value['expected_amount'],snapshot_json='{}',
        created_by=user['id'],created_at=stamp())
    db.execute('INSERT INTO cashea_orders('+','.join(fields)+') VALUES('+','.join('?' for _ in fields)+')',tuple(fields.values()))
    checkpoint('order_created')
    payment=None
    if value['initial_amount']:
        meta={k:value[k] for k in ('total_amount','initial_amount','financed_amount','invoice_number','expected_on')}
        meta.update(code=code,charge_totals={str(c['id']):c['amount'] for c in value['charges']})
        payment=record_payment(db,dict(student_id=value['student']['id'],paid_on=value['ordered_on'],
            currency=value['initial_currency'],amount=data.get('initial_received'),method=value['initial_method'],
            reference=value['initial_reference'],notes='Inicial de '+code,
            request_key='cashea-inicial-'+secrets.token_hex(16),duplicate_reference_confirmed=data.get('duplicate_reference_confirmed'),
            duplicate_reason=data.get('duplicate_reason')),user['id'],cashea=meta)['id']
    remaining=value['initial_amount']
    for charge in value['charges']:
        cash=min(remaining,charge['amount']);remaining-=cash
        financed=charge['amount']-cash
        if financed:db.execute('INSERT INTO cashea_allocations VALUES(?,?,?)',(target,charge['id'],financed))
    snapshot=dict(value,id=target,code=code,payment_id=payment);snapshot.pop('preview_hash')
    db.execute('UPDATE cashea_orders SET payment_id=?,snapshot_json=? WHERE id=?',(payment,canonical(snapshot),target))
    audit(db,user['id'],'cashea-order',dict(id=target,code=code,total=value['total_amount'],initial=value['initial_amount'],financed=value['financed_amount'],invoice_duplicates=value['invoice_duplicates'],invoice_reason=value['invoice_reason']))
    return dict(saved=True,id=target,code=code,payment_id=payment)


def settle(db,data,user,*,preview_only=False):
    from .administration import ensure_open_day
    ids=data.get('order_ids')
    if not isinstance(ids,list) or not 1<=len(ids)<=500:raise ValidationError('Marca de una a 500 órdenes pendientes.')
    ids=[integer(i,1,2147483647) for i in ids]
    if len(set(ids))!=len(ids):raise ValidationError('No repitas una orden en la liquidación.')
    orders=[dict(r) for r in db.execute('SELECT * FROM cashea_orders WHERE id IN ('+','.join('?' for _ in ids)+') ORDER BY id',ids)]
    if len(orders)!=len(ids) or any(o['state']!='por_liquidar' or not o['financed_amount'] for o in orders):
        raise ValidationError('Alguna orden ya no está pendiente. Revisa nuevamente la selección.')
    on=valid_date(data.get('received_on'))
    if on>local_today().isoformat() or any(o['ordered_on']>on for o in orders):raise ValidationError('La recepción no puede ser futura ni anterior a las ventas.')
    ensure_open_day(db,on)
    amount,currency,received,rate=zero_conversion(db,data.get('amount'),data.get('currency','USD'),on)
    expected=sum(o['expected_amount'] for o in orders);gross=sum(o['financed_amount'] for o in orders)
    difference=amount-expected;gross_difference=amount-gross
    reason=text(data,'reason',500)
    if (difference or gross_difference) and not reason and not preview_only:raise ValidationError('Explica la diferencia o comisión antes de confirmar la liquidación.')
    reference=required(data,'reference',200);reference_key=''.join(reference.upper().split())
    if db.execute('SELECT 1 FROM cashea_settlements WHERE voided=0 AND received_on=? AND currency=? AND reference_key=?',(on,currency,reference_key)).fetchone():
        raise ValidationError('Esta referencia bancaria ya está registrada para la fecha y moneda. Revisa la liquidación anterior.')
    review=dict(order_ids=sorted(ids),orders=[{k:o[k] for k in ('id','code','state','financed_amount','expected_amount')} for o in orders],received_on=on,currency=currency,received_amount=received,exchange_rate=rate,amount=amount,expected_amount=expected,gross_amount=gross,difference=difference,gross_difference=gross_difference,reason=reason,reference=reference)
    review['preview_hash']=digest(review)
    if preview_only:return review
    if data.get('preview_hash')!=review['preview_hash']:raise ValidationError('La liquidación cambió. Revisa nuevamente la selección y los importes.')
    target=next_record_id(db,'cashea_settlements');code=f'CL-{target:06d}'
    snapshot=dict(code=code,received_on=on,currency=currency,received_amount=received,exchange_rate=rate,amount=amount,
        gross_amount=gross,expected_amount=expected,difference=difference,gross_difference=gross_difference,
        reference=reference,reason=reason,orders=[{k:o[k] for k in ('id','code','invoice_number','financed_amount','expected_amount')} for o in orders],
        school=dict(db.execute('SELECT key,value FROM settings WHERE key NOT LIKE \'id_floor_%\'')),operator=user['name'],note=NOTE)
    fields=dict(id=target,code=code,received_on=on,currency=currency,received_amount=received,exchange_rate=rate,
        amount=amount,reference=reference,reference_key=reference_key,gross_amount=gross,expected_amount=expected,
        difference=difference,gross_difference=gross_difference,reason=reason,created_by=user['id'],created_at=stamp(),snapshot_json=canonical(snapshot))
    db.execute('INSERT INTO cashea_settlements('+','.join(fields)+') VALUES('+','.join('?' for _ in fields)+')',tuple(fields.values()))
    for order in orders:
        db.execute('INSERT INTO cashea_settlement_orders(settlement_id,order_id,expected_amount) VALUES(?,?,?)',(target,order['id'],order['expected_amount']))
        db.execute("UPDATE cashea_orders SET state='liquidada' WHERE id=?",(order['id'],))
    audit(db,user['id'],'cashea-settlement',dict(id=target,code=code,orders=sorted(ids),received=amount,expected=expected,difference=difference,gross_difference=gross_difference,reason=reason))
    return dict(saved=True,id=target,code=code,amount=amount,expected_amount=expected,difference=difference,gross_difference=gross_difference)


def action(db,endpoint,data,user,void_payment):
    if user['role']=='reader' or (endpoint in ADMIN and user['role']!='admin'):raise PermissionError('Tu perfil no permite esta operación Cashea.')
    if endpoint=='cashea-preview':return preview(db,data,user)
    if endpoint=='cashea-settlement-preview':return settle(db,data,user,preview_only=True)
    key=required(data,'request_key',100)
    if not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',key):raise ValidationError('La solicitud Cashea no tiene una clave válida. Abre nuevamente el formulario.')
    token=hashlib.sha256(key.encode()).hexdigest();body=digest({k:v for k,v in data.items() if k!='request_key'})
    cached=db.execute('SELECT * FROM cashea_requests WHERE request_key=?',(token,)).fetchone()
    if cached:
        if (cached['action'],cached['user_id'],cached['body_hash'])!=(endpoint,user['id'],body):raise ValidationError('La clave ya se usó con otra operación, usuario o contenido.')
        return json.loads(cached['response_json'])
    from .administration import ensure_open_day
    if endpoint=='cashea-order':result=create_order(db,data,user)
    elif endpoint=='cashea-settlement':result=settle(db,data,user)
    elif endpoint=='cashea-settings':
        weekday=integer(data.get('cashea_settlement_day'),0,6)
        grace=integer(data.get('cashea_grace_days'),0,365)
        pct,_=percent(data.get('cashea_commission_percent'))
        required_invoice=data.get('cashea_invoice_required')
        if required_invoice not in (True,False,'0','1','on'):raise ValidationError('Revisa si la factura es obligatoria.')
        values=dict(cashea_settlement_day=str(weekday),cashea_grace_days=str(grace),cashea_commission_percent=pct,
            cashea_invoice_required='1' if required_invoice in (True,'1','on') else '0')
        previous=settings(db)
        for k,v in values.items():db.execute('UPDATE settings SET value=? WHERE key=?',(v,k))
        audit(db,user['id'],endpoint,dict(before=previous,after=values));result=dict(saved=True,settings=values)
    else:
        target=integer(data.get('id'),1,2147483647);reason=required(data,'reason',500)
        if endpoint=='cashea-void-settlement':
            row=db.execute('SELECT * FROM cashea_settlements WHERE id=? AND voided=0',(target,)).fetchone()
            if not row:raise ValidationError('Liquidación inexistente o ya anulada.')
            ensure_open_day(db,row['received_on'])
            ids=[r[0] for r in db.execute('SELECT order_id FROM cashea_settlement_orders WHERE settlement_id=? AND active=1',(target,))]
            db.execute('UPDATE cashea_settlement_orders SET active=0 WHERE settlement_id=?',(target,))
            for oid in ids:db.execute("UPDATE cashea_orders SET state='por_liquidar' WHERE id=? AND state='liquidada'",(oid,))
            db.execute('UPDATE cashea_settlements SET voided=1,void_reason=?,voided_on=? WHERE id=?',(reason,local_today().isoformat(),target))
        elif endpoint in ('cashea-void-order','cashea-order-date'):
            row=db.execute("SELECT * FROM cashea_orders WHERE id=? AND state<>'anulada'",(target,)).fetchone()
            if not row:raise ValidationError('Orden inexistente o ya anulada.')
            ensure_open_day(db,row['ordered_on'])
            if endpoint=='cashea-order-date':
                expected=valid_date(data.get('expected_on'))
                if row['state']!='por_liquidar' or expected<row['ordered_on']:raise ValidationError('Solo se cambia la fecha de una orden pendiente, sin anticiparla a la venta.')
                db.execute('UPDATE cashea_orders SET expected_on=? WHERE id=?',(expected,target))
            else:
                if db.execute('SELECT 1 FROM cashea_settlement_orders WHERE order_id=? AND active=1',(target,)).fetchone():raise ValidationError('Anula primero la liquidación de esta orden.')
                if row['payment_id']:void_payment(row['payment_id'],reason,target)
                db.execute("UPDATE cashea_orders SET state='anulada',void_reason=?,voided_on=? WHERE id=?",(reason,local_today().isoformat(),target))
        else:raise ValidationError('Operación Cashea desconocida.')
        audit(db,user['id'],endpoint,dict(id=target,reason=reason));result=dict(saved=True,id=target)
    errors=integrity_errors(db)
    if errors:raise ValidationError('No se confirmó Cashea: '+errors[0])
    db.execute('INSERT INTO cashea_requests VALUES(?,?,?,?,?,?)',(token,endpoint,user['id'],body,canonical(result),stamp()))
    checkpoint('action_complete')
    return result


def cash_rows(db,cutoff=None):
    condition='(voided_on IS NULL OR voided_on>?) AND received_on<=?' if cutoff else 'voided=0'
    return [{k:r[k] for k in r.keys() if k!='snapshot_json'} for r in db.execute('SELECT * FROM cashea_settlements WHERE '+condition+' ORDER BY received_on,id', (cutoff,cutoff) if cutoff else ())]


def decorate_charges(db,entries):
    from .documents import amount
    covered={}
    for sql,field in (("SELECT a.charge_id,a.amount FROM cashea_allocations a JOIN cashea_orders o ON o.id=a.order_id WHERE o.state<>'anulada'",'financed'),
                      ("SELECT a.charge_id,a.amount FROM allocations a JOIN cashea_orders o ON o.payment_id=a.payment_id WHERE o.state<>'anulada'",'initial')):
        for cid,value in db.execute(sql):
            item=covered.setdefault(cid,dict(initial=0,financed=0));item[field]+=value
    for charge in entries:
        if charge['id'] in covered:
            value=covered[charge['id']]
            charge['cashea_initial']=value['initial'];charge['cashea_financed']=value['financed']
            charge['cashea_label']=('Pagada con Cashea' if not charge['balance'] else 'Incluye Cashea')+' (inicial '+amount(value['initial'])+' + financiado '+amount(value['financed'])+')'
    return entries


def extend_cash_summary(db,result):
    on=result['closed_on']
    sales=[dict(r) for r in db.execute('SELECT id,state,financed_amount FROM cashea_orders WHERE ordered_on=? ORDER BY id',(on,))]
    received=[dict(r) for r in db.execute('SELECT * FROM cashea_settlements WHERE received_on=? ORDER BY id',(on,))]
    if not sales and not received:return result
    lines={(r['method'],r['currency']):r for r in result['lines']}
    for row in received:
        result['movements'].append(dict(type='cashea_settlement',id=row['id'],amount=row['amount'],currency=row['currency'],received_amount=row['received_amount'],voided=row['voided'],reference=row['reference'],exchange_rate=row['exchange_rate'],method='Transferencia'))
        if row['voided']:continue
        key=('Transferencia',row['currency'])
        entry=lines.setdefault(key,dict(method=key[0],currency=key[1],income=0,expense=0,net=0,income_usd=0,expense_usd=0))
        entry['income']+=row['received_amount'];entry['income_usd']+=row['amount'];entry['net']=entry['income']-entry['expense']
    result['cashea_orders']=sales
    result['cashea']=cutoff_summary(db,on,on)
    result['lines']=[lines[k] for k in sorted(lines)]
    result['income_usd']=sum(line['income_usd'] for line in result['lines'])
    result['preview_hash']=digest(dict(movements=result['movements'],orders=sales,cashea=result['cashea']))
    return result


def cutoff_summary(db,start,end):
    orders=[dict(r) for r in db.execute("SELECT * FROM cashea_orders WHERE ordered_on<=? AND (voided_on IS NULL OR voided_on>?)",(end,end))]
    settled={r[0] for r in db.execute('''SELECT so.order_id FROM cashea_settlement_orders so JOIN cashea_settlements s ON s.id=so.settlement_id
        WHERE s.received_on<=? AND (s.voided_on IS NULL OR s.voided_on>?)''',(end,end))}
    sales=[o for o in orders if start<=o['ordered_on']<=end]
    received=[s for s in cash_rows(db,end) if start<=s['received_on']<=end]
    pending=[o for o in orders if o['id'] not in settled and o['financed_amount']]
    liquidated_ids={r[0] for r in db.execute('''SELECT so.order_id FROM cashea_settlement_orders so JOIN cashea_settlements s ON s.id=so.settlement_id
        WHERE s.received_on BETWEEN ? AND ? AND (s.voided_on IS NULL OR s.voided_on>?)''',(start,end,end))}
    return dict(sold=sum(o['total_amount'] for o in sales),initial=sum(o['initial_amount'] for o in sales),
        financed=sum(o['financed_amount'] for o in sales),received=sum(s['amount'] for s in received),
        settled_financed=sum(o['financed_amount'] for o in orders if o['id'] in liquidated_ids),
        pending=sum(o['financed_amount'] for o in pending),expected_pending=sum(o['expected_amount'] for o in pending),
        differences=sum(s['gross_difference'] for s in received),start=start,end=end)


def book(db):
    config=settings(db);today=local_today();groups={}
    orders=[dict(r) for r in db.execute('''SELECT o.*,s.name AS student_name,s.student_code FROM cashea_orders o
        JOIN students s ON s.id=o.student_id ORDER BY o.expected_on,o.id''')]
    for order in orders:
        order.pop('snapshot_json')
        limit=date.fromisoformat(order['expected_on'])+timedelta(days=int(config['cashea_grace_days']))
        order['overdue']=order['state']=='por_liquidar' and order['financed_amount']>0 and today>limit
        if order['state']=='por_liquidar':
            week=(date.fromisoformat(order['expected_on'])-timedelta(days=date.fromisoformat(order['expected_on']).weekday())).isoformat()
            group=groups.setdefault(week,dict(week=week,financed=0,expected=0,count=0,overdue=0))
            group['financed']+=order['financed_amount'];group['expected']+=order['expected_amount'];group['count']+=1;group['overdue']+=int(order['overdue'])
    settlements=[dict(r) for r in db.execute('SELECT * FROM cashea_settlements ORDER BY received_on DESC,id DESC')]
    for s in settlements:s.pop('snapshot_json')
    return dict(settings=config,orders=orders,settlements=settlements,weeks=[groups[k] for k in sorted(groups)],
        pending=sum(o['financed_amount'] for o in orders if o['state']=='por_liquidar'),
        overdue_count=sum(o['overdue'] for o in orders),note=NOTE)


def detail(db,kind,target):
    target=integer(target,1,2147483647)
    table='cashea_orders' if kind=='order' else 'cashea_settlements'
    row=db.execute('SELECT * FROM '+table+' WHERE id=?',(target,)).fetchone()
    if not row:raise ValidationError('Documento Cashea inexistente.')
    value=json.loads(row['snapshot_json'])
    return dict(value,id=row['id'],state=row['state'] if kind=='order' else ('anulada' if row['voided'] else 'liquidada'),
                void_reason=row['void_reason'],**({'expected_on':row['expected_on']} if kind=='order' else {}))


def integrity_errors(db):
    checks=(
      ('La cobertura financiada no coincide con la orden.','''SELECT o.id FROM cashea_orders o LEFT JOIN cashea_allocations a ON a.order_id=o.id GROUP BY o.id HAVING o.financed_amount<>COALESCE(SUM(a.amount),0)'''),
      ('La inicial no coincide con su pago.','''SELECT o.id FROM cashea_orders o LEFT JOIN payments p ON p.id=o.payment_id WHERE (o.initial_amount>0 AND (p.id IS NULL OR p.amount<>o.initial_amount OR p.student_id<>o.student_id OR p.paid_on<>o.ordered_on OR p.voided<>(o.state='anulada'))) OR (o.initial_amount=0 AND o.payment_id IS NOT NULL)'''),
      ('Una asignación Cashea corresponde a otro alumno o un cargo anulado.','''SELECT a.order_id FROM cashea_allocations a JOIN cashea_orders o ON o.id=a.order_id JOIN charges c ON c.id=a.charge_id WHERE c.student_id<>o.student_id OR (c.cancelled<>0 AND o.state<>'anulada')'''),
      ('El estado de una orden no coincide con su liquidación.','''SELECT o.id FROM cashea_orders o WHERE (o.financed_amount>0 AND o.state='liquidada')<>(EXISTS(SELECT 1 FROM cashea_settlement_orders so JOIN cashea_settlements s ON s.id=so.settlement_id WHERE so.order_id=o.id AND so.active=1 AND s.voided=0))'''),
      ('Una liquidación no coincide con sus órdenes.','''SELECT s.id FROM cashea_settlements s LEFT JOIN cashea_settlement_orders so ON so.settlement_id=s.id LEFT JOIN cashea_orders o ON o.id=so.order_id GROUP BY s.id HAVING s.gross_amount<>COALESCE(SUM(o.financed_amount),0) OR s.expected_amount<>COALESCE(SUM(so.expected_amount),0)'''),
      ('Una membresía de liquidación tiene un estado inválido.','''SELECT so.order_id FROM cashea_settlement_orders so JOIN cashea_settlements s ON s.id=so.settlement_id JOIN cashea_orders o ON o.id=so.order_id WHERE so.active<>1-s.voided OR so.expected_amount<>o.expected_amount OR (so.active=1 AND o.state<>'liquidada')'''),
    )
    errors=[message for message,sql in checks if db.execute(sql).fetchone()]
    for table,fields in (('cashea_orders',('total_amount','initial_amount','financed_amount','commission_bps','commission_amount','expected_amount')),
                         ('cashea_settlements',('amount','received_amount','gross_amount','expected_amount','difference','gross_difference')),
                         ('cashea_allocations',('amount',)),('cashea_settlement_orders',('expected_amount',))):
        if db.execute('SELECT 1 FROM '+table+' WHERE '+' OR '.join("typeof("+field+")<>'integer'" for field in fields)).fetchone():
            errors.append('Cashea contiene un importe que no es un entero en centavos.');break
    for row in db.execute('SELECT * FROM cashea_settlements'):
        try:
            from .db import valid_rate
            rate=Decimal(valid_rate(row['exchange_rate']))
            calculated=int((Decimal(row['received_amount'])/rate).quantize(Decimal('1'),rounding=ROUND_HALF_UP)) if row['currency']=='VES' else row['received_amount']
            if calculated!=row['amount'] or (row['currency']=='USD' and rate!=1):raise ValueError()
            if (row['difference'] or row['gross_difference']) and not row['reason'].strip():raise ValueError()
        except (ValueError,InvalidOperation):errors.append('Una liquidación Cashea tiene conversión o motivo inválidos.');break
    if db.execute('''SELECT 1 FROM cashea_orders WHERE commission_amount<>(financed_amount*commission_bps+5000)/10000
        OR (state='anulada')<>(voided_on IS NOT NULL) OR (state='anulada' AND trim(void_reason)='')''').fetchone():
        errors.append('Una orden Cashea tiene comisión o anulación inválida.')
    if db.execute("SELECT 1 FROM cashea_settlements WHERE voided<>(voided_on IS NOT NULL) OR (voided=1 AND trim(void_reason)='')").fetchone():
        errors.append('Una liquidación Cashea tiene anulación inválida.')
    from .db import BALANCES
    if db.execute('SELECT 1 FROM ('+BALANCES+') WHERE paid>amount').fetchone():errors.append('La cobertura supera el importe de un cargo.')
    return errors
