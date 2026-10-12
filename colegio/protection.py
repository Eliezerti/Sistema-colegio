"""Read-only Windows checks. Unknown never means protected; no elevation or ACL writes."""
import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


WINDOWS_CHECK = r"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$ErrorActionPreference = 'Stop'
$result = @{acl = $null; bitlocker = $null}
try {
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $acl = Get-Acl -LiteralPath $env:AULA_PROTECTION_DIRECTORY
    $rules = @($acl.GetAccessRules($true, $true, [System.Security.Principal.SecurityIdentifier]) | ForEach-Object {
        @{sid = $_.IdentityReference.Value; type = [int]$_.AccessControlType; rights = [int]$_.FileSystemRights}
    })
    $result.acl = @{user = $identity.User.Value; rules = $rules}
} catch { }
try {
    $drive = (Get-Item -LiteralPath $env:AULA_PROTECTION_DIRECTORY).PSDrive.Root
    if ($drive -match '^[A-Za-z]:\\$') {
        $volume = Get-BitLockerVolume -MountPoint $drive.Substring(0, 2) -ErrorAction Stop
        $result.bitlocker = @{protection = [int]$volume.ProtectionStatus; volume = [int]$volume.VolumeStatus}
    }
} catch { }
$result | ConvertTo-Json -Depth 5 -Compress
"""


def unknown_protection(detail='La revisión está pendiente.'):
    return {
        'acl': {'status': 'unknown', 'label': 'No se pudo comprobar', 'detail': detail},
        'bitlocker': {'status': 'unknown', 'label': 'No se pudo comprobar', 'detail': detail},
    }


def classify_acl(data):
    unknown = unknown_protection()['acl']
    if not isinstance(data, dict) or not isinstance(data.get('user'), str) or not data['user'].startswith('S-1-'):
        return unknown
    rules = data.get('rules')
    if not isinstance(rules, list) or not rules:
        return unknown
    trusted = {data['user'], 'S-1-5-18', 'S-1-5-32-544'}  # This user, SYSTEM, Administrators.
    readable = False
    shared = False
    for rule in rules:
        if (not isinstance(rule, dict) or not isinstance(rule.get('sid'), str)
                or type(rule.get('rights')) is not int or rule.get('type') not in (0, 1)):
            return unknown
        # Effective deny/group combinations require a deeper Windows access check.
        if rule['type'] == 1:
            return unknown
        rights = rule['rights'] & ~0x100000  # Ignore Synchronize by itself.
        if rights and rule['sid'] not in trusted:
            shared = True
        if rule['sid'] == data['user'] and rights & 1:
            readable = True
    if shared:
        return {'status': 'shared', 'label': 'Hay permisos adicionales', 'detail':
            'La carpeta permite acceso a otras cuentas o grupos. Pide a un técnico que revise sus permisos antes de guardar datos reales.'}
    if not readable:
        return unknown
    return {'status': 'restricted', 'label': 'Sin accesos adicionales detectados', 'detail':
        'En la carpeta solo se detectaron permisos para tu cuenta, SYSTEM y administradores de Windows. Los archivos internos pueden tener permisos distintos.'}


def classify_bitlocker(data):
    if not isinstance(data, dict) or type(data.get('protection')) is not int or type(data.get('volume')) is not int:
        return unknown_protection()['bitlocker']
    protection, volume = data['protection'], data['volume']
    if protection == 1 and volume == 1:
        return {'status': 'active', 'label': 'Activo', 'detail':
            'Windows informa que el disco de los datos está cifrado y la protección está activada. Conserva su clave de recuperación fuera de esta PC.'}
    if protection == 0 and volume in range(6):
        return {'status': 'inactive', 'label': 'Protección desactivada', 'detail':
            'BitLocker no está activo o su protección está suspendida. Pide a un técnico que lo revise y conserva la clave de recuperación.'}
    if protection == 1 and volume in (2, 3, 4, 5):
        return {'status': 'incomplete', 'label': 'Cifrado sin completar', 'detail':
            'Windows informa que el cifrado está en curso o suspendido. Todavía no se confirmó la protección completa del disco.'}
    return unknown_protection()['bitlocker']


def inspect_protection(directory):
    if os.name != 'nt':
        return unknown_protection('Esta revisión requiere Windows. No se comprobó la protección del disco ni los permisos de Windows.')
    result = unknown_protection('Windows no permitió completar la revisión. Puede requerir ayuda de un técnico; Aula no solicita permisos de administrador.')
    # Fixed script + environment argument: paths are never interpreted as PowerShell code.
    environment = dict(os.environ, AULA_PROTECTION_DIRECTORY=str(Path(directory).resolve()))
    try:
        executable = Path(os.environ.get('SystemRoot', r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
        command = subprocess.run([str(executable), '-NoProfile', '-NonInteractive', '-Command', WINDOWS_CHECK],
            env=environment, capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=8, check=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if command.returncode != 0:
            return result
        data = json.loads(command.stdout.lstrip('\ufeff'))
        if not isinstance(data, dict):
            return result
        if data.get('acl') is not None:
            result['acl'] = classify_acl(data['acl'])
        if data.get('bitlocker') is not None:
            result['bitlocker'] = classify_bitlocker(data['bitlocker'])
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return result


class ProtectionMonitor:
    """Check asynchronously and at most once every five minutes; never block a payment."""
    def __init__(self, directory):
        self.directory = directory
        self.lock = threading.Lock()
        self.result = unknown_protection()
        self.last_check = None
        self.worker = None
        self.closed = False

    def _check(self):
        try:
            result = inspect_protection(self.directory)
        except Exception:
            result = unknown_protection('No se pudo completar la revisión de Windows.')
        result['checked_at'] = datetime.now(timezone.utc).isoformat()
        with self.lock:
            self.result = result
            self.last_check = time.monotonic()

    def snapshot(self):
        with self.lock:
            due = self.last_check is None or time.monotonic()-self.last_check >= 300
            if due and not self.closed and (self.worker is None or not self.worker.is_alive()):
                self.worker = threading.Thread(target=self._check, daemon=True)
                self.worker.start()
            return dict(self.result)

    def close(self):
        with self.lock:
            self.closed = True
            worker = self.worker
        if worker:
            worker.join(timeout=10)
