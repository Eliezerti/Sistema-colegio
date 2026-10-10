# Revisión de la detección de Microsoft Defender

El usuario reportó `Trojan:Win32/Bearfoos.B!ml` después de abrir o instalar `Aula-Colegio-Instalador-1.0.8.exe`. La notificación de Defender solicita reiniciar. No se ha confirmado si es malware o un falso positivo.

La descarga pública de `desktop-1.0.8` se convirtió en borrador y se conserva el archivo para revisión. Los nuevos instaladores también se generan como borradores; no se recomienda sustituir el archivo por otra versión sin revisar.

SHA256 del instalador oficial conservado y del artefacto de GitHub (no se ha obtenido el hash del archivo en el equipo del usuario):

```text
7852d8436ae2678ad33a1e1b55022e93949754d795f00f5ec517408fe8e5d8ad
```

La coincidencia prueba que se conserva el archivo construido, **no que sea seguro**. La compilación utilizó PyInstaller 6.12.0 e Inno Setup, con dependencias fijadas. El componente WebView2 se obtuvo de Microsoft y se comprobó su firma. Las pruebas de instalación, datos y ventanas pasaron, pero **no se había ejecutado un análisis antivirus**. No se firmó comercialmente el instalador de Aula. Una detección de aprendizaje automático y el empaquetado pueden motivar una revisión de falso positivo; no bastan para declararlo.

`windows-antivirus-audit.yml` descarga el artefacto exacto, comprueba su SHA256 y analiza con Microsoft Defender en un equipo Windows desechable. **No instala ni ejecuta el archivo reportado**. Conserva motor, firmas, resultado y hashes del análisis. Si el motor no está disponible, el análisis falla; no se informa de un resultado limpio.

Las compilaciones siguientes deben superar el análisis antes de ejecutar el instalador para las pruebas funcionales. Las publicaciones siguen siendo borradores mientras se investiga el reporte; un análisis sin detecciones con otras firmas no invalida lo observado en el equipo del usuario.

El [primer análisis independiente en Windows](https://github.com/Eliezerti/Sistema-colegio/actions/runs/37728590559) y el [análisis con informe visible](https://github.com/Eliezerti/Sistema-colegio/actions/runs/37729148630) terminaron con `Scan finished` y `found no threats` para el SHA256 indicado. Ambos usaron producto `4.18.26080.4`, motor `1.1.26080.3` y firmas `1.459.601.0`. Un intento intermedio no pudo actualizar las firmas y **no realizó un análisis válido**; no se cuenta como resultado limpio. El actualizador ahora intenta el canal oficial MMPC si falla Windows Update.

Son análisis estáticos en un equipo desechable. No reprodujeron la apertura en el equipo del usuario ni compararon su archivo o configuración de Defender. La diferencia observada **no confirma un falso positivo ni autoriza a permitir la detección**. Hace falta revisar la entrada del equipo afectado en Historial de protección, incluidos los elementos afectados y la acción aplicada.

La [compilación de revisión 1.0.10](https://github.com/Eliezerti/Sistema-colegio/actions/runs/37729115399) superó el nuevo análisis de `dist`, las pruebas funcionales y la validación de instalación en Windows. Su lanzamiento permanece como **borrador**, igual que el instalador 1.0.8 retirado. No se ofrece como reemplazo aprobado para ignorar la alerta del equipo del usuario.

En el equipo afectado: sigue las acciones de Defender en **Historial de protección**, mantén la cuarentena, reinicia si se solicita y ejecuta **Examen completo**. No desactives la protección ni añadas exclusiones. No elimines la carpeta de datos del colegio. La revisión del archivo no sustituye el análisis del equipo donde se abrió.

La evaluación de un posible falso positivo puede solicitarse en el [portal oficial de Microsoft para envío de archivos](https://www.microsoft.com/en-us/wdsi/filesubmission). Este repositorio no ha presentado una solicitud ni recibido un dictamen de Microsoft.


## Versión local 1.0.13

La [compilación 1.0.13](https://github.com/Eliezerti/Sistema-colegio/actions/runs/37830250554) terminó correctamente: pruebas automatizadas, compilación, análisis de Defender, instalación y ventana nativa normal/de prueba, reinstalación y desinstalación conservando datos, y un segundo análisis de Defender después de esas pruebas. Los dos análisis de la carpeta dist (instalador y aplicación empaquetada) finalizaron con salida 0 y `found no threats`.

Archivo: `Aula-Colegio-Instalador-1.0.13.exe`, 20.421.705 bytes. SHA256: `9714be7b6edaa03eab71a247c51219de6c425b5cd72d3b7fb7f1fbe23ab08d3c`. Motor: `1.1.26080.3`. Firmas: `1.459.601.0`, actualizadas el `2026-10-07T08:47:31+00:00`. Las anotaciones de la ejecución muestran el motor, firmas, resultado y hash de ambos análisis. Los informes completos se conservan como artefacto Defender-Windows de esa ejecución. La descarga recuperada del borrador se comparó con ese hash antes de publicar.

Se ofrece esta nueva versión para la solicitud explícita de mejoras e instalador local. No se rehabilita 1.0.8, no se ha recibido un dictamen de Microsoft y no se ha revisado el equipo del usuario. Un resultado limpio con esas firmas no asegura que otra configuración no detecte el archivo. No desactives Defender ni añadas exclusiones si bloquea la nueva descarga. El ejecutable no cuenta con un certificado comercial de firma de código.


## Nueva identidad · versión 1.0.14

La [compilación de la nueva identidad](https://github.com/Eliezerti/Sistema-colegio/actions/runs/37836753883), del commit `6a42c5afd3ef2577584e44ca2377a8662a18284e`, terminó correctamente. Pasaron las 95 pruebas automatizadas en Windows, la apertura de las ventanas normal y de prueba, los accesos directos, la bandeja y la comprobación de instalación, reinstalación y desinstalación conservando la base y los respaldos. Se comprobó la carga del logotipo de producto en la ventana nativa.

Los análisis de Defender anteriores y posteriores a ejecutar el instalador finalizaron con salida 0 y `found no threats`: motor `1.1.26080.3`, firmas `1.459.601.0`, actualizadas el `2026-10-07T08:47:31+00:00`. Archivo: `Aula-Colegio-Instalador-1.0.14.exe`, 20.810.537 bytes; SHA256 `ed475caff54c5df4be1f7aff5f17d89181fcddf4524dd5cd46ac1e7f3cc91352`. Se descargó el borrador y se verificó su SHA256 y el archivo de suma antes de publicarlo. Estos resultados corresponden a este archivo y estas firmas; siguen aplicándose las limitaciones del análisis descritas anteriormente.

El instalador lleva el ICO claro oficial de Aula Colegio / ELIEZER PEREZ suministrado por el propietario, sin alterar sus siete tamaños. Se conservan la identificación del instalador y las rutas de instalación y datos; el cambio visual no reemplaza la identidad fiscal guardada de los colegios ni sus recibos emitidos.


## Diseño original restaurado · 1.0.15 en borrador

Se restauró el diseño original a petición del usuario, conservando los módulos administrativos, datos y rutas de instalación. La [compilación 1.0.15](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38013749540), commit `428d01c0ac64924172a2f292f86da7075496a076`, superó las 95 pruebas de Windows y la instalación, ventanas normal/de prueba, bandeja, reinstalación y desinstalación conservando la base y los respaldos. El instalador también reemplaza los accesos directos de la identidad 1.0.14 por los originales; se probó con accesos simulados de esa versión.

Ambos análisis de la carpeta dist finalizaron con salida 0 y `found no threats`. Motor `1.1.26080.3`; firmas `1.459.645.0`, actualizadas el `2026-10-09T16:49:58+00:00`. Archivo: `Aula-Colegio-Instalador-1.0.15.exe`, 20.437.843 bytes; SHA256 `e6192a4e41ed409d9b3987385a7f3c812791e6d1d6174ac8063cf9904780fdee`. Se descargó y comprobó el archivo del borrador contra esa suma y contra el archivo de verificación.

El usuario recordó que los instaladores están siendo detectados como virus. No se ha identificado si el aviso corresponde a la antigua 1.0.8 o a una versión posterior; tampoco se ha recibido un nuevo nombre de amenaza. **1.0.15 permanece en borrador, sin una nueva descarga pública recomendada**, hasta contrastar el archivo y la alerta del equipo afectado. Estos dos resultados sin detecciones no resuelven por sí solos el reporte. No se cambió la política de Defender ni se añadieron exclusiones, y no se modificaron los datos del equipo del usuario.


## Reporte confirmado de 1.0.8 y 1.0.14

El usuario identificó ambos nombres de instalador, sin recordar el nombre de amenaza de la alerta actual. La publicación de 1.0.14 se retiró convirtiéndola en borrador; 1.0.8 ya estaba retirada. Los instaladores nuevos siguen sin publicarse mientras se contrastan la detección y el archivo afectado del Historial de protección. No se ha revisado la PC ni confirmado que sus archivos coincidan con los oficiales.

La [nueva auditoría de ambos instaladores](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38014556607), commit `50aca54c9928f31e212f92b7cb043326133d14d7`, verificó los SHA256 oficiales y analizó los artefactos sin instalar ni ejecutarlos. Ambos finalizaron con salida 0 y `found no threats`, motor `1.1.26080.3`, producto `4.18.26080.4`, firmas `1.459.645.0` actualizadas el `2026-10-09T16:49:58+00:00`. Se confirmó `NotSigned` para los dos instaladores: no tienen certificado comercial. La falta de firma no demuestra malware ni prueba que sea la causa del aviso. Estos análisis estáticos no equivalen a observar la detección en el equipo afectado y no permiten declarar falso positivo.

El flujo `windows-antivirus-audit.yml` ahora revisa ambos archivos con SHA256 fijados, independientemente, y conserva informes separados. No recompila ni sustituye la muestra reportada. Las anotaciones muestran el hash, estado de firma, motor y resultado. No se añadió ninguna exclusión ni se desactivó Defender.


## Primer mes a cobrar · 1.0.16 en borrador

Se añade un primer mes a cobrar separado del período académico. Las altas e importaciones nuevas proponen el mes de carga, con opción de elegirlo expresamente; se acepta la plantilla anterior de 16 columnas y la nueva de 17. La actualización al esquema 9 conserva el límite anterior de alumnos existentes, cargos, pagos y documentos archivados. El pase de año establece el inicio del nuevo ciclo aprobado. El diseño original continúa activo.

La [compilación de Windows 1.0.16](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38015634580), commit `a4483521bfd0aa7acce28cecc07be590570d7a24`, terminó correctamente: 104 pruebas en Windows, instalación, accesos, ventanas normal/pruebas, bandeja, actualización y desinstalación conservando datos. En Linux terminó la misma suite con una prueba omitida por depender de Windows; también pasaron los flujos del navegador normal, prueba y móvil, y se comprobó visualmente el formulario en escritorio y teléfono usando datos aislados.

Ambos análisis de Defender de esta compilación terminaron con salida 0 y `found no threats`, motor `1.1.26080.3`, firmas `1.459.645.0`, actualizadas el `2026-10-09T16:49:58+00:00`. Archivo: `Aula-Colegio-Instalador-1.0.16.exe`, 20.443.512 bytes; SHA256 `95e8f612ff64034714b7f85e7b785dcf960ab438b804e741167602da9c724500`. Se descargó el artefacto del borrador y se comprobó contra el archivo de verificación y las anotaciones del análisis.

**1.0.16 permanece en borrador**, sin publicar como nueva descarga recomendada. Falta contrastar las alertas de 1.0.8 y 1.0.14 con el Historial de protección de la PC afectada. Los análisis del runner no resuelven ese reporte. No se ejecutaron las muestras reportadas en el equipo del usuario ni se añadieron exclusiones.


## Constancia y correcciones · 1.0.17 en borrador

Se añade nacimiento opcional (Pendiente si no se dispone de fecha), mes abreviado en mayúsculas y una constancia sin la nota de tarifas. Edición y archivo reversible de alumnos y representantes aparecen junto al nombre; se conservan sus pagos, cargos y documentos, y los archivados dejan de generar mensualidades. Los representantes vinculados a alumnos sin archivar quedan protegidos. Los grados sin alumnos vinculados se pueden eliminar con motivo, confirmación y copia previa.

Corregir mensualidades, desde Morosidad o Cuenta, revisa los cargos a anular y su importe, exige motivo y confirmación, fija el primer mes y anula solo mensualidades previas sin pagos. Bloquea cargos con pagos aplicados o convenios vigentes y cambios concurrentes. También sirve si una edición anterior ya repuso octubre y quedó septiembre cargado. La anulación no se regenera al abrir o preparar el mes. Se conservan los recibos y constancias originales y se emite una nueva constancia de la corrección. El esquema 10 añade flags de archivo sin borrar registros.

La [compilación Windows 1.0.17](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38020375006), commit `f81c7c9458ea58ad722fdef4a4a171377cc2243f`, completó 117 pruebas y las verificaciones de instalación, ventanas, accesos, bandeja, actualización y desinstalación conservando datos. En Linux pasó la suite de 116 pruebas (una específica de Windows omitida), seguida de las 13 pruebas finales de administración con un caso adicional; también pasaron los flujos del navegador normal, perfil de pruebas y directorios. Se comprobó visualmente la constancia y el formulario de corrección, usando datos ficticios aislados. No se accedió ni se modificó la base de la PC del usuario.

Ambos análisis de Defender de esta compilación finalizaron con salida 0 y `found no threats`, motor `1.1.26080.3`, firmas `1.459.647.0`, actualizadas el `2026-10-09T19:56:15+00:00`. Archivo: `Aula-Colegio-Instalador-1.0.17.exe`, 20.444.315 bytes; SHA256 `e936786fb61e9ba6ddaed2b474d65f9284e8d2e2764a01e1c6d6f2275c8c5fa7`. Se descargó del borrador y se verificó contra su archivo de suma y las anotaciones de los análisis.

**1.0.17 permanece en borrador.** El usuario indicó que instaló 1.0.16 y utiliza alumnos reales, pero no se recibió el detalle de las alertas anteriores de 1.0.8/1.0.14. Los resultados del runner no prueban que esas detecciones se hayan resuelto ni equivalen a una revisión de Microsoft. No se añadieron exclusiones ni se cambió la protección del equipo.


## Directorios más limpios · 1.0.18 en borrador

Morosidad deja cuatro acciones: Cuenta, Aviso, Convenio y Registrar pago. Editar matrícula, Corregir mensualidades y Seguimiento permanecen dentro de Cuenta. En Alumnos y Representantes, Editar y Eliminar del directorio se agrupan junto a la cuenta y los documentos en la columna Acciones de la derecha; en Grados, Editar y Eliminar también se mueven allí. Se conserva el archivo reversible y la protección de datos. No cambia el esquema ni el motor financiero.

Pasaron los flujos de navegador normal y de directorios, incluyendo edición, corrección, protección de registros vinculados, archivo y recuperación. Se revisaron las cuatro tablas con datos ficticios aislados y pantallas de 1440 y 1100 píxeles; en pantallas estrechas las acciones se acomodan dentro de su columna.

La primera ejecución de la [compilación Windows 1.0.18](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38022271156), commit `f291a3feeaf25ecab35aa4feeba2a21d617fe41b`, completó 117 pruebas y generó el instalador. Se detuvo en la actualización de firmas de Defender: Windows Update y el canal oficial MMPC devolvieron un error. No llegó a analizar ni ejecutar el instalador, ni guardó una nueva descarga. Se repite el trabajo en un runner nuevo, manteniendo todas las verificaciones.

La segunda ejecución terminó correctamente: 117 pruebas, instalación, accesos directos, ventanas normal/pruebas, bandeja, actualización y desinstalación conservando datos. Ambos análisis finalizaron con salida 0 y `found no threats`, motor `1.1.26080.3`, firmas `1.459.647.0`, actualizadas el `2026-10-09T19:56:15+00:00`. Archivo: `Aula-Colegio-Instalador-1.0.18.exe`, 20,446,514 bytes; SHA256 `70a5881fb83281d2315384e8b7243bfa5444bbd1f1e37ebdc29d1da6e6ea20e8`. Se descargó del borrador y se verificó contra la suma suministrada y la evidencia de ambos análisis.

**1.0.18 permanece en borrador.** No se recibió el detalle del Historial de protección de la PC para las alertas anteriores. La revisión en el runner no resuelve ese reporte. No se desactivó Defender ni se añadieron exclusiones.


## Reporte diario y listados PDF · 1.0.20 en borrador

Alumnos y matrículas, Representantes y Personal incluyen un botón PDF / Imprimir con vista previa y PDF A4 horizontal. Los listados respetan búsquedas, grado y archivados del directorio. Llevan logo, razón social, RIF, fecha, cantidad de registros, encabezados repetidos y número de página. Las filas extensas de representantes se continúan sin perder alumnos vinculados. Las mensualidades descontadas y saldos se expresan en USD; las cuentas bancarias conservan todos sus dígitos.

Reportes → Reporte diario PDF muestra cobros con fecha de hoy, referencias, importes reales por moneda y equivalente USD de cada operación, conservando su conversión original. Los cobros anulados permanecen identificados y fuera de los totales. Los datos del alumno, representante y grado se toman del recibo conservado, o de la constancia anterior al pago para un grado histórico no guardado. La morosidad corresponde al corte al generar el documento, incluye deudas de fichas archivadas y muestra contacto, grado, vencido y mayor atraso. El perfil de pruebas identifica los documentos como prueba. El envío por correo es manual.

La guía explica el envío de PDF para consulta, el traslado por USB/correo de un respaldo completo y su restauración, y la diferencia entre datos y programa. Dos bases locales no se sincronizan ni se fusionan. Para casa como base principal y colegio como copia, este último debe usar Consulta; cualquier cambio local se reemplazaría al restaurar.

La compilación 1.0.19 fue cancelada deliberadamente para incluir la petición posterior del reporte diario; no se generó una publicación descargable de esa versión. La [compilación Windows 1.0.20](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38027345181), commit `e79902954b1a506601d67faeb1dee3d6925d922c`, completó 127 pruebas y las comprobaciones de instalación, accesos, ventanas normal/pruebas, bandeja, actualización y desinstalación conservando datos. En Linux pasaron 126 pruebas (una específica de Windows omitida), seguidas de las 10 pruebas finales de documentos y finanzas con el caso adicional de identidad del recibo; también pasaron navegador normal y modo de pruebas. Se inspeccionaron la vista previa y el PDF con datos ficticios aislados. No se accedió a la base real de la PC del usuario.

Ambos análisis terminaron con salida 0 y `found no threats`, motor `1.1.26080.3`, firmas `1.459.647.0`, actualizadas el `2026-10-09T19:56:15+00:00`. Archivo: `Aula-Colegio-Instalador-1.0.20.exe`, 20,458,722 bytes; SHA256 `33f1799c9281387d34f8c15ab25c279b00d26653e2d00175bc9dc705fe622cdf`. Se descargó del borrador y se verificó contra la suma suministrada y la evidencia de ambos análisis.

**1.0.20 permanece en borrador.** Falta el detalle del Historial de protección de la PC para las alertas anteriores de 1.0.8/1.0.14. El resultado del runner no demuestra que ese reporte se haya resuelto. No se desactivó Defender ni se añadieron exclusiones.
