# Bitácora protegida · A4

## Uso diario

Abre **Configuración → Bitácora** con tu usuario Administrador. Muestra las últimas 300 operaciones. **Buscar** consulta toda la historia con fechas y texto; **Ver detalle** despliega los valores anteriores y nuevos. **PDF** y **CSV** exportan todas las operaciones de esos filtros, aunque no estén en las primeras 300. Las fechas de filtro son días de Venezuela; los archivos identifican las fechas de registro UTC. Caja y Consulta no pueden abrir ni exportar este visor.

No necesitas crear otra contraseña. Las contraseñas de Aula y de respaldos siguen siendo las mismas.

**Vaciar registros conserva toda la bitácora**, sus huellas y los usuarios. Añade quién vació, cuándo, las cantidades revisadas y la ruta del respaldo previo. No hay borrado ni retención automática de la bitácora. Un saldo de $0 tampoco autoriza borrar historia financiera.

Las ediciones guardan los campos que realmente cambiaron, calculados desde las filas de SQLite dentro de la misma transacción. Se registra el usuario autenticado; procesos automáticos y recuperación local quedan identificados como tales. No se guardan contraseñas, hashes de contraseñas, cookies, tokens ni claves de respaldo. Los cambios de datos bancarios personales se señalan sin copiar los números; un logo se identifica por su huella, sin duplicar la imagen. Esta fase no cambia quién puede ver la nómina: esa revisión queda para A5.

## Verificación y límites

Cada fila tiene una huella SHA-256 que incorpora su contenido, la cadena, el límite histórico de migración y la huella anterior. La revisión también detecta disparadores de protección retirados o modificados. Unas tablas acompañantes conservan las huellas: las filas originales no se reescriben. SQLite rechaza inserciones ajenas al mecanismo de Aula y modificaciones o borrados de la bitácora. Un control separado, `colegio.sqlite3.audit-head.json`, conserva la última huella para detectar también la eliminación de un final coherente.

**Verificar datos y cobros**, en Protección y mantenimiento, comprueba también la cadena y ese control. Un respaldo se comprueba en una copia temporal con su cadena interna. El archivo cifrado conserva además la autenticación de A2; el control separado de la PC no forma parte del archivo portable.

Las huellas **detectan alteraciones; no impiden que quien controle Windows cambie la base y todos los controles**. No son una firma independiente ni prueba de lo ocurrido antes de instalar A4. Los registros anteriores a la migración se conservan y se marcan como protegidos desde esa revisión. Un respaldo anterior a A4 se identifica como bitácora antigua sin cadena.

Si falla la comprobación, Aula muestra **Solo consulta: revisa la bitácora**. Se impiden nuevas modificaciones, cobros y generación automática o manual de mensualidades, incluso al iniciar o consultar reportes. Se mantienen ingreso, consulta, verificación, exportación de bitácora y creación de una copia local para preservar la información. Una copia externa no se da por comprobada si su cadena falla. Conserva la carpeta completa y pide revisión técnica; no borres ni recrees controles para ocultar el aviso.

`colegio.sqlite3.audit-pending.json` permite resolver un corte entre confirmar la transacción SQLite y publicar su última huella. Al siguiente inicio se comprueba si quedó la versión anterior o la nueva; no se inventa historia ni se generan mensualidades antes de resolver el control. Un registro pendiente ilegible o que no coincide deja Aula en consulta.

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

La validación completa de Python, navegador normal, Pruebas e importación y, cuando esté disponible, el instalador Windows se incorpora aquí al cerrar A4. No se considera una prueba pasada hasta que termine con resultado correcto.
