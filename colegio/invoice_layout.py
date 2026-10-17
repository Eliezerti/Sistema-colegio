"""Versioned preprinted-form geometry. Never allocates a fiscal number."""
import copy
import hashlib
import json
import math
import re
import string
from decimal import Decimal, InvalidOperation
from .db import ValidationError
from .pdf_fonts import text_width

MM = 72 / 25.4
VARIABLES = frozenset(('fecha','numero_factura','numero_control','cliente','documento_cliente',
    'direccion','concepto','forma_pago','referencia','tasa','exento','base','iva','igtf',
    'total','observaciones','usuario','recibo','moneda','mes','año','grado'))
DETAIL_KEYS = frozenset(('concepto','cantidad','precio','exento','total'))
WARNING = 'Confirma con tu contador que este medio de emisión es válido para el colegio.'


def number(value, low, high, label):
    if isinstance(value,bool) or not isinstance(value,(str,int,float)):
        raise ValidationError('Valor inválido: '+label)
    try: result=Decimal(str(value))
    except InvalidOperation: raise ValidationError('Valor inválido: '+label) from None
    if not result.is_finite() or not Decimal(str(low))<=result<=Decimal(str(high)):
        raise ValidationError('Fuera de rango: '+label)
    return float(result)


def text(value,limit,label,*,empty=True):
    if not isinstance(value,str) or len(value)>limit or (not empty and not value.strip()) or any(ord(c)<32 and c!='\n' for c in value):
        raise ValidationError('Texto inválido: '+label)
    try:value.encode('cp1252')
    except UnicodeError:raise ValidationError('Usa caracteres imprimibles en español: '+label) from None
    return value


def whole(value,low,high,label):
    if type(value) is not int or not low<=value<=high:raise ValidationError('Entero inválido: '+label)
    return value


def boolean(value,label):
    if type(value) is not bool:raise ValidationError('Marca explícitamente: '+label)
    return value


def exact_keys(value,keys,label):
    if not isinstance(value,dict) or set(value)!=set(keys):raise ValidationError('Campos inválidos: '+label)


def variables(value):
    text(value,2000,'texto con variables')
    try:
        for _,key,spec,conversion in string.Formatter().parse(value):
            if key is not None and (key not in VARIABLES or spec or conversion):
                raise ValidationError('Variable desconocida o formato no permitido: '+str(key))
    except ValueError:raise ValidationError('Llaves incompletas en el texto con variables.') from None
    return value


def paper_preset(name):
    if name=='media_vertical':w,h,pw,ph,placement,rotation=139.7,215.9,139.7,215.9,'full',0
    elif name=='media_horizontal':w,h,pw,ph,placement,rotation=215.9,139.7,215.9,139.7,'full',0
    elif name=='carta':w,h,pw,ph,placement,rotation=215.9,279.4,215.9,279.4,'full',0
    elif name in ('carta_arriba','carta_abajo'):
        w,h,pw,ph,placement,rotation=139.7,215.9,215.9,279.4,('top' if name=='carta_arriba' else 'bottom'),90
    else:raise ValidationError('Tamaño de papel desconocido.')
    return dict(width_mm=w,height_mm=h,page_width_mm=pw,page_height_mm=ph,placement=placement,rotation=rotation,margin_mm=5)


def field(identifier,source,x,y,w,h,**options):
    result=dict(id=identifier,kind='system',source=source,text='',visible=True,x_mm=x,y_mm=y,
        width_mm=w,height_mm=h,font='sans',size_pt=10,bold=False,italic=False,align='left',
        uppercase=False,leading=1.2,max_chars=300,overflow='wrap')
    result.update(options);return result


def example_template():
    return dict(format='Aula-forma-libre',version=1,name='Ejemplo media carta',calibrated=False,
        paper=paper_preset('media_vertical'),grid_mm=1,snap=True,background='',
        fields=[field('fecha','fecha',10,10,55,8),
            field('factura','numero_factura',75,10,54,8,visible=False),
            field('control','numero_control',75,18,54,8,visible=False),
            field('cliente','cliente',10,27,119,10,bold=True,size_pt=11),
            field('documento','documento_cliente',10,40,119,8),
            field('direccion','direccion',10,51,119,18),
            field('metodo','forma_pago',10,140,58,10),
            field('referencia','referencia',71,140,58,10),
            field('tasa','tasa',10,153,119,8),
            field('exento','exento',79,166,50,9,align='right'),
            field('total','total',79,178,50,11,align='right',bold=True,size_pt=12),
            field('observaciones','observaciones',10,195,119,11,size_pt=8)],
        details=dict(visible=True,y_mm=77,line_height_mm=10,max_lines=6,font='sans',size_pt=10,
            columns=[dict(key='concepto',x_mm=10,width_mm=79,align='left'),
                dict(key='cantidad',x_mm=91,width_mm=10,align='right'),
                dict(key='total',x_mm=104,width_mm=25,align='right')]))


def validate(raw):
    exact_keys(raw,('format','version','name','calibrated','paper','grid_mm','snap','background','fields','details'),'plantilla')
    if raw['format']!='Aula-forma-libre' or type(raw['version']) is not int or raw['version']!=1:
        raise ValidationError('Formato o versión de plantilla incompatible.')
    result=copy.deepcopy(raw);text(result['name'],100,'nombre',empty=False)
    boolean(result['calibrated'],'calibrada');boolean(result['snap'],'imán')
    result['grid_mm']=number(result['grid_mm'],.1,20,'cuadrícula')
    p=result['paper'];exact_keys(p,('width_mm','height_mm','page_width_mm','page_height_mm','placement','rotation','margin_mm'),'papel')
    for key in ('width_mm','height_mm','page_width_mm','page_height_mm'):p[key]=number(p[key],50,1000,key)
    p['margin_mm']=number(p['margin_mm'],0,30,'margen')
    if type(p['rotation']) is not int or p['rotation'] not in (0,90) or p['placement'] not in ('full','top','bottom'):
        raise ValidationError('Posición o giro del formulario inválido.')
    w,h=(p['height_mm'],p['width_mm']) if p['rotation']==90 else (p['width_mm'],p['height_mm'])
    available_h=p['page_height_mm'] if p['placement']=='full' else p['page_height_mm']/2
    if p['placement']!='full' and (abs(p['page_width_mm']-215.9)>.001 or abs(p['page_height_mm']-279.4)>.001):
        raise ValidationError('Arriba/abajo requiere una hoja carta vertical.')
    if w>p['page_width_mm']+.00001 or h>available_h+.00001:raise ValidationError('El formulario no cabe a tamaño real en ese papel; cambia orientación o medidas.')
    bg=result['background']
    if not isinstance(bg,str) or len(bg)>700000 or (bg and not bg.startswith('data:image/png;base64,')):
        raise ValidationError('El fondo requiere PNG RGB/RGBA, máximo 500 KB.')
    if bg:
        from .branding import pdf_logo
        try:pdf_logo(bg)
        except (ValueError,TypeError,OverflowError):raise ValidationError('Fondo PNG inválido.') from None
    fields=result['fields']
    if not isinstance(fields,list) or not 1<=len(fields)<=80:raise ValidationError('La plantilla requiere de 1 a 80 campos.')
    seen=set()
    for f in fields:
        exact_keys(f,('id','kind','source','text','visible','x_mm','y_mm','width_mm','height_mm','font','size_pt','bold','italic','align','uppercase','leading','max_chars','overflow'),'campo')
        if not isinstance(f['id'],str) or not re.fullmatch('[a-zA-Z][a-zA-Z0-9_-]{0,49}',f['id']) or f['id'] in seen:
            raise ValidationError('Identificador de campo inválido o repetido.')
        seen.add(f['id'])
        if f['kind'] not in ('system','text') or f['source'] not in VARIABLES or f['font'] not in ('sans','mono') or f['align'] not in ('left','center','right') or f['overflow'] not in ('error','wrap','shrink'):
            raise ValidationError('Opciones de campo inválidas.')
        variables(f['text'])
        for key in ('visible','bold','italic','uppercase'):boolean(f[key],key)
        for key in ('x_mm','y_mm'):f[key]=number(f[key],0,1000,key)
        for key in ('width_mm','height_mm'):f[key]=number(f[key],.1,1000,key)
        f['size_pt']=number(f['size_pt'],6,72,'tamaño de fuente');f['leading']=number(f['leading'],1,3,'interlineado')
        whole(f['max_chars'],1,3000,'máximo de caracteres')
        if f['visible']:inside(p,f['x_mm'],f['y_mm'],f['width_mm'],f['height_mm'])
    d=result['details'];exact_keys(d,('visible','y_mm','line_height_mm','max_lines','font','size_pt','columns'),'detalle')
    boolean(d['visible'],'detalle');d['y_mm']=number(d['y_mm'],0,1000,'Y detalle')
    d['line_height_mm']=number(d['line_height_mm'],2,100,'alto detalle');whole(d['max_lines'],1,100,'líneas detalle')
    d['size_pt']=number(d['size_pt'],6,36,'fuente detalle')
    if d['font'] not in ('sans','mono') or not isinstance(d['columns'],list) or not 1<=len(d['columns'])<=5:raise ValidationError('Columnas de detalle inválidas.')
    seen=set()
    for col in d['columns']:
        exact_keys(col,('key','x_mm','width_mm','align'),'columna')
        if col['key'] not in DETAIL_KEYS or col['key'] in seen or col['align'] not in ('left','center','right'):raise ValidationError('Columna desconocida o repetida.')
        seen.add(col['key']);col['x_mm']=number(col['x_mm'],0,1000,'X columna');col['width_mm']=number(col['width_mm'],.1,1000,'ancho columna')
        if d['visible']:inside(p,col['x_mm'],d['y_mm'],col['width_mm'],d['line_height_mm']*d['max_lines'])
    if 'concepto' not in seen or 'total' not in seen:raise ValidationError('El detalle requiere concepto y total.')
    if len(json.dumps(result,ensure_ascii=False).encode())>800000:raise ValidationError('Plantilla demasiado grande.')
    return result


def inside(p,x,y,w,h):
    m=p['margin_mm']
    if x<m-.00001 or y<m-.00001 or x+w>p['width_mm']-m+.00001 or y+h>p['height_mm']-m+.00001:
        raise ValidationError('Un campo o el detalle queda fuera del margen del formulario.')


def profile(raw=None):
    raw=raw or dict(name='Sin calibrar',x_tenths=0,y_tenths=0,scale=1,margin_mm=5)
    exact_keys(raw,('name','x_tenths','y_tenths','scale','margin_mm'),'perfil de impresora')
    return dict(name=text(raw['name'],100,'impresora',empty=False),
        x_tenths=whole(raw['x_tenths'],-500,500,'desplazamiento X'),
        y_tenths=whole(raw['y_tenths'],-500,500,'desplazamiento Y'),
        scale=number(raw['scale'],.95,1.05,'escala fina'),margin_mm=number(raw['margin_mm'],0,30,'margen de impresora'))


def parse_json(raw):
    if not isinstance(raw,str) or len(raw.encode('utf-8'))>800000:raise ValidationError('JSON de plantilla inválido o excesivo.')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValidationError('Clave repetida en el JSON de plantilla.')
            result[key]=value
        return result
    try:return validate(json.loads(raw,object_pairs_hook=pairs))
    except (ValueError,TypeError,RecursionError) as error:
        if isinstance(error,ValidationError):raise
        raise ValidationError('JSON de plantilla inválido.') from None


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def width(value,size,font,bold=False):
    return len(value)*size*.6 if font=='mono' else text_width(value,size,bold)


def lines(value,w,size,font,bold,wrap):
    result=[]
    for original in value.split('\n'):
        if not wrap:result.append(original);continue
        current=''
        for char in original:
            if current and width(current+char,size,font,bold)>w:
                split=current.rfind(' ')
                if split>0:result.append(current[:split]);current=current[split+1:]+char
                else:result.append(current);current=char
            else:current+=char
        result.append(current)
    return result


def fit(value,f):
    text(value,3000,'valor del campo')
    if f['uppercase']:value=value.upper()
    if len(value)>f['max_chars']:raise ValidationError('Texto demasiado largo en '+f['id']+'; no se imprimió cortado.')
    size=f['size_pt'];h=f['height_mm']*MM
    while True:
        # Conservative bounds cover ascenders/descenders and italic overhang
        # of all eight standard faces, not just the visible capital letters.
        padding=size*(.25 if f['italic'] else .2);w=f['width_mm']*MM-2*padding
        rows=lines(value,w,size,f['font'],f['bold'],f['overflow']!='error')
        if size*1.5+(len(rows)-1)*size*f['leading']<=h+.00001 and all(width(row,size,f['font'],f['bold'])<=w+.00001 for row in rows):return rows,size
        if f['overflow']!='shrink' or size<=6.00001:raise ValidationError('El texto no cabe en '+f['id']+'; aumenta el campo o revisa el texto.')
        size=max(6,round(size-.1,2))


def point(p,pr,x,y):
    """Top-left form millimeters -> top-left page millimeters."""
    if p['rotation']==90:x,y=p['height_mm']-y,x
    rh=p['width_mm'] if p['rotation']==90 else p['height_mm']
    rw=p['height_mm'] if p['rotation']==90 else p['width_mm']
    ox=(p['page_width_mm']-rw)/2 if p['placement']!='full' else 0
    oy=0 if p['placement'] in ('full','top') else p['page_height_mm']/2
    return ox+x*pr['scale']+pr['x_tenths']/10,oy+y*pr['scale']+pr['y_tenths']/10


def page_box(p,pr,x,y,w,h):
    points=[point(p,pr,*v) for v in ((x,y),(x+w,y),(x,y+h),(x+w,y+h))]
    m=pr['margin_mm']
    if any(px<m-.00001 or py<m-.00001 or px>p['page_width_mm']-m+.00001 or py>p['page_height_mm']-m+.00001 for px,py in points):
        raise ValidationError('El perfil desplaza contenido fuera del margen imprimible; calibra antes de emitir.')
    return points


def escaped(value):
    return ''.join('\\'+chr(b) if chr(b) in '()\\' else f'\\{b:03o}' if b<32 or b>126 else chr(b) for b in value.encode('cp1252'))


def n(value):
    if abs(value)<.0000001:value=0
    return f'{value:.6f}'.rstrip('0').rstrip('.') or '0'


def sample():
    return dict(fecha='01/01/2026',numero_factura='EJEMPLO',numero_control='EJEMPLO',
        cliente='Representante de ejemplo',documento_cliente='Documento del representante',
        direccion='Dirección de ejemplo',concepto='Mensualidad enero 2026 – Grado de ejemplo',
        forma_pago='Transferencia',referencia='EJEMPLO',tasa='BCV: EJEMPLO',
        exento='USD 100,00',base='USD 0,00',iva='USD 0,00',igtf='USD 0,00',total='USD 100,00',
        observaciones='PRUEBA SIN VALIDEZ',usuario='Operador de ejemplo',recibo='EJEMPLO',
        moneda='USD',mes='enero',año='2026',grado='Grado de ejemplo')


def render(layout,data,items,printer=None,*,calibration=False,include_background=False):
    """One exact-size page. Real emission has no path that embeds the scan."""
    layout=validate(layout);pr=profile(printer);p=layout['paper']
    if not isinstance(data,dict) or not VARIABLES<=data.keys():raise ValidationError('Faltan variables de la factura.')
    values={k:text(data[k],3000,k) for k in VARIABLES}
    if not isinstance(items,list) or len(items)>100:raise ValidationError('Detalle inválido.')
    commands=[];placements=[]
    scale=pr['scale'];rh=p['width_mm'] if p['rotation']==90 else p['height_mm'];rw=p['height_mm'] if p['rotation']==90 else p['width_mm']
    ox=(p['page_width_mm']-rw)/2 if p['placement']!='full' else 0
    top=0 if p['placement'] in ('full','top') else p['page_height_mm']/2
    base_y=p['page_height_mm']-top-rh*scale-pr['y_tenths']/10
    commands.append(f"q {n(scale)} 0 0 {n(scale)} {n((ox+pr['x_tenths']/10)*MM)} {n(base_y*MM)} cm")
    if p['rotation']==90:commands.append(f"0 -1 1 0 0 {n(p['width_mm']*MM)} cm")
    # Clockwise rotation in PDF coordinates matches point() in top-left mm.
    image=None
    if calibration and include_background and layout['background']:
        from .branding import pdf_logo
        image=pdf_logo(layout['background'])
        commands.append(f"q {n(p['width_mm']*MM)} 0 0 {n(p['height_mm']*MM)} 0 0 cm /Scan Do Q")
    if calibration:
        commands.append('0.75 G 0.2 w')
        for x in range(10,int(p['width_mm']),10):commands.append(f"{n(x*MM)} 0 m {n(x*MM)} {n(p['height_mm']*MM)} l S")
        for y in range(10,int(p['height_mm']),10):commands.append(f"0 {n(y*MM)} m {n(p['width_mm']*MM)} {n(y*MM)} l S")
        for x,y in ((7,7),(p['width_mm']-7,7),(7,p['height_mm']-7),(p['width_mm']-7,p['height_mm']-7)):
            commands.append(f"0 G 0.6 w {n((x-2)*MM)} {n(y*MM)} m {n((x+2)*MM)} {n(y*MM)} l S {n(x*MM)} {n((y-2)*MM)} m {n(x*MM)} {n((y+2)*MM)} l S")
        commands.append(f"BT /F1 6 Tf 1 0 0 1 {n(10*MM)} {n((p['height_mm']-7)*MM)} Tm ({escaped('PRUEBA · SIN VALIDEZ · 100 % · NO CONSUME NÚMEROS')}) Tj ET")
        for x in range(20,int(p['width_mm'])-5,10):commands.append(f"BT /F1 5 Tf 1 0 0 1 {n(x*MM)} {n((p['height_mm']-10)*MM)} Tm ({x} mm) Tj ET")
    def draw(f,value):
        if not f['visible']:return
        page_box(p,pr,f['x_mm'],f['y_mm'],f['width_mm'],f['height_mm'])
        rows,size=fit(value,f);font=1+(4 if f['font']=='mono' else 0)+(1 if f['bold'] else 0)+(2 if f['italic'] else 0)
        padding=size*(.25 if f['italic'] else .2);available=f['width_mm']*MM-2*padding
        for pos,row in enumerate(rows):
            offset=0 if f['align']=='left' else (available-width(row,size,f['font'],f['bold']))/(2 if f['align']=='center' else 1)
            x=f['x_mm']*MM+padding+offset;y=(p['height_mm']-f['y_mm'])*MM-size*1.08-pos*size*f['leading']
            commands.append(f'BT 0 g /F{font} {n(size)} Tf 1 0 0 1 {n(x)} {n(y)} Tm ({escaped(row)}) Tj ET')
        placements.append(dict(id=f['id'],corners_mm=page_box(p,pr,f['x_mm'],f['y_mm'],f['width_mm'],f['height_mm']),size_pt=size,lines=len(rows)))
    for f in layout['fields']:
        value=values[f['source']] if f['kind']=='system' else f['text'].format_map(values)
        draw(f,value)
    d=layout['details']
    if d['visible']:
        if len(items)>d['max_lines']:raise ValidationError('Hay más conceptos que líneas del formulario; no se imprimió cortado.')
        for index,item in enumerate(items):
            if not isinstance(item,dict) or not DETAIL_KEYS<=item.keys():raise ValidationError('Falta una columna de detalle.')
            for col in d['columns']:
                f=field('detalle-'+str(index)+'-'+col['key'],'concepto',col['x_mm'],d['y_mm']+index*d['line_height_mm'],col['width_mm'],d['line_height_mm'],font=d['font'],size_pt=d['size_pt'],align=col['align'],max_chars=2000)
                draw(f,text(item[col['key']],2000,'detalle'))
    commands.append('Q')
    pdf=assemble(p['page_width_mm']*MM,p['page_height_mm']*MM,commands,image)
    return dict(pdf=pdf,sha256=hashlib.sha256(pdf).hexdigest(),width_pt=p['page_width_mm']*MM,height_pt=p['page_height_mm']*MM,placements=placements)


def assemble(w,h,commands,image=None):
    faces=('Helvetica','Helvetica-Bold','Helvetica-Oblique','Helvetica-BoldOblique','Courier','Courier-Bold','Courier-Oblique','Courier-BoldOblique')
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Count 1 /Kids [11 0 R] >>']
    objects += [('<< /Type /Font /Subtype /Type1 /BaseFont /'+face+' /Encoding /WinAnsiEncoding >>').encode() for face in faces]
    resources=' /Font << '+' '.join(f'/F{i} {i+2} 0 R' for i in range(1,9))+' >>'
    if image:resources+=' /XObject << /Scan 13 0 R >>'
    objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {n(w)} {n(h)}] /Resources <<{resources} >> /Contents 12 0 R >>'.encode())
    stream='\n'.join(commands).encode('ascii')
    objects.append(f'<< /Length {len(stream)} >>\nstream\n'.encode()+stream+b'\nendstream')
    if image:
        iw,ih,encoded=image
        objects.append((f'<< /Type /XObject /Subtype /Image /Width {iw} /Height {ih} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /DecodeParms << /Predictor 15 /Colors 3 /BitsPerComponent 8 /Columns {iw} >> /Length {len(encoded)} >>\nstream\n').encode()+encoded+b'\nendstream')
    output=bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n');offsets=[0]
    for i,obj in enumerate(objects,1):offsets.append(len(output));output.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
    start=len(output);output.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:output.extend(f'{offset:010d} 00000 n \n'.encode())
    output.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode());return bytes(output)
