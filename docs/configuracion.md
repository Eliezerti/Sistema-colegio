# Configuración por apartados

Entra como Administrador y abre Configuración. Cada pestaña tiene sus propias acciones:

| Apartado | Qué contiene |
|---|---|
| Identidad y calendario | Nombre y razón social, datos fiscales, logo, contactos y calendario escolar. |
| Protección y mantenimiento | Ruta de la segunda copia, respaldos, declaración de nube, diagnóstico de Windows, verificación y restauración. El vaciado permanece en un apartado avanzado con sus controles anteriores. |
| Usuarios y acceso | Crear usuarios y cambiar contraseñas. Se mantienen los permisos actuales. |
| Bitácora | Visor actual de las últimas 300 operaciones. Este cambio no implementa la fase pendiente de cadena de hashes ni exportación. |

Cambiar de pestaña conserva lo escrito. Guardar el destino de respaldo solo modifica esa ruta, no la identidad ni el calendario. Los borradores de estos dos formularios se mantienen en memoria durante la sesión, incluso al guardar otro apartado; no son un respaldo y se pierden al cerrar o recargar la ventana. Cerrar sesión los elimina. No se guardan contraseñas de usuario en esos borradores.

Puedes navegar entre pestañas con las flechas izquierda/derecha, Inicio y Fin. Los avisos de respaldo siguen visibles fuera de las pestañas. Revisar en Configuración abre directamente Protección y mantenimiento.

## BitLocker y su clave de recuperación

«No se pudo comprobar» en Aula significa que Windows no permitió obtener un resultado fiable. No significa que BitLocker esté activo o desactivado. Aula usa los permisos de la cuenta que la abrió; no pide elevación, no cambia permisos ni activa el cifrado.

Los resultados desconocidos aparecen en ámbar para señalar una revisión pendiente. El color no cambia el estado y no confirma protección activa.

1. Busca Administrar BitLocker en Inicio y revisa la unidad donde está la base; Configuración muestra la ruta, por ejemplo C:\Users\…\AppData\Local\AulaColegio\colegio.sqlite3.
2. Si Windows dice BitLocker activado, la comprobación de Aula puede seguir sin permisos. Conserva el resultado como desconocido y revisa Windows cuando lo necesites.
3. Si dice En espera de activación, la protección aún no está activada. Comprueba tu respaldo externo antes de pulsar Activar BitLocker y sigue el asistente de Windows.
4. Cuando Windows pida guardar la clave de recuperación, comprueba que tienes el número de 48 dígitos. Guárdalo en un USB separado o imprímelo. Si ya está activo y la unidad está desbloqueada, Hacer una copia de seguridad de la clave de recuperación permite sacar otra copia.
5. Si la guardaste en una cuenta Microsoft, consulta https://aka.ms/myrecoverykey con esa misma cuenta. Una cuenta vacía no demuestra que no exista una clave: puede estar en otra cuenta o no haberse guardado allí.
6. Escanear un QR y guardar una llave de acceso en la aplicación Contraseñas del teléfono sirve para iniciar sesión; esa llave no es el número de recuperación de BitLocker. Si el QR se usó durante un guardado en Microsoft, verifica por separado que la clave de 48 dígitos aparece en la cuenta.

No compartas la clave en chats o capturas. En Windows con cifrado de dispositivo, busca Cifrado del dispositivo en Configuración; si faltan las opciones o se solicitan permisos, pide ayuda técnica. Si la unidad se está cifrando, espera a que termine antes de considerar completado ese proceso.

BitLocker protege el disco de esa PC, no cifra por sí solo las copias del USB o de Drive. El cifrado de respaldos de Aula continúa pendiente; sus claves, cuando se implemente, serán independientes de BitLocker.

## Usuarios y acceso

Administración crea usuarios con perfil Administrador, Caja o Consulta y puede configurar entre 5 y 60 minutos de inactividad. Consulta no registra ni modifica movimientos. Si otros intentos bloquean un ingreso, utiliza Desbloquear acceso local desde Inicio de Windows, con tu contraseña actual. La recuperación de una contraseña olvidada es una operación distinta.

## Bitácora y comprobación

En Bitácora filtra y exporta operaciones, revisa valores anteriores y nuevos y comprueba la cadena. Si falla, Aula permite consultar y respaldar, pero bloquea cambios. No borres archivos de control para quitar el aviso. En Protección y mantenimiento, Verificar datos y cobros revisa integridad, referencias, saldos y correlativos sin reparar ni cambiar registros.

Aula se utiliza en esta PC. El acceso privado de otras computadoras fue retirado; para soporte usa el escritorio remoto de Windows. Para consultar desde casa, abre un respaldo en solo lectura.
