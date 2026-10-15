"""Only a fictional archive and its test credentials leave the disposable key store."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.test_system import SystemTests
from tests.crypto_helpers import configure,PASSWORD
from colegio.storage import consistent_backup
from colegio.backup_export import write_encrypted


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    output=Path(args.output)
    if not (output/'disposable-b1-only.txt').is_file():raise RuntimeError('Área ficticia no autorizada.')
    f=SystemTests();f.setUp()
    try:
        f.request('payments',f.payment())
        with tempfile.TemporaryDirectory(prefix='aula-llaves-portabilidad-') as temp:
            keys=Path(temp)/'keys';recovery=configure(keys)
            plain=Path(temp)/'snapshot.sqlite3';consistent_backup(f.path,plain)
            write_encrypted(plain,output/'solo-archivo.aulabak',keys)
            metadata={'fictional':True,'password':PASSWORD,'recovery':recovery,'payments':1,
                'pending':f.request('state')['summary']['pending']}
            (output/'credenciales-ficticias.json').write_text(json.dumps(metadata),encoding='utf-8')
        print('PASS: fixture portátil creado; almacén de llaves de origen eliminado.')
    finally:f.tearDown()

if __name__=='__main__':main()
