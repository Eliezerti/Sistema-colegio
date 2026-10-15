"""Reproducible HTTP measurements, fictional data only; no real data directory."""
import argparse
from contextlib import closing
import csv
from datetime import date
import http.client
import json
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import threading
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from colegio.db import initialize,connect,hash_password,local_today
from colegio.server import SchoolServer


def seed(path,count,years):
    initialize(path)
    today=local_today();year=today.year-(today.month<9)
    with closing(connect(path)) as db,db:
        db.execute('INSERT INTO users VALUES(1,?,?,?,?)',('admin','Prueba ficticia',hash_password('FICTICIO-medicion-segura'),'admin'))
        db.execute("UPDATE settings SET value=? WHERE key='school_year'",(str(year),))
        db.execute('INSERT INTO grades VALUES(1,?,?)',('Grado ficticio',count))
        for sid in range(1,count+1):
            db.execute('INSERT INTO guardians(id,name,document,phone) VALUES(?,?,?,?)',(sid,f'Representante ficticio {sid}',f'F-{sid}','04000000000'))
            db.execute('''INSERT INTO students(id,name,document,birth_date,guardian_id,grade_id,school_year,
                monthly_fee,discount,status,enrollment_start,enrollment_end,student_code,billing_start)
                VALUES(?,?,?,?,?,1,?,10000,0,'active',?,?,?,?)''',
                (sid,f'Alumno ficticio {sid}',f'A-{sid}','2015-01-01',sid,year,
                f'{year}-09-01',f'{year+1}-08-31',f'AL-{sid:06d}',today.strftime('%Y-%m')))
            for annual in range(year-years+1,year+1):
                for month in range(10):
                    y,m=annual+(month+8)//12,(month+8)%12+1
                    on=f'{y}-{m:02d}-10'
                    charge=db.execute("INSERT INTO charges(student_id,period,concept,amount,due_date) VALUES(?,?,'Mensualidad',10000,?)",(sid,on[:7],on)).lastrowid
                    if month<3:
                        payment=db.execute('''INSERT INTO payments(student_id,amount,paid_on,method,created_by,created_at,
                            request_key,currency,received_amount,exchange_rate,receipt_snapshot)
                            VALUES(?,10000,?,'Efectivo',1,?,?,'USD',10000,'1','{}')''',
                            (sid,min(on,today.isoformat()),min(on,today.isoformat())+'T00:00:00+00:00',f'{sid}-{annual}-{month}')).lastrowid
                        db.execute('INSERT INTO allocations VALUES(?,?,10000)',(payment,charge))


def measure(count,years):
    with tempfile.TemporaryDirectory(prefix='aula-medicion-') as temporary:
        path=Path(temporary)/'colegio.sqlite3';seed(path,count,years)
        server=SchoolServer(('127.0.0.1',0),str(path));thread=threading.Thread(target=server.serve_forever);thread.start()
        cookie=csrf='' 
        def request(route,body=None):
            nonlocal cookie
            client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=30)
            client.request('POST' if body is not None else 'GET','/api/'+route,
                json.dumps(body) if body is not None else None,{'Content-Type':'application/json','Cookie':cookie,'X-CSRF-Token':csrf})
            response=client.getresponse();data=response.read()
            if response.getheader('Set-Cookie'):cookie=response.getheader('Set-Cookie').split(';')[0]
            if response.status!=200:raise RuntimeError((response.status,data))
            client.close();return data
        try:
            request('login',dict(username='admin',password='FICTICIO-medicion-segura'))
            csrf=json.loads(request('session'))['user']['csrf']
            clock=json.loads(request('clock-status'))
            if clock['blocked']:
                request('clock-confirm',dict(pending_id=clock['pending']['id'],observed_at=clock['current_time'],reviewed=True))
            request('confirm-rate',dict(rate_date=local_today().isoformat(),rate='100'))
            results=[]
            for view,route in (('completo','state?history=1'),('principal','state')):
                request(route);elapsed=[]
                for _ in range(3):
                    start=time.perf_counter();raw=request(route);elapsed.append(time.perf_counter()-start)
                results.append(dict(os=platform.system(),students=count,years=years,charges=count*10*years,
                    payments=count*3*years,view=view,bytes=len(raw),median_seconds=round(statistics.median(elapsed),4),
                    max_seconds=round(max(elapsed),4)))
            return results
        finally:
            server.shutdown();thread.join();server.server_close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    rows=[]
    for count in (500,800):
        for years in (1,2,3):rows+=measure(count,years)
    with open(args.output,'w',newline='',encoding='utf-8') as output:
        writer=csv.DictWriter(output,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(rows,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
