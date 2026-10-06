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
5. En **Configuración**, registra el nombre del colegio, teléfono, dirección, año escolar, mes de inicio y día de vencimiento.

Los datos de Windows quedan en `%LOCALAPPDATA%\AulaColegio\colegio.sqlite3`, separados del código. **Abrir-carpeta-de-datos.bat** abre esa carpeta. Actualizar o mover los archivos del programa no borra los datos. Usa la misma cuenta de Windows para abrir el sistema: cada cuenta tiene su propia carpeta local.

La interfaz utiliza el navegador de Windows; el servidor y la base de datos funcionan en la misma computadora. El servidor escucha exclusivamente en `127.0.0.1` y no está preparado para acceso desde otras computadoras. Los registros y consultas funcionan sin internet. La tasa BCV requiere consultarla y registrarla manualmente.

## Flujo diario

1. Crea los **grados / secciones** y su capacidad.
2. Registra los **representantes**, con cédula, teléfono y correo. Un representante puede estar asociado con varios alumnos.
3. **Matricula a los alumnos**: documento o código único, fecha de nacimiento, grado, representante, año escolar, fechas de matrícula, mensualidad en USD y descuento o beca.
4. En **Mensualidades y cargos**, genera el período mensual. La generación respeta las fechas de matrícula, el estado del alumno y el descuento; repetirla no duplica cargos. Los cargos adicionales permiten registrar inscripción, transporte, actividades y otros conceptos.
5. Registra la **tasa BCV** de la fecha del cobro: bolívares por un dólar. Consulta la publicación oficial en [bcv.org.ve](https://www.bcv.org.ve/). Fines de semana y feriados: registra para la fecha del pago la tasa oficial vigente que corresponda. El sistema no la descarga ni certifica automáticamente.
6. En **Caja y cobros**, selecciona alumno, fecha, moneda, importe, método y referencia. El sistema admite abonos parciales y aplica primero los cargos pendientes más antiguos. Imprime el comprobante o guárdalo como PDF desde el diálogo de impresión de Windows.
7. En **Morosidad**, filtra por alumno, representante o grado; consulta deuda vencida y días de atraso. Prepara avisos de cobranza para copiar y compartir por tus propios medios. **Seguimiento** registra contactos, acuerdos y fecha prometida de pago; los avisos no se envían automáticamente.
8. Registra gastos y pagos al personal en **Egresos y nómina**. El módulo de personal conserva el salario de referencia; cada desembolso se registra explícitamente.
9. Consulta **Reportes** por rango de fechas y exporta los libros completos como CSV compatible con Excel. Los CSV incluyen los registros anulados y su estado. La morosidad corresponde al corte actual, aunque filtres ingresos de otro período.

### Año escolar y matrícula

El año escolar usa su **año de inicio**: `2026` significa `2026–2027`. Por defecto empieza en septiembre y termina en agosto del año siguiente; se puede configurar otro mes de inicio. Las fechas de matrícula deben estar dentro de ese año escolar. Un alumno matriculado durante un mes recibe el cargo completo de ese mes; **no se calcula prorrateo automático**. Usa un cargo manual si necesitas un importe especial.

Al pasar un alumno a otro año escolar, actualiza su matrícula y fechas. Sus cargos y pagos anteriores permanecen en su cuenta. Esta versión guarda la matrícula actual; no incluye un módulo separado de expedientes de matrícula por cada año. Inactivar un alumno evita nuevas mensualidades automáticas, pero mantiene la deuda existente.

### Dinero, conversiones y correcciones

- Los importes se guardan como **centavos enteros**, con dos decimales. La conversión de Bs a USD usa aritmética decimal y redondea al centavo más cercano, con mitad hacia arriba. Las tasas admiten hasta seis decimales.
- Ejemplo: mensualidad **50 USD**, descuento **10 %** → cargo **45 USD**. Pago **2.252,81 Bs** a **100,125 Bs/USD** → abono **22,50 USD** y saldo **22,50 USD**.
- Cada pago en Bs conserva el importe recibido, moneda, tasa aplicada y equivalente USD. Cambiar la tasa de esa fecha no modifica operaciones anteriores. Los recibos también conservan los datos del colegio, alumno y representante que tenían al emitirse.
- El saldo se mantiene en USD. El equivalente en Bs mostrado en morosidad es una referencia con la tasa registrada de hoy; al pagar se utiliza la tasa de la fecha elegida.
- Un pago no puede superar el saldo. Para anticipos, crea primero el cargo correspondiente al período futuro. No se lleva una billetera de créditos sin asignar.
- La generación de cargos y el registro de pagos son transaccionales. Una misma solicitud de pago reintentada conserva un solo recibo. Dos pagos distintos ingresados manualmente se consideran operaciones distintas: revisa referencias bancarias antes de cobrarlas otra vez.
- No se eliminan pagos ni egresos: el administrador puede **anularlos con motivo** y registrar la corrección. Anular un pago restaura la deuda que había abonado. Un cargo con pagos válidos no se puede anular hasta anular esos pagos.
- Cambiar tarifa, beca o día de vencimiento afecta cargos nuevos. No recalcula cargos ya emitidos. Los recargos y convenios especiales se registran como cargos explícitos; no hay intereses automáticos.

## Usuarios y respaldo

**Administrador:** configura el colegio, mantiene expedientes y usuarios, cobra, registra egresos, anula operaciones y descarga respaldos.

**Caja:** consulta expedientes y reportes, genera mensualidades, crea cargos, registra cobros, tasas BCV, seguimiento de cobranza y egresos. No puede modificar expedientes, gestionar usuarios ni anular operaciones.

**Consulta:** lectura de los módulos y reportes, sin operaciones de escritura. Los usuarios de consulta tienen acceso a expedientes y salarios; asigna este perfil solo a personas autorizadas para ver esa información.

Las contraseñas se almacenan con PBKDF2-SHA256 y sal aleatoria. Las sesiones vencen a las doce horas y se invalidan al cambiar la contraseña. La bitácora conserva las operaciones registradas; la interfaz muestra las últimas 300. La base no está cifrada: protege la cuenta de Windows y los archivos de respaldo. El sistema es para usuarios de confianza en una computadora local.

### Descargar y restaurar

- En **Configuración → Respaldo**, descarga una copia consistente de toda la base, incluso con el sistema abierto. Guarda copias periódicas en otro dispositivo.
- Al iniciar se guarda una copia automática por día en la subcarpeta `backups`; se conservan las últimas 30 copias diarias. Son copias del estado **al abrir el sistema**, no de cada operación. Para respaldar los cobros del día, descarga una copia al finalizar la jornada.
- Para restaurar, cierra Aula y ejecuta **Restaurar-respaldo.bat**. Selecciona el archivo `.sqlite3` y escribe `RESTAURAR`. La herramienta comprueba su integridad y compatibilidad, conserva una copia previa de los datos actuales y bloquea la restauración mientras Aula utiliza esa carpeta.
- Los respaldos no conservan sesiones autenticadas. Tras restaurar, inicia sesión con las cuentas que contiene el respaldo. El respaldo conserva sus contraseñas, por lo que debe almacenarse de forma segura.

También puedes restaurar desde la terminal:

```bat
py -3 -m colegio.restore --data-dir "%LOCALAPPDATA%\AulaColegio" --backup "D:\Respaldos\colegio.sqlite3"
```

## Alcance de esta versión

Incluye administración de alumnos y representantes, matrícula actual, grados y capacidad, tarifas y becas, mensualidades, otros cargos, cobranza, morosidad, recibos, tasas, personal, pagos de nómina, egresos, reportes, usuarios y respaldos.

Los recibos son **comprobantes administrativos**: no implementan facturación fiscal SENIAT. El módulo de nómina registra desembolsos y salarios de referencia; no calcula prestaciones, vacaciones, retenciones ni obligaciones laborales. Tampoco incluye contabilidad de partida doble, inventario, evaluación académica, conciliación bancaria automática ni integración con WhatsApp. Estos módulos necesitan reglas adicionales del colegio para una ampliación posterior.

## Desarrollo y validación

Python 3.10+ y un navegador moderno (Edge, Chrome o Firefox). El programa no tiene dependencias externas, servicios remotos, credenciales de terceros ni pasos de compilación.

```bash
python -m colegio.server
python -m unittest discover -s tests -v
```

En Linux puede ser necesario usar `python3`; en Windows, `py -3`. La ejecución manual usa `data/` dentro del proyecto. Puedes cambiar carpeta o puerto:

```bash
python -m colegio.server --data-dir /ruta/a/datos --port 8765
```

Las pruebas integradas usan bases temporales y verifican conversiones, abonos, distribución entre cargos, reintentos, anulaciones, tasas y recibos históricos, descuentos, años escolares, capacidad, permisos, CSRF, exportación y restauración. No escriben en la base real.

Validación opcional de interfaz, con Node, Playwright y Chromium disponibles:

```bash
python tests/run_browser.py
```

Este comando crea datos ficticios en una carpeta temporal, inicia su propio servidor y valida matrícula, mensualidades, cobro en Bs, recibo, morosidad, egresos, reportes, diseño adaptable y permisos de consulta. Para usar otro Chromium, define `CHROMIUM_PATH`. La prueba opcional no es una dependencia del programa.

El funcionamiento del servidor y la interfaz se verifica en Linux durante el desarrollo. Los lanzadores y la ruta de bloqueo de archivos para Windows requieren una prueba final en una computadora Windows antes de utilizar datos reales.
