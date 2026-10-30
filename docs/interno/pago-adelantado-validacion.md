# Pago de mensualidades por adelantado · revisión

30/10/2026 · Aula 1.0.74 en desarrollo, rama `cashea`, esquema 14. Base `39d9e8d`; código del ajuste `21107054a9e7f1a0f8d0f0cdfbc3912b2fbb0fd1`. Sin fusión a main, etiquetas ni publicación final. No se usaron datos del colegio ni se modificaron bases reales. No se añadieron dependencias.

[Diseño entregado antes del código](../../DISENO_PAGO_ADELANTADO.md) · [Guía de cobro](../cobros-y-arqueo.md#cómo-cobrar-un-mes-por-adelantado) · [Salida real completa de Linux y fallo inicial](pago-adelantado-pruebas.txt).

## Qué se encontró

La preparación explícita **sí existía**: `generate_month`, `colegio/db.py:350`, ruta POST `/api/generate`. También existe el botón de Mensualidades y cargos. La pantalla de cobro solo ofrecía preparar otro período cuando ningún alumno tenía saldo y excluía alumnos al día; Cashea también los excluía. Preparar el período por esa vía afecta a todo el grupo, no solo al alumno que paga. No era necesario inventar otro generador.

La unicidad ya estaba protegida por `monthly_assessments` (alumno + período), la unicidad del cargo y `assess_month`, que se conserva sin cambios. Preparar ahora noviembre y abrir Aula el 1 de noviembre no crea una segunda mensualidad.

## Qué cambió

- Cobro y Cashea comparten una consulta de opciones por alumno. Muestran alumnos al día y meses futuros en gris, “Por adelantado”. Selección consecutiva desde la deuda más antigua; el último mes admite abono parcial. No se crea un mes seleccionado al que el importe no alcance.
- Máximo de 3 meses siguientes por defecto, configurable de 0 a 12 solo por Administración. Se respeta el ciclo activo, matrícula, `billing_start`, estado activo y fin de matrícula. Cero impide nuevas preparaciones; no borra cargos existentes. La preparación futura masiva queda solo para Administración, para que Caja use el límite del cobro individual.
- Se verifica la tarifa antes de guardar. La transacción existente prepara mediante `assess_month`, registra el pago con el motor actual, anota el nuevo snapshot y la bitácora. Un error o cambio de reloj revierte todo. La evaluación guarda la tarifa/beca actual y no se recalcula después. Beca completa: evaluación en cero, sin pago ni R-.
- Las revisiones de Cashea no crean meses futuros. Confirmar convierte las opciones previstas en cargos reales y conserva sus reglas de inicial, financiación, factura R-/CA-, liquidación, permisos e idempotencia.
- El importe sugerido y su conversión USD/Bs usan enteros y redondeo HALF_UP. Al cambiar moneda en un anticipo se convierte también la cifra escrita, incluido un abono parcial; si falta tasa se deja vacío para revisar. El motor conserva su conversión original.
- Nuevos recibos indican “Mensualidad AAAA-MM (pagada por adelantado)” y fecha real. Nuevos estados de cuenta/solvencias identifican el adelanto. El vencimiento normal y la mora no cambian. Resumen y reportes añaden “Cobrado por adelantado (meses futuros)”, incluido en ingresos, sin contarlo dos veces. Se cuenta el dinero realmente aplicado a meses posteriores al mes del pago; financiación Cashea y liquidaciones no se presentan como un segundo anticipo. Los PDF/CSV sin anticipos conservan su estructura anterior.
- Anular conserva R-, motivo y cargo preparado, que queda pendiente con su vencimiento normal. Reintentos no preparan otro mes ni reescriben el recibo. Consulta, CSRF y perfiles se comprueban en el servidor.

## Protección de datos y esquema

No hay DDL ni migración nueva: se mantiene el esquema 14. `advance_months_limit` se lee con valor por defecto y se guarda mediante UPSERT en `settings` únicamente al guardar Ajustes. Abrir una copia en consulta no inserta ese ajuste. No se crean tablas, usuarios ni registros de negocio en una instalación nueva.

Se comparó literalmente el código de `record_payment`, `assess_month`, `synchronize_monthly_charges`, `convert_received` y `next_record_id` con la base: idénticos. [Huellas de esa comprobación](pago-adelantado-motor.json). `colegio/db.py`, el esquema y `session.js` no tienen diff. No se actualizan snapshots anteriores. Las pruebas conservan la referencia de caja, diario, mensual, pagos, órdenes y cadena de bitácora de los fixtures ficticios publicados 1.0.73 y 1.0.74/esquema 13; también ejecutan sus migraciones y respaldos verificados existentes. No se necesita una copia de migración 14→14 porque no se migra.

## Pruebas reales en Linux

Python 3.12.14 · SQLite 3.53.1 · cryptography 50.0.0 · Node 24.19.0 · Playwright JS 1.62.1. Sockets HTTP locales autorizados; bases temporales ficticias. No se omitieron pruebas para evitar restricciones del entorno.

| Comando | Resultado real |
|---|---|
| Línea base: `python -m unittest discover -s tests -v` | 358 en 397,900 s, OK, 3 omitidas por Windows |
| Línea base: navegadores normal, `--demo`, `--roster` | Los tres terminaron con código 0 |
| `python -m unittest discover -s tests -v` | **371 en 345,817 s, OK: 368 correctas, 3 omitidas** |
| `python tests/run_browser.py` | **Código 0**, flujo anterior + anticipos + consulta |
| `python tests/run_browser.py --demo` | **Código 0** |
| `python tests/run_browser.py --roster` | **Código 0** |
| Pruebas específicas de anticipo | 13 correctas; 17,700 s en ejecución dirigida |
| Pruebas de reloj | 7 correctas; 6,530 s en ejecución dirigida |

Las tres omisiones de Linux son DPAPI, mutex/enfoque de Windows y diálogo nativo Windows/Tk. Son las mismas que antes del cambio; no se eliminó ninguna de las 358 pruebas anteriores, incluidas las 314 originales y Cashea. Se añadieron 13.

La primera ejecución completa del ajuste tuvo **un fallo de 369**: el test que simulaba un cambio de reloj seguía interceptando `colegio.server.record_payment`; la invocación real ahora está dentro de `colegio.advance_payments`. Se corrigió el destino de la inyección, conservando respuesta 428 y verificaciones de rollback. Se añadieron pruebas del mismo caso con anticipo y de terminación real del proceso tras preparar la mensualidad; ambas revierten cargo, evaluación, pago y bitácora. Después pasó la ejecución completa de 371. La salida del fallo permanece en la evidencia.

## Casos cubiertos

30/10/2026→noviembre, un solo cargo y saldo/mora cero; día 1 sin duplicado; dos meses y abono parcial; orden más antiguo; selección sin saltos; límite, fuera de ciclo, matrícula y `billing_start`; tarifa cambiada antes de guardar y congelada después; beca 100 %; Bs con original/tasa/equivalente; límite cero; cierre de caja del día; anulación; solicitud repetida o cambiada; concurrencia de dos solicitudes; rollback por error, reloj y salida real del proceso; Administración/Caja/Consulta y CSRF; rutas en modo consulta; informes mensual/diario y PDF/CSV; saldo de Cashea 40/16/24 y revisión sin crear cargo; integridad, claves foráneas y bitácora.

El navegador recorre alumno al día → futuro → USD/Bs → abono parcial → recibo → Cashea → evaluación sin cobro, además del recorrido completo anterior. Las pruebas existentes verifican convenios, pase de año, instalación en cero, restauración, Probar respaldo, cifrado y conservación de historia.

PDF ficticio adicional: dos meses, fecha 30/10/2026, USD 80,00, **una página de 396 × 612 puntos**, comprobado con `pdfinfo` y `pdftotext`. No se modificó el diseño de impresión.

## Windows y límites

Validación nativa del mismo código iniciada en [Actions 41129108781](https://github.com/Eliezerti/Sistema-colegio/actions/runs/41129108781), job 124315173545, código `2110705`. **En curso al escribir esta revisión; no se cuenta como aprobada.** Incluye las 371 pruebas, tres navegadores, compilación, instalación limpia, impresión nativa en PDF, consulta cifrada y actualización desde el instalador 1.0.73.

La impresora física del colegio y un cobro real con Cashea no se prueban en este entorno. Antes de usar con representantes: imprimir un recibo ficticio y revisar el flujo en modo Pruebas. No registrar pagos de prueba en la base real. El paquete es de revisión; no se publicó una versión final.

## Paquete saneado

El ZIP contiene los archivos modificados, diff completo desde `39d9e8d`, diseño, guías y evidencia. No contiene bases del usuario, carpetas de datos, `.env`, almacenes de claves ni ejecutables. Las pruebas y logs usan datos ficticios. El empaquetador comprueba nombres permitidos, patrones de secretos, inventario, hashes y límite de 20 MB. Se verificará también el diff contra la base y la lectura del ZIP antes de entregar.
