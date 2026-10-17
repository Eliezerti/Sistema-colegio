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
