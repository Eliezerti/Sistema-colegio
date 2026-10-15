# Consultar una copia sin restaurarla

En Inicio → Aula → Abrir copia en solo lectura, selecciona un respaldo .aulabak o una copia antigua .sqlite3. Si está cifrado, usa su contraseña o su clave de recuperación. No necesitas el almacén de llaves de la PC que creó el respaldo.

Aula verifica el archivo y abre una copia temporal separada de los datos reales. No restaura ni reemplaza la base del colegio. No abre para escritura la carpeta de origen. Si el archivo es antiguo, actualiza solamente el temporal; si es de una versión de esquema más nueva, pide actualizar Aula. Una copia corrupta o una contraseña incorrecta no se abren.

El aviso permanente «Copia del [fecha], solo lectura» identifica la consulta. La fecha corresponde a la modificación del archivo y no está certificada; copiarlo puede cambiarla. Los saldos consideran los cargos ya registrados en esa copia. No se generan nuevas mensualidades ni se confirman tasas. Puedes consultar pantallas, recibos ya emitidos y reportes; no registrar pagos, egresos ni cambios. El servidor y SQLite bloquean las escrituras, aunque alguien intente usar una ruta directamente.

La sesión existe solo en memoria y conserva el cierre por inactividad. Al terminar la sesión, abre nuevamente la copia desde Windows. Cierra la ventana para eliminar el temporal, incluido su perfil de navegador. Una consulta cerrada no se incorpora a la base real ni publica respaldos.

Para el ZIP: python -m colegio.read_only RUTA_DEL_RESPALDO. Añade --recovery si usarás la clave de recuperación. La contraseña se pide sin mostrarla y nunca como argumento. Cierra con Ctrl+C.
