"""School account classification, cash deposits and distinct non-tuition income."""
from datetime import datetime,timezone
import hashlib
import json
from .db import ValidationError,audit,integer,required,valid_date,local_today,money,convert_received,valid_period
from .income_rules import Account,destination,suggested_account,cash_deposit,IncomeError
from .administration import ensure_open_day

ADMIN={'income-account','income-category','income-assign','income-other','income-void-other','income-void-deposit'}
ACTIONS=ADMIN|{'income-deposit'}


def account(db,identifier):
    r=db.execute('SELECT * FROM school_accounts WHERE id=?',(integer(identifier,1,2147483647),)).fetchone()
    if not r:raise ValidationError('Cuenta inexistente.')
    return Account(r['id'],r['name'],r['currency'],r['kind'],r['bank'],r['last4'],bool(r['active']))


def bcv(db,on,currency,rate):
    if currency=='VES':return rate
    row=db.execute('SELECT rate FROM exchange_rates WHERE rate_date=?',(on,)).fetchone()
    return row[0] if row else ''


def current_accounts(db):return [dict(r) for r in db.execute('SELECT * FROM school_accounts ORDER BY name')]


def preferences(db):
    result={}
    for r in db.execute('''SELECT p.currency,p.method,a.account_id FROM payments p JOIN payment_accounts a ON a.payment_id=p.id
                          WHERE p.voided=0 ORDER BY p.id DESC'''):
        result.setdefault(r['currency']+'|'+r['method'],r['account_id'])
    return result


def bind_payment(db,data,result,uid):
    pid=result['id'];existing=db.execute('SELECT account_id FROM payment_accounts WHERE payment_id=?',(pid,)).fetchone()
    selected=data.get('account_id')
    if result.get('duplicate'):
        if selected and (not existing or existing[0]!=integer(selected,1,2147483647)):
            raise ValidationError('El pago ya existe con otra clasificación. No se cambió su cuenta.')
        return result
    row=db.execute('SELECT * FROM payments WHERE id=?',(pid,)).fetchone()
    if not selected:
        accounts=[Account(r['id'],r['name'],r['currency'],r['kind'],r['bank'],r['last4'],bool(r['active'])) for r in current_accounts(db)]
        selected=suggested_account(accounts,row['currency'],row['method'],preferences(db).get(row['currency']+'|'+row['method']))
    if not selected:raise ValidationError('Selecciona la cuenta destino. Administración debe configurar Cuentas del colegio si aún no hay cuentas.')
    chosen=account(db,selected);destination(chosen,row['currency'],row['method'])
    db.execute('INSERT INTO payment_accounts(payment_id,account_id,bcv_rate) VALUES(?,?,?)',(pid,chosen.id,bcv(db,row['paid_on'],row['currency'],row['exchange_rate'])))
    audit(db,uid,'income-payment-account',dict(payment_id=pid,account_id=chosen.id))
    return result


def bind_expense(db,data,eid,uid):
    if not data.get('account_id'):return
    row=db.execute('SELECT * FROM expenses WHERE id=?',(eid,)).fetchone();chosen=account(db,data['account_id'])
    if row['method']=='No especificado':
        if not chosen.active or chosen.currency!=row['currency']:raise ValidationError('Selecciona una cuenta activa de la misma moneda.')
    else:destination(chosen,row['currency'],row['method'])
    db.execute('INSERT INTO expense_accounts(expense_id,account_id,bcv_rate) VALUES(?,?,?)',(eid,chosen.id,bcv(db,row['spent_on'],row['currency'],row['exchange_rate'])))
    audit(db,uid,'income-expense-account',dict(expense_id=eid,account_id=chosen.id))


def on_day(data,key):
    on=valid_date(data.get(key))
    if on>local_today().isoformat():raise ValidationError('No se permiten movimientos futuros.')
    return on


def signature(fields):return hashlib.sha256(json.dumps(fields,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def retry(db,table,data,fields):
    key=required(data,'request_key',100)
    prior=db.execute('SELECT id,request_fingerprint FROM '+table+' WHERE request_key=?',(key,)).fetchone()
    digest=signature(fields)
    if prior:
        if prior['request_fingerprint']!=digest:raise ValidationError('La clave de operación ya se utilizó con otros datos.')
        return {'id':prior['id'],'duplicate':True},key,digest
    return None,key,digest


def action(db,endpoint,data,user):
    uid=user['id'];db.audit_user=uid
    if user['role']=='reader' or endpoint in ADMIN and user['role']!='admin':raise PermissionError('Tu perfil no permite esta operación.')
    try:return _action(db,endpoint,data,user)
    except IncomeError as error:raise ValidationError(str(error)) from None


def _action(db,endpoint,data,user):
    uid=user['id'];now=datetime.now(timezone.utc).isoformat()
    if endpoint=='income-account':
        identifier=integer(data['id'],1,2147483647) if data.get('id') else None
        active=data.get('active',True) in (True,'1','true','on')
        chosen=Account(identifier or 1,required(data,'name'),required(data,'currency',3),required(data,'kind',4),str(data.get('bank','')).strip(),str(data.get('last4','')).strip(),active)
        fields=dict(name=chosen.name,bank=chosen.bank,currency=chosen.currency,kind=chosen.kind,last4=chosen.last4,active=int(active))
        if identifier:
            prior=account(db,identifier)
            if (prior.currency,prior.kind)!=(chosen.currency,chosen.kind):
                raise ValidationError('La moneda y el tipo de una cuenta no cambian. Desactívala y crea otra para conservar el historial.')
            db.execute('UPDATE school_accounts SET name=:name,bank=:bank,last4=:last4,active=:active WHERE id=:id',dict(fields,id=identifier))
        else:
            if db.execute('SELECT COUNT(*) FROM school_accounts').fetchone()[0]>=200:raise ValidationError('Máximo 200 cuentas; revisa las existentes.')
            identifier=db.execute('INSERT INTO school_accounts(name,bank,currency,kind,last4,active) VALUES(:name,:bank,:currency,:kind,:last4,:active)',fields).lastrowid
        audit(db,uid,endpoint,dict(id=identifier,active=active));return {'id':identifier}
    if endpoint=='income-category':
        name=required(data,'name');identifier=data.get('id');active=data.get('active',True) in (True,'1','true','on')
        if identifier:
            identifier=integer(identifier,1,2147483647)
            if not db.execute('SELECT 1 FROM income_categories WHERE id=?',(identifier,)).fetchone():raise ValidationError('Categoría inexistente.')
            db.execute('UPDATE income_categories SET name=?,active=? WHERE id=?',(name,int(active),identifier))
        else:
            if db.execute('SELECT COUNT(*) FROM income_categories').fetchone()[0]>=200:raise ValidationError('Máximo 200 categorías; revisa las existentes.')
            identifier=db.execute('INSERT INTO income_categories(name,active) VALUES(?,?)',(name,int(active))).lastrowid
        audit(db,uid,endpoint,dict(id=identifier,active=active));return {'id':identifier}
    if endpoint=='income-assign':
        kind=data.get('kind');ids=data.get('ids');reason=required(data,'reason',500)
        if kind not in ('payments','expenses') or not isinstance(ids,list) or not 1<=len(ids)<=500 or len(set(map(str,ids)))!=len(ids) or len(reason)<10:
            raise ValidationError('Selecciona de 1 a 500 registros distintos y explica la revisión con al menos diez caracteres.')
        chosen=account(db,data.get('account_id'));target='payment_accounts' if kind=='payments' else 'expense_accounts';column='payment_id' if kind=='payments' else 'expense_id';date_key='paid_on' if kind=='payments' else 'spent_on'
        for value in ids:
            identifier=integer(value,1,2147483647);row=db.execute('SELECT * FROM '+kind+' WHERE id=?',(identifier,)).fetchone()
            if not row or row['voided']:raise ValidationError('Hay un movimiento inexistente o anulado.')
            ensure_open_day(db,row[date_key])
            if not chosen.active or chosen.currency!=row['currency']:raise ValidationError('Revisa moneda y cuenta activa.')
            if row['method']!='No especificado':destination(chosen,row['currency'],row['method'])
            db.execute('INSERT INTO '+target+'('+column+',account_id,bcv_rate) VALUES(?,?,?) ON CONFLICT('+column+') DO UPDATE SET account_id=excluded.account_id',
                       (identifier,chosen.id,''))
        audit(db,uid,endpoint,dict(kind=kind,ids=ids,account_id=chosen.id,reason=reason));return {'assigned':len(ids)}
    if endpoint=='income-other':
        on=on_day(data,'received_on');amount,currency,received,rate=convert_received(db,data,on)
        chosen=account(db,data.get('account_id'));method=required(data,'method');destination(chosen,currency,method)
        category=integer(data.get('category_id'),1,2147483647)
        if not db.execute('SELECT 1 FROM income_categories WHERE id=? AND active=1',(category,)).fetchone():raise ValidationError('Selecciona una categoría activa.')
        fields=dict(concept=required(data,'concept'),category_id=category,received_on=on,amount=amount,currency=currency,received_amount=received,
            exchange_rate=rate,bcv_rate=bcv(db,on,currency,rate),account_id=chosen.id,method=method,reference=str(data.get('reference',''))[:200],support=required(data,'support',1000))
        prior,key,digest=retry(db,'other_income',data,{k:v for k,v in fields.items() if k not in ('amount','exchange_rate','bcv_rate')})
        if prior:return prior
        ensure_open_day(db,on)
        fields.update(created_by=uid,created_at=now,request_key=key,request_fingerprint=digest)
        columns=','.join(fields);identifier=db.execute('INSERT INTO other_income('+columns+') VALUES('+','.join(':'+k for k in fields)+')',fields).lastrowid
        audit(db,uid,endpoint,dict(id=identifier,account_id=chosen.id,amount=received,currency=currency));return {'id':identifier}
    if endpoint=='income-deposit':
        on=on_day(data,'deposited_on');chosen=account(db,data.get('account_id'));currency=required(data,'currency',3);amount=money(data.get('amount'))
        allocations=data.get('payments')
        if not isinstance(allocations,list) or not 1<=len(allocations)<=500:raise ValidationError('Vincula de 1 a 500 cobros en efectivo.')
        normalized=[]
        for entry in allocations:
            if not isinstance(entry,dict):raise ValidationError('Aplicación inválida.')
            normalized.append(dict(payment_id=integer(entry.get('payment_id'),1,2147483647),amount=money(entry.get('amount'))))
        normalized.sort(key=lambda r:r['payment_id'])
        fields=dict(deposited_on=on,amount=amount,currency=currency,account_id=chosen.id,reference=required(data,'reference'),support=required(data,'support',1000),difference_reason=str(data.get('difference_reason','')).strip()[:500])
        prior,key,digest=retry(db,'cash_deposits',data,dict(fields,payments=normalized))
        if prior:return prior
        ensure_open_day(db,on);payments=[]
        for entry in normalized:
            row=db.execute('SELECT * FROM payments WHERE id=?',(entry['payment_id'],)).fetchone()
            if not row or row['voided'] or row['paid_on']>on:raise ValidationError('Revisa que los recibos sean válidos y no posteriores al depósito.')
            used=db.execute('''SELECT COALESCE(SUM(a.amount),0) FROM cash_deposit_payments a JOIN cash_deposits d ON d.id=a.deposit_id
                                WHERE a.payment_id=? AND d.voided=0''',(row['id'],)).fetchone()[0]
            payments.append((row['id'],entry['amount'],row['received_amount']-used,row['currency'],row['method']))
        totals=cash_deposit(chosen,amount,payments,currency=currency,reason=fields['difference_reason'])
        fields.update(difference=totals['difference'],created_by=uid,created_at=now,request_key=key,request_fingerprint=digest)
        identifier=db.execute('INSERT INTO cash_deposits('+','.join(fields)+') VALUES('+','.join(':'+k for k in fields)+')',fields).lastrowid
        db.executemany('INSERT INTO cash_deposit_payments VALUES(?,?,?)',[(identifier,r['payment_id'],r['amount']) for r in normalized])
        audit(db,uid,endpoint,dict(id=identifier,account_id=chosen.id,amount=amount,currency=currency,difference=fields['difference'],payment_ids=[r['payment_id'] for r in normalized]));return {'id':identifier}
    if endpoint in ('income-void-other','income-void-deposit'):
        table,column=('other_income','received_on') if endpoint=='income-void-other' else ('cash_deposits','deposited_on')
        identifier=integer(data.get('id'),1,2147483647);reason=required(data,'reason',500)
        row=db.execute('SELECT * FROM '+table+' WHERE id=?',(identifier,)).fetchone()
        if not row or row['voided'] or len(reason)<10:raise ValidationError('Revisa el movimiento y explica la anulación con al menos diez caracteres.')
        ensure_open_day(db,row[column]);db.execute('UPDATE '+table+' SET voided=1,void_reason=? WHERE id=?',(reason,identifier))
        audit(db,uid,endpoint,dict(id=identifier,reason=reason));return {'saved':True}
    raise ValidationError('Operación desconocida del libro de ingresos.')


def report(db,user,period,*,offset=0):
    period=valid_period(period);offset=integer(offset,0,10000000)
    accounts=current_accounts(db)
    totals={}
    for table,column,original,direction in (('payments','paid_on','received_amount','income'),('other_income','received_on','received_amount','other'),('expenses','spent_on','received_amount','expense')):
        for r in db.execute('SELECT currency,SUM('+original+') AS total FROM '+table+' WHERE voided=0 AND substr('+column+',1,7)=? GROUP BY currency',(period,)):
            totals.setdefault(r['currency'],dict(currency=r['currency'],income=0,other=0,expense=0))[direction]=r['total']
    result=dict(period=period,totals=list(totals.values()),accounts=accounts,
        unassigned={kind:db.execute('SELECT COUNT(*) FROM '+kind+' p LEFT JOIN '+link+' a ON a.'+key+'=p.id WHERE a.'+key+' IS NULL AND p.voided=0').fetchone()[0]
                    for kind,link,key in (('payments','payment_accounts','payment_id'),('expenses','expense_accounts','expense_id'))})
    if user['role']=='reader':
        result['accounts']=[{k:a[k] for k in ('id','name','currency','kind','active')} for a in accounts];return result
    result.update(categories=[dict(r) for r in db.execute('SELECT * FROM income_categories ORDER BY name')],
        other=[dict(r) for r in db.execute('SELECT * FROM other_income WHERE substr(received_on,1,7)=? ORDER BY id DESC LIMIT 100 OFFSET ?',(period,offset))],
        deposits=[dict(r) for r in db.execute('SELECT * FROM cash_deposits WHERE substr(deposited_on,1,7)=? ORDER BY id DESC LIMIT 100 OFFSET ?',(period,offset))],
        unassigned_payments=[dict(r) for r in db.execute('''SELECT p.id,p.paid_on,p.method,p.currency,p.received_amount FROM payments p LEFT JOIN payment_accounts a ON a.payment_id=p.id
                       WHERE a.payment_id IS NULL AND p.voided=0 ORDER BY p.id DESC LIMIT 100 OFFSET ?''',(offset,))],
        cash_available=[dict(r) for r in db.execute('''SELECT p.id,p.paid_on,p.currency,p.received_amount-COALESCE((SELECT SUM(a.amount) FROM cash_deposit_payments a JOIN cash_deposits d ON d.id=a.deposit_id WHERE a.payment_id=p.id AND d.voided=0),0) AS available
                     FROM payments p WHERE p.method='Efectivo' AND p.voided=0 AND available>0 ORDER BY p.id DESC LIMIT 100 OFFSET ?''',(offset,))],offset=offset)
    for key in ('other','deposits'):
        for row in result[key]:row.pop('request_key',None);row.pop('request_fingerprint',None)
    return result
