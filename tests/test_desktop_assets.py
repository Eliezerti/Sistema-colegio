import http.client
import tempfile
import threading
import unittest
from pathlib import Path

from colegio.db import initialize
from colegio.server import SchoolServer


class DesktopAssetsTests(unittest.TestCase):
    def test_responsive_assets_available_and_retired_phone_routes_absent(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'colegio.sqlite3'
            initialize(path)
            server = SchoolServer(('127.0.0.1', 0), str(path))
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                client = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
                try:
                    for asset in ('/', '/responsive.js', '/app.js', '/session.js', '/style.css'):
                        client.request('GET', asset)
                        response = client.getresponse()
                        body = response.read()
                        self.assertEqual(response.status, 200, asset)
                        self.assertEqual(response.getheader('Cache-Control'), 'no-store')
                        if asset == '/':
                            self.assertIn(b'/responsive.js', body)
                            self.assertNotIn(b'rel="manifest"', body)
                            self.assertNotIn(b'phone-install', body)
                    for asset in ('/mobile.js', '/manifest.webmanifest', '/service-worker.js',
                                  '/offline.html', '/icon-mobile-192.png', '/icon-mobile-512.png'):
                        client.request('GET', asset)
                        response = client.getresponse()
                        response.read()
                        self.assertEqual(response.status, 404, asset)
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
