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

## Tokens y compatibilidad

El token aleatorio de 256 bits permanece en la cookie HttpOnly, SameSite=Strict y Secure cuando corresponde. En SQLite se guarda **solo SHA-256 del token**, con un prefijo de formato. Copiar ese valor no sirve como cookie. No se guardan tokens en claro en la base, bitácora ni configuración.

No hay migración de esquema: se reutilizan `sessions` y `settings`; solo el estado de autenticación es descartable. Las sesiones anteriores se eliminan al iniciar el servidor y el registro monotónico empieza vacío. Los respaldos siguen excluyendo sesiones autenticadas. No se modifican fichas, cargos, importes, recibos, motor de nómina ni la ubicación de datos. A1, A2, WAL/FULL, CSRF, permisos, control del reloj y respaldos de cinco minutos se mantienen.

Esto no impide que alguien con acceso a tu cuenta de Windows examine memoria, modifique el programa o lea datos sin cifrar. Los borradores son temporales y dependen de conservar abierta la ventana.

## Prueba manual con datos ficticios

1. En Aula - Pruebas entra como Administrador temporal. En Usuarios y acceso elige **5 minutos** y guarda.
2. Abre Nuevo representante y escribe un nombre ficticio sin guardar. Deja de usar la ventana. No uses datos personales reales en esta prueba.
3. Aproximadamente un minuto antes del cierre aparece el aviso. Pulsa Seguir trabajando: el formulario debe continuar intacto.
4. Vuelve a dejar la ventana inactiva. Al vencer debe ocultar formulario, datos y documentos.
5. Entra con el mismo administrador de prueba y confirma la tasa. Recupera el borrador, revisa que no apareció ningún representante nuevo y cancélalo.
6. En una cuenta de Windows o PC de prueba separada, con una base ficticia, crea dos administradores y Caja. Abre sesiones de las cuentas, cierra Aula y recupera la clave de un administrador. Al reiniciar, las cookies anteriores no sirven y cada administrador recibe su aviso.
7. Falla cinco veces una contraseña ficticia. Debe aparecer la espera; otra cuenta debe poder ingresar desde la misma PC. No hagas esta prueba con tu única cuenta real de trabajo.

## Validación y entrega

Validación Linux: **259 pruebas descubiertas en 135.019 s, 256 correctas y tres exclusivas de Windows omitidas** (mutex/ventana nativa/DPAPI). Los tres recorridos de navegador pasaron con el código final: normal (incluye A3 y fallos del borrador), Pruebas e importación. La primera compilación 1.0.36 pasó las 259 pruebas nativas (288.365 s, sin omisiones), instalación/ventanas/actualización/desinstalación y ambos análisis de Defender. Se reemplaza en la entrega por la revisión final que garantiza ocultar datos incluso al fallar la captura del borrador; la entrega final 1.0.37 pasó también **259 pruebas en Windows en 376.416 s, sin omisiones**, más instalación, accesos, ventanas normal/Pruebas/bandeja, reinstalación y desinstalación con conservación de datos. Las cuatro suites exigidas se ejecutaron realmente. También se prueba rollback de recuperación si falla el aviso, reconocimiento antiguo rechazado, aviso ilegible explícito y liberación del control de acceso al fallar la verificación. La prueba de navegador acelera solo el aviso visual y revoca la sesión en el servidor real; las pruebas Python avanzan el reloj monotónico para verificar el vencimiento efectivo sin esperar quince minutos.

La bitácora con cadena de hashes, restricciones de datos bancarios y otras tandas siguen pendientes de aprobación; A3 no las implementa.

Archivos de A3: colegio/sessions.py, login_limiter.py, security_notices.py, server.py y reset_password.py; static/session.js, app.js, index.html y style.css; tests/test_sessions.py (17 métodos nuevos), test_clock_endpoints.py (umbral actualizado), session_browser.cjs y browser.cjs; README, CHANGELOG, guías de sesiones/configuración/mantenimiento Markdown y HTML, notas del workflow Windows y ZIP fuente/suma. No hay cambios en módulos de nómina, archivos móviles/PWA, motor financiero ni esquema.

Commits de implementación: 8fb4087 (sesiones y recuperación), 9c9ff87 (fallos y reversibilidad), 728b49a (aviso, borradores y manuales).

## Instalador final 1.0.37

[Descargar la entrega A3](https://github.com/Eliezerti/Sistema-colegio/releases/tag/untagged-f612cb9336e27ef27bd0). Archivo **Aula-Colegio-Instalador-1.0.37.exe**, 23233045 bytes. SHA-256 **6492167f388f77a76fff97846c06d3aadf32044b1b84c5ba33ad0e561cc81405**. Descargado y coincidente con su sidecar y ambos registros de análisis. Defender: motor 1.1.26080.3, firmas 1.459.691.0, sin detecciones antes/después. Runner 38333489104 sobre d5b7a462b1cb37d5bb9c93b39b647c2abd509a7e.

Crea una copia externa, cierra desde Colegio → Salir y cerrar Aula e instala con la misma cuenta de Windows. Usa tus mismos usuario y contraseña de Aula; tendrás que identificarte nuevamente. No uses Vaciar registros ni necesitas restaurar para actualizar.

La compilación inicial 1.0.36 también pasó todas las pruebas; se reemplaza por 1.0.37 por el cierre seguro ante fallos del borrador, no por una detección de Defender. El instalador sigue en borrador porque las alertas antiguas de 1.0.8/1.0.14 no se explican con estos análisis. No desactives Defender ni añadas exclusiones si tu PC lo bloquea. No se añade firma digital en A3.

**No ejecutado:** espera física de quince minutos, captura/recuperación en la PC del usuario, otra cuenta real de Windows, actualización desde el ejecutable histórico 1.0.35 ni pruebas nativas en un WebView2 antiguo. El reloj monotónico se controla en las pruebas para verificar límites, y el navegador simula ausencia de structuredClone y falla de captura; no se presentan como un ensayo en esos equipos. La prueba del instalador usa el instalador actual para la reinstalación. No se cambia ni ensaya una base real de alumnos.

Commits posteriores: 8f7a2e5 (validación Linux/paquete), d5b7a46 (captura segura y prueba de fallos). La entrega no implementa A4/A5 ni las tandas siguientes.
