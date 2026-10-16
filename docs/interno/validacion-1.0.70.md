# Validación 1.0.70

Excepción autorizada expresamente: retirar todos los cobros ficticios y dejar sus cargos pendientes, conservando alumnos, representantes y configuración. No hay migración ni función de vaciado web. La operación exige cierre de Aula, Administrador y confirmación y se permite una sola vez. Los documentos derivados impiden el borrado hasta revisarlos.

Pruebas específicas: 5 correctas, incluidos seis cortes reales del proceso. Conservación de auditoría previa y cadena válida; respaldo cifrado comprobado con contraseña; pagos 32,50 → 0 y egresos 7,25 → 7,25; cargos idénticos, saldo pendiente aumenta exactamente lo retirado. Piso previo de recibos 99 → 0 y primer nuevo pago id 1; pisos restantes conservados.

En el primer ensayo, una comprobación usó una columna incorrecta de cargos; se corrigió a cancelled. Los procesos independientes de Linux exigieron desbloquear el cifrado con la contraseña legítima: se añadió ese paso sin cambiar la protección. Otro ensayo comparó el objeto devuelto por record_payment con un entero; se corrigió para comprobar su id. Ensayo específico final correcto. No se modificaron bases del usuario.

Linux: `python -m unittest discover -s tests -v`, 306 pruebas en 170,084 s, 303 correctas y 3 exclusivas de Windows omitidas (DPAPI, mutex/enfoque y ventana Tk de restauración). Navegadores `python tests/run_browser.py`, `--demo` y `--roster`: correctos. El recorrido ficticio de limpieza destinado al ejecutable instalado también pasó en Python.

Revisión final de código: `58783fd`. [Ejecución Windows 38808075749](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38808075749): completada correctamente. La ejecución inicial 38807868329 se canceló para incorporar la exigencia de Verificar datos y cobros antes de limpiar, sin eliminar pruebas.

Windows Server 2022: `python -m unittest discover -s tests -v`, 306 correctas en 407,130 s, sin omisiones. Navegadores normal, --demo y --roster: correctos. Instalación limpia, actualización publicada 1.0.67 → 1.0.70, otra cuenta de Windows y desinstalación conservando datos: correctas. PDF y WebView2, consulta cifrada y Defender antes/después: correctos.

`PASS LIMPIEZA` en el ejecutable instalado: respaldo cifrado descifrado y verificado, alumno conservado, bitácora válida y nuevo pago con id 1. La base usada es ficticia y temporal, independiente de los datos de la cuenta de Windows. Los cortes reales, claves erróneas, cambios después de revisión, documentos emitidos, restauración pendiente y bloqueo de reloj se probaron en las cinco pruebas nuevas de la suite, también correctas en Windows.

[Instalador 1.0.70](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38808075749/artifacts/12006879946) y [evidencia real](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38808075749/artifacts/12007358907). El ZIP de entrega contiene únicamente el EXE validado; no se publican archivos de huellas. La impresora física, un corte eléctrico del equipo del colegio y la ejecución sobre la base del usuario no se realizaron: requieren su PC y su confirmación local. La herramienta se detiene si hay cierres o documentos financieros; no se presume que la base del usuario esté libre de ellos.

Evidencia de código: colegio/trial_payment_cleanup.py (previsión, verificación, autenticación, respaldo y transacción); tests/test_trial_payment_cleanup.py (cinco casos, seis terminaciones de proceso); colegio/desktop_checks.py:trial_cleanup y packaging/test_installer.ps1 (EXE instalado). La aplicación sobre la PC del usuario solo ocurre al ejecutar la herramienta y confirmar localmente.
