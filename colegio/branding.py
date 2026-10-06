"""School identity supplied by its administrator and bundled PNG for documents."""
import struct
import zlib
from functools import lru_cache
from pathlib import Path

SCHEMA_VERSION = 6
LOGO_FILE = 'logo-colegio-v1.png'
SCHOOL_PROFILE = {
    'legal_name': 'ALEJANDRO VON HUMBOLDT, C.A.',
    'rif': 'J-50835934-8',
    'fiscal_address': ('Calle 48 entre carreras 16 y 17, local Nro. 16-46, sector Centro, '
                       'Barquisimeto, Lara. Zona postal 3001.'),
    'logo': LOGO_FILE,
}


@lru_cache(maxsize=4)
def pdf_logo(filename):
    """Embed our RGB PNG's original IDAT stream with PDF's PNG predictor.

    Only known bundled assets are allowed. No image conversion or third-party
    runtime packages are needed; the full-resolution artwork stays unchanged.
    """
    if filename != LOGO_FILE:
        return None
    raw = (Path(__file__).resolve().parent.parent / 'static' / filename).read_bytes()
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
            if (bits, color, compression, filtering, interlace) != (8, 2, 0, 0, 0):
                raise ValueError('El logo requiere un PNG RGB de 8 bits sin entrelazado.')
            dimensions = w, h
        elif kind == b'IDAT':
            compressed.append(payload)
        elif kind == b'IEND':
            break
        offset += 12+length
    if not dimensions or not compressed:
        raise ValueError('Faltan los datos del logo PNG.')
    w, h = dimensions
    return w, h, b''.join(compressed)
