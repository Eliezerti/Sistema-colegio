"""Build a source distribution for Windows, without databases or credentials."""
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
    files = [root / name for name in ('.gitattributes','README.md','CHANGELOG.md','INFORME-MAÑANA.md','desktop_entry.py','requirements.txt','requirements-desktop.txt','Iniciar-Aula.bat','Iniciar-Pruebas.bat','Configurar-Red.bat','Iniciar-Red.bat','Restaurar-respaldo.bat','Abrir-carpeta-de-datos.bat','Recuperar-clave-admin.bat')]
    files.extend(p for p in (root/'docs').rglob('*') if p.is_file() and p.suffix in ('.md','.html','.json','.csv'))
    # Isolated historical test fixtures only, each bound to its published source.
    import json
    for fixture_root in (root/'tests/fixtures/restore',root/'tests/fixtures/retirement',root/'tests/fixtures/income'):
        metadata=json.loads((fixture_root/'manifest.json').read_text())
        for fixture in metadata if isinstance(metadata,list) else [metadata]:
            name=fixture['filename']
            if Path(name).name!=name or not fixture.get('fictional'): raise RuntimeError('Fixture inválida.')
            path=fixture_root/name
            if hashlib.sha256(path.read_bytes()).hexdigest()!=fixture['sha256']: raise RuntimeError('Fixture histórica alterada.')
            files.append(path)
    for directory in ('colegio','static','tests','packaging'):
        files.extend(p for p in (root / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.js','.cjs','.css','.html','.svg','.png','.ttf','.json','.txt','.ico','.iss','.ps1','.spec'))
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            data = path.read_bytes()
            if path.suffix == '.bat':
                data = path.read_text(encoding='utf-8').replace('\r\n','\n').replace('\n','\r\n').encode('utf-8')
            archive.writestr('Aula/' + path.relative_to(root).as_posix(), data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():
            raise RuntimeError('El archivo ZIP no superó su verificación.')
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.sha256').write_text(f'{digest}  {output.name}\n')
    print(f'Paquete creado: {output}\n{len(files)} archivos · {output.stat().st_size} bytes\nSHA256: {digest}')


if __name__ == '__main__':
    main()
