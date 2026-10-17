# Estado de trabajo nocturno

**Núcleo de Fases 1–3 integrado y validado en Linux y Windows. Fase 4: diseño, sin funciones entregadas todavía.**

- Rama `autonomo/ingresos-facturas`; código verde `a772d2553d2f070f33aa715692d5cdb95988cdc3`. Main intacta; sin merge, etiquetas ni versión publicada. No se abrió ni modificó una base del usuario.
- Fase 1: cuentas escolares, cuenta destino, asignación explícita de históricos, otros ingresos y depósitos parciales. Fase 2: CSV/XLSX, perfiles editables, huellas, duplicados, cruces únicos y parciales, clasificaciones y privacidad. Fase 3: cierre mensual, bloqueo del servidor, foto conservada, reapertura motivada y relación CSV/PDF.
- Esquema 15, catorce tablas nuevas aditivas. Transiciones 12→13→14→15 con respaldo previo verificado y cinco terminaciones reales por transición; integridad, claves foráneas y cadena. Fixture publicado 1.0.71 y referencia independiente de caja/reportes/morosidad. Instalación lógica vacía.
- **Linux final: 355 en 309,459 s, 352 correctas y tres nativas omitidas; normal/demo/roster salida 0.** Registros `/workspace/work/noche3/final355-*.log`; resumen conservado en `docs/interno/ingresos-evidencia/linux-cuatro-suites.json`.
- **Windows final: 355 correctas en 666,551 s, sin omisiones; normal/demo/roster salida 0.** [39028897879](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39028897879), evidencia `windows-final.json` en la misma carpeta. También terminó correctamente el punto anterior `cb34ad7`: 354 en 750,012 s, tres navegadores salida 0; no se canceló ninguna suite en marcha.
- HTTP final con 800 alumnos: Linux 12/36 meses, principal 7.993/8.000 bytes, medianas 0,185610/0,442593 s; Windows 12 meses, 8.093 bytes y 0,394435 s. CSV con tamaño, mediana y máximo en `docs/interno/ingresos-evidencia/`. Windows 36 meses no ejecutado.
- Últimos arreglos: aislamiento de reloj de referencia; LF obligatorio para conservar su huella; exclusión de otros ingresos de caja de pendientes bancarios; rechazo con cifrado bloqueado antes de crear copia de reversión. Prueba compuesta portable de libro conciliado y cierre, con contraseña/recuperación sin almacén original, restauración e inmutabilidad de consulta.
- Fallos y resultados previos completos en INFORME-MAÑANA.md e historial. Dos validaciones que estaban solo en cola se sustituyeron antes de ejecutar pruebas; las activas terminaron. Inicial Windows fallido sin logs recuperables, causa desconocida; repetición diagnosticó CRLF, corregido sin relajar huellas.

## Siguiente fase y punto de retorno

Se continúa Fase 4 por autorización autónoma, conservando este punto verde del núcleo. Diseño en `docs/interno/facturas-diseno.md`. Primero reglas de plantilla/PDF con pruebas; integrar API, esquema e interfaz solo como bloque funcional completo. No presentar botones ni emisión fiscal parcial como entregados. Si una prueba sigue fallando tras dos arreglos, revertir la fase mediante commits normales al punto verde anterior y conservar el informe.

Pendientes del núcleo: conversión entre cuentas/monedas, depósitos de efectivo convertidos y traslado de efectivo de otros ingresos. Soporte textual sin adjuntos. No se inventan tasas ni recibos para cubrir esos casos.

No existe instalador de esta rama. No se ejecutaron instalación/actualización/desinstalación ni impresión física de este código. NO VERIFICADO: extracto real de Provincial, formulario real, calibración y confirmación fiscal. El ZIP fuente en scratch fue verificado, sin base de negocio ni respaldos; no es instalador ni publicación.

## Entorno y recuperación

Al reanudar, el entorno volvió a `a5b5aed` sin logs anteriores. Se recuperó la rama enviada; no se perdió código. La revisión por límite de uso volvió a permitir el mismo mecanismo autorizado. No se eludió la política de red: el host de un artefacto estaba prohibido; las nuevas anotaciones de GitHub conservan resultados y tracebacks por API permitida. Los logs antiguos no observados no se declaran correctos. Los nuevos logs y evidencia real sustituyen esa incertidumbre para el núcleo final.

## Fase 4 en desarrollo local (no entregada ni enviada al remoto)

Punto de retorno completo: `1526124651db4588e0d551b676965d5de5973402` (código verde `a772d25`, 355 y las cuatro suites en ambos sistemas). El árbol local contiene trabajo de Fase 4 todavía sin validación completa ni interfaz: reglas/plantillas/PDF, esquema 16 aditivo, API y registro de facturas. No abrir una base del usuario con este árbol en desarrollo.

- Plantillas: 8 pruebas correctas en 0,115 s. PDF independiente (pypdf/PyMuPDF): primera ejecución detectó cuadros de fuente fuera del margen (13 subcasos); primer arreglo reserva ascendentes/descendentes y cursiva, 2 pruebas correctas en 0,086 s, incluida media carta 396×612 y carta arriba/abajo con giro a tamaño real. PNG de ejemplo y PDF solo en `/workspace/work/noche4/`.
- Migración: primera dirigida 11, un fallo del test al comparar audit_meta sin admitir el avance de la cabecera. Se exige incremento de una entrada, cadena/baseline iguales y todas las filas de negocio idénticas. Primer arreglo: 11 correctas en 6,714 s. Cinco cortes reales 15→16 y respaldo cifrado previo de 15, desde datos publicados 1.0.71. Instalación lógica vacía.
- API: primera dirigida 10, una falla de orden en el registro: el ID interno del borrador dejaba la hoja dañada 2 después de la factura 3. Ordenado por fecha y número preimpreso. Las 10 pruebas de facturas pasaron en la ampliación siguiente; además pasaron concurrencia real de dos cajeros, inmutabilidad/reimpresión idéntica, cierres, restauración portable y conservación de números tras dos restauraciones.
- Ampliación 30 pruebas: dos errores de fixtures sintéticos de marca que conservaban tablas de la ampliación al simular esquema viejo. Se corrige solo su constructor; nunca se modifica un fixture publicado ni se debilita el migrador. Repetición en curso: `/workspace/work/noche3/invoices-compat-fixed1.log`.
- Siguiente: terminar interfaz/editor, pruebas reales de navegador, ampliar evidencia independiente del PDF a Windows y ejecutar cuatro suites completas. Ninguna función de Fase 4 se declara entregada. Falta instalador y verificación física/fiscal. Si una prueba sigue fallando tras dos arreglos, retirar esta fase al punto de retorno mediante commits normales; no tocar datos del usuario.


## Reanudación · 17/10/2026 10:53 Venezuela

Fase 4 implementada localmente y cuatro suites Linux completas correctas: **379 en 408,506 s, tres exclusivas de Windows omitidas; normal/demo/roster salida 0**. Registros `/workspace/work/noche4/final-*.log` y `.exit`. Primer pase completo 379 en 343,004 s: un fallo por perfil vacío; primer arreglo y repetición completa correctos. Matriz dirigida correcta. PDF independiente dos correctas en 0,100 s; aislamiento de entrada BORRADOR dos correctas en 0,005 s. API/GUI, sesión fiscal, numeración, portable, permisos y referencia incluidas.

Commits locales: `35ffaf1` PDF; `58a4cc3` esquema 16; `6ca60e3` backend; `f1c4bb0` prefijos/validación; `ea7301e` editor y navegador. Falta enviar esta fase y terminar Windows. El remoto aún conserva `1526124`. No abrir una base del usuario.

Medición real Linux 800/12 con 9.600 facturas/PDF: principal 7.993 bytes / mediana 0,331963 s / máximo 0,448516 s; relación mensual 425.987 / 0,177546; registro facturas 49.222 / 0,119056. CSV `/workspace/work/noche4/invoices-800-12.csv`. Generador corregido (sintaxis/importación), ejecución final salida 0.

Se preparó instalador BORRADOR aislado, todavía sin compilar ni validar: AppId/programa/accesos separados, datos bajo `%LOCALAPPDATA%\AulaRevisionIngresos\AulaColegio`; no sustituye el publicado. Entrada probada sin tocar producción. CI ejecutará cuatro suites, medición, verificación PDF, compilación, Defender, instalación separada, autopruebas y desinstalación. Sin releases ni etiquetas. Faltan actualización desde publicado/otra cuenta de este borrador y pruebas físicas; no se declaran realizadas.

La consulta anterior a GitHub fue bloqueada por límite de uso de revisión automática; no se ejecutó ni se eludió. Tras la nueva indicación del usuario, el mismo mecanismo autorizado permitió consultar de nuevo. Sigue válido el punto verde Windows anterior 39028897879; no se atribuye ese resultado a Fase 4.
