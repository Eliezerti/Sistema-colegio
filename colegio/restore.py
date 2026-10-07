import argparse
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from contextlib import closing

from .server import ROOT
from .storage import DataLock, consistent_backup


def restore(backup, directory):
    backup = Path(backup).resolve()
    directory = Path(directory).resolve()
    target = directory / 'colegio.sqlite3'
    if not backup.is_file() or backup == target:
        raise ValueError('Selecciona un archivo de respaldo distinto de la base activa.')
    with closing(sqlite3.connect(backup.as_uri() + '?mode=ro', uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('El respaldo tiene errores de integridad.')
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        expected = {'settings','students','guardians','grades','charges','payments','allocations',
                    'expenses','employees','users','sessions','exchange_rates','audit'}
        columns = {r[1] for r in db.execute('PRAGMA table_info(payments)')}
        if not expected <= tables or not {'receipt_snapshot','exchange_rate','received_amount'} <= columns:
            raise ValueError('El archivo no es un respaldo compatible de Aula.')
        if db.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('El respaldo contiene referencias inválidas.')
    with DataLock(directory):
        with tempfile.TemporaryDirectory(dir=directory) as temp:
            temp = Path(temp)
            replacement = Path(temp) / 'restaurado.sqlite3'
            # Prepare a checked replacement before touching the current database.
            consistent_backup(backup, replacement)
            originals = [target.with_name(target.name + suffix) for suffix in ('', '-wal', '-shm', '-journal')]
            originals = [file for file in originals if file.exists()]
            if originals:
                stamp = f'{datetime.now():%Y%m%d-%H%M%S-%f}'
                backups = directory / 'backups'
                backups.mkdir(parents=True, exist_ok=True)
                raw = temp / 'estado-original'
                raw.mkdir()
                # Preserve exact files before SQLite attempts to read a damaged DB.
                for original in originals:
                    shutil.copy2(original, raw / original.name)
                previous = temp / 'anterior.sqlite3'
                try:
                    if not target.exists():
                        raise sqlite3.DatabaseError('Falta la base principal; se conservan sus archivos auxiliares.')
                    consistent_backup(target, previous)
                except (sqlite3.DatabaseError, RuntimeError):
                    # A corrupt current DB must not prevent restoring a valid backup.
                    # This is forensic preservation, not a usable SQLite backup.
                    os.replace(raw, backups / f'danado-antes-restauracion-{stamp}')
                else:
                    os.replace(previous, backups / f'antes-restauracion-{stamp}.sqlite3')
            for suffix in ('-wal','-shm','-journal'):
                target.with_name(target.name + suffix).unlink(missing_ok=True)
            os.replace(replacement, target)
    return target


def main():
    parser = argparse.ArgumentParser(description='Restaurar un respaldo de Aula con el sistema cerrado.')
    parser.add_argument('--data-dir', default=str(ROOT / 'data'))
    parser.add_argument('--backup')
    args = parser.parse_args()
    backup = args.backup
    if not backup:
        try:
            import tkinter as tk
            from tkinter.filedialog import askopenfilename
            root = tk.Tk()
            root.withdraw()
            backup = askopenfilename(title='Selecciona el respaldo de Aula', filetypes=[('Base de datos Aula','*.sqlite3')])
            root.destroy()
        except Exception:
            raise SystemExit('No se pudo abrir el selector. Usa --backup "ruta del respaldo.sqlite3".')
    if not backup:
        return
    print(f'Se restaurará: {backup}\nDestino: {Path(args.data_dir).resolve()}')
    print('Se conservará una copia del estado actual antes de reemplazarlo, incluso si la base está dañada.')
    if input('Escribe RESTAURAR para continuar: ').strip() != 'RESTAURAR':
        print('Restauración cancelada.')
        return
    try:
        print(f'Respaldo restaurado correctamente: {restore(backup, args.data_dir)}')
    except (ValueError, RuntimeError, sqlite3.Error, OSError) as error:
        raise SystemExit(f'No se restauró: {error}')


if __name__ == '__main__':
    main()
