"""Real browser proof of a disposable read-only copy; fictional data only."""
from contextlib import closing
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.test_system import SystemTests
from colegio.storage import consistent_backup
from colegio.read_only import open_copy

f=SystemTests();f.setUp()
try:
    f.request('payments',f.payment())
    source=f.path.parent/'copia-navegador.sqlite3';consistent_backup(f.path,source)
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    with open_copy(source) as viewer:
        temporary=Path(viewer.db_path).parent
        thread=threading.Thread(target=viewer.serve_forever);thread.start()
        try:
            env=dict(os.environ,AULA_VIEW_URL=f'http://127.0.0.1:{viewer.server_port}/?view_token={viewer.launch}')
            subprocess.run(['node','tests/viewer_browser.cjs'],env=env,check=True)
        finally:viewer.shutdown();thread.join()
    assert not temporary.exists()
    assert before==hashlib.sha256(source.read_bytes()).hexdigest()
finally:f.tearDown()
