# Diseño Cashea · Aula 1.0.74 · antes de programar

Base: commit validado `324d388`, Aula 1.0.73, esquema 12. Rama `cashea` en un worktree separado. La corrección documental local de `2a3d00b` se copia íntegra a esta rama; el original queda igual. El borrador `autonomo/ingresos-facturas` no se consulta ni modifica. Los resultados previos de la base son 314 pruebas (311 correctas y tres exclusivas de Windows omitidas en Linux) y los tres navegadores correctos. Se repetirán con el código final.

## Contabilidad operativa

Una venta cubre la deuda del alumno por **inicial + financiado**. Solo la inicial y las liquidaciones recibidas son dinero cobrado. El financiado se presenta como cobertura Cashea y cuenta por liquidar; nunca se inserta como pago ficticio. No hay cuotas del cliente que administrar. No se conecta a Cashea, bancos o SENIAT ni se generan números de factura.

Ejemplo: total 13000 centavos, inicial 7800 y financiado 5200. Saldo del alumno cero; caja recibió 7800. Cuando llega la liquidación, entra su importe real, una sola vez y fuera de efectivo. Con inicial cero no existe R-: siempre existe CA-.

## Inventario de lecturas y sumas (estado antes del cambio)

| Archivo / línea | Uso actual | Integración prevista |
|---|---|---|
| `db.py:252–267` | BALANCES, cargos, abonado/saldo/vencimiento | Única expresión de cobertura: abonos válidos + asignaciones de órdenes no anuladas. Distinguir dinero abonado de financiado; sin órdenes, mismo resultado financiero |
| `db.py:354–416` | Cobro, FIFO, idempotencia, snapshot y R- | Reutilizar record_payment para la inicial; metadatos Cashea opcionales solo al construir un recibo nuevo. Ningún UPDATE de snapshot histórico |
| `server.py:61–127` | snapshot, saldos familiares, resumen, antigüedad e ingresos del mes | Deuda desde BALANCES; ingresos reales incluyen liquidaciones válidas. Campos Cashea separados, sin convertir CL- en pagos R- |
| `state_view.py:7–35` | Principal reducido, cobrado hoy, monedas y conteos | Sumar liquidaciones reales al dinero de hoy y mostrar desglose; financiado nunca cobrado |
| `static/app.js:150–166` | Resumen | Desglose Cashea sin doble conteo; sin Cashea conserva funcionamiento |
| `static/app.js:227–259` | Matrícula, cargos, caja, morosidad y reportes | Deuda cubierta desde servidor; etiquetas explícitas de Cashea; estados de cuenta con desglose |
| `administration.py:351–385` | Resumen y cierre, arqueo, huella de movimientos | Incorporar liquidación real como transferencia; bloque Cashea del día. Huella incluye ventas/CL para invalidar revisión vieja; efectivo solo pagos/egresos de ese método |
| `administration.py:396–425` | Cuenta familiar y solvencia | Cargos cubiertos por inicial+financiado; texto «Pagada con Cashea» y vínculos CA-. No inventar recibos |
| `directory_reports.py:141–207` | Diario, monedas cobradas, morosidad por grado | Inicial normal; liquidaciones reales separadas; cobertura no morosa; CA/CL en bloque propio |
| `monthly_report.py:13–83` | Caja por método/moneda, pendientes actuales y anulaciones | Sección Cashea al corte con fechas de venta/liquidación/anulación; importes reales y cobertura separados. El resto del reporte conserva su contrato |
| `lifecycle.py:84–95` | Convenios: suma directa de allocations | Reutilizar la cobertura central de db.py para considerar Cashea, sin duplicar fórmulas de saldo |
| `lifecycle.py:13–80` | Matrícula y pase de año | Nuevas tablas conservadas; respaldo permanente contiene Cashea. No borrar ni trasladar órdenes al promocionar |
| `student_admin.py:46–86` | Corrección de meses: impide cargos abonados | La cobertura Cashea también impide corregir esos cargos como si estuviesen impagos |
| `institution_archive.py:32–156` | Revisión, huella y borrado definitivo | Toda orden Cashea protege la ficha, incluso anulada o con inicial cero |
| `documents.py` / recibo HTML en `app.js` | PDF/HTML de R-, cuentas, solvencias y cierre | Bloque opcional en R- nuevo; PDF CA- propio; textos de cobertura y bloque de cierre. Sin modificar la representación de recibos anteriores sin Cashea |
| `backup_inspection.py:12–104` | Tablas, saldos, monedas y pisos al probar respaldo | Exigir tablas Cashea en esquema 13, validar invariantes y computar cobertura/liquidaciones; bases antiguas siguen inspeccionándose sin tablas nuevas |
| `restore_reports.py:9–95`, `restore.py:49–138` | Comparación, pérdidas, reservas y restauración | Mostrar órdenes/CL ausentes, reservas CA/CL y conservar nuevas tablas en copia/migración |
| `maintenance.py:4–72` | Verificar datos y correlativos | CA/CL, totales inicial+financiado, asignaciones, alumno, membresías, estados, diferencias y huellas |
| `trial_payment_cleanup.py:27–99` | Limpieza excepcional de cobros ficticios | Bloquear si existe cualquier historial Cashea; nunca dejar órdenes ligadas a inicial borrada |
| `read_only.py:79–113` | Inspección, migración en temporal y SQLite inmutable | Compatibilidad 13 y vistas Cashea; todos los POST nuevos bloqueados por el gate existente |
| `server.py:162–203, 335–360, 895` | Mutaciones, cierre y respaldo posterior | Nuevas acciones con permisos, CSRF, reloj, cadena e idempotencia; impedir anular una inicial por fuera de la orden |
| `tests/permission_matrix.py`, `test_read_only_copy.py` | Inventario de rutas y contrato por perfil | Agregar GET/POST nuevos; Consulta lee informes, Caja crea ventas/CL, Administración configura/anula |
| `db.initialize`, `schema.py`, `audit_chain.py`, `tests/zero_install.py` | Arranque, esquema y guards | Migración 12→13 aditiva con copia verificada; todas las tablas Cashea vacías y pisos CA/CL cero |

También se revisarán exportaciones de pagos/egresos, listados de alumnos y guardianes, importación y documentos históricos: R- sigue siendo un pago real; Cashea tiene sus propios informes, no se altera un CSV antiguo silenciosamente.

## Esquema 13 y decisiones que precisan el diseño propuesto

1. Se conservan las cuatro tablas propuestas: `cashea_orders`, `cashea_allocations`, `cashea_settlements`, `cashea_settlement_orders`.
2. Se agrega **cashea_requests**, una tabla técnica vacía de idempotencia. Motivo: también ajustes y anulaciones necesitan request_key, huella de contenido, actor y respuesta confirmada; solo poner una clave en la venta/CL no cubre esos POST. La clave se guarda como hash y queda protegida por A5. Alternativa descartada: buscar respuestas dentro de JSON de la bitácora sin una unicidad SQL. No hay datos precargados.
3. Órdenes y liquidaciones guardan snapshot propio para emitir/reimprimir CA/CL y fechas de anulación. Se conservan las asignaciones y membresías históricas; al anular se dejan sin efecto mediante el estado/fecha, no se borran filas ni se reescribe el snapshot.
4. Los pisos `id_floor_cashea_orders` y `id_floor_cashea_settlements` empiezan en cero, se usan con next_record_id y se preservan al restaurar. CA-/CL- empiezan en 1; R-/E-/AL- no se reinician.
5. Una orden captura comisión, descuento estimado y neto esperado al crearla: cambiar ajustes no recalcula ventas anteriores. Porcentajes en texto decimal validado y puntos básicos enteros para cálculo; dinero en centavos. Redondeo HALF_UP y financiado = total − inicial, sin pérdida de centavos.
6. Se muestran **dos diferencias** en la liquidación: recibido menos neto esperado, y recibido menos financiado bruto. Resuelve la ambigüedad entre «comisión reduce esperado» y «comisión se refleja en diferencia». Se ve bruto/comisión/neto/recibido; cualquier descuento o diferencia exige explicación. No se crea un egreso automático ni se traslada al alumno. Nota visible de consulta con contador.
7. Liquidaciones bancarias se registran como transferencia, separadas de R-. No incrementan el arqueo de efectivo. Se admite selección parcial del lote de órdenes, no cuotas ni pagos parciales de una orden: una diferencia aceptada con motivo liquida las órdenes seleccionadas.

## Creación, cargos y comprobantes

La vista previa revisa la deuda actual y las mensualidades elegidas. Para no cambiar el FIFO de record_payment, deben corresponder al prefijo más antiguo de cargos pendientes que cubre el total. Si hay un cargo anterior de otro concepto, se informa y se resuelve por cobro normal; no se redirige la inicial a otro cargo silenciosamente. Total no supera deuda seleccionada; no se financian intereses inventados.

En una sola transacción: validar revisión/fechas/cierre → crear orden → registrar inicial mediante record_payment si es positiva → asignar financiado al resto de los mismos cargos → guardar comprobante y respuesta idempotente → comprobar → confirmar cadena y SQL. Una segunda solicitud idéntica devuelve la misma respuesta; otro contenido/actor con la clave se rechaza. CSRF, sesión, reloj, cadena y permisos se comprueban antes.

La calculadora de porcentaje sugiere la inicial; el importe realmente recibido manda. 133,33 al 50 % sugiere 66,67 y financia 66,66. Para VES se usa convert_received con la tasa de la fecha; no se usa float ni se recalcula la tasa histórica. Inicial cero no llama al motor de pagos ni consume R-.

Factura manual obligatoria por defecto; duplicado normalizado exige confirmación explícita y motivo. Referencia Cashea opcional. Fecha de venta no futura. Día esperado por defecto miércoles estrictamente siguiente, incluso si la venta es miércoles; fecha editable no anterior a venta. Día semanal y días de gracia configurables por Administración, con request_key y bitácora.

CA- contiene únicamente escuela, alumno/grado, mensualidades, importes, factura, referencias y fecha esperada; no cédula ni nacimiento del menor. No es factura fiscal. El R- de inicial nuevo recibe un campo Cashea calculado internamente, ignorando campos falsificados en el cobro normal; los snapshots anteriores no se actualizan.

## Anulaciones, informes al corte y restauración

Solo Administración anula. Una orden pendiente revierte cobertura y anula su inicial con las validaciones actuales; un pago ligado no se anula por el botón genérico. Con orden liquidada se exige anular primero su CL. La anulación de CL conserva sus órdenes y membresías históricas y las devuelve a por_liquidar. Toda operación respeta el cierre de su fecha; se registra fecha efectiva de anulación, actor y motivo. No se permite liquidar anuladas ni fechas recibidas anteriores a sus ventas.

El informe Cashea al corte se calcula por fecha de venta, recepción y anulación; no se filtra solo por el estado actual. Una CL anulada después del corte sigue contando en aquel corte; una posterior al corte no lo liquida retrospectivamente. Se separan vendido, inicial, financiado, recibido, financiado liquidado y pendiente bruto/neto. No se rehacen cierres ni documentos emitidos antes.

Migración: reserva de escritor y bloqueo → verificar 12/cadena/FK → copia previa consistente y hash comprobado (con cifrado de segundo destino si está configurado) → DDL aditivo, defaults y guards de nuevas tablas → version 13/evento → verificar y COMMIT. Reintento tras corte completa o conserva íntegro 12; no hay media migración. Reversión documentada con copia anterior y 1.0.73 en carpeta distinta, conservando datos posteriores para revisión. Fixture real ficticio creado por el código publicado 324d388, sin falsificar PRAGMA para simular una versión.

## Validación y entrega

- Referencia sin Cashea: mismos pagos, allocations, importes, snapshots, numeración, caja y reportes de 1.0.73; ajustes/esquema/tablas técnicas nuevos se documentan aparte.
- Pruebas de 130/78/52, inicial cero, 133,33, varios cargos, tasas VES, fechas, duplicados, idempotencia, diferencias, selección parcial, anulaciones, cierres, convenios, solvencias, corte, permisos, consulta, respaldo/restauración y cortes reales de proceso.
- Conservar las 314 pruebas; documentar únicamente adaptaciones necesarias por esquema 13 y por el inventario ampliado de rutas/tablas. No omitir pruebas para conseguir un verde.
- Flujo de navegador completo y tres modos normal/Pruebas/importación. Resultados reales; Windows/impresora física se distinguen de Linux cuando no estén disponibles.
- Versión 1.0.74 en metadatos/instalador/flujo/docs; actualización nativa desde 1.0.73 en el verificador. No hay release final, firma digital ni merge a main.
- Commits pequeños, CHANGELOG y guía Cashea; ZIP de revisión con diff íntegro y archivos cambiados, sin bases reales, secretos ni personas reales. El fallo de empaquetado de evidencia queda en commit separado si se corrige.

Este diseño se entrega antes de implementar. No exige otra aprobación en el texto recibido; se continúa con su implementación y las pruebas.
