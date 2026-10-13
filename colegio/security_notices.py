"""Recovery notices survive restart without storing authentication secrets."""
import json
import secrets
from datetime import datetime, timezone, timedelta

from .db import ValidationError

NOTICE_KEY = 'security_password_recovery'


def record_recovery(db, user):
    notice = {'id': secrets.token_hex(16), 'username': user['username'],
              'occurred_at': datetime.now(timezone(timedelta(hours=-4))).isoformat()}
    db.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
               (NOTICE_KEY, json.dumps(notice, ensure_ascii=False)))
    return notice


def pending_notice(db, user):
    if user['role'] != 'admin':
        return None
    row = db.execute('SELECT value FROM settings WHERE key=?', (NOTICE_KEY,)).fetchone()
    if not row:
        return None
    try:
        notice = json.loads(row[0])
        if not isinstance(notice, dict) or not all(isinstance(notice.get(k), str) for k in ('id', 'username', 'occurred_at')):
            raise ValueError
    except (ValueError, TypeError):
        return {'id': '', 'unreadable': True}
    seen = db.execute('SELECT value FROM settings WHERE key=?', ('security_recovery_seen_' + str(user['id']),)).fetchone()
    return None if seen and seen[0] == notice['id'] else notice


def acknowledge_notice(db, user, data):
    if user['role'] != 'admin':
        raise PermissionError('Este aviso corresponde a Administración.')
    notice = pending_notice(db, user)
    if not notice or not notice['id'] or data.get('notice_id') != notice['id']:
        raise ValidationError('El aviso cambió. Vuelve a comprobarlo antes de confirmar.')
    db.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
               ('security_recovery_seen_' + str(user['id']), notice['id']))
