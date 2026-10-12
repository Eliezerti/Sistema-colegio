"""Persistent wall-clock checks, independent of the financial SQLite schema."""
import json
import os
import re
import secrets
import shutil
import sqlite3
import tempfile
import threading
import time
import weakref
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

OFFLINE_LIMIT = timedelta(days=7)
ADJUSTMENT_LIMIT = timedelta(minutes=2)
CARACAS = timezone(timedelta(hours=-4))


def utc_now():
    return datetime.now(timezone.utc)


def parse_time(value):
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None or stamp.year < 1900:
        raise ValueError('Invalid clock timestamp')
    return stamp.astimezone(timezone.utc)


def sync_directory(path):
    if os.name != 'nt':
        handle = os.open(path, os.O_RDONLY)
        try:
            os.fsync(handle)
        finally:
            os.close(handle)


def atomic_json(path, value):
    path = Path(path)
    handle, name = tempfile.mkstemp(prefix='.aula-control-', suffix='.tmp', dir=path.parent)
    os.close(handle)
    try:
        with open(name, 'w', encoding='utf-8') as saved:
            json.dump(value, saved, ensure_ascii=False)
            saved.flush()
            os.fsync(saved.fileno())
        os.replace(name, path)
        sync_directory(path.parent)
    finally:
        if Path(name).exists():
            Path(name).unlink()


def latest_recorded_time(database):
    """Bootstrap an existing installation from recorded activity, never tuition dates."""
    values = []
    try:
        with closing(sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro', uri=True)) as db:
            for table in ('audit', 'payments', 'enrollment_documents'):
                try:
                    value = db.execute(f'SELECT MAX(created_at) FROM {table}').fetchone()[0]
                    if value:
                        values.append(parse_time(value))
                except (sqlite3.Error, TypeError, ValueError):
                    continue
    except sqlite3.Error:
        pass
    return max(values) if values else None


class ClockConfirmationRequired(Exception):
    def __init__(self, status):
        super().__init__('Revisa la fecha y hora de Windows. Solo un administrador puede confirmar antes de continuar.')
        self.status = status


class ClockInputError(ValueError):
    pass


class ClockGuard:
    def __init__(self, database, *, now=None, monotonic=None, history=False):
        self.database = Path(database).resolve()
        self.path = self.database.parent/'clock-status.json'
        self.now = now or utc_now
        self.monotonic = monotonic or time.monotonic
        self.lock = threading.RLock()
        self.anchor = None
        self.anchor_tick = self.monotonic()
        self.saved_tick = self.anchor_tick
        self.invalid_file = False
        self.persistence_error = False
        current = self.now()
        try:
            self.state = json.loads(self.path.read_text(encoding='utf-8'))
            if self.state['version'] != 1:
                raise ValueError('Clock version')
            self.last = parse_time(self.state['last_seen'])
            pending = self.state.get('pending')
            if pending is not None and (not isinstance(pending, dict) or
                not re.fullmatch(r'[A-Za-z0-9_-]{20,64}', str(pending.get('id', '')))):
                raise ValueError('Clock pending state')
            try:
                atomic_json(self.path, self.state)
            except OSError:
                self.persistence_error = True
        except FileNotFoundError:
            recorded = latest_recorded_time(database) if history else None
            self.last = recorded or current
            self.state = {'version':1, 'last_seen':self.last.isoformat(), 'pending':None}
            try:
                atomic_json(self.path, self.state)
            except OSError:
                self.persistence_error = True
            if recorded is not None:
                # First adoption, deleted control file, or a database brought to
                # another PC: recorded activity is not a trusted elapsed clock.
                self._pending('initial_review', current)
        except (OSError, ValueError, TypeError, KeyError):
            self.last = current
            self.state = {'version':1, 'last_seen':current.isoformat(), 'pending':None}
            self.invalid_file = True
        self.persisted = self.last

    def _pending(self, reason, current):
        self.state['pending'] = {'id':secrets.token_urlsafe(24), 'reason':reason,
                                 'previous_time':self.last.isoformat(), 'detected_time':current.isoformat()}
        try:
            if not self.invalid_file:
                atomic_json(self.path, self.state)
        except OSError:
            self.persistence_error = True

    def snapshot(self):
        with self.lock:
            current, tick = self.now(), self.monotonic()
            if not self.state.get('pending'):
                if self.invalid_file or self.persistence_error:
                    self._pending('control_unavailable', current)
                else:
                    reference = self.anchor + timedelta(seconds=max(0, tick-self.anchor_tick)) if self.anchor else self.last
                    difference = current-reference
                    if difference < -ADJUSTMENT_LIMIT:
                        self._pending('backwards', current)
                    elif difference > (ADJUSTMENT_LIMIT if self.anchor else OFFLINE_LIMIT):
                        self._pending('forward', current)
                    else:
                        if self.anchor is None:
                            self.anchor, self.anchor_tick = current, tick
                        self.last = max(self.last, current)
                        self.state['last_seen'] = self.last.isoformat()
                        if tick-self.saved_tick >= 30 or self.last.astimezone(CARACAS).date() != self.persisted.astimezone(CARACAS).date():
                            try:
                                atomic_json(self.path, self.state)
                                self.saved_tick = tick
                                self.persisted = self.last
                            except OSError:
                                self.persistence_error = True
                                self._pending('control_unavailable', current)
            pending = self.state.get('pending')
            return {'blocked':bool(pending), 'current_time':current.isoformat(),
                    'last_seen':self.last.isoformat(), 'pending':dict(pending) if pending else None,
                    'offline_days':OFFLINE_LIMIT.days, 'adjustment_seconds':int(ADJUSTMENT_LIMIT.total_seconds())}

    def require(self):
        status = self.snapshot()
        if status['blocked']:
            raise ClockConfirmationRequired(status)
        return status

    def confirm(self, db, user, data):
        if user['role'] != 'admin':
            raise PermissionError('Solo un administrador puede confirmar la fecha y hora.')
        with self.lock:
            status = self.snapshot()
            pending = status['pending']
            if (not pending or data.get('pending_id') != pending['id'] or data.get('reviewed') is not True):
                raise ClockInputError('Revisa nuevamente la fecha y marca la confirmación.')
            current = self.now()
            try:
                observed = parse_time(data.get('observed_at', ''))
            except (TypeError, ValueError) as error:
                raise ClockInputError('Vuelve a comprobar la fecha antes de confirmar.') from error
            if abs(current-observed) > ADJUSTMENT_LIMIT or current.astimezone(CARACAS).date() != observed.astimezone(CARACAS).date():
                raise ClockInputError('La fecha o la hora volvió a cambiar. Revisa nuevamente antes de confirmar.')
            from .db import audit
            # Correcting a future clock must not leave cookies valid for months.
            # Never extend an existing session; only cap excessive expirations.
            db.execute('UPDATE sessions SET expires=MIN(expires,?)', (int(current.timestamp())+12*3600,))
            audit(db, user['id'], 'clock_confirmation', dict(pending, confirmed_time=current.isoformat(),
                confirmed_by=user['id'], previous_last_seen=self.last.isoformat()))
            # Commit the audit BEFORE unlocking financial activity. If the metadata
            # cannot be published, the guard stays blocked and the attempt remains recorded.
            db.commit()
            if self.invalid_file and self.path.exists():
                shutil.copyfile(self.path, self.path.with_name('clock-status-invalid-'+pending['id']+'.json'))
            updated = {'version':1, 'last_seen':current.isoformat(), 'pending':None}
            atomic_json(self.path, updated)
            self.state, self.last = updated, current
            self.persisted = current
            self.anchor, self.anchor_tick = current, self.monotonic()
            self.saved_tick = self.anchor_tick
            self.invalid_file = self.persistence_error = False
            return self.snapshot()

    def close(self):
        with self.lock:
            if self.invalid_file:
                return
            try:
                atomic_json(self.path, self.state)
            except OSError:
                self.persistence_error = True


_guards = weakref.WeakValueDictionary()
_lock = threading.RLock()


def get_clock(database, *, history=False):
    key = str(Path(database).resolve())
    with _lock:
        guard = _guards.get(key)
        if guard is None:
            guard = ClockGuard(database, history=history)
            _guards[key] = guard
        return guard


def require_database_clock(db):
    database = db.execute('PRAGMA database_list').fetchone()[2]
    if database:  # Standalone in-memory fixtures have no persistent PC state.
        get_clock(database).require()
