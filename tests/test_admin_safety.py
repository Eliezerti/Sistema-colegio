from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import test_system
from colegio.db import connect, local_today, ValidationError


class AdministrativeSafetyTests(unittest.TestCase):
    setUp = test_system.SystemTests.setUp
    tearDown = test_system.SystemTests.tearDown
    request = test_system.SystemTests.request
    student_data = test_system.SystemTests.student_data
    payment = test_system.SystemTests.payment





    def reset_data(self):
        return dict(preview_hash=self.request('reset-preview')['preview_hash'],confirmation='VACIAR REGISTROS',password='Una-clave-segura')





    def test_demo_endpoints_cannot_enter_or_erase_production(self):
        self.request('demo-login',{},status=403)
        self.request('demo-presence',{'token':'incorrecto','client':'tab','action':'close'},status=403)
        self.request('demo-exit',{},status=403)
        self.assertEqual(len(self.request('state')['students']),1)
