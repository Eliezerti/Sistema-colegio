# Ajuste Cashea: número de recibo e inicial en Bs

28/10/2026 · rama `cashea` · Aula 1.0.74 en desarrollo · esquema 14. Base del diff: `e3ba2d6e5f02ab1ce4cf1cfbbb6b18ea30a17e5e`. Código funcional: `3163f0cb19ae18405cfb4b15a952d81f93c08d43`; los commits posteriores solo ajustan sincronización de pruebas y documentación. Sin fusión a main, etiquetas ni versión final.

## Cambios

- Recibo por defecto: `invoice_number` es el R- realmente insertado por la inicial, dentro de la misma transacción, y `invoice_origin` guarda `recibo`. Predicción sin reserva, revisión si otro cajero consume el número, índice único que también conserva números anulados, idempotencia y bitácora. Con inicial cero se usa el CA- y la etiqueta «N.º de orden», sin pago ni consumo de R-. Administración puede elegir Manual: número siempre obligatorio, con revisión y motivo para duplicados manuales; nunca permite reutilizar un identificador de origen Recibo.
- Número destacado y Copiar en la confirmación posterior al guardado, detalle y listado; número real en CA- y reportes. Anular avisa que también debe anularse en el portal. Las órdenes anteriores permanecen Manual, incluidos duplicados autorizados y números vacíos que antes se permitían: no se renumeran.
- La moneda determina la etiqueta, el importe visible y la calculadora. Cambiar USD → Bs convierte con la tasa confirmada del día; si falta, limpia la cifra y pide confirmar la tasa. Muestra tasa, original y equivalente USD en la revisión; más de 1 % de diferencia avisa sin bloquear. JavaScript calcula con BigInt y admite tasas Decimal en notación científica. El importe real manda.
- La guía y Ajustes incluyen una sola aclaración sobre el carácter no fiscal y la validación con Cashea/contador. No se añade esa advertencia al formulario de venta.
- Esquema 14 porque ya se entregaron copias en 13. Migración aditiva, copia anterior local verificada y cifrada en el segundo destino configurado para la base activa, integridad/foreign keys/bitácora y cinco terminaciones reales. La conversión, consulta y restauración migran temporales privados sin tocar origen ni su destino externo. Reversión documentada mediante copia previa; no elimina datos posteriores.

## Evidencia y conservación

Se conservaron los 345 casos anteriores y se añadieron 13. Los cambios en pruebas anteriores son expectativas de esquema 14 y los dos escenarios que ahora deben elegir explícitamente Manual. No se eliminaron casos, no se relajaron permisos, totales, contraseñas, tiempos ni comprobaciones de seguridad.

El fixture `tests/fixtures/cashea/desktop-1.0.74-schema13-ficticio.sqlite3` fue generado ANTES de modificar código con `e3ba2d6`, a partir del fixture publicado ficticio 1.0.73. Contiene dos órdenes manuales duplicadas autorizadas, cinco alumnos ficticios, cero sesiones y cero fechas de nacimiento. Su manifiesto registra procedencia y SHA-256. La referencia de cierre, resumen, reporte diario y mensual fue calculada con el código previo; la migración conserva todos sus importes, filas, snapshots y el prefijo exacto de la cadena. La comparación excluye únicamente la nueva preferencia y la hora de emisión.

La implementación de `record_payment`, `convert_received`, `money` y `next_record_id` es textualmente idéntica a `e3ba2d6`; el único cambio de `db.py` incorpora la migración al inicio. Hay prueba de R- histórico en PDF idéntico antes y después de una nueva venta. Se verifican instalación vacía, pisos en cero, restauración, Probar respaldo, consulta, permisos, CSRF, idempotencia y concurrencia de dos ventas con la misma predicción.

## Resultados reales

[Salida completa de Linux](cashea-ajuste-pruebas.txt).

| Comando | Linux |
|---|---|
| `python -m unittest discover -s tests -v` | 358 pruebas en 287.019 s; OK, tres nativas omitidas |
| `python tests/run_browser.py` | Código 0, incluidos Cashea, Copiar, 40/16/24, USD/Bs, tasa científica, tasa ausente, borrador recuperado, Manual, inicial cero y consulta |
| `python tests/run_browser.py --demo` | Código 0 |
| `python tests/run_browser.py --roster` | Código 0 |

Las tres omisiones en Linux son DPAPI, mutex/ventana Windows y diálogo nativo Tk de restauración. No se cambiaron sus condiciones. El PDF CA- ficticio se comprobó además con `pdfinfo`: una página, 396 × 612 puntos; número R- real destacado. La impresión física del colegio no se ejecutó.

Windows, primer intento [40762203368](https://github.com/Eliezerti/Sistema-colegio/actions/runs/40762203368), job 123076810906, commit `3163f0c`: **358 unittest en 607.294 s, OK sin omisiones**, compilación correcta. Falló el navegador normal en `cashea_browser.cjs:128`: `page.waitForFunction` esperando Manual agotó 30000 ms tras un POST de Ajustes 200. No llegaron a ejecutarse `--demo`, `--roster`, instalación, impresión nativa ni actualización en ese intento. [Salida y traceback](cashea-ajuste-windows.txt).

La prueba navegaba a Ajustes y editaba antes de esperar la actualización asíncrona que reemplaza su formulario. Se sincronizó con el cambio real de estado, se añadió una respuesta deliberadamente lenta de 250 ms y se comprueba que el POST y la respuesta guarden Manual. No se ampliaron tiempos, no se retiró la espera ni se modificó el producto. Se repitieron las tres suites en Linux: todas correctas. La repetición completa aprobó todos los pasos: [Actions 40765068773](https://github.com/Eliezerti/Sistema-colegio/actions/runs/40765068773), job 123086889259, commit `047d150`. La salida final está en [evidencia Windows](cashea-ajuste-windows.txt).

### Resultado final en Windows

Windows Server 2022, Python 3.12.10. Job completo **success**; código funcional idéntico a `3163f0c`, pruebas sincronizadas en `047d150`.

| Comando | Resultado real |
|---|---|
| `python -m unittest discover -s tests -v` | 358 en 870.031 s, OK sin omisiones |
| `python tests/run_browser.py` | Código 0; incluye Copiar, R- real, Bs, 40/16/24, tasa ausente/científica, Manual con petición/respuesta comprobadas, inicial cero y consulta |
| `python tests/run_browser.py --demo` | Código 0 |
| `python tests/run_browser.py --roster` | Código 0 |

Compilación, inventario e Inno Setup correctos. Instalación limpia, accesos directos, ventanas, bandeja, consulta cifrada y eliminación del temporal correctos. WebView2 verificó una página de 396 × 612, 612 × 792 y 792 × 612 puntos según papel, con escala predeterminada. Actualización real del instalador 1.0.73 al nuevo 1.0.74: datos/totales y PDF histórico idénticos; CA/R/CL, inicial VES (original Bs 1.600, tasa 100, USD 16), número R- real, integridad y desinstalación conservadora comprobados. La migración 13 → 14 se prueba con el fixture del esquema previamente entregado; la actualización nativa usa 1.0.73.

[Instalador BORRADOR aprobado por esta validación](https://github.com/Eliezerti/Sistema-colegio/actions/runs/40765068773/artifacts/12851326222) · [Evidencia nativa y JSON de actualización](https://github.com/Eliezerti/Sistema-colegio/actions/runs/40765068773/artifacts/12851850601). Sigue siendo una entrega de revisión en `cashea`; no es una publicación final. La impresión física del colegio y la aceptación del número por Cashea/contador no se han verificado.

## Incidencias durante el desarrollo

- Primera ejecución de la línea base en sandbox: 345 casos, 150 errores porque `socket.socket()` estaba prohibido, tres omisiones nativas. La prueba de seguridad produjo el traceback completo conservado en la evidencia. Se habilitó la ejecución autorizada con sockets en 127.0.0.1: prueba de seguridad correcta, línea base 345 correcta con tres omisiones y los tres navegadores correctos, antes de editar el código.
- Primera ejecución dirigida: dos fallos en pruebas nuevas. La referencia comparaba la hora/configuración de emisión y la prueba de tasa omitía confirmar un cambio superior al 10 %. Se corrigieron esas preparaciones, conservando las protecciones del producto; las 13 pruebas nuevas pasaron. Una edición de validación de respaldos tuvo un error de indentación, corregido antes de la repetición.
- Primera suite completa del ajuste: 358 en 354.618 s, tres fallos `14 != 13` en expectativas antiguas de restauración, cifrado y calendario. Se actualizaron exclusivamente esas expectativas a 14 y se repitió completa: resultado verde arriba.
- Se cancelaron las ejecuciones Windows de commits superados para concentrar la validación en el commit final. Una cancelación no se presenta como prueba aprobada.

## Paquete y límites

El ZIP incremental incluye archivos modificados, diff binario completo desde `e3ba2d6`, diseño, guía, pruebas y evidencia. El empaquetador limita archivos y tamaño, busca patrones de secretos, verifica nombres ficticios y hash del fixture, excluye sesiones y fechas de nacimiento. Solo incluye la base de prueba declarada; no hay base del usuario, .env, llaves, token, entorno virtual ni ejecutables. El manifiesto permite verificar cada archivo. Se comprobó también `git apply --check` del diff contra una copia de `e3ba2d6`.

No se registraron cobros en una base real. Pendiente del colegio: impresión física y validación con Cashea y su contador del uso del número R-. No hay conexión con Cashea ni con bancos y no se implementó numeración fiscal.

[Diseño y reversión](../../DISENO_CASHEA.md) · [Guía de usuario](../cashea.md).
