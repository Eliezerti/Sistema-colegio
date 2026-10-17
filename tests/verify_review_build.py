"""Exercise the actual draft entry before GUI launch, without any production data."""
import os
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from colegio import desktop


class ReviewEntryTests(unittest.TestCase):
    def test_entry_selects_separate_empty_data_root_before_desktop_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);production=root/'AulaColegio';production.mkdir()
            fixture=production/'colegio.sqlite3';fixture.write_bytes(b'FICTICIO no abrir')
            selected=[]
            with patch.dict(os.environ,{'LOCALAPPDATA':str(root)}),patch.object(desktop,'TITLE',desktop.TITLE),patch.object(desktop,'main',side_effect=lambda:selected.append(desktop.data_directory())):
                runpy.run_path(str(Path(__file__).resolve().parents[1]/'packaging/review_entry.py'),run_name='__main__')
                self.assertTrue(desktop.TITLE.startswith('BORRADOR'))
                self.assertEqual(selected,[root/'AulaRevisionIngresos'/'AulaColegio'])
                self.assertFalse(selected[0].exists())
            self.assertEqual(fixture.read_bytes(),b'FICTICIO no abrir')

    def test_missing_windows_root_stops_before_desktop_launch(self):
        with patch.dict(os.environ,clear=True),patch.object(desktop,'main') as launch:
            with self.assertRaises(RuntimeError):runpy.run_path(str(Path(__file__).resolve().parents[1]/'packaging/review_entry.py'),run_name='__main__')
            launch.assert_not_called()


if __name__=='__main__':unittest.main(verbosity=2)
