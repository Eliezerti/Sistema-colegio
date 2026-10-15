"""Native smoke checks, called only with disposable --self-test data."""
import ctypes
import json
import os
import re
import shutil
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
    school = {'school_name': 'Mi colegio', 'school_year': '2026'}
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
    # Exercise the real receipt markup and WebView2 print settings with a frozen,
    # fictional document. No payment is registered in any database.
    from .branding import SCHOOL_PROFILE
    from .documents import render_pdf
    receipt = {'settings': dict(SCHOOL_PROFILE), 'payment': {
        'id': 31, 'paid_on': '2026-10-14', 'guardian_name': 'Representante',
        'guardian_document': 'V-12345678', 'guardian_phone': '04121234567',
        'guardian_address': '', 'student_name': 'Alumno',
        'student_code': 'AL-000001', 'student_document': 'CE-199998887771',
        'grade_name': 'Primero / A', 'currency': 'VES', 'received_amount': 300000,
        'amount': 3000, 'balance_before': 8000, 'balance_after': 5000,
        'exchange_rate': '100', 'method': 'Transferencia', 'reference': 'TR-001',
        'operator': 'Administración', 'voided': False, 'notes': 'Pago ficticio.'},
        'allocations': [{'concept': f'Mensualidad ficticia {i}', 'period': '2026-09',
                         'amount': 1000, 'balance_after': 0} for i in range(3)]}
    pdf = render_pdf('receipt', receipt)
    if b'/MediaBox [0 0 396 612]' not in pdf or b'/Count 1 ' not in pdf:
        raise RuntimeError('El comprobante PDF no ocupa una única media carta.')
    (path / 'comprobante-media-carta.pdf').write_bytes(pdf)
    window.evaluate_js("document.querySelector('#print-area').innerHTML=paymentReceiptMarkup(" +
                       json.dumps(receipt, ensure_ascii=False) + ");setReceiptPaper('half-letter');")
    paired = render_pdf('receipt', receipt, 'letter-pair')
    if b'/MediaBox [0 0 792 612]' not in paired or b'/Count 1 ' not in paired:
        raise RuntimeError('No se prepararon dos copias en una sola carta horizontal.')
    (path / 'comprobante-dos-copias.pdf').write_bytes(paired)
    for name, width, height in (('media-carta',5.5,8.5), ('media-carta-en-carta',8.5,11), ('dos-copias',11,8.5)):
        target = path / (name + '-webview2.pdf')
        if name == 'dos-copias':
            window.evaluate_js("document.querySelector('#native-letter-check').remove();setReceiptPaper('letter-pair');")
        if height == 11:
            window.evaluate_js("document.head.insertAdjacentHTML('beforeend','<style id=native-letter-check>@page receipt-half-letter{size:letter;margin:0}</style>')")

        def print_receipt():
            core = form.browser.webview.CoreWebView2
            settings = core.Environment.CreatePrintSettings()
            settings.PageWidth, settings.PageHeight = width, height
            # Escala predeterminada de WebView2; no se impone al usuario.
            settings.MarginTop = settings.MarginBottom = 0
            settings.MarginLeft = settings.MarginRight = 0
            settings.ShouldPrintBackgrounds = True
            settings.ShouldPrintHeaderAndFooter = False
            return core.PrintToPdfAsync(str(target), settings)

        task = form.Invoke(Func[Object](print_receipt))
        until = time.monotonic() + 30
        while not task.IsCompleted and time.monotonic() < until:
            time.sleep(.05)
        if not task.IsCompleted or not task.GetAwaiter().GetResult():
            raise RuntimeError('No se pudo imprimir el comprobante con WebView2.')
        printed = target.read_bytes()
        box = re.search(rb'/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]', printed)
        if not box or tuple(float(v) for v in box.groups()) != (width * 72, height * 72):
            raise RuntimeError('WebView2 cambió las dimensiones físicas del comprobante.')
        if len(re.findall(rb'/Type\s*/Page\b', printed)) != 1:
            raise RuntimeError('WebView2 añadió páginas al comprobante.')
        print(f'PASS RECIBO: WebView2 {name}, {width * 72:g} x {height * 72:g} puntos, una página, escala predeterminada.')
    window.evaluate_js("setReceiptPaper('half-letter')")
    if os.environ.get('AULA_RECEIPT_REPORT_DIR'):
        evidence = Path(os.environ['AULA_RECEIPT_REPORT_DIR'])
        evidence.mkdir(parents=True, exist_ok=True)
        for name in ('comprobante-media-carta.pdf', 'media-carta-webview2.pdf', 'media-carta-en-carta-webview2.pdf',
                     'comprobante-dos-copias.pdf', 'dos-copias-webview2.pdf'):
            shutil.copyfile(path / name, evidence / name)
    found, watcher = cancel_dialog()
    # WinForms file dialogs must run on the window's STA thread.
    selected = form.Invoke(Func[Object](lambda: window.create_file_dialog(
        webview.OPEN_DIALOG, directory=str(path), file_types=('PDF (*.pdf)',))))
    watcher.join(1)
    if not found.is_set() or selected:
        raise RuntimeError('No se comprobó el selector de archivos de la ventana Windows.')
    print('PASS B2: PDF administrativo, impresión PDF nativa WebView2 y selector Windows abierto/cancelado.')


def trial_cleanup(directory):
    """Bundled-executable smoke, strictly inside its disposable self-test directory."""
    from contextlib import closing
    from .db import initialize,connect,hash_password,record_payment,local_today,next_record_id
    from .clock_guard import ClockGuard
    from .backup_keys import prepare,confirm
    from .audit_chain import local_status
    from .trial_payment_cleanup import preview,clear,CONFIRMATION
    from .backup_inspection import probe_backup
    folder=Path(directory)/'limpieza-ficticia';path=folder/'colegio.sqlite3'
    initialize(path);ClockGuard(path).require()
    pending,recovery=prepare(folder,'FICTICIO-limpieza-respaldo-2026');confirm(folder,pending)
    today=local_today().isoformat();year=local_today().year
    with closing(connect(path)) as db,db:
        db.execute("INSERT INTO users VALUES(1,'admin-ficticio','Prueba local',?,'admin')",(hash_password('FICTICIO-clave-prueba-2026'),))
        db.execute("INSERT INTO guardians(id,name,document) VALUES(1,'Representante ficticio','PRUEBA-V-1')")
        db.execute("INSERT INTO grades(id,name) VALUES(1,'Grado ficticio')")
        db.execute("INSERT INTO students(id,name,document,birth_date,guardian_id,grade_id,school_year,monthly_fee,discount,status,enrollment_start,enrollment_end) VALUES(1,'Alumno ficticio','PRUEBA-A-1','2015-01-01',1,1,?,10000,0,'active',?,?)",(year,f'{year}-01-01',f'{year}-12-31'))
        db.execute("INSERT INTO charges(student_id,period,concept,amount,due_date) VALUES(1,?,'Concepto ficticio',10000,?)",(today[:7],today))
        record_payment(db,dict(student_id=1,amount='10',currency='USD',method='Efectivo',paid_on=today,request_key='ficticio-antes'),1)
    review=preview(folder)
    result=clear(folder,username='admin-ficticio',password='FICTICIO-clave-prueba-2026',preview_hash=review['preview_hash'],
        confirmation=CONFIRMATION,trial_only=True,reason='Preparación ficticia antes de producción')
    assert probe_backup(result['backup']['path'],'FICTICIO-limpieza-respaldo-2026')['payments']==1
    with closing(connect(path)) as db,db:
        assert next_record_id(db,'payments')==1 and local_status(db)['ok']
        assert db.execute('SELECT COUNT(*) FROM students').fetchone()[0]==1
        assert record_payment(db,dict(student_id=1,amount='10',currency='USD',method='Efectivo',paid_on=today,request_key='ficticio-produccion'),1)['id']==1
    print('PASS LIMPIEZA: ejecutable instalado, respaldo cifrado verificable, alumno conservado, bitácora válida y primer recibo R-000001.',flush=True)
