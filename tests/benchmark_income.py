"""HTTP benchmark, 800 fictional pupils x 12 months; never accepts a data directory."""
import argparse,base64,csv,hashlib,http.client,json,platform,statistics,sys,tempfile,threading,time
from contextlib import closing
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from colegio.db import initialize,connect,hash_password,local_today
from colegio.server import SchoolServer


def seed_invoices(db):
    """Synthetic historical rows only in this script's temporary database, never issuance."""
    from colegio import invoice_layout as layout,invoices
    template=layout.example_template();template['calibrated']=True
    encoded=invoices.encoded;stamp=invoices.now()
    cfg=dict(invoices.defaults(),enabled=True,reviewed=True)
    db.execute('INSERT INTO invoice_preferences VALUES(1,?,1,?)',(encoded(cfg),stamp))
    issuer=dict(name='Colegio FICTICIO',rif='J-FICTICIO',address='Dirección ficticia',printer_name='Imprenta FICTICIA',printer_rif='',authorization='NO VERIFICADO',printed_on='',notes='Solo medición')
    db.execute("INSERT INTO invoice_batches(id,name,invoice_from,invoice_to,control_from,control_to,active,data_json,saved_by,saved_at) VALUES(1,'FICTICIO medición','000001','999999','000001','999999',1,?,1,?)",(encoded(issuer),stamp))
    db.execute('INSERT INTO invoice_templates(id,name,saved_by,saved_at) VALUES(1,?,1,?)',(template['name'],stamp))
    db.execute('INSERT INTO invoice_template_versions(id,template_id,revision,layout_json,layout_hash,saved_by,saved_at) VALUES(1,1,1,?,?,1,?)',(encoded(template),layout.digest(template),stamp))
    db.execute('UPDATE invoice_templates SET current_version_id=1 WHERE id=1')
    profile=layout.profile()
    for p in db.execute('SELECT id,paid_on,reference FROM payments ORDER BY id').fetchall():
        n=str(p['id']).zfill(6);nums=dict(invoice_number=n,control_number=n,invoice_key=str(p['id']),control_key=str(p['id']))
        source=invoices.source(db,p['id']);source['client']['address']='Dirección ficticia'
        source['issued_on']=p['paid_on'];snapshot=invoices.content(db,source)
        snapshot.update(payment=dict(method='Transferencia',reference=p['reference']),issuer=issuer,numbers=nums,operator='Medición ficticia',numbering_review={})
        fields,items=invoices.variables_for(snapshot,'Medición ficticia',nums)
        pdf=layout.render(template,fields,items,profile)
        db.execute("""INSERT INTO invoices(payment_id,batch_id,template_version_id,issued_on,state,invoice_number,control_number,invoice_key,control_key,profile_json,snapshot_json,pdf_base64,pdf_sha256,created_by,created_at,issued_by,issued_at)
            VALUES(?,1,1,?,'issued',?,?,?,?,?,?,?,?,1,?,1,?)""",(p['id'],p['paid_on'],n,n,str(p['id']),str(p['id']),encoded(profile),encoded(snapshot),base64.b64encode(pdf['pdf']).decode(),pdf['sha256'],stamp,stamp))


def seed(path,months=12,with_invoices=False):
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
        if with_invoices:seed_invoices(db)


def measure(months=12,with_invoices=False):
    with tempfile.TemporaryDirectory(prefix='aula-medicion-ingresos-') as directory:
        path=Path(directory)/'colegio.sqlite3';seed(path,months,with_invoices)
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
            for endpoint in ('state','bank-book','accounting-report',*(['invoice-book'] if with_invoices else [])):
                request(endpoint);times=[]
                for _ in range(3):
                    start=time.perf_counter();raw=request(endpoint);times.append(time.perf_counter()-start)
                payload=json.loads(raw)
                if endpoint=='state':assert payload['counts']['students']==800 and payload['counts']['payments']==800*months and payload['summary']['pending']==0
                if endpoint=='accounting-report':assert len(payload['income'])==800 and payload['totals']['income_usd']==8000000
                if endpoint=='bank-book':assert len(payload['bank_pending'])==100 and all(b['proposal']['unique'] for b in payload['bank_pending'])
                if endpoint=='invoice-book':assert len(payload['sales'])==100
                rows.append(dict(os=platform.system(),students=800,months=months,charges=800*months,payments=800*months,bank_movements=800*months,invoices=800*months if with_invoices else 0,endpoint=endpoint,bytes=len(raw),median_seconds=round(statistics.median(times),6),max_seconds=round(max(times),6)))
            return rows
        finally:server.shutdown();thread.join();server.server_close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--months',type=int,choices=(12,24,36),default=12);parser.add_argument('--with-invoices',action='store_true');args=parser.parse_args();rows=measure(args.months,args.with_invoices)
    with open(args.output,'w',encoding='utf-8',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(rows,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
