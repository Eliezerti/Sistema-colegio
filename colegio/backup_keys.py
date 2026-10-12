"""Local keyring: Windows DPAPI, or explicitly unlocked RAM on other systems."""
import copy
import ctypes
import hashlib
import hmac
import json
import secrets
import sys
import threading
import unicodedata
from pathlib import Path

from .backup_crypto import (CryptoError, b64, unb64, canonical, derive_password, recovery_label,
                            public_bytes, X25519PrivateKey, expand, AESGCM)
from .clock_guard import atomic_json
from .storage import DataLock

_lock=threading.RLock()
_memory={}
NAME='keyring.json'
CHECK=hashlib.sha256(b'Aula backup check version 1').digest()


def folder(directory):
    path=Path(directory).resolve()/'.backup-crypto'
    if path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction()):
        raise CryptoError('El almacén de cifrado no puede enlazarse a una carpeta de nube o USB.')
    path.mkdir(parents=True,exist_ok=True,mode=0o700)
    return path


def dpapi(data,protect):
    """Current user only, UI forbidden. No machine-wide key or plaintext fallback."""
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    buffer=ctypes.create_string_buffer(data)
    source=Blob(len(data),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));result=Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    operation=crypt.CryptProtectData if protect else crypt.CryptUnprotectData
    operation.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    operation.restype=wintypes.BOOL
    kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    if not operation(ctypes.byref(source),None,None,None,None,1,ctypes.byref(result)):
        raise CryptoError('Windows no permitió abrir el almacén de cifrado de esta cuenta. No se copiarán datos sin cifrar.')
    try:return ctypes.string_at(result.data,result.size)
    finally:kernel.LocalFree(ctypes.cast(result.data,ctypes.c_void_p))


def public(state):
    return {k:v for k,v in state.items() if k!='master'}


def sign(state):
    content={k:v for k,v in state.items() if k not in ('master','mac')}
    return hmac.new(state['master'],canonical(content),hashlib.sha256).hexdigest()


def validate(state):
    try:
        unb64(state['id'],16);unb64(state['salt'],32);unb64(state['recovery_public'],32);unb64(state['prefix'],4)
        if state['version']!=1 or type(state['counter']) is not int or not 0<=state['counter']<2**64-3:raise ValueError()
        if len(state['master'])!=32 or not hmac.compare_digest(state['mac'],sign(state)):raise ValueError()
        if not isinstance(state['prefixes'],list) or state['prefix'] not in state['prefixes']:raise ValueError()
        unb64(state['check_nonce'],12);unb64(state['check'],48)
        check_key=expand(state['master'],unb64(state['id'],16),b'local-check')
        if AESGCM(check_key).decrypt(unb64(state['check_nonce'],12),unb64(state['check'],48),unb64(state['recovery_public'],32))!=CHECK:raise ValueError()
    except Exception:raise CryptoError('No se pudo comprobar el almacén de cifrado. No se publicará una copia sin protección.') from None
    return state


def read(directory,password=None):
    path=folder(directory)/NAME
    try:
        if not path.exists():raise CryptoError('Configura el cifrado de respaldos en Protección y mantenimiento antes de enviar una copia fuera de esta PC.')
        if path.stat().st_size>1048576:raise ValueError()
        wrapper=json.loads(path.read_text())
        if wrapper['platform']=='dpapi' and sys.platform=='win32':
            state=json.loads(dpapi(__import__('base64').b64decode(wrapper['blob'],validate=True),False))
            state['master']=unb64(state['master'],32)
        elif wrapper['platform']=='memory' and sys.platform!='win32':
            state=wrapper['public'];cached=_memory.get(str(path))
            if password is not None:state={**state,'master':derive_password(password,unb64(state['salt'],32))}
            elif cached and cached[0]==state['id']:state={**state,'master':cached[1]}
            else:raise CryptoError('Desbloquea el cifrado con la contraseña del respaldo después de abrir Aula en este sistema.')
        else:raise CryptoError('El almacén pertenece a otro sistema o cuenta. Puedes restaurar con archivo y contraseña; configura las nuevas copias en esta PC.')
        state=validate(state)
        if sys.platform!='win32':_memory[str(path)]=(state['id'],state['master'])
        return state
    except CryptoError:raise
    except Exception:raise CryptoError('No se pudo comprobar el almacén de cifrado. No se enviarán copias sin cifrar.') from None


def save(directory,state):
    state={**state,'mac':sign(state)};validate(state)
    path=folder(directory)/NAME
    if sys.platform=='win32':
        payload={**state,'master':b64(state['master'])}
        wrapper={'platform':'dpapi','blob':b64(dpapi(canonical(payload),True))}
    else:wrapper={'platform':'memory','public':public(state)}
    atomic_json(path,wrapper)
    if sys.platform!='win32':path.chmod(0o600)
    if sys.platform!='win32':_memory[str(path)]=(state['id'],state['master'])


def status(directory):
    path=Path(directory).resolve()/'.backup-crypto'/NAME
    if not path.exists():return {'configured':False,'ready':False,'message':'Cifrado pendiente de configurar.'}
    with _lock:
        try:
            state=read(directory)
            return {'configured':True,'ready':True,'key_id':state['id'],
                    'recovery_id':hashlib.sha256(unb64(state['recovery_public'],32)).hexdigest()[:16],
                    'persistent':sys.platform=='win32','message':'Cifrado preparado para copias nuevas.'}
        except CryptoError as error:return {'configured':True,'ready':False,'message':str(error)}


def prepare(directory,password):
    if not isinstance(password,str) or not 12<=len(unicodedata.normalize('NFC',password))<=256 or len(password)>256:
        raise CryptoError('La contraseña de respaldos debe tener entre 12 y 256 caracteres.')
    with _lock,DataLock(folder(directory)):
        existing=read(directory) if (folder(directory)/NAME).exists() else None
        recovery=secrets.token_bytes(32) if existing is None else None
        prefixes=list(existing['prefixes']) if existing else []
        prefix=b64(secrets.token_bytes(4))
        while prefix in prefixes:prefix=b64(secrets.token_bytes(4))
        state={'version':1,'id':b64(secrets.token_bytes(16)),'salt':b64(secrets.token_bytes(32)),
               'recovery_public':existing['recovery_public'] if existing else b64(public_bytes(X25519PrivateKey.from_private_bytes(recovery))),
               'prefix':prefix,'prefixes':[*prefixes,prefix],'counter':0,'check_nonce':b64(secrets.token_bytes(12))}
        state['master']=derive_password(password,unb64(state['salt'],32))
        state['check']=b64(AESGCM(expand(state['master'],unb64(state['id'],16),b'local-check')).encrypt(
            unb64(state['check_nonce'],12),CHECK,unb64(state['recovery_public'],32)))
        state['mac']=sign(state)
        return {'state':state,'previous_id':existing['id'] if existing else None},recovery_label(recovery) if recovery else None


def confirm(directory,pending):
    with _lock,DataLock(folder(directory)):
        current=read(directory)['id'] if (folder(directory)/NAME).exists() else None
        if current!=pending['previous_id']:raise CryptoError('La configuración cambió. Repite la preparación de la contraseña.')
        save(directory,pending['state'])


def unlock(directory,password):
    with _lock,DataLock(folder(directory)):read(directory,password)


def reserve(directory):
    with _lock,DataLock(folder(directory)):
        state=read(directory);start=state['counter'];state['counter']+=3
        save(directory,state) # Durable reservation BEFORE any encryption/publication.
        prefix=unb64(state['prefix'],4)
        return copy.deepcopy(state),[prefix+i.to_bytes(8,'big') for i in range(start+1,start+4)]
