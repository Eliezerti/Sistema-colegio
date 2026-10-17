"""HTTP benchmark, 800 fictional pupils x 12 months; never accepts a data directory."""
import argparse,csv,hashlib,http.client,json,platform,statistics,sys,tempfile,threading,time
from contextlib import closing
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from colegio.db import initialize,connect,hash_password,local_today
from colegio.server import SchoolServer


def seed(path,months=12):
    initialize(path);today=local_today();school_year=today.year-(today.month<9)
    with closing(connect(path)) as db,db:
        db.execute('INSERT INTO users(id,username,name,password,role) VALUES(1,?,?,?,?)',('admin','Medición ficticia',hash_password('FICTICIO-medicion-segura'),'admin'))
        db.execute("UPDATE settings SET value=? WHERE key='school_year'",(str(school_year),))
        db.execute("INSERT INTO school_accounts(id,name,bank,currency,kind,last4) VALUES(1,'Banco ficticio USD','Ficticio','USD','bank','0000')")
        for grade in range(1,9):db.execute('INSERT INTO grades VALUES(?,?,100)',(grade,'Grado ficticio '+str(grade)))
        iid=db.execute('INSERT INTO statement_imports(account_id,file_sha256,filename,profile_json,rows_count,imported_by,imported_at) VALUES(1,?,?,?,?,1,?)',(hashlib.sha256(b'fixture de rendimiento, no extracto real').hexdigest(),'FICTICIO-RENDIMIENTO.csv','{}',800*months,today.isoformat())).lastrowid
        for sid in range(1,801):
            db.execute('INSERT INTO guardians(id,name,document) VALUES(?,?,?)',(sid,'Representante ficticio '+str(sid),'FICTICIO-'+str(sid)))
            db.execute('''INSERT INTO students(id,name,document,birth_date,guardian_id,grade_id,school_year,monthly_fee,discount,status,enrollment_start,enrollment_end,student_code,billing_start)
                VALUES(?,?,?,'',?,?,?,10000,0,'active',?,?,?,?)''',(sid,'Alumno ficticio '+str(sid),'INTERNO-NO-CEDULA-'+str(sid),sid,(sid-1)//100+1,school_year,f'{school_year}-09-01',f'{school_year+1}-08-31',f'AL-{sid:06d}',today.strftime('%Y-%m')))
            for ago in range(months-1,-1,-1):
                serial=today.year*12+today.month-1-ago;y,m=divmod(serial,12);period=f'{y}-{m+1:02d}';on=min(date(y,m+1,10),today).isoformat()
                charge=db.execute("INSERT INTO charges(student_id,period,concept,amount,due_date) VALUES(?,?,'Mensualidad',10000,?)",(sid,period,f'{period}-10')).lastrowid
                ref=f'FICTICIO-{sid}-{period}'
                pid=db.execute('''INSERT INTO payments(student_id,amount,paid_on,method,reference,created_by,created_at,request_key,currency,received_amount,exchange_rate,receipt_snapshot)
                    VALUES(?,10000,?,'Transferencia',?,1,?,?,'USD',10000,'1','{}')''',(sid,on,ref,on+'T12:00:00+00:00',ref)).lastrowid
                db.execute('INSERT INTO allocations VALUES(?,?,10000)',(pid,charge));db.execute("INSERT INTO payment_accounts VALUES(?,1,'100')",(pid,))
                db.execute('INSERT INTO bank_movements(import_id,account_id,movement_on,direction,amount,currency,reference,description,bank_id,fingerprint,source_row) VALUES(?,1,?,\'credit\',10000,\'USD\',?,\'Medición ficticia\',?,?,?)',(iid,on,ref,ref,hashlib.sha256(ref.encode()).hexdigest(),pid+1))


def measure(months=12):
    with tempfile.TemporaryDirectory(prefix='aula-medicion-ingresos-') as directory:
        path=Path(directory)/'colegio.sqlite3';seed(path,months)
        server=SchoolServer(('127.0.0.1',0),str(path));thread=threading.Thread(target=server.serve_forever);thread.start();cookie=csrf=''
        def request(route,data=None):
            nonlocal cookie
            client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=60)
            client.request('GET' if data is None else 'POST','/api/'+route,json.dumps(data) if data is not None else None,{'Cookie':cookie,'X-CSRF-Token':csrf,'Content-Type':'application/json'})
            response=client.getresponse();raw=response.read()
            if response.getheader('Set-Cookie'):cookie=response.getheader('Set-Cookie').split(';')[0]
            client.close()
            if response.status!=200:raise RuntimeError((response.status,raw[:500]))
            return raw
        try:
            request('login',dict(username='admin',password='FICTICIO-medicion-segura'));csrf=json.loads(request('session'))['user']['csrf'];clock=json.loads(request('clock-status'))
            if clock['blocked']:request('clock-confirm',dict(pending_id=clock['pending']['id'],observed_at=clock['current_time'],reviewed=True))
            request('confirm-rate',dict(rate_date=local_today().isoformat(),rate='100'))
            rows=[]
            for endpoint in ('state','bank-book','accounting-report'):
                request(endpoint);times=[]
                for _ in range(3):
                    start=time.perf_counter();raw=request(endpoint);times.append(time.perf_counter()-start)
                payload=json.loads(raw)
                if endpoint=='state':assert payload['counts']['students']==800 and payload['counts']['payments']==800*months and payload['summary']['pending']==0
                if endpoint=='accounting-report':assert len(payload['income'])==800 and payload['totals']['income_usd']==8000000
                if endpoint=='bank-book':assert len(payload['bank_pending'])==100 and all(b['proposal']['unique'] for b in payload['bank_pending'])
                rows.append(dict(os=platform.system(),students=800,months=months,charges=800*months,payments=800*months,bank_movements=800*months,endpoint=endpoint,bytes=len(raw),median_seconds=round(statistics.median(times),6),max_seconds=round(max(times),6)))
            return rows
        finally:server.shutdown();thread.join();server.server_close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--months',type=int,choices=(12,24,36),default=12);args=parser.parse_args();rows=measure(args.months)
    with open(args.output,'w',encoding='utf-8',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(rows,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
