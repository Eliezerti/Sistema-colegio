# Aula · Administración de colegios

Sistema administrativo local para **una computadora Windows**, preparado para colegios de Venezuela. Las mensualidades y la deuda se expresan en **USD**; los cobros y egresos pueden registrarse en **USD o bolívares (VES)** con la tasa BCV correspondiente a la fecha de la operación.

## Descargar el sistema

Abre [Aula-Windows.zip](https://github.com/Eliezerti/Sistema-colegio/blob/main/descargas/Aula-Windows.zip) y pulsa **Download raw file** (icono de descarga) en GitHub. Si el repositorio es privado, inicia sesión con una cuenta que tenga acceso. El archivo [Aula-Windows.sha256](descargas/Aula-Windows.sha256) permite verificar la integridad del paquete.

El ZIP incluye los archivos del programa y los lanzadores para Windows; no incluye Python ni datos de alumnos. Descomprímelo con **Extraer todo** y sigue estos pasos.

## Instalar y abrir en Windows

1. Instala **Python 3.10 o posterior**, de 64 bits, desde [python.org](https://www.python.org/downloads/windows/). En el instalador activa **Add python.exe to PATH**. No se necesitan paquetes adicionales.
2. Descomprime la carpeta del sistema en una ubicación permanente, por ejemplo `C:\Aula`.
3. Haz doble clic en **Iniciar-Aula.bat**. Se abrirá la interfaz en tu navegador. Mantén abierta la ventana de comandos durante el uso; ciérrala con **Ctrl+C** cuando termines.
4. En la primera apertura crea tu usuario administrador con una contraseña de al menos diez caracteres. No existe una contraseña predeterminada.
5. Confirma la **tasa BCV de hoy** en la pantalla **Tasas y respaldo**. Después revisa **Configuración**: el logo, la razón social, el RIF y el domicilio fiscal del colegio ya están incorporados. Completa teléfono, correo, dirección de contacto, año escolar, mes de inicio y día de vencimiento. Estos datos aparecen en los documentos nuevos.

Los datos de Windows quedan en `%LOCALAPPDATA%\AulaColegio\colegio.sqlite3`, separados del código. **Abrir-carpeta-de-datos.bat** abre esa carpeta. Actualizar o mover los archivos del programa no borra los datos. Usa la misma cuenta de Windows para abrir el sistema: cada cuenta tiene su propia carpeta local.

La interfaz utiliza el navegador de Windows; el servidor y la base de datos funcionan en la misma computadora. El servidor escucha exclusivamente en `127.0.0.1` y no está preparado para acceso desde otras computadoras. Los registros y consultas funcionan sin internet. La tasa BCV requiere consultarla y registrarla manualmente.

## Actualizar una instalación existente

1. En Aula, descarga un respaldo de tu base y cierra el programa con **Ctrl+C**.
2. Descarga el ZIP actualizado y usa **Extraer todo** en una carpeta nueva, por ejemplo `C:\Aula-actualizado`. También puedes reemplazar los archivos del programa anterior con Aula cerrado.
3. Abre **Iniciar-Aula.bat** desde la carpeta nueva, con la **misma cuenta de Windows**. Usa tu usuario habitual: los alumnos, representantes, cobros y egresos permanecen en `%LOCALAPPDATA%\AulaColegio`.
4. La primera apertura crea un respaldo `antes-actualizacion-*.sqlite3` y amplía la base automáticamente. Esta versión incorpora una sola vez el logo y los datos fiscales suministrados del colegio. Conserva el nombre comercial configurado, el año escolar, los contactos, alumnos, cobros y documentos anteriores. Los alumnos de versiones antiguas reciben un código único y los cargos del personal se incorporan al catálogo. Completa sus datos bancarios en **Personal**.

Si usabas otro directorio de datos con un comando personalizado, conserva ese `--data-dir`; el lanzador estándar solo abre `%LOCALAPPDATA%\AulaColegio`.

### Identidad del colegio y membrete fiscal

El logo PNG está incluido en el programa y aparece al entrar, en el menú y en los membretes de los documentos nuevos. No necesita internet. En **Configuración → Datos del colegio** puedes descargar el PNG y editar los datos fiscales:

- **Razón social:** ALEJANDRO VON HUMBOLDT, C.A.
- **RIF:** J-50835934-8.
- **Domicilio fiscal:** Calle 48 entre carreras 16 y 17, local Nro. 16-46, sector Centro, Barquisimeto, Lara. Zona postal 3001.

El nombre comercial del colegio se configura aparte de la razón social. La dirección de contacto también se mantiene separada del domicilio fiscal. Los recibos de pagos completos y abonos, las constancias de matrícula, las relaciones de nómina y el resumen administrativo impreso usan el mismo membrete. Los PDF descargables llevan el logo incorporado en el propio archivo y repiten el membrete cuando hay varias páginas.

Los documentos guardados conservan la razón social, el RIF, el domicilio y la versión del logo existentes al emitirlos. Cambiar Configuración afecta documentos nuevos; las aperturas posteriores no sobrescriben tus cambios. Los comprobantes anteriores a esta versión conservan sus datos y su emblema anteriores.

### Diseño del recibo de pago

El recibo presenta el membrete sin bordes exteriores, datos del representante y del alumno en columnas, conceptos con importes alineados y un bloque destacado para el **importe recibido**. El total aplicado en USD y la tasa BCV se muestran juntos. Las referencias, direcciones y observaciones aparecen cuando tienen contenido. El diseño sirve tanto para pagos completos como para abonos; indica lo aplicado en esta operación.

El PDF descargable usa **A4 vertical** e incorpora sus fuentes para conservar la tipografía en otras computadoras. Si hay muchos conceptos u observaciones, continúa en otras páginas con el membrete, el número de recibo y los encabezados de la tabla repetidos. Los recibos anulados se identifican en todas las páginas. Mejorar el diseño no modifica los importes ni los datos históricos guardados.

[Ver una muestra del recibo con datos ficticios](https://github.com/Eliezerti/Sistema-colegio/blob/main/docs/recibo-ejemplo.png).

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

Las contraseñas se almacenan con PBKDF2-SHA256 y sal aleatoria. Las sesiones vencen a las doce horas y se invalidan al cambiar la contraseña. La bitácora conserva las operaciones registradas; la interfaz muestra las últimas 300. La base no está cifrada: protege la cuenta de Windows y los archivos de respaldo. El sistema es para usuarios de confianza en una computadora local.

### Descargar y restaurar

- En **Tasas y respaldo** al entrar o en **Configuración → Respaldo**, descarga una copia consistente de toda la base, incluso con el sistema abierto. Guarda copias periódicas en otro dispositivo.
- Al iniciar se guarda una copia automática por día en la subcarpeta `backups`; se conservan las últimas 30 copias diarias. Son copias del estado **al abrir el sistema**, no de cada operación. Para respaldar los cobros del día, descarga una copia al finalizar la jornada.
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

**Límite de recuperación:** restaurar devuelve todos los datos al momento de la copia y no combina registros. Los movimientos posteriores al respaldo no reaparecen automáticamente. Las copias automáticas se crean al abrir, una por fecha; no se crean después de cada pago ni periódicamente si el programa permanece abierto varios días.

**Falla del disco o pérdida de la computadora:** los respaldos locales pueden perderse junto con la base. Descarga copias durante la jornada de cobros y al finalizarla, y conserva una copia reciente en otro dispositivo o almacenamiento privado externo. Guarda los archivos de respaldo descargados; no sincronices la base SQLite activa mediante Drive o Dropbox. Esta versión todavía no realiza copias externas automáticas.

También puedes restaurar desde la terminal:

```bat
py -3 -m colegio.restore --data-dir "%LOCALAPPDATA%\AulaColegio" --backup "D:\Respaldos\colegio.sqlite3"
```

## Alcance de esta versión

Incluye administración de alumnos y representantes, matrícula actual, grados y capacidad, tarifas y becas, mensualidades, otros cargos, cobranza, morosidad, recibos, tasas, personal, pagos de nómina, egresos, reportes, usuarios y respaldos.

Los recibos son **comprobantes administrativos**: no implementan facturación fiscal SENIAT. El módulo de nómina registra desembolsos y salarios de referencia; no calcula prestaciones, vacaciones, retenciones ni obligaciones laborales. Tampoco incluye contabilidad de partida doble, inventario, evaluación académica, conciliación bancaria automática ni integración con WhatsApp. Estos módulos necesitan reglas adicionales del colegio para una ampliación posterior.

## Desarrollo y validación

Python 3.10+ y un navegador moderno (Edge, Chrome o Firefox). El programa no tiene dependencias externas, servicios remotos, credenciales de terceros ni pasos de compilación. Las fuentes Liberation Sans de los PDF se distribuyen sin modificaciones bajo SIL Open Font License 1.1; su licencia está incluida en `colegio/fonts/LICENSE.txt`.

```bash
python -m colegio.server
python -m unittest discover -s tests -v
```

En Linux puede ser necesario usar `python3`; en Windows, `py -3`. La ejecución manual usa `data/` dentro del proyecto. Puedes cambiar carpeta o puerto:

```bash
python -m colegio.server --data-dir /ruta/a/datos --port 8765
```

Las pruebas integradas usan bases temporales y verifican conversiones, abonos, distribución entre cargos, reintentos, anulaciones, tasas y recibos históricos, descuentos, códigos únicos para hermanos, constancias PDF, tasa obligatoria, nómina de 15 empleados con cuentas bancarias y redondeos, migración de registros anteriores, mensualidades automáticas, cambios de mes, becas completas, años escolares, capacidad, permisos, CSRF, exportación, restauración de una base dañada, conservación de archivos originales y recuperación tras borrado del archivo principal. No escriben en la base real.

Validación opcional de interfaz, con Node, Playwright y Chromium disponibles:

```bash
python tests/run_browser.py
```

Este comando crea datos ficticios en una carpeta temporal, inicia su propio servidor y valida matrícula, mensualidades, cobro en Bs, recibo, morosidad, egresos, reportes, diseño adaptable y permisos de consulta. Para usar otro Chromium, define `CHROMIUM_PATH`. La prueba opcional no es una dependencia del programa.

El funcionamiento del servidor y la interfaz se verifica en Linux durante el desarrollo. Los lanzadores y la ruta de bloqueo de archivos para Windows requieren una prueba final en una computadora Windows antes de utilizar datos reales.
