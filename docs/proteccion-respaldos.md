# Avisos de respaldo y protección de esta PC

## Qué significa el aviso amarillo

Administrador y Caja lo ven en todas las secciones, incluida la pantalla de confirmación de la tasa. No tiene botón para cerrarlo. También permanece al buscar, filtrar y mostrar archivados. Consulta y Aula - Pruebas no lo muestran: Pruebas no crea copias reales.

| Aviso | Qué hacer |
|---|---|
| No hay segunda carpeta configurada | Administrador: Configuración → Segunda copia de seguridad. Escribe la ruta de un USB o de una carpeta externa privada. Guarda los cambios. |
| No hay una copia confirmada | Revisa el destino y pulsa Crear respaldo ahora. Una fecha de copia del destino anterior no confirma la carpeta nueva. |
| La copia externa tiene más de 3 días | Conecta el USB o revisa la carpeta. Administrador: Crear respaldo ahora. Se compara la fecha registrada con la hora del servidor. |
| Falló el respaldo local | Revisa espacio y permisos de la carpeta de datos. No borres la base, WAL ni SHM. Solicita ayuda si vuelve a fallar. |
| Falló la copia al segundo destino | Conecta el USB o revisa espacio y permisos del destino; crea otra copia. El cobro ya confirmado no se borra ni se repite. |

Caja no puede cambiar la configuración ni crear respaldos manuales: debe avisar al administrador. La comprobación de avisos se actualiza cada 30 segundos mientras la pantalla está visible y al regresar a ella. Después de guardar cambios o crear una copia se actualiza la pantalla. El aviso desaparece solamente cuando el estado vuelve a ser correcto.

Una carpeta distinta del mismo disco no protege contra una falla de ese disco. Aula confirma la copia en la carpeta local de Drive, no su llegada a la nube. Estos avisos no inspeccionan continuamente archivos externos borrados manualmente: informan el resultado y la fecha de los intentos de copia registrados. Conserva el USB y comprueba periódicamente una restauración.

## BitLocker y permisos de la carpeta

Administrador: abre Configuración → Protección y mantenimiento → Protección de esta PC. La primera revisión puede estar pendiente unos segundos. Se actualiza en segundo plano, como máximo una vez cada cinco minutos; no bloquea cobros ni modifica datos.

**BitLocker** se comprueba en el disco que contiene la carpeta de datos, no necesariamente en C:. Solo dice **Activo** cuando Windows informa cifrado completo y protección activada. Una protección suspendida no se muestra como activa. Un cifrado en curso se identifica como sin completar.

**No se pudo comprobar** significa que la consulta no dio un resultado verificable. Puede faltar la herramienta de Windows, faltar permiso, ser una unidad no compatible o agotarse el tiempo de consulta. En Linux esta comprobación de Windows tampoco está disponible. No significa «activo» ni confirma que el disco esté desprotegido. No abras Aula como administrador solamente para quitar este mensaje: pide a un técnico que compruebe BitLocker desde Windows y conserve su clave de recuperación fuera de la PC.

La revisión de **ACL** busca permisos adicionales en la carpeta de datos. «Sin accesos adicionales detectados» significa que se encontraron permisos para tu cuenta, SYSTEM y administradores de Windows. «Hay permisos adicionales» indica acceso para otras cuentas o grupos que un técnico debe revisar. Reglas de denegación o resultados incompletos se muestran como no comprobados; no se adivinan los permisos efectivos.

Esta revisión se limita a la carpeta; archivos internos pueden tener permisos distintos. No impide que alguien que controle tu cuenta de Windows acceda a los datos. BitLocker protege el disco frente a acceso fuera de Windows; no cifra automáticamente una copia en USB.

**Aula no cambia ACL, no solicita elevación ni activa BitLocker.** No hay migración de esquema ni cambio de ubicación de la base. Los respaldos automáticos de cinco minutos, copias posteriores a cobros, WAL y `synchronous=FULL` mantienen su funcionamiento. Los respaldos externos y descargados siguen sin cifrar en este punto.

## Prueba manual con el administrador y Caja

1. Comprueba el aviso sin segunda carpeta. Navega a Alumnos, Representantes, Caja y Reportes; busca y filtra. El aviso debe permanecer.
2. Configura una carpeta de un USB, guarda y crea un respaldo. Verifica que apareció una copia `.sqlite3` en el USB y que no hay aviso de error.
3. Desconecta el USB y pulsa Crear respaldo ahora. Debe avisar del fallo externo. Conecta el USB, vuelve a crear una copia y comprueba que desaparece el aviso.
4. Entra como Caja: debe ver el problema, sin acceso a Configuración ni un botón para cerrarlo. Consulta y Pruebas no deben mostrarlo.
5. En Configuración revisa BitLocker y ACL. Contrasta los resultados con un técnico desde Windows. Si no se pudo comprobar, debe decirlo claramente.

No cambies la fecha del equipo con datos reales para simular tres días: todavía falta la protección del reloj. El límite de antigüedad y sus casos de error se comprueban en pruebas automatizadas con datos temporales.


La segunda carpeta se compara con el disco de la base: si comparte disco, aparece un aviso propio aunque la copia esté recién escrita. Si no se puede determinar, se indica. En Windows se comparan unidades y particiones; unidades distintas pueden compartir disco físico. En otros sistemas solo se confirma el mismo sistema de archivos; no se supone independencia entre volúmenes. El almacenamiento virtual y las carpetas de nube requieren comprobar su protección real. Aula no verifica la subida a la nube.

BitLocker se consulta con los permisos de la cuenta que abrió Aula; una cuenta estándar puede no tener permiso. «Cómo comprobarlo desde Windows» explica cómo revisarlo con ayuda del administrador de Windows. Una comprobación manual no convierte el resultado automático desconocido en «Activo».
