# Restauración segura · A1

A1 no añade un esquema nuevo: Aula sigue en esquema 10. Al abrir una copia histórica, utiliza las migraciones que ya existían, con respaldo previo. Las cuentas, saldos y documentos del usuario no se modifican al instalar esta actualización.

## Probar respaldo sin restaurar

Configuración → Protección y mantenimiento → Probar respaldo → seleccionar .sqlite3 → Comprobar copia. Solo Administrador puede usar el endpoint y exige CSRF. Hasta 32 MB en la ventana; para archivos mayores usa **Inicio de Windows → Aula Colegio → Probar respaldo**, disponible incluso si Aula no puede abrir la base.

Aula copia el archivo a una carpeta temporal y abre SQLite allí en solo lectura. Elimina esa carpeta al terminar, también ante un error. No escribe WAL, SHM ni otros archivos en el USB o carpeta del respaldo. Una base con WAL asociado no se trata como respaldo completo. Muestra integridad, referencias, esquema, alumnos, pagos válidos/anulados, último recibo y saldo registrado. No genera mensualidades, migra o reemplaza ninguna base. Las copias actuales no están cifradas; eso corresponde a A2.

No deduce la fecha de creación a partir del nombre o la fecha del archivo. Para copias sin metadatos fiables muestra **No se conoce una fecha fiable de creación de este respaldo**. La fecha del pago es distinta de la fecha en que se registró.

## Restaurar con Aula cerrado

1. En Aula usa **Colegio → Salir y cerrar Aula**. X puede ocultar la ventana y dejar el servidor funcionando.
2. En Inicio de Windows abre **Restaurar respaldo** y selecciona la copia.
3. Revisa alumnos, cantidad de pagos, anulaciones, último recibo con fecha de pago/registro y total cobrado en USD histórico. Se comparan los registros por identidad, ID, request_key y huella de contenido, no solo por fechas. También se revisan egresos, fichas, cargos, convenios y otros cambios.
4. Si no hay diferencias que perder, escribe **RESTAURAR**. Si se perderían o revertirían registros, escribe **RESTAURAR CON PÉRDIDA DE DATOS**.
5. Aula vuelve a comprobar la revisión bajo el bloqueo exclusivo. Si cambió la base o la copia, cancela y solicita otra revisión.
6. Antes de reemplazar, guarda la copia completa verificada **antes-restauracion-…sqlite3**, los archivos originales, la candidata y los informes de pérdida PDF/CSV cuando hay diferencias. Si falla esta preparación, no reemplaza.
7. Al terminar muestra las rutas de los informes y de la copia anterior. Abre Aula, confirma el reloj/tasa si lo solicita y verifica saldos y recibos.

El PDF/CSV identifica movimientos con correlativo, fecha, alumno/persona, USD, moneda e importe recibido, método, referencia y estados anterior/restaurado. No incluye cuentas bancarias de empleados ni contraseñas. El estado exacto completo se conserva en la copia SQLite anterior. CSV UTF-8 con separador punto y coma; textos que podrían ejecutarse como fórmulas en Excel llevan un apóstrofo de protección.

El respaldo completo reemplaza usuarios, configuración y datos. No fusiona dos PC ni importa solo un alumno. Registra la restauración en la bitácora de la base restaurada y en **restauraciones.json**, junto a la base. Identifica la cuenta del sistema operativo; no la presenta como una sesión autenticada de Administrador de Aula.

## Correlativos que no retroceden

next_record_id en colegio/db.py utiliza MAX(id) o id_floor_<tabla>, el mayor, más uno. Restaurar antes reemplazaba ese piso con el de la copia antigua.

Ahora combina el máximo de ambas bases para payments, expenses, students, guardians, employees y enrollment_documents. Los siguientes R-, E-, AL- y M- no reutilizan automáticamente números que aparecían en la base sustituida. Puede haber saltos justificados por registros conservados en el informe/copia anterior, o por borrados previos.

## Base actual dañada

Muestra **No se pudo comparar**, sin inventar cero movimientos. Conserva los archivos originales en **danado-antes-restauracion-…**. La confirmación es **RESTAURAR SIN PODER COMPARAR**.

Si los pisos actuales son ilegibles, debes indicar los últimos seis números utilizados, nunca inferiores a los de la copia seleccionada. Revisa recibos/documentos emitidos; si no los conoces, cancela y solicita ayuda técnica. No se puede garantizar un máximo desconocido de una base ilegible solo a partir de un respaldo antiguo. Los números declarados quedan registrados.

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
