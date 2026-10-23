# Archivo de la institución

## Retirar a un alumno o representante

1. En Administración, abre **Archivo de la institución**. Solo lo ve Administrador; en Aula - Pruebas funciona sobre datos temporales.
2. Elige **Alumnos** o **Representantes**. Busca por nombre o documento y filtra **En directorio**, **En archivo** o **Todas las fichas**.
3. Pulsa **Revisar ficha**. Verás sus vínculos, documentos y movimientos; para alumnos, el saldo pendiente.
4. Selecciona **Archivar ficha**, escribe un motivo y ARCHIVAR. El alumno queda inactivo y deja de generar mensualidades nuevas. No se anulan deudas existentes. El representante solo se archiva si sus alumnos ya están archivados o fueron reasignados.

El directorio habitual muestra las fichas disponibles. El archivo conserva el historial sin llenar el listado cotidiano. Las fichas ocupan poco espacio: eliminarlas no es una estrategia de mantenimiento de disco.

Al borrar una ficha, el archivo SQLite puede conservar su tamaño y reutilizar después el espacio liberado. No se compacta ni se borra historial automáticamente para reducir ese archivo.

## Recuperar una ficha

Revisar ficha → Recuperar ficha → motivo y RECUPERAR. El alumno vuelve como inactivo: revisa el primer mes a cobrar, representante y período antes de activarlo. El representante vuelve al directorio.

## Borrar una ficha creada por error

### Matrícula duplicada o equivocada

En **Alumnos y matrículas**, abre **Editar** en la fila equivocada. Al final del formulario despliega **Corrección de fichas creadas por error** y pulsa **Eliminar esta ficha…**. Esta opción solo aparece para Administración, dentro de la ficha; no está junto a los botones del directorio.

1. Revisa nombre, código, grado, representante y cantidades. No hace falta archivar ni dejar inactivo al alumno antes.
2. Si solo tiene cargos sin pagos, Aula permite eliminar la ficha junto con esos cargos, sus evaluaciones de mensualidad y sus constancias. Deja de aparecer en alumnos, matrícula y morosidad, incluso después de reiniciar.
3. Escribe el motivo, tu contraseña de Administrador, el código exacto de la ficha equivocada y BORRAR FICHA. En modo Pruebas se omite únicamente la contraseña; la revisión y las confirmaciones se conservan.
4. Aula vuelve a comprobar todo dentro de la transacción y crea el respaldo previo verificado. Si falla el respaldo local o el segundo destino configurado, no borra. Si alguien cambió la ficha o registró un pago después de revisarla, tendrás que revisarla otra vez.

**No elimina pagos ni recibos, aunque estén anulados**, abonos, convenios, seguimientos, estados de cuenta, solvencias ni vínculos con actas de pase de año. En esos casos muestra el motivo del bloqueo. El representante, los demás alumnos, los cobros y el correlativo de recibos se conservan. Los códigos eliminados de alumno y constancia no se reutilizan.

Esta corrección quita la deuda equivocada del alumno eliminado; por eso disminuyen los pendientes de ese duplicado. Los importes cobrados y egresados, el cierre de caja y las cuentas de los demás alumnos permanecen iguales.

El borrado es de la ficha en la base activa. La bitácora, el respaldo previo, las copias anteriores y los archivos descargados conservan información. No es borrado forense del disco ni eliminación de todas las copias existentes. No hay borrado masivo ni botón para deshacer: restaurar un respaldo completo puede dejar fuera operaciones posteriores.

### Fichas vacías desde el Archivo de la institución

**Un saldo de $0 no significa que esté vacía.** Los cargos pagados o anulados, pagos/recibos anulados o válidos y egresos mantienen bloqueado el borrado definitivo. También se comprueban convenios, seguimientos, relaciones de pago, actas y documentos familiares. Un representante con alumnos vinculados sigue protegido, aunque estén archivados.

Solo si la ficha ya está archivada y no tiene movimientos ni vínculos protegidos aparece **Borrar definitivamente**:

1. Revisa qué se elimina. En un alumno sin movimientos se eliminan también sus propias constancias de matrícula y evaluaciones de mensualidad sin importe; la pantalla lo indica.
2. Escribe el motivo, tu contraseña de Administrador y BORRAR FICHA.
3. Aula vuelve a comprobar el historial dentro de la transacción. Si cambió desde la revisión, tendrás que revisarlo nuevamente.
4. Antes de borrar, crea un respaldo completo `antes-borrar-ficha-…sqlite3` y verifica su integridad. Copia también al segundo destino si está configurado. Si falla cualquier copia, no borra la ficha.
5. Guarda la operación y su motivo en bitácora. No borra otros alumnos, representantes ni movimientos. Conserva el correlativo para no reutilizar automáticamente el código o número de una ficha/constancia eliminada.

En **Aula - Pruebas**, la cuenta entra sin una contraseña conocida: el borrado de fichas temporales pide motivo y BORRAR FICHA, conserva la revisión y crea su copia previa en la carpeta temporal, pero no pide la contraseña del sistema real. Solo el modo Pruebas configurado por el servidor permite esto; enviar un campo «demo» desde el navegador al sistema real no lo habilita. El Administrador real siempre debe confirmar con su contraseña. Las copias de la sesión de pruebas se eliminan al cerrar esa sesión.

No hay borrado masivo. Para recuperar una ficha borrada hace falta restaurar el respaldo completo con Aula cerrada; esa restauración reemplaza toda la base y puede dejar fuera cambios posteriores. No es un botón para deshacer una sola ficha.

Los respaldos anteriores, PDF, Excel y archivos enviados siguen conteniendo sus datos. El borrado de Aula no es una eliminación de todas las copias existentes. No se purgan respaldos ni bitácora.

## Al actualizar

La actualización no archiva ni borra fichas por su cuenta. Antes de instalar, crea y prueba una copia externa, cierra Aula por completo e instala con la misma cuenta de Windows. Comprueba después saldos y recibos. Practica siempre en Aula - Pruebas.
