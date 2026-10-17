"""Validated roster imports, immutable daily closes and family documents."""
import base64
import csv
import hashlib
import io
import json
import re
import sqlite3
import unicodedata
import zipfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET

from .db import ValidationError, audit, charges, integer, local_today, money, required, valid_date, valid_period, synchronize_monthly_charges
from .documents import store

LEGACY_COLUMNS = ('representante_nombre','representante_cedula','representante_telefono',
    'representante_email','representante_direccion','alumno_nombre','alumno_cedula',
    'nacimiento','grado','ano_escolar','mensualidad_usd','descuento_pct',
    'inicio_matricula','fin_matricula','estado','observaciones')
COLUMNS = LEGACY_COLUMNS + ('primer_mes_cobro',)
EXPORT_COLUMNS = COLUMNS + ('alumno_codigo','grado_capacidad','alumno_archivado',
                            'representante_archivado','saldo_usd_informativo')
OLD_EXPORT_COLUMNS = ('alumno','codigo','documento','grado','ano escolar',
                      'representante','telefono','estado','saldo usd')
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFD',str(value)).upper() if c.isalnum())


def import_date(value, column):
    """Accept unambiguous Venezuelan day/month/year as well as ISO dates."""
    value = str(value).strip()
    match = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})', value)
    try:
        if match:
            return date(int(match[3]),int(match[2]),int(match[1])).isoformat()
        return valid_date(value)
    except (ValueError,ValidationError):
        raise ValidationError(f'{column}: fecha inválida «{value}». Usa AAAA-MM-DD, por ejemplo 2016-04-23, o una fecha de Excel.')


def import_amount(value):
    value = str(value).strip()
    if re.fullmatch(r'\d+,\d{1,2}', value): value=value.replace(',','.')
    try: return str(Decimal(money(value))/100)
    except ValidationError:
        raise ValidationError('mensualidad_usd: usa dólares sin símbolos ni miles, con hasta dos decimales; ejemplo 100.00. No escribas el precio ya descontado.')


def import_period(value):
    value = str(value).strip()
    if not value:
        return ''
    # Excel can store the selected month as a date rather than a text cell.
    if len(value) != 7:
        value = import_date(value,'primer_mes_cobro')[:7]
    return valid_period(value)


def import_integer(value,column,minimum,maximum):
    try: return integer(value,minimum,maximum)
    except ValidationError:
        raise ValidationError(f'{column}: escribe un entero entre {minimum} y {maximum}, sin símbolos. El año escolar lleva solo el año de inicio y el descuento no lleva %.')


def import_template(xlsx=False, grades=(), settings=None, roster_rows=None, columns=COLUMNS):
    from xml.sax.saxutils import escape
    from .import_guide import FIELDS, STEPS
    if not xlsx:
        out = io.StringIO(); csv.writer(out, delimiter=';').writerow(COLUMNS)
        return out.getvalue().encode('utf-8-sig')
    settings = settings or {}
    year = int(settings.get('school_year',local_today().year))
    month = int(settings.get('start_month',9))
    start = date(year,month,1).isoformat()
    end = (date(year+1,month,1)-timedelta(days=1)).isoformat()
    sheets = [
        ('Alumnos',[columns]+(roster_rows or []),True),
        ('Instrucciones',[['PASO','INSTRUCCIÓN']]+[[str(i),t] for i,t in enumerate(STEPS,1)]+[['','','','']]+[['COLUMNA','OBLIGATORIA','QUÉ ESCRIBIR','EJEMPLO']]+FIELDS,False),
        ('Grados',[['NOMBRE EXACTO DEL GRADO / SECCIÓN']]+[[g] for g in grades],False),
    ]
    out = io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        overrides = ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,len(sheets)+1))
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'+overrides+'</Types>')
        z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml','<workbook xmlns="'+NS['s']+'" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'+''.join(f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>' for i,(name,_,_) in enumerate(sheets,1))+'</sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(sheets)+1))+'<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr('xl/styles.xml','<styleSheet xmlns="'+NS['s']+'"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF245D50"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="49" fontId="1" fillId="2" borderId="0" xfId="0"><alignment wrapText="1"/></xf><xf numFmtId="49" fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="top" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        for i,(name,records,roster) in enumerate(sheets,1):
            widths = [24]*len(columns) if roster else ([12,110,55,28] if name=='Instrucciones' else [65])
            cols=''.join(f'<col min="{n}" max="{n}" width="{w}" customWidth="1" style="2"/>' for n,w in enumerate(widths,1))
            rows=[]
            for n,record in enumerate(records,1):
                cells=''.join(f'<c r="{chr(65+j)}{n}" t="inlineStr" s="{1 if n==1 else 2}"><is><t xml:space="preserve">{escape(str(v))}</t></is></c>' for j,v in enumerate(record))
                rows.append(f'<row r="{n}" ht="{36 if roster else 50}" customHeight="1">{cells}</row>')
            z.writestr(f'xl/worksheets/sheet{i}.xml','<worksheet xmlns="'+NS['s']+'"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>'+cols+'</cols><sheetData>'+''.join(rows)+'</sheetData></worksheet>')
    return out.getvalue()


def export_roster(state, xlsx=False):
    """Export the current enrollment and linked guardian, not the financial ledger."""
    guardians = {g['id']:g for g in state['guardians']}
    grades = {g['id']:g for g in state['grades']}
    records = []
    for s in state['students']:
        g = guardians[s['guardian_id']]
        records.append([g['name'],g['document'],g['phone'],g['email'],g['address'],
            s['name'],'' if s['document']==s['student_code'] else s['document'],s['birth_date'] if s['birth_date']>='1900-01-01' else '',
            s['grade_name'],str(s['school_year']),format(Decimal(s['monthly_fee'])/100,'.2f'),
            str(s['discount']),s['enrollment_start'],s['enrollment_end'],s['status'],s['notes'],
            s['billing_start'] or s['enrollment_start'][:7],s['student_code'],
            str(grades[s['grade_id']]['capacity']),str(int(bool(s['archived']))),
            str(int(bool(g['archived']))),format(Decimal(s['balance'])/100,'.2f')])
    if xlsx:
        return import_template(True,[g['name'] for g in state['grades']],state['settings'],records,EXPORT_COLUMNS)
    out=io.StringIO(newline='');writer=csv.writer(out,delimiter=';');writer.writerow(EXPORT_COLUMNS)
    for record in records:
        # Escape both formula-like text and literal leading quotes reversibly.
        writer.writerow(["'"+v if v.startswith("'") or v.lstrip().startswith(('=','+','-','@')) else v for v in record])
    return out.getvalue().encode('utf-8-sig')


def parse_import(data):
    try:
        raw = base64.b64decode(data.get('content',''),validate=True)
    except (ValueError, TypeError):
        raise ValidationError('Archivo inválido.')
    if not raw or len(raw)>2_000_000:
        raise ValidationError('Selecciona un archivo de hasta 2 MB.')
    name = str(data.get('filename','')).lower()
    physical_rows = None
    if name.endswith('.csv'):
        try: text = raw.decode('utf-8-sig')
        except UnicodeDecodeError: text = raw.decode('cp1252')
        try:
            # Optional final cells may be omitted; detect the separator from the fixed header.
            dialect = csv.Sniffer().sniff(text.splitlines()[0],delimiters=';,\t')
            matrix = list(csv.reader(io.StringIO(text),dialect))
        except csv.Error:
            raise ValidationError('CSV inválido. Usa la plantilla con separador punto y coma.')
    elif name.endswith('.xlsx'):
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                if len(z.infolist())>200 or sum(i.file_size for i in z.infolist())>12_000_000:
                    raise ValidationError('El Excel expandido es demasiado grande.')
                def xml(path):
                    source = z.read(path)
                    if b'<!DOCTYPE' in source.upper() or b'<!ENTITY' in source.upper():
                        raise ValidationError('El Excel contiene XML no permitido.')
                    return ET.fromstring(source)
                workbook = xml('xl/workbook.xml')
                properties=workbook.find('s:workbookPr',NS)
                epoch=date(1904,1,1) if properties is not None and properties.get('date1904') in ('1','true') else date(1899,12,30)
                sheet = workbook.find('s:sheets/s:sheet',NS)
                rid = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                rel = next(r for r in xml('xl/_rels/workbook.xml.rels') if r.get('Id')==rid)
                target = rel.get('Target','')
                path = target.lstrip('/') if target.startswith('/') else 'xl/'+target
                if rel.get('TargetMode')=='External' or '..' in PurePosixPath(path).parts:
                    raise ValidationError('Hoja de Excel no permitida.')
                strings = []
                if 'xl/sharedStrings.xml' in z.namelist():
                    strings = [''.join(e.itertext()) for e in xml('xl/sharedStrings.xml').findall('s:si',NS)]
                matrix, physical_rows = [], []
                for row in xml(path).findall('s:sheetData/s:row',NS):
                    values = ['']*len(EXPORT_COLUMNS)
                    for cell in row.findall('s:c',NS):
                        if cell.find('s:f',NS) is not None:
                            raise ValidationError('No se importan fórmulas. En Excel pega los datos como valores.')
                        ref = re.fullmatch(r'([A-Z]+)[0-9]+',cell.get('r',''))
                        if not ref: raise ValidationError('Celda de Excel inválida.')
                        col = 0
                        for c in ref[1]: col=col*26+ord(c)-64
                        val = cell.findtext('s:v','',NS)
                        kind = cell.get('t','')
                        if kind=='s': val=strings[int(val)]
                        if kind=='inlineStr': val=''.join(cell.find('s:is',NS).itertext())
                        if col>len(EXPORT_COLUMNS):
                            if val: raise ValidationError('El Excel contiene columnas adicionales; usa la plantilla.')
                            continue
                        if matrix and kind not in ('s','inlineStr','str','d') and val:
                            if str(matrix[0][col-1]).strip().lower() in ('nacimiento','inicio_matricula','fin_matricula','primer_mes_cobro'):
                                val = (epoch+timedelta(days=int(Decimal(val)))).isoformat()
                            else: val = format(Decimal(val),'f').rstrip('0').rstrip('.') if '.' in val else val
                        values[col-1]=val
                    matrix.append(values)
                    physical_rows.append(int(row.get('r',len(matrix))))
        except (zipfile.BadZipFile, KeyError, ET.ParseError, ValueError, IndexError, AttributeError, StopIteration, InvalidOperation, OverflowError):
            raise ValidationError('Excel inválido. Usa la primera hoja de la plantilla .xlsx, sin contraseña ni macros.')
    else:
        raise ValidationError('Selecciona un archivo .csv o .xlsx (no .xls).')
    headers = tuple(str(c).strip().lower() for c in matrix[0]) if matrix else ()
    if physical_rows:
        while headers and not headers[-1]: headers=headers[:-1]
    if headers == OLD_EXPORT_COLUMNS:
        raise ValidationError('Este es un listado antiguo de 9 columnas, no una exportación completa para importar. Le faltan cédulas de representantes, tarifas, descuentos y fechas. En la versión nueva, vuelve a exportar desde Alumnos y matrículas y selecciona Excel o CSV. No uses Saldo USD como mensualidad. Para trasladar también pagos y saldos exactos, usa un respaldo completo.')
    if headers not in (COLUMNS,LEGACY_COLUMNS,EXPORT_COLUMNS):
        missing = [c for c in COLUMNS if c not in headers]
        raise ValidationError('Encabezados incorrectos. Completa la primera hoja Alumnos, conserva las 17 columnas y su orden. También se admite la plantilla anterior de 16 columnas.' + (' Faltan: '+', '.join(missing) if missing else ' Descarga una plantilla nueva.'))
    # Preserve physical Excel/CSV row numbers even when users leave blank rows.
    numbered = [((physical_rows[i-1] if physical_rows else i),r) for i,r in enumerate(matrix[1:],2) if any(str(v).strip() for v in r)]
    matrix = [r for _,r in numbered]
    if not 1<=len(matrix)<=1000:
        raise ValidationError('El archivo debe contener entre 1 y 1000 filas de alumnos.')
    records = []
    for index,row in numbered:
        if physical_rows:
            if any(str(v).strip() for v in row[len(headers):]):
                raise ValidationError(f'Fila {index}: columna adicional sin encabezado. Usa la plantilla o la exportación completa.')
            row=row[:len(headers)]
        if headers==EXPORT_COLUMNS:
            if len(row)!=len(EXPORT_COLUMNS):
                raise ValidationError(f'Fila {index}: columnas de exportación incompletas o campo demasiado largo.')
            values=[str(v).strip() for v in row]
            if not physical_rows:
                values=[v[1:] if v.startswith("'") else v for v in values]
            if any(len(v)>2000 for v in values):
                raise ValidationError(f'Fila {index}: campo demasiado largo.')
            records.append(dict(zip(EXPORT_COLUMNS,values),_row=index,_format='export'))
            continue
        if len(row)==len(LEGACY_COLUMNS):
            row=list(row)+['']
        if headers==LEGACY_COLUMNS and len(row)==len(COLUMNS) and str(row[-1]).strip():
            raise ValidationError('Columna adicional sin encabezado: descarga la plantilla con primer_mes_cobro.')
        if len(row)!=len(COLUMNS) or any(len(str(v))>2000 for v in row):
            raise ValidationError('Fila con columnas incorrectas o un campo demasiado largo.')
        records.append(dict(zip(COLUMNS,(str(v).strip() for v in row)), _row=index,_format='template'))
    return records, hashlib.sha256(raw).hexdigest()


def import_roster(db,data,user,save_record):
    records,digest = parse_import(data)
    preview = data.get('preview') is True
    if not preview and data.get('confirmed_hash')!=digest:
        raise ValidationError('Revisa la vista previa antes de confirmar este archivo.')
    billing_default = local_today().strftime('%Y-%m')
    if not preview and data.get('confirmed_month') != billing_default:
        raise ValidationError('Vuelve a revisar el archivo: el mes de cobro debe coincidir con el de la vista previa.')
    errors, imported = [], []
    before_guardians = db.execute('SELECT COUNT(*) FROM guardians').fetchone()[0]
    original_guardian_ids={g[0] for g in db.execute('SELECT id FROM guardians')}
    original_student_ids={s[0] for s in db.execute('SELECT id FROM students')}
    before_grades = db.execute('SELECT COUNT(*) FROM grades').fetchone()[0]
    before_balance = sum(c['balance'] for c in charges(db))
    source_balance=0;archived_guardians=set();capacities={};guardian_states={}
    db.execute('SAVEPOINT roster_batch')
    for r in records:
        index=r['_row']
        db.execute('SAVEPOINT roster_row')
        try:
            exported=r['_format']=='export'
            archived=import_integer(r['alumno_archivado'],'alumno_archivado',0,1) if exported else 0
            guardian_archived=import_integer(r['representante_archivado'],'representante_archivado',0,1) if exported else 0
            if guardian_archived and not archived:
                raise ValidationError('Un representante archivado solo puede tener alumnos archivados en esta exportación.')
            if archived and r['estado'].lower() not in ('inactive','inactivo'):
                raise ValidationError('Un alumno archivado debe estar inactivo.')
            code=r['alumno_codigo'] if exported else ''
            if exported and (not re.fullmatch(r'AL-\d{6,10}',code) or db.execute('SELECT 1 FROM students WHERE student_code=? OR document=?',(code,code)).fetchone()):
                raise ValidationError('Código de alumno inválido o ya existente. No se puede importar dos veces la misma ficha.')
            if exported:
                if not re.fullmatch(r'\d{1,18}(?:\.\d{1,2})?',r['saldo_usd_informativo']):
                    raise ValidationError('saldo_usd_informativo: importe USD inválido. Este campo no se usa como tarifa ni restaura deudas.')
                exported_balance=int(Decimal(r['saldo_usd_informativo'])*100)
            doc = required(r,'representante_cedula')
            guardian_key=normalized(doc)
            if exported and guardian_key in guardian_states and guardian_states[guardian_key]!=guardian_archived:
                raise ValidationError('El mismo representante tiene estados de archivo distintos en el archivo.')
            matches = [g for g in db.execute('SELECT * FROM guardians') if normalized(g['document'])==normalized(doc)]
            if len(matches)>1: raise ValidationError('Hay más de un representante con esa cédula; revisa el directorio.')
            fields = {'name':required(r,'representante_nombre'),'document':doc,
                'phone':r['representante_telefono'],'email':r['representante_email'],'address':r['representante_direccion']}
            if matches:
                g = matches[0]
                if exported and g['id'] in original_guardian_ids and bool(g['archived'])!=bool(guardian_archived):
                    raise ValidationError('El representante existente tiene un estado de archivo distinto. Revisa su ficha.')
                for key in ('name','phone','email','address'):
                    if fields[key] and normalized(fields[key])!=normalized(g[key]):
                        raise ValidationError('La cédula del representante existe con datos distintos. Corrige el archivo o el directorio.')
                guardian_id=g['id']
            else: guardian_id=save_record(db,'guardians',fields,user)['id']
            grade = db.execute('SELECT id FROM grades WHERE name=? COLLATE NOCASE',(required(r,'grado'),)).fetchone()
            if exported:
                capacity=import_integer(r['grado_capacidad'],'grado_capacidad',1,500)
                key=r['grado'].casefold()
                if key in capacities and capacities[key]!=capacity:
                    raise ValidationError('El mismo grado tiene capacidades distintas en el archivo.')
                if not grade:
                    grade_id=save_record(db,'grades',{'name':r['grado'],'capacity':capacity},user)['id']
                    grade={'id':grade_id}
            if not grade: raise ValidationError('Grado / sección inexistente. Créalo antes de importar y copia su nombre exacto.')
            name,birth = required(r,'alumno_nombre'),import_date(r['nacimiento'],'nacimiento') if r['nacimiento'] else ''
            if r['estado'].lower() not in ('','activo','inactivo','active','inactive'):
                raise ValidationError('estado: escribe activo o inactivo; vacío significa activo.')
            duplicates=db.execute('SELECT id FROM students WHERE guardian_id=? AND name=? COLLATE NOCASE AND birth_date=?',(guardian_id,name,birth)).fetchall()
            if any(not exported or s[0] in original_student_ids for s in duplicates):
                raise ValidationError('Alumno repetido: mismo nombre, nacimiento y representante.')
            student = save_record(db,'students',{'name':name,'document':r['alumno_cedula'],
                '_import_code':code or None,'_import_archived':bool(archived),
                'birth_date':birth,'guardian_id':guardian_id,'grade_id':grade['id'],
                'school_year':import_integer(r['ano_escolar'],'ano_escolar',2000,2100),'monthly_fee':import_amount(r['mensualidad_usd']),
                'discount':import_integer(r['descuento_pct'] or '0','descuento_pct',0,100),'enrollment_start':import_date(r['inicio_matricula'],'inicio_matricula') if r['inicio_matricula'] else '',
                'enrollment_end':import_date(r['fin_matricula'],'fin_matricula') if r['fin_matricula'] else '',
                'billing_start':import_period(r['primer_mes_cobro']),'status':{'activo':'active','inactivo':'inactive'}.get(r['estado'].lower(),r['estado'].lower() or 'active'),
                'notes':r['observaciones']},user)
            if exported:
                capacities[key]=capacity
                guardian_states[guardian_key]=guardian_archived
                if guardian_archived: archived_guardians.add(guardian_id)
                source_balance+=exported_balance
            imported.append({'row':index,'student_name':name,'guardian_name':fields['name'],
                'grade_name':r['grado'],'student_code':student['student_code'],'billing_start':student['billing_start'],
                'status':r['estado'].lower() or 'active','archived':archived})
            db.execute('RELEASE roster_row')
        except (ValidationError,sqlite3.IntegrityError) as error:
            db.execute('ROLLBACK TO roster_row'); db.execute('RELEASE roster_row')
            errors.append({'row':index,'message':str(error) if isinstance(error,ValidationError) else 'Documento repetido o estado inválido.'})
    for guardian_id in archived_guardians:
        db.execute('UPDATE guardians SET archived=1 WHERE id=?',(guardian_id,))
    synchronize_monthly_charges(db)
    result = {'hash':digest,'billing_default':billing_default,'rows':len(records),'students':len(imported),
        'source':'export' if records[0]['_format']=='export' else 'template',
        'grades':db.execute('SELECT COUNT(*) FROM grades').fetchone()[0]-before_grades,
        'source_balance':source_balance if records[0]['_format']=='export' else None,
        'guardians':db.execute('SELECT COUNT(*) FROM guardians').fetchone()[0]-before_guardians,
        'new_balance':sum(c['balance'] for c in charges(db))-before_balance,
        'errors':errors,'lines':imported[:100],'preview':preview}
    if preview or errors: db.execute('ROLLBACK TO roster_batch')
    db.execute('RELEASE roster_batch')
    if not preview and errors:
        raise ValidationError(f"No se importó ninguna fila. Fila {errors[0]['row']}: {errors[0]['message']}")
    if not preview: audit(db,user['id'],'roster-import',{'students':len(imported),'guardians':result['guardians'],'grades':result['grades'],'file_hash':digest})
    return result


def ensure_open_day(db,on):
    if db.execute('SELECT 1 FROM cash_closures WHERE closed_on=? AND reopened_at IS NULL',(on,)).fetchone():
        raise ValidationError('La caja de esa fecha está cerrada. Administración debe reabrirla con un motivo antes de modificar movimientos.')


def cash_summary(db,on):
    on=valid_date(on)
    if on>local_today().isoformat(): raise ValidationError('No se puede cerrar una fecha futura.')
    lines = {}; movements=[]
    sources=[('payments','paid_on','income'),('expenses','spent_on','expense')]
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='other_income'").fetchone():sources.append(('other_income','received_on','income'))
    for table,column,direction in sources:
        for r in db.execute(f'SELECT * FROM {table} WHERE {column}=? ORDER BY id',(on,)):
            movement={'type':'other-income' if table=='other_income' else direction,'id':r['id'],'currency':r['currency'],'received_amount':r['received_amount'],
                'amount':r['amount'],'method':r['method'],'reference':r['reference'],'voided':r['voided'],'exchange_rate':r['exchange_rate']}
            movements.append(movement)
            if r['voided']: continue
            key=(r['method'],r['currency'])
            entry=lines.setdefault(key,{'method':key[0],'currency':key[1],'income':0,'expense':0,'net':0,'income_usd':0,'expense_usd':0})
            entry[direction]+=r['received_amount']; entry[direction+'_usd']+=r['amount']
            entry['net']=entry['income']-entry['expense']
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='cash_deposits'").fetchone():
        for r in db.execute('SELECT * FROM cash_deposits WHERE deposited_on=? ORDER BY id',(on,)):
            movements.append(dict(type='transfer',id=r['id'],currency=r['currency'],received_amount=r['amount'],amount=0,
                method='Efectivo → Transferencia',reference=r['reference'],voided=r['voided'],exchange_rate=''))
            if r['voided']:continue
            for method,sign in (('Efectivo',-1),('Transferencia',1)):
                key=(method,r['currency']);entry=lines.setdefault(key,dict(method=method,currency=r['currency'],income=0,expense=0,net=0,income_usd=0,expense_usd=0))
                entry['net']+=sign*r['amount']
    return {'closed_on':on,'lines':[lines[k] for k in sorted(lines)],'movements':movements,
        'preview_hash':hashlib.sha256(json.dumps(movements,sort_keys=True).encode()).hexdigest(),
        'income_usd':sum(v['income_usd'] for v in lines.values()),'expense_usd':sum(v['expense_usd'] for v in lines.values()),
        'active_id':(dict(r)['id'] if (r:=db.execute('SELECT id FROM cash_closures WHERE closed_on=? AND reopened_at IS NULL',(on,)).fetchone()) else None)}


def close_cash(db,data,user):
    summary = cash_summary(db,data.get('closed_on')); ensure_open_day(db,summary['closed_on'])
    if data.get('preview_hash')!=summary['preview_hash']:
        raise ValidationError('Los movimientos cambiaron desde la vista previa. Abre de nuevo el cierre y revisa los importes.')
    counts = []
    for currency in ('USD','VES'):
        opening=money(data.get('opening_'+currency,'0')); counted=money(data.get('counted_'+currency))
        expected=opening+sum(r['net'] for r in summary['lines'] if r['currency']==currency and r['method']=='Efectivo')
        if expected<0: raise ValidationError('El efectivo esperado es negativo. Revisa el fondo inicial y los egresos.')
        counts.append({'currency':currency,'opening':opening,'expected':expected,'counted':counted,'difference':counted-expected})
    notes=str(data.get('notes','')).strip()[:2000]
    if any(c['difference'] for c in counts) and not notes:
        raise ValidationError('Explica las diferencias del arqueo en observaciones.')
    summary.update(counts=counts,notes=notes,school=dict(db.execute('SELECT key,value FROM settings')),
        operator=user['name'],issued_on=local_today().isoformat(),created_at=datetime.now(timezone.utc).isoformat())
    result=db.execute('INSERT INTO cash_closures(closed_on,snapshot_json,created_at,created_by) VALUES(?,?,?,?)',
        (summary['closed_on'],json.dumps(summary,ensure_ascii=False),summary['created_at'],user['id']))
    audit(db,user['id'],'cash-close',{'id':result.lastrowid,'closed_on':summary['closed_on']})
    return {'id':result.lastrowid}


def reopen_cash(db,data,user):
    target=integer(data.get('id'),1,2147483647); reason=required(data,'reason',500)
    result=db.execute('UPDATE cash_closures SET reopened_at=?,reopen_reason=? WHERE id=? AND reopened_at IS NULL',
        (datetime.now(timezone.utc).isoformat(),reason,target))
    if not result.rowcount: raise ValidationError('Cierre inexistente o ya reabierto.')
    audit(db,user['id'],'cash-reopen',{'id':target,'reason':reason})
    return {'saved':True}


def guardian_account(db,guardian_id):
    guardian_id=integer(guardian_id,1,2147483647)
    g=db.execute('SELECT * FROM guardians WHERE id=?',(guardian_id,)).fetchone()
    if not g: raise ValidationError('Representante inexistente.')
    students=[dict(s) for s in db.execute('SELECT s.*,gr.name AS grade_name FROM students s JOIN grades gr ON gr.id=s.grade_id WHERE guardian_id=? ORDER BY s.name',(guardian_id,))]
    if not students: raise ValidationError('Este representante no tiene alumnos vinculados.')
    smap={s['id']:s for s in students}; entries=[]
    for c in charges(db):
        if c['student_id'] not in smap: continue
        entries.append(dict(c,student_name=smap[c['student_id']]['name'],grade_name=smap[c['student_id']]['grade_name']))
    payments=[dict(p) for p in db.execute('SELECT p.id,p.student_id,p.paid_on,p.amount,p.received_amount,p.currency,p.exchange_rate,p.method,p.reference,p.voided,s.name AS student_name FROM payments p JOIN students s ON s.id=p.student_id WHERE s.guardian_id=? ORDER BY p.paid_on,p.id',(guardian_id,))]
    return {'guardian':dict(g),'students':students,'charges':entries,'payments':payments,
        'balance':sum(c['balance'] for c in entries),'overdue':sum(c['balance'] for c in entries if c['overdue']),
        'issued_on':local_today().isoformat()}


def issue_guardian_document(db,data,user):
    kind=data.get('kind')
    if kind not in ('account','solvency'): raise ValidationError('Documento de representante inválido.')
    doc=guardian_account(db,data.get('guardian_id'))
    if kind=='solvency' and doc['balance']:
        raise ValidationError('No se puede emitir solvencia: hay saldo pendiente en uno o más alumnos vinculados.')
    doc.update(kind=kind,school=dict(db.execute('SELECT key,value FROM settings')))
    return {'id':store(db,'guardian_documents',doc,user['id'])}


def load_administrative_document(db,kind,target):
    table={'guardian-document':'guardian_documents','cash-close':'cash_closures'}[kind]
    r=db.execute(f'SELECT * FROM {table} WHERE id=?',(target,)).fetchone()
    if not r: raise ValidationError('Documento inexistente.')
    result=dict(json.loads(r['snapshot_json']),id=target)
    if kind=='cash-close': result.update(reopened_at=r['reopened_at'],reopen_reason=r['reopen_reason'])
    return result
