"""Authentication lifetimes are process-local and independent of the PC clock."""
import hashlib
import re
import threading
import time

from .db import ValidationError, integer

IDLE_KEY = 'session_idle_minutes'
ABSOLUTE_SECONDS = 12 * 3600


def token_hash(token):
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        return ''
    return 'sha256:' + hashlib.sha256(token.encode('ascii')).hexdigest()


def idle_minutes(db):
    row = db.execute('SELECT value FROM settings WHERE key=?', (IDLE_KEY,)).fetchone()
    try:
        return integer(row[0], 5, 60) if row else 15
    except ValidationError:
        return 15  # Invalid configuration never disables the limit.


class Sessions:
    def __init__(self, now=None):
        self.now = now or time.monotonic
        self.lock = threading.RLock()
        self.entries = {}

    def issue(self, digest):
        with self.lock:
            tick = self.now()
            self.entries[digest] = (tick, tick)

    def status(self, digest, minutes):
        with self.lock:
            entry = self.entries.get(digest)
            if entry is None:
                return None
            tick = self.now()
            started, active = entry
            remaining = min(minutes * 60 - (tick - active), ABSOLUTE_SECONDS - (tick - started))
            if remaining <= 0 or tick < active:
                self.entries.pop(digest, None)
                return None
            return {'remaining_seconds': remaining, 'idle_minutes': minutes,
                    'absolute_remaining_seconds': ABSOLUTE_SECONDS - (tick - started)}

    def touch(self, digest, minutes):
        with self.lock:
            if not self.status(digest, minutes):
                return None  # An expired token cannot be revived by a heartbeat.
            started, _ = self.entries[digest]
            self.entries[digest] = (started, self.now())
            return self.status(digest, minutes)

    def revoke(self, digest):
        with self.lock:
            self.entries.pop(digest, None)

    def clear(self):
        with self.lock:
            self.entries.clear()
