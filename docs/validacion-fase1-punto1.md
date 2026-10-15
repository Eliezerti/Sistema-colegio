# Validación · Fase 1, punto 1

## Alcance

Avisos permanentes de respaldo para Administrador y Caja, y revisión de ACL/BitLocker de solo lectura. Sin migración de esquema, movimiento de base ni cambios en datos existentes. No incluye protección del reloj, cifrado de copias, sesiones, nueva bitácora ni SQLCipher.

## Resultados ejecutados en Linux

| Comando | Resultado |
|---|---|
| `python -m unittest discover -s tests -v` | 158 pruebas descubiertas: 157 correctas y una exclusiva de Windows omitida. |
| `python tests/run_browser.py` | Correcto: flujo principal, avisos en tasa y aplicación, persistencia con búsquedas/archivados, actualización y resolución, Administrador/Caja/Consulta, cobros, documentos y PDF. |
| `python tests/run_browser.py --demo` | Correcto: datos temporales independientes y borrado al cerrar. |
| `python tests/run_browser.py --roster` | Correcto: exportación/importación Excel/CSV, estados, documentos y conservación de la base de origen. |

Se añadieron 18 pruebas unitarias/de integración: 9 de avisos y 9 de protección. Las pruebas de avisos cubren el límite exacto de tres días, zonas horarias equivalentes, fecha externa desconocida, destino cambiado, errores locales/externos, estado corrupto, recuperación después del error, autenticación, perfiles, CSRF y aislamiento de Pruebas. Las de protección cubren BitLocker completo/suspendido/incompleto, ACL adicional/compleja, herramientas ausentes, salida inválida, timeout, rutas que contienen caracteres especiales y ejecución en segundo plano.

La suite incluye los controles financieros anteriores; no se reemplazaron por pruebas superficiales. Las pruebas usan bases temporales y personas ficticias.

## Windows

La [compilación 1.0.26](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38197453462) terminó correctamente. Ejecutó 158 pruebas en 141,143 segundos, sin omisiones. La prueba del instalador confirmó instalación, accesos, ventanas normal/Pruebas, bandeja, reinstalación y desinstalación conservando los archivos de datos. Es reinstalación de la misma versión; no se presenta como una prueba entre versiones distintas.

Comandos ejecutados por el flujo de Windows:

```powershell
./packaging/build_windows.ps1 -Version "1.0.26"
./packaging/scan_windows.ps1 -Path dist
./packaging/test_installer.ps1 -Version "1.0.26"
./packaging/scan_windows.ps1 -Path dist -ReportDir "$env:RUNNER_TEMP/defender-after-runtime"
```

El primer comando ejecutó `python -m unittest discover -s tests -v` antes de compilar. Defender terminó sin detecciones antes y después de las pruebas, motor `1.1.26080.3`, firmas `1.459.678.0`. El instalador descargado de la publicación en borrador tiene 20.472.557 bytes y el mismo SHA-256 que el archivo analizado y su archivo de hash:

```text
5af7f253eda03dc5bd913780190d32e792832cba5e51bce964e5c20f59a41067
```

Se revisaron los registros de GitHub Actions. El ZIP adicional de evidencia Defender no se pudo descargar desde este entorno (HTTP 403 del almacenamiento de artefactos); sigue disponible en la ejecución. Esto no impidió comprobar los resultados y el hash registrados ni descargar/verificar el instalador.

Linux no ejecuta el mutex/enfoque de ventanas de Windows. Las pruebas unitarias de clasificación simulan las respuestas de Windows; la ejecución del servidor en Windows usa la consulta real. Ningún resultado del runner certifica BitLocker ni los permisos de la PC del colegio. Falta contrastarlos allí con un técnico. Tampoco se resolvieron por estos análisis las detecciones anteriores de Defender reportadas para 1.0.8 y 1.0.14.

## Archivos del cambio

- Servidor: `colegio/backup_health.py`, `colegio/protection.py`, `colegio/server.py`, `colegio/storage.py`.
- Interfaz: `static/app.js`, `static/style.css`. La protección continúa en la versión enfocada en mensualidades.
- Pruebas: `tests/test_backup_alerts.py`, `tests/test_protection.py`, `tests/browser.cjs`.
- Documentación: `README.md`, `CHANGELOG.md`, `docs/mantenimiento.md`, `docs/mantenimiento.html`, `docs/proteccion-respaldos.md`, `docs/proteccion-respaldos.html`, `docs/revision-defender.md` y este informe.
- Entrega: `.github/workflows/windows-desktop.yml`, exclusivamente notas y título del borrador para describir el punto 1.

Código y pruebas: commit `a71fc552664f8db6a8b09d8d2eb7dd357a308828`. [Compilación Windows de este commit](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38197453462).

## Prueba manual del colegio

Sigue la guía [Avisos de respaldo y protección de esta PC](proteccion-respaldos.md#prueba-manual-con-el-administrador-y-caja). No cambies la fecha del equipo con datos reales. Verifica la copia en un USB, su desconexión y reconexión; revisa los perfiles y pide a un técnico que contraste BitLocker/ACL desde Windows.

Instalador 1.0.26: [publicación en borrador para revisión del propietario](https://github.com/Eliezerti/Sistema-colegio/releases/tag/untagged-a372996b67d6dee4a93b). Inicia sesión en GitHub con la cuenta propietaria para ver el borrador. Crea un respaldo externo, cierra Aula completamente e instala con la misma cuenta de Windows. No uses Vaciar registros.
