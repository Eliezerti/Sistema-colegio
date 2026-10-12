# Formato de respaldo cifrado · AULABK01, versión 1

Extensión `.aulabak`. Independiente del esquema SQLite (actualmente 10). No hay migración SQL en A2. Implementación con cryptography 50.0.0, AES-256-GCM, X25519 y HKDF-SHA256; scrypt usa hashlib/OpenSSL. No se implementan primitivas criptográficas propias.

## Estructura binaria

1. Ocho bytes ASCII `AULABK01`.
2. Longitud de cabecera: entero unsigned big-endian de cuatro bytes, entre 1 y 16.384.
3. JSON ASCII canónico: claves ordenadas, sin espacios, ensure_ascii=true. Claves duplicadas/representaciones no canónicas y campos desconocidos se rechazan.
4. AES-GCM del contenido, seguido de su etiqueta de 16 bytes. Contenido antes de cifrar: SHA256 binario de 32 bytes del SQLite + bytes exactos de ese SQLite. No hay compresión ni ZIP dentro del formato.

La cabecera contiene exactamente:

| Campo | Contenido |
|---|---|
| version / cipher | 1 / AES-256-GCM |
| backup_id | 32 bytes aleatorios, Base64; sal por copia para HKDF |
| key_id | 16 bytes aleatorios, Base64; época de contraseña |
| scrypt | n=131072, r=8, p=1 y salt de 32 bytes en Base64 |
| recovery_public | Clave pública X25519 de 32 bytes, Base64 |
| ephemeral | Clave pública X25519 efímera de esta copia, Base64 |
| database_size | Tamaño exacto del SQLite, máximo 512 MiB |
| password_nonce / recovery_nonce / data_nonce | Tres nonces diferentes de 12 bytes, Base64 |
| password_key / recovery_key | DEK cifrada + etiqueta: 48 bytes, Base64 |

No contiene nombres, cédulas, contraseñas, claves secretas de recuperación ni material derivado de contraseña en claro. No inventa fecha de creación; A1 sigue mostrando fecha no fiable cuando no hay metadatos certificados. Las fechas internas de movimientos no se usan para decidir pérdida de registros.

## Claves y autenticación

Cada copia tiene una DEK aleatoria de 32 bytes. Contraseña normalizada NFC y codificada UTF-8; al configurarla se exigen 12–256 caracteres tras normalizar. scrypt requiere aproximadamente 128 MiB, límite de ejecución 256 MiB, salida de 32 bytes. La sal scrypt pertenece a la época de contraseña; HKDF añade una sal independiente de 32 bytes por copia:

- Envoltura por contraseña: HKDF-SHA256(scrypt(password, salt), salt=backup_id, info=`AULABK01/password`, length=32).
- Envoltura por recuperación: X25519 entre clave efímera y pública del destinatario; HKDF-SHA256(shared, salt=backup_id, info=`AULABK01/recovery`, length=32).
- AES-256-GCM para cada envoltura cifra la DEK. AAD: JSON canónico de cabecera sin password_key/recovery_key, seguido de `/password` o `/recovery` respectivamente.
- AES-256-GCM del contenido usa AAD = magic + longitud + cabecera completa, incluidas ambas envolturas.

Al abrir, se valida estructura, tamaños y parámetros antes de ejecutar KDF. En versión 1 no se aceptan N/r/p arbitrarios que agoten memoria. Se autentica GCM y comprueba SHA256 antes de abrir SQLite; después se conservan integrity_check, foreign_key_check, rechazo de esquema futuro y todas las protecciones de A1.

La clave de recuperación son 32 bytes aleatorios representados con 64 dígitos hexadecimales, en grupos de cuatro. Se muestra una vez y se confirma con los últimos cuatro. X25519 aplica el tratamiento estándar de RFC 7748; no se afirma que su seguridad equivalga a 256 bits de búsqueda exhaustiva. Solo su parte pública se guarda; la parte secreta se descarta tras mostrarla. Cambiar contraseña conserva esa misma pública y crea una época nueva: anteriores copias siguen usando su contraseña original o recuperación.

## Nonces y almacenamiento local

Se reservan tres valores antes de cifrar: prefijo aleatorio de cuatro bytes por época + contador unsigned de ocho bytes big-endian. El contador aumenta en tres y se guarda atómicamente con fsync antes de escribir cualquier archivo cifrado. Bloqueo de hilo y archivo evita reservas concurrentes. No utiliza fecha ni reloj. Una configuración ilegible bloquea salidas externas; nunca reinicia automáticamente el contador o envía SQLite.

A1 no restaura este almacén, que está fuera de SQLite: `.backup-crypto/keyring.json`. En Windows, todo su contenido (incluido material derivado y contador) se protege con DPAPI de la cuenta actual, sin CRYPTPROTECT_LOCAL_MACHINE ni diálogos/elevación. No conserva contraseñas ni la recuperación secreta. En Linux, solo metadatos y comprobadores autenticados se escriben; el material derivado queda en RAM y requiere desbloquear con contraseña tras reiniciar. No hay una alternativa persistente sin cifrar.

Almacén validado con HMAC-SHA256 y un comprobador AES-GCM de propósito separado (`AULABK01/local-check`). No se exporta en copias SQLite ni en configuración exportada. DPAPI funciona con la cuenta Windows original; no es necesario para abrir una copia portátil. Quien controle esa sesión Windows puede acceder al material derivado actual: esta protección no defiende la PC abierta comprometida. La advertencia de pérdida de contraseña/recuperación se refiere a restauración portátil cuando no se dispone de otros secretos válidos, incluido el almacén local protegido; no existe un botón para recuperar la contraseña desde DPAPI.

Restaurar una imagen completa de Windows o manipular deliberadamente archivos de claves queda fuera de la reversión A1: configura una época nueva antes de emitir copias. Los hashes/DPAPI no impiden que quien controla Windows restituya una versión antigua del almacén. La DEK y la subclave por copia añaden aleatoriedad independiente; no se promete seguridad ante un generador aleatorio comprometido.

## Publicación y temporales

La instantánea de entrada y la verificación descifrada solo están en carpetas locales privadas. Las rutas no confían en TMP/TEMP, que podrían apuntar al USB/nube. Windows usa LocalAppData consultado a Windows; Linux utiliza /tmp/aula-privado-UID con modo 0700. Los trabajos de creación están bajo `.backup-crypto/work/job-ID`, dentro de los datos y sus permisos; no se permite enlazar esos temporales a otro destino.

Destino externo: temporal `.aula-cipher-ID-aleatorio.tmp`, siempre cifrado. Se sincroniza, se vuelve a leer, se verifican las dos envolturas, se descifra localmente, se comprueba SHA256 y SQLite. Solo después se publica `.aulabak` por reemplazo atómico y se confirma el estado externo. No reemplaza un archivo final existente. Drive confirma sincronización por su propia aplicación, no por Aula.

Los temporales se eliminan ante éxito/error. Un kill real puede impedir finally; el siguiente inicio bajo DataLock y después de resolver A1 limpia únicamente trabajos propios identificados y temporales cifrados asociados. Nunca incluye antes-restauracion, originales, candidatas, informes ni copias publicadas. Si el USB falta, elimina contenido local temporal y conserva solo el marcador para reintentar; no impide trabajar localmente. Marcadores desconocidos/ilegibles no autorizan borrar nada. Borrar un archivo no garantiza borrado forense en SSD: el disco local depende de BitLocker y permisos.

## Referencias y pruebas

Vectores publicados NIST AES-256-GCM, RFC 7914 (scrypt), RFC 7748 (X25519) y RFC 5869 (HKDF). Además: credenciales incorrectas/correctas, alteración, truncamiento, límites KDF, nonce duplicado, reservas persistentes, épocas de contraseña, esquema 99 cifrado, restauración A1, originales intactos, secretos fuera de SQL/informes, TMP redirigido, DPAPI nativo y cinco terminaciones reales de proceso. Resultados de ejecución y límites en cifrado-respaldos.md.
