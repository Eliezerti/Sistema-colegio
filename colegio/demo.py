"""Disposable workspaces; never read, clone or reset a production database."""
import shutil
import tempfile
from pathlib import Path

from .storage import DataLock


MARKER = 'aula-disposable-workspace-v1'


class DemoWorkspace:
    def __init__(self, root=None):
        self.root = Path(root) if root else Path(tempfile.gettempdir()) / 'AulaColegio-Pruebas'
        self.lock = self.temporary = None

    def __enter__(self):
        if self.root.is_symlink():
            raise RuntimeError('La carpeta de pruebas no puede ser un enlace a otra carpeta.')
        self.lock = DataLock(self.root)
        try:
            # Only remove marked, disposable sessions we created, after owning the lock.
            # This also recovers the temporary space after a power cut or forced kill.
            for folder in self.root.glob('prueba-*'):
                marker = folder / '.aula-pruebas'
                if folder.is_symlink() or not folder.is_dir() or not marker.is_file():
                    continue
                if marker.read_text(encoding='utf-8') == MARKER:
                    shutil.rmtree(folder)
            self.temporary = tempfile.TemporaryDirectory(prefix='prueba-', dir=self.root)
            self.directory = Path(self.temporary.name)
            (self.directory / '.aula-pruebas').write_text(MARKER, encoding='utf-8')
            return self.directory
        except BaseException:
            self.__exit__()
            raise

    def __exit__(self, *args):
        try:
            if self.temporary:
                self.temporary.cleanup()
        finally:
            if self.lock:
                self.lock.close()
