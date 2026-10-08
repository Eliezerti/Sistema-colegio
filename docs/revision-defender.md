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

El [primer análisis independiente en Windows](https://github.com/Eliezerti/Sistema-colegio/actions/runs/37728590559) terminó con éxito y sin detecciones para el archivo oficial conservado. Se solicitó otra ejecución que hace visibles en las anotaciones el motor, las firmas y el resultado exacto. Esta diferencia respecto al equipo del usuario no confirma un falso positivo ni autoriza a permitir la detección.

En el equipo afectado: sigue las acciones de Defender en **Historial de protección**, mantén la cuarentena, reinicia si se solicita y ejecuta **Examen completo**. No desactives la protección ni añadas exclusiones. No elimines la carpeta de datos del colegio. La revisión del archivo no sustituye el análisis del equipo donde se abrió.

La evaluación de un posible falso positivo puede solicitarse en el [portal oficial de Microsoft para envío de archivos](https://www.microsoft.com/en-us/wdsi/filesubmission). Este repositorio no ha presentado una solicitud ni recibido un dictamen de Microsoft.
