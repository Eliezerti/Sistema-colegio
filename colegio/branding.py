"""School identity supplied by its administrator and bundled PNG for documents."""
import struct
import zlib
import base64
from functools import lru_cache
from pathlib import Path

SCHEMA_VERSION = 9
INSTITUTION_TYPE = 'Unidad Educativa Colegio'
SCHOOL_NAME = 'Unidad Educativa Colegio Alejandro Von Humboldt'
LOGO_FILE = 'logo-colegio-v1.png'
SCHOOL_PROFILE = {
    'legal_name': 'ALEJANDRO VON HUMBOLDT, C.A.',
    'rif': 'J-50835934-8',
    'fiscal_address': ('Calle 48 entre carreras 16 y 17, local Nro. 16-46, sector Centro, '
                       'Barquisimeto, Lara. Zona postal 3001.'),
    'logo': LOGO_FILE,
}


def logo_bytes(filename):
    if filename == LOGO_FILE:
        return (Path(__file__).resolve().parent.parent / 'static' / filename).read_bytes()
    if isinstance(filename,str) and filename.startswith('data:image/png;base64,') and len(filename) <= 700000:
        return base64.b64decode(filename.split(',',1)[1],validate=True)
    return None


@lru_cache(maxsize=8)
def pdf_logo(filename):
    """Embed our RGB PNG's original IDAT stream with PDF's PNG predictor.

    Only known bundled assets are allowed. No image conversion or third-party
    runtime packages are needed; the full-resolution artwork stays unchanged.
    """
    raw = logo_bytes(filename)
    if raw is None:
        return None
    if raw[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('El logo no es un PNG válido.')
    offset, compressed, dimensions = 8, [], None
    while offset + 12 <= len(raw):
        length = struct.unpack_from('>I', raw, offset)[0]
        kind = raw[offset+4:offset+8]
        payload = raw[offset+8:offset+8+length]
        if offset+12+length > len(raw):
            raise ValueError('El PNG está incompleto.')
        crc = struct.unpack_from('>I', raw, offset+8+length)[0]
        if zlib.crc32(kind+payload) & 0xffffffff != crc:
            raise ValueError('El PNG está dañado.')
        if kind == b'IHDR':
            w, h, bits, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            if bits != 8 or color not in (2,6) or (compression,filtering,interlace) != (0,0,0):
                raise ValueError('El logo requiere un PNG RGB/RGBA de 8 bits sin entrelazado.')
            if not 1 <= w <= 2048 or not 1 <= h <= 2048:
                raise ValueError('El logo no puede superar 2048 × 2048 píxeles.')
            dimensions = w, h
        elif kind == b'IDAT':
            compressed.append(payload)
        elif kind == b'IEND':
            break
        offset += 12+length
    if not dimensions or not compressed:
        raise ValueError('Faltan los datos del logo PNG.')
    w, h = dimensions
    compressed = b''.join(compressed)
    channels = 3 if color == 2 else 4
    stride = w * channels
    expected = (stride+1)*h
    decoder = zlib.decompressobj()
    pixels = decoder.decompress(compressed,expected+1)
    if len(pixels)!=expected or not decoder.eof or decoder.unused_data:
        raise ValueError('El PNG contiene datos de imagen inválidos.')
    if color == 2:
        if any(pixels[y*(stride+1)] > 4 for y in range(h)):
            raise ValueError('Filtro PNG inválido.')
        return w,h,compressed
    # Flatten transparency onto white; PDFs and old snapshots stay self-contained.
    prior = bytearray(stride); result = bytearray()
    for y in range(h):
        pos=y*(stride+1); kind=pixels[pos]; row=bytearray(pixels[pos+1:pos+1+stride])
        if kind>4: raise ValueError('Filtro PNG inválido.')
        for i in range(stride):
            a=row[i-channels] if i>=channels else 0
            b=prior[i]; c=prior[i-channels] if i>=channels else 0
            if kind==1: predictor=a
            elif kind==2: predictor=b
            elif kind==3: predictor=(a+b)//2
            elif kind==4:
                p=a+b-c; distances=(abs(p-a),abs(p-b),abs(p-c))
                predictor=(a,b,c)[distances.index(min(distances))]
            else: predictor=0
            row[i]=(row[i]+predictor)&255
        result.append(0)
        for i in range(0,stride,4):
            alpha=row[i+3]
            result.extend((v*alpha+255*(255-alpha)+127)//255 for v in row[i:i+3])
        prior=row
    return w,h,zlib.compress(bytes(result))
