# Tanda D · diseño y evidencia

Trabajo autorizado completo, por cambios pequeños. Firma del instalador y publicación de huellas fuera del alcance.

## D1 · limpieza

Evidencia previa: packaging/Aula.iss:41 empaquetaba todo HTML; las líneas 133–134 de retired-files.iss eliminaban privilegios-personal, no lo incluían. server.py:67 y :102 exponían settings completos. db.py:198–199 ya derivaba el año; el asistente en app.js:127 no pedía calendario. app.js:367 ya ocultaba Nómina, pero server.py:358 aceptaba la categoría por API. network.py:20–24 limitaba el origen a Tailscale; desktop.py:105–109 permitía activarlo. El servidor solo escuchaba en loopback.

Diseño aplicado: lista explícita de manuales del colegio; internos conservados solo en repositorio. id_floor_* se conservan en SQLite y se omiten en el estado de todos los perfiles. Primer inicio pide calendario con fecha local de Venezuela. Nuevos egresos rechazan Nómina, incluidos variantes de mayúsculas y acento; históricos intactos. Acceso privado retirado, incluyendo activación por Windows, CLI y scripts; una configuración antigua de cliente nunca crea una base local por accidente. Se conservan Host, Origin, CSRF, permisos y sesiones.

Línea base local: unittest 292 pruebas en 163,338 s, 289 correctas y tres exclusivas de Windows omitidas. Navegadores normal, demo y roster correctos. Restricción inicial de sockets resuelta mediante ejecución autorizada. cryptography 50.0.0 instalado.

Pruebas D1: 15 pruebas en 5,335 s, 14 correctas y mutex exclusivo de Windows omitido. Incluyen API real, conservación de egresos históricos y totales de caja/reporte, privacidad por perfil, rechazo de red y protección contra abrir datos vacíos. Validación final de toda la tanda pendiente.

## D2 · desbloqueo local protegido

Se conserva íntegro el limitador monotónico: cinco fallos, espera progresiva hasta 60 segundos, aislamiento por usuario y dos comprobaciones simultáneas. Hallazgo en server.py:632–640 de la versión previa: la espera se aplicaba antes de comprobar una contraseña correcta. No se permite saltarla desde HTTP sin una prueba local.

Inicio de Windows → Desbloquear acceso local pide usuario y contraseña actuales de Administración. Emite un código aleatorio de 128 bits, válido dos minutos y una sola vez, ligado a la ejecución actual de Aula. No modifica la contraseña. El formulario de login recibe el código en un campo secreto; sigue exigiendo la contraseña correcta. La recuperación tiene una plaza propia para que un ataque no ocupe todas las comprobaciones. Emisión y uso quedan en bitácora sin guardar código ni contraseña. Reiniciar invalida los códigos. El respaldo de SQLite no contiene los archivos temporales de acceso.

Alternativa para el ZIP: python -m colegio.local_login --data-dir CARPETA --username USUARIO. La contraseña se pide sin mostrarla ni pasarla en argumentos. Pruebas: cuatro correctas en 2,656 s, incluyendo ataque, otro usuario, credencial incorrecta, código ajeno, una sola utilización, saturación, reloj monotónico, reinicio y bitácora válida.
