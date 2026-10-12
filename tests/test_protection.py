import json
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from colegio.protection import (ProtectionMonitor, classify_acl, classify_bitlocker,
                                inspect_protection, unknown_protection)


USER = 'S-1-5-21-1234-5678-9012-1001'


class ProtectionTests(unittest.TestCase):
    def test_bitlocker_only_reports_active_when_complete_and_enabled(self):
        self.assertEqual(classify_bitlocker({'protection': 1, 'volume': 1})['status'], 'active')
        self.assertEqual(classify_bitlocker({'protection': 0, 'volume': 1})['status'], 'inactive')
        self.assertEqual(classify_bitlocker({'protection': 0, 'volume': 0})['status'], 'inactive')
        self.assertEqual(classify_bitlocker({'protection': 1, 'volume': 2})['status'], 'incomplete')
        for data in (None, {}, {'protection': 2, 'volume': 1}, {'protection': '1', 'volume': 1},
                     {'protection': True, 'volume': 1}, {'protection': 1, 'volume': 99}):
            with self.subTest(data=data):
                self.assertEqual(classify_bitlocker(data)['label'], 'No se pudo comprobar')

    def test_acl_flags_other_users_and_groups_without_modifying_permissions(self):
        rules = [{'sid': sid, 'type': 0, 'rights': 2032127}
                 for sid in (USER, 'S-1-5-18', 'S-1-5-32-544')]
        self.assertEqual(classify_acl({'user': USER, 'rules': rules})['status'], 'restricted')
        for sid in ('S-1-1-0', 'S-1-5-11', 'S-1-5-32-545', 'S-1-5-21-OTHER-USER'):
            with self.subTest(sid=sid):
                shared = rules+[{'sid': sid, 'type': 0, 'rights': 1}]
                self.assertEqual(classify_acl({'user': USER, 'rules': shared})['status'], 'shared')

    def test_acl_unknown_for_incomplete_or_complex_rules(self):
        for data in (None, {}, {'user': USER, 'rules': []},
                     {'user': USER, 'rules': [{'sid': USER, 'type': 1, 'rights': 1}]},
                     {'user': USER, 'rules': [{'sid': USER, 'type': 0, 'rights': 'FullControl'}]},
                     {'user': USER, 'rules': [{'sid': 'S-1-5-18', 'type': 0, 'rights': 1}]}):
            with self.subTest(data=data):
                self.assertEqual(classify_acl(data)['label'], 'No se pudo comprobar')

    def test_non_windows_is_explicitly_unknown_and_runs_no_command(self):
        with patch('colegio.protection.os', SimpleNamespace(name='posix')), patch('colegio.protection.subprocess.run') as run:
            result = inspect_protection('.')
        run.assert_not_called()
        self.assertEqual(result['bitlocker']['label'], 'No se pudo comprobar')
        self.assertIn('requiere Windows', result['acl']['detail'])

    def windows_check(self, command=None, exception=None):
        with tempfile.TemporaryDirectory(prefix="aula-árbol-'-$-") as directory:
            fake_os = SimpleNamespace(name='nt', environ={'SystemRoot': r'C:\Windows'})
            with patch('colegio.protection.os', fake_os), patch('colegio.protection.subprocess.run',
                return_value=command, side_effect=exception) as run:
                result = inspect_protection(directory)
            arguments, options = run.call_args
            self.assertNotIn(directory, arguments[0][-1])
            self.assertEqual(options['env']['AULA_PROTECTION_DIRECTORY'], str(Path(directory).resolve()))
            self.assertEqual(options['timeout'], 8)
            self.assertNotIn('shell', options)
            return result

    def test_windows_output_is_parsed_and_path_is_not_executable_code(self):
        data = {'acl': {'user': USER, 'rules': [{'sid': USER, 'type': 0, 'rights': 1}]},
                'bitlocker': {'protection': 1, 'volume': 1}}
        result = self.windows_check(SimpleNamespace(returncode=0, stdout='\ufeff'+json.dumps(data)))
        self.assertEqual(result['acl']['status'], 'restricted')
        self.assertEqual(result['bitlocker']['status'], 'active')

    def test_command_failure_timeout_missing_tools_and_invalid_output_are_unknown(self):
        cases = [(SimpleNamespace(returncode=1, stdout=''), None),
                 (SimpleNamespace(returncode=0, stdout='not-json'), None),
                 (SimpleNamespace(returncode=0, stdout='[]'), None),
                 (SimpleNamespace(returncode=0, stdout='{"acl":null,"bitlocker":null}'), None),
                 (None, FileNotFoundError('powershell.exe')),
                 (None, subprocess.TimeoutExpired('powershell.exe', 8))]
        for command, exception in cases:
            with self.subTest(command=command, exception=exception):
                result = self.windows_check(command, exception)
                self.assertEqual(result['acl']['label'], 'No se pudo comprobar')
                self.assertEqual(result['bitlocker']['label'], 'No se pudo comprobar')

    def test_acl_and_bitlocker_fail_independently(self):
        result = self.windows_check(SimpleNamespace(returncode=0,
            stdout='{"acl":null,"bitlocker":{"protection":1,"volume":1}}'))
        self.assertEqual(result['acl']['status'], 'unknown')
        self.assertEqual(result['bitlocker']['status'], 'active')

    def test_background_check_does_not_block_or_run_on_every_request(self):
        entered, release = threading.Event(), threading.Event()
        def inspect(directory):
            entered.set()
            release.wait(timeout=2)
            return unknown_protection('Resultado de prueba')
        monitor = ProtectionMonitor('.')
        with patch('colegio.protection.inspect_protection', side_effect=inspect) as check:
            try:
                self.assertEqual(monitor.snapshot()['acl']['status'], 'unknown')
                self.assertTrue(entered.wait(timeout=1))
                for _ in range(10):
                    monitor.snapshot()
                self.assertEqual(check.call_count, 1)
                release.set()
                monitor.worker.join(timeout=2)
                self.assertIn('checked_at', monitor.snapshot())
                self.assertEqual(check.call_count, 1)
                monitor.last_check -= 301
                monitor.snapshot()
                monitor.worker.join(timeout=2)
                self.assertEqual(check.call_count, 2)
            finally:
                release.set()
                monitor.close()
        monitor.snapshot()
        self.assertEqual(check.call_count, 2)

    def test_background_exception_never_reports_protected(self):
        monitor = ProtectionMonitor('.')
        with patch('colegio.protection.inspect_protection', side_effect=RuntimeError('Unexpected check error')):
            monitor.snapshot()
            monitor.close()
        self.assertEqual(monitor.snapshot()['bitlocker']['status'], 'unknown')
