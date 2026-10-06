"""Run optional Playwright checks with an isolated database and server."""
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix='aula-e2e-') as temp:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        with (Path(temp) / 'server.log').open('w') as log:
            server = subprocess.Popen([sys.executable, '-u', '-m', 'colegio.server', '--port', str(port), '--data-dir', temp], cwd=root, stdout=log, stderr=log)
            try:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                ready = False
                for _ in range(50):
                    if server.poll() is not None:
                        raise RuntimeError('El servidor terminó antes de iniciar.')
                    try:
                        with opener.open(f'http://127.0.0.1:{port}/api/session', timeout=1):
                            ready = True
                        break
                    except OSError:
                        time.sleep(0.1)
                if not ready:
                    raise RuntimeError('El servidor no inició dentro del tiempo esperado.')
                runtime_env = dict(os.environ)
                runtime_env['AULA_TEST_URL'] = f'http://127.0.0.1:{port}'
                result = subprocess.run(['node', 'tests/browser.cjs'], cwd=root, env=runtime_env)
                if result.returncode:
                    print((Path(temp) / 'server.log').read_text(), file=sys.stderr)
                return result.returncode
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == '__main__':
    raise SystemExit(main())
