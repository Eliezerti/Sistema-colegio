"""Pure, side-effect-free rules for the proposed income ledger.

Not installed as an API: caller-owned transactions, permissions, audit and migration
must be implemented before any live-bank import or account assignment is enabled.
Amounts are integer cents in the original currency; no implicit currency matching.
"""
from dataclasses import dataclass
from datetime import date, timedelta, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import csv
import hashlib
import io
import json
import re
import unicodedata


class IncomeError(ValueError):
    pass


MAX_CENTS = 99_999_999_900
METHODS = ('Efectivo', 'Transferencia', 'Pago móvil', 'Tarjeta', 'Otro')
CURRENCIES = ('USD', 'VES')


def text(value, limit=200, *, required=False):
    if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 for c in value):
        raise IncomeError('Texto inválido o demasiado largo.')
    value = value.strip()
    if required and not value:
        raise IncomeError('Falta un dato obligatorio.')
    return value


def cents(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= MAX_CENTS:
        raise IncomeError('El importe debe ser un entero positivo en centavos.')
    return value


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise IncomeError('Usa una fecha AAAA-MM-DD válida.')
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise IncomeError('Fecha inválida.') from None


def reference(value):
    """Numeric leading zeros are insignificant for matching, never for display."""
    original = text(value)
    normalized = ''.join(c for c in unicodedata.normalize('NFKC', original).upper() if c.isascii() and c.isalnum())
    return (normalized.lstrip('0') or '0') if normalized.isdigit() else normalized


@dataclass(frozen=True)
class Account:
    id: int
    name: str
    currency: str
    kind: str = 'bank'
    bank: str = ''
    last4: str = ''
    active: bool = True

    def __post_init__(self):
        if type(self.id) is not int or self.id < 1 or self.currency not in CURRENCIES or self.kind not in ('bank', 'cash') or type(self.active) is not bool:
            raise IncomeError('Cuenta inválida.')
        text(self.name, required=True); text(self.bank)
        if any(re.search(r'[0-9]{12,}', re.sub(r'[\s-]','',value)) for value in (self.name,self.bank)):
            raise IncomeError('No guardes números completos de cuenta en el nombre o banco.')
        if not isinstance(self.last4, str) or (self.last4 and not re.fullmatch('[0-9]{4}', self.last4)):
            raise IncomeError('Guarda únicamente los últimos cuatro dígitos.')
        if self.kind == 'cash' and (self.bank or self.last4):
            raise IncomeError('Caja efectivo no lleva banco ni dígitos de cuenta.')


def destination(account, currency, method):
    if not isinstance(account, Account) or not account.active or account.currency != currency or method not in METHODS:
        raise IncomeError('Selecciona una cuenta activa de la misma moneda.')
    if (method == 'Efectivo') != (account.kind == 'cash'):
        raise IncomeError('Efectivo va a Caja efectivo; los demás métodos a una cuenta bancaria.')
    return account.id


def suggested_account(accounts, currency, method, last_used=None):
    """A suggestion only. Never assign a historic payment as a side effect."""
    compatible = []
    for account in accounts:
        try:
            destination(account, currency, method)
        except IncomeError:
            continue
        compatible.append(account)
    if method == 'Efectivo':
        return compatible[0].id if len(compatible) == 1 else None
    return last_used if any(a.id == last_used for a in compatible) else None


@dataclass(frozen=True)
class Movement:
    id: str
    account: int
    on: str
    amount: int
    currency: str
    reference: str = ''
    direction: str = 'credit'

    def __post_init__(self):
        text(self.id, 100, required=True); day(self.on); cents(self.amount); text(self.reference)
        if type(self.account) is not int or self.account < 1 or self.currency not in CURRENCIES or self.direction not in ('credit', 'debit'):
            raise IncomeError('Movimiento inválido.')


def proposals(bank, ledger, *, tolerance_days=3):
    """One-to-one auto proposals require a unique candidate on BOTH sides.

    Many-to-one and cross-currency links always need explicit review. This function
    suggests; it does not authorize, persist or automatically post a transaction.
    """
    if type(tolerance_days) is not int or not 0 <= tolerance_days <= 31:
        raise IncomeError('Tolerancia inválida.')
    bank, ledger = list(bank), list(ledger)
    for records in (bank, ledger):
        if any(not isinstance(r, Movement) for r in records) or len({r.id for r in records}) != len(records):
            raise IncomeError('Movimientos inválidos o identificadores repetidos.')
    from bisect import bisect_left, bisect_right
    if len(bank)>20000 or len(ledger)>20000:
        raise IncomeError('Divide la revisión en lotes de hasta 20.000 movimientos.')
    index = {}
    def key(row):
        return (row.account,row.currency,row.direction,row.amount,reference(row.reference))
    for row in ledger:
        index.setdefault(key(row),[]).append((day(row.on).toordinal(),row.id))
    groups={}
    for group,entries in index.items():
        entries.sort()
        groups[group]=(entries,[on for on,_ in entries],[0]*(len(entries)+1))
    candidates={};counts={}
    for row in bank:
        group=key(row)
        if group not in groups or not group[-1]:
            candidates[row.id]=[];counts[row.id]=0;continue
        entries,days,differences=groups[group];on=day(row.on).toordinal()
        left=bisect_left(days,on-tolerance_days);right=bisect_right(days,on+tolerance_days)
        counts[row.id]=right-left
        candidates[row.id]=[rid for _,rid in entries[left:min(right,left+50)]]
        # Count competing bank movements without expanding every possible edge.
        differences[left]+=1;differences[right]-=1
    frequency={}
    for entries,_,differences in groups.values():
        active=0
        for position,(_,rid) in enumerate(entries):
            active+=differences[position];frequency[rid]=active
    result=[]
    for row in bank:
        matches=candidates[row.id];count=counts[row.id]
        unique=count==1 and frequency[matches[0]]==1
        result.append(dict(bank_id=row.id,candidates=matches,candidate_count=count,
            candidates_truncated=count>len(matches),unique=unique,
            reason=('Sin candidato por cuenta, moneda, importe, referencia y fecha' if not count
                    else 'Candidato único en ambos lados' if unique
                    else 'Requiere revisión: varios candidatos compiten')))
    return result


def allocation_plan(bank, ledger, links, *, already_bank=None, already_ledger=None):
    """Validate explicit partial links without mixing currencies or double coverage.

    links: (bank_id, ledger_id, original_cents). Dates beyond tolerance and differing
    references remain review decisions, not permission to infer an exchange rate.
    """
    bank, ledger = list(bank), list(ledger)
    banks = {r.id:r for r in bank}; entries = {r.id:r for r in ledger}
    if len(banks) != len(bank) or len(entries) != len(ledger):
        raise IncomeError('Identificadores repetidos.')
    used_bank, used_ledger = dict(already_bank or {}), dict(already_ledger or {})
    for used, records in ((used_bank,banks),(used_ledger,entries)):
        if any(k not in records or type(v) is not int or not 0 <= v <= records[k].amount for k,v in used.items()):
            raise IncomeError('La cobertura anterior no es válida.')
    seen = set(); result = []
    for bid, lid, amount in links:
        cents(amount)
        if (bid,lid) in seen or bid not in banks or lid not in entries:
            raise IncomeError('Vínculo duplicado o inexistente.')
        seen.add((bid,lid)); b, e = banks[bid], entries[lid]
        if (b.account,b.currency,b.direction) != (e.account,e.currency,e.direction):
            raise IncomeError('No se pueden mezclar cuentas, monedas o créditos y débitos.')
        used_bank[bid] = used_bank.get(bid,0)+amount
        used_ledger[lid] = used_ledger.get(lid,0)+amount
        if used_bank[bid] > b.amount or used_ledger[lid] > e.amount:
            raise IncomeError('La cobertura supera el importe disponible.')
        result.append((bid,lid,amount))
    return {'links':result, 'bank_remaining':{k:r.amount-used_bank.get(k,0) for k,r in banks.items()},
            'ledger_remaining':{k:r.amount-used_ledger.get(k,0) for k,r in entries.items()}}


def cash_deposit(account, amount, payments, *, currency, reason=''):
    """payments: (payment_id, allocated_cents, available_cents, currency, method)."""
    destination(account, currency, 'Transferencia'); cents(amount)
    seen = set(); covered = 0
    for pid, allocated, available, original_currency, method in payments:
        if type(pid) is not int or pid < 1 or pid in seen or method != 'Efectivo' or original_currency != currency:
            raise IncomeError('Selecciona cobros en efectivo distintos y de la misma moneda.')
        cents(allocated); cents(available)
        if allocated > available:
            raise IncomeError('El recibo ya está cubierto por otro depósito.')
        seen.add(pid); covered += allocated
    if not seen:
        raise IncomeError('Vincula los cobros en efectivo que cubre la planilla.')
    difference = amount-covered
    if difference and len(text(reason,500)) < 10:
        raise IncomeError('Explica la diferencia del depósito, con al menos diez caracteres.')
    return {'covered':covered, 'deposited':amount, 'difference':difference}


def equivalents(amount, currency, rate):
    """Explicit historical BCV rate, including USD receipts (their stored '1' is NOT BCV)."""
    cents(amount)
    if currency not in CURRENCIES or isinstance(rate,bool):
        raise IncomeError('Moneda o tasa inválida.')
    try:
        r = Decimal(str(rate))
        if not r.is_finite() or not 0 < r <= Decimal('1000000000') or r.as_tuple().exponent < -6:
            raise InvalidOperation()
        rounded = lambda n:int(n.quantize(Decimal('1'),rounding=ROUND_HALF_UP))
        return {'usd':amount if currency=='USD' else rounded(Decimal(amount)/r),
                'ves':amount if currency=='VES' else rounded(Decimal(amount)*r)}
    except (InvalidOperation,ValueError,TypeError):
        raise IncomeError('Indica la tasa BCV histórica verificada, con hasta seis decimales.') from None


def parse_csv(raw, profile, account):
    """Strict editable mapping. No live import, bank access or retention of raw files.

    Profile: delimiter, encoding, date_format (%Y-%m-%d or %d/%m/%Y), decimal,
    columns mapping date/amount/reference/description[/bank_id]. Signed amount:
    credit positive, debit negative. No invented Provincial-specific layout.
    """
    if not isinstance(raw,bytes) or not 0 < len(raw) <= 2_000_000 or not isinstance(account,Account) or account.kind != 'bank' or not account.active:
        raise IncomeError('Selecciona un CSV de hasta 2 MB y una cuenta bancaria activa.')
    if not isinstance(profile,dict):raise IncomeError('Perfil de importación inválido.')
    delimiter = profile.get('delimiter',';'); encoding = profile.get('encoding','utf-8-sig')
    date_format = profile.get('date_format','%Y-%m-%d'); decimal = profile.get('decimal','.')
    columns = profile.get('columns',{})
    if delimiter not in (';',',','\t') or encoding not in ('utf-8-sig','cp1252') or date_format not in ('%Y-%m-%d','%d/%m/%Y') or decimal not in ('.',','):
        raise IncomeError('Perfil de importación inválido.')
    if not isinstance(columns,dict) or not {'date','amount','reference','description'} <= columns.keys() or set(columns)-{'date','amount','reference','description','bank_id'} or any(not isinstance(v,str) or not v for v in columns.values()) or len(set(columns.values())) != len(columns):
        raise IncomeError('Mapea columnas distintas de fecha, importe, referencia y descripción.')
    try:
        reader = csv.reader(io.StringIO(raw.decode(encoding),newline=''),delimiter=delimiter,strict=True)
        headers = next(reader)
        if len(headers)>50 or len(set(headers)) != len(headers) or not set(columns.values()) <= set(headers):
            raise IncomeError('Encabezados duplicados o faltan columnas del mapeo.')
        result = []; seen = {}; duplicate_rows = []
        for number, cells in enumerate(reader,2):
            if not any(cells):continue
            if len(result)>=10000 or len(cells)!=len(headers) or any(len(c)>2000 or '\x00' in c for c in cells):
                raise IncomeError(f'Fila {number}: tamaño o columnas inválidos.')
            values = dict(zip(headers,cells)); get = lambda key: values[columns[key]].strip()
            stamp = datetime.strptime(get('date'),date_format).date().isoformat()
            # Do not guess separators or strip grouping separators: ambiguous amounts fail.
            value = get('amount')
            pattern = r'-?(?:0|[1-9][0-9]*)(?:'+re.escape(decimal)+r'[0-9]{1,2})?'
            if not re.fullmatch(pattern,value):
                raise IncomeError(f'Fila {number}: importe inválido; sin separadores de miles.')
            signed = Decimal(value.replace(decimal,'.'))*100
            amount = cents(abs(int(signed))); direction = 'credit' if signed>0 else 'debit'
            ref = text(get('reference')); description = text(get('description'),500)
            bank_id = text(get('bank_id'),100) if 'bank_id' in columns else ''
            canonical = json.dumps([account.id,stamp,amount,account.currency,direction,reference(ref),description],ensure_ascii=False,separators=(',',':'))
            content_hash = hashlib.sha256(canonical.encode()).hexdigest()
            identity = 'bank:'+bank_id if bank_id else 'content:'+content_hash
            if identity in seen:
                # Identical-looking transfers may be legitimate when the bank supplies no ID.
                # Flag for review; never silently throw an income away.
                if bank_id:raise IncomeError(f'Fila {number}: identificador bancario repetido.')
                duplicate_rows.append({'row':number,'first_row':seen[identity],'reason':'Posible duplicado; falta identificador único del banco'})
            seen.setdefault(identity,number)
            identifier = str(number)
            result.append({'movement':Movement(identifier,account.id,stamp,amount,account.currency,ref,direction),
                           'description':description,'bank_id':bank_id,'fingerprint':content_hash,'row':number})
    except (UnicodeError,csv.Error,StopIteration,ValueError,InvalidOperation) as error:
        if isinstance(error,IncomeError):raise
        raise IncomeError('CSV inválido: revisa codificación, fecha, importe y mapeo.') from None
    if not result:raise IncomeError('El archivo no contiene movimientos.')
    return {'file_sha256':hashlib.sha256(raw).hexdigest(),'rows':result,'duplicates':duplicate_rows,
            'status':'VISTA PREVIA: no se ha importado ni conciliado ningún movimiento'}


def parse_statement(raw, filename, profile, account):
    """Preview CSV or first XLSX sheet. No macros, formulas or external links.

    References and bank IDs must be TEXT in Excel, since lost leading zeros
    cannot be recovered from a numeric cell. Dates may use actual Excel serials.
    """
    if not isinstance(profile,dict) or not isinstance(filename,str):
        raise IncomeError('Indica archivo y perfil válidos.')
    if filename.lower().endswith('.csv'):
        return parse_csv(raw,profile,account)
    if not filename.lower().endswith('.xlsx') or not isinstance(raw,bytes) or not 0 < len(raw) <= 2_000_000:
        raise IncomeError('Selecciona CSV o Excel .xlsx de hasta 2 MB; no .xls ni macros.')
    import zipfile
    from xml.etree import ElementTree as ET
    from pathlib import PurePosixPath
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos=archive.infolist(); names=archive.namelist()
            if len(infos)>200 or len(set(names)) != len(names) or sum(i.file_size for i in infos)>12_000_000 or any(i.flag_bits & 1 for i in infos):
                raise IncomeError('Excel cifrado, repetido o demasiado grande al expandir.')
            if any('vba' in n.lower() or 'externallinks/' in n.lower() for n in names):
                raise IncomeError('No se importan macros ni vínculos externos.')
            def xml(name):
                source=archive.read(name)
                # Reject UTF-16/32 XML and DTDs rather than attempting entity expansion.
                if b'\x00' in source or b'<!DOCTYPE' in source.upper() or b'<!ENTITY' in source.upper():
                    raise IncomeError('XML no permitido en el Excel.')
                return ET.fromstring(source)
            for name in names:
                if name.endswith('.rels') and any(r.get('TargetMode')=='External' for r in xml(name)):
                    raise IncomeError('No se importan vínculos externos.')
            workbook=xml('xl/workbook.xml')
            sheet=workbook.find('s:sheets/s:sheet',ns)
            if sheet is None:raise IncomeError('El Excel no contiene hojas.')
            rid=sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            relation=next(r for r in xml('xl/_rels/workbook.xml.rels') if r.get('Id')==rid)
            target=relation.get('Target','')
            path=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            if '..' in PurePosixPath(path).parts or not path.startswith('xl/'):
                raise IncomeError('Hoja no permitida.')
            props=workbook.find('s:workbookPr',ns)
            epoch1904=props is not None and props.get('date1904') in ('1','true')
            shared=[]
            if 'xl/sharedStrings.xml' in names:
                shared=[''.join(node.itertext()) for node in xml('xl/sharedStrings.xml').findall('s:si',ns)]
            matrix=[]; types=[]
            for row in xml(path).findall('s:sheetData/s:row',ns):
                if len(matrix)>10000:raise IncomeError('Máximo 10.000 movimientos.')
                values={}; kinds={}
                for cell in row.findall('s:c',ns):
                    if cell.find('s:f',ns) is not None:raise IncomeError('No se importan fórmulas; pega como valores.')
                    ref=re.fullmatch(r'([A-Z]{1,3})[1-9][0-9]*',cell.get('r',''))
                    if not ref:raise IncomeError('Celda inválida.')
                    col=0
                    for char in ref[1]:col=col*26+ord(char)-64
                    if col>50 or col in values:raise IncomeError('Columnas excesivas o celdas repetidas.')
                    kind=cell.get('t','n');value=cell.findtext('s:v','',ns)
                    if kind=='s':
                        if not value.isascii() or not value.isdigit() or not 0 <= int(value) < len(shared):
                            raise IncomeError('Índice de texto compartido inválido.')
                        value=shared[int(value)]
                    elif kind=='inlineStr':
                        node=cell.find('s:is',ns)
                        value=''.join(node.itertext()) if node is not None else ''
                    elif kind not in ('n','str','d'):raise IncomeError('Tipo de celda no permitido.')
                    if len(value)>2000:raise IncomeError('Celda demasiado larga.')
                    values[col-1]=value; kinds[col-1]=kind
                if not any(values.values()):continue
                width=max(values,default=-1)+1
                matrix.append([values.get(n,'') for n in range(width)])
                types.append(kinds)
            if not matrix:raise IncomeError('El Excel no contiene datos.')
            headers=matrix[0]; columns=profile.get('columns',{})
            if not isinstance(columns,dict):raise IncomeError('Mapeo inválido.')
            for index,row in enumerate(matrix[1:],1):
                row.extend(['']*(len(headers)-len(row)))
                for field in ('reference','bank_id'):
                    header=columns.get(field)
                    if header in headers:
                        col=headers.index(header)
                        if row[col] and types[index].get(col)=='n':
                            raise IncomeError('Referencia e identificador bancario deben ser texto en Excel para conservar ceros.')
                header=columns.get('date')
                if header in headers:
                    col=headers.index(header)
                    if types[index].get(col)=='n' and row[col]:
                        serial=Decimal(row[col])
                        if not serial.is_finite() or serial != serial.to_integral_value() or not 1 <= serial <= 2_958_465 or (not epoch1904 and serial==60):
                            raise IncomeError('Fecha numérica de Excel inválida o con hora.')
                        epoch=date(1904,1,1) if epoch1904 else date(1899,12,30) if serial>60 else date(1899,12,31)
                        row[col]=(epoch+timedelta(days=int(serial))).strftime(profile.get('date_format','%Y-%m-%d'))
                    elif types[index].get(col)=='d' and row[col]:
                        row[col]=day(row[col]).strftime(profile.get('date_format','%Y-%m-%d'))
                header=columns.get('amount')
                if header in headers:
                    col=headers.index(header)
                    if types[index].get(col)=='n' and row[col] and profile.get('decimal','.')==',':
                        row[col]=row[col].replace('.',',')
            buffer=io.StringIO(newline='');writer=csv.writer(buffer,delimiter=profile.get('delimiter',';'))
            writer.writerows(matrix)
            result=parse_csv(buffer.getvalue().encode('utf-8-sig'),dict(profile,encoding='utf-8-sig'),account)
            result['file_sha256']=hashlib.sha256(raw).hexdigest()
            result['date_epoch']='1904' if epoch1904 else '1900'
            return result
    except (zipfile.BadZipFile,KeyError,ET.ParseError,StopIteration,ValueError,IndexError,OverflowError,InvalidOperation,TypeError) as error:
        if isinstance(error,IncomeError):raise
        raise IncomeError('Excel inválido: revisa la primera hoja, el mapeo y los tipos de celda.') from None
