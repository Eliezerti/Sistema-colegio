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
