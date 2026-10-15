# Tanda D · en desarrollo

- D7: actualización nativa desde 1.0.67, portabilidad cifrada en otra cuenta Windows, cortes reales durante publicación por niveles y guía de pruebas físicas.

- D6: morosidad por grado en reporte diario y cierre mensual PDF/CSV con monedas y métodos separados, egresos, saldo, pendiente y anulaciones de bitácora, sin datos personales de alumnos.

- D5: abrir respaldos cifrados o antiguos en consulta aislada; SQLite inmutable, escrituras bloqueadas en servidor, sesión en memoria y temporal eliminado al cerrar.

- D4: niveles cifrados de 60 copias diarias y 24 mensuales, cierres escolares permanentes y recordatorio de prueba externa después de 35 días.

- D3: estado principal acotado con totales íntegros; historial bajo demanda y medición HTTP reproducible de 500/800 alumnos con uno, dos y tres años.

- D2: recuperación local durante un bloqueo de login, con contraseña de Administración, código de un uso, vencimiento monotónico y bitácora; el limitador de fuerza bruta se conserva.

- D1: documentación interna fuera del instalador y limpieza de copias antiguas; correlativos privados; calendario explícito al crear el administrador; rechazo de Nómina en egresos nuevos sin alterar históricos; retiro del acceso privado, conservando acceso local y sus protecciones. Sin migración.

# Historial de cambios

## Mensualidades y administración mínima · esquema 12

- Retiro de Personal y Nómina: API, interfaz, documentos, módulos y cuatro tablas. Egresos simplificados sin empleado ni horarios; importes y correlativos existentes conservados.
- Migración con copia previa verificada, reconstrucción transaccional de expenses, cinco cortes reales y cadena de bitácora original conservada. Restauración y conversión de respaldos antiguos migran únicamente la copia privada antes de publicarla.
- Instalación en cero: identidad genérica, sin usuarios o datos precargados, pisos cero y primeros R-/E-/AL- en 1. Plantilla sin personas de ejemplo; modo Pruebas separado. Vaciar registros retirado de producción.
- README, inventario, guías y Puesta en producción actualizados; guías y recursos de Personal eliminados. Se conservan A1–A5, cifrado, sesiones, bitácora, respaldos y cobros. B3/B4 pendientes. Linux: 292 en 150,716 s, 289 correctas y tres nativas omitidas; normal/--demo/--roster PASS. Windows: 292 correctas en 486,343 s sin omisiones; instalación en cero, actualización publicada y segunda cuenta real PASS. Impresión nativa y Defender antes/después correctos. Instalador 1.0.67 descargado y SHA-256 coincidente. Las primeras revisiones detectaron aserciones de funciones retiradas, pisos ahora presentes en cero y diferencias de cabecera por WAL; se corrigieron las pruebas al contrato nuevo sin desactivar WAL/FULL ni omitir controles.

## Comprobante · ORIGINAL y COPIA, márgenes y firmas · 1.0.62 verificada

- Media carta individual de 396 × 612 puntos con márgenes cercanos a 5 mm, contenido más arriba y pie junto al contenido. Zona para firma ampliada.
- Nueva opción carta horizontal de 792 × 612 puntos: dos medias cartas verticales al 100 %, identificadas únicamente ORIGINAL y COPIA, con el mismo R-, importes y referencia. No duplica operaciones ni modifica cálculos, correlativos, datos, esquema o A1–A5. B3 sigue pendiente.
- Comprobaciones de PDF, cambio repetido de formato sin acumular copias, conservación del pago e impresión nativa de ambas copias. Linux: 299 descubiertas en 167,031 s, 296 correctas y tres nativas omitidas; normal, --demo y --roster PASS. Windows: 299 correctas en 577,177 s sin omisiones; impresión nativa y comparación independiente de ambas copias PASS, instalación/actualización/otra cuenta y conservación correctas. Defender antes/después sin detecciones. EXE descargado: 21.248.159 bytes y SHA-256 coincidente. Evidencia en la guía.

## Comprobante de pago · media carta vertical · 1.0.57 verificada

- Media carta vertical de 13,97 × 21,59 cm, PDF real de 396 × 612 puntos y formato predeterminado también en la descarga directa. Encabezado, espacios y firmas compactados; conserva R-, representante, alumno/grado, conceptos, importes, saldo, método y referencia. Sin código AL- ni cédula escolar.
- Impresión con ancho físico fijo de 396 puntos; hoja carta al 100 % sin ampliación. Prueba nativa WebView2 ampliada con PDF ficticio de tres conceptos, dimensiones, página única y escala explícita 1,0.
- Validación final: Linux 297 descubiertas en 170,788 s, 294 correctas y tres nativas omitidas; navegadores normal/--demo/--roster PASS. Windows 297 correctas en 419,073 s sin omisiones; PDFs nativos de una página y equivalencia de posiciones/tamaños al 100 %, instalación/actualización/otra cuenta y conservación completas. Defender antes/después sin detecciones. Instalador 1.0.57 de 21.248.716 bytes descargado y SHA-256 coincidente.
- 1.0.54 y 1.0.56 no se entregan: la verificación independiente detectó efectos de reglas adaptables sobre número R- y saldo. Se corrigieron las reglas de impresión y se repitieron las cuatro suites y Windows, sin relajar verificaciones. Ejecución 1.0.55 exclusivamente diagnóstica sobre los PDFs guardados, sin compilar instalador.
- Sin migración, cambios de cálculos, correlativos o datos históricos; A1–A5 conservados. B3 pendiente. Resultados de validación en [la guía](docs/comprobante-media-carta.md).

## B2 · Limpieza y reducción · 1.0.53 verificada

- Opción 2 aprobada: se retiran PWA/pasarela Wi-Fi y recursos exclusivos, sin retirar el menú adaptable ni el acceso privado del escritorio. Pago móvil y teléfonos de contacto permanecen.
- Interfaz adaptable independiente; desregistro de trabajador anterior y limpieza solo de cachés públicos de Aula. Rutas retiradas responden 404.
- Mensajes y README distinguen accesos del instalador y lanzadores del ZIP; se corrigen nombres anteriores y textos operativos desactualizados.
- Pruebas nativas ampliadas para Tcl/Tk, calendario, selectores y PDF/impresión WebView2, siempre con datos temporales; la impresión física queda para el usuario. Se retiran tres pruebas exclusivas de la pasarela eliminada y se añade rechazo de sus argumentos antes de abrir datos.
- Inventario previo real del PYZ/archivos del instalador anterior entregado 1.0.49 (borrador), con huella y Defender. Inventario confirmado: 733 módulos, 1.113 archivos y 58.445.044 bytes instalados. Se excluyen 181 módulos presentes de las familias aprobadas y 128 recursos (738.446 bytes); Tcl/Tk, es_ve, encodings, tzdata y directorios requeridos por WebView2 permanecen. Spec sin UPX y comprobación del PYZ antes de publicar.
- Actualización: retiro de 128 archivos de programa obsoletos con rutas exactas del inventario, sin borrar carpetas completas ni tocar base/respaldos. Se comprueba también actualización real desde 1.0.49 e inventario de la instalación actualizada.
- Verificador de Defender: el tercer canal oficial requiere paquete Microsoft con Authenticode válido y registra su huella antes de aceptar la actualización.
- 1.0.50: inventario real y 295 pruebas Windows correctas, pero actualización posterior de firmas fallida; sin publicación. Se añade como tercer canal el paquete oficial x64 de Microsoft, con firma válida, versión/frescura y Defender activo obligatorios; los análisis y bloqueo permanecen.
- Resultados reales Linux: 296 en 172.376 s, 293 correctas y tres nativas omitidas; los tres recorridos solicitados correctos y prueba adaptable adicional con desregistro real del trabajador antiguo y conservación de otro. Windows final: 296 correctas sin omisiones en 442.306 s; controles nativos y actualizaciones/otra cuenta/conservación completos. Runner 38454601433, fuente 1938dfb.
- 1.0.51 cancelada para incorporar retiro seguro al actualizar. 1.0.52 correcta en pruebas/ventanas/actualizaciones, pero con fuentes de plataformas sobrantes en datos: filtro corregido y validación completa repetida en 1.0.53. Canal oficial de firmas ejercitado en 1.0.52, sin detecciones; no se afirma impresión física ni Windows 10/11 local.
- [Instalador final en borrador](https://github.com/Eliezerti/Sistema-colegio/releases/tag/untagged-a7c54162b1e7e546f55f): 21.236.040 bytes frente a 23.272.158, reducción 8,75%. Runtime comparable 53.658.392 → 51.210.228 bytes, reducción 4,56%; PYZ 733 → 492 módulos. Fuente ZIP descargada coincide tras normalizar finales de línea.
- SHA256 EXE descargado `7bdf71a73abc03e72bb13d53d1dcf9fc999630e947d0806fbfbdd8b8466afb85`, coincidente con sidecar y ambos análisis. Defender motor 1.1.26080.3, firmas 1.459.691.0, sin detecciones. Inventarios antes/después/actualización conservados y guía manual; se detiene B2 antes de B3.

## B1 · Consistencia y pruebas reales · 1.0.49 verificada

- Verificar datos: totales de cobros válidos/aplicaciones, duplicados y saltos por encima de reservas; ninguna reparación ni cambio de esquema/datos/cálculos.
- Cortes reales en respaldo local y borrado; prueba HTTP simultánea de cinco cuentas de Caja, calendario y seis decimales. Matriz automática de rutas con contrato independiente y evidencia por perfiles/CSRF.
- Se conservan pruebas anteriores de cobro/restauración/cifrado/bitácora y febrero 29. Revisión dirigida final: 11 pruebas correctas en 8.444 s; 86 rutas y 561 solicitudes comprobadas. Expectativas iniciales corregidas en las nuevas pruebas, sin debilitar el producto.
- Primer intento nativo 1.0.43 detenido antes de ejecutar pruebas: el contexto runner.temp se había declarado al nivel de trabajo; se mueve al paso que ejecuta las pruebas. No se generó ni publicó instalador.
- Intento 1.0.44: 298 pruebas Windows correctas en 359.688 s; instalación nueva y comparación financiera tras actualizar desde 1.0.13 correctas. La prueba de desinstalación se detuvo al asumir unins000.exe; ahora consulta la ruta registrada por Windows. La segunda cuenta no se alcanzó y no se publicó instalador.
- La revisión 1.0.45 completó actualización, migración, desinstalación y conservación de base/respaldo; el mensaje final usó una flecha no representable en CP1252 y detuvo la prueba antes de la segunda cuenta. Se fija UTF-8 en los flujos del verificador, sin cambios del producto. No se publicó instalador.
- Se ajusta la identidad numérica a la sintaxis de icacls (*SID) únicamente en la carpeta ficticia compartida; la ejecución 1.0.47 se cancela antes de terminar para verificar el script corregido, sin presentarla como pasada.
- La revisión 1.0.48 completó instalación nueva, actualización desde 1.0.13 y desinstalación con base/respaldo conservados; la segunda cuenta se creó, pero el puente del verificador heredó TEMP de la principal y recibió acceso denegado antes de cargar su entorno. Se compila el puente solo en el área ficticia autorizada y luego se sustituye el entorno por el bloque real generado para su token. No se publicó instalador ni se afirmó la segunda cuenta como aprobada.
- Pruebas Windows integradas en el pipeline: se guardan evidencias de permisos, actualización histórica y segunda cuenta; el ZIP se construye desde el commit probado. No se modifica el empaquetado de módulos ni se adelanta B2.
- Preparada validación nativa de instalación sin datos, actualización desde 1.0.13 publicada (SHA256/Defender antes de abrir), segunda identidad estándar real y conservación al desinstalar. Linux final: 298 pruebas en 170.610 s, 295 correctas y tres nativas omitidas; los tres recorridos de navegador correctos. Windows final: 298 correctas sin omisiones en 425.470 s; instalación sin datos, actualización publicada 1.0.13 → 1.0.49 y segunda cuenta estándar real correctas, con conservación al desinstalar. [Guía](docs/calidad-b1.md).

- 1.0.49: primer intento detenido por actualización de firmas; segundo con un error Windows 10053 en una prueba existente. Tercer intento completo correcto sin modificar móvil/PWA ni relajar pruebas. Runner 38441960072, intento 3, fuente c3152ed.
- [Instalador final en borrador](https://github.com/Eliezerti/Sistema-colegio/releases/tag/untagged-271c812f1502ae021e92), 23272158 bytes; SHA256 descargado `3d4846ab01e76a96c3e3dc738a1945dfde1aa0d3fb845173e7fc18cf3e0ead2b` coincide con sidecar y ambos análisis. Defender motor 1.1.26080.3, firmas 1.459.691.0, sin detecciones antes/después. ZIP descargado verificado, 166 archivos y fuente probada (finales de línea normalizados).
- Matriz completa Linux en docs/permisos-b1.md/csv. El artefacto Windows fue subido por el runner; su descarga local dio HTTP 403 y no se afirma haber leído los JSON. Resultados nativos comprobados en registros completos. Windows Server 2022 con herramientas de desarrollo; hardware, BitLocker, Windows 10/11 del usuario y pruebas sin internet pendientes. Se detiene B1 antes de B2.

## A5 · Datos bancarios por perfil · 1.0.42 verificada

- Proyección de empleados y resumen de nóminas en el servidor: Caja/Consulta no reciben banco, cuenta, tipo ni datos del titular. Documentos JSON/PDF de nómina y sueldo exclusivos de Administración, incluidos los históricos.
- Directorio/PDF del personal sin columnas bancarias para perfiles restringidos; acciones adaptadas sin sustituir el control del servidor. Caja conserva el registro de egresos/sueldo y Administración abre el recibo.
- Sin migración, cambios de datos existentes o cálculos. Se conservan A1–A4 y los respaldos de cinco minutos.
- Seis pruebas HTTP por perfiles y recorrido de navegador ampliado. Primera revisión dirigida: 13 de 14 correctas; una aserción nueva de estructura de arqueo corregida sin tocar el cálculo. Linux final: 287 pruebas en 156.063 s, 284 correctas y tres nativas de Windows omitidas; navegador normal, Pruebas y roster correctos. Windows final: 287 correctas en 384.343 s, sin omisiones; instalación/accesos/ventanas/bandeja/reinstalación/desinstalación conservando datos. [Guía](docs/privilegios-personal.md).
- [Instalador 1.0.42 en borrador](https://github.com/Eliezerti/Sistema-colegio/releases/tag/untagged-b75722b7d277df4695d2), 23270319 bytes; SHA256 `44789c21c1d0c9fb731bda632d657640eace1700e184b5159a7010f67c2bf534` comprobado tras descargar contra sidecar y ambos análisis. Defender motor 1.1.26080.3, firmas 1.459.691.0, sin detecciones antes/después. Runner 38344052502 sobre commit 5dd2e0f. No se afirma prueba en tu PC, otra cuenta de Windows ni actualización desde un EXE histórico.
- Fuente A5 en 5dd2e0f; documentación final y ZIP de código actualizado para la entrega. Se detiene la tanda A sin avanzar a la B ni a SQLCipher.

## A4 · Bitácora protegida · 1.0.41 verificada

- Esquema 11: tablas acompañantes de huellas y guardas SQLite; filas originales conservadas. Copia previa verificada, reversión y cortes reales del proceso probados con bases ficticias.
- Cadena SHA-256 y control separado con publicación recuperable; inserción oficial, actualización/borrado de bitácora rechazados.
- Valores anteriores/nuevos calculados desde SQLite, sin contraseñas/tokens ni cuentas bancarias completas. Vaciar conserva toda la historia. Restaurar enlaza ramas y el detalle de movimientos excluidos sin debilitar A1.
- Consulta conservada si falla la verificación; se impiden cambios y generación automática. Visor Administrador con filtros y exportaciones PDF/CSV. [Guía](docs/bitacora.md).
- Visor con detalles desplegables, conservación de borradores de otros apartados y exportaciones protegidas frente a fórmulas de Excel; pruebas de permisos y navegador añadidas.
- La primera ejecución Windows ejecutó 278 pruebas en 428.856 s y detectó una carrera de publicación; no generó instalador. Se corrige con coordinación por base y pruebas concurrentes y de SAVEPOINT.
- Guías HTML de A4, mantenimiento y configuración con enlaces a archivos incluidos en el instalador; comprobación de existencia de destinos locales.
- Exportación con rótulos de filtros en español y lectura tolerante de detalles históricos del operador, sin cambiar sus filas originales.
- Linux final: 281 pruebas en 147.706 s, 278 correctas y tres exclusivas de Windows omitidas; los tres comandos de navegador correctos. 22 métodos nuevos en test_audit_chain.py y test_audit_api.py; recorrido de navegador ampliado.
- Windows final: 281 correctas en 320.496 s, sin omisiones; instalación/accesos/ventanas/bandeja/reinstalación/desinstalación conservando datos. Runner 38342112487 sobre f9cb708. La revisión 1.0.39 pasó 280 pruebas; 1.0.40 se canceló antes de completar para incluir la corrección final, sin afirmar éxito.
- [Instalador 1.0.41 en borrador](https://github.com/Eliezerti/Sistema-colegio/releases/tag/untagged-a74c40a40fbb6b05fd60), 23264641 bytes; SHA256 `7ca76e87faa003708666c7ee05aadda8206f7918e25f1729cd5ef9e1f120b8a5` verificado tras descargar contra sidecar y ambos análisis Defender. Motor 1.1.26080.3, firmas 1.459.691.0, sin detecciones antes/después. No se afirma prueba de tu PC ni actualización desde el EXE 1.0.37.
- Commits de implementación: 7e46253 (migración/cadena), 0f26c3e (visor/exportaciones), 71deefc (concurrencia/reversión), de5a556 (enlaces instalados) y f9cb708 (detalles históricos/textos). No se avanza a A5.

## A3 · Sesiones y recuperación de acceso · 1.0.37 verificada

- Cierre de 15 minutos configurable entre 5 y 60, tiempos monotónicos y máximo absoluto de doce horas. Las consultas automáticas no renuevan; cookies conservan HttpOnly/SameSite/Secure y CSRF. Tokens SHA-256 en SQLite; reiniciar exige ingreso nuevo.
- Verificación de clave libera sus recursos incluso si falla la consulta o el comprobador; prueba de fallos consecutivos sin bloqueo persistente.
- Espera por cuenta y origen/cuenta desde cinco fallos, progresión 5/10/20/40/60 segundos, sin prohibición global de 127.0.0.1.
- Recuperación local con respaldo previo, invalidación de todas las sesiones y aviso persistente por administrador; evento sin contraseñas. Sin migración de esquema ni cambios financieros.
- Cierre oculta datos incluso si falla conservar el borrador; evita depender de structuredClone en WebView2 anteriores y prueba ambos casos en navegador.
- Primera compilación Windows 1.0.36: 259 pruebas correctas en 288.365 s sin omisiones, instalación y dos análisis Defender sin detecciones (motor 1.1.26080.3, firmas 1.459.691.0). Se reemplaza por la revisión final de captura segura, verificada en 1.0.37. SHA256 1.0.36: `237be299404d54c1efade6770bdd7eba43c4c93bd134320315c74b23f5719666`.
- Aviso un minuto antes, borrador solo en RAM para el mismo usuario/perfil, sin contraseñas ni archivos. Oculta datos al vencer, descarta borradores al cambiar de usuario y no los guarda automáticamente. Preferencia independiente en Usuarios y acceso.
- Linux final: 259 pruebas en 135.019 s, 256 correctas y tres exclusivas de Windows omitidas. Recorridos normal (incluye A3), Pruebas e importación correctos. 17 métodos nuevos; cambio de umbral en prueba del reloj. Windows final: 259 correctas en 376.416 s, sin omisiones; instalación/accesos/ventanas/bandeja/reinstalación/desinstalación conservando datos.
- Primer recorrido Python: 255 pruebas en 129.290 s, 252 correctas y tres exclusivas de Windows omitidas. Ese recorrido preliminar fue superado por la verificación final; evidencia en docs/sesiones-acceso.md.

- [Instalador final 1.0.37 en borrador](https://github.com/Eliezerti/Sistema-colegio/releases/tag/untagged-f612cb9336e27ef27bd0), 23233045 bytes; SHA256 `6492167f388f77a76fff97846c06d3aadf32044b1b84c5ba33ad0e561cc81405` comprobado contra sidecar y ambos análisis. Defender motor 1.1.26080.3, firmas 1.459.691.0, sin detecciones antes/después. Runner 38333489104, fuente d5b7a46. Las alertas antiguas y la prueba del equipo del usuario siguen pendientes. No se avanza a A4.

## A2 · cifrado de respaldos (sin migración SQL)

- AES-256-GCM, scrypt 128 MiB, envolturas por contraseña y recuperación X25519/HKDF, formato AULABK01 documentado. Nonces reservados antes de cifrar, independientes del reloj/SQLite.
- Recuperación mostrada una vez con confirmación de últimos cuatro. Windows DPAPI protege solo material derivado/estado local; fuera de Windows se desbloquea RAM al iniciar. No contraseñas ni recuperación secreta en SQLite, logs, informes o exportaciones. Cambio de contraseña conserva recuperación y afecta solo copias nuevas.
- Cubre cuatro salidas: automática externa, descarga y externas previas a vaciar/borrar. Verifica ambas envolturas, descifra localmente y comprueba huella/integridad/referencias antes de publicación atómica. Temporales externos siempre cifrados; locales privados sin confiar en TMP/USB/nube. Cortes reales y limpieza de trabajos propios en siguiente inicio.
- A1 acepta cifradas y antiguas con advertencia, conserva comparación, correlativos, informes y recuperación. Conversión voluntaria crea otra copia; no borra originales antiguos ni versiones de Drive. Locales 5 minutos/diarios y especiales mantienen comportamiento; especiales conservadas indefinidamente.
- Configuración tiene tarjeta propia de cifrado, preparación/confirmación y hoja de recuperación para imprimir; se limpia al cerrar. Probar respaldo ofrece contraseña/recuperación y conversión sin borrar. Herramientas de Inicio aceptan ambas clases; autoprueba del ejecutable ejercita AES/scrypt/X25519/DPAPI reales sobre datos ficticios.
- Pruebas: vectores NIST/RFC, alteración/truncamiento, contraseña/recuperación, épocas, nonces, esquema 99 cifrado, permisos/CSRF, cinco cortes reales, persistencia/DPAPI y navegador. Linux final: 242 descubiertas en 129.630 s, 239 correctas y tres nativas omitidas; navegador normal, Pruebas e importación correctos. Windows 1.0.35: 242 correctas en 376.997 s, sin omisiones, incluidas DPAPI y pruebas de corte.
- Primera ejecución del runner 38311993958: unitarias correctas, actualización de firmas falló en Windows Update/MMPC; no se analizó, ejecutó ni publicó el instalador. Segundo intento sobre c82dc0d completó instalación/accesos/ventanas/bandeja/reinstalación/desinstalación conservando base y respaldo; ejecutable ejercitó cifrado y ambas credenciales con datos ficticios.
- Defender antes/después sin detecciones: motor 1.1.26080.3, firmas 1.459.690.0. [Instalador 1.0.35 en borrador](https://github.com/Eliezerti/Sistema-colegio/releases/tag/untagged-3e6bb27e7d59ebbe89ea), 23220929 bytes; SHA256 `af8bdbf4f1f496518db8d4182f04b4ca338671336b25b47113c8fae60abda7e1` coincide con sidecar y ambos análisis. No resuelve alertas antiguas ni certifica la PC del usuario. No se avanza a A3 ni se cambian sesiones, bitácora general, nómina, móvil, ubicación o firma.


## A1 · restauración segura (sin nueva migración)

- Revisión de esquema/integridad/referencias en copia temporal; esquema 99 rechazado. Comparación por identidad/contenido y confirmaciones reforzadas para pérdida o base ilegible.
- Copia previa, originales y candidata preservados; intención persistente comprobada. Inicio recupera la operación antes de conectar/migrar/generar mensualidades; registro dañado bloquea el inicio.
- Conserva máximos de seis correlativos, informes de pérdida PDF/CSV sin cuentas bancarias/contraseñas y registros en SQLite y archivo externo.
- Fixtures generadas desde tags publicados 1.0.4/6/7/13, con manifiesto SHA256; pruebas de cortes reales y saldos después de las migraciones ya existentes.
- Probar respaldo disponible en Configuración y como acceso independiente de Inicio; carga autenticada con CSRF, temporal eliminado y límite web de 32 MB. Diálogos nativos muestran comparación y confirmación, rutas de informes y revisión de correlativos ilegibles. Instalador incorpora solo el nuevo acceso.
- Instalador mantiene Tcl/Tk y dependencias existentes; solo agrega el acceso Probar respaldo y comprueba su destino/argumentos. El ZIP fuente incluye únicamente las cuatro fixtures ficticias verificadas por su manifiesto; excluye bases reales.
- Revisión e informes usan nombres comprensibles en español (Pagos, Cargos, Representantes), sin mostrar nombres internos de tablas. Comprobador nativo traduce errores de SQLite de copias dañadas; prueba explícita de mensaje.
- Cifrado, sesiones, cadena de bitácora, privilegios, reducción y firma permanecen fuera de A1.
- Validación Linux final: 223 descubiertas en 74.415 s, 221 correctas y dos exclusivas de Windows omitidas; los tres recorridos de navegador correctos. Esquema futuro también bloqueado al iniciar, antes de migrar.
- Windows [1.0.34 en borrador](https://github.com/Eliezerti/Sistema-colegio/releases/tag/untagged-53d32cb7abf24fbc94e9): 223 pruebas correctas en 255.960 s sin omisiones; instalación, accesos de Inicio, ventanas normal/Pruebas/bandeja, reinstalación y desinstalación conservando base/respaldo. Runner 38303608499 sobre 7a349eb. La primera compilación A1 1.0.33 también pasó; se reemplaza en la entrega por el ajuste de textos en español, no por un fallo de pruebas.
- Defender antes/después: motor 1.1.26080.3, firmas 1.459.690.0, sin detecciones. Instalador descargado de la versión, 20,541,854 bytes; hash coincide con sidecar y ambos registros de análisis. SHA256: `cd88a16defd595c2374cee29a9281abc71911a8ed728bf9e0743344b0bad9ec8`. Permanece en borrador por las alertas antiguas pendientes; pruebas de la PC del usuario y actualización desde binarios históricos no se afirman como realizadas.

## Sin publicar · Archivo de la institución

- El Administrador temporal de Aula - Pruebas puede borrar fichas ficticias sin una contraseña desconocida: motivo, confirmación, revisión y copia temporal siguen siendo obligatorios. Esta excepción depende del modo del servidor; el sistema real exige contraseña incluso si el cliente envía «demo». No accede a la base real ni copia pruebas a la nube.

- Módulo exclusivo de Administración con apartados de alumnos, representantes y personal, búsqueda, filtro por estado y una sola acción de revisión por fila. Las acciones de archivo salen de los directorios habituales.
- Archivo/recuperación conserva historial; personal reutiliza su estado Inactivo. El listado y PDF de personal permiten incluir inactivos explícitamente, sin cambios al motor de nómina.
- Borrado definitivo limitado a fichas archivadas sin cargos, pagos, egresos, convenios, seguimientos, documentos financieros o vínculos. Un saldo de $0 no basta. Las constancias propias sin movimientos se detallan y eliminan junto a una ficha de alumno vacía.
- Administración, CSRF, contraseña, motivo, confirmación escrita y revisión vigente se comprueban en servidor. Copias previas únicas verificadas localmente y en el segundo destino configurado; fallo de cualquier copia cancela el borrado.
- Conserva bitácora, fichas ajenas y correlativos de fichas/constancias eliminadas. No elimina respaldos anteriores ni archivos descargados. Sin migración de esquema o modificación automática de fichas existentes.
- Validación Linux: 210 pruebas descubiertas, 209 correctas y una exclusiva de Windows omitida; recorridos de navegador normal, Pruebas e importación correctos. Nueve pruebas nuevas de archivo y una de aislamiento temporal, permisos, historial con saldo cero, documentos con vínculos históricos, copias verificadas/restaurables, fallos y correlativos.
- Primer intento Windows 1.0.31 detenido antes de generar el instalador: tres conexiones de inspección en las pruebas quedaron abiertas y bloquearon la limpieza de archivos temporales. Se corrige su cierre explícito; no se omiten pruebas ni se altera código de aplicación para resolverlo.
- Instalador 1.0.32 validado: 210 pruebas correctas en Windows, instalación/ventanas/actualización/desinstalación conservando datos y dos análisis de Defender sin detecciones (firmas 1.459.684.0). SHA256 del ejecutable descargado comprobado. Permanece en borrador por las alertas antiguas pendientes; resultados y pasos manuales en docs/archivo-institucion.md.

## Sin publicar · Pago móvil y recibos más claros

- Pago móvil disponible en cobros y separado en reportes y cierres; conserva moneda, tasa, referencia, transacciones e idempotencia. No cambia métodos ni cálculos de nómina.
- Recibos HTML, impresión y PDF A4/media carta/tickets sin cédula escolar ni código AL-. Se mantienen número R-, identificación del representante e instantáneas históricas.
- Arqueo indica «Efectivo inicial en caja» y explica que el saldo bancario y los cobros electrónicos no son efectivo físico. Sin migración de esquema.
- Validación independiente de este cambio: 200 pruebas descubiertas en Linux, 199 correctas y una exclusiva de Windows omitida; los tres recorridos de navegador correctos. Prueba real de Pago móvil en bolívares, reintento idempotente y cierre separando efectivo USD/Bs de cobros electrónicos; PDF de todos los formatos sin AL- ni identificación escolar.

## Sin publicar · configuración organizada por apartados

- Pestañas independientes de Identidad y calendario, Protección y mantenimiento, Usuarios y acceso y Bitácora; navegación accesible por teclado y un solo apartado visible.
- El destino de respaldo se guarda con una operación limitada a esa ruta, sin modificar identidad, calendario ni datos contables. Conserva permisos de Administrador, CSRF, validación de ruta, bitácora y respaldo posterior.
- Los borradores de identidad y destino se conservan en memoria al cambiar de pestaña y guardar otro apartado; se borran al cerrar sesión. No se guardan contraseñas en esos borradores.
- Ayuda de Windows distingue BitLocker, su recuperación de 48 dígitos y las llaves de acceso de Microsoft. No activa BitLocker ni presenta un resultado desconocido como activo.
- Preferencias permanentes registradas en AGENTS.md. Sin migración de esquema, cambio de ubicación, modificación de registros existentes, móvil/PWA o nómina.
- Validación Linux: 198 descubiertas, 197 correctas y una exclusiva de Windows omitida. Navegadores normal, Pruebas e importación correctos; dos pruebas nuevas de servidor y ampliación del recorrido de Configuración.
- Instalador 1.0.30: 198 pruebas correctas en Windows, instalación, ventanas, reinstalación y desinstalación conservando datos. Defender antes/después sin detecciones, firmas 1.459.684.0; archivo descargado verificado por SHA256. Continúa en borrador por las alertas antiguas pendientes.

## Sin publicar · carpeta de nube declarada por administración

- Declaración manual de una carpeta sincronizada con Drive, OneDrive o Dropbox, después de verificar una copia reciente en su web. Sustituye únicamente el aviso de disco desconocido por un recordatorio discreto.
- No afirma que Aula verificó la subida ni cambia el diagnóstico de discos, ACL o BitLocker. Los avisos de mismo disco, falta de destino, fallos y copias antiguas siguen visibles.
- Solo Administrador, con CSRF y revisión explícita, puede declarar o quitar la declaración. Se registra el cambio en bitácora. Cambiar la ruta la invalida; una declaración de otra PC no se aplica.
- Usa una clave opcional de configuración existente, creada solo al confirmar; no hay migración de esquema ni modificación de datos contables. Conserva respaldos de cinco minutos y protección del reloj.
- Validación Linux: 196 descubiertas, 195 correctas y una exclusiva de Windows omitida. Navegadores normal, Pruebas e importación correctos. Ocho pruebas nuevas de permisos, persistencia, alcance, fallos, otra PC y conservación de esquema/importes.
- Instalador 1.0.29 en borrador: 196 pruebas correctas en Windows, instalación/ventanas/reinstalación/desinstalación conservando datos y dos análisis de Defender sin detecciones. Archivo descargado y SHA256 verificados; siguen pendientes las alertas antiguas del equipo del usuario.

## Sin publicar · identificación del alumno en recibos

- La pantalla de recibo, la impresión y los PDF A4, media carta y térmicos muestran el código interno de Aula, nunca el documento del alumno como reemplazo.
- Los recibos anteriores sin código muestran «Código interno no registrado». Se conserva la identificación del representante y el documento del alumno en la ficha y la constancia de matrícula.
- Pruebas con código presente, ausente, vacío y nulo; no se modifica SQLite, cobros ni instantáneas históricas. No se ha aplicado el cifrado ni comenzado los puntos posteriores.
- Validación Linux: 188 pruebas, 187 correctas y una exclusiva de Windows omitida; navegadores normal, Pruebas e importación correctos.
- Instalador 1.0.28 en borrador: 188 pruebas correctas en Windows, instalación/ventanas/reinstalación/desinstalación conservando datos y dos análisis de Defender sin detecciones. SHA256 verificado contra el archivo descargado y el registro del runner. Las alertas anteriores del equipo del usuario siguen pendientes.

## Fase 1, punto 2 · controlador del reloj

- Control persistente separado de los datos contables, con publicación atómica y sincronización.
- Política aprobada: siete días entre aperturas y tolerancia de dos minutos para ajustes; comparación monotónica durante el uso.
- Confirmación exclusiva de Administrador, registro previo en bitácora y bloqueo ante control ausente con historial, ilegible o no publicable.
- Pruebas de persistencia, permisos, confirmación, ajustes y fallos; sin cambio de esquema ni importes existentes.

### Integración del bloqueo

- Protección en servidor y motor: inicio, consultas, cobros, generación y documentos. Revisión final antes de confirmar modificaciones; un salto durante un cobro revierte la transacción.
- Pantalla de revisión en horario de Venezuela; solo Administrador confirma con CSRF. La impresión comprueba el reloj y la pantalla elimina documentos pendientes al bloquear.
- Limitación de acceso con tiempo monotónico; confirmar el reloj no prolonga sesiones y limita vencimientos excesivos causados por fechas futuras.
- Prueba explícita del 29 de febrero y conservación de importes/deduplicación.

### Conservación de respaldos

- Orden de publicación persistido en cada destino, independiente de nombres y reloj corregido; mantiene límites de 30 diarias y 90 automáticas.
- Copias previas a operaciones destructivas no se incluyen en la depuración automática.
- Un registro de orden ilegible no autoriza borrar copias. Fallar al registrar conservación no impide copiar una instantánea ya verificada al segundo destino; se muestra aviso.
- Pruebas con fechas futuras de nombres y archivos, posterior corrección, límites independientes, registros corruptos y fallos de sincronización dirigidos a la copia del USB.

## Sin publicar · Fase 1, punto 1 · 11 de octubre de 2026

- Aviso persistente para Administrador y Caja cuando falta el segundo destino, no hay copia externa confirmada, la copia externa tiene más de tres días o el último respaldo falló. Visible también antes de confirmar la tasa; permanece al buscar y filtrar, sin botón de cierre.
- Estado de respaldos calculado con la hora del servidor; cambiar la carpeta externa invalida la confirmación del destino anterior. Los errores al guardar el estado permanecen visibles hasta completar una copia nueva.
- Revisión de ACL y BitLocker en segundo plano, de solo lectura, sin elevación. Si Windows no permite la consulta, el resultado es «No se pudo comprobar».
- Guías y pruebas de estados, límites de antigüedad, permisos por perfil, actualización del aviso y diagnóstico de Windows.
- Sin migración de esquema ni cambios en datos existentes, carpeta de datos, transacciones de cobros, respaldos de cinco minutos, móvil/PWA o módulo de nómina.
- Validación: Linux, 158 descubiertas (157 correctas y una omitida); Windows, 158 correctas. Navegadores normal, Pruebas e importación correctos. Instalador 1.0.26 en borrador, con validación nativa y conservación de datos.
- Pendiente: comprobación de BitLocker/ACL en la PC del colegio y revisión de las alertas de Defender anteriores. Los análisis del runner no certifican esa PC.

## Seguimiento del punto 1

- Aclarado en pantalla: copia escrita en la carpeta, no subida a la nube.
- Aviso propio por mismo disco, y estado desconocido cuando no puede verificarse.
- Ayuda para comprobar BitLocker/ACL desde Windows con los permisos adecuados, sin elevar Aula.
- Prueba adicional: Pruebas no muestra avisos reales. Sin cambios de esquema ni datos existentes.

Validación del seguimiento: 161 descubiertas en Linux (160 correctas, una exclusiva de Windows omitida); navegadores normal, Pruebas e importación correctos. La consulta física de Windows y su revisión en la PC del colegio no se certifican con estas pruebas Linux.

## Validación del punto 2 · instalador 1.0.27 en borrador

- Linux: 186 descubiertas, 185 correctas y una exclusiva de Windows omitida; navegadores normal, Pruebas e importación correctos. Windows: 186 correctas, instalación, ventanas, reinstalación y desinstalación conservando datos.
- Intento 1 detenido al fallar actualización de firmas; no se analizó ni ejecutó el instalador. Un único reintento en runner nuevo pasó ambos análisis de Defender sin detecciones, motor 1.1.26080.3 y firmas 1.459.680.0.
- ZIP de código fuente antiguo retirado del borrador y actualización del ZIP del repositorio con verificación de módulos del reloj. El ejecutable validado no cambia.
- No se comenzó el cifrado del punto 3. Sin migración SQLite, cambio de ubicación ni modificación de datos contables anteriores.
