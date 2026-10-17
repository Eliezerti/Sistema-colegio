# Estado de trabajo nocturno

**Fase 1 integrada y validada en Linux. Validación Windows en curso. Fases 2–4 pendientes.**

- Rama `autonomo/ingresos-facturas`; código de Fase 1: `ddba0ca9a2707f1fd9b133b4aea732d757fd1c2a`. Main, etiquetas y publicación intactos.
- Commits: `2701023` migración; `1e003a4` servidor y reportes; `11e00dc` pruebas; `ddba0ca` interfaz.
- Fase 0 documentada. Fase 1: catálogo, cuenta destino, asignación histórica, otros ingresos/categorías, depósitos parciales, egresos con cuenta, permisos y bitácora. [Guía](cuentas-ingresos.md).
- Esquema 13 aditivo; copia previa verificada (cifrada cuando está configurado), fixture real del código publicado 1.0.71 con datos ficticios, integridad/cadena y cinco cortes reales comprobados. Ninguna base del usuario abierta o modificada.
- Los recibos originales, importes y correlativos se conservan. Los depósitos no duplican ingresos. Instalación nueva con siete tablas nuevas vacías.

## Resultados reales de esta fase

| Comando | Linux | Windows |
|---|---|---|
| `python -m unittest discover -s tests -v` | 333 en 206,436 s; 330 correctas y 3 nativas omitidas | En ejecución; no aprobado aún |
| `python tests/run_browser.py` | Salida 0, incluye flujo nuevo por interfaz y copia consulta | En ejecución |
| `python tests/run_browser.py --demo` | Salida 0 | En ejecución |
| `python tests/run_browser.py --roster` | Salida 0 | En ejecución |

Windows: https://github.com/Eliezerti/Sistema-colegio/actions/runs/39001990044
Logs Linux: `/workspace/work/noche2/phase1-*-fixed.log`, `phase1-roster-final.log`.

Primera regresión ampliada: 331 en 213,631 s, 15 errores y 3 omisiones. Causas: fixtures sintéticos antiguos con tablas acompañantes nuevas, fixtures de pago sin cuenta y reapertura con cabecera local de bitácora dañada. Primer arreglo: fixtures actualizados y conservación de consulta con escrituras bloqueadas ante bitácora dañada; 57 dirigidas correctas y repetición completa correcta. Roster inicial falló por no elegir cuenta; ajustado el flujo real, sin omitir la validación. La prueba dirigida inicial de Consulta recibió 428: se confirmó la tasa diaria por el flujo vigente, sin quitar el control.

## Próximo bloque

1. Recoger resultado y logs Windows; actualizar informe y pruebas reales. No reutilizar el resultado anterior del núcleo aislado como validación de Fase 1.
2. Fase 2: importaciones y perfiles persistidos, duplicados entre archivos, conciliación y clasificaciones. Las reglas puras existen; no constituyen el flujo operativo.
3. Fase 3: cierre mensual protegido, relación para contador y conciliación contra extracto. Después, Fase 4 completa si alcanza el uso.

No existe instalador nuevo. No se hicieron instalación/actualización/desinstalación de esta rama ni impresión física. NO VERIFICADO: Provincial, formulario/calibración y confirmación fiscal. No hay aprobación pendiente.
