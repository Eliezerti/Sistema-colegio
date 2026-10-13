# Datos bancarios del personal · A5

## Qué cambia

Solo Administración puede recibir banco, número y tipo de cuenta, nombre y cédula del titular del personal. La regla se aplica en el servidor con el perfil de la sesión autenticada; cambiar una pantalla o enviar role=admin no concede acceso. No requiere configurar otra contraseña.

Caja y Consulta siguen consultando nombre, cédula del empleado, cargo, teléfono, estado y salario de referencia. El listado Personal del colegio y su PDF/impresión omiten la columna bancaria. Las relaciones de pago guardadas muestran descripción, fecha, tasa y totales, sin enviar las líneas guardadas ni cuentas. Consultar su documento o un recibo de sueldo, JSON o PDF, devuelve permiso denegado. Esto incluye documentos antiguos que conservan una cuenta anterior a la ficha actual. Administración conserva sus documentos completos y sus valores originales.

Caja sigue registrando egresos y pagos de sueldo. El recibo queda guardado con la operación, pero solo Administración puede abrirlo. La pantalla de Caja confirma el registro sin abrir un documento restringido. Emitir un recibo de sueldo por separado queda reservado a Administración. Consulta sigue sin registrar movimientos. Los cobros de alumnos y sus comprobantes no cambian.

No se modifica la base, el esquema 11, datos existentes, cálculos de nómina, correlativos, transacciones, reloj, bitácora, sesiones, avisos ni respaldos. No se toca móvil/PWA ni se adelanta la tanda B o los informes de la tanda C.

## Vías revisadas

En la fuente anterior (65dd6b6), colegio/server.py:103 enviaba todas las columnas de employees y :106 enviaba el snapshot completo de las nóminas; :965 abría nóminas y recibos de sueldo sin comprobar Administración. colegio/directory_reports.py:49 imprimía banco y cuenta para todos los perfiles. El hallazgo era correcto.

Ahora colegio/staff_access.py define la proyección permitida. colegio/server.py consulta únicamente columnas autorizadas para Caja/Consulta, entrega resúmenes de nóminas mediante extracción explícita de campos y comprueba el perfil antes de cargar documentos restringidos. colegio/directory_reports.py construye el listado sin columnas bancarias para esos perfiles. static/app.js adapta las acciones a los permisos, sin usar la pantalla como protección principal.

Bitácora, copias completas y revisión de fichas archivadas ya eran exclusivos de Administración; se comprueba que continúan restringidos. Los CSV financieros, reporte diario y arqueo continúan disponibles y no añaden campos bancarios del empleado.

## Qué probar manualmente

1. Usa Aula Pruebas y datos ficticios. Entra como Administrador y crea un empleado con banco, una cuenta de 20 dígitos que comience por cero, tipo y titular.
2. Prepara una relación de pago y registra un pago de sueldo ficticio. Administración debe ver sus datos completos y descargar los PDF.
3. Crea usuarios Caja y Consulta en Configuración → Usuarios y acceso. Cierra sesión y entra por separado con cada perfil.
4. En Personal deben verse el empleado, salario y estado, sin banco ni cuenta. PDF / Imprimir debe seguir funcionando, sin columna bancaria. Las relaciones muestran sus totales, sin botón para abrir su documento.
5. En Egresos no debe aparecer Recibo de sueldo ni Emitir recibo para Caja/Consulta. Con Caja puedes registrar un pago ficticio: debe confirmar que se guardó sin abrir el recibo. Consulta no puede registrar pagos.
6. Vuelve a Administración y comprueba que el recibo y sus datos originales siguen allí. No realices cobros ficticios en la aplicación que contiene los datos reales del colegio.

## Límites

Esta restricción protege el acceso desde Aula, no archivos abiertos directamente con la cuenta de Windows. El Administrador, las copias completas descifradas y la base conservan la información bancaria. Mantén BitLocker y los permisos de la carpeta. No escribas cuentas bancarias en campos libres como concepto, referencia u observaciones: no se intenta reconocer ni censurar números introducidos manualmente allí. Los salarios, cédulas y teléfonos autorizados continúan visibles; asigna esos perfiles solo a personas autorizadas.

No se afirma prueba sobre tu PC real, tu BitLocker, otra cuenta de Windows ni una actualización desde un instalador histórico. No se usan tus fichas reales en ninguna prueba.

## Archivos y pruebas

colegio/staff_access.py, colegio/server.py, colegio/directory_reports.py, static/app.js, tests/test_staff_access.py, tests/test_directory_reports.py, tests/browser.cjs, README.md, CHANGELOG.md, docs/privilegios-personal.md/html, docs/configuracion.md/html, docs/bitacora.md/html y descargas/Aula-Windows.zip/sha256.

Se añaden seis pruebas HTTP con datos ficticios: acceso completo de Administración sin cambios de filas; estado activo/inactivo de Caja/Consulta sin campos bancarios; documentos históricos y PDF denegados aun al cambiar la cuenta; directorios/CSV/reporte diario/arqueo permitidos sin datos bancarios; Caja registra sueldo, Consulta no y Administración recupera el recibo; usuario anónimo y perfil ausente no reciben bancos. El recorrido de navegador verifica ambos perfiles, estado recibido, columnas, vista de impresión y acciones.

## Resultados de esta entrega

La primera revisión dirigida descubrió 14 pruebas: 13 correctas y una aserción nueva errónea sobre la estructura del arqueo (totals.expense_usd en vez de expense_usd). Se corrigió la prueba; no se cambió el cálculo de caja. Validación final Linux: `python -m unittest discover -s tests -v` ejecutó **287 pruebas en 156.063 s**, 284 correctas y tres exclusivas de Windows omitidas (DPAPI, exclusión entre instancias y ventana nativa de revisión). `python tests/run_browser.py`, `python tests/run_browser.py --demo` y `python tests/run_browser.py --roster`: correctos. El recorrido normal incluye la revisión de Caja y Consulta de A5 y la sesión de A3. El instalador Windows está pendiente de ejecutar y verificar; su resultado se incorpora al terminar.
