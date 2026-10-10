"""Reviewed bulk year transitions and payment plans without duplicating debt."""
import hashlib
import json
from datetime import date, datetime, timezone

from .db import ValidationError, audit, charges, integer, local_today, money, required, valid_date, synchronize_monthly_charges
from .documents import store


def roster_for_year(db,year):
    year=integer(year,2000,2099)
    students=[dict(s) for s in db.execute('''SELECT s.*,gr.name AS grade_name,g.name AS guardian_name
        FROM students s JOIN grades gr ON gr.id=s.grade_id JOIN guardians g ON g.id=s.guardian_id
        WHERE school_year=? AND s.archived=0 ORDER BY gr.name,s.name''',(year,))]
    return {'source_year':year,'students':students,'preview_hash':hashlib.sha256(json.dumps(students,sort_keys=True).encode()).hexdigest()}


def transition_year(db,data,user,save_record):
    source=integer(data.get('source_year'),2000,2099)
    target=integer(data.get('target_year'),2001,2100)
    if target!=source+1: raise ValidationError('El año de destino debe ser el siguiente al de origen.')
    cohort=roster_for_year(db,source)
    if data.get('roster_hash')!=cohort['preview_hash']:
        raise ValidationError('La matrícula cambió. Vuelve a cargar los alumnos antes de cerrar el año.')
    school=dict(db.execute('SELECT key,value FROM settings'))
    start=valid_date(data.get('enrollment_start'));end=valid_date(data.get('enrollment_end'))
    academic_start=date(target,int(school['start_month']),1).isoformat()
    academic_end=date(target+1,int(school['start_month']),1).isoformat()
    if not academic_start<=start<=end<academic_end:
        raise ValidationError('Las fechas nuevas deben pertenecer al año escolar de destino.')
    closed_on=valid_date(data.get('closed_on'))
    if closed_on>local_today().isoformat() or not date(source,int(school['start_month']),1).isoformat()<=closed_on<academic_start:
        raise ValidationError('La fecha de cierre debe pertenecer al año de origen y no puede ser futura. Elige la fecha real en que concluyó el curso.')
    lines=data.get('lines')
    if not isinstance(lines,list) or not lines or len(lines)>5000: raise ValidationError('Revisa la lista de alumnos.')
    source_map={s['id']:s for s in cohort['students']};seen=set();plans=[];errors=[]
    counts={g['id']:db.execute("SELECT COUNT(*) FROM students WHERE grade_id=? AND school_year=? AND status='active'",(g['id'],target)).fetchone()[0] for g in db.execute('SELECT * FROM grades')}
    grades={g['id']:dict(g) for g in db.execute('SELECT * FROM grades')}
    for row in lines:
        sid=integer(row.get('student_id'),1,2147483647)
        if sid not in source_map or sid in seen: raise ValidationError('Lista con alumnos repetidos o ajenos al año de origen.')
        seen.add(sid);student=source_map[sid];action=row.get('action')
        if action not in ('promote','repeat','withdraw','skip'): raise ValidationError('Selecciona avanzar, repetir, retirar o dejar sin cambios.')
        if student['status']=='inactive' and action in ('promote','repeat'):
            errors.append(student['name']+': está retirado/inactivo. Reactívalo individualmente antes de matricularlo de nuevo.')
        if action in ('promote','repeat') and student['enrollment_start']>closed_on:
            errors.append(student['name']+': su matrícula empezó después de la fecha de cierre.')
        grade_id=student['grade_id'] if action=='repeat' else integer(row.get('grade_id',student['grade_id']),1,2147483647)
        if grade_id not in grades: raise ValidationError('Selecciona un grado de destino existente.')
        if action=='promote' and grade_id==student['grade_id']:
            errors.append(student['name']+': para conservar el mismo grado selecciona Repite.')
        if action in ('promote','repeat'): counts[grade_id]+=1
        fee=money(row.get('monthly_fee',str(student['monthly_fee']/100)))
        plans.append({'student_id':sid,'student_name':student['name'],'action':action,
            'source_grade':student['grade_name'],'target_grade':grades[grade_id]['name'],
            'grade_id':grade_id,'monthly_fee':fee,'source':student})
    # Transitions are all-or-nothing, and capacity is assessed for the full destination cohort.
    for gid,count in counts.items():
        if count>grades[gid]['capacity']: errors.append(f"{grades[gid]['name']}: {count} alumnos para {grades[gid]['capacity']} cupos.")
    result={'source_year':source,'target_year':target,'lines':plans,'errors':errors,
        'enrollment_start':start,'enrollment_end':end,'closed_on':closed_on,'school':school}
    digest=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest();result['hash']=digest
    if data.get('preview') is True: return result
    if errors: raise ValidationError(errors[0])
    if data.get('confirmed_hash')!=digest: raise ValidationError('Revisa la vista previa de este pase de año antes de confirmar.')
    for plan in plans:
        s=plan['source']
        if plan['action']=='skip': continue
        update={k:s[k] for k in ('id','name','document','birth_date','guardian_id','grade_id','school_year','discount','status','notes','enrollment_start','enrollment_end','billing_start')}
        update['monthly_fee']=f"{s['monthly_fee']/100:.2f}"
        if plan['action']=='withdraw': update['status']='inactive'
        else:
            update.update(grade_id=plan['grade_id'],school_year=target,enrollment_start=start,enrollment_end=end,
                billing_start=start[:7],monthly_fee=f"{plan['monthly_fee']/100:.2f}",status='active')
        save_record(db,'students',update,user)
    synchronize_monthly_charges(db)
    school_year=db.execute("SELECT value FROM settings WHERE key='school_year'").fetchone()[0]
    if int(school_year)==source: db.execute("UPDATE settings SET value=? WHERE key='school_year'",(str(target),))
    result['id']=store(db,'year_transitions',result,user['id'])
    return {'id':result['id'],'changed':sum(p['action']!='skip' for p in plans)}


def plan_status(db,r):
    doc=dict(json.loads(r['snapshot_json']),id=r['id'],cancelled=r['cancelled'],cancel_reason=r['cancel_reason'])
    covered=0
    for original in doc['charges']:
        now=db.execute('''SELECT COALESCE(SUM(a.amount),0) FROM allocations a JOIN payments p ON p.id=a.payment_id
            WHERE a.charge_id=? AND p.voided=0''',(original['id'],)).fetchone()[0]
        covered+=max(0,now-original['paid'])
    remaining=min(covered,doc['total']); installments=[]
    for item in doc['installments']:
        paid=min(remaining,item['amount']);remaining-=paid
        installments.append(dict(item,paid=paid,balance=item['amount']-paid,
            overdue=item['due_date']<local_today().isoformat() and paid<item['amount']))
    doc.update(installments=installments,paid=min(covered,doc['total']),balance=max(0,doc['total']-covered))
    return doc


def create_plan(db,data,user):
    sid=integer(data.get('student_id'),1,2147483647)
    student=db.execute('''SELECT s.*,g.name AS guardian_name,g.document AS guardian_document,gr.name AS grade_name
        FROM students s JOIN guardians g ON g.id=s.guardian_id JOIN grades gr ON gr.id=s.grade_id WHERE s.id=?''',(sid,)).fetchone()
    if not student: raise ValidationError('Alumno inexistente.')
    for r in db.execute('SELECT * FROM payment_plans WHERE student_id=? AND cancelled=0',(sid,)):
        if plan_status(db,r)['balance']: raise ValidationError('Este alumno ya tiene un convenio pendiente. Cancélalo con motivo antes de reemplazarlo.')
    pending=[c for c in charges(db,sid) if c['overdue']]
    total=sum(c['balance'] for c in pending)
    if not total: raise ValidationError('Este alumno no tiene deuda vencida para convenir.')
    if data.get('expected_total')!=total: raise ValidationError('La deuda cambió. Abre de nuevo el convenio y revisa las cuotas.')
    source=data.get('installments')
    if not isinstance(source,list) or not 1<=len(source)<=60: raise ValidationError('Define entre 1 y 60 cuotas.')
    installments=[];prior=''
    for i,item in enumerate(source,1):
        on=valid_date(item.get('due_date'));value=money(item.get('amount'))
        if on<local_today().isoformat() or on<prior or not value:
            raise ValidationError('Las cuotas deben tener importe positivo y fechas desde hoy, en orden.')
        prior=on;installments.append({'number':i,'due_date':on,'amount':value})
    if sum(i['amount'] for i in installments)!=total:
        raise ValidationError('La suma de las cuotas debe coincidir exactamente con la deuda vencida.')
    doc={'student':dict(student),'charges':pending,'installments':installments,'total':total,
        'notes':str(data.get('notes',''))[:2000],'school':dict(db.execute('SELECT key,value FROM settings'))}
    target=store(db,'payment_plans',doc,user['id'],sid)
    return {'id':target}


def cancel_plan(db,data,user):
    target=integer(data.get('id'),1,2147483647);reason=required(data,'reason',500)
    if not db.execute('UPDATE payment_plans SET cancelled=1,cancel_reason=? WHERE id=? AND cancelled=0',(reason,target)).rowcount:
        raise ValidationError('Convenio inexistente o ya cancelado.')
    audit(db,user['id'],'payment-plan-cancel',{'id':target,'reason':reason});return {'saved':True}
