"""Local Host/Origin protection and explicit rejection of retired remote access."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


def private_origin(value):
    if not isinstance(value, str) or len(value) > 300:
        raise ValueError('Indica el enlace HTTPS privado de Tailscale.')
    value=value.strip()
    try:
        url=urlsplit(value)
        hostname=url.hostname or ''
        port=url.port
    except ValueError:
        raise ValueError('El enlace privado no es válido.') from None
    label=r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?'
    if (url.scheme!='https' or not re.fullmatch(label+r'\.'+label+r'\.ts\.net',hostname)
            or url.username is not None or url.password is not None or port not in (None,443)
            or url.path not in ('','/') or url.query or url.fragment):
        raise ValueError('Usa el enlace HTTPS de esta PC: https://equipo.red.ts.net, sin rutas ni contraseñas.')
    return 'https://'+hostname


class PrivateAccess:
    def __init__(self, origin=''):
        if origin:
            raise ValueError('El acceso privado fue retirado. Usa Aula en esta PC o el escritorio remoto de Windows.')
        self.origin=''
        self.hostname=urlsplit(self.origin).hostname if self.origin else ''

    def remote_host(self, host):
        return bool(self.hostname) and host.lower() in (self.hostname,self.hostname+':443')

    def allowed_host(self, host, port):
        return host in (f'127.0.0.1:{port}',f'localhost:{port}') or self.remote_host(host)

    def allowed_origin(self, host, origin, port):
        if origin is None:
            return True
        if self.origin and origin==self.origin:
            return True
        return host in (f'127.0.0.1:{port}',f'localhost:{port}') and origin=='http://'+host

    def secure_cookie(self, host, origin, forwarded_proto):
        # Only a loopback proxy can reach this server. Do not expose the listener.
        return bool(self.origin) and (self.remote_host(host) or origin==self.origin or forwarded_proto=='https')

    def snapshot(self):
        return {'mode':'private-network' if self.origin else 'local','remote_url':self.origin}


def load_config(path):
    try:
        data=json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(data,dict) or data.get('version')!=1:
            raise ValueError()
        return private_origin(data.get('remote_origin'))
    except (OSError,ValueError,TypeError):
        raise ValueError('La configuración de red no existe o no es válida. Ejecuta Configurar-Red.bat en la PC principal.') from None


def save_config(directory, origin):
    raise ValueError('El acceso privado fue retirado. Usa el escritorio remoto de Windows.')


def main():
    raise SystemExit('El acceso privado fue retirado. Usa el escritorio remoto de Windows.')


if __name__=='__main__':
    main()
