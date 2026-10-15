> A2 amplía este flujo para aceptar .aulabak con contraseña o recuperación. Las .sqlite3 antiguas conservan advertencia. Consulta [la guía A2](cifrado-respaldos.md); las pruebas/instalador A1 de abajo son evidencia histórica, no validación de A2.

# Restauración segura · A1

A1 no añade un esquema nuevo: Aula sigue en esquema 10. Al abrir una copia histórica, utiliza las migraciones que ya existían, con respaldo previo. Las cuentas, saldos y documentos del usuario no se modifican al instalar esta actualización.

## Probar respaldo sin restaurar

Configuración → Protección y mantenimiento → Probar respaldo → seleccionar .sqlite3 → Comprobar copia. Solo Administrador puede usar el endpoint y exige CSRF. Hasta 32 MB en la ventana; para archivos mayores usa **Inicio de Windows → Aula Colegio → Probar respaldo**, disponible incluso si Aula no puede abrir la base.

Aula copia el archivo a una carpeta temporal y abre SQLite allí en solo lectura. Elimina esa carpeta al terminar, también ante un error. No escribe WAL, SHM ni otros archivos en el USB o carpeta del respaldo. El acceso de Inicio rechaza un archivo con WAL asociado. En el navegador selecciona una copia generada por Aula: el navegador no permite revisar otros archivos de la carpeta de origen. Muestra integridad, referencias, esquema, alumnos, pagos válidos/anulados, último recibo y saldo registrado. No genera mensualidades, migra o reemplaza ninguna base. Las copias A1 y locales no están cifradas; A2 añade las externas/descargadas cifradas.

No deduce la fecha de creación a partir del nombre o la fecha del archivo. Para copias sin metadatos fiables muestra **No se conoce una fecha fiable de creación de este respaldo**. La fecha del pago es distinta de la fecha en que se registró.

## Restaurar con Aula cerrado

1. En Aula usa **Colegio → Salir y cerrar Aula**. X puede ocultar la ventana y dejar el servidor funcionando.
2. En Inicio de Windows abre **Restaurar respaldo** y selecciona la copia.
3. Revisa alumnos, cantidad de pagos, anulaciones, último recibo con fecha de pago/registro y total cobrado en USD histórico. Se comparan los registros por identidad, ID, request_key y huella de contenido, no solo por fechas. También se revisan egresos, fichas, cargos, convenios y otros cambios.
4. Si no hay diferencias que perder, escribe **RESTAURAR**. Si se perderían o revertirían registros, escribe **RESTAURAR CON PÉRDIDA DE DATOS**.
5. Aula vuelve a comprobar la revisión bajo el bloqueo exclusivo. Si cambió la base o la copia, cancela y solicita otra revisión.
6. Antes de reemplazar, guarda la copia completa verificada **antes-restauracion-…sqlite3**, los archivos originales, la candidata y los informes de pérdida PDF/CSV cuando hay diferencias. Si falla esta preparación, no reemplaza.
7. Al terminar muestra las rutas de los informes y de la copia anterior. Abre Aula, confirma el reloj/tasa si lo solicita y verifica saldos y recibos.

El PDF/CSV identifica movimientos con correlativo, fecha, alumno/persona, USD, moneda e importe recibido, método, referencia y estados anterior/restaurado. No incluye contraseñas. El estado exacto completo se conserva en la copia SQLite anterior. CSV UTF-8 con separador punto y coma; textos que podrían ejecutarse como fórmulas en Excel llevan un apóstrofo de protección.

El respaldo completo reemplaza usuarios, configuración y datos. No fusiona dos PC ni importa solo un alumno. Registra la restauración en la bitácora de la base restaurada y en **restauraciones.json**, junto a la base. Identifica la cuenta del sistema operativo; no la presenta como una sesión autenticada de Administrador de Aula.

## Correlativos que no retroceden

next_record_id en colegio/db.py utiliza MAX(id) o id_floor_<tabla>, el mayor, más uno. Restaurar antes reemplazaba ese piso con el de la copia antigua.

Ahora combina el máximo de ambas bases para payments, expenses, students, guardians y enrollment_documents. Los siguientes R-, E-, AL- y M- no reutilizan automáticamente números que aparecían en la base sustituida. Puede haber saltos justificados por registros conservados en el informe/copia anterior, o por borrados previos.

## Base actual dañada

Muestra **No se pudo comparar**, sin inventar cero movimientos. Conserva los archivos originales en **danado-antes-restauracion-…**. La confirmación es **RESTAURAR SIN PODER COMPARAR**.

Si los pisos actuales son ilegibles, debes indicar los últimos cinco números utilizados, nunca inferiores a los de la copia seleccionada. Revisa recibos/documentos emitidos; si no los conoces, cancela y solicita ayuda técnica. No se puede garantizar un máximo desconocido de una base ilegible solo a partir de un respaldo antiguo. Los números declarados quedan registrados.

## Si el proceso se interrumpe

Antes de retirar WAL/SHM queda **.restore-pending.json**, con la operación ya confirmada y las huellas de candidata, originales, copia anterior e informes. Al iniciar, Aula completa esa operación antes de abrir SQLite, migrar o generar mensualidades. La repetición no duplica la entrada de restauración.

Si el registro está truncado, ilegible, alterado o falta una copia verificable, aparece **Recuperación pendiente**. No abre la base ni borra los respaldos. Conserva toda la carpeta y pide ayuda técnica; no borres el registro pendiente ni WAL/SHM manualmente.

Esto protege frente a la terminación del proceso en las etapas probadas. No sustituye un UPS ni garantiza recuperación ante fallos de hardware que destruyan simultáneamente datos y copias. Las huellas detectan inconsistencias; no impiden que alguien con control de Windows reescriba el registro.

## Prueba manual guiada con datos ficticios

Usa una PC/cuenta de Windows de prueba sin información real; restaurar reemplaza toda la base. Aula - Pruebas sirve para experimentar, pero su base temporal se borra al cerrar y no ofrece exportación de respaldos.

1. En una instalación de prueba crea Administrador, grado, representante y alumno ficticios. Registra un cargo suficiente y un pago de $10: anota su R-.
2. Crea y descarga la copia A. Luego registra otro pago de $5 y anota su R-.
3. Ejecuta Probar respaldo sobre A: debe mostrar solo el primer pago. Comprobar no debe cambiar el historial actual.
4. Cierra Aula completamente. Restaura A: debe advertir el segundo pago que se perdería y exigir la confirmación reforzada.
5. Comprueba PDF y CSV: segundo R-, fecha, alumno, importe, método y referencia. Conserva antes-restauracion.
6. Abre Aula y registra un tercer pago ficticio. Su R- debe ser mayor que el segundo, no repetirlo.
7. Restaura antes-restauracion si quieres recuperar la base previa completa. También se revisa y puede dejar fuera el tercer pago: no deshace un solo movimiento.

No cortes electricidad ni mates el proceso con datos reales para probar. Las pruebas automatizadas hacen esos cortes en carpetas temporales.

## Fixtures históricas reproducibles

Generadas con el código real de tags publicados:

| Tag | Commit | Esquema |
|---|---|---|
| desktop-1.0.4 | 612e7e31b6047d2c63e25f35fe8aa069051bb551 | 7 |
| desktop-1.0.6 | 027f3a4ffc13ab317ed28d0fe6a3ef5c370cd7b1 | 7 |
| desktop-1.0.7 | ece5227dfefa4d5ebc5c184b1e486485787355aa | 7 |
| desktop-1.0.13 | cabeab4361a9acc7e1b73274a60d045ac9210c16 | 8 |

tests/generate_restore_fixtures.py reproduce las bases en Linux usando git archive; no ejecuta instaladores antiguos. Datos y credenciales ficticios. tests/fixtures/restore/manifest.json guarda origen y SHA256. Las pruebas restauran, abren con Aula actual, verifican integridad/referencias y conservan un pago de USD 50 y saldo USD 50. No se inventa una versión cambiando solo user_version.

La validación de instalación/ventanas del instalador actual se reporta aparte; esta prueba no afirma haber instalado ni actualizado binarios de esas cuatro versiones.

## Validación A1 en Linux · 12 de octubre de 2026

- `python -m unittest discover -s tests -v`: 223 pruebas descubiertas en 74.415 s; 221 correctas y dos exclusivas de Windows omitidas (mutex/ventanas y revisión Tk con comprobador independiente).
- `python tests/run_browser.py`: correcto; revisión de copia válida/corrupta, autorización/CSRF y comprobación de que probar no modifica cargos ni pagos, además del recorrido habitual.
- `python tests/run_browser.py --demo`: correcto.
- `python tests/run_browser.py --roster`: correcto.
- Los cortes utilizan terminación real de un subproceso antes de retirar WAL/SHM, después de retirarlos, después de reemplazar y después de registrar la operación. El siguiente inicio completa la intención confirmada antes de inicializar/generar y conserva la copia anterior con los dos cobros.
- Esquema 99 rechazado tanto al restaurar como al iniciar una base futura, sin migración ni sustitución. Registro pendiente truncado impide abrir y generar.

Windows se ejecutó por separado y sus resultados se detallan abajo. No se han ejecutado pruebas en la PC real del usuario.

El instalador conserva Tcl/Tk y la lista de dependencias vigente: no se excluyen módulos del PYZ en A1. Su cambio funcional es el acceso independiente Probar respaldo. El ZIP de código fuente incluye las cuatro bases ficticias SHA256 del manifiesto para que las pruebas históricas también puedan ejecutarse desde esa distribución; no incorpora información real.

La revisión y la columna Tipo del CSV muestran nombres de registros en español. El comprobador de Inicio comunica archivos dañados con un mensaje en español en lugar del error técnico de SQLite; queda cubierto por la prueba nativa de ventanas.

## Validación Windows y descarga · A1 1.0.34

[Instalador 1.0.34 en borrador](https://github.com/Eliezerti/Sistema-colegio/releases/tag/untagged-53d32cb7abf24fbc94e9). Descarga **Aula-Colegio-Instalador-1.0.34.exe**, no el ZIP fuente. Instala con la misma cuenta Windows después de crear/verificar una copia externa y cerrar Aula completamente. Una actualización conserva la base; no uses Vaciar registros para actualizar.

[Runner Windows 2022, Python 3.12](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38303608499), commit **7a349eb74ab601103faf520c3aedff18e999bb2b**:

- Unitarias: **223 correctas en 255.960 s, sin omisiones**. Incluye los cuatro cortes reales, cuatro fixtures publicadas y la ventana Tk de revisión/comprobador independiente. La prueba de archivo dañado provoca deliberadamente un registro ERROR de diagnóstico, comprueba el mensaje en español y termina correctamente; no es un fallo de la suite.
- Instalador: acceso Probar respaldo con destino Aula.exe y argumento --test-backup; instalación, ventanas normal/Pruebas, bandeja, reinstalación y desinstalación sin cambiar las huellas de la base o respaldo preparados por la prueba.
- Defender antes y después: motor **1.1.26080.3**, firmas **1.459.690.0**, sin detecciones. Los dos registros de análisis indican el mismo hash del ejecutable.
- Archivo descargado de la versión: **20,541,854 bytes**, SHA256 **cd88a16defd595c2374cee29a9281abc71911a8ed728bf9e0743344b0bad9ec8**, comprobado contra el sidecar y ambos análisis. El servicio de artefactos rechazó la descarga; se verificó el mismo ejecutable desde la versión de GitHub sin omitir TLS ni comprobación de hash.
- La compilación inicial A1 1.0.33 aprobó sus pruebas; 1.0.34 añade los nombres/mensajes en español que se entregan. No se ofrece una versión con validación fallida.

No se probaron instalación bajo otra cuenta Windows ni actualización desde los ejecutables históricos 1.0.4/6/7/13. Sus bases sí se reprodujeron desde tags reales y restauraron/abrieron en Linux y Windows. La reinstalación probada utiliza el instalador actual. Tampoco se verificó Defender, BitLocker, energía o restauración de datos reales en la PC del usuario.

Las alertas antiguas de 1.0.8/1.0.14 siguen pendientes: este análisis no las explica ni garantiza detección universal. No desactives Defender ni añadas exclusiones. A1 no firma el ejecutable, cifra las copias ni endurece sesiones/bitácora/permisos: eso pertenece a tandas posteriores. Las huellas de restauración detectan inconsistencia, no impiden alteraciones de quien controla Windows. Un máximo ilegible exige correlativos declarados correctos; si se desconocen, cancela y pide revisión técnica.

## Archivos y pruebas de esta entrega

- Núcleo: colegio/backup_inspection.py, restore.py, restore_journal.py y restore_reports.py. Integración de inicio: colegio/server.py y reset_password.py (en este último solo resolver/bloquear una restauración pendiente antes de abrir; no cambia el comportamiento de sesiones).
- Interfaz: colegio/desktop.py y static/app.js. Instalador: packaging/Aula.iss, packaging/test_installer.ps1 y .github/workflows/windows-desktop.yml. Se conserva Tcl/Tk y las dependencias existentes.
- Trece métodos de prueba nuevos: nueve en tests/test_restore_safety.py, uno en test_historical_restore.py (cuatro subcasos históricos), dos en test_system.py y uno nativo en test_restore_windows_ui.py. El corte real cubre cuatro etapas en subcasos. tests/browser.cjs añade copia válida/corrupta y conservación del historial.
- Adaptación al flujo de revisión obligatorio: tests/restore_helpers.py, test_recovery.py y test_institution_archive.py. Reproducción histórica: tests/generate_restore_fixtures.py y tests/fixtures/restore/ (cuatro SQLite ficticias y manifest.json con tags/commits/SHA256).
- Distribución: tests/package_windows.py y descargas/Aula-Windows.zip/.sha256. Documentación: README.md, CHANGELOG.md, docs/restauracion-segura.md/.html y docs/mantenimiento.html.
- Commits de implementación: **e3f54cc** (núcleo), **7a7c6e2** (comprobador/revisión), **b5670df** (instalador/distribución), **7a349eb** (textos en español). La actualización posterior de resultados/documentación no modifica el código validado.

No hay nueva migración: esquema 10 vigente, motor financiero y ubicación intactos. No se editó información real. A1 termina aquí; A2 requiere confirmación.
