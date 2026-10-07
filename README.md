# Aula · Administración de colegios

Sistema administrativo para colegios de Venezuela, con una **base central en una computadora Windows**. Puede usarse en esa PC o compartirse con las laptops del colegio y de casa mediante acceso privado. Las mensualidades y la deuda se expresan en **USD**; los cobros y egresos pueden registrarse en **USD o bolívares (VES)** con la tasa BCV correspondiente a la fecha de la operación.

## Descargar el sistema

El **instalador de escritorio para Windows 10/11 de 64 bits** se publica en [Versiones e instaladores](https://github.com/Eliezerti/Sistema-colegio/releases). Descarga el archivo **Aula-Colegio-Instalador-…exe**, no el ZIP de código fuente. Incluye Python y la aplicación; no necesitas instalar Python por separado. La compilación Windows y la prueba de la ventana deben terminar correctamente para que aparezca el instalador.

### Instalar la aplicación de escritorio

1. Cierra la versión anterior de Aula. Si todavía usas un .bat, ciérralo con **Ctrl+C**. Conserva un respaldo y utiliza **la misma cuenta de Windows** que usabas para mantener la ruta de datos existente.
2. Ejecuta el instalador .exe y sigue **Siguiente → Instalar**. Deja marcada la creación de accesos directos. Puedes elegir **Abrir Aula al iniciar sesión en Windows** para la PC principal. El instalador comprueba WebView2, un componente de Microsoft para mostrar la ventana; si falta, su instalación inicial necesita internet. Después el uso local funciona sin conexión.
3. Abre **Colegio Alejandro Von Humboldt** desde el escritorio. La primera apertura pregunta cómo usar esta computadora:
   - **PC principal:** guarda los datos. Deja el enlace vacío durante la primera configuración local. Crea tu administrador si la base está vacía; si ya existía una base en `%LOCALAPPDATA%\AulaColegio`, entra con tu usuario habitual.
   - **Conectarme al colegio:** para tu casa y las otras laptops. Pega el enlace HTTPS privado de la PC principal y conecta Tailscale. Esta opción no crea una segunda base SQLite.
4. Para cambiar la conexión, cierra Aula completamente y abre **Configurar Aula** desde **Inicio → Colegio Alejandro Von Humboldt**. La configuración del equipo no cambia los alumnos, cobros o contraseñas.

La interfaz se abre en una **ventana propia**, sin consola ni navegador externo para usar el sistema. En la PC principal, pulsar **X** oculta la ventana y deja el servicio activo junto al reloj de Windows. Abre el icono junto al reloj o vuelve a hacer doble clic en el acceso directo para mostrarla. Para detener el sistema, utiliza **Colegio → Salir y cerrar Aula** o esa opción en el icono del reloj. Si el acceso compartido está activo, pide confirmación porque las otras computadoras se desconectarán. Las operaciones en curso terminan antes de liberar la base. En una laptop conectada al colegio, cerrar su ventana cierra únicamente esa aplicación; no apaga la PC principal.

El instalador incluye **Aula - Pruebas**, **Restaurar respaldo**, **Recuperar clave del administrador**, **Configurar Aula** y **Abrir carpeta de datos** en el menú Inicio. Las herramientas de recuperación usan ventanas y requieren cerrar el sistema de la PC principal. El acceso **Aula - Pruebas** abre el administrador temporal y mantiene el aislamiento descrito abajo; se elimina al cerrar su ventana. No deja el servicio de pruebas en el reloj.

Actualizar o desinstalar la aplicación no elimina `%LOCALAPPDATA%\AulaColegio`, los usuarios ni los respaldos. El programa se instala por usuario de Windows en `%LOCALAPPDATA%\Programs\AulaColegio`, separado de esa base. El instalador no mueve automáticamente datos de otra cuenta o computadora.

### Distribución de código fuente · alternativa con Python

Abre [Aula-Windows.zip](https://github.com/Eliezerti/Sistema-colegio/blob/main/descargas/Aula-Windows.zip) y pulsa **Download raw file** (icono de descarga) en GitHub. Si el repositorio es privado, inicia sesión con una cuenta que tenga acceso. El archivo [Aula-Windows.sha256](descargas/Aula-Windows.sha256) permite verificar la integridad del paquete.

El ZIP incluye los archivos del programa y los lanzadores para Windows; no incluye Python ni datos de alumnos. Descomprímelo con **Extraer todo** y sigue estos pasos.

## Instalar y abrir desde el ZIP en Windows

1. Instala **Python 3.10 o posterior**, de 64 bits, desde [python.org](https://www.python.org/downloads/windows/). En el instalador activa **Add python.exe to PATH**. No se necesitan paquetes adicionales.
2. Descomprime la carpeta del sistema en una ubicación permanente, por ejemplo `C:\Aula`.
3. Haz doble clic en **Iniciar-Aula.bat**. Se abrirá la interfaz en tu navegador. Mantén abierta la ventana de comandos durante el uso; ciérrala con **Ctrl+C** cuando termines.
4. En la primera apertura crea tu usuario administrador con una contraseña de al menos diez caracteres. No existe una contraseña predeterminada.
5. Confirma la **tasa BCV de hoy** en la pantalla **Tasas y respaldo**. Después revisa **Configuración**: el logo, la razón social, el RIF y el domicilio fiscal del colegio ya están incorporados. Completa teléfono, correo, dirección de contacto, año escolar, mes de inicio y día de vencimiento. Estos datos aparecen en los documentos nuevos.

Los datos de Windows quedan en `%LOCALAPPDATA%\AulaColegio\colegio.sqlite3`, separados del código. **Abrir-carpeta-de-datos.bat** abre esa carpeta. Actualizar o mover los archivos del programa no borra los datos. Usa la misma cuenta de Windows para abrir el sistema: cada cuenta tiene su propia carpeta local.

La interfaz utiliza el navegador; el servidor y la base de datos funcionan en la PC principal. El servidor escucha exclusivamente en `127.0.0.1`. El uso directo en esa PC funciona sin internet; para compartirlo sigue la configuración privada de la siguiente sección. La tasa BCV requiere consultarla y registrarla manualmente.

## Trabajar en el colegio y desde casa

Todos consultan y modifican **la misma base**, guardada en la PC principal del colegio. En las otras laptops solo se necesitan un navegador y **Tailscale**. Cada persona inicia sesión con su propio usuario de Aula; no lleva una copia de los alumnos o de los cobros en su laptop.

### Preparar la PC principal del colegio

1. Elige la computadora que guardará los datos y usa siempre la misma cuenta de Windows. Instala Aula con los pasos anteriores. Si los registros ya están en otra PC, descarga allí un respaldo y restáuralo en la PC principal con **Restaurar-respaldo.bat** antes de comenzar a trabajar. Desde ese momento, registra los movimientos únicamente en esta base central.
2. Abre **Iniciar-Aula.bat**. Crea el primer administrador localmente si aún no existe y, en **Configuración → Usuarios y permisos**, crea un usuario por empleado. Usa **Caja** para registrar cobros y **Consulta** para ver información; reserva **Administrador** para quien corresponda. Cierra Aula con **Ctrl+C** al terminar la configuración.
3. Instala [Tailscale para Windows](https://tailscale.com/download) e inicia sesión en tu red privada. Desde la administración de Tailscale autoriza las cuentas y los equipos que tendrán acceso. Instálalo también en tu laptop de casa y en las laptops de los empleados, conectándolos a la misma red privada autorizada.
4. En **PowerShell de la PC principal**, ejecuta:

   ```powershell
   & "$env:ProgramFiles\Tailscale\tailscale.exe" serve --bg http://127.0.0.1:8765
   ```

   Si instalaste Tailscale en otra ubicación, usa la ruta de su `tailscale.exe`. Sigue el enlace de autorización que muestre el comando si solicita habilitar HTTPS. Copia el enlace privado que te indique, con formato `https://nombre-equipo.nombre-red.ts.net`. Usa **Tailscale Serve**, que comparte el acceso dentro de tu red privada. No actives **Funnel** ni abras el puerto 8765 en el router. [Documentación de Tailscale Serve](https://tailscale.com/kb/1242/tailscale-serve).

5. Con el instalador de escritorio, abre **Configurar Aula**, selecciona **PC principal** y pega ese enlace HTTPS. Si usas el ZIP de código fuente, ejecuta **Configurar-Red.bat**. El enlace se guarda en `%LOCALAPPDATA%\AulaColegio\red.json`; no cambia los usuarios ni la base existente.
6. Con el instalador, abre el icono **Colegio Alejandro Von Humboldt**; el modo compartido se activa automáticamente con la configuración guardada. Si usas el ZIP, abre **Iniciar-Red.bat**. Mantén Aula y Tailscale activos. **Configuración → Acceso compartido del colegio** muestra el enlace. No abras otra copia del servidor con un .bat mientras la aplicación de escritorio esté activa.

### Entrar desde las laptops y desde casa

Conecta Tailscale. Puedes instalar el mismo .exe, elegir **Conectarme al colegio** y pegar el **mismo enlace HTTPS privado**: abrirás una ventana propia sin base SQLite local. También puedes abrir ese enlace en Edge o Chrome si prefieres no instalar la aplicación. Entra con tu usuario de Aula. No instales una segunda base ni Python en esas laptops. Un cobro registrado por un empleado queda en la base central y tú puedes consultarlo desde casa al cargar o actualizar la pantalla.

La PC principal y el router deben estar encendidos, con internet y sin suspensión mientras se necesite acceso desde casa. Un UPS ayuda a mantenerlos disponibles durante los cortes. Si se apaga la PC principal, el sistema compartido deja de estar disponible; los datos permanecen en esa PC y sus respaldos. El modo local sigue disponible con **Iniciar-Aula.bat** cuando no hay conexión.

Los respaldos, la restauración y la recuperación local de contraseñas se administran en la PC principal. Una carpeta de Drive o un USB sirve para copiar **respaldos**, nunca para compartir la base activa. Si cambias la PC principal o su nombre en Tailscale, vuelve a ejecutar Configurar-Red.bat con el nuevo enlace y comunica ese enlace a los usuarios. El archivo red.json es configuración del equipo, y no forma parte del respaldo SQLite.

El **modo de prueba es local y separado**: usa el acceso **Aula - Pruebas**, o Iniciar-Pruebas.bat si usas el ZIP, en la computadora donde quieras experimentar. No comparte ni abre la base real del colegio.

Esta versión valida el acceso a través de un intermediario HTTPS privado, permisos y cobros simultáneos. La instalación de Tailscale, sus permisos, los certificados HTTPS y la conexión real entre tus computadoras deben configurarse y comprobarse en esos equipos antes de trabajar con los datos del colegio.

## Probar sin mezclar datos del colegio

Haz doble clic en **Iniciar-Pruebas.bat** y pulsa **Entrar como administrador de prueba**. Tendrás permisos de administrador y una base **vacía y separada**, creada para esa sesión. Confirma una tasa de prueba y registra los alumnos, empleados, cobros y pagos que quieras. La franja **Modo prueba** permanece visible. Los recibos y PDF se identifican con **PRUEBA SIN VALIDEZ**.

Para terminar, pulsa **Cerrar y borrar pruebas**. También se cierra al salir de la última pestaña de prueba: espera unos cinco segundos. Recargar la página conserva los registros mientras siga abierta la sesión. Se pueden mantener varias pestañas; cerrar una no borra datos si queda otra. Si el navegador deja de responder sin avisar al servidor, la falta de señales de sus pestañas se detecta después de diez minutos. Puedes cerrar la ventana del programa con **Ctrl+C** para terminar antes.

Cada nueva apertura empieza vacía. Los datos temporales se eliminan al cerrar normalmente; si ocurre un corte de energía o un cierre forzado, cualquier carpeta de prueba pendiente se limpia **antes de la siguiente apertura**. Los PDF y CSV que descargues permanecen en tu carpeta de descargas: bórralos allí si ya no los necesitas. El modo de prueba no guarda respaldos ni copia datos al USB o a Drive.

**Iniciar-Aula.bat** abre los datos reales en el puerto 8765. **Iniciar-Pruebas.bat** usa el puerto 8766, otra cookie de acceso y una carpeta temporal independiente. No copia ni lee la base del colegio. No acepta `--data-dir`, para impedir que una sesión de prueba apunte a los datos reales. También puedes crear accesos directos a ambos lanzadores en el escritorio.

## Vaciar registros existentes del colegio

Actualizar el programa **no borra automáticamente** la base instalada en tu PC. Si quieres eliminar los registros cargados previamente, entra como administrador y abre **Configuración → Administración avanzada · vaciar registros → Revisar vaciado de registros**.

Se muestra la cantidad de registros que desaparecerán. Debes introducir tu contraseña, escribir **VACIAR REGISTROS** y marcar la confirmación. Antes de borrar, Aula genera un respaldo verificado `antes-vaciar-…sqlite3` en la carpeta local de respaldos y en el segundo destino si está configurado. Si falla alguna copia, se conserva la base. Esas copias no entran en la rotación de respaldos automáticos; consérvalas para poder restaurar el estado anterior.

Se eliminan alumnos, representantes, grados, empleados y sus cargos, mensualidades, pagos, egresos, cierres, tasas, convenios, seguimientos y documentos guardados. **Se conservan los usuarios, las contraseñas, el logo, los datos fiscales y la configuración.** Se cierran todas las sesiones y debes volver a entrar y confirmar la tasa. Los números de cobros, egresos y alumnos continúan después del último usado. La bitácora conserva el evento de vaciado y la ruta del respaldo; los movimientos anteriores quedan en esa copia.

Esta opción sirve para un reinicio deliberado. Para experimentar o repetir pruebas, usa **Iniciar-Pruebas.bat**, que se limpia solo. Para recuperar un vaciado, cierra el programa y usa **Restaurar-respaldo.bat** con el archivo `antes-vaciar-…sqlite3`.

## Actualizar una instalación existente

1. En Aula, descarga un respaldo de tu base y cierra el programa con **Ctrl+C**.
2. Descarga el ZIP actualizado y usa **Extraer todo** en una carpeta nueva, por ejemplo `C:\Aula-actualizado`. También puedes reemplazar los archivos del programa anterior con Aula cerrado.
3. Abre **Iniciar-Aula.bat** desde la carpeta nueva, con la **misma cuenta de Windows**. Usa tu usuario habitual: los alumnos, representantes, cobros y egresos permanecen en `%LOCALAPPDATA%\AulaColegio`.
4. La primera apertura crea un respaldo `antes-actualizacion-*.sqlite3` y amplía la base automáticamente. Esta versión incorpora una sola vez el logo y los datos fiscales suministrados del colegio. Conserva el nombre comercial configurado, el año escolar, los contactos, alumnos, cobros y documentos anteriores. Los alumnos de versiones antiguas reciben un código único y los cargos del personal se incorporan al catálogo. Completa sus datos bancarios en **Personal**.

Si usabas otro directorio de datos con un comando personalizado, conserva ese `--data-dir`; el lanzador estándar solo abre `%LOCALAPPDATA%\AulaColegio`.

### Identidad del colegio y membrete fiscal

La actualización incorpora el tipo «Unidad Educativa Colegio» en los membretes nuevos y amplía el nombre institucional abreviado del colegio. Conserva la razón social fiscal del RIF y los documentos ya emitidos. El tipo de institución también se puede editar en Configuración.

El logo PNG está incluido en el programa y aparece al entrar, en el menú y en los membretes de los documentos nuevos. No necesita internet. En **Configuración → Datos del colegio** puedes descargar el PNG y editar los datos fiscales:

- **Nombre institucional:** Unidad Educativa Colegio Alejandro Von Humboldt.
- **Tipo de institución en el membrete:** Unidad Educativa Colegio.
- **Razón social fiscal:** ALEJANDRO VON HUMBOLDT, C.A.
- **RIF:** J-50835934-8.
- **Domicilio fiscal:** Calle 48 entre carreras 16 y 17, local Nro. 16-46, sector Centro, Barquisimeto, Lara. Zona postal 3001.

El nombre comercial del colegio se configura aparte de la razón social. La dirección de contacto también se mantiene separada del domicilio fiscal. Los recibos de pagos completos y abonos, las constancias de matrícula, las relaciones de nómina y el resumen administrativo impreso usan el mismo membrete. Los PDF descargables llevan el logo incorporado en el propio archivo y repiten el membrete cuando hay varias páginas.

Los documentos guardados conservan la razón social, el RIF, el domicilio y la versión del logo existentes al emitirlos. Cambiar Configuración afecta documentos nuevos; las aperturas posteriores no sobrescriben tus cambios. Los comprobantes anteriores a esta versión conservan sus datos y su emblema anteriores.

### Diseño del recibo de pago

El recibo presenta el membrete sin bordes exteriores, datos del representante y del alumno en columnas, con el grado / sección junto al nombre del alumno, conceptos con importes alineados y un bloque destacado para el **importe recibido**. El total aplicado en USD y la tasa BCV se muestran juntos. El grado de los pagos nuevos queda guardado con el recibo. Para recibos antiguos se consulta la última constancia de matrícula emitida antes del pago; si no existe esa información se muestra «Grado no registrado», sin sustituirlo por el grado actual. Las referencias, direcciones y observaciones aparecen cuando tienen contenido. El diseño sirve tanto para pagos completos como para abonos; indica lo aplicado en esta operación.

En el recibo, **Tamaño del recibo** permite elegir **Media carta horizontal (21,59 × 13,97 cm)** o **A4 vertical**. Se abre inicialmente en media carta; puedes cambiar el formato antes de **Descargar PDF** o **Imprimir**, sin alterar el pago. Media carta se recomienda para los cobros habituales y A4 para recibos con muchos conceptos, direcciones u observaciones extensas.

También puedes seleccionar **Ticket térmico de 58 mm o 80 mm**. El PDF tiene el ancho real del rollo y ajusta la longitud al contenido, con continuación si hay muchos conceptos. Instala el controlador de la impresora en Windows y selecciona escala 100 %; el sistema usa el diálogo de impresión de Windows, sin controlar directamente el corte del rollo.

El PDF usa el tamaño físico seleccionado e incorpora sus fuentes para conservar la tipografía en otras computadoras. Al imprimirlo en una hoja carta, selecciona **Tamaño real / escala 100 %**; evita **Ajustar a página**, que puede ampliar el recibo hasta ocupar toda la hoja. Revisa el tamaño de papel y la vista previa de tu impresora. El botón Imprimir del programa también prepara la página en el formato elegido.

Si hay muchos conceptos u observaciones, el PDF continúa en otras páginas del mismo tamaño con el membrete, el número de recibo y los encabezados de la tabla repetidos. Los recibos anulados se identifican en todas las páginas. Mejorar el diseño o cambiar su tamaño no modifica los importes ni los datos históricos guardados.

[Ver una muestra del recibo con datos ficticios](https://github.com/Eliezerti/Sistema-colegio/blob/main/docs/recibo-ejemplo.png).

[Ver la muestra en media carta](https://github.com/Eliezerti/Sistema-colegio/blob/main/docs/recibo-media-carta.png).

[Ver el ticket de 58 mm](https://github.com/Eliezerti/Sistema-colegio/blob/main/docs/recibo-ticket-58.png) · [Ver la revisión de un pase de año](https://github.com/Eliezerti/Sistema-colegio/blob/main/docs/pase-de-ano.png).

## Flujo diario

1. Al abrir o iniciar sesión, revisa y confirma la **tasa BCV del día** en **Tasas y respaldo**. La pantalla permite descargar un respaldo si eres administrador. Las operaciones quedan bloqueadas hasta confirmar la tasa; al cambiar el día hay que confirmarla nuevamente. Consulta puede confirmar una tasa ya registrada, pero administración o caja debe cargarla si falta. Crea los **grados / secciones** y su capacidad.
2. Registra los **representantes**, con cédula, teléfono y correo. Un representante puede estar asociado con varios alumnos.
3. **Matricula a los alumnos**: busca al representante por nombre o cédula y selecciónalo; completa nacimiento, grado, año escolar, fechas, mensualidad en USD y descuento. El importe final se calcula inmediatamente: **100 USD con 10 % de descuento → 90 USD**. El código único **AL-000001** se asigna automáticamente al guardar; la cédula propia del alumno es opcional. No uses la cédula del representante: dos hermanos comparten representante y tienen códigos distintos. Al guardar se abre una **constancia de matrícula** con botones **Descargar PDF** e **Imprimir**. Puedes volver a abrir la última constancia desde **Alumnos → Constancia**; para alumnos anteriores a esta actualización, guarda su matrícula para generar la primera.
4. Las **mensualidades se calculan automáticamente** al abrir Aula, consultar los módulos y guardar una matrícula: se incluyen los meses desde su inicio hasta el mes actual, dentro de su año escolar. Los saldos aparecen directamente en **Resumen**, **Alumnos**, **Mensualidades y cargos** y **Morosidad**, sin pulsar un botón. **Preparar otro período** es opcional para cobrar meses futuros por adelantado. Los cargos adicionales permiten registrar inscripción, transporte, actividades y otros conceptos.
5. Registra la **tasa BCV** de la fecha del cobro: bolívares por un dólar. Consulta la publicación oficial en [bcv.org.ve](https://www.bcv.org.ve/). Fines de semana y feriados: registra para la fecha del pago la tasa oficial vigente que corresponda. El sistema no la descarga ni certifica automáticamente.
6. En **Caja y cobros**, selecciona alumno, fecha, moneda, importe, método y referencia. El sistema admite abonos parciales y aplica primero los cargos pendientes más antiguos. El comprobante incluye encabezado del colegio, representante, alumno, conceptos abonados, método, referencia, importes, tasa y espacios para firmas. Usa **Descargar PDF** para obtener el archivo directamente o **Imprimir** para imprimirlo desde Windows. El diseño también se aplica a los abonos parciales.
7. En **Morosidad**, filtra por alumno, representante o grado; consulta deuda vencida y días de atraso. Prepara avisos de cobranza para copiar y compartir por tus propios medios. **Seguimiento** registra contactos, acuerdos y fecha prometida de pago; los avisos no se envían automáticamente.
8. En **Personal → Cargos**, crea el catálogo de cargos y luego selecciónalos al guardar cada empleado. El sueldo de referencia en USD es individual. Completa banco, cuenta venezolana de 20 dígitos, tipo de cuenta, titular y cédula del titular. **Pagar nómina** propone el importe en Bs convertido con la tasa de hoy; revisa y registra cada desembolso como egreso. También puedes registrar gastos en **Egresos y nómina**.
9. Consulta **Reportes** por rango de fechas y exporta los libros completos como CSV compatible con Excel. Los CSV incluyen los registros anulados y su estado. La morosidad corresponde al corte actual, aunque filtres ingresos de otro período.

### Nómina consolidada

En **Personal → Preparar nómina**, elige descripción y fecha, y ajusta manualmente el sueldo a pagar de cada empleado activo. Se conserva el salario de referencia del expediente. La fecha necesita su propia tasa BCV registrada: puedes cargar una tasa histórica desde el botón **BCV** de la barra superior.

**Generar relación de pago** guarda una sola relación con todos los empleados: nombre, cédula, cargo, banco, tipo y número de cuenta, titular, cédula del titular, monto USD, monto Bs y totales. **Descargar PDF** genera un único archivo, con tantas páginas como necesite; **Imprimir** permite llevarlo en físico. Se señalan las cuentas o bancos pendientes para completarlos antes de transferir. Las últimas 30 relaciones se pueden abrir desde **Personal**.

La conversión USD → Bs se redondea por empleado al centavo, con mitad hacia arriba; el total Bs suma esos importes. La relación conserva los datos, montos y tasa usados al generarla. **Preparar o descargar una nómina no registra egresos ni marca empleados como pagados**: registra los pagos realizados con **Pagar nómina** y su referencia bancaria.

### Recibo individual de sueldo para firmar

Al pulsar **Personal → Pagar nómina**, indica el período pagado **desde / hasta**, la hora de entrada, la hora de salida y las observaciones. El importe se puede ajustar antes de registrar el pago. Guardar crea el egreso y su recibo juntos; si no se puede emitir el documento, el pago no se guarda parcialmente.

Se abre un **Recibo de sueldo**, descargable en PDF e imprimible: logo y membrete fiscal, empleado, cédula, cargo, período, horario informado, fecha, importe recibido, equivalente USD, tasa, método, referencia y datos bancarios registrados. Incluye declaración de recepción, espacios para las firmas de administración y del empleado, fecha de firma y huella. El horario se introduce manualmente; este recibo no sustituye un registro diario de asistencia. La conformidad del empleado se acredita con su firma física.

En **Egresos y nómina → Recibo de sueldo** puedes volver a abrirlo. El documento conserva los datos originales aunque después cambies el empleado, su sueldo, banco o los datos fiscales. Anular el egreso identifica su recibo como anulado. Para pagos de nómina anteriores sin recibo, **Emitir recibo** permite completar período y horario sin registrar otro pago; utiliza los datos del empleado y colegio disponibles al emitirlo.

[Ver un recibo de sueldo generado en modo prueba](docs/recibo-sueldo-prueba.png).

### Mensualidades y morosidad automáticas

Ejemplo: un alumno matriculado desde septiembre con mensualidad de **100 USD** tendrá cargos de septiembre y octubre al abrir Aula en octubre. Si septiembre no se ha pagado y pasó su vencimiento, figurará en **Morosidad**. Octubre aparece como pendiente y pasa a morosidad al día siguiente del vencimiento, si sigue sin pagarse. No se cargan noviembre ni otros meses futuros automáticamente.

Se completan los meses faltantes de cada matrícula activa, aunque su año escolar sea anterior al configurado actualmente. Se respetan las fechas de inicio y fin, los descuentos y el límite del año escolar. Volver a abrir o consultar no duplica mensualidades. Los cargos anteriores, pagos, abonos, recibos y anulaciones se conservan. Una mensualidad anulada no se vuelve a generar. Las becas del 100 % quedan calculadas con importe cero y no se convierten luego en deuda por un cambio de tarifa.

Al cambiar tarifa, beca o estado de un alumno, primero se calculan los meses pendientes con sus condiciones anteriores. Las condiciones nuevas se aplican a meses aún no calculados. Si registras una matrícula con inicio anterior a hoy, se incluyen esos meses con la tarifa y beca que indiques.

**Pagos anteriores al uso de Aula:** si un alumno ya pagó esos meses por fuera del sistema, registra los pagos históricos con sus fechas e importes para que el saldo represente su deuda real. El programa no puede conocer cobros que no se han registrado.

### Año escolar y matrícula

El año escolar usa su **año de inicio**: `2026` significa `2026–2027`. Por defecto empieza en septiembre y termina en agosto del año siguiente; se puede configurar otro mes de inicio. Las fechas de matrícula deben estar dentro de ese año escolar. Un alumno matriculado durante un mes recibe el cargo completo de ese mes; **no se calcula prorrateo automático**. Usa un cargo manual si necesitas un importe especial.

Al pasar un alumno a otro año escolar, actualiza su matrícula y fechas. Sus cargos y pagos anteriores permanecen en su cuenta. El expediente muestra la matrícula actual. Cada guardado nuevo conserva una constancia con los datos, representante y tarifa de ese momento; la interfaz abre la última constancia y no incluye todavía un directorio de todos los años escolares. Inactivar un alumno evita nuevas mensualidades automáticas, pero mantiene la deuda existente.

### Dinero, conversiones y correcciones

- Los importes se guardan como **centavos enteros**, con dos decimales. La conversión de Bs a USD usa aritmética decimal y redondea al centavo más cercano, con mitad hacia arriba. Las tasas admiten hasta seis decimales.
- Ejemplo: mensualidad **50 USD**, descuento **10 %** → cargo **45 USD**. Pago **2.252,81 Bs** a **100,125 Bs/USD** → abono **22,50 USD** y saldo **22,50 USD**.
- Cada pago en Bs conserva el importe recibido, moneda, tasa aplicada y equivalente USD. Cambiar la tasa de esa fecha no modifica operaciones anteriores. Los recibos y las constancias también conservan los datos del colegio, alumno y representante que tenían al emitirse.
- El saldo se mantiene en USD. El equivalente en Bs mostrado en morosidad es una referencia con la tasa registrada de hoy; al pagar se utiliza la tasa de la fecha elegida.
- Un pago no puede superar el saldo. Para anticipos, crea primero el cargo correspondiente al período futuro. No se lleva una billetera de créditos sin asignar.
- El cálculo automático de mensualidades y el registro de pagos son transaccionales. Una misma solicitud de pago reintentada conserva un solo recibo. Dos pagos distintos ingresados manualmente se consideran operaciones distintas: revisa referencias bancarias antes de cobrarlas otra vez.
- No se eliminan pagos ni egresos: el administrador puede **anularlos con motivo** y registrar la corrección. Anular un pago restaura la deuda que había abonado. Un cargo con pagos válidos no se puede anular hasta anular esos pagos.
- Cambiar tarifa, beca o día de vencimiento afecta meses aún no calculados. No recalcula cargos ya emitidos. Los recargos y convenios especiales se registran como cargos explícitos; no hay intereses automáticos.

## Usuarios y respaldo

**Administrador:** configura el colegio, mantiene expedientes y usuarios, cobra, registra egresos, anula operaciones y descarga respaldos.

**Caja:** consulta expedientes y reportes, genera mensualidades, crea cargos, registra cobros, tasas BCV, seguimiento de cobranza y egresos. No puede modificar expedientes, gestionar usuarios ni anular operaciones.

**Consulta:** lectura de los módulos y reportes, sin operaciones de escritura. Los usuarios de consulta tienen acceso a expedientes y salarios; asigna este perfil solo a personas autorizadas para ver esa información.

Las contraseñas se almacenan con PBKDF2-SHA256 y sal aleatoria. Las sesiones vencen a las doce horas y se invalidan al cambiar la contraseña. La bitácora conserva las operaciones registradas; la interfaz muestra las últimas 300. La base no está cifrada: protege la cuenta de Windows y los archivos de respaldo. En modo compartido, autoriza solo los equipos y las personas del colegio en Tailscale y asigna a cada usuario los permisos necesarios en Aula. El servidor admite únicamente la dirección local y el enlace HTTPS configurado; conserva la protección CSRF y usa cookies Secure en las sesiones HTTPS.

### Descargar y restaurar

- En **Tasas y respaldo** al entrar o en **Configuración → Respaldo**, descarga una copia consistente de toda la base, incluso con el sistema abierto. Guarda copias periódicas en otro dispositivo.
- Al iniciar se guarda una copia automática por día en la subcarpeta `backups`; se conservan las últimas 30 copias diarias. Además, se crean respaldos después de operaciones financieras y cada cinco minutos mientras Aula permanece abierto. Configura un segundo destino para protegerte ante una falla del disco; también puedes descargar una copia manual.
- Para restaurar, cierra Aula y ejecuta **Restaurar-respaldo.bat**. Selecciona el archivo `.sqlite3` y escribe `RESTAURAR`. La herramienta comprueba la integridad y compatibilidad del respaldo, prepara la recuperación antes de reemplazar los datos y bloquea la restauración mientras Aula utiliza esa carpeta. Si la base actual está sana, conserva un respaldo previo; si está dañada, conserva los archivos originales en una carpeta `backups/danado-antes-restauracion-*` y permite recuperar el respaldo válido. Esa carpeta conserva evidencia para una revisión técnica, no es un respaldo utilizable.
- Los respaldos no conservan sesiones autenticadas. Tras restaurar, inicia sesión con las cuentas que contiene el respaldo. El respaldo conserva sus contraseñas, por lo que debe almacenarse de forma segura.

### Si falla el programa o se pierden datos

Un cierre inesperado no significa que se haya perdido la base: primero vuelve a abrir Aula y verifica el último pago antes de ingresarlo de nuevo. Los pagos y sus abonos se guardan en una misma transacción.

Si necesitas recuperar la base:

1. Cierra Aula y conserva la carpeta de datos actual; no la borres ni elimines sus respaldos.
2. Busca la copia válida más reciente en `%LOCALAPPDATA%\AulaColegio\backups` o en el dispositivo externo donde hayas guardado una descarga.
3. Ejecuta **Restaurar-respaldo.bat**, selecciona el archivo `.sqlite3` y confirma con `RESTAURAR`.
4. Abre Aula, entra con las cuentas del respaldo y comprueba el último recibo, fecha, cobros y saldos. Concilia los movimientos posteriores a esa copia con sus recibos y referencias bancarias.

Si desapareció el archivo principal pero siguen existiendo respaldos locales, Aula avisa y no crea silenciosamente una base vacía. Usa la herramienta de restauración para recuperarla.

**Límite de recuperación:** restaurar devuelve todos los datos al momento de la copia y no combina registros. Los movimientos posteriores al respaldo no reaparecen automáticamente. Se crea una copia diaria al abrir (últimas 30), una copia después de cobros, egresos, anulaciones, cierres y operaciones masivas, y una copia cada cinco minutos mientras el servidor está abierto (últimas 90). Los respaldos se verifican y se publican de forma atómica: una copia interrumpida no reemplaza una válida. SQLite usa WAL y `synchronous=FULL` en cada conexión de la aplicación. Las pruebas incluyen matar un proceso a mitad de un cobro y después de confirmarlo; no reemplazan una prueba de corte eléctrico con datos ficticios en la PC del colegio ni un UPS.

**Falla del disco o pérdida de la computadora:** los respaldos locales pueden perderse junto con la base. Configura un segundo destino en otro dispositivo o almacenamiento privado externo y comprueba las copias; también puedes descargar un respaldo manual. Guarda los archivos de respaldo descargados; no sincronices la base SQLite activa mediante Drive o Dropbox. En **Configuración → Segunda carpeta de respaldos**, introduce una ruta absoluta fuera de la carpeta activa de Aula, por ejemplo `E:\RespaldosAula` o una carpeta local del cliente de Drive. El sistema copia el respaldo verificado, nunca la base activa ni su WAL, y conserva las últimas 90 copias propias en ese destino. El USB debe estar conectado; la subida desde una carpeta de Drive depende de su cliente y de internet. Si falla el segundo destino, el cobro permanece registrado y se muestra una advertencia. El segundo destino no está activado hasta configurar su ruta. La barra superior muestra la antigüedad del último respaldo local, en rojo si supera un día o falla. La ruta completa de la base y los errores del segundo destino se muestran en Configuración.

También puedes restaurar desde la terminal:

```bat
py -3 -m colegio.restore --data-dir "%LOCALAPPDATA%\AulaColegio" --backup "D:\Respaldos\colegio.sqlite3"
```

## Alcance de esta versión

Incluye administración de alumnos y representantes, importación Excel/CSV, matrícula actual e historial de pases masivos, grados y capacidad, tarifas y becas individuales, mensualidades, otros cargos, cobranza, morosidad, convenios, recibos A4/media carta/térmicos, documentos familiares, tasas con confirmación, personal, nómina, egresos, cierres con arqueo, reportes, usuarios, recuperación local de contraseña y respaldos frecuentes con segundo destino configurable.

Los recibos son **comprobantes administrativos**: no implementan facturación fiscal SENIAT. El módulo de nómina registra desembolsos y salarios de referencia; no calcula prestaciones, vacaciones, retenciones ni obligaciones laborales. Tampoco incluye contabilidad de partida doble, inventario, evaluación académica, conciliación bancaria automática ni envío automático por WhatsApp. Los avisos se abren manualmente mediante enlaces prellenados. Estos módulos necesitan reglas adicionales del colegio para una ampliación posterior.


### Importación inicial de Excel / CSV

En **Alumnos y matrículas → Importar Excel / CSV**, descarga la plantilla `.xlsx` o `.csv`, conserva los encabezados y completa una fila por alumno. Se usa la primera hoja del Excel; `.xls`, macros, archivos protegidos y fórmulas no se admiten. En Excel pega los datos como valores, y usa formato texto para cédulas y teléfonos. Fechas ISO `AAAA-MM-DD` o fechas numéricas de Excel; importes en USD con punto decimal, sin símbolos. Crea los grados y sus cupos antes de importar; usa su nombre exacto.

Los hermanos repiten los datos del representante. La cédula identifica al representante existente; datos distintos para la misma cédula producen un error, nunca una actualización silenciosa. Se revisan documentos repetidos, nombre/nacimiento/representante, fechas, cupos y tarifas. La vista previa no guarda filas y muestra los cargos que se generarían. Si hay errores, ninguna fila se importa. Corrige el archivo y vuelve a revisarlo; solo confirma después de comprobar fechas, tarifas y deudas. Límite: 2 MB y 1000 alumnos por archivo. Se crea un respaldo local antes de confirmar. Esta importación no importa pagos históricos.

### Cierre diario y arqueo

En **Cierre de caja** (también destacado en Reportes), selecciona una fecha y pulsa **Revisar / cerrar caja**. El corte separa ingresos y egresos por **método y moneda**, usando importes realmente recibidos/pagados. Los equivalentes USD se muestran aparte; no se suman USD y Bs. Los anulados se excluyen de los totales y se mantienen en el detalle.

Indica el fondo inicial y cuenta el efectivo físico en cada moneda. **Esperado = fondo inicial + cobros en efectivo − egresos en efectivo**. La pantalla y el PDF muestran la diferencia; si la hay, exige una explicación. Los egresos anteriores a esta versión figuran como «No especificado» y no descuentan efectivo. Los egresos nuevos permiten seleccionar método. No se trasladan automáticamente fondos iniciales de otro cierre: registra el efectivo que quedó físicamente en caja.

El cierre guarda su corte, operador, arqueo y membrete; puedes descargar PDF o imprimirlo. Se bloquean cobros, egresos y anulaciones de esa fecha. Solo administración puede **Reabrir** con motivo, para corregir movimientos y generar otro cierre. El documento anterior conserva su corte y se identifica como reabierto. Si hay movimientos nuevos desde la vista previa, hay que revisarla otra vez antes de cerrar.

### Estado de cuenta familiar y solvencia

En **Representantes → Cuenta familiar** ves los cargos y pagos de todos sus alumnos, incluidos los inactivos. Administración y caja pueden emitir **Estado de cuenta PDF** y **Constancia de solvencia**. La solvencia exige saldo cero en todos los cargos registrados de la familia, incluidos períodos futuros que ya se hayan preparado. No acredita períodos futuros sin cargar ni cobros externos sin registrar. Cada documento conserva su fecha de corte y se puede reabrir desde los documentos emitidos de esa cuenta.

### Pase masivo de año / grados

1. Haz el cierre al concluir realmente el curso y comprueba mensualidades y pagos del año que cierras. Crea los grados / secciones de destino y su capacidad.
2. En **Alumnos y matrículas → Pase de año / grados**, escribe el año de inicio del curso de origen (por ejemplo `2026` para 2026–2027) y pulsa **Cargar alumnos del año**. El destino es el siguiente año.
3. Indica la **fecha real de cierre** del curso, y las fechas de matrícula del nuevo año. La fecha de cierre no puede ser futura. Si el colegio termina clases antes del fin configurado del año escolar, revisa y selecciona la fecha real. Los meses del año anterior ya cargados se conservan; al avanzar/repetir dejan de generarse meses posteriores del año anterior.
4. Define el destino de cada grado y, si corresponde, cambia el destino individual. Selecciona **Avanza**, **Repite**, **Retirado** o **Sin cambios** por alumno. Quien **repite** se matricula en el nuevo año en el mismo grado. Quien se **retira** permanece en el año anterior, inactivo, con sus deudas y pagos. **Sin cambios** conserva íntegra su matrícula anterior y su estado. Los alumnos ya inactivos no se reactivan masivamente: revísalos individualmente.
5. Revisa las mensualidades base nuevas; los descuentos individuales se conservan. Pulsa **Revisar pase de año**, verifica destinos, fechas, repitentes, retirados y cupos, y marca la confirmación.
6. **Aplicar pase de año** actualiza el grupo en una transacción y genera un **acta PDF** con la matrícula anterior y las decisiones. Si hay un error o la matrícula cambió desde la revisión, no se aplica parcialmente. Hay un respaldo previo y otro posterior.

Los códigos únicos no cambian. Se conservan todos los cargos, abonos, pagos, recibos y constancias anteriores. Las constancias nuevas usan el nuevo grado; un recibo anterior sigue mostrando el grado que tenía cuando se emitió. El acta se abre desde **Pases guardados**. Si el año configurado del colegio era el de origen, se actualiza al de destino; en los demás casos se conserva.

### Controles en caja y convenios

Una referencia que ya figure en un pago válido produce una alerta con sus recibos. Se compara sin espacios y sin distinguir mayúsculas; conserva ceros iniciales. Para registrarla otra vez se requiere confirmación y un motivo auditado. Reintentar la misma solicitud no crea un pago nuevo. La referencia por sí sola no prueba que sean la misma transferencia: compara banco, fecha y monto.

La tasa BCV pide confirmación adicional si cambia más del **10 %** respecto a la tasa existente de esa fecha, o la anterior registrada si todavía no existe. Un cambio igual al 10 % no exige confirmación. Revisa siempre la publicación oficial; la confirmación no certifica la tasa.

En **Morosidad → Convenio** o en la cuenta del alumno puedes distribuir su deuda vencida en hasta 60 cuotas, con fechas e importes. Deben sumar exactamente la deuda. El convenio **no crea deuda adicional, no cobra intereses y no borra la mora**: organiza los cargos existentes. Los cobros habituales se aplican primero al cargo más antiguo y actualizan el cumplimiento; anularlos vuelve a dejar pendientes las cuotas. Solo puede haber un convenio pendiente por alumno. Administración puede cancelarlo con motivo; se conserva el documento y la deuda. Los cargos de un convenio deben liberarse cancelando el convenio antes de poder anularlos.

El PDF conserva las condiciones iniciales; el cumplimiento actual se consulta en pantalla.

El **Resumen** reúne las cifras en un solo bloque: **Cobrado hoy** (equivalente USD y dinero realmente recibido por moneda) y **Deuda vencida**. Debajo aparecen el cobrado del mes, el saldo pendiente total y los alumnos activos. Dos enlaces permiten revisar los vencimientos de los próximos siete días y los alumnos nuevos en mora; los detalles de cobros y cuentas están más abajo. Si no hay atrasos, se muestra un mensaje claro en lugar de barras vacías. Estas cifras se calculan con los datos registrados. Un alumno nuevo en mora es aquel cuya primera deuda actualmente vencida corresponde a los últimos siete días.

[Ver el nuevo resumen con datos ficticios de prueba](docs/resumen-colegio.png).

Los avisos de cobranza incluyen **Abrir WhatsApp con el aviso** para teléfonos venezolanos válidos. Puedes editar el texto antes de abrirlo; el enlace `wa.me` no envía automáticamente el mensaje.

### Recuperar la contraseña del administrador

Cierra Aula y ejecuta **Recuperar-clave-admin.bat**, indica el usuario administrador y escribe una contraseña nueva dos veces (no se muestra al escribir). Se guarda un respaldo previo, se invalidan sus sesiones y se registra la recuperación en bitácora. No cambia otros datos ni crea una cuenta nueva. Requiere acceso local al equipo y a la carpeta de datos; no hay restablecimiento por correo. Si usas una ruta de datos personalizada, ejecuta `py -3 -m colegio.reset_password --data-dir "RUTA"`.

### Instalación y protección del equipo

La distribución de escritorio incluye Python. La alternativa ZIP necesita Python instalado en Windows. Ambas utilizan la carpeta `%LOCALAPPDATA%\AulaColegio` del usuario que lo abrió. Configuración muestra la ruta exacta. No se ha cambiado automáticamente a `C:\ProgramData`: primero hay que migrar y verificar la base existente y asignar permisos de los usuarios de Windows. Cambiar únicamente el lanzador puede abrir una base diferente y aparentar pérdida de datos.

El instalador .exe se construye con PyInstaller e Inno Setup en GitHub Actions sobre Windows. Se publica únicamente después de superar las pruebas integradas y cargar la ventana propia con su logo y JavaScript. El ZIP de código fuente sigue disponible como alternativa; no contiene el ejecutable. Usa un **UPS** para la PC y el router. Activa **BitLocker** en Windows, si la edición y el equipo lo permiten, y conserva la clave de recuperación fuera de esa PC. Protege también el USB y las copias externas: cifrar la PC no cifra automáticamente esos respaldos.

Para soporte remoto puedes instalar Chrome Remote Desktop o AnyDesk en esa PC y conceder acceso cuando lo necesites. Este repositorio no instala ni configura esas herramientas, y el asistente no obtiene acceso remoto por instalar esta actualización. Para trabajar desde varias laptops utiliza el modo de acceso privado descrito arriba: Aula sigue escuchando solo en `127.0.0.1` y Tailscale Serve proporciona el enlace HTTPS privado. Los respaldos de Drive sirven para recuperación/traslado; no sincronizan dos bases activas.

## Desarrollo y validación

Python 3.10+ y un navegador moderno (Edge, Chrome o Firefox). El programa no necesita paquetes Python adicionales ni pasos de compilación. El uso local no necesita servicios remotos; el acceso compartido requiere instalar y configurar Tailscale en los equipos reales. Las fuentes Liberation Sans de los PDF se distribuyen sin modificaciones bajo SIL Open Font License 1.1; su licencia está incluida en `colegio/fonts/LICENSE.txt`.

```bash
python -m colegio.server
python -m unittest discover -s tests -v
```

En Linux puede ser necesario usar `python3`; en Windows, `py -3`. La ejecución manual usa `data/` dentro del proyecto. Puedes cambiar carpeta o puerto:

```bash
python -m colegio.server --data-dir /ruta/a/datos --port 8765
```

Las pruebas integradas usan bases temporales y verifican importación Excel/CSV con vista previa y rollback, promoción masiva con repitentes y retirados, cupos del grupo, cierres y arqueos, documentos familiares y solvencia, convenios sin deuda duplicada, referencias repetidas, confirmación de tasas, tickets de 58/80 mm, respaldo después de cobros y segundo destino fallido, reinicio local de clave y procesos matados durante/después del cobro, además de conversiones, abonos, distribución entre cargos, reintentos, anulaciones, tasas y recibos históricos, descuentos, códigos únicos para hermanos, constancias PDF, tasa obligatoria, nómina de 15 empleados con cuentas bancarias y redondeos, migración de registros anteriores, mensualidades automáticas, cambios de mes, becas completas, años escolares, capacidad, permisos, CSRF, exportación, restauración de una base dañada, conservación de archivos originales y recuperación tras borrado del archivo principal. No escriben en la base real.

Las pruebas de acceso compartido verifican configuración sin modificar la base, rechazo de direcciones y orígenes ajenos, sesiones HTTPS con cookie Secure, permisos de consulta, creación inicial del administrador solo en modo local y dos cajeros cobrando simultáneamente sobre la misma base, con reintentos y respaldo consistente. Simulan los encabezados del intermediario privado; no sustituyen la prueba de Tailscale entre las PC reales.

Validación opcional de interfaz, con Node, Playwright y Chromium disponibles:

```bash
python tests/run_browser.py
python tests/run_browser.py --demo
```

Estos comandos crean datos ficticios en carpetas temporales e inician sus propios servidores. El primero valida matrícula, mensualidades, cobro en Bs, recibos de alumnos y empleados, morosidad, egresos, reportes, diseño adaptable, permisos y vaciado protegido. El segundo comprueba el administrador de prueba, PDF identificado como prueba, recarga y varias pestañas, cierre de la última pestaña y eliminación física de los datos temporales. Las pruebas integradas también comprueban reinicio tras proceso matado, rechazo de un directorio real en modo prueba, respaldo antes de vaciar, fallo del segundo destino y conservación de numeraciones. Para usar otro Chromium, define `CHROMIUM_PATH`. Las pruebas opcionales no son una dependencia del programa.

El funcionamiento del servidor y la interfaz se verifica en Linux durante el desarrollo. Los lanzadores y la ruta de bloqueo de archivos para Windows requieren una prueba final en una computadora Windows antes de utilizar datos reales.

### Construir el instalador de escritorio

La compilación requiere Windows 10/11 de 64 bits, Python 3.12 e Inno Setup 6. El flujo `.github/workflows/windows-desktop.yml` instala las dependencias fijadas de `requirements-desktop.txt`, ejecuta las pruebas, incluye recursos y Python con PyInstaller, verifica la firma de Microsoft del instalador WebView2 y construye el instalador con `packaging/Aula.iss`. Ejecuta el propio Aula.exe con `--self-test` sobre una base temporal y un WebView2 real antes de publicar una versión descargable. Nunca incluye la base de desarrollo.

```powershell
./packaging/build_windows.ps1 -Version "1.0.0"
./dist/Aula/Aula.exe --self-test
```

Para probar el escritorio desde código en Windows: `py -3 -m pip install -r requirements-desktop.txt` y `py -3 -m colegio.desktop`. El servidor de desarrollo y sus pruebas en Linux siguen usando únicamente la biblioteca estándar; las dependencias de escritorio no son necesarias para ese flujo.
