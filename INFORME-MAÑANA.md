# Informe de la mañana · ingresos y facturas

**Rama de revisión: Fases 1–4 integradas. Fase 4 correcta en Linux; validación final Windows e instalador BORRADOR pendientes de terminar. Conversiones entre cuentas/monedas aún pendientes.**

Rama `autonomo/ingresos-facturas`. Código integrado inicialmente en `2d3af092dec8f25bd8442ae859777f4686bbebd5`; ajustes finales de efectivo `cb34ad7` y cifrado previo `a772d25`. Ese último commit pasó las cuatro suites en ambos sistemas; es el punto verde del núcleo. No se fusionó main, no se publicó versión ni etiqueta y no se abrió ni modificó ninguna base del usuario. Solo datos ficticios.

## Resultado por fase

| Fase | Implementado y límites |
|---|---|
| 0 | Inventario y diseño: [decisiones autónomas](docs/DECISIONES-AUTONOMAS.md) y [diseño interno](docs/interno/ingresos-diseno.md). |
| 1 | Cuentas escolares editables, últimos cuatro dígitos, cuenta en cobros/egresos, asignación histórica explícita y atómica, otros ingresos con categorías y soporte textual, depósitos parciales de efectivo sin doble cobertura. Permisos, interfaz, API y bitácora integrados. Los depósitos trasladan saldo; no duplican ingresos. |
| 2 | CSV/XLSX con perfiles editables, vista previa, huella/usuario/fecha, importación idempotente, revisión de posibles duplicados y rechazo de ID bancario conflictivo. Cruce único por ambos lados y vínculos parciales; débitos/egresos y clasificaciones con soporte. Extractos solo Administración. **Pendiente:** vínculos entre cuentas/monedas y depósitos de efectivo convertidos. |
| 3 | Foto mensual conservada, bloqueo del período en servidor, reapertura administrativa con motivo e historia, revisión de pendientes, opciones fiscales informativas y relación CSV con BOM/PDF para contador. Incluye tasas conservadas, monedas y cuentas, diferencias contra el extracto, sin documentos ni fechas de nacimiento de menores. Factura asociada incorporada en Fase 4, sin duplicar el ingreso. Cuatro suites correctas en Linux y Windows con los últimos ajustes. |
| 4 | Editor visual en mm, fondo PNG solo para calibración, perfiles, versiones y JSON; lotes con prefijos/ceros, confirmación de números, hojas dañadas, anulación, inmutabilidad y reimpresión del mismo PDF. Relación de ventas CSV/PDF y factura asociada en ingresos. Esquema 16 aditivo. Correcta en Linux; Windows en validación. |

Guías: [cuentas e ingresos](docs/cuentas-ingresos.md), [conciliación](docs/conciliacion-bancaria.md), [Control de ingresos y cierre mensual](docs/control-ingresos-cierre-mensual.md).

## Fase 4 · validación final real

Código de emisión `6ca60e3`, prefijos/validación `f1c4bb0`, interfaz `ea7301e`; todo en la rama de revisión, sin usar bases reales.

| Comando | Linux | Windows del código nuevo |
|---|---|---|
| `python -m unittest discover -s tests -v` | **379 en 408,506 s: 376 correctas, tres exclusivas de Windows omitidas; salida 0** | Pendiente de terminar |
| `python tests/run_browser.py` | **Salida 0**; editor, arrastre/flechas, calibración sin número, emisión/reimpresión idéntica y recuperación de sesión sin mezclar usuarios | Pendiente de terminar |
| `python tests/run_browser.py --demo` | **Salida 0** | Pendiente de terminar |
| `python tests/run_browser.py --roster` | **Salida 0** | Pendiente de terminar |

Registros completos: `/workspace/work/noche4/final-*.log`, con códigos de salida separados. `tests/verify_invoice_pdfs.py`: **dos correctas en 0,100 s**, usando pypdf y PyMuPDF; una página, 396×612 puntos, márgenes/cuadros de texto, ñ/tildes/cursiva, perfil desplazado y carta arriba/abajo con giro a tamaño real. `tests/verify_review_build.py`: **dos correctas en 0,005 s**, selección de carpeta separada antes de iniciar escritorio y rechazo sin LOCALAPPDATA. No es impresión física.

Migración 15→16: fixture publicado 1.0.71 atravesando 13/14/15, respaldo cifrado previo comprobado con contraseña/recuperación y cinco terminaciones reales. Filas de negocio, recibos y prefijo de bitácora conservados; la cabecera avanza exactamente una entrada. Tablas nuevas vacías en instalación nueva. Permisos/CSRF por HTTP, meses cerrados, concurrencia real de dos cajeros, inmutabilidad, rangos/prefijos/ceros/duplicados/saltos/agotamiento, hojas dañadas, anulación, portable sin almacén original, consulta y rechazo de PDF alterado. Los números conocidos se conservan al restaurar, incluso tras dos restauraciones antiguas.

Primer pase completo: **379 en 343,004 s, un fallo, tres omisiones**; una petición vacía podía guardar un perfil por defecto. Primer arreglo: rechazar el perfil ausente/vacío en servidor. La matriz dirigida pasó y el segundo pase completo es el resultado verde de arriba. No se omitieron pruebas ni se relajaron permisos. Otros fallos iniciales de la fase: cuadro de fuente, comparación de cabecera auditada, orden del registro y fixtures sintéticos antiguos; corregidos y repetidos, sin modificar fixtures publicados. El test de exportación portable pasó a crear snapshot consistente antes de cifrar: se conserva el rechazo a WAL activo. El primer navegador falló por URL relativa en su cliente de pruebas; corregido y repetido completo.

Con **800 alumnos, 12 meses, 9.600 cobros/movimientos/facturas con PDF ficticio**, HTTP Linux: principal **7.993 bytes**, mediana **0,331963 s**, máximo **0,448516 s**; conciliación 86.849 bytes / 0,344910 s; relación mensual 425.987 bytes / 0,177546 s; registro de facturas 49.222 bytes / 0,119056 s. Es una carga temporal sintética, no velocidad de emisión ni extracto real. El generador de esta medición tuvo dos errores de preparación (paréntesis e importación), corregidos; ejecución posterior salida 0. No se usa un resultado fallido como medición.

Guía nueva: [facturas preimpresas y calibración](docs/facturas-preimpresas.md). Ejemplo **SIN CALIBRAR**, formulario real/calibración física/validez fiscal **NO VERIFICADOS**. IVA e IGTF no calculados ni activables en este borrador; etiquetas editables. No se inventan tasas históricas ni números preimpresos.

## Pruebas del punto verde anterior · núcleo Fases 1–3

| Comando | Linux, entorno recuperado | Windows Server 2022, últimos ajustes |
|---|---|---|
| `python -m unittest discover -s tests -v` | **355 en 309,459 s; 352 correctas y tres nativas omitidas; salida 0** | **355 correctas en 666,551 s, sin omisiones; salida 0** |
| `python tests/run_browser.py` | **Salida 0**, incluidos cuentas, importación, conciliación, cierre mensual y copia de consulta | **Salida 0** |
| `python tests/run_browser.py --demo` | **Salida 0** | **Salida 0** |
| `python tests/run_browser.py --roster` | **Salida 0** | **Salida 0** |

Las tres omisiones Linux son DPAPI, mutex/enfoque de ventanas y restauración nativa con Tk. Son exclusivas de Windows; no se omitieron pruebas para sortear restricciones. Python 3.12.14 y cryptography 50.0.0. Navegador local: Playwright de Node disponible en el entorno y Chromium del sistema; CI instala Playwright 1.58.2 y Node 22.

Validaciones anteriores, sin reutilizarlas como aprobación del núcleo final:

| Punto | Linux | Windows | Evidencia |
|---|---|---|---|
| Fase 1 `ddba0ca` | 333 en 206,436 s, tres nativas omitidas; tres navegadores salida 0 | 333 correctas en 550,777 s, sin omisiones; tres navegadores salida 0 | [39001990044](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39001990044) |
| Fase 2 `e6b40ee` | 343 en 219,629 s, tres nativas omitidas; tres navegadores salida 0 | 343 correctas en 446,056 s, sin omisiones; tres navegadores salida 0 | [39003181236](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39003181236) |
| Fase 3 antes de referencia completa | 351 en 233,656 s, tres nativas omitidas; tres navegadores salida 0; referencia adicional correcta sola | [39004156877](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39004156877) falló; no se recuperaron sus logs | No aprobado |

La repetición anterior de 352 no se pudo recuperar tras reiniciarse el entorno; no se declara aprobada. Se volvió a ejecutar completa y el resultado real es la tabla final de arriba. [Resumen conservado de las cuatro suites Linux](docs/interno/ingresos-evidencia/linux-cuatro-suites.json). Registros finales actuales: `/workspace/work/noche3/final355-*.log`. Los registros del entorno anterior desaparecieron; sus resultados ya observados y enlaces CI se conservan en este informe y el historial de la rama.

Windows `c276966`: **352 correctas en 668,336 s, sin omisiones; normal/demo/roster salida 0**, [run 39027327681](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39027327681), [evidencia de anotaciones](docs/interno/ingresos-evidencia/windows-c276.json). Este punto precede al ajuste de efectivo y a la comprobación previa de cifrado; no se reutiliza como aprobación final.

Linux final de `a772d25`: las cuatro suites correctas, con terminación real observada de cada comando; no se omiten pruebas para sortear restricciones. Se amplió la cobertura: recuperación del cierre conciliado sin almacén original (contraseña y recuperación); exclusión de otros ingresos en efectivo de pendientes bancarios; rechazo de las tres migraciones antes de copiar si el cifrado está bloqueado. La suite final ejecutó **355 correctas en Windows en 666,551 s, sin omisiones, y normal/demo/roster salida 0**, en [39028897879](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39028897879).

[Evidencia Windows final](docs/interno/ingresos-evidencia/windows-final.json), publicada por CI sin depender de la descarga del artefacto.

## Cobertura y referencia independiente

- Fixture ficticio producido por el código publicado de 1.0.71, commit `cfbad62338849cd2089de6fd58c1c43ee115f772`, con manifiesto y huella comprobados. La referencia de totales se generó ejecutando esas fuentes, no la implementación nueva. Cinco fuentes se contrastaron byte por byte con ese commit.
- Igualdad exacta de caja, resumen/morosidad, informe diario y mensual frente a esa referencia tras todas las migraciones. Recibos, aplicaciones, cargos, egresos y prefijo de la cadena conservados.
- Transiciones 12→13→14→15 aditivas: respaldo previo verificado, contraseña y recuperación, cinco terminaciones reales por transición, integridad SQLite, claves foráneas y cadena al reiniciar. No se borran ni reconstruyen tablas existentes.
- Instalación lógica en cero: tablas de negocio y las catorce nuevas vacías, sin usuarios por defecto, identidad genérica, pisos en cero y cadena limpia. No equivale a instalar un EXE de esta rama.
- Permisos HTTP/CSRF, Consulta sin escrituras, privacidad del extracto, idempotencia, cobertura parcial y dos peticiones concurrentes de depósito, conflictos/duplicados, CSV/Excel corruptos, ceros, ambigüedad y tolerancia de fecha.
- Bloqueos de cobros, anulaciones, asignaciones, ingresos, depósitos e importación/conciliación del mes cerrado. Reintento confirmado sin nuevo recibo. Reapertura motivada y opciones informativas sin modificar cálculos.
- CSV con BOM, PDF real descargado, ñ/tildes, informe sin identificaciones de menores, restauración cifrada con vínculos, Probar respaldo, Verificar datos y consulta de copia conservados por las suites.

## Fallos encontrados y arreglos

| Bloque | Resultado real y actuación |
|---|---|
| Línea base antigua | Sockets restringidos: se repitió con el mecanismo autorizado; no se omitieron pruebas. |
| Fase 1 | Primera completa: 331 en 213,631 s, 15 errores y tres omisiones. Fixtures antiguos y lectura con cabecera de bitácora dañada corregidos; escritura sigue bloqueada. Dirigidas y cuatro suites posteriores correctas. Roster se actualizó para elegir la cuenta requerida. |
| Fase 2 | Primer dirigido: referencia ficticia repetida sin confirmar; se usó la confirmación vigente. Primera completa: 343 en 219,262 s, un fallo de contrato: el cruce válido vacío devuelve 200 y cero vínculos. Contrato corregido, 12 dirigidas y completa correctas. Primer navegador: selector ambiguo; se usó el diálogo correcto. |
| Fase 3 local | Contraseña errónea del fixture corregida. El rechazo 400 deliberado de mes cerrado se cuenta exactamente en la prueba de navegador; otros errores siguen fallando la suite. |
| Reanudación | Ocho dirigidas: una falló porque una importación tardía retenía el Mock de fecha de la referencia. Primer arreglo: congelar datetime solo durante esa prueba, sin cambiar la función real ni relajar fechas futuras. Ocho correctas en 9,207 s y completa 352 correcta. |
| Portabilidad | Checkout equivalente a Windows con autocrlf produjo 124 CRLF y otra huella. Se fija ese JSON a LF: cero CRLF y huella original idéntica. No se normaliza ni omite la comprobación. |
| Windows inicial | Run inicial fallido sin traceback recuperable: el host del artefacto fue rechazado por política y `gh run view --log` devolvió vacío. Se agrega a los nuevos runs evidencia en anotaciones: salidas, conteo, duración y traceback completo por partes. La causa de aquel run no se inventa. La repetición [39027076426](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39027076426) sí publicó diagnóstico: 352 en 596,378 s, un fallo de huella del JSON (CRLF), sin omisiones; normal/demo/roster salida 0. [Traceback y resultados de las anotaciones](docs/interno/ingresos-evidencia/windows-primer-arreglo.json). Coincide exactamente con la reproducción de portabilidad; el run con LF fijado terminó correcto, como se registra arriba. La causa del run inicial no se infiere de esta repetición. |

La revisión automática por límite de uso impidió una consulta antes de reiniciarse el entorno; no fue una determinación de riesgo. Al reanudar, volvió a funcionar el mismo mecanismo autorizado y se recuperó la rama enviada. No se eludieron revisión, credenciales ni política de red.

Dos hallazgos finales reproducidos y corregidos al primer intento: otros ingresos en efectivo aparecían entre pendientes bancarios (1 falla; después 7 dirigidas correctas en 13,114 s); un almacén inaccesible detenía las migraciones después de crear una copia privada (tres subcasos negativos fallidos; después 7 pruebas de migración correctas en 8,682 s). La corrección adelanta el rechazo antes de crear la carpeta o copia y no elimina archivos existentes.

Las repeticiones intermedias de 353 (332,730 s) y 354 (316,790 s) terminaron correctas, con tres nativas omitidas y los tres navegadores correctos. Empezaron antes de completar los últimos ajustes; no se usan como aprobación final. Las dos ejecuciones Windows que solo estaban en cola se sustituyeron antes de ejecutar pruebas; ninguna suite en marcha se canceló. Las nuevas validaciones usan máquinas independientes por commit.

## Rendimiento HTTP

800 alumnos, 12 meses: 9.600 cargos, pagos y movimientos bancarios ficticios. Calentamiento y tres muestras; mediana. Medición local posterior a las suites, sin ejecutarlas en paralelo.

| Entorno / meses | Ruta | Bytes | Mediana, s |
|---|---|---:|---:|
| Linux / 12 | `/api/state` | 7.993 | 0,185610 |
| Linux / 12 | `/api/bank-book` | 86.849 | 0,264491 |
| Linux / 12 | `/api/accounting-report` | 421.083 | 0,141985 |
| Linux / 36 | `/api/state` | 8.000 | 0,442593 |
| Linux / 36 | `/api/bank-book` | 87.086 | 0,866808 |
| Linux / 36 | `/api/accounting-report` | 421.668 | 0,380038 |

Windows final / 12 meses: state **8.093 bytes y 0,394435 s**, banco 86.849 y 0,299684 s; informe 421.083 y 0,145015 s. [CSV Windows](docs/interno/ingresos-evidencia/windows-12-meses.csv). Windows / 36 meses: no ejecutado. [CSV Linux de 12 meses](docs/interno/ingresos-evidencia/linux-12-meses.csv) y [36 meses](docs/interno/ingresos-evidencia/linux-36-meses.csv) conservan tamaño, mediana y máximo de tres muestras. El escenario de 36 meses tiene 28.800 registros por lado. No se usa una medición de reglas puras para afirmar rendimiento HTTP.

El objetivo principal menor de 1 MB y 1 s se cumple en las mediciones Linux de 12 y 36 meses para la pantalla principal. La revisión bancaria de 36 meses tuvo mediana de 0,867 s en la repetición final y 1,003 s en una anterior; la variación no se oculta. No es una garantía para cualquier PC. La ventana de candidatos admite hasta 20.000 por lado; el libro tiene un límite de seguridad de 200.000 registros, escala no validada.

## Decisiones, reversión y riesgos

Todas las decisiones con motivo, alternativa y reversión: [DECISIONES-AUTONOMAS.md](docs/DECISIONES-AUTONOMAS.md). No hay aprobación pendiente.

Las copias previas están en `.aula-migrations/schema-13/`, `schema-14/` y `schema-15/`. Si el cifrado estaba configurado, se exige desbloqueo y se publica una copia cifrada verificada; sin configuración queda SQLite privado local, **no se presenta como cifrado**. No se rota automáticamente. Para volver a 14 usa su copia y el código de Fase 2 en otra carpeta vacía; para 1.0.71 usa la copia 12. Conserva íntegra la carpeta actual y sus operaciones posteriores; no sobrescribas ni borres la base.

Riesgos y pendientes: conversión entre cuentas/monedas y traslado de efectivo de otros ingresos no habilitados; soporte textual, sin adjuntos; mapeo bancario genérico con importe firmado, sin formato oficial Provincial verificado; cada posible duplicado requiere revisión. Reapertura administrativa no sustituye revisión contable.

**NO VERIFICADO:** extracto real de Provincial, formulario real, calibración física, validez fiscal del medio de emisión y revisión con el contador. No hay IVA/IGTF calculados, conexión bancaria ni conexión SENIAT.

## Instalador y pendientes

**BORRADOR preparado para compilar desde esta rama, condicionado a Windows correcto. Todavía no existe EXE validado ni SHA-256 para entregar.** Instala programa y accesos separados; el punto de entrada usa `%LOCALAPPDATA%\AulaRevisionIngresos\AulaColegio`, incluso al abrir directamente el EXE. No reemplaza ni actualiza la versión publicada. Cierra Aula publicado antes de abrirlo, porque comparten mutex y puertos. No habilita inicio automático. No se trabajó en firma digital ni certificados.

El ZIP de fuentes fue verificado en scratch (integridad, fixtures publicados y referencia con huellas idénticas, documentación y ausencia de base de negocio/respaldos). No es un instalador ni una publicación; no se incluye un enlace a un archivo temporal.

No se ejecutaron instalación limpia de un EXE nuevo, actualización, otra cuenta de Windows, desinstalación ni impresión física de esta rama. Los tests lógicos y las suites en Windows no sustituyen esas pruebas.

Fase 4 tiene [diseño y límites](docs/interno/facturas-diseno.md) y las funciones descritas arriba. Falta terminar Windows y el instalador, además de la comprobación física/fiscal. No confundir el PDF verificado con papel físicamente calibrado. Una copia ajena no conoce facturas posteriores que nunca recibió: revisar también las hojas físicas antes de emitir tras restaurar.

## Pruebas manuales del colegio

1. Piloto separado de producción con datos ficticios; comparar caja, reportes, morosidad y permisos de cada perfil.
2. Revisar mapeo con un extracto real confidencial: signos, centavos, fechas, referencias y solapamientos. No subirlo al repositorio público.
3. Probar una copia externa y restaurarla en otra PC, con archivo + contraseña y archivo + recuperación, sin el almacén de llaves original.
4. Revisar conceptos y validez del medio de emisión con el contador. Calibrar con fotocopias, formulario real e impresora del colegio, antes de usar hojas numeradas, siguiendo la guía.
5. Cuando exista instalador borrador validado, probar instalación/actualización y desinstalación que conserve datos; después, prueba física supervisada de corte de luz durante un cobro. Ninguna se declara realizada.
