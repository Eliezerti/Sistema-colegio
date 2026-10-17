# Facturas sobre formulario preimpreso · diseño de Fase 4

Diseño de trabajo, no una función entregada. No modifica los recibos de mensualidades. El punto verde de Fases 1–3 se conserva antes de integrar este bloque. Sin conexión al SENIAT ni cálculo de IVA/IGTF. Medidas reales, medio fiscal y calibración física: **NO VERIFICADOS**.

## Persistencia y permisos

- Esquema 16 aditivo: configuración de emisión, lotes, plantillas, versiones de plantilla, perfiles de impresora, facturas y eventos de impresión. Ninguna fila inicial; el ejemplo se ofrece desde el editor y solo se guarda por acción administrativa.
- Transición 15→16 con copia previa verificada del esquema 15 y la misma protección de cifrado. Prueba desde el fixture publicado 1.0.71 atravesando todas las migraciones; cinco terminaciones reales, integridad, claves foráneas y cadena. Reversión en otra carpeta con copia previa y código del punto verde; conservar la carpeta actual completa.
- Administración configura emisor, lotes, plantillas y perfiles; anula facturas con motivo. Caja y Administración preparan borradores, emiten y registran impresión. Consulta recibe informes, sin configurar ni emitir. Guardia del servidor, CSRF, reloj, A5 y copia de consulta se aplican a todas las rutas nuevas.
- Datos fiscales del representante en la factura, sin nombre, documento ni nacimiento del menor. La bitácora registra identificadores y huellas de las instantáneas, sin copiar datos fiscales. Los respaldos incluyen las nuevas tablas.

## Lotes y emisión

- Datos preimpresos y de imprenta editables por lote; varios lotes y uno activo. Los rangos de factura y control se conservan como texto numérico para mantener ceros iniciales, con claves numéricas canónicas para detectar duplicados.
- Aula propone los siguientes números disponibles como ayuda; nunca reserva ni emite por consultarlos. El operador debe escribirlos o confirmar expresamente los valores propuestos. Validar rangos, unicidad, orden, saltos y agotamiento dentro de una transacción de escritura. Cada salto requiere revisión y motivo; no declarar automáticamente hojas dañadas.
- Estados: Borrador, Emitida, Anulada y Hoja dañada o inutilizada. Toda hoja usada o dañada conserva factura/control y motivo; los números no se reutilizan al anular. El registro debe explicar los saltos y hojas inutilizadas.
- Una factura emitida conserva instantánea de datos, versión de plantilla, perfil aplicado y PDF exacto. No se editan sus importes, cliente ni números. Una corrección requiere anulación administrativa y nueva emisión. Reimpresión del PDF conservado, registrada con usuario y motivo; no volver a renderizar con una plantilla nueva.
- Emisión desde un cobro válido, con total original conservado y conceptos editables. Por defecto, «Mensualidad {mes} {año} – {grado}», sin nombre del menor. Las líneas deben sumar el importe original y corresponder al cobro; no recalcular pagos ni aplicaciones. Exento, base/IVA/IGTF en cero; las opciones fiscales son informativas.
- Antes de emitir, exigir lote activo, configuración revisada, confirmación de los números y plantilla marcada por Administración como calibrada. Advertencia de configuración: «Confirma con tu contador que este medio de emisión es válido para el colegio». No presentar ese marcado como validación física realizada por desarrollo.
- Mes cerrado: no preparar, emitir, editar ni anular facturas del período; reapertura administrativa motivada. La impresión de una factura ya emitida no modifica el cobro ni el cierre. Un cobro con factura vigente no se anula sin revisar primero la factura.

## Plantillas y PDF

- Ejemplo inicial editable «Ejemplo media carta», **SIN CALIBRAR**; sin números, empresa ni personas precargadas. Media carta vertical: 139,7 × 215,9 mm, PDF 396 × 612 pt. También horizontal, carta y tamaño personalizado.
- Para formulario en la mitad superior/inferior de carta, conservar tamaño real. Si se usa el formulario vertical de media carta, hace falta girarlo para que quepa en una mitad; mostrar esa orientación y comprobar sus coordenadas. Nunca encoger ni cortar silenciosamente para hacerlo caber.
- Editor con reglas y cuadrícula en mm, imán configurable, arrastre, flechas de 0,1 mm y Mayús de 1 mm. Edición numérica de X/Y/ancho/alto; fuente, tamaño, negrita/cursiva, alineación, mayúsculas, interlineado, longitud y respuesta al texto largo por campo. Rechazar variables desconocidas al guardar.
- Campos del sistema y campos propios de texto fijo o con variables. Zona de detalles con Y inicial, alto y máximo de líneas, columnas y anchos. Si no cabe texto o hay demasiadas líneas, detener la impresión con explicación; nunca producir una factura cortada.
- Fondo escaneado validado y acotado para pantalla/calibración; no incorporarlo al PDF de emisión real, aunque el cliente envíe una opción forjada. Impresión de prueba con datos ficticios, sin factura ni consumo de números; fondo opcional solo en esa prueba.
- Perfiles de impresora: desplazamientos X/Y en décimas de mm, escala fina y margen. Tamaño PDF elegido exacto, una página, escala predeterminada 1. Margen inicial 5 mm; comprobar que el contenido completo transformado queda dentro del área imprimible. El margen físico real requiere prueba con la impresora del colegio.
- Versiones de plantilla inmutables y restauración creando una versión nueva. Importar/exportar JSON con validación del mismo esquema y límites; no ejecutar HTML, JavaScript, rutas o fuentes suministradas por el archivo.
- Conservar PDF exacto como texto base64 con huella, para que restauración e inspección existentes sigan manejando JSON. Usar fuentes PDF estándar con WinAnsi para ñ/tildes y métricas conocidas, manteniendo el archivo pequeño; no guardar una copia completa de fuentes grandes por factura.

## Informes e integración

- Relación de ventas CSV con BOM/PDF: fecha, factura/control, cliente y documento fiscal del representante, concepto, exento/base/IVA/IGTF, total original y moneda, estado, recibo, usuario y versión de plantilla. Sin datos personales del menor.
- Relación de ingresos mensual: factura asociada y estados, sin duplicar el ingreso. El cierre incluye los pendientes de facturación; la foto del informe cerrado queda conservada.
- Matriz de permisos, catálogo de rutas, mantenimiento/Verificar datos, comparación de restauración, modo consulta, limpieza excepcional y prueba de instalación vacía deben incluir las tablas nuevas.

## Puerta de validación

Numeración y concurrencia de dos cajeros; rangos/duplicados/orden/saltos/agotamiento; hoja dañada y anulación; inmutabilidad y reimpresión idéntica tras editar plantilla/perfil; importación/exportación/versiones; campos y variables; texto largo y detalle desbordado; dimensiones y coordenadas PDF independientes, perfiles, carta arriba/abajo, ñ/tildes, fondo ausente en emisión y prueba sin consumo. Permisos reales por HTTP y cierres en servidor; restauración portable, consulta y referencia de totales. Cuatro suites completas. Tras dos arreglos fallidos de una prueba, retirar la fase al punto verde previo, dejando el informe y el estado actualizados.

Pruebas físicas pendientes por definición: fotocopias del formulario y calibración con la impresora real, extracto bancario real privado y revisión del contador. No se pueden declarar realizadas en CI.
