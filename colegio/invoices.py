"""Preprinted invoice tracking; operator-supplied numbers, never tax calculations."""
import base64
import csv
import hashlib
import io
import json
import re
import sqlite3
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
from .db import ValidationError,audit,integer,required,valid_date,valid_period,local_today
from .administration import ensure_open_day
from .documents import amount,period_label
from . import invoice_layout as layout

ADMIN={'invoice-config','invoice-batch','invoice-template','invoice-template-restore','invoice-import-template',
       'invoice-profile','invoice-test','invoice-void'}
WRITERS={'invoice-draft','invoice-edit-draft','invoice-issue','invoice-damaged','invoice-print','invoice-preview'}
ACTIONS=ADMIN|WRITERS
STATES={'draft':'Borrador','issued':'Emitida','void':'Anulada','damaged':'Hoja dañada o inutilizada'}
ISSUER_KEYS=('name','rif','address','printer_name','printer_rif','authorization','printed_on','notes')


def now():return datetime.now(timezone.utc).isoformat()
def encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def reason(data,key='reason'):
    value=layout.text(data.get(key),1000,'motivo',empty=False).strip()
    if len(value)<10:raise ValidationError('Explica el motivo con al menos diez caracteres.')
    return value


def printed(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{1,16}',value) or int(value)<1:
        raise ValidationError('Escribe un número preimpreso de 1 a 16 dígitos, mayor que cero.')
    return value,str(int(value))


def cents(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{1,9}(?:\.[0-9]{1,2})?',value):
        raise ValidationError('Importe inválido; usa como máximo dos decimales.')
    return int(Decimal(value)*100)


def decimal(value):return f'{value//100}.{value%100:02d}'


def defaults():
    return dict(enabled=False,reviewed=False,concept_template='Mensualidad {mes} {año} – {grado}',
        iva_enabled=False,igtf_enabled=False,iva_label='IVA',igtf_label='IGTF')


def preferences(db):
    row=db.execute('SELECT payload_json FROM invoice_preferences WHERE id=1').fetchone()
    value=json.loads(row[0]) if row else defaults()
    review=db.execute("SELECT value FROM settings WHERE key='invoice_restore_review_required'").fetchone()
    if review and review[0]:value['reviewed']=False
    return value


def reservation_records(records):
    """Only printed identifiers and hashes; never client fiscal data."""
    gathered=[]
    for record in records.get('audit',[]):
        if record['action']=='restore-backup':
            try:gathered.extend(json.loads(record['details']).get('invoice_reservations',[]))
            except (ValueError,TypeError):raise ValidationError('No se verificó el registro de numeración restaurada.') from None
    for record in records.get('invoices',[]):
        if record.get('invoice_key') is not None:
            gathered.append(dict(invoice_number=record['invoice_number'],control_number=record['control_number'],
                invoice_key=record['invoice_key'],control_key=record['control_key'],state=record['state'],
                pdf_sha256=record['pdf_sha256'],issued_on=record['issued_on']))
    result={}
    for entry in gathered:
        if not isinstance(entry,dict) or not {'invoice_number','control_number','invoice_key','control_key','state','pdf_sha256','issued_on'}<=entry.keys():
            raise ValidationError('Registro de numeración restaurada incompleto.')
        for label in ('invoice','control'):
            if printed(entry[label+'_number'])[1]!=entry[label+'_key']:raise ValidationError('Numeración restaurada inválida.')
        key=(entry['invoice_key'],entry['control_key'],entry['pdf_sha256'])
        prior=result.get(key)
        if prior is None or entry['state']=='void':result[key]={k:entry[k] for k in ('invoice_number','control_number','invoice_key','control_key','state','pdf_sha256','issued_on')}
    return list(result.values())


def reservations(db):
    return reservation_records(dict(audit=[dict(r) for r in db.execute("SELECT action,details FROM audit WHERE action='restore-backup'")]))


def validate_preferences(raw):
    layout.exact_keys(raw,defaults(),'configuración de facturas')
    value=dict(raw)
    for key in ('enabled','reviewed','iva_enabled','igtf_enabled'):layout.boolean(value[key],key)
    if value['iva_enabled'] or value['igtf_enabled']:raise ValidationError('Aula no calcula IVA ni IGTF; mantén ambos desactivados.')
    layout.variables(value['concept_template'])
    if any(key is not None and key not in ('mes','año','grado') for _,key,_,_ in __import__('string').Formatter().parse(value['concept_template'])):
        raise ValidationError('El concepto predeterminado admite {mes}, {año} y {grado}. Los campos de impresión admiten las demás variables.')
    for key in ('iva_label','igtf_label'):layout.text(value[key],30,key,empty=False)
    return value


def version(db,identifier):
    row=db.execute('SELECT v.*,t.current_version_id FROM invoice_template_versions v JOIN invoice_templates t ON t.id=v.template_id WHERE v.id=?',
        (integer(identifier,1,2147483647),)).fetchone()
    if not row:raise ValidationError('Versión de plantilla inexistente.')
    result=dict(row);result['layout']=layout.validate(json.loads(result['layout_json']))
    if layout.digest(result['layout'])!=result['layout_hash']:raise ValidationError('No se verificó la plantilla; revisa el respaldo.')
    return result


def printer(db,identifier):
    if not identifier:return layout.profile()
    row=db.execute('SELECT profile_json FROM invoice_printer_profiles WHERE id=?',(integer(identifier,1,2147483647),)).fetchone()
    if not row:raise ValidationError('Perfil de impresora inexistente.')
    return layout.profile(json.loads(row[0]))


def batch(db,identifier,*,active=False):
    row=db.execute('SELECT * FROM invoice_batches WHERE id=?',(integer(identifier,1,2147483647),)).fetchone()
    if not row or (active and not row['active']):raise ValidationError('Selecciona un lote activo.')
    return dict(row)


def next_numbers(db,lot):
    result={}
    for label in ('invoice','control'):
        used=[int(r[0]) for r in db.execute('SELECT '+label+'_key FROM invoices WHERE batch_id=? AND '+label+'_key IS NOT NULL',(lot['id'],))]
        used.extend(int(r[label+'_key']) for r in reservations(db) if int(lot[label+'_from'])<=int(r[label+'_key'])<=int(lot[label+'_to']))
        following=max(used,default=int(lot[label+'_from'])-1)+1
        result[label]=str(following).zfill(len(lot[label+'_from'])) if following<=int(lot[label+'_to']) else ''
        result[label+'_remaining']=max(0,int(lot[label+'_to'])-following+1)
    result['warning']='Lote agotado' if not result['invoice'] or not result['control'] else 'Lote por agotarse' if min(result['invoice_remaining'],result['control_remaining'])<=10 else ''
    return result


def numbers(db,lot,data,*,old_damaged=False):
    if data.get('numbers_confirmed') is not True:raise ValidationError('Escribe o confirma expresamente ambos números preimpresos.')
    proposal=next_numbers(db,lot);result={};review={}
    for label in ('invoice','control'):
        value,key=printed(data.get(label+'_number'))
        if not int(lot[label+'_from'])<=int(key)<=int(lot[label+'_to']):raise ValidationError('El número queda fuera del rango del lote.')
        if db.execute('SELECT 1 FROM invoices WHERE '+label+'_key=?',(key,)).fetchone():raise ValidationError('Ese número de factura o control ya está contabilizado.')
        if any(entry[label+'_key']==key for entry in reservations(db)):raise ValidationError('Ese número ya se usó antes de una restauración; no se reutiliza.')
        expected=int(proposal[label]) if proposal[label] else int(lot[label+'_to'])+1
        if int(key)<expected and not old_damaged:raise ValidationError('El número retrocede en el orden del lote. Revisa las hojas ya contabilizadas.')
        if int(key)>expected:
            if data.get('gap_confirmed') is not True:raise ValidationError('Hay un salto de numeración: revisa y confirma el motivo.')
            review[label]=dict(first=str(expected),last=str(int(key)-1),reason=reason(data,'gap_reason'))
        result[label+'_number']=value;result[label+'_key']=key
    return result,review


def payment_source(db,identifier):
    row=db.execute('''SELECT p.id,p.amount,p.received_amount,p.currency,p.exchange_rate,p.paid_on,p.method,p.reference,p.voided,p.receipt_snapshot,
        g.name AS client_name,g.document AS client_document,g.address AS client_address,gr.name AS grade_name,a.bcv_rate
        FROM payments p JOIN students s ON s.id=p.student_id JOIN guardians g ON g.id=s.guardian_id
        JOIN grades gr ON gr.id=s.grade_id LEFT JOIN payment_accounts a ON a.payment_id=p.id WHERE p.id=?''',(integer(identifier,1,2147483647),)).fetchone()
    if not row or row['voided']:raise ValidationError('Selecciona un cobro válido.')
    return dict(row)


def source(db,identifier):
    p=payment_source(db,identifier);periods=list(db.execute('SELECT c.period,c.concept,a.amount FROM allocations a JOIN charges c ON c.id=a.charge_id WHERE a.payment_id=? ORDER BY c.period,c.id',(p['id'],)))
    try:grade=json.loads(p['receipt_snapshot']).get('person',{}).get('grade_name') or p['grade_name']
    except (ValueError,AttributeError):grade=p['grade_name']
    items=[];cumulative=previous=0;template=preferences(db)['concept_template']
    for charge in periods:
        period=charge['period'];label=period_label(period);parts=label.split()
        values={key:'' for key in layout.VARIABLES};values.update(mes=parts[0].lower() if parts else '',año=period[:4],grado=grade)
        concept=template.format_map(values) if charge['concept']=='Mensualidad' else charge['concept']+' – '+grade
        cumulative+=charge['amount'];cut=int((Decimal(p['received_amount'])*cumulative/p['amount']).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
        items.append(dict(concept=concept,quantity=1,unit_price=decimal(cut-previous)));previous=cut
    if not items:items=[dict(concept='Concepto por revisar – '+grade,quantity=1,unit_price=decimal(p['received_amount']))]
    return dict(payment_id=p['id'],receipt='R-'+str(p['id']).zfill(6),paid_on=p['paid_on'],issued_on=local_today().isoformat(),
        client=dict(name=p['client_name'],document=p['client_document'],address=p['client_address']),
        items=items,observations='',currency=p['currency'],original_amount=p['received_amount'],
        bcv_rate=p['bcv_rate'] or (p['exchange_rate'] if p['currency']=='VES' else ''),grade=grade,
        month=periods[0]['period'] if periods else p['paid_on'][:7])


def content(db,data):
    p=payment_source(db,data.get('payment_id'));on=valid_date(data.get('issued_on'))
    if on>local_today().isoformat():raise ValidationError('La factura no puede tener fecha futura.')
    ensure_open_day(db,on);ensure_open_day(db,p['paid_on'])
    client=data.get('client');layout.exact_keys(client,('name','document','address'),'cliente de factura')
    client={key:layout.text(client[key],500 if key=='address' else 150,key,empty=False).strip() for key in client}
    raw=data.get('items')
    if not isinstance(raw,list) or not 1<=len(raw)<=100:raise ValidationError('Registra de 1 a 100 conceptos.')
    items=[]
    for item in raw:
        layout.exact_keys(item,('concept','quantity','unit_price'),'concepto de factura')
        quantity=integer(item['quantity'],1,9999);price=cents(item['unit_price'])
        items.append(dict(concept=layout.text(item['concept'],1000,'concepto',empty=False).strip(),quantity=quantity,unit_cents=price,amount_cents=quantity*price))
    if sum(item['amount_cents'] for item in items)!=p['received_amount']:raise ValidationError('Los conceptos deben sumar exactamente el importe original del cobro; el cobro no se modifica.')
    observations=layout.text(data.get('observations',''),1000,'observaciones')
    basis=source(db,p['id'])
    return dict(payment_id=p['id'],issued_on=on,client=client,items=items,observations=observations,
        currency=p['currency'],original_amount=p['received_amount'],
        bcv_rate=p['bcv_rate'] or (p['exchange_rate'] if p['currency']=='VES' else ''),
        grade=basis['grade'],month=basis['month'],receipt='R-'+str(p['id']).zfill(6))


def row(db,identifier,user,*,draft=False):
    found=db.execute('SELECT * FROM invoices WHERE id=?',(integer(identifier,1,2147483647),)).fetchone()
    if not found:raise ValidationError('Factura inexistente.')
    result=dict(found)
    if draft and result['state']!='draft':raise ValidationError('La factura emitida es inmutable; no se edita como borrador.')
    if draft and user['role']!='admin' and result['created_by']!=user['id']:
        raise PermissionError('Solo el creador o Administración puede modificar ese borrador.')
    return result


def draft_hash(record):
    return layout.digest({key:record[key] for key in ('id','payment_id','batch_id','template_version_id','issued_on','profile_json','snapshot_json','state')})


def variables_for(snapshot,operator,numbers_value=None):
    value=snapshot;nums=numbers_value or {};month=period_label(value['month']).split();currency=value['currency']
    fields={key:'' for key in layout.VARIABLES}
    fields.update(fecha='/'.join(reversed(value['issued_on'].split('-'))),numero_factura=nums.get('invoice_number',''),
        numero_control=nums.get('control_number',''),cliente=value['client']['name'],documento_cliente=value['client']['document'],
        direccion=value['client']['address'],concepto='; '.join(item['concept'] for item in value['items']),
        forma_pago=value['payment']['method'],referencia=value['payment']['reference'],
        tasa='BCV: '+value['bcv_rate'] if value['bcv_rate'] else 'NO VERIFICADO · falta tasa histórica',
        exento=amount(value['original_amount'],currency),base=amount(0,currency),iva=amount(0,currency),igtf=amount(0,currency),
        total=amount(value['original_amount'],currency),observaciones=value['observations'],usuario=operator,
        recibo=value['receipt'],moneda=currency,mes=month[0].lower() if month else '',año=value['month'][:4],grado=value['grade'])
    return fields,[dict(concepto=item['concept'],cantidad=str(item['quantity']),precio=amount(item['unit_cents'],currency),
        exento=amount(item['amount_cents'],currency),total=amount(item['amount_cents'],currency)) for item in value['items']]


def unchanged(db,payment_id):
    if db.execute("SELECT 1 FROM invoices WHERE payment_id=? AND state='issued'",(payment_id,)).fetchone():
        raise ValidationError('El cobro tiene una factura vigente. Administración debe revisar y anular primero la factura.')


def action(db,endpoint,data,user):
    if user['role']=='reader' or (endpoint in ADMIN and user['role']!='admin'):raise PermissionError('Tu perfil no permite esta operación de facturas.')
    from .audit_chain import require as require_chain
    from .clock_guard import require_database_clock
    require_chain(db);require_database_clock(db)
    try:return _action(db,endpoint,data,user)
    except sqlite3.IntegrityError as error:
        raise ValidationError('No se guardó: nombre, número o vínculo ya utilizado, o factura inmutable.') from error


def _action(db,endpoint,data,user):
    uid=user['id'];stamp=now()
    if endpoint=='invoice-config':
        value=validate_preferences(data.get('config'))
        flag=db.execute("SELECT value FROM settings WHERE key='invoice_restore_review_required'").fetchone()
        if value['reviewed'] and flag and flag[0]:
            if data.get('restore_review_confirmed') is not True:raise ValidationError('Revisa las facturas excluidas y las hojas disponibles tras restaurar, y confirma esa revisión.')
            db.execute("UPDATE settings SET value='' WHERE key='invoice_restore_review_required'")
        db.execute('INSERT INTO invoice_preferences VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET payload_json=excluded.payload_json,saved_by=excluded.saved_by,saved_at=excluded.saved_at',(encoded(value),uid,stamp))
        audit(db,uid,endpoint,dict(enabled=value['enabled'],reviewed=value['reviewed'],taxes_calculated=False));return dict(saved=True)
    if endpoint=='invoice-batch':
        name=layout.text(data.get('name'),100,'lote',empty=False);identifier=integer(data['id'],1,2147483647) if data.get('id') else None
        limits={key:printed(data.get(key))[0] for key in ('invoice_from','invoice_to','control_from','control_to')}
        for label in ('invoice','control'):
            low,high=int(limits[label+'_from']),int(limits[label+'_to'])
            if low>high:raise ValidationError('El inicio del rango supera el final.')
            for other in db.execute('SELECT * FROM invoice_batches WHERE id<>?',(identifier or 0,)):
                if low<=int(other[label+'_to']) and high>=int(other[label+'_from']):raise ValidationError('Ese rango se superpone con otro lote; revisa los números preimpresos.')
            if identifier:
                used=[int(r[0]) for r in db.execute('SELECT '+label+'_key FROM invoices WHERE batch_id=? AND '+label+'_key IS NOT NULL',(identifier,))]
                if any(not low<=value<=high for value in used):raise ValidationError('El rango nuevo excluiría hojas ya contabilizadas.')
        issuer=data.get('issuer');layout.exact_keys(issuer,ISSUER_KEYS,'datos preimpresos e imprenta')
        issuer={key:layout.text(issuer[key],1000 if key in ('address','notes') else 200,key,empty=key not in ('name','rif','printer_name')) for key in issuer}
        active=layout.boolean(data.get('active'),'lote activo')
        if identifier:batch(db,identifier)
        if active:db.execute('UPDATE invoice_batches SET active=0 WHERE active=1 AND id<>?',(identifier or 0,))
        values=(name,*[limits[key] for key in ('invoice_from','invoice_to','control_from','control_to')],int(active),encoded(issuer),uid,stamp)
        if identifier:db.execute('UPDATE invoice_batches SET name=?,invoice_from=?,invoice_to=?,control_from=?,control_to=?,active=?,data_json=?,saved_by=?,saved_at=? WHERE id=?',(*values,identifier))
        else:identifier=db.execute('INSERT INTO invoice_batches(name,invoice_from,invoice_to,control_from,control_to,active,data_json,saved_by,saved_at) VALUES(?,?,?,?,?,?,?,?,?)',values).lastrowid
        audit(db,uid,endpoint,dict(id=identifier,active=active,ranges=limits));return dict(id=identifier)
    if endpoint in ('invoice-template','invoice-import-template','invoice-template-restore'):
        if endpoint=='invoice-template-restore':
            previous=version(db,data.get('version_id'));value=previous['layout'];identifier=previous['template_id']
        else:
            value=layout.parse_json(data.get('json')) if endpoint=='invoice-import-template' else layout.validate(data.get('layout'))
            identifier=integer(data['id'],1,2147483647) if data.get('id') else None
            if endpoint=='invoice-import-template':value['calibrated']=False
        if identifier:
            if not db.execute('SELECT 1 FROM invoice_templates WHERE id=?',(identifier,)).fetchone():raise ValidationError('Plantilla inexistente.')
            db.execute('UPDATE invoice_templates SET name=?,saved_by=?,saved_at=? WHERE id=?',(value['name'],uid,stamp,identifier))
        else:identifier=db.execute('INSERT INTO invoice_templates(name,saved_by,saved_at) VALUES(?,?,?)',(value['name'],uid,stamp)).lastrowid
        revision=db.execute('SELECT COALESCE(MAX(revision),0)+1 FROM invoice_template_versions WHERE template_id=?',(identifier,)).fetchone()[0]
        vid=db.execute('INSERT INTO invoice_template_versions(template_id,revision,layout_json,layout_hash,saved_by,saved_at) VALUES(?,?,?,?,?,?)',(identifier,revision,encoded(value),layout.digest(value),uid,stamp)).lastrowid
        db.execute('UPDATE invoice_templates SET current_version_id=? WHERE id=?',(vid,identifier))
        audit(db,uid,endpoint,dict(id=identifier,version_id=vid,revision=revision,layout_hash=layout.digest(value),calibrated=value['calibrated']));return dict(id=identifier,version_id=vid)
    if endpoint=='invoice-profile':
        value=layout.profile(data.get('profile'));identifier=integer(data['id'],1,2147483647) if data.get('id') else None
        if identifier:
            if not db.execute('SELECT 1 FROM invoice_printer_profiles WHERE id=?',(identifier,)).fetchone():raise ValidationError('Perfil inexistente.')
            db.execute('UPDATE invoice_printer_profiles SET name=?,profile_json=?,saved_by=?,saved_at=? WHERE id=?',(value['name'],encoded(value),uid,stamp,identifier))
        else:identifier=db.execute('INSERT INTO invoice_printer_profiles(name,profile_json,saved_by,saved_at) VALUES(?,?,?,?)',(value['name'],encoded(value),uid,stamp)).lastrowid
        audit(db,uid,endpoint,dict(id=identifier));return dict(id=identifier)
    if endpoint=='invoice-test':
        value=layout.validate(data.get('layout'));pr=layout.profile(data.get('profile'));example=layout.sample()
        items=[dict(concepto=example['concepto'],cantidad='1',precio='100,00',exento='100,00',total='100,00')]
        result=layout.render(value,example,items,pr,calibration=True,include_background=data.get('include_background') is True)
        audit(db,uid,endpoint,dict(layout_hash=layout.digest(value),pdf_sha256=result['sha256'],number_consumed=False))
        return dict(pdf_base64=base64.b64encode(result['pdf']).decode(),sha256=result['sha256'],filename='Aula-Calibracion-PRUEBA.pdf')
    if endpoint in ('invoice-draft','invoice-edit-draft'):
        value=content(db,data);p=payment_source(db,value['payment_id'])
        value['payment']=dict(method=p['method'],reference=p['reference'])
        value['profile_id']=integer(data['profile_id'],1,2147483647) if data.get('profile_id') else None
        vid=integer(data.get('template_version_id'),1,2147483647);version(db,vid)
        lot=batch(db,data.get('batch_id'));pr=printer(db,data.get('profile_id'))
        identifier=integer(data['id'],1,2147483647) if endpoint=='invoice-edit-draft' else None
        if identifier:
            existing=row(db,identifier,user,draft=True)
            if data.get('confirmed_hash')!=draft_hash(existing):raise ValidationError('Cambió el borrador; vuelve a revisarlo.')
            ensure_open_day(db,existing['issued_on'])
            db.execute('UPDATE invoices SET payment_id=?,batch_id=?,template_version_id=?,issued_on=?,profile_json=?,snapshot_json=? WHERE id=?',(p['id'],lot['id'],vid,value['issued_on'],encoded(pr),encoded(value),identifier))
        else:identifier=db.execute("INSERT INTO invoices(payment_id,batch_id,template_version_id,issued_on,state,profile_json,snapshot_json,created_by,created_at) VALUES(?,?,?,?,'draft',?,?,?,?)",(p['id'],lot['id'],vid,value['issued_on'],encoded(pr),encoded(value),uid,stamp)).lastrowid
        audit(db,uid,endpoint,dict(id=identifier,payment_id=p['id'],version_id=vid));return dict(id=identifier)
    if endpoint=='invoice-issue':
        existing=row(db,data.get('id'),user,draft=True)
        if data.get('confirmed_hash')!=draft_hash(existing):raise ValidationError('Cambió el borrador; revísalo antes de emitir.')
        cfg=preferences(db)
        if not cfg['enabled'] or not cfg['reviewed']:raise ValidationError(layout.WARNING+' Administración debe revisar y habilitar la emisión.')
        ensure_open_day(db,existing['issued_on']);p=payment_source(db,existing['payment_id']);ensure_open_day(db,p['paid_on'])
        if db.execute("SELECT 1 FROM invoices WHERE payment_id=? AND state='issued'",(p['id'],)).fetchone():raise ValidationError('Ese cobro ya tiene una factura vigente.')
        v=version(db,existing['template_version_id'])
        if not v['layout']['calibrated'] or v['current_version_id']!=v['id']:raise ValidationError('Selecciona y revisa la versión actual calibrada de la plantilla.')
        lot=batch(db,existing['batch_id'],active=True);nums,review=numbers(db,lot,data)
        value=json.loads(existing['snapshot_json'])
        if value['original_amount']!=p['received_amount'] or value['currency']!=p['currency']:raise ValidationError('Cambió el cobro de origen; revisa el borrador.')
        value.update(issuer=json.loads(lot['data_json']),operator=user['name'],issued_by=uid,issued_at=stamp,numbers=nums,numbering_review=review,template_revision=v['revision'],template_hash=v['layout_hash'])
        values,items=variables_for(value,user['name'],nums);pr=json.loads(existing['profile_json'])
        result=layout.render(v['layout'],values,items,pr)  # no client flag can print the scan
        db.execute("UPDATE invoices SET state='issued',invoice_number=?,control_number=?,invoice_key=?,control_key=?,snapshot_json=?,pdf_base64=?,pdf_sha256=?,issued_by=?,issued_at=? WHERE id=?",
            (nums['invoice_number'],nums['control_number'],nums['invoice_key'],nums['control_key'],encoded(value),base64.b64encode(result['pdf']).decode(),result['sha256'],uid,stamp,existing['id']))
        audit(db,uid,endpoint,dict(id=existing['id'],payment_id=p['id'],invoice=nums['invoice_number'],control=nums['control_number'],template_version_id=v['id'],pdf_sha256=result['sha256'],numbering_review=review));return dict(id=existing['id'],warning=next_numbers(db,lot)['warning'])
    if endpoint=='invoice-preview':
        existing=row(db,data.get('id'),user,draft=True);value=json.loads(existing['snapshot_json']);v=version(db,existing['template_version_id'])
        values,items=variables_for(value,user['name'],dict(invoice_number='PRUEBA',control_number='PRUEBA'))
        result=layout.render(v['layout'],values,items,json.loads(existing['profile_json']),calibration=True)
        audit(db,uid,endpoint,dict(id=existing['id'],pdf_sha256=result['sha256'],number_consumed=False))
        return dict(pdf_base64=base64.b64encode(result['pdf']).decode(),sha256=result['sha256'],filename='Aula-Borrador-PRUEBA.pdf')
    if endpoint=='invoice-damaged':
        lot=batch(db,data.get('batch_id'),active=True);why=reason(data);on=valid_date(data.get('issued_on'))
        if on>local_today().isoformat():raise ValidationError('La hoja no puede tener fecha futura.')
        ensure_open_day(db,on)
        old=data.get('prior_gap_confirmed') is True
        if old and user['role']!='admin':raise PermissionError('Solo Administración regulariza una hoja anterior con motivo.')
        nums,review=numbers(db,lot,data,old_damaged=old)
        value=dict(reason=why,operator=user['name'],numbers=nums,numbering_review=review,issuer=json.loads(lot['data_json']))
        identifier=db.execute("INSERT INTO invoices(batch_id,issued_on,state,invoice_number,control_number,invoice_key,control_key,snapshot_json,created_by,created_at,issued_by,issued_at) VALUES(?,?,'damaged',?,?,?,?,?,?,?,?,?)",(lot['id'],on,nums['invoice_number'],nums['control_number'],nums['invoice_key'],nums['control_key'],encoded(value),uid,stamp,uid,stamp)).lastrowid
        audit(db,uid,endpoint,dict(id=identifier,invoice=nums['invoice_number'],control=nums['control_number'],reason=why,numbering_review=review));return dict(id=identifier,warning=next_numbers(db,lot)['warning'])
    if endpoint=='invoice-void':
        existing=row(db,data.get('id'),user)
        if existing['state']!='issued':raise ValidationError('Solo se anula una factura emitida vigente.')
        ensure_open_day(db,existing['issued_on']);why=reason(data)
        db.execute("UPDATE invoices SET state='void',voided_by=?,voided_at=?,void_reason=? WHERE id=?",(uid,stamp,why,existing['id']))
        audit(db,uid,endpoint,dict(id=existing['id'],reason=why,invoice=existing['invoice_number'],control=existing['control_number']));return dict(id=existing['id'],voided=True)
    if endpoint=='invoice-print':
        existing=row(db,data.get('id'),user)
        if existing['state']!='issued':raise ValidationError('Solo se imprime una factura emitida vigente.')
        if any(r['control_key']==existing['control_key'] and (r['state']!='issued' or r['pdf_sha256']!=existing['pdf_sha256']) for r in reservations(db)):
            raise ValidationError('La restauración conserva una anulación o diferencia de esta factura; Administración debe revisarla antes de imprimir.')
        raw=base64.b64decode(existing['pdf_base64'],validate=True)
        if hashlib.sha256(raw).hexdigest()!=existing['pdf_sha256']:raise ValidationError('No se verificó el PDF conservado; revisa el respaldo.')
        count=db.execute('SELECT COUNT(*) FROM invoice_print_events WHERE invoice_id=?',(existing['id'],)).fetchone()[0]
        why=reason(data) if count else 'Primera impresión'
        if count and data.get('reprint_confirmed') is not True:raise ValidationError('Confirma la reimpresión y su motivo; no uses otra hoja numerada.')
        db.execute('INSERT INTO invoice_print_events(invoice_id,pdf_sha256,reason,printed_by,printed_at) VALUES(?,?,?,?,?)',(existing['id'],existing['pdf_sha256'],why,uid,stamp))
        audit(db,uid,endpoint,dict(id=existing['id'],reprint=bool(count),pdf_sha256=existing['pdf_sha256'],reason=why))
        return dict(id=existing['id'],pdf_base64=existing['pdf_base64'],sha256=existing['pdf_sha256'],filename='Factura-'+existing['invoice_number']+'.pdf',reprint=bool(count))
    raise ValidationError('Operación de facturas inexistente.')


def detail(db,identifier,user):
    if user['role']=='reader':raise PermissionError('Consulta solo recibe informes de facturas.')
    r=row(db,identifier,user);snapshot=json.loads(r['snapshot_json'])
    result={key:r[key] for key in ('id','payment_id','batch_id','template_version_id','issued_on','state','invoice_number','control_number','created_by','created_at','issued_by','issued_at','void_reason')}
    result.update(snapshot=snapshot,profile=json.loads(r['profile_json']),draft_hash=draft_hash(r),
        prints=[dict(p) for p in db.execute('SELECT id,reason,printed_by,printed_at FROM invoice_print_events WHERE invoice_id=? ORDER BY id',(r['id'],))])
    return result


def outstanding_numbers(db,period):
    count=0
    for record in db.execute("SELECT batch_id,snapshot_json FROM invoices WHERE substr(issued_on,1,7)=? AND state<>'draft'",(period,)):
        for label,gap in json.loads(record['snapshot_json']).get('numbering_review',{}).items():
            first,last=int(gap['first']),int(gap['last'])
            occupied=db.execute('SELECT COUNT(*) FROM invoices WHERE batch_id=? AND CAST('+label+'_key AS INTEGER) BETWEEN ? AND ?',(record['batch_id'],first,last)).fetchone()[0]
            count+=max(0,last-first+1-occupied)
    return count


def pending(db,period):
    if not preferences(db)['enabled']:return dict(invoice_drafts=0,invoice_unbilled=0,invoice_numbers=0)
    return dict(invoice_drafts=db.execute("SELECT COUNT(*) FROM invoices WHERE state='draft' AND substr(issued_on,1,7)=?",(period,)).fetchone()[0],
        invoice_unbilled=db.execute("SELECT COUNT(*) FROM payments p WHERE voided=0 AND substr(paid_on,1,7)=? AND NOT EXISTS(SELECT 1 FROM invoices i WHERE i.payment_id=p.id AND i.state='issued')",(period,)).fetchone()[0],
        invoice_numbers=outstanding_numbers(db,period))


def sales(db,period):
    period=valid_period(period)
    if period>local_today().isoformat()[:7]:raise ValidationError('Selecciona un mes actual o anterior.')
    records=[];totals={}
    for r in db.execute("SELECT * FROM invoices WHERE substr(issued_on,1,7)=? AND state<>'draft' ORDER BY issued_on,CAST(invoice_key AS INTEGER),id",(period,)):
        snap=json.loads(r['snapshot_json']);damaged=r['state']=='damaged';currency='' if damaged else snap['currency'];total=0 if damaged else snap['original_amount']
        review=snap.get('numbering_review',{})
        records.append(dict(id=r['id'],date=r['issued_on'],invoice=r['invoice_number'],control=r['control_number'],
            client='' if damaged else snap['client']['name'],document='' if damaged else snap['client']['document'],
            concept='' if damaged else '; '.join(item['concept'] for item in snap['items']),currency=currency,exempt=total,base=0,iva=0,igtf=0,total=total,
            state=r['state'],state_label=STATES[r['state']],receipt='' if damaged else snap['receipt'],operator=snap['operator'],
            template_version_id=r['template_version_id'],template_revision=snap.get('template_revision'),
            reason=snap.get('reason','') if damaged else r['void_reason'],numbering_review=review))
        if r['state']=='issued':totals[currency]=totals.get(currency,0)+total
        if len(records)>50000:raise ValidationError('Divide el informe en meses más pequeños antes de exportar.')
    school={key:value for key,value in db.execute('SELECT key,value FROM settings') if key in ('school_name','legal_name','institution_type','rif','fiscal_address','address','phone','email','logo')}
    return dict(period=period,records=records,totals=totals,school=school,note='Relación administrativa de formularios preimpresos. Números confirmados por operador; Aula no calcula IVA/IGTF ni sustituye al contador. Anuladas y hojas dañadas conservan número, pero no suman ventas. Sin datos personales del menor. Un salto no declara automáticamente hojas dañadas.')


def book(db,user,period,offset=0):
    period=valid_period(period);offset=integer(offset,0,1000000);report=sales(db,period)
    result=dict(period=period,offset=offset,sales=report['records'][offset:offset+100],total_records=len(report['records']),totals=report['totals'],pending=pending(db,period),warning=layout.WARNING)
    if user['role']=='reader':return result
    lots=[]
    for r in db.execute('SELECT * FROM invoice_batches ORDER BY id'):
        value=dict(r);value['issuer']=json.loads(value.pop('data_json'));value['proposal']=next_numbers(db,value);lots.append(value)
    flag=db.execute("SELECT value FROM settings WHERE key='invoice_restore_review_required'").fetchone()
    result.update(config=preferences(db),batches=lots,restore_review_required=bool(flag and flag[0]),
        templates=[dict(r) for r in db.execute("SELECT t.id,t.name,t.current_version_id,v.revision,json_extract(v.layout_json,'$.calibrated') AS calibrated FROM invoice_templates t JOIN invoice_template_versions v ON v.id=t.current_version_id ORDER BY t.name")],
        profiles=[dict(id=r['id'],**json.loads(r['profile_json'])) for r in db.execute('SELECT * FROM invoice_printer_profiles ORDER BY name')],
        drafts=[dict(r) for r in db.execute("SELECT id,payment_id,issued_on,created_by,template_version_id FROM invoices WHERE state='draft' AND substr(issued_on,1,7)=? ORDER BY id LIMIT 100 OFFSET ?",(period,offset))])
    return result


def template_detail(db,identifier,user):
    if user['role']!='admin':raise PermissionError('Solo Administración configura plantillas.')
    v=version(db,identifier)
    return dict(id=v['template_id'],version_id=v['id'],revision=v['revision'],layout=v['layout'],
        history=[dict(r) for r in db.execute('SELECT id,revision,layout_hash,saved_by,saved_at FROM invoice_template_versions WHERE template_id=? ORDER BY revision DESC',(v['template_id'],))])


def csv_bytes(data):
    out=io.StringIO(newline='');writer=csv.writer(out,delimiter=';')
    def line(values):
        writer.writerow(["'"+str(v) if str(v).lstrip().startswith(('=','+','-','@')) else str(v) for v in values])
    line(['Relación de ventas',data['period']]);line(['Fecha','Factura (texto)','Control (texto)','Cliente','Documento fiscal','Concepto','Moneda','Exento','Base','IVA','IGTF','Total','Estado','Recibo','Usuario','Versión plantilla','Motivo','Saltos revisados'])
    for r in data['records']:
        # Text prefixes preserve zeroes in Excel without executable formulas.
        line([r['date'],"'"+r['invoice'],"'"+r['control'],r['client'],r['document'],r['concept'],r['currency'],
            *[decimal(r[k]) for k in ('exempt','base','iva','igtf','total')],r['state_label'],r['receipt'],r['operator'],r['template_version_id'] or '',r['reason'],encoded(r['numbering_review'])])
    line([]);line(['Totales de facturas vigentes por moneda'])
    for currency,total in sorted(data['totals'].items()):line([currency,decimal(total)])
    line([data['note']]);return ('\ufeff'+out.getvalue()).encode('utf-8')


def pdf_bytes(data,user):
    from .directory_reports import daily_pdf
    lines=[[r['date'],r['invoice']+'\n'+r['control'],r['client']+'\n'+r['document'],r['concept'],amount(r['total'],r['currency']) if r['currency'] else '',r['state_label']+'\n'+r['reason'],r['receipt']+'\n'+r['operator']+'\nV'+str(r['template_version_id'] or '')] for r in data['records']]
    tax_lines=[[r['invoice'],r['currency'],*[amount(r[k],r['currency']) if r['currency'] else '' for k in ('exempt','base','iva','igtf','total')]] for r in data['records']]
    return daily_pdf(dict(title='Relación de ventas · formularios preimpresos',school=data['school'],issued_on=local_today().isoformat(),
        issued_at=now(),operator=user['name'],filter_label=data['period'],count_label=str(len(lines))+' formularios contabilizados',
        summaries=[('Facturas vigentes · '+currency,amount(total,currency)) for currency,total in data['totals'].items()],
        sections=[dict(title='Facturas y hojas',headings=['Fecha','Factura / control','Cliente / documento fiscal','Concepto','Total original','Estado / motivo','Recibo / usuario / versión'],widths=[65,90,155,150,90,105,103],lines=lines),
            dict(title='Importes declarados · sin cálculo de impuestos',headings=['Factura','Moneda','Exento','Base','IVA','IGTF','Total'],widths=[100,60,140,115,115,115,113],lines=tax_lines)],note=data['note']))


def review_records(db):
    errors=[]
    try:
        from .invoice_schema import verify_layout
        verify_layout(db)
        for record in db.execute('SELECT id,layout_json,layout_hash FROM invoice_template_versions'):
            value=layout.validate(json.loads(record['layout_json']))
            if layout.digest(value)!=record['layout_hash']:raise ValueError('plantilla')
        for record in db.execute("SELECT * FROM invoices WHERE state IN('issued','void')"):
            raw=base64.b64decode(record['pdf_base64'],validate=True)
            if hashlib.sha256(raw).hexdigest()!=record['pdf_sha256']:raise ValueError('PDF')
            snap=json.loads(record['snapshot_json']);p=payment_source(db,record['payment_id']) if record['state']=='issued' else db.execute('SELECT * FROM payments WHERE id=?',(record['payment_id'],)).fetchone()
            if p is None or snap['original_amount']!=p['received_amount'] or snap['currency']!=p['currency'] or sum(i['amount_cents'] for i in snap['items'])!=snap['original_amount']:
                raise ValueError('importes de factura')
        reservations(db)
    except (ValueError,TypeError,KeyError,sqlite3.Error):errors.append('No se verificó una factura, plantilla o numeración conservada. Revisa el respaldo y la bitácora.')
    return errors
