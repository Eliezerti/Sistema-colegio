"""Generate fictional databases with the actual source of published Git tags (Linux)."""
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

TAGS=('desktop-1.0.4','desktop-1.0.6','desktop-1.0.7','desktop-1.0.13')
SCRIPT="""
from contextlib import closing
from pathlib import Path
import sys
from colegio.db import initialize,connect,record_payment,hash_password
from colegio.storage import consistent_backup
p=Path('fictional.sqlite3')
initialize(p)
with closing(connect(p)) as db,db:
 db.execute("INSERT INTO users(id,username,name,password,role) VALUES(1,'fixture','Administrador ficticio',?,'admin')",(hash_password('Clave-ficticia-fixture'),))
 db.execute("INSERT INTO guardians(id,name,document) VALUES(1,'Representante ficticio','V-FICTICIO')")
 db.execute("INSERT INTO grades(id,name,capacity) VALUES(1,'Grado ficticio',30)")
 db.execute(\"\"\"INSERT INTO students(id,name,document,birth_date,guardian_id,grade_id,school_year,monthly_fee,discount,status,enrollment_start,enrollment_end)
               VALUES(1,'Alumno ficticio','DOC-FICTICIO','2015-01-01',1,1,2025,10000,0,'inactive','2025-09-01','2026-08-31')\"\"\")
 db.execute("INSERT INTO charges(student_id,period,concept,amount,due_date) VALUES(1,'2025-09','Mensualidad',10000,'2025-09-10')")
 record_payment(db,{'student_id':1,'amount':'50','currency':'USD','paid_on':'2025-09-20','method':'Transferencia','reference':'FICTICIA','request_key':'fixture-published-tag'},1)
consistent_backup(p,sys.argv[1])
"""


def main():
    root=Path(__file__).resolve().parent.parent
    output=root/'tests/fixtures/restore';output.mkdir(parents=True,exist_ok=True)
    manifests=[]
    for tag in TAGS:
        commit=subprocess.check_output(['git','rev-parse',tag],cwd=root,text=True).strip()
        with tempfile.TemporaryDirectory(prefix='aula-historical-source-') as temporary:
            temporary=Path(temporary)
            archive=temporary/'source.tar'
            with archive.open('wb') as out:subprocess.run(['git','archive',tag],cwd=root,stdout=out,check=True)
            with tarfile.open(archive) as source:source.extractall(temporary,filter='data')
            path=output/(tag+'.sqlite3')
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(temporary))
            subprocess.run([sys.executable,'-c',SCRIPT,str(path)],cwd=temporary,env=env,check=True,timeout=30)
            import sqlite3
            from contextlib import closing
            with closing(sqlite3.connect(path)) as db:version=db.execute('PRAGMA user_version').fetchone()[0]
            manifests.append({'tag':tag,'commit':commit,'schema':version,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                              'fictional':True,'payments':1,'balance_usd':5000,'filename':path.name})
    (output/'manifest.json').write_text(json.dumps(manifests,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifests,indent=2))


if __name__=='__main__':main()
