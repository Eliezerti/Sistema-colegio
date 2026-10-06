"""Calendar-driven billing must preserve historical finance and waived months."""
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date
from pathlib import Path
from unittest.mock import patch

from colegio.db import connect, initialize, charges, generate_month, record_payment, synchronize_monthly_charges


class MonthlyAutomationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'colegio.sqlite3'
        initialize(self.path)
        self.db=connect(self.path)
        self.db.execute("INSERT INTO users(id,username,name,password,role) VALUES(1,'fixture','Administración','unused','admin')")
        self.db.execute("INSERT INTO guardians(id,name,document) VALUES(1,'Representante','V-123')")
        self.db.execute("INSERT INTO grades(id,name,capacity) VALUES(1,'Primaria',30)")
        self.db.execute('''INSERT INTO students(id,name,document,student_code,birth_date,guardian_id,grade_id,school_year,
            monthly_fee,discount,status,enrollment_start,enrollment_end)
            VALUES(1,'Alumno','AL-000001','AL-000001','2015-01-01',1,1,2025,10000,10,'active','2025-09-15','2026-08-31')''')
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def sync(self, on):
        with self.db:
            return synchronize_monthly_charges(self.db,date.fromisoformat(on))

    def test_elapsed_months_reopening_and_due_dates(self):
        self.assertEqual(self.sync('2025-10-06'),{'created':2,'assessed':2})
        with patch('colegio.db.local_today',return_value=date(2025,10,6)):
            ledger=charges(self.db)
        self.assertEqual([r['period'] for r in ledger],['2025-09','2025-10'])
        self.assertEqual([r['amount'] for r in ledger],[9000,9000])
        self.assertEqual([r['overdue'] for r in ledger],[True,False])
        self.assertEqual(self.sync('2025-10-06'),{'created':0,'assessed':0})
        self.assertEqual(self.sync('2025-11-01')['created'],1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM charges').fetchone()[0],3)

    def test_calendar_rollover_end_of_enrollment_and_short_month(self):
        with self.db:
            self.db.execute("UPDATE students SET enrollment_start='2025-11-01',enrollment_end='2026-02-28'")
            self.db.execute("UPDATE settings SET value='31' WHERE key='due_day'")
        self.assertEqual(self.sync('2026-01-01')['created'],3)
        self.assertEqual(self.sync('2026-06-01')['created'],1)
        ledger=charges(self.db)
        self.assertEqual([r['period'] for r in ledger],['2025-11','2025-12','2026-01','2026-02'])
        self.assertEqual([r['due_date'] for r in ledger],['2025-11-30','2025-12-31','2026-01-31','2026-02-28'])
        self.assertEqual(self.sync('2028-01-01')['created'],0)

    def test_full_scholarship_and_cancelled_month_stay_calculated(self):
        with self.db:
            self.db.execute('UPDATE students SET discount=100')
        self.assertEqual(self.sync('2025-10-06'),{'created':0,'assessed':2})
        with self.db:
            self.db.execute('UPDATE students SET discount=0')
        self.assertEqual(self.sync('2025-11-01')['created'],1)
        self.assertEqual([r['period'] for r in charges(self.db)],['2025-11'])
        with self.db:
            self.db.execute("UPDATE charges SET cancelled=1 WHERE period='2025-11'")
            result=generate_month(self.db,{'period':'2025-09','school_year':2025},1)
        self.assertEqual(result['created'],0)
        self.assertEqual(self.sync('2025-12-01')['created'],1)
        self.assertEqual([r['period'] for r in charges(self.db)],['2025-12'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM charges').fetchone()[0],2)

    def test_existing_charge_payment_and_receipt_are_preserved(self):
        with self.db:
            self.db.execute("INSERT INTO charges(student_id,period,concept,amount,due_date) VALUES(1,'2025-09','Mensualidad',7777,'2025-09-10')")
            receipt=record_payment(self.db,{'student_id':1,'amount':'20','currency':'USD','paid_on':'2025-09-20',
                'method':'Efectivo','request_key':'historic'},1)['id']
        old=dict(self.db.execute('SELECT * FROM payments WHERE id=?',(receipt,)).fetchone())
        self.assertEqual(self.sync('2025-10-06')['created'],1)
        ledger=charges(self.db)
        self.assertEqual([r['amount'] for r in ledger],[7777,9000])
        self.assertEqual(sum(r['balance'] for r in ledger),14777)
        self.assertEqual(dict(self.db.execute('SELECT * FROM payments WHERE id=?',(receipt,)).fetchone()),old)
        self.assertEqual(json.loads(old['receipt_snapshot'])['person']['student_name'],'Alumno')

    def test_inactive_future_and_other_academic_year(self):
        with self.db:
            self.db.execute("UPDATE students SET status='inactive'")
        self.assertEqual(self.sync('2025-10-06')['created'],0)
        with self.db:
            self.db.execute("UPDATE students SET status='active',enrollment_start='2025-11-01'")
        self.assertEqual(self.sync('2025-10-06')['created'],0)
        with self.db:
            self.db.execute("UPDATE settings SET value='2027' WHERE key='school_year'")
        self.assertEqual(self.sync('2027-12-01')['created'],10)
        self.assertEqual(charges(self.db)[-1]['period'],'2026-08')

    def test_explicit_future_period_and_concurrent_reopening(self):
        def reopen(_):
            with closing(connect(self.path)) as db, db:
                db.execute('BEGIN IMMEDIATE')
                return synchronize_monthly_charges(db,date(2025,10,6))
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(reopen,range(2)))
        self.assertEqual(sum(r['created'] for r in results),2)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM charges').fetchone()[0],2)
        with self.db:
            self.assertEqual(generate_month(self.db,{'period':'2025-11','school_year':2025},1)['created'],1)
        self.assertEqual(self.sync('2025-11-01')['created'],0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM charges').fetchone()[0],3)


if __name__=='__main__':
    unittest.main()
