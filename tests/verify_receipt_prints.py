"""Independent CI check for native WebView2 receipt PDFs (pypdf, test-only)."""
from pathlib import Path
import math
import sys
from pypdf import PdfReader


def inspect(path, size):
    reader = PdfReader(path)
    assert len(reader.pages) == 1, f'{path}: se añadieron páginas'
    page = reader.pages[0]
    assert (float(page.mediabox.width), float(page.mediabox.height)) == size, f'{path}: tamaño incorrecto'
    fragments = []

    def visit(text, cm, tm, font, font_size):
        if not text.strip():
            return
        x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
        y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
        fragments.append((text, x, size[1] - y, font_size * math.hypot(cm[0], cm[1])))

    text = page.extract_text(visitor_text=visit)
    assert 'R-000031' in text and 'TR-001' in text, f'{path}: faltan recibo o referencia'
    assert 'Firma del representante' in text, f'{path}: falta la firma'
    assert 'AL-000001' not in text and 'CE-199998887771' not in text, f'{path}: identificación escolar expuesta'
    assert all(0 <= x <= 396 and 0 <= y <= 612 for _, x, y, _ in fragments), f'{path}: contenido fuera de media carta'
    return text, fragments


def main(directory):
    directory = Path(directory)
    inspect(directory / 'comprobante-media-carta.pdf', (396, 612))
    half_text, half = inspect(directory / 'media-carta-webview2.pdf', (396, 612))
    letter_text, letter = inspect(directory / 'media-carta-en-carta-webview2.pdf', (612, 792))
    assert half_text == letter_text, 'Cambiar a carta alteró el contenido'
    assert len(half) == len(letter), 'Cambiar a carta alteró los fragmentos impresos'
    for a, b in zip(half, letter):
        assert a[0] == b[0] and all(abs(x - y) < .1 for x, y in zip(a[1:], b[1:])), 'Cambiar a carta amplió, desplazó o cambió el texto'
    print('PASS RECIBO INDEPENDIENTE: 396 x 612 puntos; una página; mismo contenido, posiciones y escala en carta; sin identificadores escolares.')


if __name__ == '__main__':
    main(sys.argv[1])
