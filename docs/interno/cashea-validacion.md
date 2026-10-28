# Cashea · Aula 1.0.74 · validación de revisión

Base publicada: `324d388`, versión 1.0.73, esquema 12. Código de aplicación de esta entrega: `e5429bc58f2054dbebbe71f3926c67e84dd72f5a`, rama `cashea`. Los commits posteriores de entrega solo reúnen documentación, evidencia y ajustes del flujo de CI. No se fusiona a `main`, no se etiqueta ni se publica una versión final. La corrección documental local de `2a3d00b` se conservó; su copia de trabajo y el borrador `autonomo/ingresos-facturas` quedaron sin modificar.

## Qué se implementó

- Ventas CA- con aplicación FIFO a mensualidades, inicial real por el motor de cobros existente y cobertura financiada distinta del dinero recibido. Inicial cero sin pago ni consumo de R-. Ejemplo probado: USD 130 = USD 78 de inicial + USD 52 financiados; saldo y mora del alumno quedan en cero.
- Liquidaciones CL- por selección de órdenes, moneda e importe originales, tasa de la fecha, referencia bancaria, neto esperado y diferencias contra neto y bruto. La comisión no genera egreso automáticamente. La inicial conserva su método real; CL- se registra como transferencia y no aumenta el arqueo de efectivo.
- Revisiones antes de confirmar, idempotencia por usuario/contenido, permisos en servidor, CSRF, reloj, días cerrados y cadena de bitácora. Administración configura y anula; Caja registra; Consulta lee. Una inicial vinculada se anula desde su orden, no desde el botón genérico. Para anular una orden liquidada primero se anula CL-.
- PDF CA-/CL-, bloque Cashea solo en R- nuevos, cobertura en estados de cuenta y solvencias, convenios, morosidad y cierre. Informes en pantalla, PDF, CSV y XLSX; pendientes agrupados por semana también en CSV/XLSX. El listado para Cashea usa AL-, sin nombre, cédula ni nacimiento del menor. El modo Pruebas marca sus documentos y exportaciones «PRUEBA SIN VALIDEZ».
- Informe mensual Cashea al corte por fechas de venta, recepción y anulación; no depende solamente del estado actual. Los demás componentes del informe conservan su contrato anterior.

Los valores iniciales son miércoles estrictamente siguiente, factura obligatoria, comisión 0 % y cero días de gracia. Son editables por Administración. El porcentaje de inicial es una calculadora: manda lo realmente recibido. Cambiar comisión o calendario no recalcula órdenes anteriores. No hay conexión con Cashea, bancos o SENIAT ni emisión automática de números fiscales. [Guía del usuario](../cashea.md) · [Diseño previo e inventario](../../DISENO_CASHEA.md).

## Migración, respaldo y conservación

Esquema 13 aditivo: cuatro tablas de negocio y una tabla técnica `cashea_requests` para idempotencia de todas las escrituras nuevas. R-/E-/AL- conservan su numeración; CA-/CL- tienen sus propios pisos. La instalación nueva mantiene todas las tablas de negocio, usuarios, bitácora y tablas Cashea vacías; los pisos empiezan en cero y los primeros números son 1.

La base activa verifica integridad, referencias y cadena; crea y comprueba la copia previa de esquema 12 y, si tiene segundo destino configurado, exige allí una copia cifrada verificada antes del DDL. Sin llaves o con un fallo de respaldo no migra. Se probaron terminaciones reales en cinco límites de migración y dos límites de venta: queda el estado anterior íntegro o la operación completa.

Las copias privadas de conversión, restauración y consulta se vuelven a verificar, sin WAL activo, antes de migrar. Conservan una copia previa dentro del temporal y no publican en el destino externo que figura en el respaldo antiguo. No requieren el almacén de llaves de la escuela de origen. Ese contexto es interno, no una preferencia ni un parámetro HTTP. La prueba incluye un respaldo 12 con segundo destino configurado, conversión, consulta, restauración, origen intacto y destino externo sin escrituras. Otra prueba comprueba que la migración activa sigue detenida si no puede cifrar su copia externa.

El fixture `tests/fixtures/cashea/desktop-1.0.73-ficticio.sqlite3` se generó mediante las APIs del código publicado 324d388; no se falsificó su versión mediante PRAGMA. Contiene cinco alumnos y tres representantes marcados FICTICIO, sin nacimientos ni sesiones, y un marcador de contraseña sin credencial utilizable. Su manifiesto verifica la huella. La referencia se obtuvo con el código 1.0.73: cobrado USD 227, egresos USD 15, neto USD 212 y deuda USD 241. La migración conserva esos importes, movimientos, snapshots y el prefijo completo de bitácora y sus enlaces.

## Resultados reales

Linux, 28 de octubre de 2026 (commit e5429bc):

| Comando | Resultado real | Duración |
|---|---|---|
| `python -m unittest discover -s tests -v` | 345 ejecutadas; 342 correctas y 3 exclusivas de Windows omitidas | 268,283 s de unittest |
| `python tests/run_browser.py` | salida 0; Cashea, sesión, flujos existentes y consulta correctos | 56,020 s |
| `python tests/run_browser.py --demo` | salida 0; aislamiento, marca de prueba y limpieza correctos | 17,324 s |
| `python tests/run_browser.py --roster` | salida 0; importación/exportación y origen íntegro | 16,353 s |

Salida de unittest conservada literalmente:

```text
Ran 345 tests in 268.283s

OK (skipped=3)
```

Entorno Linux: Python 3.12.14, SQLite 3.53.1, cryptography 50.0.0 y Playwright Node 1.62.1. No se instalaron dependencias nuevas del producto.

Windows Server 2022, Python 3.12.10, 28 de octubre de 2026: [ejecución definitiva, intento 2](https://github.com/Eliezerti/Sistema-colegio/actions/runs/40602264590/attempts/2), mismo commit e5429bc. Resultado del trabajo: **success**.

| Comando o comprobación | Resultado real |
|---|---|
| `python -m unittest discover -s tests -v` | 345 correctas, sin omisiones; 568,669 s |
| `python tests/run_browser.py` | correcto; incluye flujo Cashea y consulta |
| `python tests/run_browser.py --demo` | correcto; aislamiento, marca y limpieza |
| `python tests/run_browser.py --roster` | correcto; importación/exportación |
| Compilación y empaquetado 1.0.74 | correctos; inventario sin módulos excluidos |
| Instalador en Windows limpio | instalación, accesos, ventanas, bandeja y desinstalación conservadora correctos |
| PDF e impresión nativa | WebView2 y selector de Windows correctos; se distingue de una impresora física |
| Consulta cifrada en WebView2 | aviso permanente, perfil Consulta y eliminación del temporal correctos |
| Actualización con instalador real 1.0.73 → 1.0.74 | datos, totales y PDF anterior idénticos antes de Cashea; CA/R/CL, VES, saldo/mora cero e integridad correctos |

Salida de unittest conservada literalmente:

```text
Ran 345 tests in 568.669s

OK
```

El primer intento tuvo dos errores WinError 10053. El segundo pasó **sin cambiar código, pruebas ni tiempos de espera**; no se atribuye una causa que no se haya comprobado. Se conservan los dos bloques en [cashea-windows-pruebas.txt](cashea-windows-pruebas.txt). Los registros completos están en GitHub Actions.

[Instalador de revisión y ZIP del código validado](https://github.com/Eliezerti/Sistema-colegio/actions/runs/40602264590/artifacts/12811146395) · [Evidencia Windows](https://github.com/Eliezerti/Sistema-colegio/actions/runs/40602264590/artifacts/12809953895). El ZIP final de revisión con esta documentación se genera después de este resultado; su manifiesto identifica el commit de documentación y el diff completo desde 324d388.

La salida completa de Linux está en [cashea-pruebas.txt](cashea-pruebas.txt); el resultado y el primer fallo de Windows se conservan en [cashea-windows-pruebas.txt](cashea-windows-pruebas.txt). Se conservan las trazas esperadas de pruebas negativas; no se filtran para aparentar un resultado correcto.

Las 314 pruebas originales conservan sus identificadores. Se agregaron 31 casos. Las adaptaciones anteriores se limitan a esperar esquema 13 tras `initialize`, ampliar tablas/pisos de la instalación vacía y añadir rutas al contrato de permisos. El helper de fixtures sintéticos anteriores a A4 retira también los objetos Cashea y confirma su transacción; solo opera en bases desechables. No se eliminó ningún caso ni se redujeron sus comprobaciones financieras o de permisos. Las tres omisiones de Linux corresponden a DPAPI, mutex/enfoque de ventanas y diálogo nativo de restauración de Windows.

## Fallos encontrados durante el trabajo

- Una llamada al generador PDF usaba un método inexistente; se corrigió y se repitió el flujo HTTP.
- Un botón Cancelar dentro del panel de ajustes nuevo interfería con la recuperación de borradores de sesión; se corrigió el formulario nuevo y se repitió el navegador, conservando la prueba original.
- El helper sintético de versiones antiguas necesitaba confirmar su nueva transacción de preparación. Se corrigió el helper de pruebas, no la migración productiva ni las protecciones de bitácora.
- Una prueba nueva intentaba cifrar directamente la base activa con WAL; Aula la rechazó correctamente. La prueba pasó a exportar una copia consistente, como exige el producto. Se mantuvo el bloqueo de bases activas.
- Se reprodujo y corrigió la migración de una copia antigua que intentaba usar el segundo destino y las llaves de la escuela original. Se añadieron pruebas tanto de portabilidad como de conservación del requisito de cifrado en la actualización activa.
- El primer intento Windows de e5429bc ejecutó 345 casos y terminó con dos errores de transporte `WinError 10053`, en rechazo de escrituras de consulta y rutas retiradas. El segundo intento pasó con el mismo código y las mismas pruebas, sin omisiones ni ampliación de tiempos de espera. La ejecución anterior eee07dd había completado 343 casos sin omisiones y la instalación/actualización nativa. Los resultados definitivos se indican arriba; no se confunden versiones.

## Ajuste opcional de CI, separado

Se verificó el hallazgo del flujo `correccion-alumnos.yml`: [ejecución 39896577102](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39896577102), trabajo 120228316424, fallo exclusivo en «Conservar evidencia». El registro dice: `The rootDirectory: D:\a\Sistema-colegio\Sistema-colegio is not a parent directory of the file: D:\a\_temp\aula-recibo-native\comprobante-dos-copias.pdf`.

El ajuste reúne archivos del repositorio, temporales y registros de Windows en `evidencia-correccion/` antes de subirlos. Está en un commit propio. El nuevo flujo Cashea usa el mismo patrón de carpeta única. No se ejecuta ni se modifica otra rama para dar por verde el flujo histórico.

## Entrega y comprobaciones manuales

El ZIP de revisión contiene el diff binario completo desde 324d388, los archivos modificados y su manifiesto; incluye solamente el fixture ficticio declarado, sin bases del usuario, `.env`, almacenes de llaves, ejecutables ni secretos reales. El empaquetador comprueba las rutas, los patrones de secretos, el fixture, el inventario ZIP y el límite de 20 MB. Las contraseñas de los tests son deliberadamente ficticias. La búsqueda de patrones no sustituye una revisión humana.

El instalador, tras pasar la comprobación nativa definitiva, es de revisión y se obtiene del artefacto de Windows señalado en los resultados. El ZIP con la evidencia final se publica como artefacto aparte, después de documentar los resultados, sin cambiar el código de aplicación validado.

No se ejecutaron impresión en la impresora física del colegio ni una liquidación bancaria real: no hay acceso a ese equipo ni a movimientos reales. Quedan para el colegio una venta piloto, revisar el depósito y las comisiones con el contador, y comprobar la impresión física con datos ficticios antes de usar el flujo en producción. La prueba virtual de impresión Windows se distingue de esas comprobaciones. Firma digital, nómina y el borrador de ingresos/facturas están fuera de esta entrega.
