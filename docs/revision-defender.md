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
