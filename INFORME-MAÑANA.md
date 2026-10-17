# Informe de la mañana · ingresos y facturas

**Entrega parcial de revisión: núcleo de Fases 1–3 integrado; validación Windows de Fase 3 pendiente. Fase 4 y conversiones entre cuentas/monedas no completadas.**

Rama `autonomo/ingresos-facturas`. Código del núcleo `2d3af092dec8f25bd8442ae859777f4686bbebd5`; los arreglos posteriores afectan pruebas, finales de línea y evidencia de CI. No se fusionó main, no se publicó versión ni etiqueta y no se abrió ni modificó ninguna base del usuario. Solo datos ficticios.

## Resultado por fase

| Fase | Implementado y límites |
|---|---|
| 0 | Inventario y diseño: [decisiones autónomas](docs/DECISIONES-AUTONOMAS.md) y [diseño interno](docs/interno/ingresos-diseno.md). |
| 1 | Cuentas escolares editables, últimos cuatro dígitos, cuenta en cobros/egresos, asignación histórica explícita y atómica, otros ingresos con categorías y soporte textual, depósitos parciales de efectivo sin doble cobertura. Permisos, interfaz, API y bitácora integrados. Los depósitos trasladan saldo; no duplican ingresos. |
| 2 | CSV/XLSX con perfiles editables, vista previa, huella/usuario/fecha, importación idempotente, revisión de posibles duplicados y rechazo de ID bancario conflictivo. Cruce único por ambos lados y vínculos parciales; débitos/egresos y clasificaciones con soporte. Extractos solo Administración. **Pendiente:** vínculos entre cuentas/monedas y depósitos de efectivo convertidos. |
| 3 | Foto mensual conservada, bloqueo del período en servidor, reapertura administrativa con motivo e historia, revisión de pendientes, opciones fiscales informativas y relación CSV con BOM/PDF para contador. Incluye tasas conservadas, monedas y cuentas, diferencias contra el extracto, sin documentos ni fechas de nacimiento de menores. Factura queda vacía porque ese módulo no existe. Linux correcto; Windows final pendiente. |
| 4 | **No implementada:** editor, calibración, lotes, emisión, numeración fiscal confirmada, hojas dañadas, reimpresión y registro de ventas. No se presenta un PDF genérico como sustituto. |

Guías: [cuentas e ingresos](docs/cuentas-ingresos.md), [conciliación](docs/conciliacion-bancaria.md), [Control de ingresos y cierre mensual](docs/control-ingresos-cierre-mensual.md).

## Pruebas reales del código final

| Comando | Linux, entorno recuperado | Windows Server 2022, núcleo final |
|---|---|---|
| `python -m unittest discover -s tests -v` | **352 en 293,531 s; 349 correctas y tres nativas omitidas; salida 0** | Pendiente de comprobar |
| `python tests/run_browser.py` | **Salida 0**, incluidos cuentas, importación, conciliación, cierre mensual y copia de consulta | Pendiente de comprobar |
| `python tests/run_browser.py --demo` | **Salida 0** | Pendiente de comprobar |
| `python tests/run_browser.py --roster` | **Salida 0** | Pendiente de comprobar |

Las tres omisiones Linux son DPAPI, mutex/enfoque de ventanas y restauración nativa con Tk. Son exclusivas de Windows; no se omitieron pruebas para sortear restricciones. Python 3.12.14 y cryptography 50.0.0. Navegador local: Playwright de Node disponible en el entorno y Chromium del sistema; CI instala Playwright 1.58.2 y Node 22.

Validaciones anteriores, sin reutilizarlas como aprobación del núcleo final:

| Punto | Linux | Windows | Evidencia |
|---|---|---|---|
| Fase 1 `ddba0ca` | 333 en 206,436 s, tres nativas omitidas; tres navegadores salida 0 | 333 correctas en 550,777 s, sin omisiones; tres navegadores salida 0 | [39001990044](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39001990044) |
| Fase 2 `e6b40ee` | 343 en 219,629 s, tres nativas omitidas; tres navegadores salida 0 | 343 correctas en 446,056 s, sin omisiones; tres navegadores salida 0 | [39003181236](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39003181236) |
| Fase 3 antes de referencia completa | 351 en 233,656 s, tres nativas omitidas; tres navegadores salida 0; referencia adicional correcta sola | [39004156877](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39004156877) falló; no se recuperaron sus logs | No aprobado |

La repetición anterior de 352 no se pudo recuperar tras reiniciarse el entorno; no se declara aprobada. Se volvió a ejecutar completa y el resultado real es la tabla final de arriba. Registros actuales: `/workspace/work/noche3/final-*.log`. Los registros del entorno anterior desaparecieron; sus resultados ya observados y enlaces CI se conservan en este informe y el historial de la rama.

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
| Windows final | Run inicial fallido sin traceback recuperable: el host del artefacto fue rechazado por política y `gh run view --log` devolvió vacío. Se agrega a los nuevos runs evidencia en anotaciones: salidas, conteo, duración y traceback completo por partes. La causa de aquel run no se inventa. Validaciones nuevas en curso. |

La revisión automática por límite de uso impidió una consulta antes de reiniciarse el entorno; no fue una determinación de riesgo. Al reanudar, volvió a funcionar el mismo mecanismo autorizado y se recuperó la rama enviada. No se eludieron revisión, credenciales ni política de red.

## Rendimiento HTTP

800 alumnos, 12 meses: 9.600 cargos, pagos y movimientos bancarios ficticios. Calentamiento y tres muestras; mediana. Medición local posterior a las suites, sin ejecutarlas en paralelo.

| Entorno / meses | Ruta | Bytes | Mediana, s |
|---|---|---:|---:|
| Linux / 12 | `/api/state` | 7.993 | 0,197489 |
| Linux / 12 | `/api/bank-book` | 86.849 | 0,299858 |
| Linux / 12 | `/api/accounting-report` | 421.083 | 0,157115 |
| Linux / 36 | `/api/state` | 8.000 | 0,450677 |
| Linux / 36 | `/api/bank-book` | 87.086 | 1,002592 |
| Linux / 36 | `/api/accounting-report` | 421.668 | 0,508382 |

Windows: pendiente de registrar. [CSV Linux de 12 meses](docs/interno/ingresos-evidencia/linux-12-meses.csv) y [36 meses](docs/interno/ingresos-evidencia/linux-36-meses.csv) conservan tamaño, mediana y máximo de tres muestras. El escenario de 36 meses tiene 28.800 registros por lado. No se usa una medición de reglas puras para afirmar rendimiento HTTP.

El objetivo principal menor de 1 MB y 1 s se cumple en las mediciones Linux de 12 y 36 meses para la pantalla principal. La revisión bancaria de 36 meses tuvo mediana de 1,003 s; no se afirma que todas las pantallas estén bajo un segundo. No es una garantía para cualquier PC. La ventana de candidatos admite hasta 20.000 por lado; el libro tiene un límite de seguridad de 200.000 registros, escala no validada.

## Decisiones, reversión y riesgos

Todas las decisiones con motivo, alternativa y reversión: [DECISIONES-AUTONOMAS.md](docs/DECISIONES-AUTONOMAS.md). No hay aprobación pendiente.

Las copias previas están en `.aula-migrations/schema-13/`, `schema-14/` y `schema-15/`. Si el cifrado estaba configurado, se exige desbloqueo y se publica una copia cifrada verificada; sin configuración queda SQLite privado local, **no se presenta como cifrado**. No se rota automáticamente. Para volver a 14 usa su copia y el código de Fase 2 en otra carpeta vacía; para 1.0.71 usa la copia 12. Conserva íntegra la carpeta actual y sus operaciones posteriores; no sobrescribas ni borres la base.

Riesgos y pendientes: conversión entre cuentas/monedas sin registro explícito no habilitada; soporte textual, sin adjuntos; mapeo bancario genérico con importe firmado, sin formato oficial Provincial verificado; cada posible duplicado requiere revisión. Reapertura administrativa no sustituye revisión contable.

**NO VERIFICADO:** extracto real de Provincial, formulario real, calibración física, validez fiscal del medio de emisión y revisión con el contador. No hay IVA/IGTF calculados, conexión bancaria ni conexión SENIAT.

## Instalador y pendientes

**No se generó instalador, ni borrador ni final: no hay enlace ni SHA-256 nuevo.** La rama se conserva para revisión del núcleo mientras faltan facturas y conversión. Compilar desde la rama es posible; no se atribuye la ausencia a una obligación de usar main. No se trabajó en firma digital ni certificados.

No se ejecutaron instalación limpia de un EXE nuevo, actualización, otra cuenta de Windows, desinstalación ni impresión física de esta rama. Los tests lógicos y las suites en Windows no sustituyen esas pruebas.

Falta completa la Fase 4: plantillas y versiones, editor visual, perfiles por impresora, calibración, papel y coordenadas, emisión y rangos/números confirmados por operador, inmutabilidad y concurrencia de dos cajeros, anulaciones/hojas dañadas, reimpresión y relación de ventas. No se declara implementada ninguna de esas funciones.

## Pruebas manuales del colegio

1. Piloto separado de producción con datos ficticios; comparar caja, reportes, morosidad y permisos de cada perfil.
2. Revisar mapeo con un extracto real confidencial: signos, centavos, fechas, referencias y solapamientos. No subirlo al repositorio público.
3. Probar una copia externa y restaurarla en otra PC, con archivo + contraseña y archivo + recuperación, sin el almacén de llaves original.
4. Revisar conceptos y validez del medio de emisión con el contador. Cuando exista el módulo completo, calibrar con fotocopias, formulario real e impresora del colegio, antes de usar hojas numeradas.
5. Cuando exista instalador borrador validado, probar instalación/actualización y desinstalación que conserve datos; después, prueba física supervisada de corte de luz durante un cobro. Ninguna se declara realizada.
