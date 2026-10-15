# Retiro de Personal y Nómina · inventario y diseño

Inventario de solo lectura sobre `9127a57`, rama local `work`, limpia al comenzar. Se mostraron estado, rama y últimos diez commits. La autorización posterior del usuario permite completar las tres fases sin pausas. No se cambió de rama ni se modificó main.

## Mapa de la versión anterior

Las líneas corresponden al commit anterior, no a los archivos después del retiro. Incluye backend, API, SQL, PDF, interfaz, archivo, restauración, demostración, permisos, guías y pruebas. No existía un importador independiente de empleados; la importación y exportación de matrículas se conservan. El CSV de egresos consumía la proyección general del servidor.

| Archivo | Líneas relacionadas |
| --- | --- |
| `CHANGELOG.md` | 54 |
| `README.md` | 31 |
| `colegio/audit_reports.py` | 16 |
| `colegio/backup_inspection.py` | 12 |
| `colegio/db.py` | 129, 151, 188, 189, 193, 211, 215, 226, 227, 228, 234 |
| `colegio/desktop.py` | 234 |
| `colegio/directory_reports.py` | 6, 10, 30, 53, 59, 62, 68, 78 |
| `colegio/documents.py` | 74, 86, 87, 89, 90, 98, 102, 796, 863, 882, 883 |
| `colegio/institution_archive.py` | 10, 64, 69, 70, 106, 110 |
| `colegio/maintenance.py` | 4 |
| `colegio/reset_records.py` | 11, 12, 14 |
| `colegio/restore_reports.py` | 12, 14, 16, 37, 52, 64 |
| `colegio/salary.py` | 1, 19, 22, 24, 29, 33, 39, 41, 45, 46 |
| `colegio/server.py` | 34, 41, 46, 90, 91, 104, 105, 107, 108, 138, 164, 199, 200, 201, 202, 254, 257, 318, 320, 325, 326, 332, 389, 396, 398, 412, 865, 962, 964, 968 |
| `colegio/staff_access.py` | 4, 5, 16, 19 |
| `docs/bitacora.html` | 1 |
| `docs/bitacora.md` | 11 |
| `docs/calidad-b1.html` | 1 |
| `docs/calidad-b1.md` | 9 |
| `docs/configuracion.html` | 1 |
| `docs/configuracion.md` | 72 |
| `docs/permisos-b1.csv` | 26, 27, 41, 42, 43, 44, 59, 60, 71, 72, 73, 74, 75, 76, 179, 180, 194, 195, 196, 197, 212, 213, 224, 225, 226, 227, 228, 229, 332, 333, 347, 348, 349, 350, 365, 366, 377, 378, 379, 380, 381, 382, 485, 486, 500, 501, 502, 503, 513, 519, 520, 521 |
| `docs/permisos-b1.md` | 31, 32, 46, 47, 48, 49, 64, 65, 76, 77, 78, 79, 80, 81, 184, 185, 199, 200, 201, 202, 217, 218, 229, 230, 231, 232, 233, 234, 337, 338, 352, 353, 354, 355, 370, 371, 382, 383, 384, 385, 386, 387, 490, 491, 505, 506, 507, 508, 518, 524, 525, 526 |
| `docs/privilegios-personal.html` | 1 |
| `docs/privilegios-personal.md` | 15, 17, 38 |
| `docs/restauracion-segura.md` | 33 |
| `static/app.js` | 43, 131, 137, 144, 169, 191, 232, 233, 234, 238, 340, 341, 342, 344, 345, 346, 364, 365, 367, 368, 370, 371, 373, 374, 393, 394, 503, 504, 505, 540, 541, 545, 546, 574, 587, 588, 591, 613, 619, 635, 915, 916, 918, 920, 921, 922, 923, 925, 927, 929, 930, 931, 936 |
| `static/session.js` | 6, 8 |
| `static/style.css` | 5, 113 |
| `tests/browser.cjs` | 42, 43, 44, 45, 47, 48, 54, 253, 302, 303, 304, 306, 308, 309, 310, 311, 482, 486 |
| `tests/demo_browser.cjs` | 31, 32, 34, 36, 38, 39, 47 |
| `tests/permission_matrix.py` | 16, 17, 18, 36, 43 |
| `tests/responsive_browser.cjs` | 52 |
| `tests/test_admin_safety.py` | 19, 21, 22, 24, 27, 31, 32, 34, 40, 42, 43, 46, 51, 52, 53, 55, 60, 61, 65, 66, 68, 100 |
| `tests/test_demo.py` | 71, 88, 89, 90, 92, 96, 97, 98, 100, 125 |
| `tests/test_directory_reports.py` | 21, 23, 37, 48, 51 |
| `tests/test_institution_archive.py` | 129, 130, 140, 141, 143, 145, 146, 149, 151, 152 |
| `tests/test_restore_safety.py` | 98, 99 |
| `tests/test_staff_access.py` | 20, 21, 22, 23, 25, 30, 62, 64, 66, 67, 68, 69, 78, 84, 85, 86, 87, 88, 89, 95, 97, 100, 105, 106, 114, 120, 123, 127, 133, 142, 146 |
| `tests/test_system.py` | 61, 345, 346, 349, 350, 353, 357, 358, 365, 367, 368, 369, 370, 371, 374, 375, 376, 377, 380, 387, 393, 394, 403, 468 |

## Archivos compartidos que deben conservarse

| Archivo anterior | Líneas | Dependencia |
|---|---|---|
| `colegio/administration.py` | 71, 111, 242, 347, 352, 372 | Plantilla/importación de alumnos; bloqueo de caja, resumen y arqueo |
| `colegio/audit_chain.py` | 18, 150, 170, 196, 370, 400 | Versión de cadena, redacción, anexado, publicación atómica, disparadores y migración A4 |
| `colegio/storage.py` | 13, 53, 76, 102 | Bloqueo exclusivo, copia consistente y respaldos automáticos |
| `colegio/restore.py` | 45, 58, 68, 129 | Comparación, confirmación, candidata y publicación A1 |
| `colegio/backup_export.py` | 19 | Publicación cifrada y verificada |
| `colegio/demo.py` | 12, 17, 38 | Carpeta temporal aislada y eliminación de la sesión de Pruebas |
| `colegio/desktop_checks.py` | 74 | Diagnóstico nativo con datos efímeros; no registra pagos |
| `static/index.html` | 10, 12 | Carga de session.js y responsive.js |
| `packaging/Aula.spec` | 15 | Recursos del programa; sin carpeta de datos ni fixtures |
| `packaging/Aula.iss` | 41 | Guías HTML instaladas y limpieza de guías retiradas |
| `packaging/build_windows.ps1` | 7 | Suite completa obligatoria antes de compilar |

## Dependencias y decisiones

- `expenses.employee_id` apuntaba a `employees.id`; `salary_receipts.expense_id` apuntaba a `expenses.id`. `employees.position_id` apuntaba a `positions.id`. Los períodos y horarios estaban en el JSON de recibos de sueldo, no en columnas independientes de egresos.
- Caja usa importe, importe recibido, moneda, tasa, método, referencia, fecha y anulación; no necesita empleados. Se preservan estas columnas y los egresos de categoría Nómina, sin emitir recibos de sueldo.
- La comparación y los informes de restauración normalizan únicamente las tablas y vínculos retirados. No ocultan diferencias de importes, fechas, anulaciones, referencia ni identidad de cobros.
- Probar respaldo inspecciona una copia privada y no modifica el origen. Restaurar migra la candidata antes de publicarla. Convertir un respaldo antiguo migra su copia privada antes de cifrarla: ningún respaldo nuevo exportado reincorpora Personal.
- Los disparadores de A4 se generan a partir del esquema: deben reconstruirse para `expenses` después de retirar la columna. Se conservan filas y enlaces originales de bitácora y se añade un evento de migración, sin recalcular la cadena antigua. Se mantiene la redacción de secretos y la lectura de acciones históricas.
- Correlativos conservados: payments, expenses, students, guardians y enrollment_documents. Se elimina solo el piso de employees y cualquier piso de las otras tablas retiradas. Una base existente no reinicia números; una instalación nueva empieza con pisos cero.
- Móvil/PWA ya estaba retirado en B2: no existen manifest.webmanifest, mobile.js, service-worker.js, offline.html ni iconos móviles; sus rutas dan 404 y la limpieza de actualización permanece. `responsive.js` está cargado y mantiene menú adaptable, conectividad y desregistro del trabajador antiguo. `session.js` está cargado y mantiene A3; solo se retiran de su lista los formularios que ya no existen.
- Vaciar registros se retira por completo del producto. En producción no habrá un botón de borrado global; las rutas responden 410. Pruebas conserva su cierre y limpieza propios. No se vacía una base existente para simular una instalación nueva.

## Migración al esquema 12

Respaldo previo consistente y verificado, solo para recuperación durante la operación. Con Aula cerrado y su bloqueo exclusivo, una transacción copia explícitamente las columnas financieras de expenses a expenses_new, elimina primero los recibos y planes de sueldo, reemplaza expenses conservando IDs y filas, y elimina employees y positions. Las claves foráneas se suspenden antes de BEGIN exclusivamente durante esta reconstrucción y se reactivan siempre; integrity_check y foreign_key_check deben pasar antes del COMMIT. WAL y synchronous=FULL se conservan.

Se reinstalan los disparadores de la tabla reconstruida y se usa el protocolo existente de cabeza pendiente de A4. Un proceso terminado antes del COMMIT deja el esquema anterior completo; después deja el esquema nuevo completo y al reiniciar se completa la publicación de la cabeza. Se compacta y trunca WAL antes de permitir nuevos respaldos, para no arrastrar cuentas en páginas libres. La copia privada previa, que necesariamente contiene el esquema viejo, no se exporta y se elimina solo después de verificar la migración completa. Si la operación falla se conserva para recuperación. Los respaldos antiguos ya existentes no se borran automáticamente: la puesta en producción indica retirarlos expresamente.

Pruebas: fixture ficticio generado con el código real publicado 1.0.53 (a5b5aed), manifiesto y SHA-256; fixtures publicados 1.0.4, 1.0.6, 1.0.7 y 1.0.13 conservados. Referencia de caja creada con el motor de 1.0.53 y comparación exacta tras migrar. Terminación real en cinco puntos; verificación de bitácora original, filas financieras, respaldo cifrado, restauración, Probar respaldo y permisos por perfil.


## Validación Linux de las tres fases

`python -m unittest discover -s tests -v`: **291 en 158,530 s, 288 correctas y tres exclusivas de Windows omitidas**. `python tests/run_browser.py`, `python tests/run_browser.py --demo` y `python tests/run_browser.py --roster`: **PASS**. Las omisiones son DPAPI, exclusión entre instancias Windows y ventana nativa Tk de restauración. La comprobación dirigida posterior de cinco pruebas de migración/referencia pasó en 4,582 s, incluida la comparación del resumen generado por el motor publicado 1.0.53.

La primera revisión completa terminó con 269 descubiertas, cuatro fallos, tres errores y tres omisiones: importación de prueba del módulo retirado, expectativas antiguas de permisos/rutas, inserción de pisos ya existentes y una comparación binaria afectada por el cambio de cabecera a WAL. Se corrigieron los contratos manteniendo pruebas HTTP, datos/DDL/cadena iguales ante fallo, WAL/FULL y guardas A1–A5. La segunda revisión pasó 290 en 152,246 s; la ronda final anterior incorpora la conversión cifrada del respaldo antiguo. No se presenta un intento fallido como entrega validada.

[La matriz activa](permisos-b1.md) y [su CSV](permisos-b1.csv) contienen resultados esperados y reales. Las rutas retiradas se comprueban adicionalmente por HTTP con Administrador, Caja y Consulta: 45 solicitudes, todas 410, sin cambios en alumnos, cobros, cargos o egresos. Las rutas son POST employees, positions, payroll-plans, salary-receipts, archive-employee, restore-employee, reset-records; GET directory/employees (JSON/PDF), payroll-plan/1 (JSON/PDF), salary-receipt/1 (JSON/PDF), archive-preview/employee/1 y reset-preview. Se conserva el Archivo para alumnos y representantes y sus permisos/revisión/borrado protegido.

Instalador y validación nativa de Windows pendientes. La impresora física del colegio, Windows 10/11 del usuario y configuración de nube/USB real no se han probado desde Linux. B3/B4 pendientes.
