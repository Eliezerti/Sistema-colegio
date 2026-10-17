"""Expected money comes from actual published 1.0.71, not the new implementation."""
from contextlib import closing,ExitStack
from datetime import date
from pathlib import Path
from unittest.mock import patch
import hashlib,json,tempfile,unittest
from colegio.db import connect,initialize
from colegio.server import snapshot
from colegio.administration import cash_summary
from colegio.directory_reports import daily_report
from colegio.monthly_report import report as monthly

class PublishedIncomeReferenceTests(unittest.TestCase):
    def test_published_cash_daily_monthly_and_arrears_identical_after_all_migrations(self):
        root=Path(__file__).parent/'fixtures/income';meta=json.loads((root/'manifest.json').read_text());raw=(root/meta['reference_filename']).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),meta['reference_sha256']);reference=json.loads(raw);self.assertTrue(reference['fictional']);self.assertEqual(reference['commit'],meta['commit']);self.assertEqual(reference['fixture_sha256'],meta['sha256'])
        from tests.test_income_schema import IncomeSchemaTests
        with tempfile.TemporaryDirectory() as d,ExitStack() as stack:
            path=IncomeSchemaTests().fixture(d);initialize(path)
            on=date.fromisoformat(reference['as_of'])
            for module in ('colegio.db','colegio.server','colegio.administration'):stack.enter_context(patch(module+'.local_today',return_value=on))
            with closing(connect(path)) as db:
                state=snapshot(db,dict(id=1,role='admin',name='Referencia ficticia'));day=daily_report(state);month=monthly(db,state,reference['as_of'][:7])
                actual=dict(cash=cash_summary(db,reference['as_of']),summary=state['summary'],daily={key:day[key] for key in reference['expected']['daily']},monthly={key:month[key] for key in reference['expected']['monthly']})
                self.assertEqual(actual,reference['expected'])
