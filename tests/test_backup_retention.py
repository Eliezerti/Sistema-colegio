import os
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from colegio.backup_retention import retain_backups
from colegio.db import connect, initialize
from colegio.storage import automatic_backup


class RetentionTests(unittest.TestCase):
    def test_retention_failure_does_not_stop_verified_copy_to_second_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'colegio.sqlite3';initialize(path)
            destination=Path(folder)/'second'
            with closing(connect(path)) as db,db:
                db.execute("UPDATE settings SET value=? WHERE key='backup_directory'",(str(destination),))
            with patch('colegio.backup_retention.atomic_json',side_effect=OSError('Inventory unavailable')):
                status=automatic_backup(path)
            self.assertFalse(status['local_error'])
            self.assertFalse(status['secondary_error'])
            self.assertTrue(status['retention_error'])
            self.assertTrue(status['secondary_retention_error'])
            self.assertTrue((destination/Path(status['local_path']).name).is_file())

    def test_future_file_names_and_mtimes_do_not_delete_recent_published_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder)
            future=[]
            for index in range(5):
                path=directory/f'aula-auto-20990101-000000-{index:06d}.sqlite3'
                path.write_bytes(b'future');os.utime(path,(4070908800,4070908800))
                retain_backups(directory,path,'aula-auto-*.sqlite3',3);future.append(path)
            recent=[]
            for index in range(4):
                path=directory/f'aula-auto-20261011-000000-{index:06d}.sqlite3'
                path.write_bytes(b'corrected');os.utime(path,(1791720000,1791720000))
                retain_backups(directory,path,'aula-auto-*.sqlite3',3);recent.append(path)
                self.assertTrue(path.exists())
            self.assertEqual(set(directory.glob('*.sqlite3')),set(recent[-3:]))

    def test_daily_and_auto_limits_are_independent_and_manual_backups_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder);manual=directory/'antes-restauracion-1.sqlite3';manual.write_bytes(b'manual')
            for index in range(5):
                for prefix in ('colegio','aula-auto'):
                    path=directory/f'{prefix}-{index}.sqlite3';path.write_bytes(b'copy')
                    retain_backups(directory,path,prefix+'-*.sqlite3',2)
            self.assertEqual(len(list(directory.glob('colegio-*'))),2)
            self.assertEqual(len(list(directory.glob('aula-auto-*'))),2)
            self.assertTrue(manual.exists())

    def test_corrupt_inventory_and_write_failure_never_authorize_deletion(self):
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder)
            for index in range(4):(directory/f'colegio-{index}.sqlite3').write_bytes(b'copy')
            history=directory/'.aula-backup-history.json';history.write_text('broken')
            with self.assertRaises(OSError):retain_backups(directory,directory/'colegio-3.sqlite3','colegio-*',2)
            self.assertEqual(len(list(directory.glob('*.sqlite3'))),4)
            history.unlink()
            with patch('colegio.backup_retention.atomic_json',side_effect=OSError('Disk full')):
                with self.assertRaises(OSError):retain_backups(directory,directory/'colegio-3.sqlite3','colegio-*',2)
            self.assertEqual(len(list(directory.glob('*.sqlite3'))),4)
