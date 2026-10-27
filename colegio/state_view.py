"""Bounded dashboard payload; all monetary summaries retain the complete ledger."""
from datetime import date, timedelta


def principal(state):
    result=dict(state)
    today=date.fromisoformat(state['today'])
    due=sorted((c for c in state['charges'] if c['balance']>0 and
        state['today']<=c['due_date']<=(today+timedelta(days=6)).isoformat()),key=lambda c:(c['due_date'],c['id']))
    oldest={}
    for charge in state['charges']:
        if charge['overdue']:
            sid=charge['student_id']
            oldest[sid]=min(oldest.get(sid,charge['due_date']),charge['due_date'])
    paid=[p for p in state['payments'] if not p['voided'] and p['paid_on']==state['today']]
    result['dashboard']={'due':due[:5],'due_count':len(due),'due_total':sum(c['balance'] for c in due),
        'new_debtors':sum(on>=(today-timedelta(days=7)).isoformat() for on in oldest.values()),
        'payment_count':len(paid),'income':sum(p['amount'] for p in paid),
        'dollars':sum(p['received_amount'] for p in paid if p['currency']=='USD'),
        'bolivars':sum(p['received_amount'] for p in paid if p['currency']=='VES')}
    settlements=[p for p in state.get('cashea_cash',[]) if p['received_on']==state['today']]
    result['dashboard']['settlement_count']=len(settlements)
    result['dashboard']['income']+=sum(p['amount'] for p in settlements)
    result['dashboard']['dollars']+=sum(p['received_amount'] for p in settlements if p['currency']=='USD')
    result['dashboard']['bolivars']+=sum(p['received_amount'] for p in settlements if p['currency']=='VES')
    result['cashea_cash']=[]
    result['students']=sorted(state['students'],key=lambda s:(-s['overdue'],s['name']))[:5]
    result['payments']=[p for p in state['payments'] if not p['voided']][:5]
    # An incomplete list is never used as a financial ledger. UI explicitly loads history.
    for key in ('guardians','charges','expenses','enrollments','payment_plans','year_transitions',
                'guardian_documents','cash_closures','collections','users','audit'):
        result[key]=[]
    result['rates']=state['rates'][:1]
    result['history_loaded']=False
    result['counts']={key:len(state[key]) for key in ('students','guardians','charges','payments','expenses')}
    result['active_school_year']=state['settings']['school_year']
    return result
