# Ajustes 1.0.69

El recordatorio de prueba externa se actualiza al terminar correctamente la prueba marcada como externa. «Ocultar por 7 días» guarda únicamente una preferencia en este navegador; no registra una prueba ni oculta fallas reales. Si se borra el almacenamiento del navegador, vuelve a mostrarse. Un reloj anterior al momento de ocultarlo invalida la preferencia. La información de nube y cifrado sigue disponible en Protección y mantenimiento.

Los comprobantes tienen más separación entre secciones y conservan firmas, número R-, personas, grado, conceptos, importes, saldo, método y referencia. No muestran código interno ni cédula escolar. PDF individual: 396 × 612 puntos; ORIGINAL/COPIA: 792 × 612. La impresión usa la configuración normal del diálogo, sin imponer escala. Sin cambios de esquema, cálculos ni correlativos. B3 sigue pendiente.

## Validación

Linux, revisión `3b44fb4`:

| Comando | Resultado real |
| --- | --- |
| `python -m unittest discover -s tests -v` | 301 en 162,547 s; 298 correctas y 3 exclusivas de Windows omitidas. |
| `python tests/run_browser.py` | Correcto, incluido visor de copias. |
| `python tests/run_browser.py --demo` | Correcto. |
| `python tests/run_browser.py --roster` | Correcto. |

Las tres omisiones son DPAPI, mutex/enfoque de ventanas y revisión de restauración con Tk; requieren Windows. El PDF ficticio de dos copias se inspeccionó con PyMuPDF: una página, 792 × 612 puntos. Las once pruebas de composición PDF también pasaron.

La primera prueba de navegador todavía buscaba el aviso de nube en su ubicación anterior; la siguiente esperaba entrar directamente después de recargar, sin confirmar la tasa. Se corrigieron las comprobaciones al recorrido real sin modificar las protecciones; el recorrido completo posterior pasó. La primera ejecución Windows se canceló al reemplazarla por esa corrección de pruebas.

Windows, ejecución 38789842262: suite y compilación correctas; navegador detenido al recibir tarde el mensaje de consola de un 401 esperado durante un cierre de sesión intencional. Se corrigió la sincronización de la prueba para esperar tanto la respuesta real como su evento de consola, sin cambiar sesiones ni ampliar los errores ignorados. Nueva validación completa pendiente.

## Evidencia de implementación

- `static/app.js:647`: preferencia temporal local, caducidad de siete días y comprobación de reloj anterior.
- `static/app.js:657`: el recordatorio se puede ocultar; los errores conservan su sección de alerta.
- `static/app.js:988`: la prueba correcta obtiene el estado actualizado del servidor y explica si se declaró externa.
- `colegio/server.py:826`: únicamente una prueba correcta declarada externa reinicia el registro, con bitácora; sin cambios en esta revisión.
- `static/style.css:316` y `colegio/documents.py:495`: separación de bloques en impresión y PDF.
- `colegio/desktop_checks.py:127`: configuración nativa con escala predeterminada, sin asignación forzada.
- `tests/browser.cjs:369`: ocultación persistente, caducidad, reloj anterior, errores visibles y actualización tras probar una copia externa.

 Las pruebas usan datos ficticios en carpetas temporales; no registran pagos reales. La impresora física del colegio requiere comprobación en el equipo del usuario.
