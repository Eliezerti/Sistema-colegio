# Informe de la mañana · ingresos y facturas

**Entrega parcial de revisión. Las Fases 1–4 NO están completas ni habilitadas en Aula.**
Rama: `autonomo/ingresos-facturas`. Punto de partida: `ed1c5e9`, Aula 1.0.71. Main, etiquetas y versión publicada intactas. Ninguna base del usuario fue abierta, limpiada o migrada.

## Qué se hizo

| Bloque | Resultado real |
|---|---|
| Fase 0 | Inventario y diseño documentados; decisiones y reversión en `docs/DECISIONES-AUTONOMAS.md`; diseño de tablas, migración y permisos en `docs/interno/ingresos-diseno.md`. Commit `427e381`, ampliado en los siguientes. |
| Fase 1 | Reglas aisladas de catálogo mínimo, cuenta sugerida y depósitos de efectivo con cobertura parcial y diferencias. No hay catálogo persistente, cuenta en el formulario, asignación masiva, otros ingresos ni rutas nuevas. **Pendiente de integración.** |
| Fase 2 | Vista previa genérica CSV/XLSX, huella del archivo, posibles duplicados, referencias originales y normalizadas; propuestas únicas por ambos lados y validación de vínculos parciales. No hay importación persistida, conciliación operativa ni deduplicación entre archivos. **Pendiente de integración.** |
| Fase 3 | Diseño de cierre protegido y relación para contador. No hay cierre mensual nuevo ni relación ampliada. Los reportes y cierres actuales no cambian. **Pendiente.** |
| Fase 4 | Solo diseño, sin editor, emisión, lotes, numeración fiscal ni PDF nuevo. **Pendiente.** |

Los commits `a311cfc`, `27241fc` y `f2c468c` contienen las reglas y sus pruebas. El commit `6f19357` corrige además un fallo de transporte del rechazo HTTP observado en la validación real de Windows, sin habilitar escrituras ni abrir SQLite. El módulo nuevo no se importa desde el servidor, escritorio ni interfaz. No se declara ningún flujo financiero nuevo como disponible.

## Pruebas reales

Validación final terminada en Linux y Windows para el código `6f19357`. Los commits posteriores solo actualizan documentación; esto no convierte en completas las fases pendientes.

- Línea base con restricción: 307 pruebas en 67,595 s; 118 errores de socket y 3 omisiones nativas. Falló por `PermissionError: [Errno 1] Operation not permitted` al crear el servidor local.
- Se utilizó el mecanismo de permisos autorizado; prueba administrativa: 1 correcta en 1,012 s. Sin modificar ni omitir pruebas para evitar el bloqueo.
- Línea base autorizada: 307 en 180,169 s; 304 correctas y 3 nativas omitidas en Linux. Navegador normal, `--demo` y `--roster`: salida 0.
- Primera regresión ampliada: 321 en 179,995 s; 318 correctas y 3 nativas omitidas. Tres navegadores: salida 0.
- Núcleo final aislado: 17 correctas en 0,326 s. Incluye oráculo independiente con 40 conjuntos de movimientos, cobertura parcial, ambigüedad por ambos lados, duplicados, ceros, tasas/redondeos, importaciones corruptas, fórmulas, vínculos externos y expansión de texto compartido Excel.
- Regresión Linux del código final `f2c468c`: 324 en 173,620 s; 321 correctas y 3 nativas omitidas.
- Windows inicial ([38996806129](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38996806129)): 324 en 482,260 s, 1 error de conexión `WinError 10053` al esperar 403 en `import-roster` de una copia de consulta. Las tres suites de navegador pasaron; salidas `1/0/0/0`. No se declaró aprobado.
- Primer arreglo `6f19357`: descarte del cuerpo rechazado, memoria acotada y plazo total 2 s; sin JSON ni conexión SQLite. Prueba dirigida: 4 correctas en 9,361 s, incluidos cuerpo grande y emisores incompletos/lentos. No se omitieron pruebas.
- Linux del arreglo: 325 en 188,147 s; 322 correctas y 3 exclusivas de Windows omitidas. Navegador normal, demo y roster: salida 0.
- Windows del primer arreglo, código `6f19357`: **325 correctas en 438,560 s, sin omisiones**. Navegador normal, `--demo` y `--roster`: salida 0; resumen de salidas `0/0/0/0`. [Ejecución 38997949165](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38997949165) · [Registros completos](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38997949165/artifacts/12087338899). No se reutiliza la validación antigua de 1.0.71 como prueba de esta rama.

Las tres omisiones Linux son DPAPI, mutex/enfoque de ventanas Windows y revisión nativa de restauración con Tk. No se omiten por motivos funcionales.

### Rendimiento del núcleo aislado

Linux, Python 3.12.14; una ejecución por escenario. 800 alumnos × 12 meses, 9.600 registros en cada lado:

| Escenario | Tiempo | Propuestas únicas |
|---|---:|---:|
| Referencias únicas | 0,067575 s | 9.600 |
| Referencias repetidas por mes | 0,065099 s | 0 |

En grupos ambiguos se entregan hasta 50 candidatos y su cantidad real. **Esto no mide HTTP, base de datos, interfaz ni Windows**, ni demuestra el rendimiento final de la conciliación integrada.

### Resumen final de las cuatro suites

| Comando | Linux | Windows Server 2022 |
|---|---|---|
| `python -m unittest discover -s tests -v` | 325 en 188,147 s; 322 correctas y 3 nativas omitidas | 325 correctas en 438,560 s; sin omisiones |
| `python tests/run_browser.py` | Salida 0 | Salida 0 |
| `python tests/run_browser.py --demo` | Salida 0 | Salida 0 |
| `python tests/run_browser.py --roster` | Salida 0 | Salida 0 |

El fallo Windows previo se corrigió en el primer intento de arreglo. No se cambió ni retiró ninguna prueba existente; se añadió cobertura del transporte. La ejecución obsoleta `38996676220` fue cancelada al sustituir su código y no se contabiliza como aprobada.

## Decisiones y reversión

- Sin migración nueva hasta probar respaldo previo reversible, interrupciones y comparación financiera con fixtures publicados. Esquema actual: 12. La propuesta 13 no está implementada.
- Sin asignar cuenta a cobros antiguos. La sugerencia es una propuesta; no altera cobros.
- Efectivo y banco de la misma moneda; nunca conciliar monedas distintas automáticamente. La conversión necesita la tasa BCV histórica verificada. La tasa `1` de un recibo USD no se reutiliza como BCV.
- Un hash de contenido sin ID bancario señala un posible duplicado; no se descarta silenciosamente un ingreso legítimo idéntico. La deduplicación persistente sigue pendiente.
- No inventar un formato de Provincial. CSV/Excel es genérico y requiere mapeo; perfil Provincial: **NO VERIFICADO**.
- IVA/IGTF y facturas no están habilitados. Formulario real, calibración, validez del medio de emisión y confirmación fiscal: **NO VERIFICADO**.
- Para revertir este trabajo, dejar de usar esta rama y volver al punto previo; no hay datos ni esquema que revertir. No hace falta borrar carpetas o restaurar la base del colegio.

## Pendientes y límites

La integración operativa de todas las fases queda pendiente. Se conserva un núcleo aislado y probado como punto de reanudación; no se entrega una aplicación a medio migrar ni se afirma que el objetivo completo quedó resuelto.

Faltan específicamente: tablas/migración y fixture 1.0.71; respaldo previo cifrado reversible sin recursión de migración; recuperación por terminación real en la migración nueva; interfaz y permisos HTTP por perfil; asignación de históricos; otros ingresos y categorías; importación persistida e historial; deduplicación entre archivos; clasificación de depósitos; conciliación cambiaria y concurrencia; cierre/reapertura mensual; exportaciones y guía operativa; editor/calibración/lotes/emisión de facturas y sus pruebas.

Las suites actuales prueban los mecanismos vigentes de restauración, consulta, bitácora, instalación en cero y comparación de totales. No acreditan los flujos nuevos que todavía no existen. La matriz de permisos, totales y migración del libro nuevo debe incorporarse antes de habilitarlo.

## Instalador

No se ejecutó instalación, actualización, desinstalación ni instalación con otra cuenta de Windows de esta rama: no existe un instalador nuevo. Las suites nativas no sustituyen esas comprobaciones.

**No se generó instalador, borrador ni final. No hay enlace ni SHA-256 de instalador nuevo.** No se trabajó en firma digital ni certificados. El flujo nuevo de Windows solo ejecuta pruebas; no modifica el empaquetado de otras tandas.

## Pruebas manuales que corresponden al colegio

1. Cuando exista el editor completo: calibrar con fotocopias del formulario real y la impresora del colegio; medir regla, márgenes, posiciones y mitades de carta antes de usar hojas numeradas.
2. Cuando se habilite la importación: revisar el mapeo con un extracto real de Provincial; validar signos, centavos, referencias, fechas y duplicados. Mantenerlo confidencial; no subirlo al repositorio público.
3. Revisar con el contador la validez del medio de emisión, datos fiscales y conceptos. Aula no se conecta a bancos ni SENIAT y no sustituye esa revisión.
4. Tras completar la integración: piloto separado de producción, comparación de cierre/reportes/morosidad, prueba de respaldo/restauración y permisos por perfil. Nada de esto se declara ejecutado físicamente.
