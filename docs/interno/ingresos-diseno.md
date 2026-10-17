# Ingresos y facturas · diseño para revisión

**Estado: núcleo de Fases 1–3 integrado, esquema 15. Fases 1/2 validadas en Linux y Windows; Fase 3 con cuatro suites Linux correctas y validación Windows final pendiente. Facturas y conversión entre cuentas/monedas pendientes.**
El inventario inicial corresponde a `ed1c5e9`; la evidencia posterior y los puntos verdes constan en `../ESTADO-NOCHE.md`. No se modifica ninguna base del colegio.

## Modelo propuesto

| Tabla nueva | Datos mínimos y relaciones |
|---|---|
| school_accounts | id, nombre, banco, USD/VES, tipo banco/caja, últimos cuatro dígitos, activa |
| payment_accounts | payment_id único → payments; account_id → school_accounts; asignación explícita auditada |
| expense_accounts | expense_id único → expenses; account_id → school_accounts |
| income_categories | id, nombre único, activa; sin categorías precargadas |
| other_income | id, concepto, categoría, fecha, importe original, moneda, tasa verificada, equivalente USD, cuenta, método, referencia, soporte, usuario, clave idempotente, anulación |
| cash_deposits | id, fecha, importe original, moneda, cuenta bancaria, planilla, soporte, motivo de diferencia, usuario, clave idempotente |
| cash_deposit_payments | depósito → cash_deposits, recibo → payments, importe original parcial; clave compuesta |
| statement_imports | id, huella del archivo, cuenta, período, perfil/version, usuario, fecha; sin conservar el archivo original dentro de la bitácora |
| bank_movements | id, importación, cuenta, fecha, crédito/débito, moneda, importe, referencia original, descripción, ID bancario y huella canónica |
| reconciliation_links | movimiento y tipo de fuente/ID, importes originales en ambos lados, tasa y fecha de conversión explícitas cuando difieran monedas, usuario, motivo |
| bank_classifications | movimiento, categoría de explicación, soporte, motivo, usuario; historia de correcciones |
| accounting_closures | id, período con un solo cierre activo, resumen congelado y huella, responsable/fecha; reaperturas con motivo e historia |
| income_annotations | recibo u otro ingreso, sujeto especial y divisas; solo informativo |

No añadir una cuenta inferida al recibo congelado. Las asociaciones nuevas pertenecen al libro de clasificación y no alteran payments, allocations ni receipt_snapshot.
Las referencias tienen dos representaciones: original para revisión; normalizada para candidatos. Un hash de movimiento es indicio de repetición, no garantía de identidad si el banco no suministra un ID único.

## Reglas puras y conexión al servidor

`colegio/income_rules.py` implementa validación mínima de cuentas y cuenta sugerida, cobertura de depósitos en efectivo, candidatos únicos por ambos lados, asignaciones parciales explícitas, equivalentes con tasa histórica y vista previa CSV/XLSX con mapeo.

- CSV: UTF-8 o Windows-1252 elegidos explícitamente; separador y decimal configurados; no adivina miles ni formatos. Fecha ISO o día/mes/año. Créditos positivos y débitos negativos.
- Excel: primera hoja; referencias e ID bancarios como texto, para no inventar ceros perdidos. Acepta fechas de Excel en calendarios 1900/1904; rechaza el 29/02/1900 inexistente, fórmulas, macros, vínculos externos, XML con entidades y archivos expandidos excesivos.
- El perfil no verificado de Provincial debe arrancar sin mapeos supuestamente oficiales. La pantalla futura permitirá guardar el mapeo revisado. No existe un perfil oficial verificado ni se usó un extracto real.
- Candidatos: misma cuenta, moneda, sentido, centavos y referencia; ±3 días. La unicidad se comprueba en ambos lados. Los grupos ambiguos muestran hasta 50 candidatos y su cantidad real; nunca se convierten en automáticos.
- Cobertura de varios recibos o depósitos: validación de asignaciones parciales, suma disponible y duplicados. La persistencia deberá resolver concurrencia dentro de BEGIN IMMEDIATE.
- Conversión USD/VES: nunca se concilian monedas distintas automáticamente. La tasa `1` de un cobro directo USD **no es una tasa BCV**. El informe ampliado necesita la tasa BCV histórica de ese día; si falta, debe mostrar NO VERIFICADO y equivalencia desconocida, nunca inventarla.

Las pruebas puras por sí solas no acreditan integración. La Fase 1 incorpora sus pruebas HTTP, interfaz, permisos, concurrencia de depósitos y conservación de totales; la conciliación persistente y el cierre mensual ya tienen interfaz y pruebas de integración.

## Migración y recuperación: requisito antes de integrar

1. Fixture publicado, verificando su manifest y huella; añadir fixture de la versión publicada 1.0.71, con identidad ficticia y procedencia documentada. No fabricarlo cambiando solo user_version.
2. Bloqueo de carpeta y del escritor; verificar reloj, integridad, referencias y cadena. Generar y verificar respaldo previo reversible. Evitar que la conversión automática de respaldos entre recursivamente en la misma migración; la copia previa debe conservar su esquema y poder restaurarse con la versión anterior.
3. Solo DDL aditivo, en una transacción. Crear tablas y claves foráneas; instalar todos los disparadores de audit_chain para las tablas nuevas; fijar la versión al final. Históricos sin asociación y nuevas tablas vacías.
4. Comparación exacta antes/después: filas de payments, allocations, expenses y charges, fotos de recibos, cash_summary, snapshot.summary, informe diario, informe mensual, morosidad y prefijo de la cadena. No modificar pisos existentes.
5. Matar un proceso real antes del respaldo, después de verificarlo, a mitad del DDL, antes y después de COMMIT y durante publicación del control de la bitácora. Solo estado original o nuevo completo; recuperar al reiniciar y comprobar integrity_check y foreign_key_check.
6. Restauración de copia antigua, comparación y pérdida: incluir nombres claros para las tablas nuevas y detectar pérdida de clasificaciones/importaciones. Probar respaldo y modo consulta migran solo su temporal; no escriben en el origen.
7. Revertir con la versión anterior y la copia previa verificada, preservando aparte cualquier dato nuevo. No ofrecer downgrade borrando tablas ni datos. No desplegar el esquema hasta validar todo el protocolo.

**El protocolo se implementó y probó en las transiciones 12→13→14→15**: fixture publicado 1.0.71, copias previas verificadas, contraseña y recuperación, integridad, cadena, comparación y cinco cortes reales por transición. Sin cifrado configurado la copia previa queda privada en SQLite; no se presenta como cifrada. Los resultados de cada plataforma constan en ESTADO-NOCHE.md.

## Cierre mensual y permisos integrados

La protección mensual se ejecuta en el servidor mediante el guardia de fecha del libro; cubre cobros, egresos, otros ingresos, depósitos, asignación histórica e importación/conciliación. El cobro directo también consulta ese guardia. Un reintento ya confirmado no crea otro recibo. El cierre conserva una foto y su huella; la reapertura administrativa mantiene el historial. No se cambió la generación de mensualidades ni el motor de cargos. Las copias de consulta siguen sin generar mensualidades ni escribir.

La relación para contador no contiene datos personales de menores. Factura es una columna vacía y explícitamente pendiente; aún no hay rutas ni emisión de facturas que validar. Se conserva el diseño de ese bloque, sin presentarlo como implementado.

Administración configura cuentas y categorías, importa, clasifica, concilia, asigna históricos, cierra y reabre meses. Caja elige cuenta en un cobro nuevo y registra depósitos; emite facturas solo cuando exista el módulo completo. Consulta ve informes; no recibe extractos crudos ni modifica registros. Las políticas cuentan con la matriz HTTP por perfiles; Consulta y Caja no reciben extractos. El soporte es texto/ubicación, sin adjuntos.

La relación para contador amplía el libro, pero no redefine silenciosamente los totales actuales. Separar mensualidades, otros ingresos, transferencias entre cuentas y depósitos de efectivo; estos últimos no son un segundo ingreso. Exportaciones con BOM y neutralización de fórmulas. Sin documentos ni fechas de nacimiento de menores.

## Facturas: alcance pendiente, sin emisión habilitada

Separar lotes, rangos, hojas, plantillas versionadas, perfiles de impresora y facturas inmutables del recibo actual. Rangos y números escritos o confirmados por operador, reserva transaccional y unicidad de factura/control. Una hoja dañada consume el control con motivo. Reimpresión auditada de la versión congelada. IVA/IGTF apagados; no habilitar cálculos fiscales sin validación del contador.

Plantilla inicial SIN CALIBRAR, fondo solo de pantalla y prueba, margen mínimo 5 mm. Cada campo y variable validados, largo y detalles nunca truncados sin aviso. Media carta vertical 396 × 612 pt; en carta, marco superior/inferior con coordenadas físicas verificadas. La impresión de facturas al 100 % es independiente de la configuración normal de los recibos existentes.

La implementación y las pruebas de lotes, concurrencia de emisión, editor, PDF de facturas, calibración e impresión física están pendientes. No se presenta un PDF genérico como formulario aprobado por SENIAT.

## Riesgos concretos que la integración debe resolver

- `colegio/audit_chain.py:147–174` sanea claves privadas conocidas, pero no conoce la descripción ni el identificador de movimientos bancarios futuros. No registrar extractos crudos en detalles, errores ni exportaciones de bitácora. Los movimientos importados deben ser inmutables; sus acciones registran ID interno, hash, cantidad y motivo, sin copiar el contenido confidencial.
- `colegio/server.py:177` sincroniza mensualidades antes de varias mutaciones. El guardia mensual no puede agregarse al final de la ruta: debe cubrir también cambios indirectos y la generación automática que atraviese un período cerrado. La asignación de cuenta a históricos cerrados requiere reapertura si modifica el libro congelado.
- `colegio/backup_export.py:30–35` migra copias antiguas al convertirlas. No llamar esa conversión sin un contexto separado desde la migración nueva: podría intentar migrar otra vez su propia copia previa. Hace falta un respaldo de reversión verificado que preserve la versión anterior, sin publicar copias nuevas con Personal ni perder el acceso por contraseña/recuperación.
- La conciliación debe reservar importes pendientes en una transacción de escritor; la validación pura recibe disponibilidad anterior, pero por sí sola no impide que dos cajeros consuman el mismo saldo. No anunciar concurrencia probada por estos tests.
- Los archivos con contenido idéntico y sin ID bancario necesitan revisión. Una huella sola no distingue dos depósitos legítimos iguales; tampoco autoriza ignorar movimientos repetidos entre dos extractos solapados.
