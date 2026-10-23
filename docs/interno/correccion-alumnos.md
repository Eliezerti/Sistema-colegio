# Corrección de matrículas duplicadas · seguimiento

Solicitud: eliminar dos fichas equivocadas desde Alumnos y matrículas, con una opción discreta. Versión confirmada por el usuario: 1.0.71. Rama `correccion/alumnos-duplicados`, desde `ed1c5e9`. El borrador de ingresos y facturas queda fuera; main y datos del usuario intactos.

## Hallazgo y solución

- `colegio/institution_archive.py:32`: la revisión anterior exige archivar y considera cualquier cargo o evaluación positiva un bloqueo, aunque sea una matrícula equivocada sin cobros.
- `static/app.js:168`: el directorio solo ofrece Editar; el borrado vacío anterior se encuentra en Archivo de la institución.
- Se conserva ese flujo anterior. La nueva revisión `student-deletion-preview/{id}` es exclusiva de Administración; `delete-error-student` exige contraseña, motivo, BORRAR FICHA, código exacto y huella de la revisión actual.
- `colegio/institution_archive.py:53`: se comprueban pagos, abonos por cargo —incluso vínculos dañados con otro alumno—, convenios, seguimientos y documentos familiares/pases de año. Los pagos/recibos anulados siguen bloqueando.
- `colegio/institution_archive.py:125`: mismo respaldo local previo verificado y segundo destino cifrado cuando está configurado. Si falla una copia, no borra.
- `colegio/institution_archive.py:146`: en una sola transacción se quitan evaluaciones, constancias, cargos sin pagos y ficha; verificación de claves foráneas y evento en la cadena. Se conservan los pisos de alumno/constancia, representantes, demás fichas y recibos.
- `static/app.js:216`: formulario de confirmación separado. En Editar matrícula, el acceso está dentro del apartado plegado «Corrección de fichas creadas por error»; no se agrega un botón destructivo al directorio.

No cambia el esquema 12 ni hay migración. No cambia el motor de cobros, sus cálculos, asignaciones ni correlativos de recibos. Al quitar cargos del duplicado, sus pendientes dejan de figurar: esta disminución de deuda equivocada es intencional. El borrado no se ejecuta durante instalación/actualización.

Se conserva A1–A5, consulta, sesiones, bitácora y respaldos. El archivo activo deja de tener la ficha; no se promete borrado forense del disco ni eliminación de respaldos, bitácora o documentos descargados. No se abre ni modifica ninguna base real en esta tarea.

## Pruebas reales locales

| Comando | Base 1.0.71 | Corrección |
|---|---|---|
| `python -m unittest discover -s tests -v` | 307 en 285,248 s; 304 correctas y tres nativas omitidas; salida 0 | 314 en 243,641 s; 311 correctas y tres nativas omitidas; salida 0 |
| `python tests/run_browser.py` | Salida 0 | Salida 0; incluye eliminación por formulario, discreción, comparación del estado completo y recarga |
| `python tests/run_browser.py --demo` | Salida 0 | Salida 0 |
| `python tests/run_browser.py --roster` | Salida 0 | Salida 0 |

Revisión final de seguridad: `python -m unittest tests.test_institution_archive tests.test_permission_matrix tests.test_read_only_copy -v`: **19 correctas en 31,551 s**, salida 0. Incluye cuatro terminaciones reales (`os._exit`) durante borrado/confirmación/publicación de la cadena, recuperación completa o intacta, respaldo restaurable, rechazo por contraseña/código/CSRF/revisión vieja, carrera con un pago nuevo, fallo de copia local/externa y vínculo de abono ajeno. Matriz HTTP de perfiles y consulta inmutable con la ruta nueva.

Referencias independientes: la ficha correcta, sus cargos, pagos, egresos, representantes, constancias, resumen completo, PDF del recibo y cierre de caja coinciden con el estado sin el duplicado. Tras borrar, Verificar datos, integrity_check y foreign_key_check correctos; el respaldo vuelve a contener el duplicado completo. El alumno no reaparece con la sincronización ni la recarga y su código no se reutiliza.

Los tres omitidos Linux requieren Windows real: DPAPI, mutex y diálogo Tk. El diálogo Tk conserva todas sus aserciones en un proceso hijo, reutilizando únicamente el arreglo de ciclo de vida nativo ya verificado en `6b139e2`; no se incorpora el producto del borrador.

## Windows y entrega

Código enviado: `324d388d586d5d317173adf2a529285e8a52da2c`. [Ejecución 39896577102](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39896577102), job `120228316424`: **en curso; todavía no se declara aprobado**.

El flujo realiza unittest al compilar, las tres suites de navegador, Defender antes/después, instalación/impresión nativa, reinstalación y desinstalación. Descarga el instalador 1.0.71 previamente auditado y comprueba una actualización real y el borrado por HTTP contra el EXE instalado, conservando recibo, alumno correcto y caja. Solo sube el instalador si todos los pasos pasan. No crea release, etiqueta, merge ni firma digital.

Pendiente: resultado Windows e instalador. No se prueba impresora física ni se eliminan las fichas del usuario: esas confirmaciones se hacen en su PC, una ficha a la vez. Instalar no borra automáticamente ningún registro.

## Reversión

Antes de usar la opción, puede conservarse 1.0.71 sin cambiar datos. Después de una eliminación, no se recupera una sola ficha al reinstalar la versión anterior: hay que revisar y restaurar la copia completa anterior, conservando primero los datos actuales y considerando las operaciones posteriores. No reemplazar carpetas a ciegas ni restaurar encima de Aula abierta.
