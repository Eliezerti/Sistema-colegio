"""Administrator-only filtered audit exports with spreadsheet injection protection."""
import csv
import io
import json
from datetime import datetime, timedelta, timezone
from .audit_chain import local_status, sanitize
from .db import ValidationError, valid_date
from .directory_reports import directory_pdf


LABELS = {'edit-values':'Cambio de datos', 'restore-backup':'Restauración de respaldo',
    'local-admin-password-reset':'Recuperación local de contraseña', 'trial-payments-cleared':'Limpieza única de cobros de prueba', 'reset_records':'Vaciado de registros',
    'setup':'Configuración inicial', 'settings':'Datos del colegio', 'rate':'Tasa BCV registrada',
    'confirm_rate':'Tasa BCV confirmada', 'payment':'Cobro registrado', 'payments':'Cobro registrado',
    'students':'Ficha de alumno', 'guardians':'Ficha de representante', 'grades':'Grado / sección',
    'employees':'Ficha de personal', 'positions':'Cargo del personal', 'users':'Usuario',
    'password':'Cambio de contraseña', 'session_idle_changed':'Tiempo de cierre de sesión',
    'generate':'Mensualidades generadas', 'void-payment':'Cobro anulado', 'void-expense':'Egreso anulado',
    'backup_directory':'Destino de respaldos', 'clock-confirm':'Fecha de la PC confirmada'}


def clean_entries(entries):
    result = []
    for row in entries:
        entry = dict(row)
        try:
            details = sanitize(json.loads(entry['details']))
            if isinstance(details,dict):
                responsible,actor = details.get('responsable'),details.get('actor')
                entry['operator'] = ((responsible.get('nombre') if isinstance(responsible,dict) else None)
                                     or (actor.get('name') if isinstance(actor,dict) else None) or entry['operator'])
            entry['details'] = json.dumps(details, ensure_ascii=False, sort_keys=True)
        except (ValueError, TypeError): entry['details'] = 'Detalle antiguo no estructurado; conserva el respaldo original para revisión técnica.'
        entry['operation'] = LABELS.get(entry['action'], 'Operación registrada')+' · '+entry['action']
        result.append(entry)
    return result


def report(db, query, user):
    where, values = [], []
    for key, sql in [('from', 'a.created_at>=?'), ('to', 'a.created_at<?')]:
        value = query.get(key, [''])[0]
        if value:
            day = valid_date(value)
            # Dates are entered as Venezuelan calendar days; convert boundaries to UTC.
            at = datetime.fromisoformat(day).replace(tzinfo=timezone(timedelta(hours=-4)))
            if key == 'to': at += timedelta(days=1)
            values.append(at.astimezone(timezone.utc).isoformat()); where.append(sql)
    search = query.get('search', [''])[0]
    if len(search) > 200: raise ValidationError('La búsqueda admite hasta 200 caracteres.')
    if search:
        where.append('(a.action LIKE ? OR u.name LIKE ? OR a.details LIKE ?)')
        values.extend(['%'+search+'%']*3)
    source = db.execute('''SELECT a.*,COALESCE(u.name,'Sistema / recuperación local') AS operator
        FROM audit a LEFT JOIN users u ON u.id=a.user_id '''+('WHERE '+' AND '.join(where) if where else '')+' ORDER BY a.id DESC', values)
    entries = clean_entries(source)
    return {'entries': entries, 'status': local_status(db), 'school': dict(db.execute('SELECT key,value FROM settings')),
            'operator': user['name'], 'filters': ' · '.join(f"{ {'from':'Desde','to':'Hasta','search':'Búsqueda'}[k]}: {v[0]}" for k,v in query.items() if k in ('from','to','search')) or 'Toda la bitácora'}


def csv_bytes(data):
    out = io.StringIO(newline='')
    writer = csv.writer(out)
    writer.writerow(['Estado de verificación', data['status']['message']])
    writer.writerow(['N.º','Fecha UTC','Usuario','Operación','Valores anteriores y nuevos / detalle'])
    def safe(value):
        value = str(value)
        return "'"+value if value.lstrip().startswith(('=', '+', '-', '@')) else value
    for r in data['entries']:
        writer.writerow([safe(r[k]) for k in ('id','created_at','operator','operation','details')])
    return ('\ufeff'+out.getvalue()).encode('utf-8')


def pdf_bytes(data):
    now = datetime.now(timezone(timedelta(hours=-4)))
    return directory_pdf({'title':'Bitácora de operaciones', 'school':data['school'],
        'issued_on': now.date().isoformat(), 'issued_at':now.strftime('%d/%m/%Y · %H:%M'),
        'operator': data['operator'], 'count_label':f"{len(data['entries'])} operaciones", 'filter_label':data['filters'],
        'headings':['N.º','Fecha UTC','Usuario','Operación','Detalle'], 'widths':[40,125,110,120,363],
        'lines':[[str(r[k]) for k in ('id','created_at','operator','operation','details')] for r in data['entries']],
        'note':data['status']['message']+' Las huellas detectan alteraciones; no impiden cambios de quien controle Windows.'})
