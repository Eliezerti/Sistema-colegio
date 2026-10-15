"""Read-only acceptance check used by unit tests and the installed Windows test."""
import sqlite3
from contextlib import closing
from colegio.audit_chain import portable_status

BUSINESS=('students','guardians','grades','charges','payments','allocations','expenses',
          'exchange_rates','payment_plans','collection_notes','enrollment_documents',
          'guardian_documents','year_transitions','monthly_assessments','cash_closures')
SEQUENCES=('payments','expenses','students','guardians','enrollment_documents')


def assert_empty_database(path):
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not list(db.execute('PRAGMA foreign_key_check'))
        assert db.execute('PRAGMA user_version').fetchone()[0]==12
        for table in (*BUSINESS,'users','audit','audit_links','sessions'):
            assert db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0,table
        profile=dict(db.execute('SELECT key,value FROM settings'))
        assert profile['school_name']=='Mi colegio'
        for key in ('legal_name','rif','address','phone','email','logo','fiscal_address'):
            assert profile[key]=='',key
        for table in SEQUENCES:assert profile['id_floor_'+table]=='0',table
        assert not db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('employees','positions','salary_receipts','payroll_plans')").fetchone()
        assert portable_status(db)['ok']
