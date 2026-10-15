# Bitácora protegida · A4

## Uso diario

Abre **Configuración → Bitácora** con tu usuario Administrador. Muestra las últimas 300 operaciones. **Buscar** consulta toda la historia con fechas y texto; **Ver detalle** despliega los valores anteriores y nuevos. **PDF** y **CSV** exportan todas las operaciones de esos filtros, aunque no estén en las primeras 300. La búsqueda conserva los borradores de otros apartados de Configuración. El CSV protege frente a nombres que Excel podría interpretar como fórmulas. Las fechas de filtro son días de Venezuela; los archivos identifican las fechas de registro UTC. Caja y Consulta no pueden abrir ni exportar este visor.

No necesitas crear otra contraseña. Las contraseñas de Aula y de respaldos siguen siendo las mismas.

No existe una función de vaciado global en producción. La bitácora no se borra ni rota automáticamente. Un saldo de $0 no autoriza borrar historia financiera.

## Verificación y límites

Cada fila tiene una huella SHA-256 que incorpora su contenido, la cadena, el límite histórico de migración y la huella anterior. La revisión también detecta disparadores de protección retirados o modificados. Unas tablas acompañantes conservan las huellas: las filas originales no se reescriben. SQLite rechaza inserciones ajenas al mecanismo de Aula y modificaciones o borrados de la bitácora. Un control separado, `colegio.sqlite3.audit-head.json`, conserva la última huella para detectar también la eliminación de un final coherente.

**Verificar datos y cobros**, en Protección y mantenimiento, comprueba también la cadena y ese control. Un respaldo se comprueba en una copia temporal con su cadena interna. El archivo cifrado conserva además la autenticación de A2; el control separado de la PC no forma parte del archivo portable.

Las huellas **detectan alteraciones; no impiden que quien controle Windows cambie la base y todos los controles**. No son una firma independiente ni prueba de lo ocurrido antes de instalar A4. Los detalles históricos pueden tener otro formato de operador; se muestran con tolerancia, sin impedir la consulta ni reescribirlos. Los registros anteriores a la migración se conservan y se marcan como protegidos desde esa revisión. Un respaldo anterior a A4 se identifica como bitácora antigua sin cadena.

Si falla la comprobación, Aula muestra **Solo consulta: revisa la bitácora**. Se impiden nuevas modificaciones, cobros y generación automática o manual de mensualidades, incluso al iniciar o consultar reportes. Se mantienen ingreso, consulta, verificación, exportación de bitácora y creación de una copia local para preservar la información. Una copia externa no se da por comprobada si su cadena falla. Conserva la carpeta completa y pide revisión técnica; no borres ni recrees controles para ocultar el aviso.

`colegio.sqlite3.audit-pending.json` permite resolver un corte entre confirmar la transacción SQLite y publicar su última huella. Al siguiente inicio se comprueba si quedó la versión anterior o la nueva; no se inventa historia ni se generan mensualidades antes de resolver el control. Un registro pendiente ilegible o que no coincide deja Aula en consulta. Las escrituras y la publicación del control se coordinan también entre solicitudes simultáneas; una consulta espera que esa publicación termine. Si una fila o un lote se revierte a un punto de guardado (SAVEPOINT), sus cambios descartados tampoco se incorporan a la bitácora.

## Restauraciones e historia anterior

Se mantienen la comparación de identidad/contenido, confirmaciones de pérdida, seis pisos de correlativos, informes PDF/CSV, copia previa y recuperación de cortes de A1. Restaurar una copia antigua no la migra durante el reemplazo: se migra al abrir Aula, como antes.

El usuario se conserva además por nombre, usuario y perfil al registrar una operación, aunque después cambie su nombre. El registro de restauración enlaza la huella de la historia entrante y la historia anterior, la huella y ruta de **antes-restauracion**, sus originales y los informes. Incluye el detalle de cobros/egresos ausentes o revertidos, sin cuentas bancarias ni contraseñas. La historia posterior al respaldo permanece en la copia previa completa y verificada; no se mezcla ni se borra. Sus controles se conservan además en originales-antes-restauracion. Los hechos registrados solo en esa rama se consultan técnicamente en la copia anterior; el visor de la base activa muestra la rama restaurada y su enlace.

En otra PC sigue bastando el archivo y su contraseña o clave de recuperación. La restauración confirmada establece el control local desde la cadena interna verificada. Esto no equivale a verificar un control independiente de la PC anterior. Conserva las copias previas, originales e informes sin borrado automático.

