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
    for table in ('cashea_requests','cashea_settlement_orders','cashea_allocations','cashea_settlements','cashea_orders'):
        db.execute('DROP TABLE IF EXISTS '+table)
    db.execute("DELETE FROM settings WHERE key LIKE 'cashea_%' OR key IN ('id_floor_cashea_orders','id_floor_cashea_settlements')")
    db.execute('DROP TABLE IF EXISTS audit_links')
    db.execute('DROP TABLE IF EXISTS audit_meta')
    db.execute('PRAGMA user_version=10')
    if hasattr(db, '_audit_checked'): db._audit_checked = False
    # Some legacy callers use closing() without a transaction context. The new
    # settings DELETE starts one: publish this disposable synthetic layout now.
    db.commit()
