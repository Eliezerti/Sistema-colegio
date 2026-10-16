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
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    report = inventory(args.directory)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('B2 INVENTARIO PYZ ' + json.dumps(report['pyz_modules']))
    print('B2 INVENTARIO ARCHIVOS ' + json.dumps(report['files']))
    print('B2 TAMANO ' + str(report['total_bytes']))
    if args.verify:
        from bundle_rules import blocked_module, keep_data
        forbidden = [f['path'] for f in report['files'] if Path(f['path']).suffix.lower() in ('.sqlite3','.sqlite','.db','.aulabak')]
        if forbidden: raise RuntimeError('El instalador contiene bases o respaldos: '+str(forbidden))
        for name in ('colegio.salary','colegio.staff_access','colegio.reset_records'):
            if name in report['pyz_modules']: raise RuntimeError('Módulo retirado en el instalador: '+name)
        unexpected = [m for m in report['pyz_modules'] if blocked_module(m)]
        required = {'colegio.trial_payment_cleanup', 'colegio.server', 'colegio.desktop', 'sqlite3', 'tkinter', 'cryptography',
                    'webview.platforms.edgechromium', 'webview.platforms.winforms'}
        missing = required - set(report['pyz_modules'])
        unwanted = [f['path'] for f in report['files'] if not keep_data(f['path'])]
        if unexpected or missing or unwanted:
            raise RuntimeError(f'Paquete incompatible: módulos sobrantes {unexpected}; faltantes {sorted(missing)}; recursos sobrantes {unwanted}')
        print('PASS B2: inventario final sin módulos excluidos y con servidor, SQLite, cifrado, Tcl/Tk y WebView2.')


if __name__ == '__main__':
    main()
