"""Read the real PyInstaller archive and bundled files; never import app modules."""
import argparse
import hashlib
import json
from pathlib import Path


def inventory(directory):
    from PyInstaller.archive.readers import CArchiveReader
    directory = Path(directory)
    executable = directory / 'Aula.exe'
    archive = CArchiveReader(str(executable))
    embedded = next(name for name in archive.toc if name.startswith('PYZ'))
    pyz = archive.open_embedded_archive(embedded)
    modules = sorted(pyz.toc)
    files = [{'path': p.relative_to(directory).as_posix(), 'bytes': p.stat().st_size}
             for p in sorted(directory.rglob('*')) if p.is_file()]
    return {'executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
            'files': files, 'total_bytes': sum(f['bytes'] for f in files),
            'pyz_modules': modules}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = inventory(args.directory)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('B2 INVENTARIO PYZ ' + json.dumps(report['pyz_modules']))
    print('B2 INVENTARIO ARCHIVOS ' + json.dumps(report['files']))
    print('B2 TAMANO ' + str(report['total_bytes']))


if __name__ == '__main__':
    main()
