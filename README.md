# Aula · Control de mensualidades

Aula administra alumnos, representantes, grados, mensualidades, cobros y los egresos mínimos del colegio en una PC Windows. Conserva tasas BCV, descuentos, convenios, pase de año, cierre de caja, reportes, importación y exportación de alumnos y Archivo de la institución.

Personal y Nómina se retiraron por completo. El esquema 12 elimina sus cuatro tablas y el vínculo de empleado de los egresos. Los egresos históricos de categoría Nómina se conservan como gastos normales, con los mismos importes, moneda, tasa, método, referencia, fechas y números. Las rutas retiradas responden 410 con un mensaje claro. Vaciar registros ya no está disponible en producción.

Una instalación nueva comienza con identidad «Mi colegio», sin alumnos, representantes, grados, cargos, pagos, egresos, tasas, convenios ni usuarios. El asistente crea el administrador. Pisos de numeración cero y primeros R-/E-/AL- en 1. La plantilla de importación se entrega vacía, sin personas de ejemplo. El modo Pruebas utiliza exclusivamente su carpeta temporal separada.

## Uso y protección

- [Puesta en producción](docs/puesta-en-produccion.md): instalar, configurar, importar y realizar el piloto.
- [Importar alumnos](docs/guia-importacion.md) y [cobros y arqueo](docs/cobros-y-arqueo.md).
- [Comprobantes](docs/comprobante-media-carta.md): media carta vertical y ORIGINAL/COPIA en carta horizontal al 100 %.
- [Archivo de la institución](docs/archivo-institucion.md): alumnos y representantes, con borrado protegido solo de fichas sin movimientos ni vínculos.
- [Restauración segura](docs/restauracion-segura.md), [cifrado de respaldos](docs/cifrado-respaldos.md), [sesiones](docs/sesiones-acceso.md) y [bitácora](docs/bitacora.md).
- [Inventario, dependencias y migración](docs/retiro-personal-inventario.md).

La actualización verifica una copia previa antes de migrar. No reinicia correlativos existentes. Los respaldos antiguos pueden revisarse y restaurarse: la candidata se migra antes de publicarla, con integridad, referencias y cadena comprobadas. No se reescriben recibos de cobro históricos ni huellas antiguas. WAL, synchronous=FULL y protecciones A1–A5 permanecen. El filtrado de secretos sigue protegiendo registros históricos aunque ya no exista Personal.

## Validación de esta entrega

Linux: 292 pruebas en 150,716 s, 289 correctas y tres exclusivas de Windows omitidas. Navegadores normal, --demo y --roster: PASS. Migración, referencias de caja/reportes, cinco cortes reales, restauración/cifrado y cero registros precargados comprobados. Windows: 292 correctas en 486,343 s sin omisiones, instalación en cero, actualización publicada y otra cuenta estándar real correctas. [Instalador 1.0.67 en borrador](https://github.com/Eliezerti/Sistema-colegio/releases), 19.626.196 bytes, SHA-256 descargado y coincidente. Defender antes/después sin detecciones. B3 (firma) y B4 permanecen pendientes.

Comandos: `python -m unittest discover -s tests -v`, `python tests/run_browser.py`, `python tests/run_browser.py --demo` y `python tests/run_browser.py --roster`.
