# Validación 1.0.71

El bloqueo visto en 1.0.70 estaba en `colegio/trial_payment_cleanup.py:35`: rechazaba cualquier documento de representante o cierre emitido. El usuario autorizó expresamente retirar estados de cuenta, solvencias y cierres de caja de prueba, junto con cobros y recibos, conservando alumnos, representantes y personal. La versión ya no tiene Personal/Nómina; se conservan todas las cuentas de acceso. No se migra ni se retira personal mediante esta herramienta.

La ampliación inicial no llegó a ejecutarse: la revisión automática exigió autorización específica de los documentos financieros. Después de la confirmación expresa del usuario, se implementó el alcance autorizado. No se modificó la base del usuario.

La revisión identifica solo tipos account y solvency; un tipo desconocido o ilegible detiene el proceso. Se exige documents_confirmed=True además de la confirmación de cobros, contraseña de Administración y motivo. Una única transacción retira guardian_documents, cash_closures, allocations y payments, reinicia únicamente el piso de pagos y revoca sesiones. Los usuarios, fichas, cargos, egresos, constancias, convenios y pases de año permanecen intactos. Se conserva el respaldo cifrado verificado y la cadena original de bitácora.

Pruebas específicas: 6 correctas en 11,177 s. Fixture con 2 pagos, estado de cuenta, solvencia, cierre, tres cuentas de acceso y pase de año. Se verifican conservación de tablas protegidas, recuperación de documentos y usuarios desde el respaldo cifrado, Verificar datos sin errores y primer recibo id 1. Siete terminaciones reales: después del respaldo, documentos, aplicaciones, pagos, contador, antes y después del commit; todas dejan estado completo o intacto y cadena válida.

Totales: ingresos 32,50 → 0 por la limpieza autorizada; egresos 7,25 → 7,25; cargos iguales y pendiente aumenta exactamente en los pagos retirados. Sin cambios en los cálculos de la operación normal.

Pendientes: cuatro suites Linux/Windows e instalador compilado. La impresora física y la limpieza sobre la base del usuario requieren su PC y confirmación local.
