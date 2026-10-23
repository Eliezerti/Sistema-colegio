# Corrección de matrículas duplicadas · seguimiento

Solicitud: eliminar dos fichas equivocadas desde Alumnos y matrículas, con una opción discreta. Versión confirmada por el usuario: 1.0.71. Rama `correccion/alumnos-duplicados`, desde `ed1c5e9`. El borrador de ingresos y facturas queda fuera; main y datos del usuario intactos.

## Hallazgo y solución

- `colegio/institution_archive.py:32`: la revisión anterior exige archivar y considera cualquier cargo o evaluación positiva un bloqueo, aunque sea una matrícula equivocada sin cobros.
- `static/app.js:168`: el directorio solo ofrece Editar; el borrado vacío anterior se encuentra en Archivo de la institución.
- Se conserva ese flujo anterior. La nueva revisión `student-deletion-preview/{id}` es exclusiva de Administración; `delete-error-student` exige contraseña, motivo, BORRAR FICHA, código exacto y huella de la revisión actual.
- `colegio/institution_archive.py:53`: se comprueban pagos, abonos por cargo —incluso vínculos dañados con otro alumno—, convenios, seguimientos y documentos familiares/pases de año. Los pagos/recibos anulados siguen bloqueando.
- `colegio/institution_archive.py:133`: mismo respaldo local previo verificado y segundo destino cifrado cuando está configurado. Si falla una copia, no borra.
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

Código compilado y validado: `324d388d586d5d317173adf2a529285e8a52da2c`. [Ejecución 39896577102](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39896577102), job `120228316424`, Windows Server 2022.

| Comando / comprobación | Resultado real |
|---|---|
| `python -m unittest discover -s tests -v` | **314 correctas en 556,162 s; sin omisiones; salida 0** |
| `python tests/run_browser.py` | Correcto, salida 0; también sesión A3 y visor de consulta |
| `python tests/run_browser.py --demo` | Correcto, salida 0 |
| `python tests/run_browser.py --roster` | Correcto, salida 0 |
| Instalación y ejecución nativa | Correctas: normal, Pruebas, consulta cifrada y eliminación del temporal |
| Actualización real 1.0.71 → 1.0.73 | Correcta; instalador anterior auditado descargado y abierto antes de actualizar |
| Borrado contra EXE instalado | Correcto por HTTP: duplicado y cargos retirados; alumno correcto, representante, recibo y caja conservados; Verificar datos correcto |
| Reinstalación y desinstalación | Correctas; datos y respaldo conservados |
| Impresión nativa WebView2 | Correcta: media carta 396×612, media carta en carta 612×792 y dos copias 792×612; una página y escala predeterminada |
| Defender antes y después | Salida 0, sin detecciones; motor 1.1.26090.9, firmas 1.461.158.0, actualizadas 22/10/2026 20:19:07 UTC |

**Instalador disponible:** [Aula 1.0.73 · corrección de alumnos](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39896577102/artifacts/12476584809). ZIP de 19.171.730 bytes; contiene únicamente `Aula-Colegio-Instalador-1.0.73.exe`. No es el borrador de ingresos/facturas. No se crean release, etiqueta, merge ni firma digital.

**Fallo de infraestructura, sin ocultarlo:** el job global terminó en failure porque la última etapa, «Conservar evidencia», mezcló archivos de C: y D: y upload-artifact rechazó la raíz común. Todas las etapas del producto y la subida del EXE terminaron en success antes de ese fallo. Mensaje completo: `The rootDirectory: D:\\a\\Sistema-colegio\\Sistema-colegio is not a parent directory of the file: D:\\a\\_temp\\aula-recibo-native\\comprobante-dos-copias.pdf`. El registro de texto completo se recuperó por el conector autorizado de GitHub, incluida la confirmación de cada prueba y del instalador subido. El ZIP auxiliar de PDF/registros no se publicó. Pendiente de infraestructura: copiar los archivos a una única carpeta antes de empaquetar la evidencia en una ejecución futura.

El entorno local quedó unavailable al finalizar Windows. Código y documentación anteriores ya estaban subidos; este informe final se guarda directamente en la misma rama mediante GitHub. La única edición local posterior era la referencia de línea 125→133, incorporada aquí. No se afirma descarga ni comprobación local del EXE tras perder el entorno.

No se prueba impresora física ni se eliminan las fichas del usuario: esas confirmaciones se hacen en su PC, una ficha a la vez. Instalar no borra automáticamente ningún registro. No se ejecutó instalación con otra cuenta Windows en esta corrección; la actualización comprobada usa la misma cuenta. No se ha repetido una suite correcta para corregir únicamente documentación.

## Reversión

Antes de usar la opción, puede conservarse 1.0.71 sin cambiar datos. Después de una eliminación, no se recupera una sola ficha al reinstalar la versión anterior: hay que revisar y restaurar la copia completa anterior, conservando primero los datos actuales y considerando las operaciones posteriores. No reemplazar carpetas a ciegas ni restaurar encima de Aula abierta.
