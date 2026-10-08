"""An explicitly enabled Wi-Fi gateway for a disposable trial, never a real base."""
import argparse
import http.client
import ipaddress
import secrets
import socket
import threading
import time
import webbrowser
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit, urlencode

PRIVATE = tuple(ipaddress.ip_network(net) for net in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
HOP_HEADERS = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
               'te', 'trailer', 'transfer-encoding', 'upgrade', 'content-length'}


def private_address(value, *, loopback=False):
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError:
        raise ValueError('Selecciona la dirección IPv4 de la conexión Wi-Fi de esta PC.') from None
    if not any(address in net for net in PRIVATE) and not (loopback and address.is_loopback):
        raise ValueError('La prueba de teléfono solo acepta direcciones de una red local privada.')
    return str(address)


def local_addresses():
    found = set()
    try:
        for result in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            try: found.add(private_address(result[4][0]))
            except ValueError: pass
    except OSError: pass
    # Choosing a route does not send a packet or require a remote service.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(('192.168.255.254', 1))
            found.add(private_address(sock.getsockname()[0]))
    except (OSError, ValueError): pass
    return sorted(found)


class PhoneDemo(ThreadingHTTPServer):
    daemon_threads = False

    def __init__(self, backend, address, port=8767):
        if not backend.demo or backend.server_address[0] != '127.0.0.1':
            raise ValueError('Solo se puede compartir una sesión de prueba temporal. La base real queda local.')
        address = private_address(address, loopback=True)
        self.backend_port = backend.server_port
        self.pin = f'{secrets.randbelow(1_000_000):06d}'
        self.pair_token = secrets.token_urlsafe(32)
        self.attempts = {}
        self.pair_lock = threading.Lock()
        self.thread = None
        super().__init__((address, port), PhoneHandler)
        self.origin = f'http://{address}:{self.server_port}'
        self.host = f'{address}:{self.server_port}'
        self.cookie_name = f'aula_phone_trial_{self.server_port}'

    @property
    def desktop_url(self):
        return f'http://127.0.0.1:{self.backend_port}/?' + urlencode({'phone_url': self.origin, 'phone_code': self.pin})

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(15)
        return connection, address

    def __enter__(self):
        self.thread = threading.Thread(target=self.serve_forever, name='Aula-Prueba-Telefono')
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.shutdown()
        if self.thread: self.thread.join()
        self.server_close()


class PhoneHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Pairing codes, cookies and form values must not enter logs.

    def respond(self, status, body, headers=()):
        if isinstance(body, str): body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        for name, value in headers: self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def pair_page(self, error=''):
        return '''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Probar Aula en teléfono</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f4f6f1;color:#19302e;font:16px/1.6 system-ui;padding:24px;min-height:100vh;display:grid;place-items:center}main{background:white;border:1px solid #e4e9e3;border-radius:18px;padding:28px;max-width:420px}h1{font-size:25px;line-height:1.3}small{color:#61726b}label{display:block;margin-top:24px}input,button{width:100%;padding:14px;font:inherit;border-radius:9px;border:1px solid #dce3d9;margin-top:8px}input{font-size:24px;letter-spacing:8px;text-align:center}button{background:#356e57;color:white;font-weight:600}.error{color:#ad493d}</style>
<main><small>UNIDAD EDUCATIVA COLEGIO ALEJANDRO VON HUMBOLDT</small><h1>Prueba Aula en tu teléfono</h1><p>Escribe el código que aparece en la PC. Ambos equipos deben estar conectados al mismo Wi-Fi.</p><form method="post" action="/pair"><label for="pin">Código de 6 dígitos</label><input id="pin" name="pin" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" required autocomplete="off"><button type="submit">Entrar a la prueba</button></form><p class="error">''' + error + '''</p><small>Datos temporales. Esta prueba no modifica los registros reales del colegio.</small></main></html>'''

    def do_GET(self): self.handle_phone(False)
    def do_POST(self): self.handle_phone(True)

    def handle_phone(self, post):
        try:
            private_address(self.client_address[0], loopback=True)
            if self.headers.get('Host') != self.server.host:
                self.respond(403, 'Usa la dirección que muestra la PC.'); return
            if post and self.headers.get('Origin') not in (None, self.server.origin):
                self.respond(403, 'Origen no permitido.'); return
            path = urlsplit(self.path).path
            length = int(self.headers.get('Content-Length', '0')) if post else 0
            if post and not 0 < length <= 3_000_000:
                self.respond(400, 'Solicitud inválida.'); return
            if post and path == '/pair':
                if length > 128 or not self.headers.get('Content-Type', '').startswith('application/x-www-form-urlencoded'):
                    self.respond(400, 'Código inválido.'); return
                fields = parse_qs(self.rfile.read(length).decode('ascii'))
                pin = fields.get('pin', [''])[0]
                if not pin.isascii() or len(pin)!=6 or not pin.isdigit():
                    self.respond(400,self.pair_page('Escribe los seis dígitos que aparecen en la PC.'));return
                with self.server.pair_lock:
                    # A global limit prevents bypassing the limit with another LAN IP.
                    now = time.monotonic()
                    recent = [t for t in self.server.attempts.get('all', []) if now-t < 60]
                    if len(recent) >= 5:
                        self.respond(429, self.pair_page('Espera un minuto antes de intentar otra vez.')); return
                    recent.append(now); self.server.attempts['all'] = recent
                    if not secrets.compare_digest(pin, self.server.pin):
                        self.respond(400, self.pair_page('Revisa el código que aparece en la PC.')); return
                self.respond(303, '', [('Location', '/'), ('Set-Cookie',
                    f'{self.server.cookie_name}={self.server.pair_token}; HttpOnly; SameSite=Strict; Path=/')]); return
            cookies = SimpleCookie()
            cookies.load(self.headers.get('Cookie', ''))
            paired = cookies.get(self.server.cookie_name)
            if not paired or not secrets.compare_digest(paired.value, self.server.pair_token):
                self.respond(200 if not post and path == '/' else 401, self.pair_page()); return
            headers = {name: value for name, value in self.headers.items()
                       if name.lower() not in HOP_HEADERS | {'host', 'origin', 'cookie', 'x-forwarded-proto', 'expect'}}
            headers['Host'] = f'127.0.0.1:{self.server.backend_port}'
            if self.headers.get('Origin'):
                headers['Origin'] = 'http://' + headers['Host']
            headers['Cookie'] = '; '.join(f'{key}={value.value}' for key, value in cookies.items()
                                          if key != self.server.cookie_name)
            body = self.rfile.read(length) if post else None
            connection = http.client.HTTPConnection('127.0.0.1', self.server.backend_port, timeout=15)
            try:
                connection.request('POST' if post else 'GET', self.path, body, headers)
                response = connection.getresponse(); payload = response.read()
                self.send_response(response.status)
                for name, value in response.getheaders():
                    if name.lower() not in HOP_HEADERS: self.send_header(name, value)
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers(); self.wfile.write(payload)
            finally: connection.close()
        except (ValueError, UnicodeError, CookieError):
            self.respond(400, 'Solicitud inválida.')
        except (OSError, http.client.HTTPException):
            self.respond(502, 'La prueba se cerró en la PC. Vuelve a abrir «Probar en teléfono».')


def main():
    from .desktop import DesktopHost
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--address')
    parser.add_argument('--port', type=int, default=8767)
    args = parser.parse_args()
    addresses = local_addresses()
    if args.address: address = private_address(args.address)
    elif len(addresses) == 1: address = addresses[0]
    else:
        if not addresses: raise SystemExit('Conecta la PC al Wi-Fi e intenta de nuevo.')
        print('Direcciones de red: ' + ', '.join(addresses))
        address = private_address(input('IPv4 de tu Wi-Fi: '))
    with DesktopHost('.', demo=True, port=0) as host, PhoneDemo(host.server, address, args.port) as phone:
        print('PRUEBA TEMPORAL EN TELÉFONO · PC y teléfono en el mismo Wi-Fi', flush=True)
        print('Abre en el teléfono: ' + phone.origin, flush=True)
        print('Código: ' + phone.pin, flush=True)
        print('Mantén esta ventana abierta. Ctrl+C cierra la prueba y borra sus registros.', flush=True)
        webbrowser.open(phone.desktop_url)
        try:
            while host.thread.is_alive(): host.thread.join(.5)
        except KeyboardInterrupt: pass


if __name__ == '__main__': main()
