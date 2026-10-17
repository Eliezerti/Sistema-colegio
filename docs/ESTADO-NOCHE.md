# Estado de trabajo nocturno

**Núcleo de Fases 1–3 integrado. Fase 3 aún no aprobada en Windows. Fase 4 y conciliación con conversión pendientes.**

- Rama: `autonomo/ingresos-facturas`. Código del núcleo: `2d3af092dec8f25bd8442ae859777f4686bbebd5`. Sin merge, etiquetas ni publicación; main intacta.
- Fase 1: cuentas escolares, cuenta en cobros/egresos, revisión explícita de históricos, otros ingresos y depósitos parciales de efectivo. Linux 333 (tres nativas omitidas) y tres navegadores correctos. Windows 333 correctas, sin omisiones y tres navegadores correctos: [39001990044](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39001990044).
- Fase 2: importación CSV/XLSX con perfiles, huella/usuario/fecha, duplicados, cruces únicos y parciales, clasificaciones y privacidad. Linux 343 (tres nativas omitidas) y tres navegadores correctos. Windows 343 correctas en 446,056 s y tres navegadores correctos: [39003181236](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39003181236).
- Fase 3 integrada: cierre mensual con foto conservada, bloqueo del servidor, reapertura motivada, opciones informativas sin impuestos y relación CSV/PDF para contador. Commits `52ac0f4`, `efd2b9f`, `784cc86`, `2d3af09`. Esquema 15 aditivo. Cada transición 12→13→14→15 tiene copia previa verificada y cinco terminaciones reales del proceso. Instalación nueva vacía.
- Linux anterior: 351 en 233,656 s, tres nativas omitidas; tres navegadores correctos. La referencia independiente adicional pasó sola (1 en 0,077 s). La repetición completa de 352 no pudo recuperarse tras reiniciarse el entorno; **no se declara aprobada**.
- Windows Fase 3 [39004156877](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39004156877): **falló** el paso de cuatro suites. No conocemos todavía qué comandos fallaron: descarga del artefacto bloqueada por política de red (host de almacenamiento no permitido), y `gh run view --log` no devolvió contenido. Rendimiento Windows no ejecutado porque depende de ese paso.

## Reanudación del 17 de octubre

El entorno volvió a la copia inicial `a5b5aed`, sin registros locales anteriores. Se recuperó del remoto el commit `2d3af09`, sin rehacer ni perder el código enviado. El bloqueo anterior de revisión automática por límite de uso dejó de impedir el mecanismo autorizado después de reanudar. No se eludió ese mecanismo ni la política de red.

Reproducción local: 8 dirigidas, una falla real; la referencia importaba tardíamente un módulo mientras `db.local_today` era un Mock de 2025. Ese módulo conservaba la fecha y rechazaba un ingreso ficticio actual como futuro. Primer arreglo: congelar la fuente datetime solo dentro de la prueba, manteniendo la función original; comprobar que el reloj no queda contaminado. **8 correctas en 9,207 s**. La protección real contra fechas futuras no se modificó.

Se agrega evidencia de CI en anotaciones de GitHub: salidas reales, conteo, duración y traceback completo por partes. Así los nuevos resultados se pueden revisar sin descargar el artefacto bloqueado. No se presenta como corrección confirmada del fallo Windows hasta ejecutar la nueva validación. La referencia de importes sigue producida por código publicado de 1.0.71; no se cambian sus valores para hacer pasar pruebas.

## Lo siguiente

1. Completado: cuatro suites Linux del primer arreglo, unittest 352 en 293,531 s (349 correctas y tres nativas omitidas), normal/demo/roster salida 0. Registros `/workspace/work/noche3/final-*.log`.
2. Consultar las anotaciones de la nueva validación Windows. Si falla, leer la causa concreta; máximo dos intentos de arreglo por prueba, luego revertir Fase 3 al punto verde de Fase 2 y registrar el resultado.
3. Actualizar README, CHANGELOG e INFORME-MAÑANA.md con el estado definitivo, evitando descripciones antiguas que aún dicen Fase 3 pendiente de integración.
4. Conservar fuera del núcleo la Fase 4: editor, lotes, emisión y numeración fiscal no implementados. Conversión entre cuentas o monedas y depósitos de efectivo convertidos también pendiente; nunca inferir una tasa.

No existe instalador de esta rama. No se ejecutaron instalación/actualización/desinstalación ni impresión física de este código. NO VERIFICADO: extracto real de Provincial, formulario real, calibración y confirmación fiscal. No se abrió ni cambió ninguna base del usuario.

## Estado actualizado de la validación

- Primer arreglo de aislamiento: `3fa075d8af7e1f04a95bd31c2870fae52ffa4480`. Run [39027076426](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39027076426) en ejecución al registrar este punto.
- Corrección de portabilidad: `c2769660078113b55246962b91fcf62c6fe197a7`. Checkout con `core.autocrlf=true` reproducía 124 CRLF y otra huella; `.gitattributes` conserva LF y la huella original. Run [39027327681](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39027327681) pendiente en la cola, sin cancelar el anterior para conservar su diagnóstico real.
- Medición HTTP Linux repetida con 800 alumnos: 12 meses (9.600 movimientos por lado) y 36 (28.800). CSV actuales en `docs/interno/ingresos-evidencia/`. Pantalla principal: 7.993/8.000 bytes y medianas 0,197489/0,450677 s. Banco 36 meses: mediana 1,002592 s; no se afirma que todas las rutas estén bajo un segundo.
- README/CHANGELOG e informe corregidos para reflejar Fase 3 integrada, sin reutilizar validaciones anteriores como aprobación final. Guía de una página: `control-ingresos-cierre-mensual.md`.
