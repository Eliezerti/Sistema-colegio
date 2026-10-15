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

## D3 · resumen e historial bajo demanda

Evidencia: snapshot en server.py:58–127 cargaba todo el historial en cada estado; app.js calculaba la pantalla principal desde esas listas. Se mantiene el cálculo completo de saldos, reportes y morosidad; la API principal proyecta únicamente resúmenes completos, cinco cobros recientes, cinco deudores y cinco vencimientos, con cantidades y totales de la semana calculados antes de limitar. history=1 solicita el libro completo. La interfaz carga el historial al navegar o abrir operaciones y conserva las pantallas y documentos existentes. Las pruebas del libro completo ahora lo piden explícitamente; la respuesta predeterminada tiene su prueba propia. Sin migración.

Medición real Linux por HTTP, una ejecución de calentamiento y tres medidas; mediana, sin compresión. Datos ficticios: diez cargos y tres pagos por alumno y año; sin logo personalizado.

| Alumnos | Años | Cargos | Pagos | Completo, bytes | Principal, bytes | Principal, segundos |
|---|---|---|---|---|---|---|
| 500 | 1 | 5000 | 1500 | 2642112 | 7017 | 0.0517 |
| 500 | 2 | 10000 | 3000 | 4958241 | 7059 | 0.0827 |
| 500 | 3 | 15000 | 4500 | 7277354 | 7065 | 0.1075 |
| 800 | 1 | 8000 | 2400 | 4229112 | 7017 | 0.0833 |
| 800 | 2 | 16000 | 4800 | 7943242 | 7060 | 0.1228 |
| 800 | 3 | 24000 | 7200 | 11656156 | 7067 | 0.1716 |

Objetivo menor a 1 MB y 1 s: alcanzado en esta máquina Linux, incluso con 800 alumnos y tres años. No se extrapola a Windows: medición nativa pendiente. La CPU todavía recorre el historial para conservar totales; la carga completa bajo demanda puede superar 1 MB. Dos pruebas específicas correctas en 2,609 s y navegador normal correcto. La primera repetición del navegador detectó que su ayudante de navegación no esperaba la carga asíncrona; se ajustó a esperar la pantalla activa y la repetición pasó.

## D4 · conservación y prueba externa

storage.py:112–143 ya publicaba ciphertext verificado al segundo destino; backup_retention.py conservaba únicamente 90 copias frecuentes allí. Se añaden niveles independientes de 60 días y 24 meses, copiando solo ciphertext ya verificado, mediante temporal, comparación y publicación atómica. Se conserva el orden de publicación resistente a retrocesos del reloj. Las copias permanentes están fuera de los patrones de rotación. El pase valida primero su vista previa y genera una copia cifrada del cierre inmediatamente antes de cambiar el año. No cambia cálculos ni esquema.

Probar respaldo registra una prueba externa únicamente tras éxito y declaración explícita del usuario; es una declaración de origen, no prueba de subida a nube. Recordatorio informativo después de 35 días o si no existe una prueba registrada. La interfaz de Windows también puede registrar esa declaración. Pruebas específicas: siete correctas en 1,895 s; límites, inventario corrupto, permanencia, descifrado real y referencia de saldos.

## D5 · consulta aislada de copias

El servidor habitual inicializaba sesiones en SQLite y snapshot sincronizaba mensualidades. Se crea un servidor de consulta separado, sin esos servicios: abre únicamente un temporal verificado, conecta SQLite con mode=ro, immutable y query_only, y rechaza antes de abrir la base todos los POST salvo actividad/cierre de sesión en memoria. Esas dos rutas requieren sesión y CSRF y nunca modifican SQLite. GET utiliza los mismos cálculos y documentos, sin sincronización de mensualidades. Inicio por enlace de un uso con cookie HttpOnly/SameSite, sin usuarios predeterminados ni sesiones importadas.

La copia antigua se migra solo dentro del temporal verificado y se vuelve a comprobar; el archivo original queda intacto. No hay migración de la base real. La fecha visible es la del archivo, explícitamente no certificada. Tres pruebas de servidor correctas en 4,473 s: todas las rutas de escritura descubiertas más rutas nuevas desconocidas, cifrado con contraseña y recuperación sin llaves de origen, contraseña errónea, corrupción, esquema nuevo, fixture publicado antiguo, integridad, ausencia de mensualidades nuevas, hashes del origen y temporal, y limpieza al cerrar. Chromium real correcto: aviso permanente, navegación e historial, sin confirmación de tasa, escrituras rechazadas y libro intacto. El recorrido normal incorpora esta comprobación.

## D6 · reportes

El reporte diario previo detallaba alumnos morosos, pero no agrupaba por grado; daily_report en directory_reports.py:150 calculaba los totales generales. Se añade una sección por grado con cantidad de alumnos y vencido USD, sin cambiar las secciones previas ni sus sumas. El informe mensual ofrece JSON, PDF y CSV y separa moneda/método, saldo previo, cobrado, egresos y saldo acumulado hasta fin de mes. Usa importes y conversiones originales, estado actual de anulaciones y pendiente actual por grado de cargos con vencimiento hasta ese mes. Se explica que no reconstruye una foto histórica ni certifica efectivo contado. Las anulaciones realizadas en el mes provienen de la fecha de bitácora convertida a Venezuela, aunque el movimiento anulado sea anterior. No incluye nombres, códigos, documentos ni teléfonos de alumnos. CSV protege fórmulas.

Once pruebas correctas en 4,625 s: reportes previos, matriz completa de perfiles, totales/caja idénticos tras generar informes, PDF/CSV, separación de monedas, privacidad y anulaciones. Primer intento detectó un supuesto de orden de secciones del reporte diario: se mantuvo el orden original y se añadió la nueva sección al final. La prueba mensual usa fechas coherentes con su mes y tasa registrada.

## D7 · validación de entrega

Se incorpora la actualización real 1.0.67 entre los instaladores históricos y el nuevo, comprobando filas, importes, integridad y eliminación de guías internas y antiguas. La cuenta estándar real también prueba un archivo cifrado con contraseña y con recuperación: Probar respaldo, restaurar, consultar y verificar cadena sin almacén de origen. La creación del fixture destruye su almacén antes de trasladar archivo y credenciales ficticios. Se conserva la instalación limpia y la desinstalación que deja los datos. El flujo Tanda D ejecuta cuatro suites, seis medidas HTTP y validación nativa e impresión; entrega únicamente el EXE si todo pasa, sin publicación de huellas ni firma digital.

Cortes de procesos reales: cobro (test_system), respaldo SQLite y publicación cifrada (test_operation_kills/test_backup_crypto), restauración (test_restore_safety), migración publicada (test_staff_retirement) y borrado de ficha (test_operation_kills). Se añaden cortes durante copia por niveles, antes de publicar y después de publicar. No se sustituyen por excepciones simuladas. Se mantiene la referencia publicada de caja/reportes tras el retiro.

Primera suite conjunta D1–D6: 299 pruebas en 171,540 s, un fallo y un error. El control nuevo de login usaba una vía de escritura que no satisfacía la prueba de sincronización Windows; se reutiliza atomic_json, ya probado. La prueba de fallo del segundo destino se actualiza para exigir conservación byte a byte de todas las copias anteriores, incluidos los niveles nuevos. Repetición específica: siete correctas en 8,076 s. Los tres recorridos de navegador de esta ronda pasaron. Repetición completa y Windows pendientes.

La guía Pruebas físicas detalla corte eléctrico, impresora y restauración en otra PC. No se presentan como ejecutados desde un runner.
