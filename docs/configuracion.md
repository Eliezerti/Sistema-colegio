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

## Alcance técnico

No se modifica el esquema, la ubicación de datos ni registros contables. El formulario de destino conserva la validación de ruta fuera de la carpeta activa y elimina la declaración de nube si cambia la ruta. Solo Administrador puede guardarlo, con CSRF y comprobación del reloj antes de confirmar. Se registra el valor anterior/nuevo y se crea el respaldo posterior. No genera cargos como efecto de cambiar la ruta.

Las funciones existentes de usuarios, contraseñas, bitácora, protección de Windows, cobros, WAL, synchronous=FULL y respaldos de cinco minutos mantienen sus reglas. Este cambio no adelanta fases de seguridad pendientes.

## Validación

- `python -m unittest discover -s tests -v`: 198 descubiertas en Linux, 197 correctas y una exclusiva de Windows omitida.
- `python tests/run_browser.py`: correcto; recorrido normal, pestañas, teclado, borradores, formularios independientes, nube, recibos, bitácora y usuarios.
- `python tests/run_browser.py --demo`: correcto; datos temporales aislados, sin destino externo ni vaciado real.
- `python tests/run_browser.py --roster`: correcto; importación y exportación en prueba, sin alterar el origen.

Dos pruebas nuevas del servidor verifican que guardar el destino conserva identidad, calendario, alumnos, cargos y pagos, y que mantiene CSRF, validación de ruta y permisos de Caja/Consulta. Pruebas tampoco puede usar esta operación, ni siquiera para vaciar la ruta. Se comprueban bitácora, WAL, synchronous=FULL y copia posterior.

La prueba de navegador comprueba un solo panel visible, navegación con teclado, cambios sin guardar y conservación de un borrador al guardar el otro formulario. El bloqueo del reloj y las transacciones financieras continúan cubiertos por la suite existente. Todas las pruebas utilizan datos ficticios y bases temporales; no se ha accedido a la base real del usuario.

## Instalador 1.0.30

- Código de aplicación: `338ccd07632131f8d611f2eea8e7b9e26607190d`.
- [Ejecución Windows](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38251125520): 198 pruebas correctas en Python 3.12; instalación, accesos directos, ventanas, bandeja, reinstalación y desinstalación conservando datos correctas.
- Defender antes y después sin detecciones, motor `1.1.26080.3`, firmas `1.459.684.0`. Este resultado no certifica la PC del usuario ni resuelve las alertas antiguas de 1.0.8/1.0.14.
- `Aula-Colegio-Instalador-1.0.30.exe`: 20.503.114 bytes; SHA256 `b1a39d03455984ee6e93799d3574c5b6682bc2ddc62ad28d64cf5a5548e6e48a`, verificado contra el archivo descargado, su suma y el registro del runner.
- [Descarga en borrador](https://github.com/Eliezerti/Sistema-colegio/releases/tag/untagged-e9d0e331378824f38692); requiere iniciar sesión en GitHub con acceso al repositorio. Descarga el ejecutable, no el ZIP de código fuente.

Antes de actualizar, crea y verifica el respaldo externo; cierra Aula desde Salir y cerrar Aula e instala con la misma cuenta de Windows. Comprueba tus alumnos, saldos y destino de Drive. En Configuración visita cada pestaña y prueba escribir un borrador, cambiar de apartado y volver. Usa Aula - Pruebas para ensayar cambios de identidad sin afectar los datos reales. La comprobación efectiva y activación de BitLocker de la PC del usuario se realizan desde Windows; no se han ejecutado remotamente.

Archivos del cambio: AGENTS.md, `colegio/server.py`, `static/app.js`, `static/style.css`, `tests/test_system.py`, `tests/test_backup_alerts.py`, `tests/browser.cjs`, README, CHANGELOG, estas guías Markdown/HTML, notas del workflow y ZIP fuente/suma. No se implementan las fases pendientes de cifrado, sesiones o bitácora protegida; no se modifica nómina, móvil/PWA ni personalización de recibos.

## Cierre por inactividad (A3)

Usuarios y acceso permite guardar el tiempo de cierre (15 minutos por defecto, entre 5 y 60). Este formulario guarda solo ese tiempo, registra el valor anterior y nuevo y conserva su borrador al cambiar de pestaña. Las consultas automáticas no renuevan la sesión. [Guía de sesiones y recuperación](sesiones-acceso.md).

## Bitácora · A4

El apartado Bitácora permite al Administrador filtrar y exportar PDF/CSV, revisar valores anteriores/nuevos y comprobar su cadena. Se conserva al vaciar registros. Si falla la verificación, Aula permite consultar y respaldar, pero bloquea cambios. [Guía y prueba manual](bitacora.md).

## Acceso a datos bancarios del personal · A5

En Usuarios y acceso, Caja y Consulta conservan fichas y salarios autorizados, pero no reciben datos bancarios ni abren documentos de nómina o sueldo. Administración conserva ese acceso. No hace falta activar un interruptor. El listado PDF del personal respeta el perfil. [Guía y prueba manual](privilegios-personal.md).

## Verificar datos y cobros · B1

En Protección y mantenimiento se añaden totales de cobros válidos/aplicaciones, cargos duplicados y revisión de saltos por encima de números reservados. La operación no repara ni cambia tus registros. [Guía y comprobaciones de B1](calidad-b1.md).
