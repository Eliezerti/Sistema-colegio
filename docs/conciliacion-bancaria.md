# Conciliación bancaria · rama de revisión

Solo Administración importa extractos, configura perfiles, clasifica depósitos y guarda o retira vínculos. Caja y Consulta reciben únicamente resúmenes; no reciben el extracto. Aula no se conecta a bancos ni al SENIAT. Trabaja primero en modo Pruebas con archivos ficticios.

## Importar y revisar

1. Configura las cuentas del colegio y revisa las cuentas de cobros anteriores. Un cobro sin cuenta no se concilia automáticamente. Efectivo se vincula primero a una planilla; el banco cruza esa planilla, sin duplicar el recibo ni el ingreso.
2. En **Control de ingresos**, crea un perfil con los encabezados exactos del archivo: fecha, importe con signo, referencia, descripción e ID bancario si existe. El separador, la codificación, la fecha y el decimal son editables. La plantilla **BBVA Provincial · NO VERIFICADO** es un ejemplo genérico, no un formato oficial. Debe comprobarse con un extracto real privado.
3. Selecciona la cuenta y un CSV o Excel `.xlsx` de hasta 2 MB y 10.000 movimientos. CSV sin separadores de miles; crédito positivo y débito negativo. Excel usa la primera hoja; referencias e ID deben ser texto. No se aceptan fórmulas, macros ni vínculos externos.
4. Revisa la vista previa. Guarda la huella del archivo, quién importó y cuándo. No se guarda el archivo original en la bitácora. Conserva el original confidencial por separado. Repetir exactamente el mismo archivo no duplica movimientos.
5. Un ID bancario ya importado se omite solo si su contenido coincide. Si cambia, la importación se detiene para revisión. Sin ID, una coincidencia de contenido se señala: no se importa sin confirmar las filas distintas y explicar el motivo. No confirmes un solapamiento por comodidad.

Los movimientos importados no se editan ni se borran. Cada importación conserva el perfil usado. Editar un perfil no cambia las importaciones anteriores. La bitácora guarda identificadores y huellas, sin copiar descripciones o referencias confidenciales del extracto. Los respaldos habituales incluyen el libro; los externos nuevos siguen cifrados.

## Conciliar

«Cruzar candidatos únicos» exige cuenta, moneda, centavos y referencia compatibles y fecha a ±3 días; la unicidad se comprueba en ambos lados. Las referencias numéricas se comparan sin ceros iniciales, conservando el original. Una referencia vacía no se cruza automáticamente. Los ambiguos quedan como propuestas.

Para agrupaciones, registra vínculos revisados con Banco ID, Libro ID e importe original parcial. **P** es recibo, **E** egreso, **O** otro ingreso y **D** planilla. Permite varios recibos por depósito y varias partes bancarias por recibo, sin exceder el importe en ningún lado. No mezcla monedas ni cuentas: USD y Bs se revisan en sus cuentas originales; las tasas históricas del libro no se sustituyen por la de hoy. Una conversión entre cuentas o monedas requiere registrar su soporte y revisar la operación; no se inventa una tasa ni un vínculo automático.

Las listas muestran banco sin recibo/egreso, libro sin depósito, diferencias de importe y pendientes con antigüedad editable. Los depósitos no explicados se clasifican con soporte: mensualidad no registrada, otro ingreso, entre cuentas propias, préstamo/aporte, reintegro u otro. **Clasificar no crea un cobro ni reduce una deuda**. Si falta registrar la mensualidad, haz el registro correcto y luego retira la clasificación con motivo antes de vincularlo.

Un registro conciliado no se anula ni se reasigna de cuenta sin retirar primero su vínculo con motivo. Retirar mantiene el historial. Los días de caja cerrada requieren reapertura administrativa antes de cambiar el libro. El cierre mensual protegido se gestiona en la relación para el contador, al final de Control de ingresos. También requiere reapertura antes de modificar el libro de un mes cerrado.

## Límites y reversión

Los candidatos de una revisión mensual admiten hasta 20.000 registros por lado. El historial del libro tiene un límite de seguridad de 200.000 registros; no se declara validado a esa escala. Se midieron 800 alumnos con 12 y 36 meses en Linux. Las pantallas muestran hasta 100 filas por listado y páginas. El próximo informe para contador debe separar diferencias contra el extracto de ingresos y traslados.

La ampliación usa esquema 14 aditivo, con copia previa verificada del esquema 13 en `.aula-migrations/schema-14/`. Si el cifrado está configurado, exige que esté desbloqueado y publica copia cifrada verificada; sin configuración queda copia privada SQLite. Conserva la carpeta actual y sus registros nuevos. Para revertir solo esta fase usa la copia 13 y el código de Fase 1 en otra carpeta vacía. Para volver a 1.0.71 usa la copia 12 de `schema-13/`. No sobrescribas la carpeta original ni abras una base nueva con una versión antigua.

**NO VERIFICADO:** un extracto real de Provincial, conversiones reales entre cuentas y revisión con el contador. Ninguna prueba utiliza datos bancarios reales.
