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
from .network import private_origin, load_config, save_config
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
    if mode not in ('primary','client'):raise ValueError('Selecciona el tipo de computadora.')
    origin=private_origin(origin) if origin else ''
    if mode=='client' and not origin:raise ValueError('Indica el enlace privado del colegio para conectarte.')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    # Never change the role/link while this PC is serving its real database.
    with DataLock(directory):
        if mode=='primary':
            if origin:save_config(directory,origin)
            else:(directory/'red.json').unlink(missing_ok=True)
        value={'version':1,'mode':mode,'remote_url':origin if mode=='client' else ''}
        path=directory/'escritorio.json';temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8');temporary.replace(path)
    return value


def configure(directory):
    import tkinter as tk
    from tkinter import ttk, messagebox
    try:current=read_desktop_config(directory) or {'mode':'primary','remote_url':''}
    except ValueError:current={'mode':'primary','remote_url':''}
    origin=current['remote_url']
    if current['mode']=='primary' and (Path(directory)/'red.json').exists():
        try:origin=load_config(Path(directory)/'red.json')
        except ValueError:origin=''
    root=tk.Tk();root.title('Configurar Aula');root.resizable(False,False)
    body=ttk.Frame(root,padding=24);body.pack(fill='both',expand=True)
    ttk.Label(body,text=TITLE,font=('Segoe UI',14,'bold'),wraplength=490).pack(anchor='w',pady=(0,15))
    ttk.Label(body,text='¿Cómo usarás esta computadora?',font=('Segoe UI',11,'bold')).pack(anchor='w')
    mode=tk.StringVar(value=current['mode']);url=tk.StringVar(value=origin);result=[]
    ttk.Radiobutton(body,text='PC principal · aquí se guardan los datos del colegio',variable=mode,value='primary').pack(anchor='w',pady=8)
    ttk.Radiobutton(body,text='Conectarme al colegio · desde una laptop o desde casa',variable=mode,value='client').pack(anchor='w',pady=(0,16))
    ttk.Label(body,text='Enlace privado del colegio · HTTPS').pack(anchor='w')
    ttk.Entry(body,textvariable=url,width=65).pack(fill='x',pady=6)
    ttk.Label(body,text='En la PC principal puedes dejarlo vacío para uso local.\nPara compartirlo, configura Tailscale Serve y copia su enlace.\nLas otras computadoras deben tener Tailscale conectado.',wraplength=490).pack(anchor='w',pady=(0,18))
    def save():
        try:result.append(write_desktop_config(directory,mode.get(),url.get().strip()))
        except (ValueError,RuntimeError,OSError) as error:messagebox.showerror('Revisa la configuración',str(error),parent=root);return
        root.destroy()
    buttons=ttk.Frame(body);buttons.pack(fill='x')
    ttk.Button(buttons,text='Cancelar',command=root.destroy).pack(side='left')
    ttk.Button(buttons,text='Guardar configuración',command=save).pack(side='right')
    root.mainloop()
    return result[0] if result else None


class DesktopHost:
    """No request threads or data locks survive a normal desktop shutdown."""
    def __init__(self,directory,*,demo=False,port=None,demo_root=None):
        self.directory=Path(directory);self.demo=demo;self.port=port if port is not None else (8766 if demo else 8765)
        self.stack=ExitStack();self.server=None;self.thread=None;self.close_lock=threading.Lock()
        self.demo_root=demo_root

    def __enter__(self):
        try:
            directory=Path(self.stack.enter_context(DemoWorkspace(self.demo_root))) if self.demo else self.directory
            origin=load_config(directory/'red.json') if not self.demo and (directory/'red.json').exists() else ''
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


def recovery(directory,action):
    import tkinter as tk
    from tkinter import filedialog, simpledialog, messagebox
    from .restore import restore
    from .reset_password import reset_password, list_administrators
    root=tk.Tk();root.withdraw()
    try:
        if action=='restore':
            file=filedialog.askopenfilename(parent=root,title='Selecciona un respaldo de Aula',filetypes=[('Respaldo de Aula','*.sqlite3')])
            if not file:return
            answer=simpledialog.askstring('Restaurar respaldo','Cierra Aula en la PC principal. Se conservará un respaldo del estado actual.\nEscribe RESTAURAR para reemplazar los datos con la copia seleccionada:',parent=root)
            if answer!='RESTAURAR':return
            restore(file,directory)
            messagebox.showinfo('Restauración completa','Puedes abrir Aula. Se han restaurado los datos y los usuarios del respaldo.',parent=root)
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


def launch_window(url,*,host=None,demo=False,storage=None,smoke=False,smoke_phone=False):
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
                if smoke_phone and not window.evaluate_js("Boolean(document.querySelector('.phone-demo-info .phone-demo-code'))"):
                    raise RuntimeError('No se mostró la dirección y el código para la prueba en teléfono.')
                if tray:
                    if closing() is not False:raise RuntimeError('El cierre de la ventana no conserva el servidor.')
                    window.show();window.restore()
                    if not host.thread.is_alive():raise RuntimeError('El servidor se detuvo al ocultar la ventana.')
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


def self_test(demo=False,phone=False):
    # A temporary base only; never inspect or initialize the owner's real data.
    from .branding import LOGO_FILE,pdf_logo
    from .pdf_fonts import font_data
    setup_logging(Path(tempfile.gettempdir())/'AulaColegio-Compilacion')
    demo=demo or phone
    with tempfile.TemporaryDirectory(prefix='aula-windows-smoke-') as temp:
        assert pdf_logo(LOGO_FILE)
        assert font_data('LiberationSans-Regular.ttf') and font_data('LiberationSans-Bold.ttf')
        with DesktopHost(temp,port=0,demo=demo,demo_root=Path(temp)/'pruebas') as host:
            disposable=host.directory
            if phone:
                from .phone_demo import PhoneDemo
                with PhoneDemo(host.server,'127.0.0.1',0) as gateway:
                    launch_window(gateway.desktop_url,host=host,demo=True,storage=host.directory/'webview',smoke=True,smoke_phone=True)
            else:launch_window(host.url,host=host,demo=demo,storage=host.directory/'webview',smoke=True)
        if demo and disposable.exists():raise RuntimeError('No se eliminaron los datos de prueba al cerrar la ventana.')


def choose_phone_address():
    import tkinter as tk
    from tkinter import ttk
    from .phone_demo import local_addresses
    addresses=local_addresses()
    if not addresses:raise ValueError('Conecta esta PC al Wi-Fi y vuelve a abrir «Probar en teléfono».')
    root=tk.Tk();root.title('Probar en teléfono');root.resizable(False,False)
    body=ttk.Frame(root,padding=24);body.pack(fill='both',expand=True)
    ttk.Label(body,text='Prueba Aula desde tu teléfono',font=('Segoe UI',16,'bold')).pack(anchor='w')
    ttk.Label(body,text='Conecta la PC y el teléfono al mismo Wi-Fi.\nEsta prueba usa datos temporales y no modifica la base real.\nAl abrir, Aula mostrará la dirección y el código para el teléfono.',wraplength=470).pack(anchor='w',pady=15)
    ttk.Label(body,text='Dirección de la conexión Wi-Fi de esta PC').pack(anchor='w')
    address=tk.StringVar(value=addresses[0])
    ttk.Combobox(body,textvariable=address,values=addresses,state='readonly',width=32).pack(anchor='w',pady=8)
    ttk.Label(body,text='Si hay varias conexiones, elige la del Wi-Fi, no la de una VPN.\nSi Windows pregunta, permite el acceso a redes privadas.',wraplength=470).pack(anchor='w',pady=10)
    result=[]
    def start():result.append(address.get());root.destroy()
    ttk.Button(body,text='Crear prueba por Wi-Fi',command=start).pack(anchor='e',pady=10)
    root.mainloop()
    return result[0] if result else None


def main():
    parser=argparse.ArgumentParser(description='Aplicación de escritorio del colegio.')
    actions=parser.add_mutually_exclusive_group()
    for name in ('demo','demo-phone','configure','restore','reset-password','data-folder','self-test','self-test-demo','self-test-phone'):
        actions.add_argument('--'+name,action='store_true')
    args=parser.parse_args()
    directory=None
    try:
        if args.self_test or args.self_test_demo or args.self_test_phone:
            self_test(demo=args.self_test_demo,phone=args.self_test_phone);return
        directory=data_directory();setup_logging(directory)
        if args.data_folder:directory.mkdir(parents=True,exist_ok=True);os.startfile(directory);return
        if args.restore or args.reset_password:
            current=read_desktop_config(directory)
            if current and current['mode']=='client':raise ValueError('Esta computadora se conecta al colegio. La recuperación se hace en la PC principal.')
            recovery(directory,'restore' if args.restore else 'password');return
        if args.configure:configure(directory);return
        demo=args.demo or args.demo_phone
        with WindowsInstance(demo) as first:
            if not first:return
            config={'mode':'primary'} if demo else read_desktop_config(directory)
            if not config:
                # A fresh desktop install works on this PC without a network wizard.
                config=write_desktop_config(directory,'primary')
            if config['mode']=='client':
                launch_window(config['remote_url'],storage=directory/'webview-cliente');return
            address=choose_phone_address() if args.demo_phone else None
            if args.demo_phone and not address:return
            with DesktopHost(directory,demo=demo) as host:
                if args.demo_phone:
                    from .phone_demo import PhoneDemo
                    with PhoneDemo(host.server,address) as phone:
                        launch_window(phone.desktop_url,host=host,demo=True,storage=host.directory/'webview')
                else:launch_window(host.url,host=host,demo=demo,storage=host.directory/'webview')
    except (Exception,SystemExit) as error:
        logging.exception('No se pudo iniciar o completar la operación de escritorio')
        if args.self_test or args.self_test_demo or args.self_test_phone:raise
        import tkinter as tk
        from tkinter import messagebox
        root=tk.Tk();root.withdraw()
        try:messagebox.showerror('Aula · no se pudo continuar',str(error)+'\n\nRevisa la configuración o el registro en la carpeta de datos.',parent=root)
        finally:root.destroy()


if __name__=='__main__':main()
