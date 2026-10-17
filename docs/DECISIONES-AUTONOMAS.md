# Decisiones autónomas · ingresos y facturas

Trabajo de revisión en `autonomo/ingresos-facturas`. No publicar ni fusionar a main.

## Fase 0 · situación comprobada

- `colegio/db.py:354`: cobros en centavos, moneda original, tasa original, referencia, clave idempotente y aplicaciones a cargos; el comprobante conserva su foto. No cambiar estos importes ni su numeración.
- `colegio/server.py:162`: permisos de escritura centralizados; Consulta no escribe. `server.py:579` bloquea escrituras de copias de consulta antes de despachar rutas.
- `colegio/administration.py:342–388`: `ensure_open_day`, `cash_summary`, `close_cash` y `reopen_cash` implementan el cierre diario. El cierre mensual nuevo debe ser adicional, no sustituirlo.
- `colegio/monthly_report.py:16`: informe mensual actual, moneda/método, egresos y morosidad. Su resultado debe seguir idéntico; otros ingresos se mostrarán aparte para no duplicar mensualidades.
- `colegio/documents.py:82,212,451,768`: PDF propio, fuentes incrustadas y tamaños configurados; `static/app.js:451` permite descargar e imprimir. Los recibos conservan impresión normal y tamaños actuales. La calibración al 100 % es exclusiva de futuras facturas preimpresas.
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

## Registro de decisiones de esta ejecución

| Decisión | Motivo | Alternativa descartada | Cómo revertir |
|---|---|---|---|
| Mantener las reglas fuera de las rutas y del escritorio | La integración y la migración nuevas todavía no tienen prueba completa | Mostrar botones que aparenten conciliar o cerrar sin persistencia garantizada | Integrarlas en una fase posterior con permisos, transacciones, respaldos y pruebas; no hay datos que revertir ahora |
| CSV y primera hoja XLSX con mapeo explícito | No existe extracto real de referencia | Suponer el formato de Provincial o adivinar separadores de miles | Ampliar perfiles versionados tras comprobar un extracto real; conservar el archivo original fuera del repositorio |
| Posibles duplicados sin ID bancario se señalan y conservan en vista previa | Dos transferencias legítimas pueden tener contenido idéntico | Descartar ingresos por una huella de contenido repetida | Cambiar la política solo con un identificador bancario verificado y pruebas de importación entre archivos |
| Unicidad en ambos lados; máximo 50 candidatos visibles con cantidad total | Evitar cruces ajenos y expansión excesiva de grupos ambiguos | Elegir el primer recibo por orden de consulta | Revisión explícita; el original no se altera y no existe conciliación guardada que deshacer |
| Referencias e ID bancarios de Excel deben ser texto | Los ceros eliminados por Excel no se pueden recuperar | Rellenar ceros inventando la longitud del banco | Aceptar otras representaciones solo con perfil real verificado y advertencia; nunca inventar el original |
| Validación Windows sin instalador | Verificar regresiones sin entregar funciones incompletas como una versión nueva | Compilar el mismo número de versión con un módulo no integrado y llamarlo entrega | Añadir compilación BORRADOR cuando el bloque operativo y sus pruebas estén completos |
| Fases 1–4 marcadas pendientes | Solo se terminó y probó el núcleo aislado de esta ejecución | Declarar las fases completas basándose en pruebas de reglas puras | Continuar desde ESTADO-NOCHE.md; no asumir una migración ni funcionalidades que no existen |

Los valores seguros del encargo para cierre, impuestos, plantillas y numeración fiscal quedan en el diseño: no son configuraciones nuevas activadas en la aplicación. No se habilitaron IVA, IGTF, acceso a bancos ni emisión fiscal.

El primer envío al remoto fue rechazado por revisión automática por falta de titularidad acreditada. Se comprobó en lectura que `origin` pertenece a la cuenta autenticada y tiene permisos de administración; el repositorio es público. Tras esa comprobación, la revisión autorizó el envío de código genérico y pruebas ficticias. No se publicaron extractos ni datos del colegio. El rechazo no se eludió por otro canal.
