"""Conservative Windows x64 package boundaries, based on 1.0.49's real inventory."""
from pathlib import PurePosixPath

EXCLUDED = ('PyInstaller', 'setuptools', 'pefile', 'altgraph', 'webview.__pyinstaller',
            'webview.platforms.android', 'webview.platforms.cef', 'webview.platforms.cocoa',
            'webview.platforms.gtk', 'webview.platforms.mshtml', 'webview.platforms.qt')
RETIRED_STATIC = ('mobile.js', 'manifest.webmanifest', 'service-worker.js', 'offline.html',
                  'icon-mobile-192.png', 'icon-mobile-512.png')


def blocked_module(name):
    return any(name == root or name.startswith(root + '.') for root in EXCLUDED)


def keep_data(name):
    parts = PurePosixPath(name.replace('\\', '/')).parts
    if parts and parts[0] == '_internal':
        parts = parts[1:]
    if len(parts) == 2 and parts[0] == 'static' and parts[1] in RETIRED_STATIC:
        return False
    if len(parts) >= 2 and parts[:2] == ('webview', '__pyinstaller'):
        return False
    if len(parts) >= 3 and parts[:2] == ('webview', 'platforms') and parts[-1].endswith('.py'):
        return not blocked_module('webview.platforms.' + parts[-1][:-3])
    if len(parts) >= 3 and parts[0] in ('_tcl_data', '_tk_data') and parts[1] == 'msgs':
        language = parts[-1].split('.')[0].split('_')[0]
        return language in ('en', 'es')
    if parts and parts[0] == 'tcl8' and parts[-1].startswith('tcltest-'):
        return False
    if '/'.join(parts) in ('webview/lib/pywebview-android.jar',
                          'webview/lib/WebBrowserInterop.x86.dll', 'webview/lib/WebBrowserInterop.x64.dll'):
        return False
    # Preserve all encodings, tzdata, Tcl/Tk binaries and clock/msgcat modules.
    # pywebview 5.4 checks all three loader directories even when using x64.
    return True
