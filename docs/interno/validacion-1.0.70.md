# Validación 1.0.70

Excepción autorizada expresamente: retirar todos los cobros ficticios y dejar sus cargos pendientes, conservando alumnos, representantes y configuración. No hay migración ni función de vaciado web. La operación exige cierre de Aula, Administrador y confirmación y se permite una sola vez. Los documentos derivados impiden el borrado hasta revisarlos.

Pruebas específicas: 5 correctas, incluidos seis cortes reales del proceso. Conservación de auditoría previa y cadena válida; respaldo cifrado comprobado con contraseña; pagos 32,50 → 0 y egresos 7,25 → 7,25; cargos idénticos, saldo pendiente aumenta exactamente lo retirado. Piso previo de recibos 99 → 0 y primer nuevo pago id 1; pisos restantes conservados.

En el primer ensayo, una comprobación usó una columna incorrecta de cargos; se corrigió a cancelled. Los procesos independientes de Linux exigieron desbloquear el cifrado con la contraseña legítima: se añadió ese paso sin cambiar la protección. Otro ensayo comparó el objeto devuelto por record_payment con un entero; se corrigió para comprobar su id. Ensayo específico final correcto. No se modificaron bases del usuario.

Pendientes: resultados de las cuatro suites Linux y Windows y de la operación en el ejecutable instalado. La aplicación sobre la PC del usuario solo ocurre al ejecutar la herramienta y confirmar localmente.
