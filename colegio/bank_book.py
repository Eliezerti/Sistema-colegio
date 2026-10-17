"""Administrator-only statement import and reconciliation; original money is immutable."""
import base64,binascii,json
from datetime import datetime,timezone,date
from .db import ValidationError,audit,integer,required,money,valid_period,local_today
from .income_book import account
from .income_rules import parse_statement,Movement,proposals,allocation_plan,reference,IncomeError
from .administration import ensure_open_day

ACTIONS={'bank-profile','bank-preview','bank-import','bank-link','bank-auto','bank-unlink','bank-classify','bank-unclassify'}
SOURCES={'P':('payments','paid_on','payment_accounts','payment_id','credit'),
 'E':('expenses','spent_on','expense_accounts','expense_id','debit'),
 'O':('other_income','received_on',None,'other_id','credit'),
 'D':('cash_deposits','deposited_on',None,'deposit_id','credit')}
CLASSIFICATIONS=('Mensualidad no registrada','Otro ingreso','Entre cuentas propias','Préstamo o aporte','Reintegro','Otro')

def now():return datetime.now(timezone.utc).isoformat()
def reason(data):
    result=required(data,'reason',1000)
    if len(result)<10:raise ValidationError('Explica el motivo con al menos diez caracteres.')
    return result

def ledger(db):
    result=[]
    for prefix,(table,on,join,key,direction) in SOURCES.items():
        if join:
            sql='SELECT p.*,a.account_id,a.bcv_rate FROM '+table+' p JOIN '+join+' a ON a.'+key+'=p.id JOIN school_accounts s ON s.id=a.account_id WHERE p.voided=0 AND s.kind=\'bank\''
        else:sql='SELECT p.* FROM '+table+' p WHERE p.voided=0'
        for row in db.execute(sql):
            row=dict(row);amount=row['amount'] if prefix=='D' else row['received_amount']
            result.append(dict(id=prefix+str(row['id']),account=row['account_id'],on=row[on],amount=amount,currency=row['currency'],reference=row['reference'],direction=direction,bcv_rate=row.get('bcv_rate','')))
            if len(result)>20000:raise ValidationError('Divide la revisión por cuenta o período antes de superar 20.000 movimientos.')
    return result

def movement(row):return Movement(row['id'],row['account'],row['on'],row['amount'],row['currency'],row['reference'],row['direction'])
def banks(db):
    return [dict(id=str(r['id']),account=r['account_id'],on=r['movement_on'],amount=r['amount'],currency=r['currency'],reference=r['reference'],direction=r['direction'],description=r['description']) for r in db.execute('SELECT * FROM bank_movements ORDER BY id')]

def used(db):
    ub={};ul={}
    for row in db.execute('SELECT * FROM reconciliation_links WHERE voided=0'):
        bid=str(row['movement_id']);ub[bid]=ub.get(bid,0)+row['amount']
        for prefix,(_,_,_,column,_) in SOURCES.items():
            if row[column] is not None:
                lid=prefix+str(row[column]);ul[lid]=ul.get(lid,0)+row['amount']
    return ub,ul

def unchanged(db,prefix,identifier):
    column=SOURCES[prefix][3]
    if db.execute('SELECT 1 FROM reconciliation_links WHERE '+column+'=? AND voided=0',(identifier,)).fetchone():
        raise ValidationError('El movimiento está conciliado. Administración debe revisar y desvincular primero, con motivo.')

def preview(db,data):
    chosen=account(db,data.get('account_id'));name=required(data,'filename',200)
    encoded=data.get('file_base64')
    if not isinstance(encoded,str) or len(encoded)>2666672:raise ValidationError('Archivo demasiado grande; máximo 2 MB.')
    try:raw=base64.b64decode(encoded,validate=True)
    except (ValueError,binascii.Error):raise ValidationError('Archivo codificado inválido.') from None
    profile=data.get('profile')
    if data.get('profile_id'):
        saved=db.execute('SELECT profile_json FROM statement_profiles WHERE id=?',(integer(data['profile_id'],1,2147483647),)).fetchone()
        if not saved:raise ValidationError('Perfil inexistente.')
        profile=json.loads(saved[0])
    parsed=parse_statement(raw,name,profile,chosen)
    duplicate_file=db.execute('SELECT id FROM statement_imports WHERE account_id=? AND file_sha256=?',(chosen.id,parsed['file_sha256'])).fetchone()
    overlaps=[]
    for entry in parsed['rows']:
        known=db.execute('SELECT fingerprint FROM bank_movements WHERE account_id=? AND bank_id=?',(chosen.id,entry['bank_id'])).fetchone() if entry['bank_id'] else None
        if known:
            overlaps.append(dict(row=entry['row'],definite=True,conflict=known[0]!=entry['fingerprint'],reason='Identificador bancario ya importado' if known[0]==entry['fingerprint'] else 'El mismo ID bancario tiene otro contenido: requiere revisión externa'))
        elif db.execute('SELECT 1 FROM bank_movements WHERE account_id=? AND fingerprint=?',(chosen.id,entry['fingerprint'])).fetchone():
            overlaps.append(dict(row=entry['row'],definite=False,reason='Contenido ya visto; revisar si es otro movimiento legítimo'))
    return chosen,name,profile,parsed,duplicate_file,overlaps

def view_preview(parts):
    chosen,name,profile,parsed,prior,overlaps=parts
    return dict(file_sha256=parsed['file_sha256'],rows_count=len(parsed['rows']),duplicates=parsed['duplicates'],overlaps=overlaps,
        already_imported=prior[0] if prior else None,rows=[dict(vars(e['movement']),description=e['description'],bank_id=e['bank_id'],row=e['row']) for e in parsed['rows'][:100]],
        truncated=len(parsed['rows'])>100,status='VISTA PREVIA · NO VERIFICADO con un extracto real del banco')

def action(db,endpoint,data,user):
    if user['role']!='admin':raise PermissionError('Solo Administración importa, clasifica y concilia extractos.')
    try:return _action(db,endpoint,data,user)
    except IncomeError as error:raise ValidationError(str(error)) from None

def _action(db,endpoint,data,user):
    uid=user['id']
    if endpoint=='bank-profile':
        name=required(data,'name',200);profile=data.get('profile')
        # Validate the mapping through the same strict CSV parser, without any bank data.
        from .income_rules import Account,parse_csv
        if not isinstance(profile,dict) or not isinstance(profile.get('columns'),dict):raise ValidationError('Completa el mapeo de columnas.')
        import csv,io
        out=io.StringIO(newline='');writer=csv.writer(out,delimiter=profile.get('delimiter',';'))
        columns=profile['columns'];headers=list(columns.values());writer.writerow(headers)
        values={'date':'01/01/2000' if profile.get('date_format')=='%d/%m/%Y' else '2000-01-01','amount':'1','reference':'0001','description':'Ejemplo','bank_id':'FICTICIO'}
        writer.writerow([values.get(k,'') for k in columns]);parse_csv(out.getvalue().encode(profile.get('encoding','utf-8-sig')),profile,Account(1,'Ejemplo','USD'))
        payload=json.dumps(profile,ensure_ascii=False);identifier=data.get('id')
        if identifier:
            identifier=integer(identifier,1,2147483647)
            if not db.execute('SELECT 1 FROM statement_profiles WHERE id=?',(identifier,)).fetchone():raise ValidationError('Perfil inexistente.')
            db.execute('UPDATE statement_profiles SET name=?,profile_json=?,updated_by=?,updated_at=? WHERE id=?',(name,payload,uid,now(),identifier))
        else:
            if db.execute('SELECT COUNT(*) FROM statement_profiles').fetchone()[0]>=100:raise ValidationError('Revisa los perfiles existentes; máximo 100.')
            identifier=db.execute('INSERT INTO statement_profiles(name,profile_json,updated_by,updated_at) VALUES(?,?,?,?)',(name,payload,uid,now())).lastrowid
        audit(db,uid,endpoint,dict(id=identifier,status='NO VERIFICADO'));return dict(id=identifier)
    if endpoint in ('bank-preview','bank-import'):
        parts=preview(db,data);chosen,name,profile,parsed,prior,overlaps=parts
        if endpoint=='bank-preview':
            audit(db,uid,endpoint,dict(sha256=parsed['file_sha256'],count=len(parsed['rows']),account_id=chosen.id));return view_preview(parts)
        if prior:return dict(id=prior[0],duplicate=True,imported=0)
        if data.get('confirmed_hash')!=parsed['file_sha256']:raise ValidationError('Revisa la vista previa antes de importar.')
        if any(e.get('conflict') for e in overlaps):raise ValidationError('Un identificador bancario ya importado tiene contenido distinto. No se sobrescribió ni importó el extracto; revisa con el banco.')
        possible={e['row'] for e in parsed['duplicates']}|{e['row'] for e in overlaps if not e['definite']}
        accepted=data.get('accepted_duplicate_rows',[])
        if not isinstance(accepted,list) or {integer(v,2,10001) for v in accepted}!=possible:
            raise ValidationError('Confirma explícitamente cada posible duplicado sin ID bancario o revisa otro archivo.')
        why=reason(data) if possible else ''
        definite={e['row'] for e in overlaps if e['definite']}
        entries=[e for e in parsed['rows'] if e['row'] not in definite]
        for entry in entries:ensure_open_day(db,entry['movement'].on)
        iid=db.execute('INSERT INTO statement_imports(account_id,file_sha256,filename,profile_json,rows_count,imported_by,imported_at,review_reason) VALUES(?,?,?,?,?,?,?,?)',
            (chosen.id,parsed['file_sha256'],name,json.dumps(profile,ensure_ascii=False),len(entries),uid,now(),why)).lastrowid
        for entry in entries:
            m=entry['movement'];db.execute('INSERT INTO bank_movements(import_id,account_id,movement_on,direction,amount,currency,reference,description,bank_id,fingerprint,source_row) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (iid,chosen.id,m.on,m.direction,m.amount,m.currency,m.reference,entry['description'],entry['bank_id'],entry['fingerprint'],entry['row']))
        audit(db,uid,endpoint,dict(id=iid,sha256=parsed['file_sha256'],count=len(entries),duplicate_ids_skipped=len(definite),account_id=chosen.id,possible_duplicates_confirmed=len(possible)))
        return dict(id=iid,imported=len(entries),duplicate_ids_skipped=len(definite))
    if endpoint in ('bank-link','bank-auto'):
        bs=banks(db);ls=ledger(db);ub,ul=used(db)
        if endpoint=='bank-auto':
            classified={str(r[0]) for r in db.execute('SELECT movement_id FROM bank_classifications WHERE voided=0')}
            pending_b=[b for b in bs if not ub.get(b['id']) and b['id'] not in classified];pending_l=[l for l in ls if not ul.get(l['id'])]
            links=[];bank_index={b['id']:b for b in pending_b}
            for p in proposals(map(movement,pending_b),map(movement,pending_l)):
                if p['unique']:
                    # Empty references are suggestions only; they do not identify a deposit.
                    b=bank_index[p['bank_id']]
                    if reference(b['reference']):links.append(dict(movement_id=b['id'],source=p['candidates'][0],amount=f"{b['amount']//100}.{b['amount']%100:02d}"))
            why='Cruce único por cuenta, moneda, centavos, referencia y fecha ±3 días'
        else:links=data.get('links');why=reason(data)
        if not isinstance(links,list) or len(links)>10000 or endpoint=='bank-link' and not links:raise ValidationError('Indica los vínculos revisados.')
        normalized=[]
        for item in links:
            if not isinstance(item,dict):raise ValidationError('Vínculo inválido.')
            normalized.append((str(integer(item.get('movement_id'),1,2147483647)),str(item.get('source','')),money(item.get('amount'))))
        allocation_plan(map(movement,bs),map(movement,ls),normalized,already_bank=ub,already_ledger=ul)
        bm={b['id']:b for b in bs};lm={l['id']:l for l in ls}
        for bid,lid,amount in normalized:
            ensure_open_day(db,bm[bid]['on']);ensure_open_day(db,lm[lid]['on'])
            if db.execute('SELECT 1 FROM bank_classifications WHERE movement_id=? AND voided=0',(int(bid),)).fetchone():raise ValidationError('Retira primero la clasificación anterior con motivo.')
            column=SOURCES[lid[0]][3]
            db.execute('INSERT INTO reconciliation_links(movement_id,'+column+',amount,reason,created_by,created_at) VALUES(?,?,?,?,?,?)',(int(bid),int(lid[1:]),amount,why,uid,now()))
        audit(db,uid,endpoint,dict(count=len(normalized)));return dict(linked=len(normalized))
    if endpoint in ('bank-unlink','bank-unclassify'):
        table='reconciliation_links' if endpoint=='bank-unlink' else 'bank_classifications';identifier=integer(data.get('id'),1,2147483647);why=reason(data)
        row=db.execute('SELECT * FROM '+table+' WHERE id=? AND voided=0',(identifier,)).fetchone()
        if not row:raise ValidationError('Registro inexistente o ya retirado.')
        bank=db.execute('SELECT movement_on FROM bank_movements WHERE id=?',(row['movement_id'],)).fetchone();ensure_open_day(db,bank[0])
        if table=='reconciliation_links':
            for prefix,(_,on,_,column,_) in SOURCES.items():
                if row[column] is not None:ensure_open_day(db,db.execute('SELECT '+on+' FROM '+SOURCES[prefix][0]+' WHERE id=?',(row[column],)).fetchone()[0])
        db.execute('UPDATE '+table+' SET voided=1,void_reason=? WHERE id=?',(why,identifier));audit(db,uid,endpoint,dict(id=identifier,reason=why));return dict(voided=True)
    if endpoint=='bank-classify':
        identifier=integer(data.get('movement_id'),1,2147483647);category=required(data,'category');why=reason(data);support=required(data,'support',1000)
        if category not in CLASSIFICATIONS:raise ValidationError('Selecciona una clasificación válida.')
        bank=db.execute('SELECT * FROM bank_movements WHERE id=?',(identifier,)).fetchone()
        if not bank or bank['direction']!='credit':raise ValidationError('Clasifica un depósito existente.')
        ensure_open_day(db,bank['movement_on'])
        if db.execute('SELECT 1 FROM reconciliation_links WHERE movement_id=? AND voided=0',(identifier,)).fetchone() or db.execute('SELECT 1 FROM bank_classifications WHERE movement_id=? AND voided=0',(identifier,)).fetchone():raise ValidationError('Ya existe un vínculo o clasificación; revisa primero.')
        cid=db.execute('INSERT INTO bank_classifications(movement_id,category,support,reason,created_by,created_at) VALUES(?,?,?,?,?,?)',(identifier,category,support,why,uid,now())).lastrowid
        audit(db,uid,endpoint,dict(id=cid,movement_id=identifier,category=category));return dict(id=cid)
    raise ValidationError('Operación inexistente.')

def report(db,user,month,*,days=7,offset=0):
    valid_period(month);days=integer(days,1,3650);offset=integer(offset,0,10000000)
    bs=banks(db);ls=ledger(db);ub,ul=used(db)
    classified={str(r[0]) for r in db.execute('SELECT movement_id FROM bank_classifications WHERE voided=0')}
    selected=[b for b in bs if b['on'].startswith(month)];total=[]
    for currency in ('USD','VES'):
        amounts=lambda rows,d:sum(r['amount'] for r in rows if r['currency']==currency and r['direction']==d)
        total.append(dict(currency=currency,bank_credit=amounts(selected,'credit'),bank_debit=amounts(selected,'debit'),
            linked=sum(ub.get(r['id'],0) for r in selected if r['currency']==currency),
            unexplained=sum(r['amount']-ub.get(r['id'],0) for r in selected if r['currency']==currency and r['id'] not in classified)))
    result=dict(month=month,totals=total)
    if user['role']!='admin':return result
    pending_b=[b for b in bs if b['amount']>ub.get(b['id'],0) and b['id'] not in classified]
    pending_l=[l for l in ls if l['amount']>ul.get(l['id'],0)]
    hints=proposals(map(movement,pending_b),map(movement,pending_l));bybank={p['bank_id']:p for p in hints}
    for b in pending_b:b.update(remaining=b['amount']-ub.get(b['id'],0),proposal=bybank[b['id']],age_days=(local_today()-date.fromisoformat(b['on'])).days)
    for l in pending_l:l.update(remaining=l['amount']-ul.get(l['id'],0),age_days=(local_today()-date.fromisoformat(l['on'])).days)
    differences=[]
    grouped={}
    for l in pending_l:
        if reference(l['reference']):grouped.setdefault((l['account'],l['currency'],l['direction'],reference(l['reference'])),[]).append(l)
    for b in pending_b:
        for l in grouped.get((b['account'],b['currency'],b['direction'],reference(b['reference'])),[]):
            if abs((date.fromisoformat(b['on'])-date.fromisoformat(l['on'])).days)<=3 and b['remaining']!=l['remaining']:
                differences.append(dict(movement_id=b['id'],source=l['id'],bank_amount=b['remaining'],ledger_amount=l['remaining'],currency=b['currency'],reason='Referencia y fecha próximas; diferencia de importe'))
                if len(differences)>=100:break
        if len(differences)>=100:break
    result.update(profiles=[dict(id=r['id'],name=r['name'],profile=json.loads(r['profile_json']),status=r['status']) for r in db.execute('SELECT * FROM statement_profiles ORDER BY name')],
        imports=[dict(r) for r in db.execute('SELECT id,account_id,file_sha256,rows_count,imported_by,imported_at FROM statement_imports ORDER BY id DESC LIMIT 100 OFFSET ?',(offset,))],
        bank_pending=[b for b in pending_b if b['on'].startswith(month)][offset:offset+100],ledger_pending=[l for l in pending_l if l['on'].startswith(month)][offset:offset+100],
        older=[dict(source='Banco',id=b['id'],on=b['on'],currency=b['currency'],remaining=b['remaining'],reason='Sin vínculo o clasificación') for b in pending_b if b['age_days']>days][:100]+[dict(source='Libro',id=l['id'],on=l['on'],currency=l['currency'],remaining=l['remaining'],reason='Sin movimiento bancario que lo cubra') for l in pending_l if l['age_days']>days][:100],
        differences=differences,links=[dict(r) for r in db.execute('SELECT * FROM reconciliation_links ORDER BY id DESC LIMIT 100 OFFSET ?',(offset,))],
        classifications=[dict(r) for r in db.execute('SELECT * FROM bank_classifications ORDER BY id DESC LIMIT 100 OFFSET ?',(offset,))])
    return result
