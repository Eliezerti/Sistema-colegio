# Comprobante de pago en media carta vertical

Formato: **396 × 612 puntos**, **13,97 × 21,59 cm**, orientación vertical. La opción `half-letter` conserva su nombre para compatibilidad, pero utiliza la nueva orientación. La interfaz y la descarga directa sin parámetro usan media carta; A4 y tickets permanecen disponibles.

El encabezado, los espacios entre bloques y las firmas se compactan sin alterar la información del pago. Se conserva el número R-, representante, alumno y grado, conceptos, importes, saldo guardado al cobrar, método y referencia. No se imprime código interno AL- ni cédula escolar. El cambio solo afecta la presentación: no registra pagos, cambia cálculos, correlativos, instantáneas o esquema, ni modifica las protecciones A1–A5. B3 sigue pendiente; esta guía documenta exclusivamente el comprobante solicitado.

## Imprimir

Selecciona **Media carta · vertical**. El PDF tiene tamaño físico real y fuentes incorporadas. En Windows selecciona **Tamaño real / escala 100 %**, desactiva Ajustar a página y los encabezados/pies del navegador. Si el controlador no ofrece media carta, utiliza una hoja carta a escala 100 %: el recibo conserva sus 13,97 × 21,59 cm y ocupa la superficie de media hoja. Carta horizontal permite colocarlo en una mitad lateral. Revisa la vista previa antes de imprimir.

La hoja preparada por Imprimir tiene ancho fijo de 396 puntos; seleccionar papel carta no estira el documento. No se cambia la configuración permanente de ninguna impresora. La escala y el papel del diálogo/controlador deben permanecer al 100 %.

Los cobros habituales se comprueban en una página, incluyendo tres conceptos, dirección, saldo y observaciones breves. Los documentos extensos conservan todo su contenido mediante continuación, en vez de recortarlo o reducirlo a texto ilegible; A4 sigue disponible para esos casos.

## Validación

Datos exclusivamente ficticios, servidores y bases temporales. La prueba Python verifica 396 × 612 puntos, una página y los datos de tres conceptos en USD y Bs. El navegador verifica PDF e impresión, una página, ancho físico y que cambiar de media carta a carta mantenga las dimensiones del contenido a escala 1.

El autodiagnóstico del instalador Windows imprime el mismo marcado del comprobante mediante WebView2, sobre media carta y carta, con `ScaleFactor = 1.0`, sin encabezados/pies adicionales. Comprueba dimensiones físicas y página única, sin registrar pagos en una base real. La prueba de impresión física depende de la impresora del colegio y no se presenta como ejecutada por el runner.

Validación final Linux: unittest completo, **297 descubiertas en 170,788 s, 294 correctas y tres exclusivas de Windows omitidas**. Navegadores normal, `--demo` y `--roster`: PASS. PDF directo y salida de impresión: una página de 396 × 612 puntos. En hoja carta: una página de 612 × 792 puntos, contenido con idénticas posiciones y tamaños de texto, contenido dentro de media carta. La primera suite completa detectó dos aserciones del formato anterior (orientación horizontal y razón social en una línea); se actualizaron al contrato vertical sin omitir verificaciones y se repitió toda la suite. La repetición intermedia se interrumpió para corregir una sangría; no se presenta como validación.

Primera revisión Windows 1.0.54: 297 pruebas correctas en 383,614 s, instalación y PDFs nativos de una página correctos. La verificación independiente detectó desplazamiento del número R- entre media carta y carta por reglas de pantalla estrecha; entrega detenida. Se fijan alineación, columnas y márgenes de impresión independientemente del ancho. Los cuatro recorridos Linux se repiten con el ajuste final; la prueba de navegador compara también operadores de texto y transformaciones de los PDFs reales. La segunda revisión Windows 1.0.56 conservó tamaños de letra, pero la regla adaptable del saldo cambiaba su disposición entre papeles; entrega también detenida. Se fija el saldo en fila para impresión y se recupera la igualdad completa de la disposición en la prueba de navegador, además de los operadores PDF. Las cuatro suites Linux pasan nuevamente con esta corrección. La entrega final se valida a continuación.


## Entrega final 1.0.57

[Windows 38615974376](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38615974376), fuente `eb414be`: **297 pruebas correctas en 419,073 s, sin omisiones**. Instalación, ventanas, bandeja, actualización/desinstalación y conservación de datos correctas. PDF del comprobante y WebView2: **una página de 396 × 612 puntos**. Sobre carta: una página de 612 × 792 puntos y contenido limitado a media carta, con **idénticos textos, posiciones y tamaños**, sin identificadores escolares. [PDFs ficticios guardados](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38615974376/artifacts/11920472674).

Defender antes y después sin detecciones; motor 1.1.26090.9, firmas 1.461.26.0. Instalador descargado y comprobado: **21.248.716 bytes**, SHA-256 `6b85f2d2d1a3ba9de0d22656f86c3f9bf2067da1fef796b668dcd7885cf03b21`, coincidente con el sidecar y ambos análisis del runner. [Instalador 1.0.57 en borrador](https://github.com/Eliezerti/Sistema-colegio/releases).

La guía incluida en el EXE explica tamaño y uso; esta evidencia final y la fuente ZIP actualizada se añaden después de compilar. Se comprobó el motor nativo de Windows Server 2022; no se ejecutó impresión física ni revisión del controlador de la impresora del colegio. Mantén Tamaño real / 100 % al imprimir. Los cambios están en el PR de revisión; main no se modificó. B3 sigue pendiente.


## ORIGINAL y COPIA en una hoja

Elige **Carta horizontal · 2 copias verticales**. El PDF y la impresión usan una hoja carta de **792 × 612 puntos**: a la izquierda **ORIGINAL** y a la derecha **COPIA**, cada una de 396 × 612 puntos al **100 %**, sin reducir ni ampliar. No se añaden destinatarios a los rótulos. Ambas tienen los mismos datos y número R-; no se registra un segundo pago.

Se acortan los márgenes a unos 5 mm y se aproxima el inicio al borde superior. El pie acompaña al contenido y se amplía la zona libre antes de cada firma a unos 11 mm. El PDF individual continúa en media carta vertical; A4 y tickets siguen disponibles.

En el diálogo de impresión selecciona Carta horizontal, Tamaño real / 100 %, sin Ajustar. Desactiva Encabezados y pies del navegador para quitar fecha, título, URL y contador, visibles en la captura de revisión. Esos textos son añadidos por el navegador y no pertenecen al recibo; Aula no cambia las preferencias permanentes del controlador.

Validación Linux de ORIGINAL/COPIA: 299 descubiertas en 167,031 s, 296 correctas y tres exclusivas de Windows omitidas. Navegadores normal, --demo y --roster: PASS; incluye dos copias completas en una página, títulos ORIGINAL y COPIA, espacio para firmas y conservación del pago al cambiar de formato. La primera ejecución completa detectó una aserción ligada al salto de línea de la razón social; la prueba ahora verifica el nombre completo impreso y la repetición de toda la suite fue correcta. Nuevo instalador Windows en validación; 1.0.57 corresponde a la entrega anterior.
