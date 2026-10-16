# Respaldos cifrados

## Configurar la protección

En Configuración → Protección y mantenimiento prepara el cifrado con una contraseña nueva. Guarda la clave de recuperación fuera de esta PC y separada de las copias; confirma que la conservaste. No compartas estas claves por el mismo medio que el respaldo. Si pierdes la contraseña y la recuperación, no hay una clave maestra que permita recuperar el contenido.

En Windows, el almacén de esta cuenta permite crear copias automáticas sin pedir contraseña cada cinco minutos. En otra cuenta o PC no necesitas ese almacén para abrir un respaldo: utiliza el archivo y su contraseña o clave de recuperación. Si el almacén falla, Aula no publica una copia externa sin cifrar como alternativa. Las copias locales continúan disponibles.

## Qué queda cifrado

| Archivo | Protección |
|---|---|
| Segundo destino, descarga y conversión de respaldo antiguo | .aulabak cifrado y verificado antes de publicar |
| Copias diarias y mensuales del segundo destino | Cifradas |
| Cierre escolar permanente | Cifrado, local y segundo destino configurado |
| Base activa, copias locales frecuentes/diarias y preservación anterior a restaurar o actualizar | Pueden quedar sin cifrar en esta PC; requieren protección de Windows y del disco |
| PDF, CSV y Excel cotidianos | No se cifran con la contraseña de respaldos |

Protege el disco con BitLocker cuando corresponda y conserva su clave de recuperación por separado. Aula informa lo que puede comprobar, pero no activa BitLocker ni cambia permisos de Windows. No copies la base activa ni respaldos locales sin cifrar a USB o nube. Descarga un .aulabak desde Aula.

## Probar, convertir o restaurar

Probar respaldo abre una copia temporal y comprueba cifrado, integridad, referencias y bitácora sin restaurar. Admite una contraseña o la recuperación. Las .sqlite3 antiguas se identifican como copias sin cifrar. Convertir y descargar cifrado crea otro archivo y conserva el original. No borra versiones sin cifrar anteriores de Drive, su historial ni su papelera: revisa esos archivos antes de producción.

Para restaurar, cierra Aula completamente y usa Restaurar respaldo desde Inicio. Revisa la comparación y la confirmación solicitada. Para mirar una copia sin reemplazar datos, usa Abrir copia en solo lectura.

## Cambiar contraseña

En Protección y mantenimiento prepara y confirma la nueva contraseña. Las copias anteriores mantienen las credenciales de su fecha; cambiar la contraseña no modifica archivos ya creados. Conserva las credenciales necesarias y prueba copias anteriores y nuevas.

## Conservación

El segundo destino conserva 90 copias frecuentes, 60 diarias y 24 mensuales. Los cierres escolares permanentes no se eliminan automáticamente. La rotación solo afecta su propio nivel; no borra respaldos manuales ni .sqlite3 antiguos. Si no se puede comprobar el inventario, no se autoriza borrar copias. Consulta el manual de mantenimiento para la rutina mensual y la prueba externa.
