"""Bundled, licensed PDF fonts. Runtime uses only Python's standard library."""
import json
import zlib
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=2)
def font_data(filename):
    directory = Path(__file__).resolve().parent/'fonts'
    metadata = json.loads((directory/'metrics.json').read_text())[filename]
    raw = (directory/filename).read_bytes()
    return metadata, len(raw), zlib.compress(raw)


def embed_fonts(objects):
    """Replace the two existing font slots, preserving the page resource IDs."""
    for slot, filename in ((2,'LiberationSans-Regular.ttf'),(3,'LiberationSans-Bold.ttf')):
        metadata, raw_length, stream = font_data(filename)
        stream_id = len(objects)+1
        objects.append(f'<< /Length {len(stream)} /Length1 {raw_length} /Filter /FlateDecode >>\nstream\n'.encode()+stream+b'\nendstream')
        descriptor_id = len(objects)+1
        objects.append((f'<< /Type /FontDescriptor /FontName /{metadata["name"]} /Flags 32 '
            f'/FontBBox [{" ".join(map(str,metadata["bbox"]))}] /ItalicAngle 0 '
            f'/Ascent {metadata["ascent"]} /Descent {metadata["descent"]} '
            f'/CapHeight {metadata["cap_height"]} /StemV {metadata["stem_v"]} '
            f'/FontFile2 {stream_id} 0 R >>').encode())
        objects[slot] = (f'<< /Type /Font /Subtype /TrueType /BaseFont /{metadata["name"]} '
            f'/Encoding /WinAnsiEncoding /FirstChar 32 /LastChar 255 '
            f'/Widths [{" ".join(map(str,metadata["widths"]))}] /FontDescriptor {descriptor_id} 0 R >>').encode()


def text_width(value, size, bold=False):
    filename = 'LiberationSans-Bold.ttf' if bold else 'LiberationSans-Regular.ttf'
    widths = font_data(filename)[0]['widths']
    return sum(widths[code-32] if code>=32 else 0 for code in str(value).encode('cp1252',errors='replace'))*size/1000
