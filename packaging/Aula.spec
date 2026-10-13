# Windows x64 only, WebView2. Tcl/Tk is required by recovery tools.
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH).parent
sys.path.insert(0, str(root / 'packaging'))
from bundle_rules import EXCLUDED, blocked_module, keep_data

datas, binaries, hidden = collect_all('webview')
datas = [item for item in datas if keep_data(item[1] + '/' + Path(item[0]).name)]
binaries = [item for item in binaries if keep_data(item[1] + '/' + Path(item[0]).name)]
hidden = [name for name in hidden if not blocked_module(name)]

a = Analysis([str(root / 'desktop_entry.py')], pathex=[str(root)], binaries=binaries,
             datas=datas + [(str(root / 'static'), 'static'), (str(root / 'colegio/fonts'), 'colegio/fonts')],
             hiddenimports=hidden + ['pystray._win32'], excludes=list(EXCLUDED),
             hookspath=[], runtime_hooks=[], noarchive=False)
a.datas = [entry for entry in a.datas if keep_data(entry[0])]
a.binaries = [entry for entry in a.binaries if keep_data(entry[0])]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Aula', debug=False,
          strip=False, upx=False, console=False, icon=str(root / 'packaging/aula.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Aula')
