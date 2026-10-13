# Comprobaciones financieras e instalación · B1

## Verificar datos

En Configuración → Protección y mantenimiento → Verificar datos y cobros, Aula comprueba integridad SQLite, referencias, aplicaciones por cobro, total de cobros válidos frente a sus aplicaciones, sobrepagos, cargos cancelados con pagos válidos, vínculos entre alumnos y cargos, mensualidades, cargos duplicados, numeración y cadena de bitácora. La verificación no genera mensualidades, repara registros ni modifica importes.

Los abonos de pagos anulados se conservan como historial, pero no se suman a cobros válidos ni al saldo abonado. La revisión mantiene además la comparación individual de cada cobro con sus aplicaciones originales.

Los correlativos reservados en id_floor_payments, expenses, students, guardians, employees y enrollment_documents explican saltos hasta ese límite después de restaurar, vaciar o borrar una ficha sin movimientos. Se informan intervalos faltantes por encima del límite, sin recorrer millones de números inexistentes. Si el límite es inválido dice que no se pudo comprobar. No se exige reutilizar números ni se renumeran registros. La reserva y la bitácora permiten revisar el contexto; no certifican por sí solas qué recibos fueron entregados físicamente antes del historial disponible.

No cambia el esquema 11, ubicación de la base, cálculos financieros, móvil/PWA, nómina, comprobantes, respaldos de cinco minutos, A1–A5 ni los avisos. Las nuevas comprobaciones son de solo lectura; una inconsistencia se informa sin intentar corregirla.

## Pruebas existentes que se conservan

Cobro: tests/test_system.py, test_process_killed_during_and_after_payment_preserves_atomicity. Restauración: tests/test_restore_safety.py, cuatro cortes reales alrededor de WAL/SHM y reemplazo. Respaldo cifrado: tests/test_backup_crypto.py, cinco cortes reales. Bitácora: tests/test_audit_chain.py, publicación y migración con procesos terminados. Febrero 29 y cambio de mes: tests/test_monthly_automation.py:74. No se duplican esas pruebas ni se retiran protecciones.

## Pruebas añadidas

Tests/test_financial_invariants.py: totales válidos y anulados separados; aplicaciones excesivas; reservas válidas, faltantes e ilegibles; duplicados en una copia ficticia con esquema dañado; tasa de seis decimales y recibo histórico inmutable; cierre anticipado conserva deudas emitidas y no crea meses posteriores; cinco cuentas independientes de Caja enviando HTTP a la vez, con referencias y solicitudes distintas. Con deuda USD 100 y cinco pagos USD 40, entran dos pagos, se rechazan tres y quedan USD 20.

Tests/test_operation_kills.py: proceso realmente terminado durante copia local, antes y después de publicar; destino anterior o nuevo íntegro y base original intacta. Borrado de representante sin vínculos después del respaldo, durante DELETE y después de COMMIT: ficha completa o borrado completo, respaldo previo íntegro, referencias y cadena verificadas. Los puntos de pausa se inyectan dentro del proceso de prueba; no se añaden interruptores al programa para simular éxito.

Tests/permission_matrix.py y test_permission_matrix.py: contrato independiente por Administración, Caja, Consulta y anónimo; inventario automático de comparaciones/prefijos y acciones del servidor. Una ruta nueva sin caso hace fallar la prueba. Se prueban solicitudes HTTP y ausencia de CSRF, incluidos PDF, importación, respaldos y documentos bancarios. Las solicitudes deliberadamente incompletas deben llegar a validación (400) solo en perfiles permitidos: 400 no significa que la operación se completó. Las operaciones válidas se comprueban en las suites funcionales existentes. Se generan JSON, CSV y Markdown con estados esperados/reales, sin cuerpos, fichas, contraseñas ni tokens. Usa AULA_PERMISSION_REPORT_DIR para guardar evidencia en una carpeta de pruebas.

## Instalación Windows real

Se agrega packaging/test_b1_windows.ps1 y tests/windows_upgrade.py/windows_other_account.py a la validación nativa. El runner es desechable; se rechaza la prueba si la cuenta ya tiene una carpeta AulaColegio. No se ejecuta sobre tus datos.

Se instala el EXE actual en una cuenta sin datos, se abre de verdad, se comprueba la pantalla de primera cuenta y que desinstalar conserve la base creada. Después se descarga el instalador realmente publicado 1.0.13; se compara la huella publicada y la huella fijada 9714be7b6edaa03eab71a247c51219de6c425b5cd72d3b7fb7f1fbe23ab08d3c. Defender debe analizarlo sin detecciones antes de ejecutarlo. Se abre una base ficticia generada desde su tag real, se instala la versión nueva, se vuelve a abrir y se comparan las filas financieras originales, recibo, integridad, referencias y saldo USD 50; se comprueban esquema 11 y respaldo previo. Las normalizaciones de código interno realizadas por la versión antigua se toman antes de establecer la referencia de la actualización.

Se crea una segunda cuenta estándar Windows real, con contraseña aleatoria solo en memoria. Se carga su perfil y el bloque de entorno generado por Windows para su token real; no se simula cambiando LOCALAPPDATA. Allí se instala y abre el EXE, se verifica que pide la primera cuenta y utiliza otra carpeta real, y que desinstalar conserva su base. La cuenta principal tiene un marcador y una base ficticia que deben permanecer intactos, con sus huellas comprobadas. Solo se cambia la ACL del área temporal compartida del test; al terminar se elimina exclusivamente esa cuenta y sus archivos ficticios. La evidencia identifica SID y carpeta, sin contraseñas.

Los resultados y diagnósticos se conservan en el artefacto Verificacion-B1. Defender del EXE nuevo, ventanas y reinstalación anteriores se mantienen. El ZIP se reconstruye desde la fuente del mismo commit antes de adjuntarlo, para evitar distribuir un paquete anterior.

## Qué probar tú

1. Guarda un respaldo externo y cierra Aula completamente antes de actualizar, usando la misma cuenta de Windows.
2. En Aula Pruebas usa fichas ficticias y entra con Administración. Abre Verificar datos y cobros: debe completar los controles y mostrar WAL y FULL.
3. No alteres números, la bitácora o SQLite en la base real para simular fallos; esos casos se prueban en carpetas desechables.
4. Al actualizar tu PC comprueba nombres, saldos y último recibo. Conserva la copia previa. Si se informa una inconsistencia, guarda un respaldo y solicita revisión; no uses Vaciar registros para resolverla.
5. Windows 10/11 de tu PC, hardware/BitLocker, instalación sin internet y otra cuenta del colegio requieren verificación local. El runner es Windows Server 2022 nuevo para Aula, con herramientas de desarrollo instaladas; no equivale a certificar cualquier PC Windows limpia.

## Evidencia y archivos

11 métodos nuevos de pruebas Python y ampliación del diagnóstico; los nuevos cortes tienen tres etapas cada uno. Revisión dirigida: 11 correctas en 8.444 s. La primera prueba de concurrencia reutilizaba referencias y activó correctamente la advertencia bancaria; se corrigió usando referencias distintas, sin cambiar el motor. La primera matriz tenía dos expectativas incorrectas (sesión anónima pública y desbloqueo ya configurado); se corrigió el contrato, sin modificar los permisos. La revisión dirigida final descubrió 86 rutas y verificó 561 solicitudes.

Las cuatro suites Linux terminaron: `python -m unittest discover -s tests -v`: **298 pruebas en 170.610 s**, 295 correctas y tres exclusivas de Windows omitidas (DPAPI, mutex de instancias y ventana nativa). `python tests/run_browser.py`, `python tests/run_browser.py --demo` y `python tests/run_browser.py --roster`: correctos. El primer intento nativo 1.0.43 se detuvo por la declaración del contexto runner.temp al nivel de trabajo, antes de ejecutar pruebas o generar instalador; se mueve al paso de compilación. El intento 1.0.44 ejecutó 298 pruebas Windows correctas en 359.688 s y comprobó instalación nueva, inicio y filas/saldo/recibo/esquema después de la actualización desde 1.0.13. Se detuvo al intentar unins000.exe; Inno puede registrar otro número al actualizar, por lo que ahora se consulta y valida la ruta real registrada por Windows. No se alcanzó la segunda cuenta ni se publicó instalador. La revisión 1.0.45 completó actualización, migración, desinstalación y conservación de base/respaldo; el mensaje final usó una flecha no representable en CP1252 y detuvo la prueba antes de la segunda cuenta. Se fija UTF-8 en los flujos del verificador, sin cambios del producto. No se publicó instalador. Se ajusta la identidad numérica a la sintaxis de icacls (*SID) únicamente en la carpeta ficticia compartida; la ejecución 1.0.47 se cancela antes de terminar para verificar el script corregido, sin presentarla como pasada. Las pruebas Windows ampliadas están pendientes de terminar; no se afirma éxito todavía. No se considera realizada una prueba de otra cuenta ni una actualización entre versiones por reinstalar el mismo EXE.

Archivos: colegio/maintenance.py, static/app.js, tests/test_financial_invariants.py, tests/test_operation_kills.py, tests/permission_matrix.py, tests/test_permission_matrix.py, tests/windows_upgrade.py, tests/windows_other_account.py, packaging/test_b1_windows.ps1, .github/workflows/windows-desktop.yml, README.md, CHANGELOG.md, docs/calidad-b1.md/html, docs/configuracion.md/html y descargas/Aula-Windows.zip/sha256.

Se detiene B1 antes de B2. Limpieza del paquete, eliminación de móvil/PWA, firma y SQLCipher siguen pendientes de sus decisiones respectivas.
