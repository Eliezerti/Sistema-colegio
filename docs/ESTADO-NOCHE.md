# Estado final · ingresos y facturas · 17/10/2026

## Resultado para revisar

Rama `autonomo/ingresos-facturas`. Código compilado y validado `1fcebfb73967fc8de7010bb0d9fc15a2e37666b5`; código de producto `ee7a488` más primer arreglo de prueba Tk `6b139e2`. Los commits posteriores solo actualizan documentación/evidencia. Main intacta; sin merge, etiquetas ni release final. Ninguna base del usuario abierta o modificada; solo datos ficticios y temporales.

Fases 1–4 integradas: cuentas, clasificación, depósitos, otros ingresos, CSV/XLSX, conciliación, cierre mensual e informes; editor de formularios preimpresos, perfiles/versiones, lotes, números confirmados, emisión, anulación, hojas dañadas y reimpresión del PDF conservado. Los recibos existentes, cálculos y correlativos permanecen iguales. Hay límites funcionales explícitos al final.

## Pruebas reales finales

| Comando | Linux | Windows Server 2022 |
|---|---|---|
| python -m unittest discover -s tests -v | 379 en 408,506 s; 376 correctas, tres nativas omitidas; salida 0 | 379 en 956,891 s, sin omisiones; salida 0 |
| python tests/run_browser.py | Salida 0 | Salida 0 |
| python tests/run_browser.py --demo | Salida 0 | Salida 0 |
| python tests/run_browser.py --roster | Salida 0 | Salida 0 |

Windows repitió unittest durante la compilación: 379 correctas en 926,067 s. PDF independiente: dos correctas, 0,100 s Linux / 0,091 s Windows; aislamiento de entrada: dos correctas, 0,005 / 0,011 s. Media carta 396×612 puntos, una página, coordenadas y fuentes, ñ/tildes/cursiva, perfiles y carta superior/inferior. No equivalen a calibración física.

[Windows final 39044266696](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39044266696), job 117429759501: **success**, incluidas compilación, Defender antes/después (salida 0, sin detecciones), instalación separada, ventanas nativas normal/Pruebas/consulta cifrada, PDF del comprobante, reinstalación y desinstalación conservando dos bases y dos respaldos ficticios. Instalación revisada sin bases ni respaldos empaquetados.

Evidencia conservada en `docs/interno/ingresos-evidencia/windows-facturas-final.json` y CSV; Linux en `linux-facturas-cuatro-suites.json`. Registros locales `/workspace/work/noche4/final-*.log`, `.exit`, `windows-fixed1-job.log`, anotaciones, estado y metadatos. Recolector terminó correctamente. No volver a ejecutar suites por cambios solo de documentación.

## Instalador BORRADOR

[Descargar artefacto ZIP](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39044266696/artifacts/12106501131): incluye `Aula-Colegio-Instalador-1.0.72-borrador.14.exe` y `.exe.sha256`. Puede requerir sesión GitHub. SHA-256 del EXE comprobado por CI antes/después:

`5f3148447d13b41ae8c50c38172e8dcf1f94dc03e2c70da16bc3a4896de3ec2b`

Cierra Aula publicado antes de abrir **Inicio → Aula - Revision ingresos → Aula BORRADOR**. AppId/programa/accesos separados; datos en `%LOCALAPPDATA%\AulaRevisionIngresos\AulaColegio`, incluso al abrir el EXE directamente. No actualiza el producto publicado ni activa inicio automático. No copiar la base de revisión encima de datos reales. Desinstalar conserva datos. Comparten mutex/puertos con el producto publicado.

El entorno bloqueó descargar el nuevo artefacto desde `productionresultssa7.blob.core.windows.net` (Forbidden); no se eludió ni se afirma haber verificado localmente el EXE. Existe y fue validado/subido en GitHub. Artefacto ZIP 19.279.149 bytes; su digest es distinto del SHA del EXE. La ruta `/codex/.../output` tampoco pudo crearse por permisos del sistema operativo; entrega por enlaces autorizados de GitHub.

## Rendimiento real · 800 alumnos y PDF ficticios

| Sistema / historia | Principal bytes / mediana / máximo | Conciliación mediana | Relación mensual mediana | Facturas mediana |
|---|---|---|---|---|
| Linux / 12 meses, 9.600 facturas | 7.993 / 0,331963 / 0,448516 s | 0,344910 s | 0,177546 s | 0,119056 s |
| Linux / 36 meses, 28.800 facturas | 8.000 / 0,483898 / 0,485014 s | 0,879629 s | 0,404841 s | 0,241264 s |
| Windows / 12 meses, 9.600 facturas | 8.093 / 0,419400 / 0,430406 s | 0,302261 s | 0,187098 s | 0,132599 s |

Son cargas sintéticas temporales; no velocidad de emisión ni extractos reales. Windows 36 meses con facturas no se ejecutó.

## Conservación y fallos resueltos

Esquemas 13–16 aditivos (21 tablas nuevas en total), copia previa verificada, fixture publicado 1.0.71 y cinco terminaciones reales por transición; integridad, claves foráneas y cadena comprobadas. Referencia independiente de caja/reportes/morosidad, recibos y aplicaciones conservados. Instalación lógica en cero. Reversión: copia previa en otra carpeta vacía y código compatible; conservar íntegra la carpeta actual y operaciones posteriores. Punto verde del núcleo: `a772d25`, documentación `1526124`.

Primer Linux completo de Fase 4: 379 en 343,004 s, un fallo por perfil vacío; primer arreglo y repetición completa verdes. Primer Windows 39042799764: unittest cerró con -2147483645 y Tcl_AsyncDelete, sin resumen ni traceback Python; normal/demo/roster 0/0/0. La prueba Tk mantiene sus aserciones reales en un hijo y recoge ciclos en su hilo; primer arreglo aprobado por dos ejecuciones completas Windows. No se omitió la prueba. No se modificaron reglas del producto ni fixtures publicados para evitar fallos.

El ZIP de logs anterior estaba en un host prohibido sa1; el registro completo se recuperó por el comando normal de logs GitHub permitido. El límite de uso de revisión automática bloqueó una consulta; tras la nueva indicación del usuario el mismo mecanismo volvió a funcionar. Ninguna suite en marcha fue cancelada. Historial de intentos y decisiones en INFORME-MAÑANA.md y DECISIONES-AUTONOMAS.md.

## Pendientes y siguiente paso

- Cruces entre cuentas/monedas, depósitos de efectivo convertidos y traslado de efectivo de otros ingresos. Soporte textual sin adjuntos. Facturas desde cobros con R; no desde otros ingresos. No inventar tasas ni recibos para resolverlo.
- Actualización del instalador publicado y otra cuenta Windows de este borrador no ejecutadas. Su instalación separada no realiza una actualización del producto.
- **NO VERIFICADO:** extracto real Provincial, formulario real, impresión/calibración física y confirmación fiscal. Ejemplo editable SIN CALIBRAR. IVA/IGTF no calculados ni activables en este borrador; etiquetas editables. Sin banco ni SENIAT conectados.
- Manuales: fotocopias e impresora real, extracto confidencial fuera del repositorio, contador, restauración en otra PC y corte físico de luz durante piloto ficticio supervisado.
- No tocar Personal/Nómina, firma digital, otras tandas ni datos del usuario. No fusionar/publicar sin otra instrucción. Siguiente paso: revisión del usuario con el BORRADOR y los pendientes explícitos, no repetir trabajo ya verde.
