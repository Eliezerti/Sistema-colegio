"""Package the editable phone interface, without databases or configuration."""
import argparse
import hashlib
import zipfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((root / 'static').rglob('*')):
            if path.is_file() and path.suffix in ('.html', '.css', '.js', '.png', '.svg', '.webmanifest', '.ttf', '.txt', '.json'):
                archive.writestr('Aula-Movil/' + path.relative_to(root / 'static').as_posix(), path.read_bytes())
        archive.writestr('Aula-Movil/LEEME.md', (root / 'docs' / 'telefono.md').read_bytes())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():
            raise RuntimeError('El paquete móvil no superó su verificación.')
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.sha256').write_text(f'{digest}  {output.name}\n')
    print(f'Interfaz móvil: {output.name} · {output.stat().st_size} bytes · SHA256 {digest}')


if __name__ == '__main__':
    main()
