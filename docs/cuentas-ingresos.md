# Cuentas e ingresos · rama de revisión

En **Control de ingresos**, Administración configura cuentas bancarias por nombre, moneda y cuatro últimos dígitos. No escribas el número completo. Para efectivo crea una cuenta de tipo «Caja efectivo» por moneda. No hay cuentas ni categorías precargadas. La moneda y el tipo no cambian una vez creada la cuenta: desactívala y crea otra si hace falta.

Cada cobro nuevo lleva cuenta destino. Efectivo propone la única Caja efectivo compatible; transferencia y pago móvil proponen la última cuenta compatible usada para ese método. Confírmala. Los cobros anteriores siguen «Sin cuenta asignada». Administración puede revisarlos y asignarlos por sus ID; la asignación no modifica importes, recibos ni correlativos. Los egresos también pueden llevar cuenta; sus ID aparecen en el listado.

Para depositar efectivo, Caja o Administración registra fecha, importe original, moneda, banco destino, referencia, soporte y recibos cubiertos. Cada vínculo indica la parte del recibo cubierta. No se permite cubrirlo dos veces. Si existe diferencia, explica el motivo. Un depósito traslada saldo de efectivo a banco, **no suma otro ingreso**. El cierre diario descuenta lo depositado del efectivo esperado. Un recibo vinculado no puede anularse hasta revisar y anular el depósito. Solo Administración anula depósitos, con motivo.

Administración registra otros ingresos separados de mensualidades, con categoría, fecha, moneda, cuenta y soporte. Se suman a ingresos de caja/reportes con identificación propia. No generan recibos de mensualidades ni cargos. No se editan después de registrar: si hay un error, Administración anula con motivo y registra el correcto. Guarda el soporte fuera del repositorio público; el campo registra una descripción o identificación, no adjunta archivos.

Consulta ve resúmenes, sin soporte ni datos bancarios del catálogo. No escribe. Los cierres diarios existentes bloquean movimientos y asignaciones del día cerrado. Cada operación queda en bitácora y conserva los respaldos habituales.

## Actualización y reversión

La primera ampliación de esta rama agrega siete tablas (esquema 13); no reconstruye ni borra tablas anteriores. Antes de la primera actualización de una base existente verifica integridad, claves foráneas y cadena, y crea una copia consistente en `.aula-migrations/schema-13/`, dentro de su carpeta de datos. El manifiesto JSON identifica esquema y copia. Si el cifrado ya está configurado y desbloqueado, la copia queda cifrada y verificada; si está configurado pero bloqueado, la actualización se detiene antes de crear su carpeta o copiar. Sin cifrado configurado queda una copia SQLite privada: protégela junto con la carpeta de datos. No se presenta como respaldo externo cifrado ni se elimina automáticamente.

Para revertir, cierra Aula y conserva **toda la carpeta actual**, incluidos registros nuevos. Con la versión anterior compatible, restaura la copia previa en **otra carpeta de datos vacía**, usando contraseña o recuperación si está cifrada. Verifica datos y totales antes de usarla. La copia previa no contiene operaciones posteriores; volver a ella no las incorpora. No abras el esquema 13 con un ejecutable antiguo ni sobrescribas la carpeta original.

La limpieza excepcional de cobros de prueba se bloquea si hay clasificaciones o registros del nuevo libro; requiere una revisión específica, no una eliminación automática de esos datos.

## Bloques posteriores

La [conciliación bancaria](conciliacion-bancaria.md) y el [cierre mensual](control-ingresos-cierre-mensual.md) tienen sus propias guías. Sus ampliaciones son los esquemas 14 y 15, también aditivos y con copia previa. Las facturas y las conversiones entre cuentas o monedas siguen pendientes. Provincial, formulario real, calibración física y confirmación fiscal: **NO VERIFICADO**. Aula no se conecta a bancos ni al SENIAT ni calcula IVA o IGTF.
