# Cobrar mensualidades por adelantado

Diseño previo a la implementación · 30/10/2026 · rama `cashea`, Aula 1.0.74 en desarrollo, esquema 14. Base: `39d9e8d`. No hay una publicación 1.0.74 en Releases y la rama sigue abierta; este ajuste conserva esa versión y se entrega en commits separados.

## Lo que existe y por qué no se encuentra

- `colegio/db.py:296`: `assess_month` evalúa cada alumno/período una sola vez, incluso becas completas y cargos anulados. `monthly_assessments` tiene clave primaria alumno + período (`db.py:234`); `charges` tiene unicidad alumno + período + concepto (`db.py:191`). Conserva la tarifa evaluada y el vencimiento normal.
- `db.py:321`: `synchronize_monthly_charges` llega hasta el mes actual, dentro de matrícula, ciclo y `billing_start`; llama a esa misma evaluación. El día 1 no duplica una evaluación existente.
- `db.py:350`: `generate_month`, ruta POST `/api/generate` (`server.py:210`), prepara explícitamente un período para **todas** las matrículas elegibles del ciclo. Ya es idempotente; no se necesita un segundo mecanismo de cargos.
- `static/app.js:376`: `openPayment` limita alumnos a saldo positivo. Solo cuando **ningún** alumno tiene saldo ofrece “Preparar otro período”; `openGenerate` está en `app.js:406`. Si otro alumno debe, la acción no aparece en el formulario. Cashea (`static/cashea.js:27`) también excluye alumnos al día y solo lista cargos existentes.
- La preparación también tiene un botón permanente en **Mensualidades y cargos** (`static/app.js:239`); por tanto la función sí es accesible en otro módulo. El problema es que no se integra en el cobro individual, requiere salir de él y prepara todo el grupo, no solo el mes del alumno que está pagando.
- `db.py:380`: `record_payment` convierte con la tasa confirmada, limita el importe a la deuda y aplica desde el vencimiento más antiguo. No se cambiará esa función ni los snapshots históricos.

Referencias de línea de la base indicada, antes del cambio.

## Diseño confirmado y precisiones

1. Una consulta compartida de opciones por alumno devolverá cargos pendientes y meses futuros preparables. No escribe ni reserva IDs. Las dos pantallas la usan; permite alumnos al día y presenta meses futuros en gris, “Por adelantado”. El calendario usa la fecha real de Aula, no una fecha de pago atrasada para ampliar el límite.
2. Configuración `advance_months_limit`, por defecto 3, rango 0–12 (0 desactiva nuevas preparaciones). Solo Administración la cambia en Identidad y calendario. Se guarda en la tabla `settings` existente mediante UPSERT; sin DDL ni cambio de esquema. No insertar valores al abrir una copia en consulta. Los cargos ya preparados no desaparecen si se reduce el límite.
3. Meses futuros dentro del ciclo activo de Ajustes y del ciclo del alumno, matrícula activa/no archivada, `billing_start` y fin de matrícula. El máximo es distancia de calendario desde el mes actual (noviembre, diciembre, enero si hoy es octubre y el máximo es 3), no cantidad arbitraria de meses que permita saltar hasta otro año. Se respetan meses evaluados en cero o anulados sin recrearlos.
4. La selección debe ser un prefijo consecutivo de los cargos pendientes más antiguos y de los meses preparables, sin saltar deuda. El último puede recibir un abono parcial. No se preparan meses seleccionados que el importe no alcance; se rechaza con mensaje para revisar la selección. Se puede seguir cobrando deuda existente por la vía habitual, sin seleccionar anticipos.
5. Antes de confirmar se informa la tarifa neta vigente. Para cobro normal se verifica una cotización de las opciones al guardar; Cashea incorpora estas opciones a su hash de revisión. Si cambió tarifa, beca, calendario o saldo, se exige revisar de nuevo; nunca aceptar silenciosamente otra tarifa.
6. Dentro de la transacción de escritura existente (`BEGIN IMMEDIATE` del servidor), validar → `assess_month` por mes seleccionado → motor actual de cobros → anotación de **ese nuevo** snapshot → bitácora → commit. Cualquier error revierte cargos, evaluaciones, pago, aplicaciones y bitácora. La vista previa Cashea usa opciones virtuales; únicamente confirmar crea cargos y convierte sus identificadores virtuales en IDs reales, antes del motor actual.
7. Beca del 100 %: mostrar “Beca completa: sin cobro”. Una acción explícita registra solo las evaluaciones en cero, sin pago, sin recibo y sin consumir correlativos. Nunca se envía un pago de importe 0 al motor. Repetir la preparación no duplica la evaluación.
8. Nuevos recibos identifican las aplicaciones a períodos posteriores al mes de la fecha real del pago como “Mensualidad AAAA-MM (pagada por adelantado)”. El concepto del cargo permanece `Mensualidad`, para conservar integridad e idempotencia. No se reescribe ningún recibo anterior. Cierre de caja conserva fecha real y totales actuales.
9. Morosidad conserva el vencimiento normal: ningún cargo futuro pendiente está vencido. Estados de cuenta/solvencias nuevos identifican pagos adelantados, distinguiéndolos de cobertura financiada por Cashea. Resumen y reportes diario/mensual añaden un subtotal **informativo**, ya incluido en ingresos, sin sumarlo otra vez. Se calcula con aplicaciones válidas cuyo período es posterior al mes del pago; no depende de que hoy ese período siga siendo futuro. En Cashea se cuenta solo la inicial realmente recibida, no lo financiado ni una liquidación como un segundo anticipo. Mensual no modifica su semántica existente de saldo actual al corte, documentada en `monthly_report.py`.
10. Anular usa la vía existente y conserva el cargo preparado como deuda del mes, sin regenerarlo ni reutilizar R-. Se explica en el diálogo y la guía. Reintentar `request_key` no prepara nuevos meses ni altera snapshots; claves con datos distintos se rechazan. El servidor conserva CSRF, permisos y bloqueo completo de modo consulta. La bitácora registra responsable, períodos, importes y pago/orden relacionados.
11. La ruta histórica de preparación masiva se conserva: no habilitarla para eludir el límite de Caja; preparación futura masiva queda solo para Administración. No cambia la generación automática hasta el presente ni el cobro de deuda ya existente.

## Pantallas y consultas afectadas

| Área | Tratamiento |
|---|---|
| Cobro, `static/app.js`, `server.mutate` | Lista compartida, alumnos al día, aviso de tarifa, selección y preparación atómica. |
| Venta Cashea, `static/cashea.js`, `colegio/cashea.py` | Misma lista/preparación; revisión sin escribir; conservar inicial, financiación, numeración e idempotencia actuales. |
| Morosidad, `charges` / `snapshot` | Mantener `due_date < hoy`; prueba de no mora. |
| Resumen / principal, `server.snapshot`, `state_view.py` | Subtotal informativo sobre el libro completo; no duplicar ingreso. |
| Cierre de caja, `administration.cash_preview` | Mismo dinero, moneda, fecha y método; prueba de referencia. No modificar snapshots de cierres previos. |
| Diario, `directory_reports.daily_report` | Línea informativa de cobros del día para meses posteriores al pago. |
| Mensual, `monthly_report.report` | Línea informativa equivalente; cargo ya pagado no se presenta pendiente. Exportaciones PDF/CSV conservan monedas y totales. |
| Estado de cuenta y solvencia, `administration.guardian_account`, `documents.py`, interfaz | Etiqueta “Pagado por adelantado” en documentos nuevos y ficha. No cambiar documentos emitidos. |
| Convenios | Siguen organizando deuda vencida, sin crear deuda ni incluir anticipo futuro como mora. |
| Pase de año | Sin cambio; conserva evaluaciones del ciclo anterior y no permite preparar el siguiente ciclo por este formulario. |
| Consulta y respaldos | Opciones solo de lectura; toda preparación bloqueada en servidor en modo consulta. Sin nuevo esquema ni migración; instalación en cero sigue vacía. |
| Ajustes, guías, bitácora y pruebas | Límite de meses, instrucción “Cómo cobrar un mes por adelantado”, etiquetas y evidencia real. |

## Validación y entrega

Línea base y validación final: `python -m unittest discover -s tests -v`, `python tests/run_browser.py`, `--demo`, `--roster`. Pruebas añadidas: 30/10→noviembre, día 1 sin duplicados, dos meses, máximo/ciclo/matrícula/billing_start, deuda previa y selección, tarifa congelada y cotización caducada, beca completa, parcial, cierre, anulación, reintento/concurrencia, perfiles/CSRF/consulta, Cashea y reportes al corte. Comparar totales y snapshots anteriores con el mismo conjunto ficticio; comprobar integridad, claves foráneas y bitácora. Mantener todas las pruebas anteriores, incluidas migraciones y cero instalación. ZIP saneado incremental con diff y evidencia. No se solicita publicación final ni se modifican datos reales. Pruebas Windows o físicas no ejecutadas se indicarán expresamente.
