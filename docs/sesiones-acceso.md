# Sesiones y recuperación de acceso · A3

## Qué cambia al actualizar

Aula cierra la sesión después de **15 minutos sin actividad**. Administración puede elegir entre 5 y 60 minutos en **Configuración → Usuarios y acceso → Cierre por inactividad**. Se aplica a Administración, Caja, Consulta y Pruebas. El cambio se registra con el tiempo anterior y el nuevo, y se aplica también a las sesiones que ya estaban abiertas.

Un minuto antes aparece **Tu sesión está por cerrarse**, con un contador y **Seguir trabajando**. Pulsar ese botón mantiene una sesión que todavía está vigente. No puede recuperar una sesión ya vencida.

Escribir, pulsar botones y desplazarse por la página cuenta como actividad. La ventana envía un aviso de actividad como máximo una vez cada 15 segundos normalmente; cerca del vencimiento lo envía inmediatamente. Las comprobaciones automáticas de tasa, reloj, respaldo y presencia de Pruebas no renuevan la sesión. Un estado consultado por otra pestaña tampoco cuenta como actividad; la actividad humana en otra pestaña de la misma sesión sí cuenta en el servidor.

El servidor comprueba la vigencia antes de atender consultas, PDF, cobros y modificaciones. El cierre no depende de que se vea el aviso, de la hora de Windows ni de un contador del navegador: utiliza tiempo monotónico. También mantiene un máximo de **12 horas desde el ingreso**, aunque haya actividad; ese máximo no se renueva. La columna de vencimiento por fecha permanece por compatibilidad, pero no decide ni extiende la autenticación.

Cerrar Aula completamente y volver a abrirlo exige iniciar sesión nuevamente. La X puede dejar el programa funcionando en la bandeja; para cerrarlo usa **Colegio → Salir y cerrar Aula**. La actualización invalida las sesiones anteriores, no cambia usuarios ni contraseñas.

## Un formulario a medias

Si vence la sesión, se ocultan los datos y los documentos de la ventana. Los formularios administrativos habituales se conservan **solo en memoria de esa ventana**. Tras entrar con el mismo usuario y perfil, confirmar el reloj si hace falta y confirmar la tasa, puedes retomar el borrador.

- **No se guarda ni se envía automáticamente.** Revisa los datos y saldos actualizados antes de guardar.
- Las contraseñas se vacían. El formulario de configuración de cifrado, la clave de recuperación mostrada, los archivos seleccionados, las pantallas de documentos y las revisiones de operaciones masivas o destructivas no se conservan. Deben revisarse otra vez.
- Entrar con otro usuario o con un perfil distinto descarta el borrador anterior.
- Cerrar sesión voluntariamente, recargar/cerrar la ventana o cerrar Aula pierde el borrador. No se guarda en localStorage, sessionStorage, archivos ni la base.
- Si falla la conservación del borrador, el cierre oculta igualmente la información y avisa que no se pudo conservar; no presenta una recuperación falsa. La captura no depende de la función structuredClone de WebView2.
- Si no hay conexión, el cierre oculta la información igualmente. No intentes repetir un cobro sin revisar si quedó registrado; las claves de solicitud e idempotencia originales siguen vigentes.
- Una ventana cerrada, una falla de Windows o la pérdida de energía no permiten recuperar lo que todavía no se había guardado.

## Recuperar una contraseña

Si nadie puede ingresar: cierra Aula completamente → **Inicio de Windows → Recuperar clave del administrador** → elige un administrador existente → escribe la contraseña nueva dos veces. La herramienta conserva el respaldo previo verificado y la recuperación sigue siendo local; no envía correos ni revela contraseñas.

La recuperación local **cierra todas las sesiones, de todas las cuentas**. En la misma transacción guarda la nueva clave, invalida las sesiones, registra el evento y deja un aviso. Cada administrador verá el aviso de la recuperación más reciente al ingresar, hasta pulsar **Ya revisé este aviso**. Confirmarlo para una cuenta no lo oculta para otros administradores. El aviso persiste al reiniciar y no contiene contraseñas. Si el registro está ilegible, se muestra que no se pudo leer y no se presenta como revisado.

El cambio habitual de clave desde **Usuarios y acceso → Cambiar clave** conserva su funcionamiento: invalida las sesiones de la cuenta modificada. Es distinto de la recuperación local de emergencia.

## Intentos fallidos

Se cuentan por usuario normalizado y por la combinación de origen y usuario. Los primeros cinco fallos se rechazan; después se espera 5 segundos. Nuevos fallos después de cada espera aumentan el plazo a 10, 20, 40 y un máximo de 60 segundos. Repetir una solicitud durante la espera no la extiende. Un ingreso correcto borra los fallos de esa cuenta; quince minutos sin intentos descartan el historial en memoria.

Los fallos de una cuenta no bloquean a las demás por usar la misma dirección local `127.0.0.1`. Hay un límite de dos verificaciones de contraseña simultáneas; si está ocupado, se pide intentar nuevamente en un segundo. No es una prohibición permanente de la IP. Las transacciones SQLite y límites de recursos del equipo siguen siendo compartidos: esto no garantiza disponibilidad ante quien controle Windows o sature el equipo. El contador continúa en memoria; reiniciar completamente el servidor lo reinicia.

## Si otros intentos bloquean tu acceso

En la PC del colegio, deja Aula abierto y abre Inicio → Aula → Desbloquear acceso local. Escribe tu usuario de Administración y tu contraseña actual. Copia el código en «Acceso bloqueado por intentos» de la pantalla de ingreso y vuelve a escribir tu contraseña. El código dura dos minutos, se usa una sola vez y no cambia tu contraseña. La emisión y el ingreso quedan en la bitácora. Si olvidaste la contraseña, utiliza Recuperar clave del administrador.
