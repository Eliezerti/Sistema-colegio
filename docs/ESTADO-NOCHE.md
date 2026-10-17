# Estado de trabajo nocturno

**Núcleo de Fases 1–3 integrado y validado en Linux y Windows. Fase 4: diseño, sin funciones entregadas todavía.**

- Rama `autonomo/ingresos-facturas`; código verde `a772d2553d2f070f33aa715692d5cdb95988cdc3`. Main intacta; sin merge, etiquetas ni versión publicada. No se abrió ni modificó una base del usuario.
- Fase 1: cuentas escolares, cuenta destino, asignación explícita de históricos, otros ingresos y depósitos parciales. Fase 2: CSV/XLSX, perfiles editables, huellas, duplicados, cruces únicos y parciales, clasificaciones y privacidad. Fase 3: cierre mensual, bloqueo del servidor, foto conservada, reapertura motivada y relación CSV/PDF.
- Esquema 15, catorce tablas nuevas aditivas. Transiciones 12→13→14→15 con respaldo previo verificado y cinco terminaciones reales por transición; integridad, claves foráneas y cadena. Fixture publicado 1.0.71 y referencia independiente de caja/reportes/morosidad. Instalación lógica vacía.
- **Linux final: 355 en 309,459 s, 352 correctas y tres nativas omitidas; normal/demo/roster salida 0.** Registros `/workspace/work/noche3/final355-*.log`; resumen conservado en `docs/interno/ingresos-evidencia/linux-cuatro-suites.json`.
- **Windows final: 355 correctas en 666,551 s, sin omisiones; normal/demo/roster salida 0.** [39028897879](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39028897879), evidencia `windows-final.json` en la misma carpeta. También terminó correctamente el punto anterior `cb34ad7`: 354 en 750,012 s, tres navegadores salida 0; no se canceló ninguna suite en marcha.
- HTTP final con 800 alumnos: Linux 12/36 meses, principal 7.993/8.000 bytes, medianas 0,185610/0,442593 s; Windows 12 meses, 8.093 bytes y 0,394435 s. CSV con tamaño, mediana y máximo en `docs/interno/ingresos-evidencia/`. Windows 36 meses no ejecutado.
- Últimos arreglos: aislamiento de reloj de referencia; LF obligatorio para conservar su huella; exclusión de otros ingresos de caja de pendientes bancarios; rechazo con cifrado bloqueado antes de crear copia de reversión. Prueba compuesta portable de libro conciliado y cierre, con contraseña/recuperación sin almacén original, restauración e inmutabilidad de consulta.
- Fallos y resultados previos completos en INFORME-MAÑANA.md e historial. Dos validaciones que estaban solo en cola se sustituyeron antes de ejecutar pruebas; las activas terminaron. Inicial Windows fallido sin logs recuperables, causa desconocida; repetición diagnosticó CRLF, corregido sin relajar huellas.

## Siguiente fase y punto de retorno

Se continúa Fase 4 por autorización autónoma, conservando este punto verde del núcleo. Diseño en `docs/interno/facturas-diseno.md`. Primero reglas de plantilla/PDF con pruebas; integrar API, esquema e interfaz solo como bloque funcional completo. No presentar botones ni emisión fiscal parcial como entregados. Si una prueba sigue fallando tras dos arreglos, revertir la fase mediante commits normales al punto verde anterior y conservar el informe.

Pendientes del núcleo: conversión entre cuentas/monedas, depósitos de efectivo convertidos y traslado de efectivo de otros ingresos. Soporte textual sin adjuntos. No se inventan tasas ni recibos para cubrir esos casos.

No existe instalador de esta rama. No se ejecutaron instalación/actualización/desinstalación ni impresión física de este código. NO VERIFICADO: extracto real de Provincial, formulario real, calibración y confirmación fiscal. El ZIP fuente en scratch fue verificado, sin base de negocio ni respaldos; no es instalador ni publicación.

## Entorno y recuperación

Al reanudar, el entorno volvió a `a5b5aed` sin logs anteriores. Se recuperó la rama enviada; no se perdió código. La revisión por límite de uso volvió a permitir el mismo mecanismo autorizado. No se eludió la política de red: el host de un artefacto estaba prohibido; las nuevas anotaciones de GitHub conservan resultados y tracebacks por API permitida. Los logs antiguos no observados no se declaran correctos. Los nuevos logs y evidencia real sustituyen esa incertidumbre para el núcleo final.
