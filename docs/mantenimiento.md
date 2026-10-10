# Usar y mantener Aula en una PC

## Instalar por primera vez

1. Usa Windows 10/11 de 64 bits y descarga el instalador de esta versión desde la publicación del repositorio. Comprueba que Defender no lo bloquee; una detección requiere detener la instalación y revisar el archivo, no añadir exclusiones.
2. Ejecuta el .exe con la cuenta de Windows que utilizará el colegio. No necesitas instalar Python. WebView2 de Microsoft puede necesitar internet la primera vez.
3. Abre **Aula - Administración escolar** desde el escritorio. Esta versión inicia localmente, sin configurar teléfonos ni otras computadoras.
4. Escribe el nombre del colegio, tu nombre, usuario y una contraseña de al menos diez caracteres. Conserva el usuario y la contraseña en un lugar seguro.
5. Confirma la tasa BCV vigente del día. En Configuración completa razón social, RIF, domicilio fiscal, tipo de institución, teléfono, correo y logo.
6. Define calendario y fecha de vencimiento antes de matricular. Crea los grados/secciones y cargos del personal según tu colegio; no existen catálogos académicos universales obligatorios.
7. Configura la segunda carpeta de respaldos, por ejemplo `E:\RespaldosColegio` para un USB o una carpeta local sincronizada por Drive. Tiene que estar fuera de la carpeta de datos de Aula.
8. Abre **Aula - Pruebas** para practicar con acceso de administrador. Los datos de esa sesión se eliminan al cerrar su ventana y nunca se mezclan con los reales.

## Dónde están los datos

El programa está en `%LOCALAPPDATA%\Programs\AulaColegio` y la base en `%LOCALAPPDATA%\AulaColegio\colegio.sqlite3`. Configuración muestra la ruta exacta. **Abrir carpeta de datos**, en Inicio, abre la carpeta correspondiente.

Usa siempre la misma cuenta de Windows: otra cuenta tiene otra carpeta local y puede ver una instalación vacía. No se migra la carpeta automáticamente a ProgramData ni se sustituyen bases existentes. No trabajes sobre una base SQLite dentro de Drive o un USB; allí se guardan únicamente copias verificadas.

Cerrar la ventana principal con X oculta Aula junto al reloj. Para cerrar completamente: menú Colegio → **Salir y cerrar Aula**, o clic derecho en el icono junto al reloj → esa misma opción. El modo prueba sí termina al cerrar su ventana.

## Editar y corregir registros

Las acciones requieren perfil Administrador. En Alumnos y Representantes, Editar y Eliminar del directorio aparecen en la columna Acciones de la derecha. Eliminar del directorio archiva la ficha, conserva su historial y permite recuperarla con Mostrar archivados. Un alumno archivado queda inactivo; sus deudas existentes siguen registradas y dejan de generarse mensualidades nuevas. Un representante vinculado a alumnos sin archivar requiere reasignar esos alumnos o archivar sus fichas antes.

En Grados y secciones, Eliminar solo permite quitar grados sin alumnos vinculados, incluidos inactivos y archivados. Se exige motivo y confirmación escrita. Las operaciones de archivo, recuperación, eliminación de grados y corrección mensual crean una copia previa y otra después de guardar; si falla la copia local previa, no se confirma la operación.

Para corregir septiembre cuando el cobro debía comenzar en octubre: Morosidad → Cuenta → Corregir mensualidades → primer mes correcto octubre → revisar septiembre e importe → escribir el motivo → confirmar. La corrección anula los cargos anteriores sin pagos y fija el primer mes; no borra movimientos ni modifica recibos antiguos. Si ya habías vuelto a poner octubre en la ficha, también puedes anular el septiembre que quedó registrado. Si hay pagos aplicados o un convenio vigente, revisa esos movimientos antes: la corrección se bloquea.

Para un cargo individual usa Cuenta → Anular cargo con motivo. Adelantar el primer mes hacia un mes anterior en una edición exige confirmación adicional: puede generar nuevas mensualidades. Cambiar una fecha por sí solo no elimina cargos existentes.

La fecha de nacimiento es opcional. Si no la tienes, déjala vacía: la constancia dice Fecha de nacimiento: Pendiente. El mes de inicio del cobro se imprime como OCT. 2026. Se conserva la información original de las constancias archivadas.

## Rutina diaria

- Consulta la tasa oficial y confírmala antes de trabajar. Una variación mayor del 10 % requiere confirmación adicional. Cada cobro conserva su tasa original.
- No hace falta generar mensualidades para ver la deuda: las matrículas activas generan automáticamente los meses transcurridos completos desde el primer mes a cobrar, dentro de su ciclo. En una matrícula nueva se propone el mes de carga, aunque el período académico haya empezado antes. No hay prorrateo por días.
- Antes de guardar un cobro revisa alumno, fecha, moneda, importe y referencia. Los abonos se aplican a los cargos pendientes más antiguos.
- El recibo indica abono o pago completo sobre la deuda registrada del alumno, deuda anterior, importe aplicado y saldo pendiente al cobrar. Ese saldo no cambia con pagos posteriores; no es una constancia de solvencia. El saldo de un concepto puede ser cero y todavía quedar deuda de otro mes.
- Revisa **Último respaldo** y los avisos de error. Configuración → **Crear respaldo ahora** crea una copia verificada y la copia al segundo destino configurado. **Descargar copia** guarda otro archivo donde elijas.
- Al terminar, usa Cierre de caja, cuenta el efectivo por moneda y compara el arqueo. Conserva el documento del cierre.
- Antes del siguiente ciclo usa Alumnos → **Pase de año / grados**: revisa promoción, repitentes, retiros y exclusiones; confirma la vista previa. Las deudas previas no se borran al pasar de grado.

## Respaldos y cortes de electricidad

Aula usa SQLite WAL con `synchronous=FULL`; los cobros y sus aplicaciones se guardan en una transacción. Hay respaldos después de operaciones financieras y cada cinco minutos mientras está abierto. Se conservan 90 copias recientes y 30 diarias locales; el segundo destino conserva 90 recientes.

Una transacción no protege contra toda falla del disco, sistema operativo o suministro. Usa un UPS. Activa cifrado de disco de Windows, como BitLocker si tu equipo lo permite, y conserva su clave de recuperación fuera de la PC. Aula no cifra por sí misma su archivo SQLite; protege también los respaldos externos.

El error de un segundo respaldo no borra ni repite un cobro ya confirmado; se muestra un aviso. Una carpeta de Drive se sincroniza mediante el cliente de Drive cuando tenga conexión: Aula no comprueba que la copia ya haya llegado al servicio en la nube.

## Actualizar sin perder registros

1. En la versión que está funcionando, crea un respaldo y descarga otra copia. Comprueba la fecha y guarda una fuera de este disco.
2. Cierra Aula completamente, incluido el icono junto al reloj.
3. Ejecuta el nuevo instalador con la **misma cuenta de Windows**. No borres la carpeta de datos y no uses Vaciar registros.
4. Abre Aula, confirma la tasa y comprueba los alumnos, un saldo conocido y el último recibo.
5. Usa Configuración → **Verificar datos y cobros**. Comprueba integridad SQLite, relaciones, aplicaciones de cobros y coherencia de mensualidades. No repara ni modifica datos.
6. Si detecta un problema, guarda una copia y solicita revisión. No reinstales repetidamente ni borres WAL/SHM intentando arreglar una base activa.

Las actualizaciones conservan la base y crean una copia antes de actualizar el esquema. Desinstalar el programa conserva los datos. No abras una base actualizada con una versión antigua: las versiones anteriores no reconocen el primer mes a cobrar y podrían generar mensualidades previas. Conserva el respaldo anterior a la actualización para cualquier revisión. Una verificación correcta no equivale a una auditoría contable completa ni garantiza que los datos introducidos sean correctos.

## Enviar información diaria al colegio

Si el personal solo necesita ver pagos y morosidad, utiliza un PDF diario: no hace falta instalar otra base de Aula ni restaurarla para leerlo.

1. Al terminar de registrar los movimientos del día, abre **Reportes → Reporte diario PDF**.
2. Revisa los cobros con fecha de hoy, sus referencias y los totales. Los nombres, representante y grado del cobro proceden del recibo conservado; no se sustituyen por una edición posterior. Se separan los dólares realmente recibidos, los bolívares realmente recibidos y el equivalente USD original de los cobros válidos. Las anulaciones quedan identificadas y fuera de los totales.
3. Revisa **Morosidad actual**: alumnos con deuda vencida, grado, representante y teléfono, importe vencido y mayor atraso. Incluye también deudas de fichas archivadas. Es el corte al generar el documento, no una reconstrucción histórica de otra fecha.
4. Pulsa **Descargar PDF** y envía el archivo `reporte-diario-AAAA-MM-DD.pdf` por correo. El personal lo abre o imprime como cualquier PDF; no debe usar Restaurar respaldo para este documento.
5. Vuelve a generar el PDF si guardaste cobros o correcciones después de descargarlo. Indica la fecha y hora del reporte para que sepan hasta qué momento llega la información.

El envío es manual desde tu correo; Aula genera el documento, pero no lo envía automáticamente. Mantén los respaldos completos como protección de los datos; un PDF no permite recuperar toda la base ni modificar registros. Si necesitan registrar cobros desde el colegio, un reporte no reemplaza el acceso a la base principal.

## Llevar tus datos a otra PC para mostrar Aula

1. En la PC donde estás cargando los datos, entra como administrador y abre Configuración → Crear respaldo ahora. Después pulsa Descargar copia y guarda el archivo `colegio-AAAA-MM-DD.sqlite3` en un USB. La descarga es una copia completa y consistente; no copies la base activa de la carpeta de datos.
2. Lleva también el instalador de Aula. En el colegio instala la misma versión o una más reciente, con la cuenta de Windows que usarán en esa PC. No abras el respaldo con una versión anterior.
3. Cierra Aula completamente en la PC del colegio, incluida la bandeja junto al reloj. Desde Inicio de Windows abre Restaurar respaldo, selecciona el `.sqlite3` del USB y escribe RESTAURAR. Esto reemplaza los datos que hubiera en esa PC; no fusiona bases. Si ya hay datos importantes allí, descarga primero una copia de ellos.
4. Abre Aula e inicia sesión con el usuario y la contraseña de Aula que ya usas en tu PC. El respaldo lleva alumnos, representantes, personal, cargos, pagos, recibos, usuarios, logo y configuración guardados en la base.
5. Confirma la tasa del día; compara la cantidad de alumnos, un saldo conocido y el último recibo. Ejecuta Configuración → Verificar datos y cobros. Revisa también la segunda carpeta de respaldos: la ruta de tu PC puede no existir en la del colegio; configura el USB o destino que tenga esa computadora.
6. Las dos instalaciones son independientes. Un cobro o edición en el colegio no aparecerá en casa automáticamente. Para usar esta etapa en una sola PC, decide cuál será la base principal y realiza allí los cambios reales. Llevar después otra copia reemplaza la base completa; no combina cambios de ambas computadoras.

### Enviar un respaldo por correo cada 2 o 3 días

Si la PC de casa es la base principal, crea allí un usuario **Consulta** para el colegio en Configuración → Usuarios antes de descargar el respaldo. En casa se registran los cambios reales; en el colegio consultan la copia recibida, con información hasta la fecha de ese respaldo.

- **Desde casa:** Crear respaldo ahora → Descargar copia → adjuntar el `.sqlite3` al correo e indicar su fecha. Si el correo no admite esa extensión, envíalo comprimido en ZIP. Si supera su límite de tamaño, utiliza un USB o un enlace privado a la copia.
- **En el colegio:** descargar y extraer el ZIP si corresponde → guardar un respaldo de la base actual → cerrar Aula completamente → Inicio de Windows → Restaurar respaldo → seleccionar la copia recibida → escribir RESTAURAR → abrir Aula, confirmar tasa y comprobar alumnos, saldos y último recibo → entrar con el usuario Consulta.
- No necesitan reinstalar el programa en cada envío. El respaldo actualiza datos; el instalador actualiza el programa. El colegio debe tener la misma versión o una más reciente que la usada para generar la copia.
- Si registran un cobro, matrícula o edición en el colegio, la próxima restauración lo reemplazaría. Este procedimiento no sirve para trabajar con modificaciones reales simultáneas en ambas computadoras. Mantén también la copia anterior por si hay que revisar una diferencia.

Para demostrar operaciones ficticias utiliza Aula - Pruebas. Ese perfil comienza vacío y se elimina al cerrar; no reutiliza ni altera la base real restaurada.

## Recuperar usuarios y contraseñas

Si otro administrador puede entrar: Configuración → Usuarios → **Cambiar clave**. Puede restablecer claves de Administración, Caja y Consulta. El nombre de usuario figura en esa tabla.

Si nadie puede entrar:

1. Cierra Aula completamente.
2. En Inicio de Windows abre **Recuperar clave del administrador**.
3. La herramienta muestra los nombres y usuarios de administradores existentes. Escribe el usuario que deseas recuperar.
4. Escribe dos veces una contraseña nueva de al menos diez caracteres.
5. Se crea un respaldo previo, se cambia la clave y se invalidan las sesiones de esa cuenta; abre Aula otra vez.

La herramienta funciona localmente, necesita acceso a esta cuenta de Windows y no revela las claves existentes. No crea una base vacía si falta la base. No permite recuperar desde internet. Para recuperar Caja o Consulta, recupera primero un administrador y cambia sus claves desde él.

## Restaurar una copia

1. Guarda el archivo de respaldo .sqlite3 en la PC y confirma de qué fecha es. No es el instalador ni un PDF.
2. Cierra Aula completamente.
3. En Inicio abre **Restaurar respaldo** y selecciona esa copia.
4. Escribe **RESTAURAR** solo si quieres reemplazar toda la base con esa versión. La restauración valida el archivo y conserva el estado anterior cuando puede hacerlo; una base dañada se conserva para análisis.
5. Abre Aula y revisa saldos, últimos cobros y usuarios. Se recuperan las contraseñas y configuración que había al hacer esa copia.

La restauración no fusiona bases: los cobros posteriores a la copia seleccionada no estarán en los datos restaurados. Conserva los comprobantes y consulta antes de volver a registrar un cobro que podría duplicarse. No existe recuperación garantizada si falla el disco y todas las copias estaban en el mismo disco.

## Vaciar registros

No se necesita para actualizar, importar, pasar de año ni hacer pruebas. Es una operación destructiva reservada a administración avanzada: exige contraseña, revisión de cantidades, frase de confirmación y respaldo previo verificado en ambos destinos cuando existe una segunda carpeta. Conserva usuarios y configuración, pero borra registros administrativos y financieros. Para practicar usa **Aula - Pruebas**.
