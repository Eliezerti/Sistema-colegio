"""Build a bounded review ZIP from committed changes, with a full binary git diff."""
import argparse,hashlib,json,re,sqlite3,subprocess,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='324d388'
ALLOWED={'.py','.js','.cjs','.css','.html','.md','.iss','.ps1','.yml','.yaml','.json','.txt'}
FIXTURE='tests/fixtures/cashea/desktop-1.0.73-ficticio.sqlite3'
SECRETS=(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{50,}',rb'AKIA[0-9A-Z]{16}')


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    if git('status','--porcelain','--untracked-files=no').strip():raise RuntimeError('Confirma los cambios antes de empaquetar: el ZIP corresponde a un commit revisable.')
    names=git('diff','--name-only','--diff-filter=ACMR',BASE,'HEAD').decode().splitlines()
    patch=git('diff','--binary','--full-index',BASE,'HEAD')
    entries={'cambios-completos.patch':patch}
    for name in names:
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or path.suffix.lower() not in ALLOWED and name!=FIXTURE:
            raise RuntimeError('Archivo no permitido en el paquete: '+name)
        entries['archivos-modificados/'+name]=git('show','HEAD:'+name)
    if FIXTURE in names:
        meta=json.loads(entries['archivos-modificados/tests/fixtures/cashea/manifest.json'])
        raw=entries['archivos-modificados/'+FIXTURE]
        if not meta['fictional'] or hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise RuntimeError('Fixture no comprobado.')
        with sqlite3.connect(':memory:') as db:
            db.deserialize(raw)
            for table in ('students','guardians'):
                if any('FICTICIO' not in name.upper() for name, in db.execute('SELECT name FROM '+table)):
                    raise RuntimeError('El fixture contiene una persona no marcada ficticia.')
            if db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]:raise RuntimeError('El fixture tiene sesiones.')
    for name,raw in entries.items():
        if any(re.search(pattern,raw) for pattern in SECRETS):
            raise RuntimeError('Revisar posible secreto o dato personal en '+name)
    manifest=dict(base=git('rev-parse',BASE).decode().strip(),head=git('rev-parse','HEAD').decode().strip(),
        branch=git('branch','--show-current').decode().strip(),files={name:hashlib.sha256(raw).hexdigest() for name,raw in entries.items()},
        review='Solo código comprometido, documentación y fixture explícitamente ficticio. Sin bases del usuario, almacén de claves, .env ni ejecutables. Patrones de secretos comprobados; nombres del fixture marcados FICTICIO. El escaneo no sustituye revisión humana.')
    entries['MANIFIESTO.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,raw in entries.items():archive.writestr(name,raw)
    if output.stat().st_size>=20*1024*1024:raise RuntimeError('El paquete supera 20 MB.')
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():raise RuntimeError('El ZIP no pasó la verificación.')
        if set(archive.namelist())!=set(entries):raise RuntimeError('Inventario ZIP distinto del revisado.')
    print(json.dumps(dict(path=str(output.resolve()),bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),files=len(entries)),ensure_ascii=False))


if __name__=='__main__':main()
