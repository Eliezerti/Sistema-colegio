"""Windows window and tray; shares the existing SQLite application unchanged."""
import argparse
import json
import logging
import os
import sys
import tempfile
import threading
import time
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path

from .demo import DemoWorkspace
from .network import private_origin
from .server import ROOT, open_school
from .storage import DataLock
from .branding import SCHOOL_NAME

TITLE='Aula · Administración escolar'


def data_directory():
    base=os.environ.get('LOCALAPPDATA')
    if not base:
        raise RuntimeError('No se encuentra la carpeta de datos del usuario de Windows.')
    return Path(base)/'AulaColegio'


class WindowsInstance:
    """One desktop instance; installer can also detect the same named mutex."""
    def __init__(self,demo=False):self.demo=demo;self.handle=None

    def __enter__(self):
        if os.name!='nt':return True
        import ctypes
        from ctypes import wintypes
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
        self.kernel.CreateMutexW.restype=wintypes.HANDLE
        self.kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        self.handle=self.kernel.CreateMutexW(None,False,'AulaColegioPruebas' if self.demo else 'AulaColegioDesktop')
        error=ctypes.get_last_error()
        if not self.handle:raise ctypes.WinError(error)
        if error!=183:return True
        user=ctypes.WinDLL('user32',use_last_error=True)
        callback=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
        user.EnumWindows.argtypes=[callback,wintypes.LPARAM]
        user.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
        user.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
        user.SetForegroundWindow.argtypes=[wintypes.HWND]
        title=('PRUEBAS · ' if self.demo else '')+TITLE
        def focus(handle,_):
            text=ctypes.create_unicode_buffer(512);user.GetWindowTextW(handle,text,512)
            if text.value==title:user.ShowWindow(handle,9);user.SetForegroundWindow(handle)
            return True
        user.EnumWindows(callback(focus),0)
        return False

    def __exit__(self,*_):
        if self.handle:self.kernel.CloseHandle(self.handle)


def read_desktop_config(directory):
    path=Path(directory)/'escritorio.json'
    if not path.exists():return None
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        if data.get('version')!=1 or data.get('mode') not in ('primary','client'):raise ValueError()
        return {'version':1,'mode':data['mode'],'remote_url':private_origin(data['remote_url']) if data['mode']=='client' else ''}
    except (OSError,ValueError,TypeError,AttributeError,KeyError):
        raise ValueError('La configuración de escritorio no es válida. Abre «Configurar Aula» en el menú Inicio.') from None


def write_desktop_config(directory,mode,origin=''):
    if mode != 'primary' or origin:
        raise ValueError('El acceso privado fue retirado. Usa el escritorio remoto de Windows.')
    origin=private_origin(origin) if origin else ''
    if mode=='client' and not origin:raise ValueError('Indica el enlace privado del colegio para conectarte.')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    # Never change the role/link while this PC is serving its real database.
    with DataLock(directory):
        if mode=='primary':
            (directory/'red.json').unlink(missing_ok=True)
        value={'version':1,'mode':mode,'remote_url':origin if mode=='client' else ''}
        path=directory/'escritorio.json';temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8');temporary.replace(path)
    return value


def configure(directory):
    from tkinter import messagebox
    messagebox.showinfo('Aula · uso local',
        'Aula funciona en esta PC. Configura el colegio dentro de Aula. '
        'Para soporte utiliza el escritorio remoto de Windows.')


class DesktopHost:
    """No request threads or data locks survive a normal desktop shutdown."""
    def __init__(self,directory,*,demo=False,port=None,demo_root=None):
        self.directory=Path(directory);self.demo=demo;self.port=port if port is not None else (8766 if demo else 8765)
        self.stack=ExitStack();self.server=None;self.thread=None;self.close_lock=threading.Lock()
        self.demo_root=demo_root

    def __enter__(self):
        try:
            directory=Path(self.stack.enter_context(DemoWorkspace(self.demo_root))) if self.demo else self.directory
            origin=''
            self.server=self.stack.enter_context(open_school(directory/'colegio.sqlite3',self.port,self.demo,origin))
            self.server.daemon_threads=False
            self.directory=directory
            self.thread=threading.Thread(target=self.server.serve_forever,name='Aula-Servidor')
            self.thread.start()
            self.url=f'http://127.0.0.1:{self.server.server_port}'
            return self
        except BaseException:self.stack.close();raise

    def close(self):
        with self.close_lock:
            if self.server is None:return
            try:
                self.server.shutdown()
                if self.thread:self.thread.join()
            finally:
                self.stack.close();self.server=None

    def __exit__(self,*_):self.close()


def backup_credentials_dialog(root,file):
    import tkinter as tk
    from tkinter import ttk
    with open(file,'rb') as saved:encrypted=saved.read(8).startswith(b'AULABK')
    if not encrypted:return None,'password'
    dialog=tk.Toplevel(root);dialog.title('Abrir respaldo cifrado');dialog.resizable(False,False)
    body=ttk.Frame(dialog,padding=24);body.pack(fill='both',expand=True)
    ttk.Label(body,text='Usa la contraseña de esta copia o su clave de recuperación.',wraplength=430).pack(anchor='w')
    kind=tk.StringVar(value='password');value=tk.StringVar()
    ttk.Radiobutton(body,text='Contraseña del respaldo',variable=kind,value='password').pack(anchor='w',pady=(12,4))
    ttk.Radiobutton(body,text='Clave de recuperación',variable=kind,value='recovery').pack(anchor='w')
    entry=ttk.Entry(body,textvariable=value,show='*',width=55);entry.pack(fill='x',pady=15);entry.focus_set()
    result=[]
    def accept():
        if value.get():result.append((value.get(),kind.get()));dialog.destroy()
    ttk.Button(body,text='Abrir copia',command=accept).pack(side='right')
    ttk.Button(body,text='Cancelar',command=dialog.destroy).pack(side='left')
    dialog.grab_set();root.wait_window(dialog)
    return result[0] if result else False


def probe_dialog():
    import tkinter as tk
    from tkinter import filedialog, messagebox
    from .backup_inspection import probe_backup
    root=tk.Tk();root.withdraw()
    try:
        file=filedialog.askopenfilename(parent=root,title='Probar respaldo sin restaurar',filetypes=[('Respaldo de Aula','*.sqlite3 *.aulabak')])
        if not file:return
        credentials=backup_credentials_dialog(root,file)
        if credentials is False:return
        s=probe_backup(file,*credentials);last=s['last_payment']
        protection='Advertencia: respaldo antiguo sin cifrar.' if s['unencrypted'] else 'Cifrado autenticado y comprobado.'
        messagebox.showinfo('Respaldo comprobado','Integridad y referencias: correctas.\nEsquema: '+str(s['schema'])+'\nAlumnos: '+str(s['students'])+'\nPagos: '+str(s['payments'])+'\nÚltimo recibo: '+(last['receipt']+' · '+last['paid_on'] if last else 'Sin pagos')+'\nSaldo pendiente USD: '+f"{s['balance_usd']/100:.2f}"+'\n\n'+s['creation_note']+'\n'+s.get('audit',{}).get('message','Bitácora antigua sin cadena de huellas.')+'\n'+protection+' No se modificó ni se restauró ninguna base.',parent=root)
    finally:root.destroy()


def restoration_review_dialog(root,review):
    import tkinter as tk
    from tkinter import ttk
    from tkinter.scrolledtext import ScrolledText
    from .restore import review_text
    from .documents import amount
    dialog=tk.Toplevel(root);dialog.title('Revisar restauración');dialog.resizable(True,True)
    dialog.geometry(f"820x{min(640,int(dialog.winfo_screenheight()*.8))}")
    body=ttk.Frame(dialog,padding=20);body.pack(fill='both',expand=True)
    ttk.Label(body,text='Revisa la base actual y el respaldo',font=('Segoe UI',14,'bold')).pack(anchor='w',pady=(0,12))
    text=ScrolledText(body,wrap='word',font=('Segoe UI',10));text.pack(fill='both',expand=True)
    value=review_text(review)
    for d in review['comparison']['details']:
        values=[d['number'],d['date'],d['person'],d['action']]
        if 'amount_usd' in d:values.extend([amount(d['amount_usd']),amount(d['received'],d['currency']),d['method'],d['reference']])
        value+='\n\n'+' · '.join(filter(None,values))
    text.insert('1.0',value);text.configure(state='disabled')
    result=[]
    buttons=ttk.Frame(body);buttons.pack(fill='x',pady=(12,0))
    ttk.Button(buttons,text='Cancelar',command=dialog.destroy).pack(side='left')
    def proceed():result.append(True);dialog.destroy()
    ttk.Button(buttons,text='Continuar a la confirmación',command=proceed).pack(side='right')
    dialog.grab_set();root.wait_window(dialog)
    return bool(result)


def recovery(directory,action):
    import tkinter as tk
    from tkinter import filedialog, simpledialog, messagebox
    from .restore import restore, preview_restore, review_text, last_restore
    from .backup_inspection import SEQUENCES
    from .reset_password import reset_password, list_administrators
    root=tk.Tk();root.withdraw()
    try:
        if action=='restore':
            file=filedialog.askopenfilename(parent=root,title='Selecciona un respaldo de Aula',filetypes=[('Respaldo de Aula','*.sqlite3 *.aulabak')])
            if not file:return
            credentials=backup_credentials_dialog(root,file)
            if credentials is False:return
            credential,kind=credentials
            review=preview_restore(file,directory,credential=credential,credential_kind=kind)
            if not restoration_review_dialog(root,review):return
            floors=None
            if review['requires_floor_review']:
                labels={'payments':'recibos R','expenses':'egresos E','students':'alumnos AL','guardians':'representantes','enrollment_documents':'constancias M'}
                floors={}
                for table in SEQUENCES:
                    number=simpledialog.askinteger('Revisar correlativos','No se pudo leer el último número de '+labels[table]+'.\nEscribe el mayor número ya utilizado. Si no lo conoces, cancela y solicita ayuda técnica.',minvalue=review['floors'][table],maxvalue=2147483646,parent=root)
                    if number is None:return
                    floors[table]=number
            answer=simpledialog.askstring('Confirmar restauración','Se conservará el estado actual y los informes de pérdida.\nEscribe '+review['confirmation']+':',parent=root)
            if answer!=review['confirmation']:return
            restore(file,directory,preview_hash=review['preview_hash'],confirmation=answer,emergency_floors=floors,credential=credential,credential_kind=kind)
            result=last_restore(directory)
            paths='\n'.join(result['reports']) or 'No hubo diferencias que perder.'
            messagebox.showinfo('Restauración completa','Puedes abrir Aula. Se aplicaron los correlativos revisados.\n\nInformes: '+paths+'\n\nCopia previa: '+(result['previous_backup'] or result['original_files']),parent=root)
        else:
            users=list_administrators(directory)
            if not users: raise ValueError('No hay administradores registrados en esta base.')
            names='\n'.join(f"{u['username']} · {u['name']}" for u in users)
            name=simpledialog.askstring('Recuperar administrador','Administradores de esta PC:\n'+names+'\n\nEscribe el usuario que deseas recuperar:',initialvalue=users[0]['username'] if len(users)==1 else '',parent=root)
            if not name:return
            password=simpledialog.askstring('Nueva contraseña','Contraseña nueva · mínimo 10 caracteres:',show='*',parent=root)
            if password is None:return
            repeat=simpledialog.askstring('Confirmar contraseña','Repite la contraseña nueva:',show='*',parent=root)
            if repeat is None:return
            if password!=repeat:raise ValueError('Las contraseñas no coinciden.')
            reset_password(directory,name,password)
            messagebox.showinfo('Contraseña recuperada','Puedes abrir Aula e iniciar sesión con tu nueva contraseña.',parent=root)
    finally:root.destroy()


def tray_icon(window,quit_app):
    import pystray
    from PIL import Image
    def show(*_):window.show();window.restore()
    icon=pystray.Icon('AulaColegio',Image.open(ROOT/'static'/'aula-app.png'),
                      'Colegio · aplicación activa',pystray.Menu(
                      pystray.MenuItem('Abrir Aula',show,default=True),
                      pystray.MenuItem('Salir y cerrar Aula',lambda *_:quit_app())))
    return icon


def launch_window(url,*,host=None,demo=False,storage=None,smoke=False):
    import webview
    from webview.menu import Menu,MenuAction
    webview.settings['ALLOW_DOWNLOADS']=True
    window=webview.create_window(('PRUEBAS · ' if demo else '')+TITLE,url,width=1280,height=820,min_size=(860,600),hidden=smoke)
    force_close=threading.Event();tray=None
    def quit_app():
        if force_close.is_set():return
        if host and host.server and host.server.access.origin and not window.create_confirmation_dialog(
                'Cerrar el sistema del colegio','Al salir, las laptops y el acceso desde casa se desconectarán. ¿Deseas cerrar Aula?'):return
        force_close.set();window.destroy()
    if host and not demo:
        tray=tray_icon(window,quit_app)
        tray.run_detached()
        def closing():
            if not force_close.is_set():window.hide();return False
        window.events.closing+=closing
    def monitor():
        if smoke:
            if not window.events.loaded.wait(60):force_close.set();window.destroy();return
            try:
                # Exercise the real Windows renderer, bundled JS and image.
                for _ in range(100):
                    ready=window.evaluate_js("Boolean(document.querySelector('form') && document.querySelector('.brand img,.brand .school-placeholder') && typeof api==='function')")
                    if ready:break
                    time.sleep(.1)
                if not ready:raise RuntimeError('La interfaz de escritorio no cargó el formulario, logo y JavaScript.')
                if demo:
                    window.evaluate_js("document.querySelector('form[data-endpoint=demo-login] button[type=submit]').click()")
                    for _ in range(100):
                        gate=window.evaluate_js("Boolean(document.querySelector('form[data-endpoint=confirm-rate]'))")
                        if gate:break
                        time.sleep(.1)
                    if not gate:raise RuntimeError('No se pudo entrar como administrador de prueba en la ventana.')
                if tray:
                    if closing() is not False:raise RuntimeError('El cierre de la ventana no conserva el servidor.')
                    window.show();window.restore()
                    if not host.thread.is_alive():raise RuntimeError('El servidor se detuvo al ocultar la ventana.')
                if not demo:
                    from .desktop_checks import renderer
                    renderer(window, host.directory)
                smoke_result.append(True)
            except Exception:logging.exception('Windows desktop smoke failed')
            finally:force_close.set();window.destroy()
        elif host:
            while not force_close.wait(.5):
                if not host.thread.is_alive():force_close.set();window.destroy();break
    smoke_result=[]
    try:
        menu=[Menu('Colegio',[MenuAction('Salir y cerrar Aula',quit_app)])]
        webview.start(monitor,gui='edgechromium',private_mode=demo or smoke,storage_path=str(storage) if storage else None,menu=menu)
    finally:
        force_close.set()
        if tray:tray.stop()
    if smoke and not smoke_result:raise RuntimeError('Falló la prueba de ventana Windows. Consulta el registro.')


def setup_logging(directory):
    logs=Path(directory)/'logs';logs.mkdir(parents=True,exist_ok=True)
    path=logs/f'escritorio-{datetime.now():%Y-%m-%d}.log'
    if getattr(sys,'frozen',False):
        stream=path.open('a',encoding='utf-8',buffering=1)
        sys.stdout=sys.stderr=stream
    logging.basicConfig(filename=path,level=logging.WARNING,format='%(asctime)s %(levelname)s %(message)s')
    return path


def self_test(demo=False):
    # A temporary base only; never inspect or initialize the owner's real data.
    from .branding import LOGO_FILE,pdf_logo
    from .pdf_fonts import font_data
    setup_logging(Path(tempfile.gettempdir())/'AulaColegio-Compilacion')
    with tempfile.TemporaryDirectory(prefix='aula-windows-smoke-') as temp:
        if not demo:
            from .desktop_checks import toolkit
            toolkit(temp)
        assert pdf_logo(LOGO_FILE)
        assert font_data('LiberationSans-Regular.ttf') and font_data('LiberationSans-Bold.ttf')
        with DesktopHost(temp,port=0,demo=demo,demo_root=Path(temp)/'pruebas') as host:
            disposable=host.directory
            # Exercise bundled cryptography + DPAPI only on this disposable smoke base.
            from .backup_keys import prepare,confirm
            from .backup_export import write_encrypted
            from .backup_inspection import probe_backup
            from .storage import consistent_backup
            pending,recovery=prepare(host.directory,'FICTICIO-ventana-cifrado-2026');confirm(host.directory,pending)
            snapshot=Path(temp)/'snapshot.sqlite3';cipher=Path(temp)/'snapshot.aulabak'
            consistent_backup(host.directory/'colegio.sqlite3',snapshot)
            write_encrypted(snapshot,cipher,host.directory)
            assert probe_backup(cipher,'FICTICIO-ventana-cifrado-2026')['integrity']=='ok'
            assert probe_backup(cipher,recovery,'recovery')['integrity']=='ok'
            launch_window(host.url,host=host,demo=demo,storage=host.directory/'webview',smoke=True)
        if demo and disposable.exists():raise RuntimeError('No se eliminaron los datos de prueba al cerrar la ventana.')


def main():
    parser=argparse.ArgumentParser(description='Aplicación de escritorio del colegio.')
    actions=parser.add_mutually_exclusive_group()
    for name in ('demo','configure','unlock-login','restore','reset-password','data-folder','test-backup','self-test','self-test-demo'):
        actions.add_argument('--'+name,action='store_true')
    args=parser.parse_args()
    directory=None
    try:
        if args.self_test or args.self_test_demo:
            self_test(demo=args.self_test_demo);return
        if args.test_backup:
            probe_dialog();return
        directory=data_directory();setup_logging(directory)
        if args.data_folder:directory.mkdir(parents=True,exist_ok=True);os.startfile(directory);return
        if args.restore or args.reset_password:
            current=read_desktop_config(directory)
            if current and current['mode']=='client':raise ValueError('Esta computadora se conecta al colegio. La recuperación se hace en la PC principal.')
            recovery(directory,'restore' if args.restore else 'password');return
        if args.unlock_login:
            from tkinter import Tk, simpledialog, messagebox
            from .local_login import issue
            root=Tk();root.withdraw()
            try:
                username=simpledialog.askstring('Desbloquear acceso local','Usuario de Administración:',parent=root)
                if not username:return
                password=simpledialog.askstring('Desbloquear acceso local','Contraseña actual:',show='*',parent=root)
                if password is None:return
                code=issue(directory,username,password)
                simpledialog.askstring('Código válido por dos minutos',
                    'Copia este código en el login de Aula. Se usa una sola vez:',initialvalue=code,parent=root)
            finally:root.destroy()
            return
        if args.configure:configure(directory);return
        demo=args.demo
        with WindowsInstance(demo) as first:
            if not first:return
            config={'mode':'primary'} if demo else read_desktop_config(directory)
            if not config:
                # A fresh desktop install works on this PC without a network wizard.
                config=write_desktop_config(directory,'primary')
            if config['mode']=='client':
                raise ValueError('Esta PC tenía acceso privado. Abre Aula en la PC del colegio mediante el escritorio remoto de Windows. No se creó una base local.')
            with DesktopHost(directory,demo=demo) as host:
                launch_window(host.url,host=host,demo=demo,storage=host.directory/'webview')
    except (Exception,SystemExit) as error:
        logging.exception('No se pudo iniciar o completar la operación de escritorio')
        if args.self_test or args.self_test_demo:raise
        import tkinter as tk
        from tkinter import messagebox
        root=tk.Tk();root.withdraw()
        from .restore_journal import RecoveryRequired
        title='Aula · Recuperación pendiente' if isinstance(error,RecoveryRequired) else 'Aula · no se pudo continuar'
        help_text='\n\nCarpeta de datos: '+str(directory) if isinstance(error,RecoveryRequired) else '\n\nRevisa la configuración o el registro en la carpeta de datos.'
        display_error=str(error)
        if args.restore or args.test_backup:
            import sqlite3
            if isinstance(error,sqlite3.Error):
                display_error='No se pudo leer o comprobar el respaldo. Puede estar dañado o no ser una copia de Aula. Conserva el archivo y selecciona otra copia verificada.'
        try:messagebox.showerror(title,display_error+help_text,parent=root)
        finally:root.destroy()


if __name__=='__main__':main()
