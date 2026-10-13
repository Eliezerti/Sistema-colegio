"""Native smoke checks, called only with disposable --self-test data."""
import ctypes
import os
import threading
import time
from pathlib import Path


def cancel_dialog(title=None):
    """Close only this process's native file chooser after proving it opened."""
    from ctypes import wintypes
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    user32.GetClassNameW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    user32.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    found = threading.Event()

    @callback_type
    def visit(handle, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        caption = ctypes.create_unicode_buffer(512)
        kind = ctypes.create_unicode_buffer(80)
        user32.GetWindowTextW(handle, caption, 512)
        user32.GetClassNameW(handle, kind, 80)
        if pid.value == os.getpid() and kind.value == '#32770' and (title is None or caption.value == title):
            found.set()
            user32.PostMessageW(handle, 0x0010, 0, 0)  # WM_CLOSE: never select/delete a file.
        return True

    def watch():
        until = time.monotonic() + 20
        while not found.is_set() and time.monotonic() < until:
            user32.EnumWindows(visit, 0)
            time.sleep(.05)

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    return found, watcher


def toolkit(directory):
    import tkinter as tk
    from tkinter import filedialog, ttk
    root = tk.Tk()
    root.withdraw()
    try:
        frame = ttk.Frame(root)
        ttk.Label(frame, text='Restauración · contraseña · selección').pack()
        ttk.Entry(frame).pack()
        ttk.Combobox(frame, values=('Contraseña', 'Recuperación')).pack()
        root.update()
        # Keep clock/tzdata and Spanish msgcat support; do not trim them blindly.
        root.tk.call('clock', 'format', 0, '-timezone', ':America/Caracas')
        root.tk.call('package', 'require', 'msgcat')
        root.tk.call('::msgcat::mclocale', 'es')
        title = 'Aula - B2 selector Tk'
        found, watcher = cancel_dialog(title)
        selected = filedialog.askopenfilename(parent=root, title=title, initialdir=str(directory))
        watcher.join(1)
        if not found.is_set() or selected:
            raise RuntimeError('No se comprobó la apertura y cancelación del selector Tk.')
    finally:
        root.destroy()
    print('PASS B2: Tcl/Tk, ttk, calendario, textos en español y selector nativo abierto/cancelado.')


def renderer(window, directory):
    import webview
    from System import Func, Object
    from .directory_reports import directory_report, directory_pdf
    path = Path(directory)
    school = {'school_name': 'Colegio ficticio B2', 'school_year': '2026'}
    report = directory_report({'settings': school, 'students': [], 'grades': [],
                               'today': '2026-10-13', 'user': {'role': 'admin', 'name': 'Prueba B2'}},
                              'students', {})
    generated = directory_pdf(report)
    if not generated.startswith(b'%PDF-'):
        raise RuntimeError('No se generó el PDF con las fuentes incluidas.')
    (path / 'listado-ficticio.pdf').write_bytes(generated)
    window.evaluate_js("document.querySelector('#print-area').innerHTML='<article class=receipt><h1>Comprobación ficticia B2</h1><p>Impresión · español · Bs 123,45</p></article>'")
    form = window.native
    output = path / 'impresion-webview2.pdf'
    task = form.Invoke(Func[Object](lambda: form.browser.webview.CoreWebView2.PrintToPdfAsync(str(output), None)))
    until = time.monotonic() + 30
    while not task.IsCompleted and time.monotonic() < until:
        time.sleep(.05)
    if not task.IsCompleted or not task.GetAwaiter().GetResult() or not output.read_bytes().startswith(b'%PDF-'):
        raise RuntimeError('No se pudo comprobar la impresión PDF del motor Windows.')
    found, watcher = cancel_dialog()
    # WinForms file dialogs must run on the window's STA thread.
    selected = form.Invoke(Func[Object](lambda: window.create_file_dialog(
        webview.OPEN_DIALOG, directory=str(path), file_types=('PDF (*.pdf)',))))
    watcher.join(1)
    if not found.is_set() or selected:
        raise RuntimeError('No se comprobó el selector de archivos de la ventana Windows.')
    print('PASS B2: PDF administrativo, impresión PDF nativa WebView2 y selector Windows abierto/cancelado.')
