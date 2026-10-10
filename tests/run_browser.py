"""Run optional Playwright checks with an isolated database and server."""
import os
import argparse
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--demo',action='store_true')
    mode.add_argument('--mobile',action='store_true')
    mode.add_argument('--phone',action='store_true')
    mode.add_argument('--directory',action='store_true')
    args=parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix='aula-e2e-') as temp:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        with (Path(temp) / 'server.log').open('w') as log:
            command=[sys.executable, '-u', '-m', 'colegio.server', '--port', str(port)]
            command+=['--demo'] if args.demo else ['--data-dir',temp]
            runtime_env=dict(os.environ)
            if args.demo or args.phone:runtime_env.update(TMPDIR=temp,TEMP=temp,TMP=temp)
            if args.phone:
                sys.path.insert(0,str(root))
                from colegio.phone_demo import local_addresses
                addresses=local_addresses()
                if not addresses:raise RuntimeError('La prueba de navegador Wi-Fi necesita una interfaz IPv4 privada.')
                runtime_env['AULA_PHONE_ADDRESS']=addresses[0]
                runtime_env['AULA_PHONE_BACKEND_PORT']=str(port)
                command=[sys.executable,'-u','-c',
                    "import os; from colegio.desktop import DesktopHost; from colegio.phone_demo import PhoneDemo; "
                    "exec(\"with DesktopHost('.',demo=True,port=int(os.environ['AULA_PHONE_BACKEND_PORT'])) as host, PhoneDemo(host.server,os.environ['AULA_PHONE_ADDRESS'],0) as phone:\\n print('PHONE-DEMO',phone.origin,phone.pin,flush=True)\\n while host.thread.is_alive(): host.thread.join(.5)\")"]
            server = subprocess.Popen(command, cwd=root, env=runtime_env, stdout=log, stderr=log)
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
                runtime_env['AULA_TEST_URL'] = f'http://127.0.0.1:{port}'
                if args.phone:
                    line=next(line for line in (Path(temp)/'server.log').read_text().splitlines() if line.startswith('PHONE-DEMO '))
                    _,runtime_env['AULA_TEST_URL'],runtime_env['AULA_TEST_PIN']=line.split()
                script = 'tests/directory_browser.cjs' if args.directory else 'tests/demo_browser.cjs' if args.demo else 'tests/mobile_browser.cjs' if args.mobile or args.phone else 'tests/browser.cjs'
                result = subprocess.run(['node', script], cwd=root, env=runtime_env)
                if result.returncode:
                    print((Path(temp) / 'server.log').read_text(), file=sys.stderr)
                elif args.demo or args.phone:
                    if server.wait(timeout=10)!=0:raise RuntimeError('El servidor de prueba no cerró correctamente.')
                    if list((Path(temp)/'AulaColegio-Pruebas').glob('prueba-*')):
                        raise RuntimeError('No se eliminaron los registros temporales al cerrar la última pestaña.')
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
