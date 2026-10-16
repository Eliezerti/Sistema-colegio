# Empezar los recibos de producción en R-000001

Esta operación excepcional elimina TODOS los cobros de prueba, incluidos los anulados, sus aplicaciones y los estados de cuenta, solvencias y cierres de caja de prueba emitidos. Los cargos que estaban abonados vuelven a quedar pendientes. Conserva alumnos, representantes, grados, cargos, egresos, tasas, convenios, usuarios, configuración, constancias de matrícula y pases de año. Las cuentas de Administración, Caja y Consulta no se borran. No reactiva cargos cancelados. No sirve para borrar pagos reales ni para cambiar únicamente el número de un recibo.

## Pasos

1. Actualiza normalmente a Aula 1.0.71. **No reemplaces ni borres la carpeta de datos.**
2. Comprueba en Protección y mantenimiento que los respaldos cifrados estén configurados. Conserva la contraseña y la clave de recuperación.
3. Cierra Aula por completo, también desde su icono junto al reloj de Windows → Salir.
4. Pulsa Windows + R y ejecuta:

   `"%LOCALAPPDATA%\Programs\AulaColegio\Aula.exe" --clear-trial-payments`

   Si instalaste el programa en otra ubicación, utiliza la ruta de Aula.exe que muestra Propiedades de su acceso directo. La carpeta del programa es distinta de la carpeta de datos.
5. Revisa la carpeta de datos y las cantidades de cobros, estados de cuenta/solvencias y cierres de caja. Confirma únicamente si TODOS esos cobros y documentos son ficticios. Escribe `SOLO COBROS DE PRUEBA`, tu usuario y contraseña de Administración y el motivo. Si el cifrado está bloqueado, se pedirá también la contraseña del respaldo.
6. La herramienta crea y verifica un respaldo cifrado antes de borrar. Al terminar muestra su ubicación: `backups/antes-limpiar-cobros-prueba-...aulabak`. Esta copia no entra en la rotación automática. Consérvala hasta comprobar la puesta en producción; mantenla identificada como respaldo de pruebas y separada de las copias de producción.
7. Abre Aula e inicia sesión nuevamente. La lista de cobros estará vacía; el contador interno estará en cero y el próximo cobro emitirá R-000001. No registres un cobro ficticio para comprobarlo en la base que usarás en producción: verifica el número al registrar el primer pago real.

## Límites

Se permite una sola vez en esa base. No aparece como botón de borrado ni como ruta de la API. La contraseña, la revisión, el motivo, la bitácora y el respaldo son obligatorios. El primer recibo es 1, no 0.

En 1.0.71, los estados de cuenta, solvencias y cierres de caja de prueba ya están incluidos en la revisión y limpieza autorizada. Se exige confirmar también su eliminación. Un documento de representante ilegible o de un tipo distinto detiene la operación sin borrar. También se detiene si Aula está abierto, hay una restauración pendiente, falla el respaldo, cambian los datos revisados, el reloj está bloqueado o la base tiene errores. **No borres registros con SQLite ni elimines archivos para forzar la operación.**

Los totales de cobros y pendientes cambian únicamente por retirar esos cobros: los egresos y cargos permanecen iguales. La cadena anterior de bitácora se conserva y se agrega el motivo de la limpieza junto al respaldo. No se cambia el esquema ni se migran bases desde esta herramienta. Restaurar la copia anterior revierte los datos mediante el procedimiento normal de restauración, con sus confirmaciones y protecciones de correlativos.

Los PDF, CSV o comprobantes impresos que hayas guardado fuera de Aula no se eliminan automáticamente. Identifícalos como pruebas y mantenlos separados de los documentos de producción. El módulo de Personal y Nómina ya estaba retirado de esta versión; esta limpieza conserva todos los usuarios existentes y no realiza ese retiro ni migra bases antiguas.
