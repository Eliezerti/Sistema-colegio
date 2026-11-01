# Avisos de cobranza · validación de revisión

01/11/2026 · Aula 1.0.74 en desarrollo · rama `cashea`, base `39eadf0`. Diseño entregado antes del código en `4f7b832`. No se fusiona a main ni se crea una publicación final.

## Resultado real en Linux

Python 3.12.14, cryptography 50.0.0, Node 24.19.0, Playwright 1.62.1 y Chromium 151.0.7922.173. Pruebas en carpetas temporales independientes; ningún registro ni respaldo del colegio se abre o modifica. Salida completa en [avisos-pruebas.txt](avisos-pruebas.txt).

| Comando | Resultado real |
|---|---|
| `python -m unittest discover -s tests -v` | 388 pruebas en 345,778 s; **OK**, 385 correctas y 3 omisiones exclusivas de Windows. |
| `python tests/run_browser.py` | **Correcto**, salida 0; incluye Cashea, anticipos, sesiones, avisos y visor de copia. |
| `python tests/run_browser.py --demo` | **Correcto**, salida 0; base aislada, recarga, pestañas y eliminación del temporal. |
| `python tests/run_browser.py --roster` | **Correcto**, salida 0; CSV/Excel, conservación de datos importados y sin copiar pagos. |
| `python -m unittest discover -s tests -p test_collection_notices.py -v` | 17 nuevas, 2,841 s; **OK**, sin omisiones. Están incluidas en las 388. |

Las tres omisiones locales son DPAPI, mutex/enfoque de ventanas y revisión/restauración con Tk nativo. Windows terminó después: **388 pruebas correctas sin omisiones en 568,150 s**, los tres navegadores y las comprobaciones del instalador correctos en [41318825940](https://github.com/Eliezerti/Sistema-colegio/actions/runs/41318825940). La primera ejecución pasó las 388 pero falló en la representación nativa CRLF del portapapeles; se corrigió solo esa prueba. [Entrega, diagnóstico y evidencia real de Windows](avisos-instalador.md). La impresión física y el envío/entrega real en WhatsApp no se ejecutaron; este ajuste no cambia la impresión ni añade envío automático.

## Cambios y evidencia en el código

- `colegio/collection_notices.py:27`: cinco tipos × tres variantes; `:70`, nombres completos; `:83`, saludo UTC−4; `:88`, formato venezolano; `:97`, teléfono.
- `collection_notices.py:128–198`: validación de marcadores, valores por defecto en código y solo personalizaciones en settings; guardado por Administración y bitácora con huellas, sin duplicar textos libres de pago. No cambia el esquema 14 ni siembra filas de configuración.
- `collection_notices.py:210–263`: contexto a partir de `charges` existente; vencidos y saldos reales, hermanos del mismo representante, seis cargos más antiguos por alumno y total completo. Tasa solo de hoy; sin tasa omite Bs. Sin conexión a bancos, Cashea ni WhatsApp.
- `collection_notices.py:265–337`: último aviso, vista previa, registro manual por Administración/Caja, clave idempotente y protección de reloj/bitácora. Transacción `BEGIN IMMEDIATE` existente en `server.py:655`; dos solicitudes HTTP simultáneas producen una sola nota. Si falla el evento auditado, se revierten todas las notas de los hermanos.
- `server.py:177–183`: permisos antes de ejecutar acciones; los avisos se despachan antes de la generación de mensualidades para que guardar ajustes o seguimiento no genere cargos. `:960`, GET autenticado; modo consulta conserva el bloqueo general de POST.
- `static/collection_notices.js`: formulario con texto editable, tipo, opciones y rotación; enlace construido desde el texto actual, inválidos con Copiar disponible, seguimiento manual y Ajustes independiente. Contexto personal ligado al DOM del modal, sin caché global ni cambios en `session.js`.
- `tests/test_collection_notices.py`: 17 pruebas nuevas. Incluyen 1/3/8 meses para cada plantilla; conversión 260,00 USD → 231.207,60 Bs a 889,26; sin tasa; conceptos, pagos parciales, cobertura Cashea, futuro/anulación excluidos; tipos por edad; marcadores, originales, variantes, nombres, horarios, teléfonos, hermanos, opciones, permisos, CSRF, rollback, idempotencia simultánea y consulta por HTTP.
- `tests/collection_notices_browser.cjs`: flujo real desde Morosidad, seis meses y total de ocho, copiar sin marcar, edición conservada al salir del campo y URL exacta, última fecha, hermanos, teléfono inválido, borradores de Ajustes, personalización, preview ficticio y restauración. Una respuesta retenida se entrega después de bloquear la sesión: el API existente la rechaza y no reabre el modal. Las aserciones comparan cargos, pagos, egresos, resumen, Cashea y cierres completos antes/después.
- `tests/permission_matrix.py`: tres POST nuevos y GET registrados en la matriz; los intentos desde una copia quedan bloqueados en el servidor. Se conserva la suite anterior completa, incluidos migraciones con fixtures publicados, cero, respaldos, restauración, cortes de proceso y permisos.

El diff no modifica `db.py`, `schema.py`, `cashea.py`, `advance_payments.py`, el cálculo de mora, documentos/recibos ni `session.js`. No hay migración ni cambios en correlativos. El instalador solo añade la guía de usuario a su lista explícita; ningún material interno se empaqueta como manual del colegio.

## Fallos encontrados y corregidos, sin ocultarlos

1. **Línea base, antes del producto nuevo:** 371 pruebas en 329,414 s, 15 fallos y tres omisiones. El 01/11/2026, 13 pruebas de anticipos congelaban el reloj del servidor al 30/10 pero los helpers importados de otros fixtures usaban la fecha real; fallaba confirmar tasa. Dos pruebas de migración congelaban solo el servidor al 27/10, dejando a la generación usar noviembre. Se fijaron únicamente los aliases de fecha de pruebas en `f27f735`; mismos importes esperados, assertions, fixtures y código financiero. Repetición dirigida: anticipos 13/13, migración 12→13 7/7 y 13→14 5/5 correctas. La salida inicial y su traceback se conservan en la evidencia.
2. El primer navegador de avisos encontró que el propio fixture cambiaba el teléfono para probar el caso inválido y lo dejaba cambiado al comparar todas las columnas de cargos enriquecidos. Se restituye ese dato ficticio antes de la comparación; no se excluye la columna ni se relaja la comparación.
3. La revisión de eventos detectó que el `change` del textarea podía regenerar el aviso al salir del campo. Se limita a selectores/casillas; el navegador ahora pierde el foco expresamente y exige conservar el texto y la URL exacta.
4. La primera prueba adicional de respuesta tardía esperaba una promesa resuelta, pero el API ya rechaza correctamente las respuestas de otra sesión. Se prueba ese rechazo concreto, sin cambiar el API ni la protección; la limpieza de fixtures ya no oculta una excepción anterior al intentar guardar sin sesión. Recorrido final correcto, sin errores de consola ni tiempos ampliados.

## Capturas y paquete

Dos capturas del modal, revisadas visualmente: [Cercano](capturas-avisos/aviso-cercano-ficticio.png) y [Hermanos](capturas-avisos/aviso-hermanos-ficticio.png). Colegio y familia están marcados FICTICIOS; solo se captura el diálogo. El textarea se puede desplazar para leer el resto. [Manifiesto](capturas-avisos/manifest.json) con huellas y generador reproducible.

`python tests/package_cashea_review.py --base 39eadf0 --output dist/Aula-1.0.74-avisos-revision.zip` empaqueta los archivos modificados, diff binario íntegro, diseño, guías, evidencia y capturas. PNG admitidos solo por ruta exacta y firma/tamaño/huella; no se habilitan imágenes arbitrarias. Se rechazan archivos fuera de la lista, bases del usuario, llaves, ejecutables y patrones de credenciales. El ZIP incluye manifiesto de cada archivo; se verifica CRC, tamaño menor de 20 MB y aplicación del diff contra la base. No incluye entorno virtual, .env ni datos personales reales.

## Revisión manual del colegio

1. Abrir Aviso en una cuenta conocida y revisar meses/abonos/total sin modificar cobros. Probar el texto breve y el convenio; personalizar el tono si se desea.
2. Revisar teléfono y WhatsApp con un contacto autorizado: confirmar que el texto copiado/abierto es el editado. Solo la persona decide si enviarlo. Marcar manualmente después, no antes.
3. Probar hermanos y datos para pagar con la revisión del Administrador; revisar la tasa del día. Consulta debe poder copiar y no marcar.

No hay aprobación técnica de entrega por WhatsApp ni garantía de aprobación Cashea. A petición posterior se construyó y validó el [instalador actualizado con avisos](avisos-instalador.md), distinto del instalador anterior de pagos adelantados. La revisión de código conserva ZIP, diff y capturas ficticias.
