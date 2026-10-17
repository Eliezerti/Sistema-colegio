# Estado de trabajo nocturno

- Rama: `autonomo/ingresos-facturas`.
- Punto inicial verde conocido: `ed1c5e9` (Aula 1.0.71); main intacta.
- Fase 0: inventario y diseño escritos en DECISIONES-AUTONOMAS.md.
- Línea base: unittest en ejecución; resultados pendientes, no declarados como aprobados.
- Fases 1–4: pendientes de implementación y validación. No se aplicaron migraciones a datos del usuario.
- No hay instalador nuevo, publicación ni etiqueta.

## Avance de reglas aisladas

- Fase 0 completada: inventario, decisiones y diseño ampliado en `docs/interno/ingresos-diseno.md`.
- Línea base autorizada: 307 pruebas en 180,169 s, 304 correctas y 3 exclusivas de Windows omitidas. Tres navegadores: salida 0.
- Ejecución restringida previa: 307 en 67,595 s; 118 errores por sockets bloqueados y 3 omisiones; conservada como resultado fallido, no se modificaron pruebas para ocultarlo.
- Prueba administrativa repetida con permiso de sockets: 1 correcta en 1,012 s.
- Reglas aisladas: 14 correctas en 0,297 s; cubren cuentas, depósitos, cruces, duplicados, CSV/XLSX y lotes ambiguos de 9.600 movimientos.
- Cuatro suites de validación final: en ejecución; resultado pendiente.
- No se integraron Fases 1–4: no hay UI, rutas, permisos nuevos, tablas, migración ni facturas. El núcleo no se importa desde la aplicación.

- Revisión adicional: 15 pruebas aisladas correctas en 0,394 s; oráculo independiente de unicidad con 40 conjuntos aleatorios y validación estricta de índices de texto Excel.
- Benchmark del motor aislado (Linux, no HTTP/Windows): 9.600 recibos y 9.600 movimientos, 800 alumnos × 12 meses; referencias únicas 0,067575 s; referencias ambiguas 0,065099 s. No es medición de la pantalla principal ni del almacenamiento.

## Punto de revisión guardado

- Rama publicada en el origin del propietario, sin merge: `autonomo/ingresos-facturas`.
- Commit del núcleo final: `f2c468c`; 17 pruebas aisladas correctas.
- CI de ese commit: https://github.com/Eliezerti/Sistema-colegio/actions/runs/38996806129 (en cola/en curso; no aprobado todavía).
- Informe de revisión: `INFORME-MAÑANA.md`. Entrega parcial explícita; Fases 1–4 siguen sin integrar.
- Próximo bloque: cerrar resultados y después implementar Fase 1 desde el diseño, empezando por el protocolo de respaldo/migración y su fixture publicado. No habilitar primero una UI financiera sin esas garantías.

## Regresión final Linux

- Código `f2c468c`: 324 pruebas en 173,620 s; 321 correctas y 3 exclusivas de Windows omitidas. Sin fallos.
- Tres navegadores: salida 0. Servidor, interfaz y sus pruebas no cambiaron; el núcleo nuevo no está conectado a ellos.
- CI anterior `38996676220` sustituido y cancelado por cambio de código; no cuenta como validación. La ejecución válida será `38996806129`, aún en curso.

## Fallo Windows observado y primer arreglo

- Ejecución `38996806129`: 324 pruebas en 482,260 s, 1 error (`WinError 10053`, rechazo POST `import-roster` en modo consulta); tres navegadores correctos, salidas `1/0/0/0`. No se declaró aprobada.
- Evidencia: `tests/test_read_only_copy.py:62`, rechazo anterior en `colegio/server.py:591` antes de consumir el cuerpo. Posible cierre TCP con datos pendientes; no se observó una escritura en la copia.
- Primer arreglo: `Handler.discard_rejected_body`, antes de devolver 403. Descarta bytes por fragmentos, máximo 46 MB y plazo total 2 s; nunca analiza JSON ni abre la base. Cuerpos inválidos siguen bloqueados.
- Prueba dirigida real: 4 correctas en 9,361 s; cuerpo de 200 KB no JSON, emisores incompleto y lento, 403, sin conexión SQLite y copia intacta.
- Pendiente repetir las cuatro suites Linux y Windows del arreglo. Máximo dos intentos de corrección; se lleva uno, sin omitir pruebas.

## Cierre Linux del primer arreglo

- Código `6f19357`: 325 pruebas en 188,147 s, 322 correctas y 3 exclusivas de Windows omitidas.
- Navegadores normal/demo/roster: salidas 0/0/0.
- Windows pendiente: https://github.com/Eliezerti/Sistema-colegio/actions/runs/38997949165
- Se conserva el fallo anterior `38996806129` en el informe, sin confundirlo con una validación correcta. No se han tocado cálculos, recibos, correlativos ni esquema.
