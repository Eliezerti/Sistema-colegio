"""Real Tk widgets on Windows; core/HTTP/browser checks run independently on Linux."""
import os
import sys
import gc
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


@unittest.skipUnless(os.name=='nt','Necesita ventanas nativas de Windows y Tk.')
class RestoreWindowsUITests(unittest.TestCase):
    def test_scrollable_review_and_independent_probe_do_not_need_an_active_database(self):
        # The actual local tool owns its Tk interpreter in a separate process.
        # Do the same here: ScrolledText/callback cycles must never survive until
        # a later HTTP worker's garbage collection destroys Tk on that thread.
        if os.environ.get('AULA_NATIVE_RESTORE_TEST_CHILD')!='1':
            env=dict(os.environ,AULA_NATIVE_RESTORE_TEST_CHILD='1',PYTHONFAULTHANDLER='1')
            result=subprocess.run([sys.executable,'-m','unittest',
                'tests.test_restore_windows_ui.RestoreWindowsUITests', '-v'],
                cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True,
                encoding='utf-8',errors='replace',timeout=90)
            self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
            self.assertIn('Ran 1 test',result.stderr)
            return
        self.addCleanup(gc.collect)  # collect cycles on the Tk owner thread
        import tkinter as tk
        from colegio.desktop import restoration_review_dialog,main
        from colegio.restore import preview_restore
        source=Path(__file__).parent/'fixtures/restore/desktop-1.0.13.sqlite3'
        with tempfile.TemporaryDirectory() as directory:
            review=preview_restore(source,directory)
            root=tk.Tk();root.withdraw()
            def walk(widget):
                for child in widget.winfo_children():
                    yield child
                    yield from walk(child)
            def accept():
                for widget in walk(root):
                    if widget.winfo_class()=='TButton' and widget.cget('text')=='Continuar a la confirmación':
                        widget.invoke();return
            def timeout():
                for widget in root.winfo_children():
                    if isinstance(widget,tk.Toplevel):widget.destroy()
            try:
                root.after(300,accept);root.after(5000,timeout)
                self.assertTrue(restoration_review_dialog(root,review))
            finally:root.destroy()
            with patch('sys.argv',['Aula','--test-backup']),patch('tkinter.filedialog.askopenfilename',return_value=str(source)),patch('tkinter.messagebox.showinfo') as shown,patch('tkinter.messagebox.askyesno',return_value=False),patch('colegio.desktop.data_directory',side_effect=AssertionError('No debe abrir la base activa')):
                main()
                self.assertIn('Integridad y referencias: correctas',shown.call_args.args[1])
                self.assertIn('R-000001',shown.call_args.args[1])
            damaged=Path(directory)/'danado.sqlite3';damaged.write_bytes(b'no es una base')
            with patch('sys.argv',['Aula','--test-backup']),patch('tkinter.filedialog.askopenfilename',return_value=str(damaged)),patch('tkinter.messagebox.showerror') as shown:
                main()
                self.assertIn('Puede estar dañado o no ser una copia de Aula',shown.call_args.args[1])
                self.assertNotIn('file is not a database',shown.call_args.args[1])
