"""AULABK01: authenticated portable backups; no credentials in file metadata."""
import base64
import hashlib
import json
import secrets
import unicodedata

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

MAGIC=b'AULABK01'
MAX_HEADER=16384
MAX_DATABASE=512*1024*1024
PARAMETERS={'n':131072,'r':8,'p':1}


class CryptoError(ValueError):
    pass


class CredentialRequired(CryptoError):
    pass


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')


def b64(value):
    return base64.b64encode(value).decode('ascii')


def unb64(value,size):
    try:
        result=base64.b64decode(value,validate=True)
        if len(result)!=size:raise ValueError()
        return result
    except (ValueError,TypeError):raise CryptoError('El archivo cifrado tiene una cabecera inválida.') from None


def derive_password(password,salt):
    if not isinstance(password,str) or not 1<=len(password)<=256:
        raise CryptoError('Escribe la contraseña del respaldo, de hasta 256 caracteres.')
    return hashlib.scrypt(unicodedata.normalize('NFC',password).encode('utf-8'),salt=salt,
                          **PARAMETERS,maxmem=256*1024*1024,dklen=32)


def expand(key,salt,purpose):
    return HKDF(algorithm=hashes.SHA256(),length=32,salt=salt,info=b'AULABK01/'+purpose).derive(key)


def public_bytes(private):
    return private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)


def recovery_private(text):
    try:
        if not isinstance(text,str) or len(text)>100:raise ValueError()
        data=bytes.fromhex(text.replace('-','').replace(' ',''))
        if len(data)!=32:raise ValueError()
        return X25519PrivateKey.from_private_bytes(data)
    except ValueError:raise CryptoError('La clave de recuperación debe contener sus 64 caracteres, completos.') from None


def recovery_label(raw):
    value=raw.hex().upper()
    return '-'.join(value[i:i+4] for i in range(0,64,4))


def parse(blob):
    try:
        if len(blob)<12 or blob[:8]!=MAGIC:raise ValueError()
        size=int.from_bytes(blob[8:12],'big')
        if not 1<=size<=MAX_HEADER or len(blob)<12+size+16:raise ValueError()
        header=json.loads(blob[12:12+size])
        if canonical(header)!=blob[12:12+size]:raise ValueError()
        if set(header)!={'version','cipher','backup_id','key_id','scrypt','recovery_public','ephemeral',
                        'database_size','password_nonce','recovery_nonce','data_nonce','password_key','recovery_key'}:raise ValueError()
        if header['version']!=1 or header['cipher']!='AES-256-GCM':raise ValueError()
        kdf=header['scrypt']
        if set(kdf)!={'n','r','p','salt'}:raise ValueError()
        if any(type(kdf[k]) is not int or kdf[k]!=v for k,v in PARAMETERS.items()):raise ValueError()
        unb64(kdf['salt'],32);unb64(header['backup_id'],32);unb64(header['key_id'],16)
        unb64(header['recovery_public'],32);unb64(header['ephemeral'],32)
        nonces=[unb64(header[k],12) for k in ('password_nonce','recovery_nonce','data_nonce')]
        if len(set(nonces))!=3:raise ValueError()
        unb64(header['password_key'],48);unb64(header['recovery_key'],48)
        if type(header['database_size']) is not int or not 0<header['database_size']<=MAX_DATABASE:raise ValueError()
        if len(blob)!=12+size+header['database_size']+32+16:raise ValueError()
        core={k:v for k,v in header.items() if k not in ('password_key','recovery_key')}
        return header,canonical(core),blob[:12+size],blob[12+size:]
    except (KeyError,ValueError,TypeError,UnicodeError,OverflowError):
        raise CryptoError('El respaldo cifrado está incompleto, alterado o usa un formato no compatible.') from None


def open_content(blob,key):
    _,_,aad,cipher=parse(blob)
    header=json.loads(aad[12:])
    try:
        plain=AESGCM(key).decrypt(unb64(header['data_nonce'],12),cipher,aad)
        database=plain[32:]
        if not secrets.compare_digest(plain[:32],hashlib.sha256(database).digest()):raise ValueError()
        return database
    except (InvalidTag,ValueError):raise CryptoError('No se pudo autenticar el respaldo. La credencial no corresponde o el archivo está alterado.') from None


def decrypt(blob,credential=None,kind='password'):
    header,core,_,_=parse(blob)
    if not credential:raise CredentialRequired('Este respaldo está cifrado. Escribe su contraseña o la clave de recuperación.')
    salt=unb64(header['backup_id'],32)
    try:
        if kind=='password':
            wrapping=expand(derive_password(credential,unb64(header['scrypt']['salt'],32)),salt,b'password')
            key=AESGCM(wrapping).decrypt(unb64(header['password_nonce'],12),unb64(header['password_key'],48),core+b'/password')
        elif kind=='recovery':
            private=recovery_private(credential)
            if public_bytes(private)!=unb64(header['recovery_public'],32):raise InvalidTag()
            shared=private.exchange(X25519PublicKey.from_public_bytes(unb64(header['ephemeral'],32)))
            wrapping=expand(shared,salt,b'recovery')
            key=AESGCM(wrapping).decrypt(unb64(header['recovery_nonce'],12),unb64(header['recovery_key'],48),core+b'/recovery')
        else:raise CryptoError('Selecciona Contraseña o Clave de recuperación.')
    except (InvalidTag,ValueError):
        raise CryptoError('La contraseña o clave no corresponde a esta copia, o el archivo está alterado.') from None
    return open_content(blob,key),header


def encrypt(database,state,nonces):
    if not 0<len(database)<=MAX_DATABASE:raise CryptoError('El respaldo supera el tamaño admitido (512 MB).')
    if len(nonces)!=3 or len(set(nonces))!=3 or any(len(n)!=12 for n in nonces):
        raise CryptoError('No se pudo reservar un nonce único. No se publicó el respaldo.')
    key=secrets.token_bytes(32);identity=secrets.token_bytes(32)
    ephemeral=X25519PrivateKey.generate()
    core={'version':1,'cipher':'AES-256-GCM','backup_id':b64(identity),'key_id':state['id'],
          'scrypt':{**PARAMETERS,'salt':state['salt']},'recovery_public':state['recovery_public'],
          'ephemeral':b64(public_bytes(ephemeral)),'database_size':len(database),
          **dict(zip(('password_nonce','recovery_nonce','data_nonce'),map(b64,nonces)))}
    password_key=expand(state['master'],identity,b'password')
    shared=ephemeral.exchange(X25519PublicKey.from_public_bytes(unb64(state['recovery_public'],32)))
    recovery_key=expand(shared,identity,b'recovery')
    header={**core,'password_key':b64(AESGCM(password_key).encrypt(nonces[0],key,canonical(core)+b'/password')),
            'recovery_key':b64(AESGCM(recovery_key).encrypt(nonces[1],key,canonical(core)+b'/recovery'))}
    encoded=canonical(header);aad=MAGIC+len(encoded).to_bytes(4,'big')+encoded
    cipher=AESGCM(key).encrypt(nonces[2],hashlib.sha256(database).digest()+database,aad)
    return aad+cipher,(key,password_key,recovery_key)


def verify_generated(blob,keys):
    key,password_key,recovery_key=keys
    header,core,_,_=parse(blob)
    try:
        for kind,wrapping in [('password',password_key),('recovery',recovery_key)]:
            wrapped=AESGCM(wrapping).decrypt(unb64(header[kind+'_nonce'],12),unb64(header[kind+'_key'],48),core+b'/'+kind.encode())
            if not secrets.compare_digest(wrapped,key):raise InvalidTag()
    except InvalidTag:raise CryptoError('No se verificaron los dos accesos al respaldo. No se publicó la copia.') from None
    return open_content(blob,key)
