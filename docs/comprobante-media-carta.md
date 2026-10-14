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

Validación final Linux: unittest completo, **297 descubiertas en 165,123 s, 294 correctas y tres exclusivas de Windows omitidas**. Navegadores normal, `--demo` y `--roster`: PASS. PDF directo y salida de impresión: una página de 396 × 612 puntos. En hoja carta: una página de 612 × 792 puntos, contenido con idénticas posiciones y tamaños de texto, contenido dentro de media carta. La primera suite completa detectó dos aserciones del formato anterior (orientación horizontal y razón social en una línea); se actualizaron al contrato vertical sin omitir verificaciones y se repitió toda la suite. La repetición intermedia se interrumpió para corregir una sangría; no se presenta como validación.

Primera revisión Windows 1.0.54: 297 pruebas correctas en 383,614 s, instalación y PDFs nativos de una página correctos. La verificación independiente detectó desplazamiento del número R- entre media carta y carta por reglas de pantalla estrecha; entrega detenida. Se fijan alineación, columnas y márgenes de impresión independientemente del ancho. Los cuatro recorridos Linux se repiten con el ajuste final; la prueba de navegador compara también operadores de texto y transformaciones de los PDFs reales. Entrega Windows final: pendiente de completar la repetición del workflow.
