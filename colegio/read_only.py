"""Isolated copy viewer: immutable SQLite, fail-closed HTTP writes, RAM-only sessions."""
from contextlib import contextmanager, closing
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
import secrets
import sqlite3
import threading
import time
from pathlib import Path

from .backup_inspection import staged_backup, inspect_copy
from .branding import SCHEMA_VERSION
from .db import local_today
from .network import PrivateAccess
from .sessions import Sessions, token_hash
from .server import SchoolServer, Handler


class ReadConnection(sqlite3.Connection):
    read_only = True


class ViewClock:
    def require(self):
        # No financial operation is possible in this process.
        return None

    def snapshot(self):
        return {'blocked':False,'read_only':True,'pending':None,
            'current_time':datetime.now(timezone.utc).isoformat()}


class ReadOnlyServer(SchoolServer):
    def __init__(self, path, metadata, port=0):
        self.read_only=True
        self.read_only_info=metadata
        self.db_path=str(path)
        self.demo=False
        self.access=PrivateAccess()
        self.clock=ViewClock()
        self.sessions=Sessions()
        self.idle=15
        self.view_lock=threading.Lock()
        self.launch=secrets.token_urlsafe(32)
        self.launch_deadline=time.monotonic()+120
        self.session_token=None
        self.csrf=secrets.token_urlsafe(32)
        ThreadingHTTPServer.__init__(self,('127.0.0.1',port),Handler)
        self.daemon_threads=False
        from .sessions import idle_minutes
        from contextlib import closing
        with closing(self.connect_view()) as db:self.idle=idle_minutes(db)

    @property
    def cookie_name(self):
        return 'aula_copy_session'

    def accept_launch(self, token):
        with self.view_lock:
            if not self.launch or time.monotonic()>self.launch_deadline or not secrets.compare_digest(token,self.launch):
                raise PermissionError('El enlace de consulta venció. Abre la copia nuevamente desde Windows.')
            self.launch=None
            self.session_token=secrets.token_urlsafe(32)
            self.sessions.issue(token_hash(self.session_token))
            return self.session_token

    def view_session(self, cookie):
        token=''
        for part in cookie.split(';'):
            if part.strip().startswith(self.cookie_name+'='):token=part.strip().split('=',1)[1]
        if not self.session_token or not secrets.compare_digest(token,self.session_token):return None
        digest=token_hash(token)
        if not self.sessions.status(digest,self.idle):return None
        return dict(id=0,name='Consulta de copia',username='copia',role='reader',csrf=self.csrf,
            token=digest,rate_confirmed_on=local_today().isoformat())

    def connect_view(self):
        db=sqlite3.connect(Path(self.db_path).resolve().as_uri()+'?mode=ro&immutable=1',uri=True,factory=ReadConnection)
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def backup_status(self):
        return {'read_only':True,'alerts':[],'crypto':{},'secondary_directory':''}

    def make_backup(self):
        raise PermissionError('Esta copia es de solo lectura; no crea respaldos.')

    def server_close(self):
        self.sessions.clear()
        ThreadingHTTPServer.server_close(self)


@contextmanager
def open_copy(source, credential=None, credential_kind='password', *, port=0):
    source=Path(source).resolve()
    # staged_backup only copies bytes from the origin, then validates/decrypts privately.
    with staged_backup(source,credential,credential_kind) as (path,inspection,_):
        if inspection['summary']['schema']<SCHEMA_VERSION:
            from .audit_chain import adopt_restored
            from .db import initialize
            # Migration affects only the verified disposable copy, never the source.
            adopt_restored(path);initialize(path)
            with closing(sqlite3.connect(path)) as db:db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            inspect_copy(path)
        copied=datetime.fromtimestamp(source.stat().st_mtime).astimezone().isoformat(timespec='seconds')
        metadata={'copied_at':copied,'date_source':'fecha del archivo, no certificada',
            'message':f'Copia del {copied}, solo lectura','schema':SCHEMA_VERSION}
        server=ReadOnlyServer(path,metadata,port)
        try:yield server
        finally:server.server_close()


def main():
    import argparse
    import getpass
    import webbrowser
    parser=argparse.ArgumentParser(description='Abrir una copia de Aula en solo lectura, sin restaurar.')
    parser.add_argument('source');parser.add_argument('--recovery',action='store_true')
    args=parser.parse_args()
    from .backup_crypto import MAGIC
    with open(args.source,'rb') as source:encrypted=source.read(len(MAGIC))==MAGIC
    credential=getpass.getpass('Clave de recuperación: ' if args.recovery else 'Contraseña del respaldo: ') if encrypted else None
    with open_copy(args.source,credential,'recovery' if args.recovery else 'password') as server:
        webbrowser.open(f'http://127.0.0.1:{server.server_port}/?view_token={server.launch}')
        try:server.serve_forever()
        except KeyboardInterrupt:pass


if __name__=='__main__':main()
