# Tanda D · entrega 1.0.68

Implementación terminada y validación nativa correcta el 15/10/2026. Base auditada 1.0.67; programa compilado desde `11fbacf`, sin modificar main. Esquema 12 conservado; no hay migración nueva sobre la base real. No se registraron pagos ni se usaron datos reales.

- [Instalador validado, ZIP con el EXE](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38769010822/artifacts/11992255597).
- [Evidencia nativa: registros, mediciones y PDF ficticios](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38769010822/artifacts/11991821161).
- [Ejecución Windows completa](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38769010822) y [revisión del código](https://github.com/Eliezerti/Sistema-colegio/pull/3).

Los enlaces de artefactos requieren iniciar sesión en GitHub. El ZIP del instalador contiene Aula-Colegio-Instalador-1.0.68.exe; no es el ZIP de código fuente. La firma digital y la publicación de huellas no forman parte de esta tanda.

## Qué quedó listo y dónde se verifica

| Punto | Resultado | Evidencia de implementación |
|---|---|---|
| D1 | Manuales del colegio separados del historial técnico; limpieza de guías antiguas al actualizar; pisos internos omitidos para todos los perfiles; calendario explícito en primer inicio; Nómina rechazada en egresos nuevos, históricos intactos; acceso privado retirado. | packaging/Aula.iss:41, packaging/retired-files.iss:133, colegio/server.py:71, :364 y :661; colegio/network.py:28. |
| D2 | Limitador monotónico conservado y recuperación local con contraseña de Administración, código aleatorio de un uso, dos minutos de validez y bitácora. No cambia la contraseña. | colegio/local_login.py:29 y :52; tests/test_tanda_d.py, LocalLoginTests. |
| D3 | Resumen principal acotado y libro completo bajo demanda; totales completos, cobros recientes y alertas calculadas antes de limitar. La interfaz pide historia al navegar u operar. | colegio/state_view.py:5; tests/benchmark_state.py; PrincipalTests. |
| D4 | Segundo destino cifrado: 90 frecuentes, 60 diarias, 24 mensuales; copia permanente antes del pase escolar revisado; recordatorio informativo tras 35 días sin prueba externa declarada. | colegio/backup_tiers.py:33 y :47; colegio/backup_probe_record.py; BackupLevelsTests. |
| D5 | Copia verificada en temporal separado, SQLite inmutable/query_only y bloqueo de escrituras en servidor. Sesión solo en memoria; enlace inicial de un uso, recarga segura y aviso permanente. No genera mensualidades ni confirma tasas. | colegio/read_only.py:33 y :96; colegio/server.py:590; tests/test_read_only_copy.py y tests/viewer_browser.cjs. |
| D6 | Reporte diario con morosidad por grado; cierre mensual JSON/PDF/CSV con moneda/método, cobros, egresos, saldo, pendiente por grado y anulaciones de bitácora. Sin identificadores de alumnos en el mensual. | colegio/monthly_report.py:13; colegio/directory_reports.py, daily_report; MonthlyReportsTests. |
| D7 | Instalación sin datos, actualización real desde 1.0.67, otra cuenta estándar real, desinstalación conservando datos, portabilidad sin almacén de origen, cortes reales y guía física. | tests/windows_upgrade.py; tests/windows_other_account.py; tests/windows_portability.py; packaging/test_installer.ps1; docs/pruebas-fisicas.md. |

### Precisiones de los hallazgos iniciales

Las referencias siguientes corresponden a la base auditada `9c9ba24`, antes de modificarla. Aula.iss:41 incluía todos los HTML, por eso empaquetaba el inventario interno. Los archivos privilegios-personal ya no existían en el repositorio y retired-files.iss:133–134 eran instrucciones para eliminarlos, no para incluirlos. Se conserva ese retiro y se añaden eliminaciones específicas de guías internas antiguas.

server.py:67 y :102 exponían todos los ajustes en el estado. db.py:198–199 ya calculaba el año con la fecha: no estaba fijo en 2026. En enero de 2027, un ciclo que empieza en septiembre puede ser 2026–2027; el asistente ahora pide revisarlo, y con inicio en enero sugiere 2027–2028. Una elección manual no se sobrescribe. app.js:367 ya ocultaba Nómina, pero server.py:358 la aceptaba por API; ahora se rechaza para egresos nuevos. PrivateAccess estaba apagado por defecto y ampliaba Host/Origin para un enlace HTTPS de Tailscale, manteniendo el servidor en loopback; se retiraron sus vías de activación.

Se encontraron además manuales históricos que todavía describían vaciado global o copias externas sin cifrar. Se conservan íntegros en docs/interno/manuales-anteriores-a-tanda-d y se entregan solo guías actuales en el instalador. El seguimiento técnico completo queda en docs/interno/seguimiento-tanda-d.md, también fuera del paquete.

## Cuatro suites: resultados reales

| Suite | Linux | Windows Server 2022 |
|---|---|---|
| python -m unittest discover -s tests -v | 301 en 173,864 s: 298 correctas, tres de Windows omitidas | 301 correctas en 509,889 s, sin omisiones |
| python tests/run_browser.py | PASS; incluye calendario 2027 y consulta con recarga/cierre | PASS, incluidas esas verificaciones |
| python tests/run_browser.py --demo | PASS | PASS |
| python tests/run_browser.py --roster | PASS | PASS |

Las tres omisiones Linux son DPAPI, mutex/enfoque de ventanas y diálogo nativo Tk. Se ejecutaron en Windows. La restricción inicial de sockets se resolvió con el mecanismo autorizado, sin omitir ni alterar pruebas para eludirla. cryptography 50.0.0 instalado, según el requisito fijado.

El primer intento nativo completo detectó una conexión de prueba sin cerrar; se corrigió manteniendo el rechazo de esquema futuro. Otro runner se detuvo porque Defender no estaba activo; se añadió una espera acotada de arranque, conservando el rechazo obligatorio si no se activa. Los verificadores de navegador tenían rutas de Linux; se hicieron portables manteniendo todas sus aserciones. La ejecución final anterior pasó íntegra; los intentos parciales o cancelados no se presentan como entregas validadas.

## Rendimiento D3

HTTP real, sin compresión, una solicitud de calentamiento y mediana de tres solicitudes. Cada carga tiene 500 u 800 alumnos, diez cargos y tres pagos por alumno y ciclo; uno, dos o tres ciclos, incluyendo períodos preparados del ciclo activo. No se usó logo personalizado. Se mide la respuesta completa por HTTP, no arranque ni dibujo de toda la interfaz. El libro completo sigue disponible con history=1. CSV con bytes, medianas y máximos: [tanda-d-mediciones.csv](tanda-d-mediciones.csv).

| Alumnos | Ciclos | Cargos | Pagos | Principal Linux, bytes / s | Principal Windows, bytes / s | Completo Windows, bytes / s |
|---|---|---|---|---|---|---|
| 500 | 1 | 5000 | 1500 | 7184 / 0.0563 | 7284 / 0.1852 | 2642127 / 0.2330 |
| 500 | 2 | 10000 | 3000 | 7226 / 0.0860 | 7326 / 0.2201 | 4958508 / 0.2742 |
| 500 | 3 | 15000 | 4500 | 7232 / 0.1006 | 7332 / 0.2569 | 7277621 / 0.3376 |
| 800 | 1 | 8000 | 2400 | 7184 / 0.1132 | 7284 / 0.2870 | 4229379 / 0.3579 |
| 800 | 2 | 16000 | 4800 | 7227 / 0.1155 | 7327 / 0.3389 | 7943509 / 0.4159 |
| 800 | 3 | 24000 | 7200 | 7234 / 0.2025 | 7334 / 0.3990 | 11656423 / 0.5011 |

Objetivo propuesto menor a 1 MB y 1 s: alcanzado en las seis cargas, también en Windows. Con 800 y tres ciclos, Windows devuelve 7.334 bytes con mediana 0,399 s y máximo 0,404 s. No garantiza el mismo tiempo en cualquier PC: el cálculo todavía recorre el historial para conservar los totales y el libro completo solicitado bajo demanda puede superar 1 MB.

## Dinero, cadena, respaldos y permisos

Las referencias publicadas de caja y reportes se conservaron exactamente: egresos válidos equivalentes a USD 30,01, con USD 10,01 en efectivo y Bs 2.000,00 por transferencia a su tasa original; el egreso anulado queda fuera. Se compararon movimientos, importes originales/conversiones, anulaciones y totales, no solo cantidades de filas. Las pruebas de cobros, cinco cajeros y referencias de saldos/antigüedad también pasaron. La actualización nativa conserva el saldo USD 50 de su fixture y todas sus filas/documentos financieros.

Matriz de perfiles y CSRF completa, rutas de Personal retiradas, protección de correlativos, integrity_check, foreign_key_check, Verificar datos y cadena válidos. Se mantienen A1–A5, WAL/FULL, importes y recibos congelados. No hay una migración nueva de producción. Las copias antiguas usadas para consultar se actualizan solo en el temporal verificado y se vuelven a comprobar; se prueba con un fixture publicado.

Cortes reales del proceso durante cobro, respaldo SQLite, cifrado/publicación, restauración, migración y borrado de ficha; se añaden tres puntos durante publicación de copias por niveles. Las bases quedan completas o intactas, con recuperación/verificación posterior. Son terminaciones reales, no excepciones que pretendan simular un corte eléctrico.

La cuenta estándar Windows real usó solo archivo cifrado más contraseña y solo archivo más recuperación, sin el almacén de origen: Probar respaldo, restauración y consulta correctos. La ventana WebView2 real abrió la copia cifrada, mostró el aviso, mantuvo Consulta, conservó el origen y eliminó el temporal al cerrar. No hay una ruta de servidor que permita registrar cobros desde esa copia; solo actividad y cierre de sesión pueden cambiar RAM con sesión y CSRF.

La retención explica qué se conserva y qué se elimina. El pase de año crea su copia permanente cifrada tras validar la revisión y antes de cambiar el curso; si falla, no confirma el pase. La declaración de haber tomado una copia externa es manual: Aula verifica su contenido, no una subida a la nube.

El pendiente del informe mensual es el saldo actual de cargos que vencen hasta el fin del mes elegido; no reconstruye una foto histórica. El saldo de caja acumula movimientos válidos, no certifica efectivo contado. Las anulaciones se seleccionan por fecha de bitácora en Venezuela. PDF/CSV se comprobaron además desde los botones reales, sin datos de identificación del alumno y sin alterar saldos.

## PDF, impresión e instalación

WebView2 e inspección independiente correctos: individual de 396 × 612 puntos, una página; sobre carta 612 × 792, una página y misma posición/tamaño al 100 %; ORIGINAL/COPIA en 792 × 612, una página con dos copias completas al 100 %. No aparecen código interno ni cédula escolar. La consulta de copias no desplaza el comprobante al imprimir. La impresora física del colegio se comprueba aparte.

Instalación en cero, apertura real, ventanas, bandeja, actualización 1.0.13 → 1.0.49 → 1.0.67 → 1.0.68 y desinstalación conservando datos: correctas. Otra cuenta estándar real: carpeta y SID distintos, instalación/inicio vacíos y datos de la cuenta principal intactos. Guías internas y antiguas retiradas de la instalación. Defender antes/después sin detecciones, motor 1.1.26090.9 y firmas 1.461.41.0.

## Límites reales y pruebas del colegio

No se dispone de la PC Windows 10/11 del colegio, su impresora ni capacidad de cortar físicamente su electricidad. Por eso no se presentan esas pruebas como ejecutadas. [Pruebas físicas](pruebas-fisicas.md) detalla corte eléctrico con datos ficticios, impresión y restauración en otra PC. Puesta en producción se volvió a renderizar: una página A4. El aviso de consulta usa la fecha del archivo, expresamente no certificada; copiar o descargar un archivo puede cambiarla.

El entorno de trabajo bloqueó la descarga local de los ZIP desde productionresultssa2.blob.core.windows.net, dominio no autorizado por su política de red. No se eludió esa restricción: el EXE y la evidencia están entregados en los artefactos de GitHub enlazados arriba, y los resultados se leyeron de los registros completos accesibles de Actions. No se adjuntaron archivos de huellas ni se trabajó en firma del instalador.
