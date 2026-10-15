# Limpieza del paquete · B2

## Alcance aprobado

Se retiran la instalación PWA, manifiesto, iconos exclusivos de teléfono, aviso sin conexión de la antigua PWA, pasarela phone_demo, sus lanzadores y pruebas exclusivas. Se conserva el diseño adaptable, menú accesible, indicador de conexión y navegador remoto privado; Pago móvil y teléfonos de contacto no cambian. El antiguo trabajador de Aula se desregistra al cargar la nueva interfaz y se eliminan solo sus cachés públicos. No se borran cachés de otras aplicaciones ni datos del colegio.

Se corrigen instrucciones para el instalado y para el ZIP; este último conserva sus lanzadores .bat. Tcl/Tk permanece porque los diálogos de recuperación, contraseña y selector lo utilizan. No hay migración, cambio de datos, cálculos, recibos, ubicaciones ni seguridad.

## Inventario previo

Antes de excluir módulos se instala en un runner desechable el EXE anterior entregado 1.0.49 (en borrador), con su SHA-256 fijado y análisis de Defender, sin abrir datos reales. Se lee el PYZ y se enumeran todos los archivos y tamaños. Nunca se consideran probados módulos de un archivo por inferencia de requirements. El tamaño del instalador anterior descargado es 23.272.158 bytes. La selección concreta de exclusiones y los resultados se documentarán después de leer ese inventario.

## Controles de validación

Se sustituyen pruebas exclusivas de teléfono por controles de rutas retiradas y se conservan las comprobaciones de ventana estrecha, formularios, PDF, cierre de sesión y conexión. Las pruebas financieras y de seguridad existentes permanecen. Las cuatro suites solicitadas y los controles nativos terminaron; los resultados reales de B2 están al final de esta guía.

## Comprobaciones del paquete reducido

El ejecutable de prueba usa únicamente bases temporales. Comprueba Tcl/Tk, ttk, calendario con America/Caracas, traducción española y la apertura/cancelación del selector nativo. En la ventana WebView2 genera un PDF administrativo con las fuentes incluidas, imprime el área de documento a otro PDF mediante PrintToPdfAsync y abre/cancela el selector Windows. La impresión física en una impresora del colegio queda para prueba manual; no se confunde con la impresión PDF del motor.

Se añaden los rechazos de los argumentos de teléfono antes de acceder a la carpeta de datos. Se retiraron tres métodos exclusivos de la pasarela eliminada; el control de recursos públicos se sustituye por comprobación de rutas retiradas. No se elimina ninguna prueba financiera o de seguridad vigente.

## Resultados Linux ejecutados

`python -m unittest discover -s tests -v`: 296 pruebas en 172.376 s; 293 correctas y tres exclusivas de Windows omitidas (DPAPI, mutex y ventana de restauración). Los tres comandos `python tests/run_browser.py`, `python tests/run_browser.py --demo` y `python tests/run_browser.py --roster` terminaron correctamente. También pasó `python tests/run_browser.py --responsive`: menú estrecho, formularios, PDF de cobro, las doce secciones, cierre de sesión, indicador sin conexión y eliminación solo de la caché antigua de Aula. El ZIP temporal se comprobó íntegro y sin los recursos retirados. No se presentan estos resultados como prueba de las futuras exclusiones Windows.

## Selección basada en el inventario real

El inventario de 1.0.49 confirmó 733 módulos PYZ, 1.113 archivos y 58.445.044 bytes instalados: 23 módulos PyInstaller, 145 setuptools, uno pefile y cuatro altgraph. También contiene los seis motores webview Android, CEF, Cocoa, GTK, MSHTML y Qt, que no usa el inicio forzado edgechromium. Se excluyen esas familias: 181 módulos presentes en el inventario anterior. El nuevo spec desactiva UPX explícitamente y verifica el PYZ final antes de generar el instalador.

Se seleccionan 128 recursos innecesarios (738.446 bytes): catálogos Tcl/Tk ajenos a inglés/español, tcltest y librerías exclusivas Android/MSHTML. Se conservan el español venezolano es_ve, todos los encodings, tzdata, clock/msgcat, ttk, motor Tcl/Tk y sus componentes de ejecución y WebView2. Se conservan también los tres directorios WebView2Loader: pywebview 5.4 comprueba su existencia al iniciar en x64; quitarlos sin cambiar esa dependencia rompería el arranque. Las exclusiones afectan al paquete, no desinstalan herramientas de la computadora que lo compila.

El intento previo 1.0.50 completó el inventario anterior, 295 pruebas Windows correctas en 430.012 s y comprobaciones de ventanas/instalación. Fallaron ambos canales de actualización de firmas en el análisis posterior; no se publicó instalador ni se afirma aprobada la ejecución completa. No contenía las exclusiones ni las nuevas comprobaciones nativas: se usa como evidencia del inventario, no de la entrega final.

## Actualización de firmas del verificador

Ante los fallos reales de Windows Update/MMPC se agrega el paquete de inteligencia oficial x64 de Microsoft como tercer canal. Antes de ejecutarlo se exige Authenticode válido de Microsoft; se comprueban código de salida, Defender activo, versión sin retroceso y actualización reciente. Se registra la huella del paquete y las versiones. Si no se puede verificar, el pipeline se detiene. El análisis posterior y su bloqueo de publicación se mantienen; no se añaden exclusiones. Los archivos de actualización se eliminan de su temporal propio.

La actualización alternativa se incorpora al verificador del pipeline; no cambia la configuración de Defender de la PC del usuario.

## Actualizar sin dejar recursos anteriores

El instalador retira únicamente los archivos obsoletos de programa identificados en el inventario de 1.0.49 (128 recursos, incluidos los seis archivos exclusivos PWA), con rutas exactas bajo {app}/_internal. No vacía carpetas completas ni usa comodines sobre datos. La base y respaldos en LOCALAPPDATA/AulaColegio quedan fuera de esa lista. Se verifica también la actualización real desde 1.0.49, además de la actualización histórica de B1, leyendo el PYZ y recursos de la instalación actualizada.

## Prueba manual guiada

1. Guarda una copia externa y cierra Aula con Colegio → Salir y cerrar Aula antes de instalar la actualización, usando la misma cuenta Windows.
2. Abre Aula - Pruebas. Comprueba el menú al reducir la ventana, crea fichas ficticias y registra un cobro ficticio. Descarga su PDF y abre Imprimir.
3. Imprime en tu impresora habitual y revisa nombre, grado, importe y legibilidad. No registres pagos reales para probar.
4. Cierra Pruebas y usa Inicio → Aula Colegio → Probar respaldo para comprobar que abre el selector y un archivo de copia con su contraseña/recuperación. Probar respaldo no restaura ni cambia datos.
5. En Aula real revisa nombres, saldos y último recibo. Conserva el respaldo previo. La instalación PWA y prueba Wi-Fi ya no están disponibles; el acceso privado de otras PC sigue disponible.

## Archivos del cambio

colegio/desktop.py, desktop_checks.py y server.py; static/app.js, responsive.js, index.html y style.css; pruebas de recursos, argumentos, navegador adaptable y actualización Windows; packaging/Aula.spec, bundle_rules.py, bundle_inventory.py, inventory_previous.ps1, retired-files.iss, Aula.iss, build_windows.ps1, scan_windows.ps1 y test_installer.ps1; workflow, .gitignore, README, CHANGELOG, estas guías/inventarios y ZIP/suma. Se retiraron phone_demo.py, el lanzador de teléfono, recursos PWA, guía/paquetes móviles y las pruebas exclusivas de la pasarela. No hay migración de esquema.

Se retiran también las copias .py de las seis plataformas excluidas y el proveedor de hooks de construcción de pywebview, presentes en el inventario original. Se conservan las fuentes Windows que utiliza el programa.

Para comparar tamaño instalado se usa el mismo conjunto en ambas versiones: Aula.exe y todos los archivos de _internal. Los documentos y el desinstalador se muestran aparte y no se mezclan con el tamaño del runtime. Referencia 1.0.49: 53.658.392 bytes de runtime; 58.445.044 bytes con documentación y desinstalador. El instalador descargado mide 23.272.158 bytes. La entrega final 1.0.53 mide 21.236.040 bytes de instalador y 51.210.228 bytes de runtime comparable.

## Resultado final 1.0.53

Ejecución [38454601433](https://github.com/Eliezerti/Sistema-colegio/actions/runs/38454601433), fuente 1938dfb. Windows: **296 pruebas correctas sin omisiones en 442.306 s**. Pasaron arranque y ventanas normal/Pruebas, bandeja, Tcl/Tk, ttk, calendario, traducción española y ambos selectores abiertos/cancelados; PDF administrativo y la impresión PDF del motor real WebView2. Instalación sin datos, actualización desde 1.0.13 y desde el instalador anterior entregado 1.0.49, segunda cuenta estándar real y desinstalaciones conservando base/respaldo correctas. Filas, recibo y saldo USD 50 ficticios conservados. El PYZ y los archivos de la instalación actualizada también pasan el control de exclusiones.

| Medida comparable | 1.0.49 | 1.0.53 | Reducción |
| --- | ---: | ---: | ---: |
| Instalador, bytes | 23.272.158 | 21.236.040 | 8,75% |
| Aula.exe + _internal, bytes | 53.658.392 | 51.210.228 | 4,56% |
| Módulos PYZ | 733 | 492 | 241 módulos |

Las 181 exclusiones directas también evitan otras dependencias transitivas; por eso el total baja 241 módulos. El runtime de la instalación actualizada mide 51.228.491 bytes: quedan 18.263 bytes de recursos anteriores compatibles, sin ninguna familia/recurso prohibido. No se borran archivos desconocidos para perseguir una diferencia de tamaño. Documentación/desinstalador se contabilizan aparte.

[Instalador final en borrador](https://github.com/Eliezerti/Sistema-colegio/releases/tag/untagged-a7c54162b1e7e546f55f), SHA-256 descargado `7bdf71a73abc03e72bb13d53d1dcf9fc999630e947d0806fbfbdd8b8466afb85`; coincide con el sidecar y ambos análisis. Defender antes/después sin detecciones, motor 1.1.26080.3, firmas 1.459.691.0. ZIP descargado íntegro: 165 archivos, fuente de ejecución igual tras normalizar finales de línea Windows. El ZIP del repositorio se reconstruye después con esta guía final; no cambia el código probado.

Inventarios completos: [antes](https://github.com/Eliezerti/Sistema-colegio/blob/main/docs/inventario-b2-antes.json), [exclusiones](https://github.com/Eliezerti/Sistema-colegio/blob/main/docs/inventario-b2-exclusiones.json), [después](https://github.com/Eliezerti/Sistema-colegio/blob/main/docs/inventario-b2-despues.json) y [actualizado](https://github.com/Eliezerti/Sistema-colegio/blob/main/docs/inventario-b2-actualizado.json). Los inventarios se reconstruyen de las líneas JSON completas del registro real del runner, sin inventar fechas o huellas no emitidas. Los artefactos adicionales fueron subidos por el pipeline; no se afirma haber descargado sus JSON.

Incidencias: 1.0.51 se canceló para incorporar retiro de archivos obsoletos al actualizar; no se presenta como pasada. 1.0.52 pasó 296 pruebas en 454.338 s, ventanas/selectores/impresión y actualizaciones, pero aún conservaba copias fuente de plataformas en los datos; se corrigió el filtro y se repitió todo en 1.0.53. El tercer canal oficial de firmas se ejercitó correctamente en 1.0.52, con versión final 1.459.691.0; 1.0.53 completó sus análisis con las fuentes habituales. En el navegador adaptable se corrigió una espera de evento tras cambiar el ancho: el fallo inicial se producía al comprobar inert antes de terminar el evento; la prueba final conserva la aserción y espera la transición. No se relajan comprobaciones.

Límites: runner Windows Server 2022 con herramientas de desarrollo, nuevo para Aula. No se ejecutaron impresión física, hardware/BitLocker, Windows 10/11 de tu PC ni instalación sin internet. Esos controles se realizan con los pasos manuales anteriores. B2 queda terminado; firma propia de Aula, documentación operativa de B4 y los informes C esperan sus tandas. No se implementa B3.
