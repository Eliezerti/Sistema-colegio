# Guía completa para importar alumnos, matrículas y representantes

1. Configura el año escolar, el mes de inicio y el vencimiento en Configuración antes de matricular.
2. Crea los grados/secciones y su capacidad. Copia sus nombres exactos a la columna grado.
3. Descarga la plantilla. Rellena únicamente la hoja Alumnos desde la fila 2; conserva sus 16 encabezados y su orden.
4. Las hojas Instrucciones, Ejemplos y Grados son de consulta y nunca se importan. Los ejemplos son ficticios.
5. Usa una fila por alumno. Para hermanos, repite exactamente los datos del representante. Si ya existe, los datos deben coincidir con su ficha.
6. No se importan pagos anteriores ni saldos históricos. Se crean mensualidades completas desde el mes de inicio de matrícula hasta el mes actual, dentro del ciclo. No hay prorrateo por días.
7. Ejemplo: base 100 USD y descuento 10 generan 90 USD al mes. Una matrícula activa desde septiembre, importada en octubre, genera septiembre y octubre si no existían.
8. Revisa las deudas que aparecen en la vista previa. Si los meses antiguos ya se pagaron, registra sus pagos reales aparte. No cambies fechas reales para ocultar deuda.
9. Guarda como .xlsx (recomendado) o CSV UTF-8. No .xls, macros, fórmulas, hojas protegidas ni columnas adicionales. Máximo 2 MB y 1000 alumnos por archivo.
10. Pulsa Revisar archivo: no guarda datos. Corrige todas las filas señaladas, vuelve a seleccionar el archivo corregido y repite la revisión.
11. Solo confirma cuando no haya errores y hayas comprobado nombres, fechas, tarifas y cargos. La confirmación guarda el lote completo; si falla una fila no se guarda ninguna.
12. La importación crea alumnos nuevos; no actualiza fichas existentes. No importes el mismo archivo dos veces.

## Las 16 columnas, en orden

| Columna | Obligatoria | Qué escribir | Ejemplo |
|---|---|---|---|
| representante_nombre | Sí | Nombre completo del representante legal. | Ana María Pérez |
| representante_cedula | Sí | Cédula propia del representante; los hermanos repiten esta misma cédula y datos. Celda como Texto. | V-12345678 |
| representante_telefono | No | Teléfono como Texto para conservar el cero inicial. | 04121234567 |
| representante_email | No | Correo del representante; puede quedar vacío. | ana@example.com |
| representante_direccion | No | Dirección del representante; puede quedar vacía. | Sector Centro, Calle 10 |
| alumno_nombre | Sí | Nombre completo del alumno; una fila por alumno. | Sofía Pérez |
| alumno_cedula | No | Cédula propia del alumno si la tiene. Nunca la del representante. Vacía: código AL automático. Celda como Texto. | Vacía |
| nacimiento | Sí | Fecha real de nacimiento. AAAA-MM-DD como Texto o fecha de Excel; sin fórmulas. | 2016-04-23 |
| grado | Sí | Nombre completo EXACTO de un grado/sección ya creado en Aula. | 1° PRIMARIA / A |
| ano_escolar | Sí | Año en que comienza el ciclo: 2026 significa 2026–2027. Entero, sin guion. | 2026 |
| mensualidad_usd | Sí | Mensualidad base en dólares, antes del descuento. Hasta dos decimales. Sin $ ni separadores de miles. | 100.00 |
| descuento_pct | No | Porcentaje entero entre 0 y 100, sin %. Vacío = 0. No es el precio final. | 10 |
| inicio_matricula | Sí | Primer día de matrícula, dentro del ciclo escolar configurado. AAAA-MM-DD o fecha Excel. | 2026-09-01 |
| fin_matricula | Sí | Último día incluido, dentro del mismo ciclo y no anterior al inicio. | 2027-08-31 |
| estado | No | activo o inactivo. Vacío = activo. Los inactivos no generan mensualidades automáticas. | activo |
| observaciones | No | Notas administrativas, sin fórmulas. | Beca aprobada del 10 % |

## Ejemplo: dos hermanos

Primero crea el grado **1° PRIMARIA / A** y otro llamado **3° PRIMARIA / A**, con capacidad suficiente. Configura año 2026 y mes de inicio septiembre. Estas fechas son un ejemplo; usa las fechas reales de tu colegio.

| Columna | Primera fila: Sofía | Segunda fila: Luis |
|---|---|---|
| representante_nombre | Ana María Pérez | Ana María Pérez |
| representante_cedula | V-12345678 | V-12345678 |
| representante_telefono | 04121234567 | 04121234567 |
| representante_email | ana@example.com | ana@example.com |
| representante_direccion | Sector Centro, Calle 10 | Sector Centro, Calle 10 |
| alumno_nombre | Sofía Pérez | Luis Pérez |
| alumno_cedula | dejar vacío | dejar vacío |
| nacimiento | 2016-04-23 | 2018-08-10 |
| grado | 3° PRIMARIA / A | 1° PRIMARIA / A |
| ano_escolar | 2026 | 2026 |
| mensualidad_usd | 100.00 | 100.00 |
| descuento_pct | 10 | 0 |
| inicio_matricula | 2026-09-01 | 2026-09-01 |
| fin_matricula | 2027-08-31 | 2027-08-31 |
| estado | activo | activo |
| observaciones | Beca aprobada del 10 % | dejar vacío |

No escribas «dejar vacío» en una celda: déjala vacía de verdad. Sofía tendrá una mensualidad de USD 90 y Luis de USD 100. Al confirmar se crea un representante y dos alumnos con códigos únicos distintos. No repitas la cédula de Ana en alumno_cedula.

## Llenarlo en Excel paso a paso

1. Abre Aula → Alumnos y matrículas → Importar Excel / CSV → Plantilla Excel.
2. Abre el archivo descargado. Si Excel muestra Vista protegida para este archivo de confianza, habilita su edición. No requiere macros.
3. En la hoja **Alumnos**, escribe desde la fila 2. No borres la fila 1 ni cambies los nombres de las columnas.
4. La plantilla prepara las columnas como texto para conservar cédulas y teléfonos. Antes de pegar números de otro archivo, selecciona esas columnas y usa Inicio → Número → **Texto**. Un cero que Excel ya eliminó no se puede recuperar automáticamente: corrígelo en el archivo.
5. Escribe las fechas como `2026-09-01`; también se aceptan fechas propias de Excel y `01/09/2026` (día/mes/año). Evita años abreviados, fechas estadounidenses y fórmulas HOY().
6. Para copiar una lista de otra hoja, usa Pegado especial → **Valores**. Las fórmulas se rechazan aunque su resultado parezca correcto.
7. Copia los grados de la hoja **Grados**. Si falta un grado, créalo en Aula y descarga de nuevo la plantilla; no lo inventes solo en Excel.
8. Para mensualidad, escribe `100` o `100.50`. Se admite `100,50` en una celda delimitada correctamente, pero el punto es el formato recomendado para CSV. Nunca `1.000,50`, `$100`, `100 Bs` ni un importe ya descontado.
9. Guarda con Archivo → Guardar como → **Libro de Excel (.xlsx)**. La carga usa la primera hoja, Alumnos. Nunca cambies el orden de las hojas.
10. Vuelve a Aula, selecciona el archivo y pulsa **Revisar archivo**. No guarda nada todavía. Verás la cantidad de alumnos, representantes y cargos que se crearían.
11. Si hay errores, corrige en Excel la fila y la columna indicadas, guarda, vuelve a seleccionar el archivo y revísalo otra vez. No confirma parcialmente filas buenas.
12. Si todo está correcto, marca la revisión de fechas, tarifas y cargos, y pulsa **Confirmar importación** una sola vez. El sistema crea un respaldo previo y guarda el lote de forma transaccional.

## Errores frecuentes

| Mensaje o problema | Cómo corregirlo |
|---|---|
| Encabezados incorrectos | Descarga la plantilla de esta versión; conserva las 16 columnas y el orden. Completa Alumnos, no Ejemplos ni Instrucciones. |
| Grado / sección inexistente | Créalo previamente y copia el nombre exacto de Grados. |
| Cédula del representante con datos distintos | Revisa su ficha. Repite exactamente nombre, teléfono, correo y dirección en los hermanos; no sobrescribe la ficha existente. |
| Documento repetido | Deja alumno_cedula vacía si el niño no tiene documento propio. No uses la cédula del representante. |
| Alumno repetido | Revisa si ya fue importado; no repitas nombre, nacimiento y representante. La importación no actualiza alumnos existentes. |
| Fechas fuera del año escolar | Para septiembre 2026–agosto 2027, inicio y fin deben quedar entre 2026-09-01 y 2027-08-31. Si tu ciclo empieza en otro mes, usa ese intervalo. |
| Descuento inválido | Entero de 0 a 100, por ejemplo 10; no 10 %, 0.10 ni 10.5. |
| Año inválido | Solo 2026, no 2026-2027, «2026/27» ni un texto. |
| Mensualidad inválida | Número sin moneda ni miles, con hasta dos decimales. |
| Fórmulas no permitidas | Copia y pega como valores; elimina fórmulas también en columnas aparentemente vacías. |
| El grado alcanzó su capacidad | Revisa los inscritos de ese ciclo y corrige capacidad o sección antes de importar. |
| Deuda mayor de lo esperado | Revisa inicio de matrícula: genera todos los meses transcurridos completos. No incorpora pagos anteriores. Registra los pagos reales por separado. |
| No hay filas | La plantilla viene vacía a propósito. Los ejemplos están en una hoja separada; escribe los alumnos reales en Alumnos. |

## CSV

La alternativa recomendada sigue siendo .xlsx. Si usas CSV, descarga la plantilla CSV y guárdala como **CSV UTF-8**. El separador de la plantilla es punto y coma. El sistema también detecta coma y tabulación. Si una dirección contiene el separador, Excel debe entrecomillarla: no armes el CSV a mano sin respetar ese formato. Las filas vacías no se importan y los errores conservan el número de fila del archivo.

## Antes de usar los saldos para cobrar

La importación no copia una contabilidad anterior. Revisa cuáles mensualidades ya se pagaron y registra esos cobros con su fecha, moneda, tasa y referencia originales. No cargues como activo un retiro sin revisar su expediente; inactivo no genera nuevas mensualidades. Un error de escritura debe corregirse desde la ficha; no vuelvas a importar el archivo completo para «actualizarlo».
