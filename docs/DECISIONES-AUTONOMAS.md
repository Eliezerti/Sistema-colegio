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

## Ajuste derivado de la prueba Windows

La prueba real de consulta falló con un cierre TCP (`WinError 10053`) al esperar 403. Se corrige únicamente el transporte del rechazo: drenar con memoria y tiempo acotados antes del 403, sin JSON ni acceso a SQLite. Se descarta ignorar errores de conexión en el test o permitir ejecutar la ruta para después revertirla. Reversión: revertir el commit de este ajuste; no hay esquema ni datos modificados. Las líneas del inventario inicial corresponden al punto de partida `ed1c5e9`.

## Fase 1 · integración posterior comprobada

La decisión previa de conservar reglas aisladas describía el punto verde anterior, no una restricción permanente. Se implementó la Fase 1 en cuatro commits pequeños (`2701023`, `1e003a4`, `11e00dc`, `ddba0ca`). Fases 2–4 siguen pendientes de integración.

| Decisión | Motivo | Alternativa descartada | Cómo revertir |
|---|---|---|---|
| Siete tablas aditivas en esquema 13; conservar columnas y fotos de recibos | Evitar alterar cálculos, correlativos o comprobantes | Reconstruir pagos para añadir metadatos | Copia previa verificada y versión anterior en carpeta vacía separada; conservar carpeta 13 y datos posteriores |
| Respaldo privado previo; cifrado si está configurado, detener si está bloqueado | Actualizar incluso bases que aún no configuraron cifrado, sin exportar una copia como si fuera cifrada | Inventar una contraseña o no respaldar | Configurar cifrado antes de actualizar; conservar copia privada con las mismas protecciones de la carpeta de datos |
| Sin cuenta histórica inferida; revisión masiva con motivo y transacción única | Una referencia no prueba la cuenta destino | Asignar históricos a la primera cuenta del catálogo | Reasignación administrativa auditada; el comprobante original sigue idéntico |
| Otros ingresos solo Administración | El encargo permite a Caja cobros y depósitos; no autoriza configurar o clasificar ingresos ajenos | Ampliar permisos por conveniencia | Cambiar la matriz de permisos y añadir pruebas explícitas antes de ampliar |
| Depósitos como traslado y diferencia explicada, no ingreso duplicado | Conservar totales y reflejar efectivo físico | Sumarlos a ingresos por segunda vez o inventar un egreso por diferencia | Anulación administrativa con motivo; nunca borrar registro o vínculo |
| Bloquear limpieza excepcional antigua ante registros del libro nuevo | Esa herramienta no está diseñada para retirar nuevas clasificaciones y depósitos | Extender un borrado fuera de este alcance | Diseñar y probar una herramienta específica antes de permitir otra operación |

Reversión detallada y límites en `cuentas-ingresos.md`. La copia del esquema 12 procede del código publicado 1.0.71, no de cambiar un número de PRAGMA. Su manifiesto y SHA-256 verifican el fixture ficticio; se prueban contraseña y recuperación, comparación exacta y cinco terminaciones reales.

La revisión automática rechazó una primera propuesta porque podía aceptar cualquier esquema futuro al saltar la migración antigua. No se ejecutó esa edición. Se sustituyó por aceptar **únicamente el esquema 13 conocido**; cualquier versión mayor sigue rechazada por ambos límites. La revisión autorizó esta alternativa. Las pruebas de consulta ante bitácora dañada conservan la disponibilidad de lectura y todos los bloqueos de escritura.

## Conciliación persistente · esquema 14

| Decisión | Motivo | Alternativa descartada | Cómo revertir |
|---|---|---|---|
| Perfiles editables y plantilla Provincial NO VERIFICADA | No existe un extracto real autorizado para contrastar | Presentar un mapeo inventado como oficial | Editar y guardar el perfil; cada importación conserva su versión del mapeo |
| Archivo idéntico idempotente; ID bancario repetido solo se omite con contenido igual | Evitar duplicados sin ocultar correcciones bancarias | Saltar cualquier ID repetido aunque cambie el importe | Revisión externa de conflictos; no sobrescribir movimientos importados |
| Sin ID, coincidencias de contenido requieren filas confirmadas y motivo | Dos transferencias legítimas pueden parecer iguales | Descartar o importar automáticamente el solapamiento | Revisar el archivo antes de confirmar; retirar vínculos no borra el original |
| Cruce único en ambos lados, referencia no vacía, centavos exactos y ±3 días | Aplicar el valor seguro del encargo | Elegir el primer candidato o cruzar por importe solo | Retirar el vínculo con motivo y revisar; se conserva historia |
| Vínculos parciales de misma cuenta y moneda; conversiones pendientes | No existe aún registro explícito de cambio entre cuentas/monedas | Usar una tasa actual o suponer que dos cuentas son la misma | Implementar operación cambiaria con tasa y fecha verificadas antes de habilitarla |
| Datos del extracto solo Administración y huellas en bitácora | Confidencialidad sin retirar trazabilidad ni A5 | Copiar descripciones/referencias bancarias al registro de auditoría | Ampliar informes solo con permiso y prueba de privacidad; mantener originales confidenciales |
| Migración 14 aditiva, snapshot previo 13 y conservación del punto verde 13 | Evitar tablas laterales fuera de respaldo/restauración | Guardar el banco en otro archivo no protegido | Copia previa 13 en otra carpeta con código Fase 1; para 1.0.71 usar copia 12 de la primera ampliación |

El banco no se conecta por red. Cada importación conserva huella, usuario, fecha y mapeo. Los nuevos datos del extracto se incluyen en respaldos/restauración; la ampliación no modifica cobros ni fotos de recibos. Guía operativa y límites: `conciliacion-bancaria.md`.

## Fase 3 · integración y validación posterior

Los estados previos de este archivo describen puntos históricos, no restricciones para continuar. Se integró el cierre mensual en `52ac0f4`, `efd2b9f`, `784cc86` y `2d3af09`; la aprobación de sus pruebas finales se registra en ESTADO-NOCHE.md.

| Decisión | Motivo | Alternativa descartada | Cómo revertir |
|---|---|---|---|
| Esquema 15 aditivo y foto mensual conservada | Mantener historia y permitir reabrir sin borrar cierres | Cambiar los cobros para representar un cierre | Copia previa 14 y código de Fase 2 en otra carpeta; conservar íntegra la carpeta 15 y sus operaciones posteriores |
| Guardia mensual central en servidor y cobro directo | Bloquear también peticiones que eviten la interfaz; permitir solo el reintento ya confirmado | Ocultar botones como única protección | Reapertura administrativa con motivo; no retirar el guardia ni editar un cierre a mano |
| Opciones fiscales informativas por ingreso | El encargo prohíbe calcular IVA/IGTF | Inferir impuestos o tratar un recibo como factura | Desmarcar antes del cierre, o reabrir con motivo para corregir; nunca alterar el comprobante original |
| Tasas conservadas; equivalencia faltante NO VERIFICADA | La tasa 1 de un pago USD no es BCV | Usar la tasa de hoy en el historial | Registrar la operación correcta con soporte antes del cierre; no inventar equivalencias ni cambiar fotos cerradas |
| Candidatos acotados al mes, con vecinos para comprobar competencia | Evitar que el historial de varios años bloquee la revisión o que se cruce otro mes sin revisarlo | Conciliar toda la historia al pulsar el botón del mes actual | Elegir otro mes; los vínculos se retiran con motivo y conservan historia |
| Congelar datetime solo dentro de la prueba de referencia | Un import tardío retenía un Mock de local_today y contaminaba otra prueba | Relajar la prohibición de movimientos futuros | Revertir el arreglo solo si se conserva otra prueba equivalente de aislamiento; no modificar la regla del producto |
| LF obligatorio en el JSON de referencia | Un checkout con autocrlf cambia los bytes y rompe la huella | Ignorar la huella o normalizar cualquier cambio antes de verificar | Regenerar una referencia independiente y su manifiesto con procedencia; no aceptar cambios sin explicación |
| Evidencia CI adicional en anotaciones | El host del artefacto del fallo no está autorizado y los logs no se recuperaron | Eludir el proxy o inventar cuál suite falló | Conservar artefactos y leer las anotaciones de cada nueva ejecución por la API permitida |
| Mantener Fase 4 sin iniciar y sin instalador | Priorizar el núcleo probado; no entregar un emisor fiscal incompleto | Presentar un PDF genérico como editor y emisión terminados | Implementar el bloque completo con migración y pruebas propias; no hay aprobación pendiente |

La reversión 15→14 requiere la copia en `.aula-migrations/schema-15/` y el código de Fase 2, en una carpeta vacía separada. Para regresar a 1.0.71 se usa la copia 12 de `schema-13/`. No abrir un esquema mayor con un ejecutable antiguo ni sobrescribir la carpeta actual. Si había cifrado configurado, la copia previa se cifra y verifica; si estaba bloqueado, no migra. Sin cifrado configurado queda copia SQLite privada, que no se presenta como respaldo cifrado externo.

La plantilla Provincial, el formulario real, la calibración y la revisión fiscal siguen NO VERIFICADOS. La falta de medidas no se usa como supuesto bloqueo técnico: el encargo permite una versión genérica, pero ese bloque aún no fue implementado. Compilar desde la rama es posible; no se alega que deba hacerse desde main.

## Efectivo y pendientes bancarios

Se excluyen otros ingresos de Caja efectivo del libro de conciliación bancaria, igual que los cobros en efectivo. Motivo: no existe extracto bancario de una caja física y el pendiente era imposible de resolver. Alternativa descartada: ocultarlo solo en pantalla o clasificarlo ficticiamente. Reversión funcional: no hace falta borrar ni migrar datos; el ingreso sigue en caja y en la relación mensual, con su cuenta original. Para depositar efectivo procedente de otros ingresos hará falta ampliar el traslado con cobertura explícita; no se inventa un recibo de mensualidad.
