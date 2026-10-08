"""One source for the Excel instructions and in-app field guide."""
FIELDS = [
 ('representante_nombre','Sí','Nombre completo del representante legal.','Ana María Pérez'),
 ('representante_cedula','Sí','Cédula propia del representante; los hermanos repiten esta misma cédula y datos. Celda como Texto.','V-12345678'),
 ('representante_telefono','No','Teléfono como Texto para conservar el cero inicial.','04121234567'),
 ('representante_email','No','Correo del representante; puede quedar vacío.','ana@example.com'),
 ('representante_direccion','No','Dirección del representante; puede quedar vacía.','Sector Centro, Calle 10'),
 ('alumno_nombre','Sí','Nombre completo del alumno; una fila por alumno.','Sofía Pérez'),
 ('alumno_cedula','No','Cédula propia del alumno si la tiene. Nunca la del representante. Vacía: código AL automático. Celda como Texto.',''),
 ('nacimiento','Sí','Fecha real de nacimiento. AAAA-MM-DD como Texto o fecha de Excel; sin fórmulas.','2016-04-23'),
 ('grado','Sí','Nombre completo EXACTO de un grado/sección ya creado en Aula.','1° PRIMARIA / A'),
 ('ano_escolar','Sí','Año en que comienza el ciclo: 2026 significa 2026–2027. Entero, sin guion.','2026'),
 ('mensualidad_usd','Sí','Mensualidad base en dólares, antes del descuento. Hasta dos decimales. Sin $ ni separadores de miles.','100.00'),
 ('descuento_pct','No','Porcentaje entero entre 0 y 100, sin %. Vacío = 0. No es el precio final.','10'),
 ('inicio_matricula','Sí','Primer día de matrícula, dentro del ciclo escolar configurado. AAAA-MM-DD o fecha Excel.','2026-09-01'),
 ('fin_matricula','Sí','Último día incluido, dentro del mismo ciclo y no anterior al inicio.','2027-08-31'),
 ('estado','No','activo o inactivo. Vacío = activo. Los inactivos no generan mensualidades automáticas.','activo'),
 ('observaciones','No','Notas administrativas, sin fórmulas.','Beca aprobada del 10 %'),
]

STEPS = [
 'Configura el año escolar, el mes de inicio y el vencimiento en Configuración antes de matricular.',
 'Crea los grados/secciones y su capacidad. Copia sus nombres exactos a la columna grado.',
 'Descarga la plantilla. Rellena únicamente la hoja Alumnos desde la fila 2; conserva sus 16 encabezados y su orden.',
 'Las hojas Instrucciones, Ejemplos y Grados son de consulta y nunca se importan. Los ejemplos son ficticios.',
 'Usa una fila por alumno. Para hermanos, repite exactamente los datos del representante. Si ya existe, los datos deben coincidir con su ficha.',
 'No se importan pagos anteriores ni saldos históricos. Se crean mensualidades completas desde el mes de inicio de matrícula hasta el mes actual, dentro del ciclo. No hay prorrateo por días.',
 'Ejemplo: base 100 USD y descuento 10 generan 90 USD al mes. Una matrícula activa desde septiembre, importada en octubre, genera septiembre y octubre si no existían.',
 'Revisa las deudas que aparecen en la vista previa. Si los meses antiguos ya se pagaron, registra sus pagos reales aparte. No cambies fechas reales para ocultar deuda.',
 'Guarda como .xlsx (recomendado) o CSV UTF-8. No .xls, macros, fórmulas, hojas protegidas ni columnas adicionales. Máximo 2 MB y 1000 alumnos por archivo.',
 'Pulsa Revisar archivo: no guarda datos. Corrige todas las filas señaladas, vuelve a seleccionar el archivo corregido y repite la revisión.',
 'Solo confirma cuando no haya errores y hayas comprobado nombres, fechas, tarifas y cargos. La confirmación guarda el lote completo; si falla una fila no se guarda ninguna.',
 'La importación crea alumnos nuevos; no actualiza fichas existentes. No importes el mismo archivo dos veces.',
]
