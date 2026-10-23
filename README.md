# Aula · Control de mensualidades

Aula administra alumnos, representantes, grados, mensualidades, cobros y egresos mínimos del colegio en una PC Windows. Incluye tasas BCV, descuentos, convenios, pase de año, cierre de caja, reportes, importación de matrículas y Archivo de la institución. Personal y Nómina están retirados.

## Comenzar y trabajar

Una instalación nueva comienza como «Mi colegio», sin registros ni usuarios predeterminados. El primer inicio pide crear el administrador y revisar año escolar, mes de inicio y vencimiento. Los primeros recibos, egresos y alumnos empiezan en 1. Pruebas utiliza una carpeta temporal separada y se elimina al cerrar.

- [Puesta en producción](docs/puesta-en-produccion.md): instalar, configurar, importar y hacer el piloto.
- [Importar alumnos](docs/guia-importacion.md): plantilla vacía, validación e importación revisada.
- [Mantenimiento](docs/mantenimiento.md): operación diaria, respaldo, actualización y recuperación.
- [Comprobantes](docs/comprobante-media-carta.md): media carta vertical y ORIGINAL/COPIA en carta horizontal, con impresión normal.
- [Archivo de la institución](docs/archivo-institucion.md): conservar historia y revisar un borrado permitido.

Una matrícula duplicada se revisa en **Alumnos y matrículas → Editar → Corrección de fichas creadas por error → Eliminar esta ficha**. Solo Administración puede borrar la ficha, sus constancias y sus cargos sin pagos, con contraseña, código del alumno y respaldo previo verificado. No hace falta archivarla. Los pagos, documentos financieros, convenios y otros vínculos protegidos bloquean esta corrección. Se conservan la bitácora y los respaldos anteriores.

Para la limpieza excepcional y única de cobros ficticios, estados de cuenta, solvencias y cierres de prueba antes de producción, consulta [Empezar recibos en R-000001](docs/limpieza-cobros-prueba.md). No reemplaces la carpeta de datos ni uses esta operación con pagos reales.

## Consulta y reportes

La pantalla principal descarga resúmenes completos y pocos movimientos recientes; solicita el historial cuando abres otras pantallas. Los saldos conservan todos los cargos y pagos. Reportes ofrece morosidad por grado y cierre mensual PDF/CSV, con monedas y métodos separados y sin datos personales de alumnos en el informe mensual. El pendiente de ese informe es actual, con el corte indicado; no reconstruye una foto histórica.

Para mirar un respaldo desde otra PC utiliza [Abrir copia en solo lectura](docs/consulta-copias.md). Trabaja en un temporal, muestra su fecha y bloquea escrituras en el servidor y SQLite. No restaura la copia ni genera mensualidades. El acceso privado por Tailscale está retirado; para soporte usa el escritorio remoto de Windows.

## Protección y recuperación

Las copias nuevas externas y descargadas están cifradas. El segundo destino conserva 90 frecuentes, 60 diarias y 24 mensuales. Los cierres escolares permanentes no se eliminan automáticamente. Se recuerda probar una copia externa después de 35 días. El aviso se puede ocultar por 7 días en ese navegador, sin ocultar errores de respaldo. Una prueba externa correcta actualiza el aviso inmediatamente. Guarda por separado la contraseña, la recuperación del respaldo y la recuperación de BitLocker.

Consulta las guías de [cifrado](docs/cifrado-respaldos.md), [restauración segura](docs/restauracion-segura.md), [sesiones](docs/sesiones-acceso.md) y [bitácora](docs/bitacora.md). Si otros intentos bloquean un ingreso, Administración puede generar un código local de un uso desde Inicio de Windows, con su contraseña actual. El límite contra fuerza bruta se conserva.

El esquema sigue en 12. No se reinician correlativos existentes ni se cambian importes históricos. Los egresos antiguos de categoría Nómina se conservan; la categoría no se admite en nuevos egresos. Se mantienen A1–A5, WAL/FULL, permisos, CSRF y respaldos verificados. La actualización de una base antigua conserva una copia previa; no reutiliza números de recibos al restaurar.

## Validación

Las [pruebas físicas del colegio](docs/pruebas-fisicas.md) requieren tu equipo: corte eléctrico, impresora y otra PC. La evidencia técnica de la tanda se conserva [en el repositorio](https://github.com/Eliezerti/Sistema-colegio/blob/tanda-d/docs/tanda-d.md), fuera del instalador. Los [ajustes 1.0.69](docs/ajustes-1.0.69.md) documentan el recordatorio y la impresión normal. Firma digital y publicación de huellas están fuera de esta tanda.

Comandos de referencia: `python -m unittest discover -s tests -v`, `python tests/run_browser.py`, `python tests/run_browser.py --demo` y `python tests/run_browser.py --roster`.
