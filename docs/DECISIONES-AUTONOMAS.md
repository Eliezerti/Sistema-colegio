# Decisiones autónomas · ingresos y facturas

Trabajo de revisión en `autonomo/ingresos-facturas`. No publicar ni fusionar a main.

## Fase 0 · situación comprobada

- `colegio/db.py:354`: cobros en centavos, moneda original, tasa original, referencia, clave idempotente y aplicaciones a cargos; el comprobante conserva su foto. No cambiar estos importes ni su numeración.
- `colegio/server.py:162`: permisos de escritura centralizados; Consulta no escribe. `server.py:579` bloquea escrituras de copias de consulta antes de despachar rutas.
- `colegio/administration.py`: `cash_summary`, `close_cash`, `reopen_cash` y `ensure_open_day` implementan el cierre diario. El cierre mensual nuevo debe ser adicional, no sustituirlo.
- `colegio/monthly_report.py:16`: informe mensual actual, moneda/método, egresos y morosidad. Su resultado debe seguir idéntico; otros ingresos se mostrarán aparte para no duplicar mensualidades.
- `colegio/documents.py`: PDF propio, fuentes incrustadas y tamaños configurados; `static/app.js:451` permite descargar e imprimir. Los recibos conservan impresión normal y tamaños actuales. La calibración al 100 % es exclusiva de futuras facturas preimpresas.
- `colegio/audit_chain.py:369`: protecciones por tabla generadas dinámicamente; cualquier tabla nueva necesita sus disparadores antes de admitir escrituras.
- `colegio/backup_inspection.py:69`: inspección y comparación recorren todas las tablas. No crear una base lateral que quede fuera de respaldos o restauración.

## Diseño aprobado por autonomía

1. Añadir tablas de cuentas y asociaciones, sin cambiar columnas, valores ni fotos de cobros/egresos existentes. Los históricos quedan sin cuenta hasta una asignación explícita. Cuenta: nombre, banco, moneda y cuatro últimos dígitos; nunca número completo.
2. Depósitos de efectivo separados de los ingresos: vincular cantidades originales de recibos, evitar doble cobertura y exigir motivo para diferencias. Un depósito no vuelve a sumarse como cobro.
3. Categorías y otros ingresos en registros separados. No sumarlos silenciosamente a los informes históricos; un informe ampliado debe distinguir fuentes.
4. Conciliación: movimientos originales inmutables, importación confidencial, deduplicación por archivo y movimiento, vínculos con importes parciales y revisión humana. No convertir usando tasas de hoy. Referencias normalizadas conservando el original.
5. Cierre mensual: transacción y validación del servidor para toda escritura del período; reapertura solo Administración con motivo. No confundir con cierre diario existente.
6. Facturas fuera del motor de recibos. No inventar números preimpresos ni activar impuestos. Solo desplegar una emisión completa si supera pruebas de inmutabilidad, rangos y concurrencia.

## Valores y alternativas

- Mantener las cuentas históricas vacías. Se descarta inferirlas a partir de banco/referencia; una inferencia equivocada falsearía conciliaciones. Revertir una clasificación mediante nueva asignación auditada, nunca reescribiendo el recibo.
- Cero datos de negocio precargados. «Caja efectivo» se configura explícitamente, no como registro semilla; se descarta contaminar instalaciones vacías. El método podrá sugerir la última cuenta compatible sin asignar históricos.
- No conectar bancos ni SENIAT, no calcular IVA/IGTF. Perfil Provincial y formulario real: **NO VERIFICADO**, hasta contrastarlos con documentos del colegio.
- No emitir instalador final. Cualquier borrador requiere cuatro suites y validación nativa real; si no se ejecuta, no se presenta como validado.
- Retener el punto verde de cada fase. Si tras dos arreglos una fase falla, retirarla de la rama y registrar el resultado; no silenciar ni omitir pruebas.

## Migración propuesta

Esquema 13 aditivo; snapshot consistente, integridad, claves foráneas y cadena comprobadas antes de DDL, una transacción con disparadores y versión al final. Prueba sobre fixtures publicados, cierre/reportes idénticos, terminación real del proceso. La reversión posterior requiere la copia previa y conservar por separado cualquier dato nuevo; un ejecutable antiguo debe rechazar el esquema nuevo. No aplicar esta propuesta a una base del usuario durante el desarrollo.
