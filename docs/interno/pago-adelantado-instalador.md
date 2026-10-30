# Instalador de pagos adelantados · seguimiento

Solicitud expresa del colegio: entregar el ejecutable instalador, además del código de revisión. Aula 1.0.74, rama `cashea`, esquema 14. El producto permanece sin cambios desde `2110705`; no se fusiona a main ni se crea una publicación final.

## Primera ejecución de entrega

[Windows 41136349136](https://github.com/Eliezerti/Sistema-colegio/actions/runs/41136349136), job 124339645246, revisión `14e2825`.

- `python -m unittest discover -s tests -v`: **371 correctas, sin omisiones, en 650,085 s**.
- Compilación e inventario B2 correctos.
- Navegador: Cashea, anticipos e impresión correctos; después se detuvo en `tests/session_browser.cjs:31`, esperando `state.settings.session_idle_minutes === '5'`, con el tiempo original de 30 segundos.
- La prueba editaba Configuración sin esperar a que la navegación terminara de reemplazar el formulario. Se corrigió la sincronización con el estado devuelto por la navegación; se verifica también que el POST real envíe `idle_minutes='5'` y responda 200. Se ejerce una demora de navegación controlada de 250 ms. No se cambia `session.js`, no se amplían tiempos ni se eliminan aserciones.
- La prueba completa de navegador corregida terminó correctamente en Linux, incluida recuperación de sesión, borradores y consulta.
- No se entregó el instalador de esta ejecución fallida. Los logs originales permanecen en Actions.

## Ejecución definitiva

[Windows 41138223826](https://github.com/Eliezerti/Sistema-colegio/actions/runs/41138223826), job 124345855102, revisión `0914dd6`. **Resultado: success. Todas las etapas obligatorias aprobadas.**

La entrega exige: 371 pruebas, los tres navegadores, instalación/reinstalación/desinstalación conservando base y respaldos, impresión nativa WebView2, consulta cifrada, actualización real desde 1.0.73 y pruebas nuevas de cobro adelantado y Cashea **desde el ejecutable instalado**. El artefacto del colegio contendrá solamente `Aula-Colegio-Instalador-1.0.74.exe` y solo se publicará si pasa todo.

La impresión física en la impresora del colegio continúa como comprobación manual. No se trabaja en firma digital ni se publican huellas del instalador.

## Entrega aprobada

- **[Descargar instalador de pagos adelantados](https://github.com/Eliezerti/Sistema-colegio/actions/runs/41138223826/artifacts/13017567946)**. El ZIP contiene únicamente `Aula-Colegio-Instalador-1.0.74.exe`.
- `python -m unittest discover -s tests -v`: **371 correctas, sin omisiones, 658,903 s**. Normal, Pruebas e importación: código 0.
- Instalación limpia, reinstalación y desinstalación correctas; base y respaldo conservan sus bytes. Accesos, ventanas y bandeja correctos.
- Impresión nativa WebView2: media carta 396×612, media carta en carta 612×792 y dos copias 792×612; una página y escala predeterminada en cada caso.
- Consulta cifrada: aviso permanente, perfil Consulta y eliminación del temporal correctos.
- Actualización real 1.0.73 → 1.0.74: datos, totales y PDF histórico idénticos; integridad, claves foráneas y bitácora correctas.
- Anticipo normal y Cashea desde **Aula.exe instalado**: cargo futuro único, recibo de una página, fecha real, reintento único, caja y verificación de datos correctos.
- [Salida real del runner](pago-adelantado-instalador-pruebas.txt). La impresión física en la impresora del colegio queda como comprobación manual.

Para actualizar: crea un respaldo actual, cierra Aula y Pruebas, extrae el ZIP y ejecuta el archivo de tipo **Aplicación**, con la misma cuenta de Windows y sobre la instalación actual. No necesitas cambiar la carpeta de datos. Al abrir, usa tu usuario habitual. En Caja y cobros → Registrar pago aparecen los meses Por adelantado.
