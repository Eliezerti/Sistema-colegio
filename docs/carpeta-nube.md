# Quitar el aviso de disco desconocido cuando usas Drive

Drive puede aparecer como una unidad virtual, por ejemplo Google Drive (E:). Esa letra no demuestra que sea otro disco físico. Aula puede escribir los respaldos sin poder determinar el disco del destino.

## Pasos

1. Comprueba en la aplicación de Drive que la sincronización esté actualizada.
2. Entra en la web de Drive y verifica un respaldo reciente en la carpeta configurada.
3. Entra como Administrador en Aula → Configuración → Protección y mantenimiento → Declarar carpeta de nube.
4. Revisa la ruta y marca «Revisé la subida de una copia reciente y esta carpeta está configurada para sincronizarse con la nube».
5. Pulsa Confirmar carpeta de nube.

Si solo estaba el aviso de disco desconocido, se sustituye por «Carpeta de nube declarada por administración · Aula no comprueba la subida». No se concede acceso a tu cuenta ni se verifica la nube automáticamente.

## Límites y protección

- Se exige una copia reciente escrita en la carpeta actual. Una copia fallida o de más de tres días no permite confirmar.
- Los avisos de fallo local/externo, destino ausente, copia antigua, conservación y mismo disco siguen visibles.
- Solo Administrador declara o quita la declaración. Caja ve los problemas y el recordatorio; Consulta y Pruebas conservan su comportamiento anterior.
- CSRF y el control del reloj se mantienen. La bitácora registra Administrador, fecha, valor anterior y nuevo.
- No cambia los resultados de discos, ACL o BitLocker. Una declaración manual no los convierte en comprobados.
- Cambiar la ruta borra la declaración. Otra PC con distinto nombre de equipo exige revisión, aunque la ruta coincida. Si reinstalas Windows o cambias la cuenta de Drive conservando equipo y ruta, usa Quitar declaración de nube y comprueba de nuevo.

Revisa periódicamente Drive. Si Aula escribe en la carpeta pero Drive no sube los archivos, Aula no puede detectar ese fallo. Conserva la carpeta privada y no pongas allí la base activa. Este cambio no cifra los respaldos.

Se guarda solo la declaración de configuración: ruta, equipo, Administrador y fecha. No se cambia el esquema ni alumnos, cobros, cargos, importes, las funciones de mensualidades.
