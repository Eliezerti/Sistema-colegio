# Restauración segura · A1

Aula verifica y prepara una copia antes de reemplazar datos. El esquema actual es 12; una copia antigua se actualiza en el temporal y una copia de esquema más nuevo se rechaza. Una actualización del programa conserva cuentas, saldos y documentos.

## Probar respaldo sin restaurar

Configuración → Protección y mantenimiento → Probar respaldo → seleccionar .aulabak o .sqlite3 antiguo → Comprobar copia. Solo Administrador puede usar el endpoint y exige CSRF. Hasta 32 MB en la ventana; para archivos mayores usa **Inicio de Windows → Aula Colegio → Probar respaldo**, disponible incluso si Aula no puede abrir la base.

Aula copia el archivo a una carpeta temporal y abre SQLite allí en solo lectura. Elimina esa carpeta al terminar, también ante un error. No escribe WAL, SHM ni otros archivos en el USB o carpeta del respaldo. El acceso de Inicio rechaza un archivo con WAL asociado. En el navegador selecciona una copia generada por Aula: el navegador no permite revisar otros archivos de la carpeta de origen. Muestra integridad, referencias, esquema, alumnos, pagos válidos/anulados, último recibo y saldo registrado. No genera mensualidades, migra o reemplaza ninguna base. Las copias nuevas externas y descargadas salen cifradas; para abrirlas se pide contraseña o recuperación.

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

Aula combina el máximo de ambas bases para payments, expenses, students, guardians y enrollment_documents. Los siguientes R-, E-, AL- y M- no reutilizan automáticamente números que aparecían en la base sustituida. Puede haber saltos justificados por registros conservados en el informe/copia anterior, o por borrados previos.

## Base actual dañada

Muestra **No se pudo comparar**, sin inventar cero movimientos. Conserva los archivos originales en **danado-antes-restauracion-…**. La confirmación es **RESTAURAR SIN PODER COMPARAR**.

Si los pisos actuales son ilegibles, debes indicar los últimos cinco números utilizados, nunca inferiores a los de la copia seleccionada. Revisa recibos/documentos emitidos; si no los conoces, cancela y solicita ayuda técnica. No se puede garantizar un máximo desconocido de una base ilegible solo a partir de un respaldo antiguo. Los números declarados quedan registrados.

## Si el proceso se interrumpe

Antes de retirar WAL/SHM queda **.restore-pending.json**, con la operación ya confirmada y las huellas de candidata, originales, copia anterior e informes. Al iniciar, Aula completa esa operación antes de abrir SQLite, migrar o generar mensualidades. La repetición no duplica la entrada de restauración.

Si el registro está truncado, ilegible, alterado o falta una copia verificable, aparece **Recuperación pendiente**. No abre la base ni borra los respaldos. Conserva toda la carpeta y pide ayuda técnica; no borres el registro pendiente ni WAL/SHM manualmente.

Esto protege frente a la terminación del proceso en las etapas probadas. No sustituye un UPS ni garantiza recuperación ante fallos de hardware que destruyan simultáneamente datos y copias. Las huellas detectan inconsistencias; no impiden que alguien con control de Windows reescriba el registro.
