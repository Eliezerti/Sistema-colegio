"""Independent CI check for native WebView2 receipt PDFs (pypdf, test-only)."""
from pathlib import Path
import math
import sys
from pypdf import PdfReader


def inspect(path, size, copies=1):
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
    assert text.count('R-000031') == copies and text.count('TR-001') == copies, f'{path}: faltan recibo o referencia'
    assert text.count('Firma del representante') == copies, f'{path}: faltan firmas'
    assert 'AL-000001' not in text and 'CE-199998887771' not in text, f'{path}: identificación escolar expuesta'
    assert all(0 <= x <= 396*copies and 0 <= y <= 612 for _, x, y, _ in fragments), f'{path}: contenido fuera de media carta'
    return text, fragments


def main(directory):
    directory = Path(directory)
    inspect(directory / 'comprobante-media-carta.pdf', (396, 612))
    half_text, half = inspect(directory / 'media-carta-webview2.pdf', (396, 612))
    letter_text, letter = inspect(directory / 'media-carta-en-carta-webview2.pdf', (612, 792))
    assert half_text == letter_text, 'Cambiar a carta alteró el contenido'
    assert len(half) == len(letter), 'Cambiar a carta alteró los fragmentos impresos'
    for a, b in zip(half, letter):
        assert a[0] == b[0] and all(abs(x - y) < .1 for x, y in zip(a[1:], b[1:])), f'Cambiar a carta alteró el fragmento: media carta={a!r}; carta={b!r}'
    inspect(directory / 'comprobante-dos-copias.pdf', (792, 612), copies=2)
    pair_text, pair = inspect(directory / 'dos-copias-webview2.pdf', (792, 612), copies=2)
    assert pair_text.count('ORIGINAL') == 1 and pair_text.count('COPIA') == 1
    pair = [v for v in pair if 'ORIGINAL' not in v[0] and 'COPIA' not in v[0]]
    left = [v for v in pair if v[1] < 396]
    right = [(text, x-396, y, size) for text, x, y, size in pair if x >= 396]
    assert len(left) == len(right) == len(half), 'No se imprimieron dos copias completas'
    for expected, a, b in zip(half, left, right):
        assert a[0] == b[0] == expected[0], 'La copia alteró información del comprobante'
        assert all(abs(x-y)<.1 for x,y in zip(a[1:],b[1:])), f'Las copias cambiaron posición o escala: {a!r}; {b!r}'
        assert abs(a[3]-expected[3])<.1, 'La copia cambió el tamaño del texto'
    signatures = [v for v in half if 'Firma del representante' in v[0]]
    assert signatures and all(10 <= y <= 590 for _, _, y, _ in signatures)
    print('PASS DOS COPIAS: carta horizontal 792 x 612 puntos; dos copias completas, posiciones equivalentes, firmas y escala 100 %.')
    print('PASS RECIBO INDEPENDIENTE: 396 x 612 puntos; una página; mismo contenido, posiciones y escala en carta; sin identificadores escolares.')


if __name__ == '__main__':
    main(sys.argv[1])
