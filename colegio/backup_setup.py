"""Administrator setup. Pending secrets stay in RAM, bound to the current session."""
import secrets
import threading
import time

from . import backup_keys
from .backup_crypto import CryptoError


class Setup:
    def __init__(self,directory):
        self.directory=directory;self.pending={};self.lock=threading.RLock()

    def discard(self,token):
        with self.lock:self.pending.pop(token,None)

    def prepare(self,data,user):
        if data.get('password')!=data.get('repeat'):raise CryptoError('Las contraseñas de respaldo no coinciden.')
        pending,recovery=backup_keys.prepare(self.directory,data.get('password'))
        token=secrets.token_urlsafe(32)
        with self.lock:
            for previous in [k for k,v in self.pending.items() if v['session']==user['token']]:self.pending.pop(previous)
            self.pending[token]={'session':user['token'],'expires':time.monotonic()+600,'pending':pending,
                                 'answer':recovery.replace('-','')[-4:] if recovery else 'CAMBIAR CONTRASEÑA DE RESPALDOS'}
        timer=threading.Timer(600,self.discard,args=(token,));timer.daemon=True;timer.start()
        return {'token':token,'recovery':recovery,'changing':recovery is None}

    def confirm(self,data,user):
        token=data.get('token')
        if not isinstance(token,str):raise CryptoError('Repite la preparación de la contraseña.')
        with self.lock:
            item=self.pending.get(token)
            if not item or item['session']!=user['token'] or item['expires']<time.monotonic():
                raise CryptoError('La preparación venció o pertenece a otra sesión. Repite el proceso.')
            answer=data.get('confirmation','')
            if not isinstance(answer,str) or not secrets.compare_digest(answer.strip().upper(),item['answer']):
                raise CryptoError('Confirma que guardaste la clave, o escribe la frase de cambio indicada.')
            backup_keys.confirm(self.directory,item['pending']);self.pending.pop(token)
        return backup_keys.status(self.directory)

    def close(self):
        with self.lock:self.pending.clear()
        with backup_keys._lock:backup_keys._memory.pop(str(backup_keys.folder(self.directory)/backup_keys.NAME),None)
