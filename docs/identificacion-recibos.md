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

## Instalador Windows 1.0.28

- Código de aplicación: commit `47341a351df1e1197af939af50f44c98fa7aa0cf`.
- [Ejecución nativa](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38209656887): 188 pruebas correctas en Python 3.12; instalación, accesos directos, ventanas normal/Pruebas, bandeja, reinstalación y desinstalación conservando datos correctas.
- Defender antes y después de ejecutar: sin detecciones, motor `1.1.26080.3`, firmas `1.459.680.0`. Este resultado no resuelve las alertas anteriores de 1.0.8/1.0.14 ni certifica la PC del usuario.
- `Aula-Colegio-Instalador-1.0.28.exe`: 20.496.235 bytes. SHA256 `7be405ab08bfa374aa7a46ef918746f646f7762f415a8c7e24ad41ca1e27aaa0`, comprobado contra el archivo descargado, el archivo de suma y el registro de los dos análisis.
- [Descarga en borrador](https://github.com/Eliezerti/Sistema-colegio/releases/tag/untagged-3ecc60c8aaea1ad5073f), requiere iniciar sesión en GitHub con acceso al repositorio.

Antes de actualizar, crea y comprueba el respaldo externo. Cierra Aula completamente e instala con la misma cuenta de Windows. Verifica un recibo existente o utiliza Aula - Pruebas para crear uno ficticio: revisa nombre, grado y código interno; el documento del alumno debe seguir en la constancia. No hace falta registrar un cobro real.

Archivos del cambio: `colegio/documents.py`, `static/app.js`, `tests/test_receipt_layout.py`, `tests/browser.cjs`, `README.md`, `CHANGELOG.md`, esta guía, notas de la compilación en `.github/workflows/windows-desktop.yml` y el ZIP de código fuente y su suma. No se alteran las instantáneas históricas, fechas, identificaciones guardadas, saldos ni importes; los PDF ya descargados mantienen su contenido anterior. No hay migración de esquema ni cambios en móvil/PWA, nómina o cifrado.
