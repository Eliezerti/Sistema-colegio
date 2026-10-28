# Cashea · Aula 1.0.74

El colegio registra la venta manualmente. Aula no se conecta a Cashea ni controla las cuotas que paga el cliente. El recibo de Aula no es una factura fiscal: el colegio debe validar con Cashea y su contador el uso de ese número. Valida también el tratamiento de comisiones y diferencias.

## Registrar una mensualidad

1. En Caja y cobros, elige el alumno y el método **Cashea**; también puedes entrar en **Cashea → Registrar venta**.
2. Marca las mensualidades desde la más antigua y revisa el total en USD. Puedes ajustar el total para cubrir solo una parte. Un cargo anterior de otro concepto debe resolverse por el cobro normal primero.
3. Escribe el porcentaje de inicial y pulsa **Calcular inicial** si necesitas una sugerencia. El importe realmente recibido es el que se registra. Con USD 130 y 60 %, la sugerencia es USD 78; quedan USD 52 financiados. Con USD 133,33 y 50 %, son USD 66,67 y USD 66,66.
4. Indica moneda, método real y referencia de la inicial. Para bolívares debe existir y estar confirmada la tasa de esa fecha. La etiqueta indica **Inicial recibida (Bs)**; al cambiar desde USD se convierte la cifra, y se muestran la tasa y el equivalente en USD. La calculadora respeta la moneda elegida. Si el equivalente difiere más de 1 % de la inicial por porcentaje aparece una advertencia: revisa la moneda y el importe antes de confirmar; lo realmente recibido manda. Puedes registrar inicial cero: no se genera recibo R- ni se consume su número.
5. Por defecto, **Número de factura** es el mismo **R-** del recibo de la inicial. Verás el siguiente número previsto; se confirma al guardar. Si otro cajero lo utiliza primero, revisa de nuevo. En la confirmación, el detalle y el listado puedes pulsar **Copiar** para llevar el número al portal de Cashea. Con origen Recibo e inicial cero se usa el **CA-**, rotulado **N.º de orden**. Si Administración eligió **Manual**, escribe el número obligatorio; una repetición exige revisión explícita y motivo. No se puede duplicar un identificador originado en un recibo u orden, aunque esté anulado.
6. Revisa la fecha esperada, los cargos, inicial, financiado y saldo; después confirma. Por defecto se espera el miércoles estrictamente siguiente: una venta en miércoles vence el miércoles de la semana siguiente.
7. Guarda el CA-. Si hubo inicial, también existe un R- normal con su método real y un bloque Cashea. Los recibos anteriores conservan su contenido. La parte financiada cubre la mensualidad y no deja al alumno moroso; todavía no es dinero recibido por el colegio.

## Registrar el depósito de Cashea

1. En **Cashea**, revisa las semanas y las órdenes vencidas. La alerta corresponde a la deuda de Cashea, no a una mora del alumno.
2. Pulsa **Registrar liquidación** y marca solo las órdenes incluidas en el depósito. Las que dejes sin marcar siguen pendientes.
3. Indica fecha de recepción, moneda, importe real y referencia bancaria. En VES se conserva la tasa de esa fecha. Revisa financiado bruto, neto esperado y recibido; escribe un motivo si existe cualquier diferencia, incluida una comisión descontada.
4. Confirma y conserva el CL-. El dinero entra como transferencia bancaria; no aumenta el efectivo esperado del arqueo. No se crea un egreso automático por comisión.
5. Puedes descargar pendientes, liquidaciones y ventas para Cashea en PDF, CSV o XLSX. El listado externo identifica al alumno solo por AL-, sin nombre, cédula ni nacimiento.

## Ajustes, correcciones y seguridad

Administración configura el día semanal, origen del número de factura (Recibo o Manual), comisión y días de gracia en **Configuración → Cashea**. Los valores iniciales son miércoles, Recibo, 0 % y cero días. La comisión y el neto quedan fijados al registrar cada orden; cambiar ajustes no modifica ventas anteriores. Caja registra ventas y liquidaciones; Consulta ve cifras y reportes.

Solo Administración puede anular, con motivo. Anula primero el CL- si la orden ya estaba liquidada; luego, si corresponde, el CA-. Anular CL- devuelve sus órdenes a pendientes; anular CA- restaura la deuda y anula su inicial. No borra registros ni reutiliza números. La orden anulada indica **Anulada: anular también en el portal de Cashea**: ese paso externo lo hace el colegio. No se permite anular la inicial desde el botón genérico de recibos. Los días cerrados siguen protegidos. La fecha esperada de una orden pendiente se puede corregir con motivo desde su detalle.

Los estados de cuenta muestran la cobertura inicial + financiado. El informe mensual separa Cashea al corte por fechas de venta, recepción y anulación. El cierre diario distingue financiado, que no es caja, de depósitos reales. Los respaldos, su comprobación y el modo consulta incluyen Cashea; un alumno con historial CA- no se puede borrar.

## Actualizar y volver atrás

Instala 1.0.74 sobre el programa; no reemplaces la carpeta de datos. Las migraciones 12 → 13 → 14 verifican la base y conserva `backups/antes-cashea-...sqlite3` y su comprobación `.migration.json`. Para el ajuste 13 → 14 conserva también `backups/antes-numero-cashea-...sqlite3`. Las órdenes anteriores quedan como Manual, sin cambiar sus números ni snapshots, incluso duplicados autorizados. Si hay segundo destino configurado, exige y verifica allí una copia cifrada del esquema anterior antes de cambiarlo; si falla, no migra. Esa copia previa no se elimina por la rotación normal.

Al convertir, restaurar o abrir un respaldo antiguo en consulta, Aula migra una copia temporal verificada. No escribe en el segundo destino de la escuela de origen ni necesita su almacén de llaves. El archivo original se conserva intacto; para una copia cifrada sigue siendo necesaria su contraseña o clave de recuperación.

Para revisar una reversión, cierra Aula y usa 1.0.73 **en otra carpeta de datos** con una copia de la base previa verificada. Para volver al ejecutable anterior de esquema 13, usa su copia previa de esquema 13 en otra carpeta. No abras una base 14 con un ejecutable de esquema 13 o 12. Conserva la base actual y todos los registros posteriores para revisión: volver a la copia previa no traslada operaciones posteriores. La restauración normal de Aula conserva sus advertencias, pisos de numeración e informes de pérdida. Una instalación nueva continúa vacía, sin usuarios por defecto.

La validación de impresora física y la revisión de una liquidación real con el contador requieren al colegio. Las pruebas automatizadas usan exclusivamente información ficticia.
