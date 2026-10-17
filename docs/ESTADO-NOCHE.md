# Estado de trabajo · ingresos y facturas

## Punto actual · 17/10/2026

Rama `autonomo/ingresos-facturas`; último código enviado `ee7a4881dec3aed662cf8aafc7b87dbe951ad75f`. `f9997f1` añade solamente seguimiento y evidencia. Main intacta; sin merge, etiquetas, release ni versión final. Solo bases ficticias y temporales; ninguna base del usuario abierta o modificada.

Fases 1–4 implementadas. Fases 1–3 tienen cuatro suites verdes en Linux y Windows. Fase 4 tiene las cuatro suites Linux verdes; **Windows e instalador BORRADOR en curso, no entregados todavía**.

## Resultados reales actuales

- Linux Fase 4: **379 en 408,506 s; 376 correctas y tres exclusivas de Windows omitidas; salida 0**. Normal, demo y roster: **salida 0**. Registros y códigos `/workspace/work/noche4/final-*.log` y `.exit`; evidencia conservada en `docs/interno/ingresos-evidencia/linux-facturas-cuatro-suites.json`.
- PDF independiente pypdf/PyMuPDF: **dos correctas en 0,100 s**. Entrada BORRADOR: **dos correctas en 0,005 s**. Media carta 396×612, una página, coordenadas y fuentes, ñ/tildes/cursiva, perfiles y carta superior/inferior. No equivale a impresión física.
- Windows nuevo: [39042799764](https://github.com/Eliezerti/Sistema-colegio/actions/runs/39042799764), job `117425504627`, código `ee7a488`. Dependencias correctas; cuatro suites en ejecución al guardar. No cancelar pruebas en marcha. Observador local `/workspace/work/noche4/windows-watch.log` y `.exit`, sesión de herramienta `44312` si sigue disponible.
- Windows anterior, SOLO núcleo: **355 en 666,551 s, sin omisiones; normal/demo/roster salida 0**, run 39028897879, código `a772d25`. No reutilizarlo como aprobación de facturas.
- Rendimiento Linux 800/12 con 9.600 cobros, movimientos y PDF de facturas: principal **7.993 bytes / mediana 0,331963 s / máximo 0,448516 s**; relación mensual 425.987 / 0,177546; registro facturas 49.222 / 0,119056.
- Linux 800/36 con 28.800 facturas/PDF: principal **8.000 bytes / 0,483898 / 0,485014**; conciliación 87.086 / 0,879629; relación 426.572 / 0,404841; facturas 49.284 / 0,241264. Ambos comandos terminaron con salida 0; CSV conservados en evidencia. Windows 36 meses de facturas no ejecutado; CI mide 12.

## Cambios y puntos de retorno

- Núcleo completo verde: `a772d25`; documentación de cierre `1526124`.
- Fase 4: `35ffaf1` plantillas/PDF; `58a4cc3` esquema 16; `6ca60e3` API/emisión; `f1c4bb0` prefijos y perfil inválido; `ea7301e` editor/sesiones/navegador; `cd367dc` compilación aislada; `ee7a488` guías/evidencia.
- Esquemas 13–16 aditivos: cuentas/ingresos, extractos/conciliación, cierres y siete tablas de facturas. Copia previa verificada; fixture publicado 1.0.71; cinco terminaciones reales por transición; integridad, claves foráneas y cadena comprobadas. Instalación lógica vacía.
- Los recibos actuales, cálculos y correlativos se conservan. Emisión preimpresa exige configuración revisada, versión calibrada y números escritos o confirmados. PDF emitido inmutable, reimpresión idéntica y auditada. Restauración conserva los números conocidos en una entrada auditada, bloquea reutilización y exige revisión administrativa.
- Primer pase completo de Fase 4: 379 en 343,004 s, un fallo por perfil vacío. Primer arreglo: rechazo en servidor; matriz dirigida y repetición completa verdes. Otros errores iniciales y correcciones están en INFORME-MAÑANA.md; no se alteraron fixtures publicados ni se omitieron pruebas. Si una prueba sigue fallando tras dos arreglos, retirar esa fase mediante commits normales al punto verde, sin borrar datos ni reescribir historia.

## Siguiente trabajo concreto

1. Dejar terminar Windows 39042799764. Consultar estado y anotaciones por la API autorizada. Registrar cuenta, tiempo y cuatro salidas reales; conservar cualquier traceback si falla.
2. Si pasa: CI compila **1.0.72-borrador.<número del run>**, analiza con Defender y prueba instalación separada, ventanas nativas, consulta, PDF del comprobante, reinstalación y desinstalación sin alterar fixtures. El artefacto solo se conserva después de estos pasos. No crear releases ni etiquetas.
3. Obtener enlace/huella del BORRADOR únicamente si termina correctamente; comprobar el archivo descargado si la política de red permite obtenerlo. No sortear hosts prohibidos.
4. Actualizar INFORME-MAÑANA.md, README, CHANGELOG y este estado con resultados finales. Enviar solo commits pequeños de la rama; finalizar con resumen de máximo 25 líneas y pendientes explícitos.

## Instalador y separación

Aún no hay EXE validado para entregar. Instalador BORRADOR con AppId/programa/accesos propios; el punto de entrada cambia LOCALAPPDATA del proceso a una subcarpeta, seleccionando `%LOCALAPPDATA%\AulaRevisionIngresos\AulaColegio` incluso al abrir directamente Aula.exe. No actualiza el producto publicado ni habilita inicio automático. Cerrar Aula publicado antes de abrir el borrador: comparten mutex/puertos. Desinstalar conserva los datos. La entrada se probó; la instalación nativa nueva todavía no.

El ZIP fuente scratch fue comprobado: archivos únicos, sin claves/respaldos, bases solamente como fixtures ficticios bajo tests/fixtures con manifiestos/huellas intactos. No es un instalador. `/codex/.../output` no existe y el sistema operativo rechazó crear /codex; entregar enlaces al repositorio/artefactos si esa ruta no está disponible.

## Límites y pendientes que no deben ocultarse

- Cruces entre cuentas o monedas, depósitos de efectivo convertidos y traslado de efectivo procedente de otros ingresos no habilitados. Soporte textual, sin archivos adjuntos. No inventar tasas ni recibos.
- Actualización nativa desde la versión publicada y otra cuenta Windows de este BORRADOR no ejecutadas. Instalar el borrador separado no equivale a actualizar el producto.
- **NO VERIFICADO:** extracto real Provincial, formulario real, impresión/calibración física y confirmación fiscal. Ejemplo editable SIN CALIBRAR. IVA/IGTF no calculados ni activables en este borrador; etiquetas editables. Sin banco ni SENIAT conectados.
- Pruebas manuales: fotocopias e impresora real, extracto confidencial fuera del repositorio, contador, restauración en otra PC y corte físico de luz durante piloto supervisado. No se declaran realizadas.
- No tocar Personal/Nómina, firma digital, otras tandas ni datos del usuario.

## Bloqueos observados

La revisión automática alcanzó su límite de uso y una consulta GitHub no se ejecutó. Tras la nueva indicación del usuario se reintentó el mismo mecanismo autorizado y volvió a funcionar; no se eludió la revisión. Un host de artefactos anterior estaba prohibido; se conservó evidencia mediante anotaciones GitHub permitidas. Los logs no recuperados no se declaran correctos.
