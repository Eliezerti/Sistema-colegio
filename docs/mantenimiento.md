> A2: los respaldos externos/descargados son .aulabak cifrados. Las copias .sqlite3 anteriores siguen admitidas con advertencia. Consulta [la guía de cifrado](cifrado-respaldos.md) antes de configurar o llevar copias.

# Usar y mantener Aula en una PC

## Instalar por primera vez

1. Usa Windows 10/11 de 64 bits y descarga el instalador de esta versión desde la publicación del repositorio. Comprueba que Defender no lo bloquee; una detección requiere detener la instalación y revisar el archivo, no añadir exclusiones.
2. Ejecuta el .exe con la cuenta de Windows que utilizará el colegio. No necesitas instalar Python. WebView2 de Microsoft puede necesitar internet la primera vez.
3. Abre **Aula - Administración escolar** desde el escritorio. Esta versión inicia localmente, sin configurar teléfonos ni otras computadoras.
4. Escribe el nombre del colegio, tu nombre, usuario y una contraseña de al menos diez caracteres. Conserva el usuario y la contraseña en un lugar seguro.
5. Confirma la tasa BCV vigente del día. En Configuración completa razón social, RIF, domicilio fiscal, tipo de institución, teléfono, correo y logo.
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

Si Aula pide revisar el reloj, no permite cobrar, generar mensualidades ni emitir documentos hasta que el Administrador confirme la fecha y hora correctas. El avance permitido entre aperturas es siete días y la tolerancia de ajustes es dos minutos. Una revisión inicial puede aparecer al actualizar una base con actividad sin archivo de control. [Cómo resolver la revisión](proteccion-reloj.md).

Aula usa SQLite WAL con `synchronous=FULL`; los cobros y sus aplicaciones se guardan en una transacción. Hay respaldos después de operaciones financieras y cada cinco minutos mientras está abierto. Se conservan 90 copias recientes y 30 diarias locales; el segundo destino conserva 90 recientes.

El orden de conservación se registra al publicar cada copia, sin depender de la fecha de su nombre. Los respaldos con una fecha futura no eliminan una copia nueva después de corregir Windows. Un registro ilegible no autoriza depurar; una copia ya verificada puede llegar al segundo destino aunque falle el registro de conservación. Revisa el aviso y el espacio disponible.

Una transacción no protege contra toda falla del disco, sistema operativo o suministro. Usa un UPS. Activa cifrado de disco de Windows, como BitLocker si tu equipo lo permite, y conserva su clave de recuperación fuera de la PC. Aula no cifra por sí misma su archivo SQLite; protege también los respaldos externos.

El error de un segundo respaldo no borra ni repite un cobro ya confirmado; se muestra un aviso. Una carpeta de Drive se sincroniza mediante el cliente de Drive cuando tenga conexión: Aula no comprueba que la copia ya haya llegado al servicio en la nube.

Administrador y Caja ven un aviso permanente cuando falta configurar la segunda carpeta, no hay una copia externa confirmada, la última tiene más de tres días o falló el último respaldo. No se puede cerrar: permanece en todas las secciones y al confirmar la tasa. Se actualiza cada 30 segundos con la pantalla visible y al volver a ella. Consulta y Pruebas no lo muestran. Administrador puede ir a Configuración; Caja debe solicitar su ayuda.

En Configuración → Protección y mantenimiento aparecen **BitLocker** y **Permisos de la carpeta de datos**. Es una revisión de solo lectura en segundo plano, cada cinco minutos. Aula no cambia permisos ni activa cifrado. Si Windows no permite comprobarlos, se muestra **No se pudo comprobar**. Las copias locales de cinco minutos mantienen su comportamiento; los respaldos todavía no están cifrados. Consulta la [guía de avisos y revisión de Windows](proteccion-respaldos.md).

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

## Consultar desde otra PC

Descarga una copia cifrada de la base principal y llévala a la otra PC. Usa Inicio → Aula → Abrir copia en solo lectura, con contraseña o recuperación. El aviso permanente identifica la copia. No restaures una base solo para mirarla: la consulta temporal no puede mezclarse con los datos reales ni registrar cobros.

Si necesitas trasladar la operación real a otra PC, haz un respaldo verificado, cierra Aula por completo y utiliza Restaurar respaldo en la nueva carpeta de datos. La restauración reemplaza toda la base y no fusiona cambios de dos computadoras. Decide cuál será la PC principal y registra allí los movimientos reales. Consulta las guías de restauración y puesta en producción.

## Recuperar usuarios y contraseñas

Si otro administrador puede entrar: Configuración → Usuarios → **Cambiar clave**. Puede restablecer claves de Administración, Caja y Consulta. El nombre de usuario figura en esa tabla.

Si nadie puede entrar:

1. Cierra Aula completamente.
2. En Inicio de Windows abre **Recuperar clave del administrador**.
3. La herramienta muestra los nombres y usuarios de administradores existentes. Escribe el usuario que deseas recuperar.
4. Escribe dos veces una contraseña nueva de al menos diez caracteres.
5. Se crea un respaldo previo, se cambia la clave y se invalidan todas las sesiones y cada administrador recibe un aviso al ingresar; abre Aula otra vez.

La herramienta funciona localmente, necesita acceso a esta cuenta de Windows y no revela las claves existentes. No crea una base vacía si falta la base. No permite recuperar desde internet. Para recuperar Caja o Consulta, recupera primero un administrador y cambia sus claves desde él.

## Restaurar una copia

1. Guarda el archivo de respaldo .aulabak (o .sqlite3 antiguo sin cifrar) en la PC y confirma de qué fecha es. No es el instalador ni un PDF.
2. Cierra Aula completamente.
3. En Inicio abre **Restaurar respaldo** y selecciona esa copia.
4. Escribe **RESTAURAR** solo si quieres reemplazar toda la base con esa versión. La restauración valida el archivo y conserva el estado anterior cuando puede hacerlo; una base dañada se conserva para análisis.
5. Abre Aula y revisa saldos, últimos cobros y usuarios. Se recuperan las contraseñas y configuración que había al hacer esa copia.

La restauración no fusiona bases: los cobros posteriores a la copia seleccionada no estarán en los datos restaurados. Conserva los comprobantes y consulta antes de volver a registrar un cobro que podría duplicarse. No existe recuperación garantizada si falla el disco y todas las copias estaban en el mismo disco.

## Producción y pruebas

En producción no existe Vaciar registros. Para practicar abre Aula - Pruebas y cierra su última ventana al terminar; solo se elimina esa carpeta temporal. Para comenzar la operación real utiliza una carpeta nueva y vacía, siguiendo [Puesta en producción](puesta-en-produccion.md).

## Llevar alumnos a Aula - Pruebas

1. Actualiza Aula con la misma cuenta de Windows, sin la operación del colegio. Crea antes un respaldo externo.
2. En la aplicación real abre Alumnos y matrículas → Exportar Excel / CSV → Exportar Excel (.xlsx). Guarda el archivo.
3. Abre Aula - Pruebas vacío y confirma la tasa. Si ya estabas probando, usa Cerrar y borrar pruebas y vuelve a abrirlo para comenzar vacío.
4. Revisa que el ciclo escolar y las reglas de cobro de Pruebas sean los que quieres mostrar. El nombre y logo del colegio se configuran allí por separado.
5. En Alumnos y matrículas → Importar Excel / CSV selecciona el mismo archivo exportado. No necesitas rellenar otra plantilla ni crear a mano los grados que falten.
6. Pulsa Revisar archivo. Comprueba cantidad, códigos, grados y cupos, activos/inactivos, tarifas y primer mes a cobrar. La revisión no guarda nada.
7. Revisa los cargos nuevos: el saldo de origen es informativo. Los pagos y recibos anteriores no viajan en Excel, así que los saldos de prueba pueden ser distintos.
8. Marca la casilla y pulsa Confirmar importación. Se carga todo el lote; si hay errores no se guarda ninguna fila. No lo importes dos veces.
9. Para el documento presentable, usa PDF / Imprimir en Alumnos o Representantes. El PDF de representantes identifica el estado de cada alumno.

El CSV antiguo de nueve columnas no contiene la información necesaria: vuelve a exportar desde la versión nueva. Si abres CSV en Excel y ofrece quitar ceros iniciales, elige No convertir. Para llevar toda la base real a la PC del colegio usa respaldo y restauración, no Excel. La importación no traslada representantes que no tengan alumnos vinculados.


La segunda carpeta se compara con el disco de la base: si comparte disco, aparece un aviso propio aunque la copia esté recién escrita. Si no se puede determinar, se indica. En Windows se comparan unidades y particiones; unidades distintas pueden compartir disco físico. En otros sistemas solo se confirma el mismo sistema de archivos; no se supone independencia entre volúmenes. El almacenamiento virtual y las carpetas de nube requieren comprobar su protección real. Aula no verifica la subida a la nube.

BitLocker se consulta con los permisos de la cuenta que abrió Aula; una cuenta estándar puede no tener permiso. «Cómo comprobarlo desde Windows» explica cómo revisarlo con ayuda del administrador de Windows. Una comprobación manual no convierte el resultado automático desconocido en «Activo».

## Sesiones y recuperación de acceso (A3)

Cierre tras 15 minutos sin actividad, configurable entre 5 y 60 en Usuarios y acceso. Un minuto antes aparece el aviso para seguir trabajando. Recuperación local de clave cierra todas las sesiones y avisa a cada administrador. El borrador de un formulario habitual permanece solo en memoria para el mismo usuario; recargar o cerrar la ventana lo pierde. [Guía completa de A3](sesiones-acceso.md).

## Control de la bitácora · A4

Verificar datos y cobros comprueba ahora la cadena de la bitácora y su control separado. Las rutas de vaciado están retiradas y no pueden borrar esta historia. Se conservan sin borrado automático las copias antes-bitacora y antes-restauracion, sus originales y los informes. Dependen de BitLocker y permisos locales. [Migración, reversión y límites](bitacora.md).

## Cuánto se conserva en el segundo destino

Todas las copias nuevas del segundo destino siguen cifradas. Aula conserva las últimas 90 copias frecuentes, hasta 60 copias diarias y 24 mensuales. Se guarda la primera copia verificada de cada día y de cada mes; las frecuentes contienen el movimiento posterior. Al superar cada límite se retiran únicamente las más antiguas de ese mismo nivel, por orden de publicación comprobado. Si el inventario está dañado, no se autoriza borrar copias. Los archivos manuales y permanentes no participan en esta rotación.

Antes de confirmar un pase de año revisado se crea una copia cifrada permanente del estado de cierre, en backups/cierres-permanentes y también en el segundo destino cuando está configurado. Esta copia no se elimina automáticamente. Si no puede crearse o copiarse al destino configurado, no se confirma el pase. El modo Pruebas no publica cierres ni respaldos reales. Configura el cifrado antes del pase de año.

Cada mes usa Probar respaldo con una copia tomada del USB o de la nube. Marca que seleccionaste una copia externa; Aula registra la comprobación correcta, pero no puede verificar que el navegador tomó el archivo de una nube. Tras más de 35 días aparece un recordatorio que no bloquea el trabajo. Puedes elegir «Ocultar por 7 días» en ese navegador; esto no registra una prueba ni oculta errores de respaldo. La prueba externa correcta actualiza el aviso inmediatamente. Si no marcas la casilla de copia externa, el resultado explica cómo reiniciar el plazo. Una contraseña errónea o una copia corrupta no lo reinician.

## Cierre mensual

En Reportes elige el mes y descarga PDF mensual o CSV mensual. Revisa cobros y egresos por moneda y método, saldo previo y saldo al cierre, pendiente por grado y anulaciones hechas en ese mes. El saldo suma operaciones válidas: no sustituye el conteo físico de efectivo. El pendiente se calcula con los saldos actuales de los cargos que vencen hasta el cierre; no es una foto histórica congelada. Las anulaciones se ubican por la fecha registrada en la bitácora. El informe mensual no incluye datos personales de alumnos. El reporte diario mantiene el detalle y añade un resumen de morosidad por grado.


## Cómo cobrar un mes por adelantado

1. En **Caja y cobros → Registrar pago**, elige al alumno, aunque esté al día. También puedes entrar desde su cuenta.
2. Al final de **Mensualidades · desde la más antigua**, marca los meses en gris que dicen **Por adelantado**. La selección incluye primero toda deuda anterior y no permite saltar meses. Puedes abonar parcialmente el último mes seleccionado.
3. Revisa la tarifa neta que aparece en el aviso. Al confirmar, ese mes queda con la tarifa y la beca actuales: un aumento posterior no lo recalcula. Si otro usuario cambia la tarifa o el saldo mientras tienes el formulario abierto, vuelve a abrirlo y revisa.
4. Escribe la fecha real, moneda, importe recibido, método y referencia. En bolívares se usa la tasa confirmada de esa fecha. Revisa el importe y pulsa **Registrar y emitir recibo**. No hace falta crear un cargo aparte.
5. El recibo indica **Mensualidad AAAA-MM (pagada por adelantado)**. El dinero entra en la caja del día en que se cobró; el estado de cuenta indica **Pagado por adelantado** o **Abono por adelantado**. Los informes muestran el subtotal informativo **Cobrado por adelantado (meses futuros)**: ya está incluido en ingresos, no se suma otra vez.

Por defecto puedes preparar los tres meses siguientes al actual, solo dentro del ciclo vigente, desde el primer mes a cobrar y hasta el fin de matrícula. Administración cambia el máximo (0–12) en **Configuración → Identidad y calendario → Calendario y reglas de mensualidades**. El valor 0 impide preparar nuevos meses; no borra cargos ya preparados. Si no aparece el mes, pide revisar ese límite, el ciclo, el estado de la matrícula y sus fechas.

Con beca completa, Aula ofrece **Registrar evaluación sin cobro**: deja el mes evaluado en cero, sin pago y sin usar un recibo. El día 1 no crea otro cargo por un mes ya evaluado, incluso si después cambia la tarifa o la beca.

En **Nueva venta Cashea** se usa la misma selección; **Revisar venta** no prepara los meses futuros. Al confirmar se prepara el cargo y se registran inicial y financiación con las reglas habituales. El subtotal de dinero adelantado cuenta solo la inicial realmente recibida; la financiación no es efectivo ni se cuenta dos veces.

Si Administración anula el pago o la orden Cashea, el recibo conserva su número y el cargo preparado permanece pendiente con su vencimiento normal. La mora empieza solo después de ese vencimiento. No borres ni vuelvas a crear la mensualidad. Los recibos y documentos anteriores se conservan como se emitieron.
