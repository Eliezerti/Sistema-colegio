from tests.audit_helpers import publish_fixture
import hashlib
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import closing

from colegio import backup_crypto as crypto,backup_keys as keys
from colegio.backup_export import write_encrypted
from colegio.backup_inspection import probe_backup,staged_backup,file_hash
from colegio.restore import preview_restore,restore,LOSS,ReviewRequired
from colegio.storage import automatic_backup,consistent_backup
from colegio.db import connect,record_payment,next_record_id
from tests import test_recovery as fixtures
from tests.crypto_helpers import configure,PASSWORD


class BackupCryptoTests(unittest.TestCase):
    def setUp(self):
        fixtures.RecoveryTests.setUp(self)
        self.recovery=configure(self.directory)
        self.cipher=self.root/'externo.aulabak'
        write_encrypted(self.backup,self.cipher,self.directory)

    tearDown=fixtures.RecoveryTests.tearDown

    def test_password_and_recovery_open_self_contained_copy_in_other_folder(self):
        a=probe_backup(self.cipher,PASSWORD);b=probe_backup(self.cipher,self.recovery,'recovery')
        self.assertFalse(a['unencrypted']);self.assertEqual(a,b)
        other=self.root/'otra-pc'
        review=preview_restore(self.cipher,other,credential=self.recovery,credential_kind='recovery')
        target=restore(self.cipher,other,preview_hash=review['preview_hash'],confirmation=review['confirmation'],credential=self.recovery,credential_kind='recovery')
        self.assertFalse((other/'.backup-crypto').exists(),'Restoring requires no original PC keyring')
        with closing(connect(target)) as db:self.assertEqual(dict(db.execute('SELECT * FROM payments').fetchone()),self.payment)

    def test_altered_truncated_wrong_password_and_bounded_kdf_never_open_sqlite(self):
        original=self.cipher.read_bytes()
        for value in (original[:-5],original[:10],original[:-1]+bytes([original[-1]^1])):
            bad=self.root/'alterado.aulabak';bad.write_bytes(value)
            with patch('colegio.backup_inspection.readonly') as opened:
                with self.assertRaises(crypto.CryptoError):probe_backup(bad,PASSWORD)
                opened.assert_not_called()
        with self.assertRaises(crypto.CryptoError):probe_backup(self.cipher,'Contraseña-ficticia-incorrecta')
        with self.assertRaises(crypto.CredentialRequired):probe_backup(self.cipher)
        header,_,_,_=crypto.parse(original);header['scrypt']['n']=2**30
        encoded=crypto.canonical(header);bad.write_bytes(crypto.MAGIC+len(encoded).to_bytes(4,'big')+encoded+original[12+int.from_bytes(original[8:12],'big'):])
        with patch('colegio.backup_crypto.derive_password') as derive:
            with self.assertRaises(crypto.CryptoError):probe_backup(bad,PASSWORD)
            derive.assert_not_called()

    def test_nonce_reservations_are_durable_and_repetition_is_rejected(self):
        state,first=keys.reserve(self.directory);_,second=keys.reserve(self.directory)
        self.assertFalse(set(first)&set(second))
        with self.assertRaisesRegex(crypto.CryptoError,'nonce único'):crypto.encrypt(self.backup.read_bytes(),state,[first[0]]*3)
        raw=self.cipher.read_bytes();header,_,_,_=crypto.parse(raw)
        header['data_nonce']=header['password_nonce'];encoded=crypto.canonical(header)
        with self.assertRaises(crypto.CryptoError):crypto.parse(crypto.MAGIC+len(encoded).to_bytes(4,'big')+encoded+raw[12+int.from_bytes(raw[8:12],'big'):])

    def test_password_rotation_keeps_recovery_and_previous_password_epochs(self):
        previous=self.cipher.read_bytes();new_password='FICTICIO-nueva-contraseña-2026'
        pending,recovery=keys.prepare(self.directory,new_password)
        self.assertIsNone(recovery,'Recovery secret is never read back or generated on password rotation')
        keys.confirm(self.directory,pending)
        newer=self.root/'nueva.aulabak';write_encrypted(self.backup,newer,self.directory)
        self.assertEqual(self.cipher.read_bytes(),previous)
        self.assertEqual(probe_backup(self.cipher,PASSWORD)['payments'],1)
        with self.assertRaises(crypto.CryptoError):probe_backup(self.cipher,new_password)
        with self.assertRaises(crypto.CryptoError):probe_backup(newer,PASSWORD)
        self.assertEqual(probe_backup(newer,new_password)['payments'],1)
        for copy in (self.cipher,newer):self.assertEqual(probe_backup(copy,self.recovery,'recovery')['payments'],1)

    def test_old_plain_backup_has_warning_and_conversion_never_changes_original(self):
        from colegio.restore import review_text
        original=self.backup.read_bytes();listing=set(self.root.iterdir())
        self.assertTrue(probe_backup(self.backup)['unencrypted'])
        self.assertIn('antiguo sin cifrar',review_text(preview_restore(self.backup,self.root/'vacía')))
        converted=self.root/'convertido.aulabak';write_encrypted(self.backup,converted,self.directory)
        self.assertEqual(self.backup.read_bytes(),original)
        self.assertEqual(probe_backup(converted,PASSWORD)['payments'],1)

    def test_encrypted_restore_retains_loss_report_correlatives_and_a1_confirmations(self):
        consistent_backup(self.backup,self.target);publish_fixture(self.target)
        with closing(connect(self.target)) as db,db:
            record_payment(db,{'student_id':1,'amount':'10','currency':'USD','paid_on':'2025-09-21','request_key':'later','method':'Efectivo'},1)
        review=preview_restore(self.cipher,self.directory,credential=PASSWORD)
        self.assertEqual(review['confirmation'],LOSS)
        with self.assertRaises(ReviewRequired):restore(self.cipher,self.directory,credential=PASSWORD)
        restore(self.cipher,self.directory,credential=PASSWORD,preview_hash=review['preview_hash'],confirmation=LOSS)
        with closing(connect(self.target)) as db:
            self.assertGreater(next_record_id(db,'payments'),2)
            event=json.loads(db.execute("SELECT details FROM audit WHERE action='restore-backup'").fetchone()[0])
            self.assertTrue(event['source_encrypted']);self.assertEqual(event['source_sha256'],file_hash(self.cipher))
        for report in (self.directory/'backups').glob('*perdidas.*'):
            for secret in (PASSWORD.encode(),self.recovery.encode()):self.assertNotIn(secret,report.read_bytes())

    def test_failed_verification_never_publishes_and_cleans_local_temporary(self):
        output=self.root/'no-publicar.aulabak'
        with patch('colegio.backup_export.inspect_copy',side_effect=ValueError('Verificación ficticia fallida')):
            with self.assertRaises(ValueError):write_encrypted(self.backup,output,self.directory)
        self.assertFalse(output.exists());self.assertFalse(list(self.root.glob('.aula-cipher-*')))
        import tempfile
        usb=self.root/'usb-temp';usb.mkdir();before=set(usb.iterdir())
        with patch.object(tempfile,'tempdir',str(usb)):
            self.assertEqual(probe_backup(self.cipher,PASSWORD)['payments'],1)
            write_encrypted(self.backup,self.root/'temporal-local.aulabak',self.directory)
        self.assertEqual(set(usb.iterdir()),before,'Untrusted TMP cannot receive any plaintext or temporary')

    def test_authenticated_future_schema_is_rejected_before_any_destination_write(self):
        future=self.root/'futuro.sqlite3';consistent_backup(self.backup,future)
        with closing(connect(future)) as db,db:db.execute('PRAGMA user_version=99')
        state,nonces=keys.reserve(self.directory);blob,_=crypto.encrypt(future.read_bytes(),state,nonces)
        copy=self.root/'futuro.aulabak';copy.write_bytes(blob)
        with self.assertRaisesRegex(ValueError,'esquema 99'):preview_restore(copy,self.root/'no-tocar',credential=PASSWORD)
        self.assertFalse((self.root/'no-tocar').exists())

    def test_local_backups_continue_when_cifrado_is_not_configured_or_keyring_is_broken(self):
        consistent_backup(self.backup,self.target);publish_fixture(self.target);external=self.root/'usb'
        with closing(connect(self.target)) as db,db:db.execute("UPDATE settings SET value=? WHERE key='backup_directory'",(str(external),))
        first=automatic_backup(self.target);self.assertTrue(first['secondary_encrypted'])
        previous=Path(first['secondary_path']);original=previous.read_bytes()
        (keys.folder(self.directory)/keys.NAME).write_text('truncado')
        failed=automatic_backup(self.target)
        self.assertFalse(failed['local_error']);self.assertTrue(failed['secondary_error'])
        self.assertEqual(failed['secondary_at'],first['secondary_at']);self.assertEqual(previous.read_bytes(),original)
        self.assertFalse(list(external.glob('*.sqlite3')))
        (keys.folder(self.directory)/keys.NAME).unlink()
        failed=automatic_backup(self.target)
        self.assertTrue(Path(failed['local_path']).exists());self.assertTrue(failed['secondary_error'])

    def test_keyring_and_snapshots_never_contain_password_or_recovery_secret(self):
        stored=(keys.folder(self.directory)/keys.NAME).read_bytes()
        for secret in (PASSWORD.encode(),self.recovery.encode(),bytes.fromhex(self.recovery.replace('-',''))):self.assertNotIn(secret,stored)
        with closing(connect(self.backup)) as db:
            contents='\n'.join(db.iterdump()).encode()
            for secret in (PASSWORD.encode(),self.recovery.encode()):self.assertNotIn(secret,contents)
        if sys.platform!='win32':
            with keys._lock:keys._memory.clear()
            self.assertFalse(keys.status(self.directory)['ready'])
            keys.unlock(self.directory,PASSWORD);self.assertTrue(keys.status(self.directory)['ready'])

    def test_real_kills_during_cipher_write_verification_and_publication_preserve_previous(self):
        consistent_backup(self.backup,self.target);publish_fixture(self.target);external=self.root/'usb'
        with closing(connect(self.target)) as db,db:db.execute("UPDATE settings SET value=? WHERE key='backup_directory'",(str(external),))
        first=automatic_backup(self.target);prior=Path(first['secondary_path']);original=prior.read_bytes()
        original_data=self.target.read_bytes();nonces=set()
        for stage in ('mid_cipher_write','after_cipher_write','during_verify','before_publish','after_publish'):
            with self.subTest(stage=stage):
                marker=self.root/(stage+'.ready')
                child="""import sys,time
from pathlib import Path
from colegio.backup_keys import unlock
from colegio.storage import automatic_backup
from tests.crypto_helpers import PASSWORD
import colegio.backup_export as export
if sys.platform!='win32':unlock(Path(sys.argv[1]).parent,PASSWORD)
def stop(stage):
 if stage==sys.argv[2]:
  Path(sys.argv[3]).write_text(stage)
  while True:time.sleep(.02)
export.checkpoint=stop
automatic_backup(Path(sys.argv[1]))
"""
                process=subprocess.Popen([sys.executable,'-c',child,str(self.target),stage,str(marker)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                try:
                    deadline=time.monotonic()+20
                    while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                    self.assertTrue(marker.exists(),'El proceso no llegó a la etapa cifrada')
                    process.kill();process.communicate(timeout=5);self.assertNotEqual(process.returncode,0)
                finally:
                    if process.poll() is None:process.kill();process.communicate()
                self.assertEqual(prior.read_bytes(),original);self.assertEqual(self.target.read_bytes(),original_data)
                persisted=json.loads((self.directory/'backup-status.json').read_text())
                self.assertEqual(persisted['secondary_sha256'],first['secondary_sha256'])
                for temp in external.glob('.aula-cipher-*'):
                    self.assertTrue(temp.read_bytes().startswith(crypto.MAGIC))
                for file in external.glob('*.aulabak'):
                    self.assertEqual(probe_backup(file,PASSWORD)['payments'],1)
                from colegio.backup_work import cleanup_work
                cleanup_work(self.directory)
                self.assertFalse(list((self.directory/'.backup-crypto'/'work').glob('job-*')))
                self.assertFalse(list(external.glob('.aula-cipher-*')))
                after=automatic_backup(self.target);self.assertFalse(after['secondary_error'])
                header,_,_,_=crypto.parse(Path(after['secondary_path']).read_bytes())
                values={header[k] for k in ('password_nonce','recovery_nonce','data_nonce')}
                self.assertFalse(values&nonces);nonces.update(values)
                # Only new successful calls can advance confirmation; reset baseline for next subcase.
                first=after
        self.assertFalse(list(external.glob('*.sqlite3')))


class KnownCryptoVectors(unittest.TestCase):
    def test_aes256_gcm_nist_vector(self):
        self.assertEqual(crypto.AESGCM(bytes(32)).encrypt(bytes(12),bytes(16),None).hex(),
                         'cea7403d4d606b6e074ec5d3baf39d18d0d1c8a799996bf0265b98b5d48ab919')

    def test_scrypt_rfc7914_vector(self):
        self.assertEqual(hashlib.scrypt(b'',salt=b'',n=16,r=1,p=1,dklen=64).hex(),
            '77d6576238657b203b19ca42c18a0497f16b4844e3074ae8dfdffa3fede21442fcd0069ded0948f8326a753a0fc81f17e8d3e0fb2e0d3628cf35e20c38d18906')

    def test_x25519_rfc7748_vector(self):
        private=crypto.X25519PrivateKey.from_private_bytes(bytes.fromhex('77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a'))
        self.assertEqual(crypto.public_bytes(private).hex(),'8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a')

    def test_hkdf_rfc5869_vector(self):
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes
        value=HKDF(algorithm=hashes.SHA256(),length=42,salt=bytes(range(13)),info=bytes(range(240,250))).derive(bytes([11])*22)
        self.assertEqual(value.hex(),'3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865')


@unittest.skipUnless(sys.platform=='win32','DPAPI solo se ejecuta en Windows.')
class WindowsDPAPITests(unittest.TestCase):
    def test_dpapi_roundtrip_and_tampering_without_plaintext_fallback(self):
        value=b'FICTICIO-material-de-prueba';encoded=keys.dpapi(value,True)
        self.assertNotIn(value,encoded);self.assertEqual(keys.dpapi(encoded,False),value)
        with self.assertRaises(crypto.CryptoError):keys.dpapi(encoded[:-1],False)
