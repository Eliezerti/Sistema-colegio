# Historial de cambios

## Sin publicar · configuración organizada por apartados

- Pestañas independientes de Identidad y calendario, Protección y mantenimiento, Usuarios y acceso y Bitácora; navegación accesible por teclado y un solo apartado visible.
- El destino de respaldo se guarda con una operación limitada a esa ruta, sin modificar identidad, calendario ni datos contables. Conserva permisos de Administrador, CSRF, validación de ruta, bitácora y respaldo posterior.
- Los borradores de identidad y destino se conservan en memoria al cambiar de pestaña y guardar otro apartado; se borran al cerrar sesión. No se guardan contraseñas en esos borradores.
- Ayuda de Windows distingue BitLocker, su recuperación de 48 dígitos y las llaves de acceso de Microsoft. No activa BitLocker ni presenta un resultado desconocido como activo.
- Preferencias permanentes registradas en AGENTS.md. Sin migración de esquema, cambio de ubicación, modificación de registros existentes, móvil/PWA o nómina.
- Validación Linux: 198 descubiertas, 197 correctas y una exclusiva de Windows omitida. Navegadores normal, Pruebas e importación correctos; dos pruebas nuevas de servidor y ampliación del recorrido de Configuración.

## Sin publicar · carpeta de nube declarada por administración

- Declaración manual de una carpeta sincronizada con Drive, OneDrive o Dropbox, después de verificar una copia reciente en su web. Sustituye únicamente el aviso de disco desconocido por un recordatorio discreto.
- No afirma que Aula verificó la subida ni cambia el diagnóstico de discos, ACL o BitLocker. Los avisos de mismo disco, falta de destino, fallos y copias antiguas siguen visibles.
- Solo Administrador, con CSRF y revisión explícita, puede declarar o quitar la declaración. Se registra el cambio en bitácora. Cambiar la ruta la invalida; una declaración de otra PC no se aplica.
- Usa una clave opcional de configuración existente, creada solo al confirmar; no hay migración de esquema ni modificación de datos contables. Conserva respaldos de cinco minutos y protección del reloj.
- Validación Linux: 196 descubiertas, 195 correctas y una exclusiva de Windows omitida. Navegadores normal, Pruebas e importación correctos. Ocho pruebas nuevas de permisos, persistencia, alcance, fallos, otra PC y conservación de esquema/importes.
- Instalador 1.0.29 en borrador: 196 pruebas correctas en Windows, instalación/ventanas/reinstalación/desinstalación conservando datos y dos análisis de Defender sin detecciones. Archivo descargado y SHA256 verificados; siguen pendientes las alertas antiguas del equipo del usuario.

## Sin publicar · identificación del alumno en recibos

- La pantalla de recibo, la impresión y los PDF A4, media carta y térmicos muestran el código interno de Aula, nunca el documento del alumno como reemplazo.
- Los recibos anteriores sin código muestran «Código interno no registrado». Se conserva la identificación del representante y el documento del alumno en la ficha y la constancia de matrícula.
- Pruebas con código presente, ausente, vacío y nulo; no se modifica SQLite, cobros ni instantáneas históricas. No se ha aplicado el cifrado ni comenzado los puntos posteriores.
- Validación Linux: 188 pruebas, 187 correctas y una exclusiva de Windows omitida; navegadores normal, Pruebas e importación correctos.
- Instalador 1.0.28 en borrador: 188 pruebas correctas en Windows, instalación/ventanas/reinstalación/desinstalación conservando datos y dos análisis de Defender sin detecciones. SHA256 verificado contra el archivo descargado y el registro del runner. Las alertas anteriores del equipo del usuario siguen pendientes.

## Fase 1, punto 2 · controlador del reloj

- Control persistente separado de los datos contables, con publicación atómica y sincronización.
- Política aprobada: siete días entre aperturas y tolerancia de dos minutos para ajustes; comparación monotónica durante el uso.
- Confirmación exclusiva de Administrador, registro previo en bitácora y bloqueo ante control ausente con historial, ilegible o no publicable.
- Pruebas de persistencia, permisos, confirmación, ajustes y fallos; sin cambio de esquema ni importes existentes.

### Integración del bloqueo

- Protección en servidor y motor: inicio, consultas, cobros, generación y documentos. Revisión final antes de confirmar modificaciones; un salto durante un cobro revierte la transacción.
- Pantalla de revisión en horario de Venezuela; solo Administrador confirma con CSRF. La impresión comprueba el reloj y la pantalla elimina documentos pendientes al bloquear.
- Limitación de acceso con tiempo monotónico; confirmar el reloj no prolonga sesiones y limita vencimientos excesivos causados por fechas futuras.
- Prueba explícita del 29 de febrero y conservación de importes/deduplicación.

### Conservación de respaldos

- Orden de publicación persistido en cada destino, independiente de nombres y reloj corregido; mantiene límites de 30 diarias y 90 automáticas.
- Copias previas a operaciones destructivas no se incluyen en la depuración automática.
- Un registro de orden ilegible no autoriza borrar copias. Fallar al registrar conservación no impide copiar una instantánea ya verificada al segundo destino; se muestra aviso.
- Pruebas con fechas futuras de nombres y archivos, posterior corrección, límites independientes, registros corruptos y fallos de sincronización dirigidos a la copia del USB.

## Sin publicar · Fase 1, punto 1 · 11 de octubre de 2026

- Aviso persistente para Administrador y Caja cuando falta el segundo destino, no hay copia externa confirmada, la copia externa tiene más de tres días o el último respaldo falló. Visible también antes de confirmar la tasa; permanece al buscar y filtrar, sin botón de cierre.
- Estado de respaldos calculado con la hora del servidor; cambiar la carpeta externa invalida la confirmación del destino anterior. Los errores al guardar el estado permanecen visibles hasta completar una copia nueva.
- Revisión de ACL y BitLocker en segundo plano, de solo lectura, sin elevación. Si Windows no permite la consulta, el resultado es «No se pudo comprobar».
- Guías y pruebas de estados, límites de antigüedad, permisos por perfil, actualización del aviso y diagnóstico de Windows.
- Sin migración de esquema ni cambios en datos existentes, carpeta de datos, transacciones de cobros, respaldos de cinco minutos, móvil/PWA o módulo de nómina.
- Validación: Linux, 158 descubiertas (157 correctas y una omitida); Windows, 158 correctas. Navegadores normal, Pruebas e importación correctos. Instalador 1.0.26 en borrador, con validación nativa y conservación de datos.
- Pendiente: comprobación de BitLocker/ACL en la PC del colegio y revisión de las alertas de Defender anteriores. Los análisis del runner no certifican esa PC.

## Seguimiento del punto 1

- Aclarado en pantalla: copia escrita en la carpeta, no subida a la nube.
- Aviso propio por mismo disco, y estado desconocido cuando no puede verificarse.
- Ayuda para comprobar BitLocker/ACL desde Windows con los permisos adecuados, sin elevar Aula.
- Prueba adicional: Pruebas no muestra avisos reales. Sin cambios de esquema ni datos existentes.

Validación del seguimiento: 161 descubiertas en Linux (160 correctas, una exclusiva de Windows omitida); navegadores normal, Pruebas e importación correctos. La consulta física de Windows y su revisión en la PC del colegio no se certifican con estas pruebas Linux.

## Validación del punto 2 · instalador 1.0.27 en borrador

- Linux: 186 descubiertas, 185 correctas y una exclusiva de Windows omitida; navegadores normal, Pruebas e importación correctos. Windows: 186 correctas, instalación, ventanas, reinstalación y desinstalación conservando datos.
- Intento 1 detenido al fallar actualización de firmas; no se analizó ni ejecutó el instalador. Un único reintento en runner nuevo pasó ambos análisis de Defender sin detecciones, motor 1.1.26080.3 y firmas 1.459.680.0.
- ZIP de código fuente antiguo retirado del borrador y actualización del ZIP del repositorio con verificación de módulos del reloj. El ejecutable validado no cambia.
- No se comenzó el cifrado del punto 3. Sin migración SQLite, cambio de ubicación ni modificación de datos contables anteriores.
