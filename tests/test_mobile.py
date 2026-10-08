import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from colegio.db import initialize
from colegio.server import SchoolServer


class MobileAssetsTests(unittest.TestCase):
    def test_public_installation_files_are_available_without_unlocking_api(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'colegio.sqlite3'
            initialize(path)
            server = SchoolServer(('127.0.0.1', 0), str(path))
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                client = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
                try:
                    for asset in ('/', '/mobile.js', '/manifest.webmanifest', '/service-worker.js',
                                  '/offline.html', '/icon-mobile-192.png', '/icon-mobile-512.png'):
                        client.request('GET', asset)
                        response = client.getresponse()
                        body = response.read()
                        self.assertEqual(response.status, 200, asset)
                        self.assertEqual(response.getheader('Cache-Control'), 'no-store')
                        if asset == '/manifest.webmanifest':
                            self.assertEqual(response.getheader('Content-Type'), 'application/manifest+json')
                            self.assertEqual(json.loads(body)['display'], 'standalone')
                        if asset.endswith('.png'):
                            self.assertTrue(body.startswith(b'\x89PNG'))
                    client.request('GET', '/api/state')
                    response = client.getresponse()
                    response.read()
                    self.assertEqual(response.status, 401)
                    client.request('GET', '/colegio.sqlite3')
                    response = client.getresponse()
                    response.read()
                    self.assertEqual(response.status, 404)
                finally:
                    client.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
