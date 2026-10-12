# Identificación del alumno en el recibo de pago

La identificación escolar guardada en la ficha se conserva en la constancia de matrícula. El recibo de pago muestra nombre del alumno, grado/sección y código interno de Aula, como AL-000038. La cédula/documento del alumno no se utiliza como reemplazo del código interno.

Esta regla se aplica a la vista del recibo, la impresión desde Aula y los PDF A4, media carta y tickets de 58 y 80 mm. Los datos del representante se mantienen.

Si una instantánea antigua no tiene código interno, el recibo indica «Código interno no registrado»; no toma el código actual ni modifica la instantánea histórica. No se cambian importes, pagos, saldos ni documentos del alumno. Un PDF descargado antes de esta actualización conserva su contenido; volver a descargar el mismo recibo no registra otro cobro.

Para comprobar la presentación sin registrar cobros reales, utiliza Aula - Pruebas. Si ya existe un pago, consultar su recibo tampoco genera otro pago.

El nombre del campo y la distinción entre cédula escolar y cédula de identidad se revisarán por separado: este cambio solo evita imprimir la identificación del alumno en el recibo de pago.

## Validación

- `python -m unittest discover -s tests -v`: 188 pruebas en Linux, 187 correctas y una exclusiva de Windows omitida.
- `python tests/run_browser.py`: correcto, incluyendo documento ausente en la vista e impresión para instantáneas con código presente, ausente, vacío y nulo.
- `python tests/run_browser.py --demo`: correcto.
- `python tests/run_browser.py --roster`: correcto.

Todas las pruebas utilizan bases temporales. No se han registrado cobros ni modificado alumnos reales. La comprobación de la instalación en Windows se realiza por separado al generar el instalador.
