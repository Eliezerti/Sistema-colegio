# Archivo de la institución

## Retirar a un alumno, representante o empleado

1. En Administración, abre **Archivo de la institución**. Solo lo ve Administrador; en Aula - Pruebas funciona sobre datos temporales.
2. Elige **Alumnos**, **Representantes** o **Personal**. Busca por nombre o documento y filtra **En directorio**, **En archivo** o **Todas las fichas**.
3. Pulsa **Revisar ficha**. Verás sus vínculos, documentos y movimientos; para alumnos, el saldo pendiente.
4. Selecciona **Archivar ficha**, escribe un motivo y ARCHIVAR. El alumno queda inactivo y deja de generar mensualidades nuevas. No se anulan deudas existentes. El representante solo se archiva si sus alumnos ya están archivados o fueron reasignados.
5. El empleado queda Inactivo; no se cambian salarios, pagos ni recibos. Puedes verlo en Personal → Mostrar inactivos y en el PDF generado con ese filtro.

El directorio habitual muestra las fichas disponibles. El archivo conserva el historial sin llenar el listado cotidiano. Las fichas ocupan poco espacio: eliminarlas no es una estrategia de mantenimiento de disco.

## Recuperar una ficha

Revisar ficha → Recuperar ficha → motivo y RECUPERAR. El alumno vuelve como inactivo: revisa el primer mes a cobrar, representante y período antes de activarlo. El representante vuelve al directorio. El empleado vuelve como activo; revisa sus datos antes de utilizarlo.

## Borrar una ficha creada por error

**Un saldo de $0 no significa que esté vacía.** Los cargos pagados o anulados, pagos/recibos anulados o válidos y egresos mantienen bloqueado el borrado definitivo. También se comprueban convenios, seguimientos, relaciones de pago, actas y documentos familiares. Un representante con alumnos vinculados sigue protegido, aunque estén archivados.

Solo si la ficha ya está archivada y no tiene movimientos ni vínculos protegidos aparece **Borrar definitivamente**:

1. Revisa qué se elimina. En un alumno sin movimientos se eliminan también sus propias constancias de matrícula y evaluaciones de mensualidad sin importe; la pantalla lo indica.
2. Escribe el motivo, tu contraseña de Administrador y BORRAR FICHA.
3. Aula vuelve a comprobar el historial dentro de la transacción. Si cambió desde la revisión, tendrás que revisarlo nuevamente.
4. Antes de borrar, crea un respaldo completo `antes-borrar-ficha-…sqlite3` y verifica su integridad. Copia también al segundo destino si está configurado. Si falla cualquier copia, no borra la ficha.
5. Guarda la operación y su motivo en bitácora. No borra otros alumnos, representantes, empleados ni movimientos. Conserva el correlativo para no reutilizar automáticamente el código o número de una ficha/constancia eliminada.

En **Aula - Pruebas**, la cuenta entra sin una contraseña conocida: el borrado de fichas temporales pide motivo y BORRAR FICHA, conserva la revisión y crea su copia previa en la carpeta temporal, pero no pide la contraseña del sistema real. Solo el modo Pruebas configurado por el servidor permite esto; enviar un campo «demo» desde el navegador al sistema real no lo habilita. El Administrador real siempre debe confirmar con su contraseña. Las copias de la sesión de pruebas se eliminan al cerrar esa sesión.

No hay borrado masivo. Para recuperar una ficha borrada hace falta restaurar el respaldo completo con Aula cerrada; esa restauración reemplaza toda la base y puede dejar fuera cambios posteriores. No es un botón para deshacer una sola ficha.

Los respaldos anteriores, PDF, Excel y archivos enviados siguen conteniendo sus datos. El borrado de Aula no es una eliminación de todas las copias existentes. No se purgan respaldos ni bitácora.

## Alcance y comprobaciones

No cambia el esquema ni la ubicación de la base, datos existentes durante la actualización, móvil/PWA, cálculo de nómina, cifrado o las fases de seguridad pendientes. Reutiliza los estados de archivo/inactividad existentes y claves de correlativos en configuración. Conserva CSRF, permisos del servidor, bloqueo del reloj, transacciones, WAL/FULL y copias de cinco minutos.

La revisión de documentos históricos ilegibles bloquea el borrado: no los considera vacíos. No se afirma cumplimiento de un plazo legal de conservación específico; esa política se revisa con la institución.

Prueba primero en Aula - Pruebas: una ficha sin movimientos admite borrado tras archivarla; un alumno con recibos pagados y saldo $0 solo permite archivar. Verifica que puedas consultar su recibo después. No borres alumnos reales para comprobar la actualización.

## Resultados ejecutados en Linux · 12 de octubre de 2026

- `python -m unittest discover -s tests -v`: 210 descubiertas, 209 correctas y una prueba nativa de Windows omitida (71,414 segundos).
- `python tests/run_browser.py`: correcto; revisa el módulo, borra un representante ficticio vacío, conserva recibos y comprueba que Caja y Consulta no vean el módulo.
- `python tests/run_browser.py --demo`: correcto.
- `python tests/run_browser.py --roster`: correcto.

Nueve pruebas de archivo y una nueva de aislamiento temporal ejercitan copia local/segundo destino, contraseña/CSRF/permisos, revisión desactualizada, conservación de recibos con saldo cero, historia de representantes reasignados, personal pagado/anulado y relaciones de pago, fallos de copia, correlativos y restauración del respaldo en otra carpeta. Las pruebas usan bases temporales y no modifican datos del usuario.

Archivos: `colegio/institution_archive.py`, integración en `colegio/server.py`, correlativos en `colegio/db.py` y `colegio/documents.py`, filtro en `colegio/directory_reports.py`, `static/app.js`, `static/style.css`, `tests/test_institution_archive.py`, `tests/browser.cjs`, `tests/test_demo.py`, `tests/demo_browser.cjs`, `AGENTS.md`, README, CHANGELOG y guías de archivo. Las notas de compilación y el paquete fuente se actualizan para la entrega.

Pendientes de esta validación Linux: instalación, ACL/BitLocker y análisis con Microsoft Defender requieren Windows. Se reportan por separado cuando termine la compilación nativa. No se comprueba desde aquí el cifrado, permisos ni antivirus de la PC del usuario.

El [primer intento Windows (1.0.31)](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38265231467) ejecutó 209 pruebas y encontró tres errores de limpieza: las conexiones de inspección de las pruebas seguían abiertas. No se generó el instalador. Se corrige con cierre explícito de esas conexiones, manteniendo las comprobaciones y la aplicación sin cambios; la siguiente ejecución debe validar también esa limpieza.
