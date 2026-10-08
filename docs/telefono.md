# Aula en el teléfono

La versión móvil es una **app web instalable (PWA)** para Android y iPhone. Tiene el logo del colegio, un menú para teléfono, formularios con controles táctiles y acceso a las mismas funciones y permisos de tu usuario. No requiere publicar una app en una tienda ni pagar una licencia adicional de Aula.

La PC principal sigue guardando la base. El teléfono no crea otra base ni sincroniza copias. La instalación móvil **no configura la conexión privada** ni mantiene funcionando Aula si la PC principal está apagada.

## Antes de instalar

1. Actualiza Aula en la PC principal a una versión que incluya el acceso móvil. Conserva un respaldo y actualiza con la misma cuenta de Windows.
2. Configura el enlace privado HTTPS del colegio en **Configurar Aula → PC principal**, como se explica en el README. La versión actual utiliza Tailscale Serve; WireGuard todavía requiere una adaptación de la configuración de red del servidor.
3. Instala Tailscale en el teléfono, autorízalo en la red privada del colegio y activa la conexión. Esta instalación de Aula no instala Tailscale ni determina el plan comercial de ese proveedor.
4. Con la PC principal encendida y Aula funcionando, abre **el enlace privado HTTPS del colegio** en el navegador del teléfono. No uses `127.0.0.1:8765`: en el teléfono esa dirección apunta al propio teléfono.
5. Entra con tu usuario de Aula. El administrador debe haber sido creado primero desde la PC principal; los empleados utilizan sus propias cuentas.

## Android

Abre el enlace en **Chrome** y pulsa **Instalar en teléfono** cuando aparezca. También puedes usar el menú de Chrome → **Instalar aplicación** o **Añadir a pantalla de inicio**, según la versión. Aparecerá un icono con el logo del colegio. La app se abre desde ese icono; Tailscale debe seguir conectado.

## iPhone

Abre el enlace en **Safari** → **Compartir → Añadir a pantalla de inicio**. Activa **Abrir como app** si aparece. El botón **Instalar en teléfono** muestra estas instrucciones. La conexión privada debe seguir activa al abrir el icono.

## Uso y conexión

- **Menú** permite entrar a alumnos, caja, morosidad, personal, reportes y demás secciones. Allí también están tu usuario y **Cerrar sesión**.
- Puedes descargar recibos en PDF. Abrirlos, compartirlos e imprimirlos depende del navegador y de las opciones del teléfono. Los archivos que descargues permanecen en el teléfono; protégelos como cualquier documento del colegio.
- Si se pierde internet o la conexión privada, se muestra un aviso. No hay cobros sin conexión ni una cola de pagos pendiente de sincronizar. Si la conexión se cortó mientras guardabas un cobro, revisa Caja y la referencia antes de empezar otro pago.
- La instalación guarda únicamente una pantalla pública de falta de conexión y un icono. **No guarda respuestas de la API, saldos, alumnos, recibos ni contraseñas en Cache Storage.** La sesión utiliza las cookies habituales de Aula.
- Cerrar la app del teléfono no cierra Aula en la PC principal ni borra los registros. La conexión privada y los permisos de Aula son controles distintos.
- Cambiar el enlace privado del colegio requiere abrir el nuevo enlace y volver a añadir el icono. Un icono antiguo no se reconfigura solo.

## HTML editable / empaquetado propio

[Aula-Movil-Web.zip](../descargas/Aula-Movil-Web.zip) incluye HTML, CSS, JavaScript, logo e iconos, manifiesto y la pantalla de conexión. Es código editable de la interfaz; no contiene alumnos, pagos, claves ni la base. El código completo del servidor está en este repositorio.

**Abrir `index.html` directamente como archivo o subirlo a otro alojamiento no crea el sistema.** La interfaz llama a `/api/` y debe ser servida desde el mismo origen HTTPS que el servidor de Aula. El instalador Windows ya incluye esos archivos; no tienes que subir el ZIP para utilizar la PWA.

Si deseas generar un APK mediante otra herramienta, úsala para abrir **el enlace privado HTTPS de Aula** con cookies habilitadas y soporte de descargas PDF. No incrustes una cuenta ni contraseña en el APK. La red privada sigue siendo necesaria. Este paquete no incluye un APK compilado, ni una app publicada en App Store, ni la configuración de un servicio remoto.

## Validación de desarrollo

`python tests/run_browser.py --mobile` abre un navegador Chromium con pantalla táctil de 375 px, matricula un alumno, registra un pago y descarga el PDF en una base temporal. Comprueba las doce secciones, menú, salida, teléfono de 320 px y tablet, archivos de instalación, desconexión, recuperación y ausencia de datos financieros en la caché del service worker.

La prueba usa un origen loopback confiable solo para validar el service worker. El registro automático en el producto se realiza únicamente bajo HTTPS. La instalación y conexión real deben probarse en los teléfonos del colegio con su enlace privado; la prueba de Chromium no sustituye una prueba física de Safari/iPhone.
