# Instalador con avisos de cobranza · 1.0.74 de revisión

01/11/2026 · Pedido posterior a la revisión de código: entregar el `.exe` actualizado. Rama `cashea`, sin fusionar a main ni crear una publicación final. El producto conserva exactamente el código de los avisos revisados; los cambios posteriores son pruebas y empaquetado.

## Comprobaciones reales previas

- [Primera ejecución de Windows](https://github.com/Eliezerti/Sistema-colegio/actions/runs/41313229093): **388 pruebas correctas en 796,270 s, sin omisiones** y compilación del `.exe` correcta. El navegador se detuvo en la comparación del portapapeles: Windows devuelve `\r\n`, mientras textarea y URL usan `\n`. Se conserva el diagnóstico. Las comprobaciones de instalación de esa ejecución no llegaron a ejecutarse y no se entregó su instalador.
- `805a815`: se corrige **solo la prueba** para exigir la cadena completa en su representación nativa: CRLF en Windows, LF en Linux; se siguen comprobando todos los caracteres, acentos, emoji, salto y URL. No se cambia el texto del producto, el copiado, el API ni las sesiones; no se excluye la comprobación ni se amplían tiempos.
- [Repetición de los tres navegadores de Windows](https://github.com/Eliezerti/Sistema-colegio/actions/runs/41318652019): **normal, Pruebas e importación correctos**. También se repitió el normal en Linux, salida 0. La ejecución anterior de las cuatro suites de Linux sigue registrada en [avisos-validacion.md](avisos-validacion.md): 388, con tres omisiones nativas; los tres navegadores correctos.
- `bee48af`: la validación de actualización desde 1.0.73 exige además servir el JS y preparar/marcar el aviso **desde Aula.exe instalado**, no desde el repositorio. Comprueba cinco tipos, mes/importe/Cashea, reintento único, seguimiento, bitácora, caja y registros financieros idénticos y mismo PDF histórico. Se conserva el control que limita estas pruebas a Windows desechable sin datos previos.

## Compilación y entrega

[Ejecución del instalador](https://github.com/Eliezerti/Sistema-colegio/actions/runs/41318825940), fuente `bee48af`: **terminó correctamente**. Windows Server 2022, Python 3.12: **388 pruebas en 568,150 s, correctas sin omisiones**, y los tres navegadores correctos. Instalación, reinstalación y desinstalación conservan datos y respaldo; impresión WebView2 y consulta cifrada correctas. La actualización real desde 1.0.73 conserva las fichas, importes y bytes del PDF anterior, y comprueba Cashea, anticipo y aviso desde el ejecutable instalado, con bitácora íntegra.

La impresión nativa comprobó una página de 396 × 612 puntos, media carta sobre carta de 612 × 792 y ORIGINAL/COPIA de 792 × 612, con escala predeterminada. No se cambia su diseño ni sus cálculos. El control del aviso instalado pasó: módulo y JS incluidos, cinco tipos, mes/total/Cashea, marca manual idempotente y ninguna diferencia en dinero ni PDF histórico.

El artefacto de entrega se llama **Aula-Instalador-1.0.74-avisos** y debe contener únicamente **Aula-Colegio-Instalador-1.0.74.exe**. Solo se sube después de todas las comprobaciones. El ZIP de código es una descarga distinta.

**[Descargar instalador](https://github.com/Eliezerti/Sistema-colegio/actions/runs/41318825940/artifacts/13089205987)**. Descarga verificada: un solo `.exe`, CRC correcto y cabeceras MZ/PE de Windows; ZIP de 19.269.721 bytes, instalador de 19.771.158 bytes. [Resultados](avisos-instalador-pruebas.txt) y [artefacto de evidencia íntegra](https://github.com/Eliezerti/Sistema-colegio/actions/runs/41318825940/artifacts/13088538686).

Cierra Aula e instala el `.exe` usando la misma cuenta de Windows. Conserva la carpeta de datos; no la reemplaces ni importes datos de prueba. Haz tu respaldo habitual antes de actualizar. No se cambian esquema, saldos, recibos ni correlativos por este ajuste. La impresión en la impresora del colegio y la entrega real en WhatsApp requieren al usuario; no se presentan como verificadas en el runner.
