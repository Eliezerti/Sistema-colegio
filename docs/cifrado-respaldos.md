# Respaldos cifrados · A2

## Configurar una sola vez en Windows

1. Instala la versión A2 con la misma cuenta de Windows, conservando datos y copias anteriores. Cierra Aula completamente antes de actualizar. No uses Vaciar registros.
2. Como Administrador: Configuración → Protección y mantenimiento → Cifrado de respaldos → Configurar cifrado.
3. Escribe y repite una contraseña de mínimo 12 caracteres. Es distinta de la de entrar a Aula; usa una frase larga y guarda la contraseña en tu gestor.
4. Guarda la clave de recuperación completa fuera de la PC y separada de los respaldos. Se muestra una sola vez. Imprimir no genera un archivo desde Aula, pero utiliza la cola de Windows: no guardes un PDF en esta PC ni en la carpeta de copias.
5. Escribe los últimos cuatro caracteres y pulsa Guardé la clave · activar cifrado. Cerrar sin confirmar deja la configuración anterior intacta; la preparación vence en diez minutos.
6. Revisa el segundo destino. La última copia debe indicar Cifrada y verificada. Si falta el USB o falla, las copias locales continúan y el aviso permanece. Aula confirma escritura, no subida a Drive; compruébala en Drive.

**Si pierdes la contraseña y la clave de recuperación de una copia portátil, esa copia NO se podrá recuperar sin otro material de clave válido.** La cuenta Windows original conserva material derivado protegido para realizar automáticamente las copias; no hay un botón para mostrar la contraseña ni la clave de recuperación. BitLocker protege el disco local, no sustituye este cifrado de archivos.

## Cambiar contraseña

Cambiar contraseña de respaldos → escribir/repetir → confirmar CAMBIAR CONTRASEÑA DE RESPALDOS. La contraseña nueva afecta SOLO copias nuevas. Las anteriores necesitan su contraseña de entonces o la clave de recuperación. La recuperación existente se conserva y no se muestra otra vez. Mantén las contraseñas anteriores mientras conserves esas copias.

En Windows el almacén protegido se abre automáticamente con esa cuenta, sin pedir contraseña cada cinco minutos. En Linux el material solo vive en RAM: Desbloquear cifrado tras cada inicio. Si el almacén falla, no hay salida sin cifrar de emergencia; el respaldo local de cinco minutos sigue funcionando.

## Qué se cifra y qué permanece sin cifrar

| Ruta/copia | Estado A2 |
|---|---|
| Segundo destino automático, también después de cobros o Crear respaldo ahora | Cifrada .aulabak, verificada antes de confirmar |
| Descargar copia | Cifrada .aulabak |
| Copia al segundo destino antes de Vaciar registros o Borrar ficha | Cifrada .aulabak; fallo cancela la operación |
| Convertir y descargar cifrado desde Probar respaldo | Copia nueva cifrada; original intacto |
| Locales automáticas de cinco minutos / diarias | SQLite sin cifrar, límites existentes 90/30 |
| Locales antes-restauracion, originales-antes-restauracion y danado-antes-restauracion | Sin cifrar; conservadas |
| Local candidata de A1 e informes de pérdida PDF/CSV | Sin cifrar; conservados |
| Locales antes-vaciar, antes-borrar-ficha | SQLite sin cifrar; conservadas |
| Locales antes-actualizacion y recuperacion-clave | SQLite sin cifrar; conservadas |
| Almacén .backup-crypto/keyring.json | DPAPI Windows, fuera de SQLite y de la exportación |

Todas las copias locales sin cifrar dependen de BitLocker del disco y de los permisos de la carpeta. No se mueve la base ni se modifica su ubicación. El cifrado no se aplica a recibos/PDF cotidianos ni cambia importación o cálculo financiero.

Aula protege las salidas que gestiona; no puede controlar el Explorador ni un programa de sincronización externo. **No copies la base activa, carpetas locales de originales o .sqlite3 sin cifrar a un USB/Drive.** Para una copia SQLite válida, Probar respaldo → seleccionar → Convertir y descargar cifrado. Los originales dañados de recuperación son para revisión técnica local, no se presentan como respaldos válidos exportables.

## Copias antiguas ya existentes

No se borran ni modifican automáticamente. Probar respaldo y Restaurar admiten .sqlite3 con advertencia Respaldo antiguo sin cifrar. Para convertir: selecciona la copia antigua en Probar respaldo, pulsa Convertir y descargar cifrado, guarda el .aulabak y compruébalo con contraseña/recuperación. Se conserva el original.

Crear un equivalente cifrado NO elimina versiones antiguas sin cifrar en Drive, su papelera o su historial. Cualquier eliminación posterior requiere tu decisión; A2 no lo hace. La rotación externa solo limita las nuevas automáticas .aulabak a 90; no incluye .sqlite3 antiguos, conversiones ni copias especiales.

## Retención de copias especiales

Conservación indefinida por defecto, sin limpieza automática. Revisión manual sugerida cada tres meses: identificar operación, espacio, disponibilidad de copias cifradas verificadas y necesidad de recuperar el estado anterior. Nunca borrar las relacionadas con una recuperación pendiente. Antes de eliminar cualquiera, pedir autorización expresa. A2 no incorpora un botón de depuración ni cambia estos respaldos.

## Abrir o restaurar en otra PC

Instala esta versión o una posterior. Basta el archivo .aulabak + su contraseña original O la clave de recuperación, no ambas. No necesitas el almacén DPAPI ni la cuenta Windows de la PC anterior.

- Probar respaldo: Configuración o Inicio → Probar respaldo, seleccionar y escribir credencial. Hasta 32 MB en la ventana; hasta 512 MB en el formato nativo, sujeto a memoria disponible.
- Restaurar: cerrar Aula completamente → Inicio → Restaurar respaldo → seleccionar .aulabak → contraseña o recuperación → revisar comparación A1 → escribir su confirmación. Mantiene esquema/integridad/referencias, correlativos, informes y resolución de interrupciones.
- Después inicia con el usuario/contraseña de Aula guardados en la copia. En la nueva PC configura la protección de las nuevas copias. Restaurar NO importa ni retrocede el almacén/contador de cifrado; en la PC original mantiene su configuración actual.

No envíes la contraseña/recuperación en el mismo mensaje que el archivo. No guardes ninguna junto al respaldo en Drive.

## Prueba manual con datos ficticios

Usa otra cuenta Windows/PC sin información real. Configura y guarda la recuperación; registra alumno/cargo/pago ficticios. Descarga A y comprueba contraseña y recuperación desde Inicio. Cambia contraseña, descarga B y comprueba: A abre con antigua, B con nueva y ambas con recuperación. Prueba una contraseña incorrecta: debe fallar sin restaurar. Restaura A tras otro pago ficticio y comprueba la comparación/informes y que no se repita el correlativo, igual que la guía A1. No cortes energía ni mates procesos con datos reales; las pruebas automatizadas usan bases temporales.

## Alcance y resultados

Sin migración SQL, sin cambio de ubicación y sin avanzar a A3. A1, WAL, synchronous=FULL, CSRF, roles, reloj, avisos y frecuencia local permanecen. La impresión y la memoria/paginación son gestionadas por Windows; no se promete borrado forense ni defensa ante quien controla Windows. El hash/AEAD detecta alteración, no impide borrar archivos. Mantén copias y UPS.

Formato detallado: [AULABK01](formato-respaldo-cifrado.md). Validación Linux final: 242 pruebas descubiertas en 129.630 s, 239 correctas y tres exclusivas de Windows omitidas (mutex/ventanas, diálogo Tk y DPAPI). Los comandos python tests/run_browser.py, --demo y --roster terminaron correctamente. Diecinueve métodos nuevos cubren las credenciales, nonces, integraciones, esquema 99, vectores y cortes; los cinco cortes son subcasos de un método. Windows/instalador/Defender se ejecutaron por separado y están documentados abajo.

El primer diagnóstico completo encontró expectativas antiguas de copias SQLite externas y un dato obligatorio omitido en una fixture de pago; se adaptaron para descifrar/verificar, manteniendo las comprobaciones financieras y de fallos. El primer recorrido de navegador detectó una espera sobre una tabla de tasa anterior: ahora espera la sustitución real del formulario después de guardar. No se cambió el motor de tasas ni se omitieron comprobaciones.

La guía HTML instalada está enlazada desde mantenimiento. El comprobador y restaurador nativos permiten elegir Contraseña del respaldo o Clave de recuperación; no dependen de que la base activa pueda abrirse. La prueba del ejecutable empaquetado incluye cifrado y descifrado por ambas rutas, con credenciales ficticias.

## Entrega Windows 1.0.35 · resultados reales

[Descargar instalador en borrador](https://github.com/Eliezerti/Sistema-colegio/releases/tag/untagged-3e6bb27e7d59ebbe89ea): **Aula-Colegio-Instalador-1.0.35.exe**, no el ZIP fuente. Instala con la misma cuenta Windows, con una copia previa conservada y Aula completamente cerrado. No uses Vaciar registros para actualizar.

[Runner 38311993958, intento 2](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38311993958/attempts/2), Windows 2022/Python 3.12, commit **c82dc0d30ee4082d40bcb5afeef61600a209dc29**:

- **242 pruebas correctas en 376.997 s, sin omisiones**; DPAPI real, diálogo/mutex nativos, vectores, A1 y cinco cortes reales aprobados.
- Instalación, accesos, ventanas normal/Pruebas/bandeja, reinstalación y desinstalación conservando huellas de la base y respaldo ficticios. Las autopruebas del ejecutable cifran y abren un archivo con contraseña y recuperación, asegurando que las primitivas/dependencias quedaron incluidas; no usan datos reales.
- Defender antes y después: motor **1.1.26080.3**, firmas **1.459.690.0**, sin detecciones.
- Ejecutable descargado: **23220929 bytes**, SHA256 **af8bdbf4f1f496518db8d4182f04b4ca338671336b25b47113c8fae60abda7e1**, comprobado contra el sidecar y ambos registros de análisis.
- Intento 1: 242 unitarias correctas en 317.509 s; actualización de firmas falló por los dos canales oficiales y detuvo el flujo antes de analizar/ejecutar/publicar. Se repitió en un worker nuevo y el intento 2 completó todos los controles, sin omitirlos ni usar firmas de emergencia.

No se probaron tu PC real, tu impresora/cola, restauración de datos reales, otra cuenta Windows ni actualización entre ejecutables antiguos. Sí se probó restauración autónoma en otra carpeta con archivo + credencial, sin almacén original. Los análisis solo describen ese ejecutable y firmas: no explican las alertas antiguas de 1.0.8/1.0.14 ni garantizan detección universal. No desactives Defender ni añadas exclusiones para abrir un archivo bloqueado. El instalador sigue sin Authenticode; firma/reducción pertenecen a puntos posteriores.

## Archivos y commits

- Núcleo nuevo: colegio/backup_crypto.py, backup_keys.py, backup_export.py, backup_setup.py, backup_work.py y backup_temporary.py.
- Integración: colegio/backup_inspection.py, backup_health.py, storage.py, restore.py, server.py, institution_archive.py. Solo cambia publicación externa de borrado de fichas sin movimientos; no modifica su política, bitácora general, nómina o transacciones financieras.
- Interfaz: colegio/desktop.py y static/app.js. Dependencias: requirements.txt / requirements-desktop.txt. Empaquetado: tests/package_windows.py, .github/workflows/windows-desktop.yml, descargas/Aula-Windows.zip/.sha256.
- Pruebas nuevas: tests/test_backup_crypto.py (16 métodos, uno DPAPI exclusivo Windows) y tres métodos de API en tests/test_system.py, total **19**. tests/crypto_helpers.py contiene únicamente credenciales ficticias. Adaptaciones: tests/restore_helpers.py, test_recovery.py, test_admin_safety.py, test_backup_alerts.py, test_backup_retention.py, test_institution_archive.py, test_network.py y browser.cjs. Se descifran las nuevas copias antes de conservar las verificaciones financieras/recuperación existentes; no se reemplazan por comprobaciones vacías.
- Documentación: README.md, CHANGELOG.md, docs/cifrado-respaldos.md/.html, formato-respaldo-cifrado.md, mantenimiento.md/.html y restauracion-segura.md/.html.
- Commits: **8e726c5** (núcleo/salidas/A1), **b2219c1** (configuración/Windows/impresión), **c82dc0d** (distribución). La documentación final no cambia el código validado.

La preparación del entorno cloud se actualizó en borrador para instalar requirements.txt y explicar el desbloqueo RAM de Linux; no cambia Windows ni publica el entorno. A2 termina aquí y no inicia A3.
