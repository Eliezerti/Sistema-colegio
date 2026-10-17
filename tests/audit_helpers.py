"""Explicit trusted fixture publication and synthetic pre-A4 schema construction.

Only disposable test databases use these helpers; product recovery requires A1 review.
"""
from colegio.audit_chain import adopt_restored, controls


def publish_fixture(path):
    adopt_restored(path)


def legacy_fixture(db):
    # Existing upgrade tests construct an older column layout. Remove ONLY new
    # companion objects before constructing that synthetic pre-A4 layout.
    for name, in db.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'audit_%'").fetchall():
        db.execute('DROP TRIGGER "'+name+'"')
    # Only these disposable synthetic-v10 fixtures remove later companion tables.
    for table in ('bank_classifications','reconciliation_links','bank_movements','statement_imports','statement_profiles','cash_deposit_payments','cash_deposits','other_income','expense_accounts','payment_accounts','income_categories','school_accounts'):
        db.execute('DROP TABLE IF EXISTS '+table)
    db.execute('DROP TABLE IF EXISTS audit_links')
    db.execute('DROP TABLE IF EXISTS audit_meta')
    db.execute('PRAGMA user_version=10')
    if hasattr(db, '_audit_checked'): db._audit_checked = False
