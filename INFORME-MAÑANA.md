# Informe de la mañana · ingresos y facturas

**Entrega parcial de revisión. Fase 1 integrada y validada en Linux y Windows. Fases 2–4 pendientes.**
Rama: `autonomo/ingresos-facturas`. Punto de partida: `ed1c5e9`, Aula 1.0.71. Main, etiquetas y versión publicada intactas. Ninguna base del usuario fue abierta, limpiada o migrada.

## Qué se hizo

| Bloque | Resultado real |
|---|---|
| Fase 0 | Inventario, diseño y decisiones documentados; sin datos reales. |
| Fase 1 | Cuentas editables, cuenta en cobros, asignación histórica explícita, depósitos parciales de efectivo sin doble cobertura, otros ingresos/categorías/soporte y egresos con cuenta. Interfaz, API, permisos y bitácora integrados. Migración aditiva a esquema 13, copia previa verificada y pruebas sobre código publicado 1.0.71. Linux y Windows correctos. |
| Fase 2 | Reglas puras CSV/XLSX, huella, referencias y propuestas; importación persistente, perfiles guardados, conciliación operativa y clasificaciones **pendientes**. |
| Fase 3 | Cierre diario y reportes vigentes incluyen otros ingresos y traslados sin duplicar ingresos; cierre mensual protegido y relación ampliada para contador **pendientes**. |
| Fase 4 | Editor, lotes, emisión y PDF de facturas **pendientes**; ningún número fiscal generado. |

Código de Fase 1: `ddba0ca9a2707f1fd9b133b4aea732d757fd1c2a`; commits `2701023` (esquema), `1e003a4` (servidor/reportes), `11e00dc` (pruebas) y `ddba0ca` (interfaz). [Guía de cuentas e ingresos](docs/cuentas-ingresos.md). El comprobante de mensualidad conserva su foto, importes y correlativo. No se asigna cuenta a históricos automáticamente.

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

## Validación de la Fase 1

- Primera regresión completa: 331 en 213,631 s, **15 errores**, tres omisiones nativas. No se declaró aprobada. Se corrigieron fixtures antiguos y el comportamiento de lectura ante cabecera de bitácora dañada; las escrituras siguen bloqueadas. Primer arreglo, dirigido: 57 correctas en 11,695 s; ocho pruebas de ingresos/migración correctas en 7,882 s.
- Repetición completa Linux: **333 en 206,436 s; 330 correctas y 3 exclusivas de Windows omitidas**. Los tres navegadores terminaron con **salida 0**. El normal prueba por interfaz cuentas, categoría, otro ingreso, cuenta en cobro, depósito y anulaciones; la deuda sigue igual y el depósito no duplica ingresos. Roster inicial falló por no elegir una cuenta; se incorporó la configuración real a ese flujo y pasó la repetición.
- Las pruebas nuevas incluyen fixture ficticio producido con el código publicado 1.0.71, conservación exacta de dinero y prefijo de cadena, copia previa cifrada abierta con contraseña y recuperación, cinco terminaciones reales del proceso, cero registros iniciales, asignación masiva atómica, concurrencia de dos solicitudes de depósito, permisos por HTTP, restauración cifrada con vínculos, revisión de datos y comparación diaria/mensual/morosidad.
- Windows para este código: [39001990044](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39001990044), **333 correctas en 550,777 s, sin omisiones; tres navegadores correctos, salidas 0/0/0/0**. [Registros](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39001990044/artifacts/12090006489). La validación Windows anterior del núcleo aislado no acredita esta integración.
- Logs de esta fase: `/workspace/work/noche2/phase1-unittest-fixed.log`, `phase1-browser-fixed.log`, `phase1-demo-fixed.log`, `phase1-roster-final.log`. Los fallos iniciales también se conservaron.

## Decisiones y reversión

- Esquema 13 implementado: siete tablas acompañantes, sin borrar ni reconstruir tablas existentes ni alterar pisos. Instalación nueva vacía, sin cuentas semilla.
- Copia previa en `.aula-migrations/schema-13/`, verificada antes de DDL. Cifrada si está configurado el cifrado; si está bloqueado, no actualiza. Sin configuración queda una copia SQLite privada local: **no se presenta como cifrada**. El manifiesto la identifica y no se rota automáticamente.
- Para revertir, conservar íntegra la carpeta actual y sus operaciones nuevas. Restaurar la copia previa en otra carpeta vacía con la versión anterior. No sobrescribir ni borrar la base actual. [Procedimiento](docs/cuentas-ingresos.md).
- Sin cuenta histórica inferida. Caja registra cobros y depósitos; Administración configura, asigna y registra/anula otros ingresos. Consulta ve resúmenes sin datos bancarios ni soporte.
- Tasa histórica BCV en metadatos nuevos; si falta para un cobro USD antiguo queda vacía, nunca se reutiliza su tasa `1` como BCV.
- No se inventó formato de Provincial: **NO VERIFICADO**. También **NO VERIFICADO**: formulario físico, calibración, validez del medio de emisión y confirmación fiscal.
- IVA/IGTF no habilitados; sin conexión a bancos o SENIAT. Las facturas todavía no existen en esta rama.
- La revisión automática rechazó una edición que podía admitir esquemas futuros desconocidos; no se ejecutó. Se sustituyó por aceptación explícita del único esquema nuevo conocido (13), conservando el rechazo de versiones superiores. La alternativa fue autorizada.

## Pendientes y límites

Fase 2: perfiles persistidos, importación confidencial e historial, duplicados entre archivos, conciliación y clasificaciones guardadas, cruce de débitos/egresos, listas y revisión. Las reglas puras no acreditan esas funciones.

Fase 3: bloqueo mensual en servidor y reapertura motivada, resumen de pendientes, relación para contador CSV/Excel/PDF con equivalentes históricos verificados, conciliación contra extracto, guía mensual y pruebas.

Fase 4: editor visual completo, calibración, plantillas versionadas, lotes y números confirmados por operador, concurrencia de emisión, inmutabilidad, hojas dañadas, reimpresión, relación de ventas y pruebas de PDF. No se presenta un PDF genérico como formulario autorizado.

Rendimiento anterior de 800 alumnos y 12 meses mide únicamente reglas puras. Falta rendimiento de HTTP/base/interfaz de la conciliación integrada, incluida Windows.

## Instalador

No se ejecutó instalación, actualización, desinstalación ni instalación con otra cuenta de Windows de esta rama: no existe un instalador nuevo. Las suites nativas no sustituyen esas comprobaciones.

**No se generó instalador, borrador ni final. No hay enlace ni SHA-256 de instalador nuevo.** No se trabajó en firma digital ni certificados. El flujo nuevo de Windows solo ejecuta pruebas; no modifica el empaquetado de otras tandas.

## Pruebas manuales que corresponden al colegio

1. Cuando exista el editor completo: calibrar con fotocopias del formulario real y la impresora del colegio; medir regla, márgenes, posiciones y mitades de carta antes de usar hojas numeradas.
2. Cuando se habilite la importación: revisar el mapeo con un extracto real de Provincial; validar signos, centavos, referencias, fechas y duplicados. Mantenerlo confidencial; no subirlo al repositorio público.
3. Revisar con el contador la validez del medio de emisión, datos fiscales y conceptos. Aula no se conecta a bancos ni SENIAT y no sustituye esa revisión.
4. Antes de usar Fase 1 en producción y tras completar las demás fases: piloto separado de producción, comparación de cierre/reportes/morosidad, prueba de respaldo/restauración y permisos por perfil. Nada de esto se declara ejecutado físicamente.
