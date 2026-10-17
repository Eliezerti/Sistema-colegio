# Estado de trabajo nocturno

**Entrega parcial comprobada. Fases 1–4 pendientes de integración.**

- Rama: `autonomo/ingresos-facturas`; origen `ed1c5e9` (1.0.71). Main y versiones publicadas intactas.
- Código final validado: `6f19357e990ce49ed84d0f96f3d5891262cbeafb`. Los commits posteriores solo actualizan documentación.
- Fase 0 completada: inventario, decisiones y diseño en `DECISIONES-AUTONOMAS.md` y `interno/ingresos-diseno.md`.
- Núcleo aislado: cuentas, sugerencias, depósitos, CSV/XLSX y candidatos/asignaciones de conciliación; 17 pruebas propias. Sin rutas, interfaz, persistencia ni nuevas tablas. No se importa desde la aplicación.
- Arreglo real adicional: rechazo HTTP 403 en copias de consulta; descarta el cuerpo con memoria/plazo acotados, sin analizar JSON ni abrir SQLite. Protecciones y archivo fuente intactos.
- Ninguna base del usuario fue abierta o modificada. Esquema 12; recibos, cálculos y correlativos conservados. No se generó instalador ni se trabajó en firma digital.

## Validación final real

| Suite | Linux | Windows Server 2022 |
|---|---|---|
| unittest completo | 325 en 188,147 s; 322 correctas y 3 nativas omitidas | 325 correctas en 438,560 s; sin omisiones |
| Navegador normal | Salida 0 | Salida 0 |
| Navegador --demo | Salida 0 | Salida 0 |
| Navegador --roster | Salida 0 | Salida 0 |

Windows: https://github.com/Eliezerti/Sistema-colegio/actions/runs/38997949165
Registros: https://github.com/Eliezerti/Sistema-colegio/actions/runs/38997949165/artifacts/12087338899
Logs Linux y desarrollo: `/workspace/work/noche/`.

## Fallos conservados

- Primera línea base restringida: 118 errores de sockets y 3 omisiones. Repetida con el mecanismo de permisos autorizado, sin alterar pruebas; prueba administrativa correcta y línea base completa correcta.
- Windows `38996806129`: 324 en 482,260 s, 1 error WinError 10053 al esperar 403 en import-roster de una copia. Tres navegadores correctos. Corregido en el primer intento (`6f19357`); prueba dirigida de cuatro casos correcta y luego cuatro suites completas correctas en ambos sistemas.
- `38996676220`: ejecución obsoleta cancelada por cambio de código; no cuenta como validación.

## Reanudación

1. Leer `INFORME-MAÑANA.md` y decisiones; no asumir fases entregadas por tener pruebas de reglas puras.
2. Implementar Fase 1: protocolo de respaldo cifrado previo reversible, fixture publicado 1.0.71, migración aditiva y terminación real del proceso; verificar integridad, referencias, cadena y totales exactos.
3. Integrar catálogo, cuenta en cobros, revisión/asignación histórica, depósitos, otros ingresos y cuentas en egresos; permisos HTTP y bitácora. Cuatro suites antes de declarar la fase completa.
4. Continuar conciliación persistida y cierre mensual, después facturas/editor. Se mantiene la autonomía autorizada; no hay una aprobación pendiente.

NO VERIFICADO: perfil real Provincial, formulario/calibración física y confirmación fiscal. No se hicieron instalación/actualización/desinstalación de esta rama ni impresión física: no existe instalador nuevo ni módulo de facturas integrado.
