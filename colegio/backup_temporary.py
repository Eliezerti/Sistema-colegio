"""Private local scratch; never trust TMP/TEMP to point away from USB/cloud."""
import os
import sys
from pathlib import Path


def private_root():
    if sys.platform=='win32':
        import ctypes
        from ctypes import wintypes
        buffer=ctypes.create_unicode_buffer(32768)
        function=ctypes.WinDLL('shell32').SHGetFolderPathW
        function.argtypes=[wintypes.HWND,ctypes.c_int,wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR]
        function.restype=ctypes.c_long
        if function(None,28,None,0,buffer)!=0:raise ValueError('Windows no permitió preparar una carpeta temporal local segura.')
        root=Path(buffer.value)/'AulaColegio-Temporales'
    else:root=Path('/tmp')/('aula-privado-'+str(os.getuid()))
    if root.is_symlink() or (hasattr(root,'is_junction') and root.is_junction()):raise ValueError('La carpeta temporal de Aula no puede ser un enlace a otro destino.')
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    if sys.platform!='win32':
        if root.stat().st_uid!=os.getuid():raise ValueError('La carpeta temporal pertenece a otra cuenta.')
        root.chmod(0o700)
    return root
