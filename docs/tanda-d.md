# Tanda D · diseño y evidencia

Trabajo autorizado completo, por cambios pequeños. Firma del instalador y publicación de huellas fuera del alcance.

## D1 · limpieza

Evidencia previa: packaging/Aula.iss:41 empaquetaba todo HTML; las líneas 133–134 de retired-files.iss eliminaban privilegios-personal, no lo incluían. server.py:67 y :102 exponían settings completos. db.py:198–199 ya derivaba el año; el asistente en app.js:127 no pedía calendario. app.js:367 ya ocultaba Nómina, pero server.py:358 aceptaba la categoría por API. network.py:20–24 limitaba el origen a Tailscale; desktop.py:105–109 permitía activarlo. El servidor solo escuchaba en loopback.

Diseño aplicado: lista explícita de manuales del colegio; internos conservados solo en repositorio. id_floor_* se conservan en SQLite y se omiten en el estado de todos los perfiles. Primer inicio pide calendario con fecha local de Venezuela. Nuevos egresos rechazan Nómina, incluidos variantes de mayúsculas y acento; históricos intactos. Acceso privado retirado, incluyendo activación por Windows, CLI y scripts; una configuración antigua de cliente nunca crea una base local por accidente. Se conservan Host, Origin, CSRF, permisos y sesiones.

Línea base local: unittest 292 pruebas en 163,338 s, 289 correctas y tres exclusivas de Windows omitidas. Navegadores normal, demo y roster correctos. Restricción inicial de sockets resuelta mediante ejecución autorizada. cryptography 50.0.0 instalado.

Pruebas D1: 15 pruebas en 5,335 s, 14 correctas y mutex exclusivo de Windows omitido. Incluyen API real, conservación de egresos históricos y totales de caja/reporte, privacidad por perfil, rechazo de red y protección contra abrir datos vacíos. Validación final de toda la tanda pendiente.
