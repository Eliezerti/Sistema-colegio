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

Pendiente de la compilación y validación nativa en GitHub Actions. Linux no ejecuta el mutex/enfoque de ventanas de Windows ni una consulta real de BitLocker/ACL de Windows. Las respuestas de Windows en las pruebas unitarias de diagnóstico se simulan: no certifican el disco ni los permisos de la PC del colegio.

## Prueba manual del colegio

Sigue la guía [Avisos de respaldo y protección de esta PC](proteccion-respaldos.md#prueba-manual-con-el-administrador-y-caja). No cambies la fecha del equipo con datos reales. Verifica la copia en un USB, su desconexión y reconexión; revisa los perfiles y pide a un técnico que contraste BitLocker/ACL desde Windows.
