"""Prepare one family notice, never transmit it. No financial writes or schema changes."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import importlib.util
import json
import re
from string import Formatter
from urllib.parse import quote

from .db import ValidationError, audit, charges, integer, local_today, required

TZ = timezone(timedelta(hours=-4))
CASHEA_AVAILABLE = importlib.util.find_spec('colegio.cashea') is not None
TYPES = {'near':'Cercano y amable (tú)', 'cordial':'Cordial (usted) · con detalle',
         'brief':'Recordatorio breve', 'late':'Atraso prolongado', 'agreement':'Propuesta de convenio de pago'}
MARKERS = frozenset(('representante','alumno','colegio','saludo','meses','total_usd',
                     'total_bs','tasa','fecha','cashea','pago'))
# The existing audit redaction recognizes *_secret settings. Their changes are
# audited below with before/after hashes, not duplicate copies of free text.
KEYS = {'emojis':'collection_notice_emojis', 'cashea':'collection_notice_cashea',
        'payment_details':'collection_notice_payment_secret', 'templates':'collection_notice_templates_secret'}
MONTHS = ('Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre')
PARTICLES = frozenset(('de','del','la','las','los','y','e','von','van','da','do','dos','das'))


def _defaults():
    intros = {
        'near': ('{saludo}, {representante} 👋\nTe escribimos de {colegio}. Te compartimos lo pendiente de {alumno}:',
                 '{saludo}, {representante} 👋\n¿Cómo estás? En {colegio} estamos revisando la cuenta de {alumno}:',
                 '{saludo}, {representante} 👋\nDesde {colegio} queríamos recordarte estos pagos de {alumno}:'),
        'cordial': ('{saludo}, {representante}.\nLe escribimos de {colegio} para recordar los pagos pendientes de {alumno}:',
                    '{saludo}, {representante}.\nEsperamos que se encuentre bien. En {colegio} estamos revisando la cuenta de {alumno}:',
                    '{saludo}, {representante}.\nDesde {colegio} queremos compartirle el detalle pendiente de {alumno}:'),
        'brief': ('{saludo}, {representante}.\nUn recordatorio de {colegio} sobre {alumno}:',
                  '{saludo}, {representante}.\nDesde {colegio}, le compartimos un recordatorio de {alumno}:',
                  '{saludo}, {representante}.\nQueríamos recordar estos pagos de {alumno} en {colegio}:'),
        'late': ('{saludo}, {representante}.\nLe escribimos de {colegio}. Hay pagos de {alumno} que siguen pendientes desde hace tiempo:',
                 '{saludo}, {representante}.\nEn {colegio} necesitamos coordinar con usted los pagos pendientes de {alumno}:',
                 '{saludo}, {representante}.\nQueremos retomar con usted la cuenta pendiente de {alumno} en {colegio}:'),
        'agreement': ('{saludo}, {representante}.\nDesde {colegio} queremos conversar sobre cómo organizar los pagos pendientes de {alumno}:',
                      '{saludo}, {representante}.\nEn {colegio} podemos revisar juntos una forma de ponerse al día con la cuenta de {alumno}:',
                      '{saludo}, {representante}.\nQueremos ayudarle a organizar estos pagos de {alumno} en {colegio}:')}
    closings = {
        'near': ('Si ya pagaste, compártenos el comprobante y lo revisamos. ¡Gracias por tu apoyo!',
                 'Si necesitas revisar algún abono, escríbenos y lo vemos contigo. ¡Gracias!',
                 'Avísanos si ya hiciste el pago para revisar el comprobante. Gracias por estar pendiente.'),
        'cordial': ('Si ya realizó el pago, puede enviarnos el comprobante para revisarlo. Muchas gracias por su apoyo.',
                    'Cualquier duda, puede escribirnos. Con gusto revisamos los abonos. Gracias por su atención.',
                    'Si ya pagó, compártanos el comprobante y lo revisamos. Agradecemos su apoyo.'),
        'brief': ('Cualquier duda, nos escribe. ¡Gracias!', 'Si ya pagó, compártanos el comprobante. ¡Gracias!',
                  'Estamos atentos para revisar cualquier abono. ¡Gracias!'),
        'late': ('Por favor, escríbanos para coordinar una fecha de pago o revisar una alternativa. Si ya pagó, envíenos el comprobante. Gracias.',
                 'Agradecemos que se comunique con administración para organizar los pagos. Podemos revisar juntos cualquier diferencia.',
                 'Necesitamos acordar cómo ponerse al día. Escríbanos para conversar; si ya pagó, revisamos su comprobante.'),
        'agreement': ('Podemos conversar sobre un convenio de pago para organizar lo pendiente. Escríbanos y revisamos juntos una propuesta que pueda cumplir.',
                      'Si le resulta difícil pagarlo de una vez, puede conversar con administración sobre un convenio. Revisamos juntos las fechas y los abonos.',
                      'Queremos proponerle que conversemos sobre un convenio de pago. Coordinemos una propuesta y sus fechas con administración.')}
    middle = '\n{meses}\n\nTotal: {total_usd}\n{total_bs}\n\n{cashea}\n\n{pago}\n\n'
    return {key:[intro+middle+closing for intro,closing in zip(intros[key],closings[key])] for key in TYPES}


DEFAULT_TEMPLATES = _defaults()


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def title_name(value):
    words = re.split(r'(\s+)', str(value).strip())
    first = True
    for index,word in enumerate(words):
        if not word or word.isspace(): continue
        lower = word.lower()
        if lower in PARTICLES and not first: words[index] = lower
        else: words[index] = ''.join(part.capitalize() if part not in ("'",'’','-') else part
                                   for part in re.split(r"([-’'])", lower))
        first = False
    return ''.join(words)


def greeting(now=None):
    current = (now or datetime.now(timezone.utc)).astimezone(TZ)
    return 'Buenos días' if 5 <= current.hour < 12 else 'Buenas tardes' if 12 <= current.hour < 19 else 'Buenas noches'


def money_text(cents, currency='USD'):
    return f"{currency} {cents//100:,}".replace(',','.')+f',{cents%100:02d}'


def rate_text(value):
    whole,_,fraction = format(Decimal(str(value)),'f').partition('.')
    return f'{int(whole):,}'.replace(',','.')+','+fraction.rstrip('0').ljust(2,'0')


def normalize_phone(value):
    value = str(value or '').strip()
    if not value or len(value)>100 or not re.fullmatch(r'\+?[0-9\s().-]+',value): return None
    digits = re.sub(r'\D','',value)
    if digits.startswith('0058'): digits=digits[2:]
    elif len(digits)==11 and digits.startswith('0'): digits='58'+digits[1:]
    elif len(digits)==10: digits='58'+digits
    if not re.fullmatch(r'58[0-9]{10}',digits): return None
    area = digits[2:5]
    return digits if area in ('412','414','416','422','424','426') or re.fullmatch(r'2[0-9]{2}',area) else None


def whatsapp_url(phone, text):
    phone = normalize_phone(phone)
    return f'https://wa.me/{phone}?text={quote(text,safe="")}' if phone else None


_EMOJI_BASE = r'[\U0001F000-\U0001FAFF\u2600-\u27BF\u2300-\u23FF\u00A9\u00AE\u203C\u2049\u2122\u2139]'
_EMOJI = re.compile(r'[0-9#*]\ufe0f?\u20e3|[\U0001F1E6-\U0001F1FF]{2}|'+
    _EMOJI_BASE+r'\ufe0f?[\U0001F3FB-\U0001F3FF]?(?:\u200d'+_EMOJI_BASE+r'\ufe0f?[\U0001F3FB-\U0001F3FF]?)*')


def limit_emojis(text, enabled):
    count=0
    def keep(match):
        nonlocal count
        count+=1
        return match.group() if enabled and count<=2 else ''
    return _EMOJI.sub(keep,text)


def validate_template(value):
    if not isinstance(value,str) or not value.strip() or len(value)>4000:
        raise ValidationError('Cada plantilla debe tener texto y como máximo 4000 caracteres.')
    seen=set()
    try:
        for _,field,spec,conversion in Formatter().parse(value):
            if field is None: continue
            if field not in MARKERS or spec or conversion:
                raise ValidationError('Marcador desconocido o con formato no permitido: {'+str(field)+'}. Usa los marcadores indicados.')
            seen.add(field)
    except ValidationError:
        raise
    except ValueError:
        raise ValidationError('Revisa las llaves de los marcadores de la plantilla.') from None
    if not {'meses','total_usd'} <= seen:
        raise ValidationError('Conserva {meses} y {total_usd} para mostrar el detalle y el total completo.')
    return value.strip()


def flag(value):
    if value in (True,1,'1'): return True
    if value in (False,0,'0'): return False
    raise ValidationError('La opción debe estar activada o desactivada.')


def settings(db):
    stored=dict(db.execute('SELECT key,value FROM settings WHERE key LIKE \'collection_notice_%\''))
    custom=json.loads(stored.get(KEYS['templates'],'{}'))
    return dict(emojis=stored.get(KEYS['emojis'],'1')=='1',
        cashea=CASHEA_AVAILABLE and stored.get(KEYS['cashea'],'1')=='1',
        payment_details=stored.get(KEYS['payment_details'],''),
        templates={k:list(custom.get(k,DEFAULT_TEMPLATES[k])) for k in TYPES},
        defaults={k:list(v) for k,v in DEFAULT_TEMPLATES.items()},types=TYPES,
        markers=sorted(MARKERS),cashea_available=CASHEA_AVAILABLE)


def validate_settings(data):
    templates=data.get('templates')
    if not isinstance(templates,dict) or set(templates)!=set(TYPES):
        raise ValidationError('Revisa los cinco tipos de aviso.')
    clean={}
    for key,variants in templates.items():
        if not isinstance(variants,list) or len(variants)!=3:
            raise ValidationError('Cada tipo de aviso debe tener sus tres versiones.')
        clean[key]=[validate_template(v) for v in variants]
    details=data.get('payment_details','')
    if not isinstance(details,str) or len(details)>2000:
        raise ValidationError('Datos para pagar admite hasta 2000 caracteres de texto libre.')
    return dict(emojis=flag(data.get('emojis')),cashea=flag(data.get('cashea')) and CASHEA_AVAILABLE,
                payment_details=details,templates=clean)


def save_settings(db, data, user):
    if user['role']!='admin': raise PermissionError('Solo Administración puede editar los avisos.')
    before=settings(db);value=validate_settings(data)
    custom={k:v for k,v in value['templates'].items() if v!=DEFAULT_TEMPLATES[k]}
    values={KEYS['emojis']:'1' if value['emojis'] else '0',KEYS['cashea']:'1' if value['cashea'] else '0',
            KEYS['payment_details']:value['payment_details'],KEYS['templates']:json.dumps(custom,ensure_ascii=False)}
    # Defaults stay in code. Saving originals removes overrides; new installs seed nothing.
    defaults={KEYS['emojis']:'1',KEYS['cashea']:'1' if CASHEA_AVAILABLE else '0',
              KEYS['payment_details']:'',KEYS['templates']:'{}'}
    for key,val in values.items():
        if val==defaults[key]: db.execute('DELETE FROM settings WHERE key=?',(key,))
        else: db.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,val))
    def summary(config):
        return dict(emojis=config['emojis'],cashea=config['cashea'],
            payment_details=dict(length=len(config['payment_details']),sha256=digest(config['payment_details'])),
            templates={k:[digest(v) for v in variants] for k,variants in config['templates'].items()})
    audit(db,user['id'],'collection_notice_settings',dict(before=summary(before),after=summary(value)))
    return dict(saved=True)


def selected_type(days):
    return 'near' if days<=30 else 'cordial' if days<=60 else 'late'


def month_text(period):
    if re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',period or ''):
        return MONTHS[int(period[5:])-1]+' '+period[:4]
    return str(period)


def debt_context(db, student_id, siblings=False):
    sid=integer(student_id,1,2147483647)
    primary=db.execute('''SELECT s.id,s.guardian_id,s.name,g.name AS guardian_name,g.phone
        FROM students s JOIN guardians g ON g.id=s.guardian_id WHERE s.id=?''',(sid,)).fetchone()
    if not primary: raise ValidationError('Selecciona un alumno existente.')
    pupils=[dict(r) for r in db.execute('SELECT id,name FROM students WHERE guardian_id=? ORDER BY name,id',(primary['guardian_id'],))]
    pupil_map={s['id']:s for s in pupils if siblings or s['id']==sid}
    eligible=[c for c in charges(db) if c['student_id'] in pupil_map and c['overdue']]
    groups=[]
    for pupil in pupil_map.values():
        items=[c for c in eligible if c['student_id']==pupil['id']]
        if items: groups.append(dict(id=pupil['id'],name=title_name(pupil['name']),charges=items))
    today=local_today()
    days=max(((today-datetime.fromisoformat(c['due_date']).date()).days for c in eligible),default=0)
    rate=db.execute('SELECT rate FROM exchange_rates WHERE rate_date=?',(today.isoformat(),)).fetchone()
    school=db.execute("SELECT value FROM settings WHERE key='school_name'").fetchone()[0]
    return dict(student_id=sid,guardian_id=primary['guardian_id'],representative=title_name(primary['guardian_name']),
        phone=primary['phone'],groups=groups,total=sum(c['balance'] for c in eligible),days=days,
        rate=rate['rate'] if rate else None,date=today.isoformat(),school=school)


def detail_text(groups, brief=False):
    result=[]
    for pupil in groups:
        lines=[];items=pupil['charges']
        for charge in items[:6]:
            concept='' if charge['concept']=='Mensualidad' else ' · '+charge['concept']
            lines.append(month_text(charge['period'])+concept+': '+money_text(charge['balance']))
        rest=items[6:]
        if rest:
            monthly=all(c['concept']=='Mensualidad' for c in rest) and len({c['period'] for c in rest})==len(rest)
            lines.append(f"y {len(rest)} {'meses' if monthly else 'cargos'} más")
        if brief:
            result.append((pupil['name']+': ' if len(groups)>1 else '')+'; '.join(lines))
        else:
            result.append((pupil['name']+'\n' if len(groups)>1 else '')+'\n'.join('• '+v for v in lines))
    return ' | '.join(result) if brief else '\n\n'.join(result)


def render(context, config, kind, variant, *, cashea, payment, now=None):
    template=validate_template(config['templates'][kind][variant])
    rate=context['rate'];bs_line=''
    if rate is not None:
        amount=int((Decimal(context['total'])*Decimal(str(rate))).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
        bs_line=f"Hoy son aproximadamente {money_text(amount,'Bs')}, con tasa BCV {rate_text(rate)}; se paga a la tasa del día del pago."
    fields=dict(representante=context['representative'],alumno=', '.join(g['name'] for g in context['groups']),
        colegio=context['school'],saludo=greeting(now),meses=detail_text(context['groups'],kind=='brief'),
        total_usd=money_text(context['total']),total_bs=bs_line,tasa=rate_text(rate) if rate is not None else '',
        fecha=datetime.fromisoformat(context['date']).strftime('%d/%m/%Y'),
        cashea='También pueden consultar Cashea: abonan una parte inicial según su nivel y financian el resto. Cashea evalúa la aprobación.' if cashea and CASHEA_AVAILABLE else '',
        pago='Datos para pagar:\n'+config['payment_details'] if payment and config['payment_details'] else '')
    text=template.format_map(fields)
    return re.sub(r'\n{3,}','\n\n','\n'.join(line.rstrip() for line in limit_emojis(text,config['emojis']).splitlines())).strip()


def last_notice(db, ids):
    for row in db.execute("SELECT a.id,a.details,a.created_at,u.name AS operator FROM audit a LEFT JOIN users u ON u.id=a.user_id WHERE a.action='collection_notice_sent' ORDER BY a.id DESC"):
        value=json.loads(row['details'])
        if set(ids).intersection(value.get('student_ids',[])):
            days=max(0,(local_today()-datetime.fromisoformat(row['created_at']).astimezone(TZ).date()).days)
            return dict(days=days,type=TYPES.get(value['type'],value['type']),at=row['created_at'],operator=row['operator'])
    return None


def preview(db, data):
    config=settings(db);siblings=flag(data.get('siblings','0'))
    context=debt_context(db,data.get('student_id'),siblings)
    kind=data.get('type') or selected_type(context['days'])
    if kind not in TYPES: raise ValidationError('Selecciona un tipo de mensaje válido.')
    variant=integer(data.get('variant',context['guardian_id']%3),0,2)
    cashea=flag(data.get('cashea','1' if config['cashea'] else '0')) and CASHEA_AVAILABLE
    payment=flag(data.get('payment','0'))
    text=render(context,config,kind,variant,cashea=cashea,payment=payment) if context['total'] else 'Esta cuenta no tiene deuda vencida. No hace falta preparar un aviso de cobranza.'
    ids=[g['id'] for g in context['groups']]
    return dict(text=text,type=kind,variant=variant,types=TYPES,siblings=siblings,cashea=cashea,payment=payment,
        student_ids=ids,guardian_name=context['representative'],phone=normalize_phone(context['phone']),
        phone_error='' if normalize_phone(context['phone']) else 'Revisa el teléfono: hace falta un número venezolano completo para abrir WhatsApp.',
        whatsapp_url=whatsapp_url(context['phone'],text),eligible=bool(context['total']),days=context['days'],
        last_notice=last_notice(db,ids or [context['student_id']]),cashea_available=CASHEA_AVAILABLE)


def example_preview(db, data, user):
    if user['role']!='admin': raise PermissionError('Solo Administración puede probar las plantillas de Ajustes.')
    value=validate_settings(data);kind=data.get('type','near');variant=integer(data.get('variant',0),0,2)
    if kind not in TYPES: raise ValidationError('Selecciona un tipo de mensaje válido.')
    context=dict(representative='María de Prueba Ficticia',school='Colegio FICTICIO',
        groups=[dict(name='Alumna Ficticia Completa',charges=[dict(period='2026-09',concept='Mensualidad',balance=4000),
                     dict(period='2026-10',concept='Mensualidad',balance=4000)])],total=8000,rate='889.26',date='2026-11-01')
    return dict(text=render(context,value,kind,variant,cashea=value['cashea'],payment=True),fictional=True)


def mark_sent(db, data, user):
    if user['role'] not in ('admin','cashier'): raise PermissionError('Tu perfil no permite registrar avisos enviados.')
    key=digest(required(data,'request_key',100));body=digest({k:v for k,v in data.items() if k!='request_key'})
    for row in db.execute("SELECT user_id,details FROM audit WHERE action='collection_notice_sent' ORDER BY id DESC"):
        prior=json.loads(row['details'])
        if prior.get('request')==key:
            if row['user_id']!=user['id'] or prior['body']!=body:
                raise ValidationError('La clave del aviso ya se usó con otros datos o usuario.')
            return dict(prior['result'],duplicate=True)
    kind=data.get('type');variant=integer(data.get('variant'),0,2)
    if kind not in TYPES: raise ValidationError('Selecciona un tipo de mensaje válido.')
    message=required(data,'message',1000000)
    context=debt_context(db,data.get('student_id'),flag(data.get('siblings',False)))
    ids=[g['id'] for g in context['groups']]
    if not ids: raise ValidationError('La cuenta ya no tiene deuda vencida. Revisa el aviso antes de marcarlo.')
    if data.get('student_ids')!=ids:
        raise ValidationError('Cambió el grupo de alumnos con deuda. Revisa el aviso antes de marcarlo.')
    note=f"Aviso de cobranza marcado manualmente como enviado · {TYPES[kind]} · versión {variant+1}."
    if len(ids)>1: note+=' Incluye hermanos con deuda.'
    stamp=datetime.now(timezone.utc).isoformat();note_ids=[]
    for sid in ids:
        result=db.execute('INSERT INTO collection_notes(student_id,note,promised_on,created_by,created_at) VALUES(?,?,NULL,?,?)',
                          (sid,note,user['id'],stamp));note_ids.append(result.lastrowid)
    result=dict(saved=True,note_ids=note_ids,duplicate=False)
    audit(db,user['id'],'collection_notice_sent',dict(request=key,body=body,type=kind,variant=variant,
        student_ids=ids,guardian_id=context['guardian_id'],message_sha256=digest(message),result=result))
    return result


def action(db, endpoint, data, user):
    from .audit_chain import require
    from .clock_guard import require_database_clock
    require(db)
    require_database_clock(db)
    if endpoint=='collection-notice-settings': return save_settings(db,data,user)
    if endpoint=='collection-notice-template-preview': return example_preview(db,data,user)
    return mark_sent(db,data,user)
