# Bitácora protegida · A4

## Uso diario

Abre **Configuración → Bitácora** con tu usuario Administrador. Muestra las últimas 300 operaciones. **Buscar** consulta toda la historia con fechas y texto; **Ver detalle** despliega los valores anteriores y nuevos. **PDF** y **CSV** exportan todas las operaciones de esos filtros, aunque no estén en las primeras 300. La búsqueda conserva los borradores de otros apartados de Configuración. El CSV protege frente a nombres que Excel podría interpretar como fórmulas. Las fechas de filtro son días de Venezuela; los archivos identifican las fechas de registro UTC. Caja y Consulta no pueden abrir ni exportar este visor.

No necesitas crear otra contraseña. Las contraseñas de Aula y de respaldos siguen siendo las mismas.

**Vaciar registros conserva toda la bitácora**, sus huellas y los usuarios. Añade quién vació, cuándo, las cantidades revisadas y la ruta del respaldo previo. No hay borrado ni retención automática de la bitácora. Un saldo de $0 tampoco autoriza borrar historia financiera.

Las ediciones guardan los campos que realmente cambiaron, calculados desde las filas de SQLite dentro de la misma transacción. Se registra el usuario autenticado; procesos automáticos y recuperación local quedan identificados como tales. No se guardan contraseñas, hashes de contraseñas, cookies, tokens ni claves de respaldo. Los cambios de datos bancarios personales se señalan sin copiar los números; un logo se identifica por su huella, sin duplicar la imagen. A4 no cambió quién podía ver la nómina; A5 restringe sus datos bancarios y documentos a Administración. [Acceso por perfil](privilegios-personal.md).

## Verificación y límites

Cada fila tiene una huella SHA-256 que incorpora su contenido, la cadena, el límite histórico de migración y la huella anterior. La revisión también detecta disparadores de protección retirados o modificados. Unas tablas acompañantes conservan las huellas: las filas originales no se reescriben. SQLite rechaza inserciones ajenas al mecanismo de Aula y modificaciones o borrados de la bitácora. Un control separado, `colegio.sqlite3.audit-head.json`, conserva la última huella para detectar también la eliminación de un final coherente.

**Verificar datos y cobros**, en Protección y mantenimiento, comprueba también la cadena y ese control. Un respaldo se comprueba en una copia temporal con su cadena interna. El archivo cifrado conserva además la autenticación de A2; el control separado de la PC no forma parte del archivo portable.

Las huellas **detectan alteraciones; no impiden que quien controle Windows cambie la base y todos los controles**. No son una firma independiente ni prueba de lo ocurrido antes de instalar A4. Los detalles históricos pueden tener otro formato de operador; se muestran con tolerancia, sin impedir la consulta ni reescribirlos. Los registros anteriores a la migración se conservan y se marcan como protegidos desde esa revisión. Un respaldo anterior a A4 se identifica como bitácora antigua sin cadena.

Si falla la comprobación, Aula muestra **Solo consulta: revisa la bitácora**. Se impiden nuevas modificaciones, cobros y generación automática o manual de mensualidades, incluso al iniciar o consultar reportes. Se mantienen ingreso, consulta, verificación, exportación de bitácora y creación de una copia local para preservar la información. Una copia externa no se da por comprobada si su cadena falla. Conserva la carpeta completa y pide revisión técnica; no borres ni recrees controles para ocultar el aviso.

`colegio.sqlite3.audit-pending.json` permite resolver un corte entre confirmar la transacción SQLite y publicar su última huella. Al siguiente inicio se comprueba si quedó la versión anterior o la nueva; no se inventa historia ni se generan mensualidades antes de resolver el control. Un registro pendiente ilegible o que no coincide deja Aula en consulta. Las escrituras y la publicación del control se coordinan también entre solicitudes simultáneas; una consulta espera que esa publicación termine. Si una fila o un lote se revierte a un punto de guardado (SAVEPOINT), sus cambios descartados tampoco se incorporan a la bitácora.

## Migración segura y reversión

El esquema pasa de **10 a 11**. Antes del cambio, Aula mantiene un bloqueo de escritura, crea **antes-bitacora-…sqlite3**, comprueba integridad y referencias, sincroniza el archivo y guarda su SHA-256 en un archivo `.migration.json`. Esa copia incluye las filas originales, también sesiones; no altera registros existentes. Las tablas nuevas y sus disparadores se crean en una transacción. Una instalación nueva crea su primera cadena sin copia previa porque aún no existían datos.

Si la creación de tablas falla antes de confirmar, SQLite revierte la migración. Se conserva la copia previa. Las pruebas terminan procesos reales antes y después de confirmar para revisar ambos casos. Estas copias especiales no se borran automáticamente, quedan sin cifrar en la PC y dependen de BitLocker y los permisos de la carpeta.

Para volver a la versión anterior, cierra Aula, conserva una copia del estado nuevo y sus controles, y usa **Inicio → Restaurar respaldo** con la copia previa a la migración. Revisa y confirma el reemplazo como exige A1. Esa copia vuelve al esquema anterior; instala después el programa anterior si necesitas mantenerlo. Abrirla con la versión nueva migrará otra vez. La reversión reemplaza datos: los cambios posteriores quedan en la copia antes-restauracion, no se fusionan. No reemplaces manualmente una base abierta ni retires WAL/SHM.

## Restauraciones e historia anterior

Se mantienen la comparación de identidad/contenido, confirmaciones de pérdida, seis pisos de correlativos, informes PDF/CSV, copia previa y recuperación de cortes de A1. Restaurar una copia antigua no la migra durante el reemplazo: se migra al abrir Aula, como antes.

El usuario se conserva además por nombre, usuario y perfil al registrar una operación, aunque después cambie su nombre. El registro de restauración enlaza la huella de la historia entrante y la historia anterior, la huella y ruta de **antes-restauracion**, sus originales y los informes. Incluye el detalle de cobros/egresos ausentes o revertidos, sin cuentas bancarias ni contraseñas. La historia posterior al respaldo permanece en la copia previa completa y verificada; no se mezcla ni se borra. Sus controles se conservan además en originales-antes-restauracion. Los hechos registrados solo en esa rama se consultan técnicamente en la copia anterior; el visor de la base activa muestra la rama restaurada y su enlace.

En otra PC sigue bastando el archivo y su contraseña o clave de recuperación. La restauración confirmada establece el control local desde la cadena interna verificada. Esto no equivale a verificar un control independiente de la PC anterior. Conserva las copias previas, originales e informes sin borrado automático.

## Prueba manual con datos ficticios

1. En Aula - Pruebas, crea un grado, representante y alumno. Cambia el nombre del representante.
2. En Configuración → Bitácora, busca `edit-values`, abre el detalle y verifica nombre anterior, nuevo y usuario. Descarga PDF y CSV; comprueba filtros, legibilidad y datos.
3. En Protección y mantenimiento, ejecuta Verificar datos y cobros. Debe comprobar también la cadena. Caja/Consulta deben recibir permiso denegado al intentar el visor.
4. Para probar vaciado o restauración, usa **otra carpeta y solo datos ficticios**, nunca tus fichas reales. Guarda una copia, registra un cobro ficticio posterior y restaura la antigua con Aula cerrado: revisa pérdida, confirmación y número siguiente. Comprueba el evento restore-backup, la ruta previa, el cobro en el informe y la historia en esa copia.
5. Vacía únicamente esa base ficticia con la revisión y contraseña: las fichas desaparecen, pero las operaciones anteriores, sus huellas y reset_records permanecen en Bitácora.
6. No alteres huellas en tu base real para probar avisos. Las pruebas automatizadas usan carpetas desechables y cubren alteración, recorte y cortes del proceso.

## Evidencia de esta entrega

Validación final Linux tras corregir concurrencia: `python -m unittest discover -s tests -v`: **281 pruebas en 147.706 s**, 278 correctas y tres exclusivas de Windows omitidas. `python tests/run_browser.py`, `python tests/run_browser.py --demo` y `python tests/run_browser.py --roster`: correctos. El recorrido normal verifica filtros, descargas PDF/CSV y conservación al vaciar, además de A3 y los controles financieros anteriores.

Se añadieron **22 métodos**: 18 de cadena/migración/conservación/concurrencia y cuatro de permisos, exportación, detalles históricos y consulta segura. Incluyen procesos reales terminados en tres etapas de publicación del control y tres etapas de migración, reversión con igualdad de todas las filas originales, manipulación de contenido/final/disparadores/control separado y rechazo de cambios. Las pruebas existentes de A1 siguen ejecutándose, incluidos los cuatro cortes reales de restauración y las cuatro versiones publicadas.

Medición orientativa en Linux: comprobar 10.000 operaciones ficticias tomó 0,053 s; no es una garantía de rendimiento en otros equipos. Windows final: **281 pruebas correctas en 320.496 s, sin omisiones**, incluidas las tres omitidas en Linux (DPAPI, exclusión entre instancias y ventana nativa de revisión). El instalador **[1.0.41 en borrador](https://github.com/Eliezerti/Sistema-colegio/releases/tag/untagged-a74c40a40fbb6b05fd60)** pasó instalación, accesos, ventanas, bandeja, reinstalación y desinstalación conservando datos. Ejecución [38342112487](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38342112487), fuente `f9cb708866a887eb81a93346dc97ab9769380da2`. Defender antes/después: sin detecciones, motor 1.1.26080.3, firmas 1.459.691.0, firmas actualizadas 2026-10-12T16:06:44Z. EXE descargado: 23.264.641 bytes; SHA-256 coincidente con sidecar y ambos análisis: `7ca76e87faa003708666c7ee05aadda8206f7918e25f1729cd5ef9e1f120b8a5`.

No se probó una actualización real desde el EXE 1.0.37 en tu PC, otros usuarios de Windows, tus privilegios/BitLocker ni tus archivos reales. La prueba de reinstalación usa la misma versión y la migración se prueba con bases ficticias verificadas. Ninguna prueba se ejecutó sobre tu base del colegio. Las guías incluidas en el EXE explican el uso; la evidencia final del runner se publica después de compilar en esta guía del repositorio y el ZIP.

## Archivos de A4

`CHANGELOG.md`, `README.md`, `descargas/Aula-Windows.zip`, `descargas/Aula-Windows.sha256`, `colegio/audit_chain.py`, `colegio/audit_reports.py`, `colegio/backup_inspection.py`, `colegio/branding.py`, `colegio/db.py`, `colegio/desktop.py`, `colegio/maintenance.py`, `colegio/reset_password.py`, `colegio/reset_records.py`, `colegio/restore.py`, `colegio/restore_journal.py`, `colegio/restore_reports.py`, `colegio/server.py`, `docs/bitacora.html`, `docs/bitacora.md`, `docs/configuracion.html`, `docs/configuracion.md`, `docs/mantenimiento.html`, `docs/mantenimiento.md`, `static/app.js`, `static/style.css`, `tests/audit_helpers.py`, `tests/browser.cjs`, `tests/test_audit_api.py`, `tests/test_audit_chain.py`, `tests/test_backup_alerts.py`, `tests/test_backup_crypto.py`, `tests/test_billing_start.py`, `tests/test_clock_endpoints.py`, `tests/test_clock_guard.py`, `tests/test_desktop.py`, `tests/test_historical_restore.py`, `tests/test_production_review.py`, `tests/test_recovery.py`, `tests/test_restore_safety.py`, `tests/test_sessions.py`, `tests/test_student_admin.py`, `tests/test_system.py`.

La primera ejecución Windows (runner 38338632948, fuente 0f26c3e) ejecutó 278 pruebas en 428.856 s y falló una por una carrera entre confirmar SQLite y publicar el control separado. Se detuvo antes de compilar el instalador. Se corrigió la coordinación, con prueba concurrente determinista y prueba de reversión de puntos de guardado; la ejecución final anterior ya verifica esa corrección. La revisión intermedia 1.0.39 pasó 280 pruebas Windows en 398.195 s; 1.0.40 fue cancelada antes de completar para incluir el ajuste final de textos y detalles históricos, sin presentarla como prueba pasada. La entrega es 1.0.41.
