# Si Aula pide revisar la fecha y hora

## Qué protege

Aula conserva el último reloj observado. Si hay un cambio sospechoso, detiene cobros, generación de mensualidades y emisión de documentos, incluidos PDF y recibos. También detiene la generación automática al iniciar y al consultar reportes. No borra ni recalcula cargos o pagos anteriores.

La política aprobada es:

- Con Aula cerrado: un avance mayor de **siete días** exige confirmación. Siete días exactos se permiten; una ausencia más larga puede ser legítima, pero se revisa antes de generar meses.
- Retrocesos: se toleran ajustes de hasta **dos minutos**, incluidos ajustes normales cerca de medianoche. Un retroceso mayor exige confirmación.
- Con Aula abierto: se compara el reloj de Windows con tiempo monotónico. Un salto inesperado hacia adelante mayor de **dos minutos** exige confirmación; trabajar varias horas normalmente no dispara el aviso.

El contador de intentos de acceso también usa tiempo monotónico. Cambiar la fecha no quita la espera por diez intentos en un minuto. El contador continúa en memoria: cerrar el servidor lo reinicia, como antes.

## Cómo continuar

1. Revisa las dos fechas que muestra Aula: la última observada y la actual de Windows. Las muestra en horario de Venezuela.
2. Comprueba fecha y hora desde Configuración de Windows → Hora e idioma → Fecha y hora. Si están equivocadas, corrígelas con ayuda de quien administra esa PC. Aula no cambia el reloj automáticamente.
3. Pulsa **Volver a comprobar**. Corregir Windows por sí solo no borra una revisión pendiente.
4. Entra como **Administrador de Aula**. Caja y Consulta no pueden confirmar. Marca que revisaste la fecha y pulsa **Confirmar fecha y hora**. Si la fecha volvió a cambiar o dejaste pasar varios minutos, vuelve a comprobarla.
5. Confirma la tasa BCV de ese día y revisa saldos antes de continuar. La confirmación queda en la bitácora con usuario, hora detectada, referencia anterior y hora aceptada.

Durante el bloqueo puedes cerrar sesión y, como administrador, descargar un respaldo. No se permite continuar por otro botón o llamando directamente al endpoint de cobros. La impresión desde el botón de Aula también comprueba el reloj. Los PDF ya descargados fuera de Aula no se pueden retirar ni impedir que se impriman.

## Primera revisión y archivos de control

Al actualizar una instalación que ya tiene actividad, o al llevar una base a otra PC, puede aparecer una revisión inicial si falta el control del reloj. Confirma la fecha real antes de trabajar. Una instalación nueva sin actividad comienza con el reloj del equipo: sin una referencia anterior o una fuente externa de hora no se puede demostrar automáticamente que esa primera fecha sea correcta.

El control está en `clock-status.json`, junto a la base, sin cambios de esquema SQLite. No lo borres ni edites para quitar un aviso. Si está dañado, se bloquea la operación y se conserva el original al confirmar. Si no puede guardarse, el sistema permanece bloqueado. La bitácora se guarda antes de desbloquear; un fallo al publicar el control conserva la restricción.

La confirmación no extiende sesiones existentes. Si alguna tenía un vencimiento excesivo por una fecha futura, se limita a un máximo de doce horas desde la fecha aceptada. Esto no implementa todavía el cierre por inactividad del punto 4.

## Respaldos con fechas futuras

Las copias siguen creándose cada cinco minutos y después de operaciones financieras. Se pueden crear durante la revisión del reloj: respaldar no genera mensualidades.

La conservación usa un orden de publicación guardado en `.aula-backup-history.json` en cada destino. Una copia nueva queda después de las anteriores aunque el reloj retroceda o su nombre tenga una fecha menor. Se conservan 30 diarias y 90 automáticas por destino. Las copias previas a actualizaciones, vaciados o restauraciones no se borran por esa regla.

Las copias antiguas que no tenían registro de orden se incorporan una sola vez usando metadatos del archivo; no se puede reconstruir con certeza su orden real anterior. Desde que se registran, el orden nuevo no depende del reloj. Si el registro está ilegible, no se autoriza eliminar copias por esa información. Una copia ya verificada puede seguir llegando al segundo destino aunque falle su registro de conservación; aparece un aviso y puede acumularse más espacio hasta revisarlo.

No edites el registro ni cambies la fecha con datos reales para probarlo. La retención tiene pruebas con nombres y fechas de archivo futuros, seguidos de una corrección del reloj.

## Qué comprobar en el colegio

- Si aparece revisión inicial, confirma como administrador una fecha y hora contrastadas desde Windows.
- Comprueba que Caja ve el bloqueo y no puede confirmar; no uses datos reales para provocar cambios de reloj.
- Después de confirmar, verifica la tasa del día, último recibo y un saldo conocido.
- Si el reloj se vuelve a desajustar al apagar la PC, solicita revisar la pila CMOS y la sincronización de Windows. Un aviso tras una suspensión prolongada debe revisarse, no ignorarse.
- Conserva respaldos externos. Este control no reemplaza un UPS ni certifica la hora mediante internet; tampoco repara mensualidades erróneas creadas antes de esta actualización.
