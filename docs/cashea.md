# Cashea · Aula 1.0.74

El colegio registra la venta manualmente. Aula no se conecta a Cashea ni controla las cuotas que paga el cliente. El comprobante CA- es administrativo; no es factura fiscal. Valida con tu contador el tratamiento de comisiones y diferencias.

## Registrar una mensualidad

1. En Caja y cobros, elige el alumno y el método **Cashea**; también puedes entrar en **Cashea → Registrar venta**.
2. Marca las mensualidades desde la más antigua y revisa el total en USD. Puedes ajustar el total para cubrir solo una parte. Un cargo anterior de otro concepto debe resolverse por el cobro normal primero.
3. Escribe el porcentaje de inicial y pulsa **Calcular inicial en USD** si necesitas una sugerencia. El importe realmente recibido es el que se registra. Con USD 130 y 60 %, la sugerencia es USD 78; quedan USD 52 financiados. Con USD 133,33 y 50 %, son USD 66,67 y USD 66,66.
4. Indica moneda, método real y referencia de la inicial. Para bolívares debe existir y estar confirmada la tasa de esa fecha. Puedes registrar inicial cero: no se genera recibo R- ni se consume su número.
5. Escribe el número de factura y, si existe, la referencia Cashea. Aula no inventa números fiscales. Una factura repetida exige revisión explícita y motivo.
6. Revisa la fecha esperada, los cargos, inicial, financiado y saldo; después confirma. Por defecto se espera el miércoles estrictamente siguiente: una venta en miércoles vence el miércoles de la semana siguiente.
7. Guarda el CA-. Si hubo inicial, también existe un R- normal con su método real y un bloque Cashea. Los recibos anteriores conservan su contenido. La parte financiada cubre la mensualidad y no deja al alumno moroso; todavía no es dinero recibido por el colegio.

## Registrar el depósito de Cashea

1. En **Cashea**, revisa las semanas y las órdenes vencidas. La alerta corresponde a la deuda de Cashea, no a una mora del alumno.
2. Pulsa **Registrar liquidación** y marca solo las órdenes incluidas en el depósito. Las que dejes sin marcar siguen pendientes.
3. Indica fecha de recepción, moneda, importe real y referencia bancaria. En VES se conserva la tasa de esa fecha. Revisa financiado bruto, neto esperado y recibido; escribe un motivo si existe cualquier diferencia, incluida una comisión descontada.
4. Confirma y conserva el CL-. El dinero entra como transferencia bancaria; no aumenta el efectivo esperado del arqueo. No se crea un egreso automático por comisión.
5. Puedes descargar pendientes, liquidaciones y ventas para Cashea en PDF, CSV o XLSX. El listado externo identifica al alumno solo por AL-, sin nombre, cédula ni nacimiento.

## Ajustes, correcciones y seguridad

Administración configura el día semanal, factura obligatoria, comisión y días de gracia en **Configuración → Cashea**. Los valores iniciales son miércoles, sí, 0 % y cero días. La comisión y el neto quedan fijados al registrar cada orden; cambiar ajustes no modifica ventas anteriores. Caja registra ventas y liquidaciones; Consulta ve cifras y reportes.

Solo Administración puede anular, con motivo. Anula primero el CL- si la orden ya estaba liquidada; luego, si corresponde, el CA-. Anular CL- devuelve sus órdenes a pendientes; anular CA- restaura la deuda y anula su inicial. No borra registros ni reutiliza números. No se permite anular la inicial desde el botón genérico de recibos. Los días cerrados siguen protegidos. La fecha esperada de una orden pendiente se puede corregir con motivo desde su detalle.

Los estados de cuenta muestran la cobertura inicial + financiado. El informe mensual separa Cashea al corte por fechas de venta, recepción y anulación. El cierre diario distingue financiado, que no es caja, de depósitos reales. Los respaldos, su comprobación y el modo consulta incluyen Cashea; un alumno con historial CA- no se puede borrar.

## Actualizar y volver atrás

Instala 1.0.74 sobre el programa; no reemplaces la carpeta de datos. La migración 12 → 13 verifica la base y conserva `backups/antes-cashea-...sqlite3` y su comprobación `.migration.json`. Si hay segundo destino configurado, exige y verifica allí una copia cifrada del esquema anterior antes de cambiarlo; si falla, no migra. Esa copia previa no se elimina por la rotación normal.

Para revisar una reversión, cierra Aula y usa 1.0.73 **en otra carpeta de datos** con una copia de la base previa verificada. No abras una base 13 con el ejecutable anterior. Conserva la base 13 y todos los registros posteriores para revisión: volver a la copia previa no traslada operaciones posteriores. La restauración normal de Aula conserva sus advertencias, pisos de numeración e informes de pérdida. Una instalación nueva continúa vacía, sin usuarios por defecto.

La validación de impresora física y la revisión de una liquidación real con el contador requieren al colegio. Las pruebas automatizadas usan exclusivamente información ficticia.
