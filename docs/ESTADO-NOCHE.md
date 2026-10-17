# Estado de trabajo nocturno

**Fase 1 integrada y validada en Linux y Windows. Conciliación integrada y validada en Linux; Windows pendiente. Fase 3 preparada, aún no integrada. Fase 4 pendiente.**

- Rama `autonomo/ingresos-facturas`; código de Fase 1: `ddba0ca9a2707f1fd9b133b4aea732d757fd1c2a`. Main, etiquetas y publicación intactos.
- Commits: `2701023` migración; `1e003a4` servidor y reportes; `11e00dc` pruebas; `ddba0ca` interfaz.
- Fase 0 documentada. Fase 1: catálogo, cuenta destino, asignación histórica, otros ingresos/categorías, depósitos parciales, egresos con cuenta, permisos y bitácora. [Guía](cuentas-ingresos.md).
- Esquema 13 aditivo; copia previa verificada (cifrada cuando está configurado), fixture real del código publicado 1.0.71 con datos ficticios, integridad/cadena y cinco cortes reales comprobados. Ninguna base del usuario abierta o modificada.
- Los recibos originales, importes y correlativos se conservan. Los depósitos no duplican ingresos. Instalación nueva con siete tablas nuevas vacías.

## Resultados reales de esta fase

| Comando | Linux | Windows |
|---|---|---|
| `python -m unittest discover -s tests -v` | 333 en 206,436 s; 330 correctas y 3 nativas omitidas | 333 correctas en 550,777 s; sin omisiones |
| `python tests/run_browser.py` | Salida 0, incluye flujo nuevo por interfaz y copia consulta | Salida 0 |
| `python tests/run_browser.py --demo` | Salida 0 | Salida 0 |
| `python tests/run_browser.py --roster` | Salida 0 | Salida 0 |

Windows: https://github.com/Eliezerti/Sistema-colegio/actions/runs/39001990044
Registros: https://github.com/Eliezerti/Sistema-colegio/actions/runs/39001990044/artifacts/12090006489
Logs Linux: `/workspace/work/noche2/phase1-*-fixed.log`, `phase1-roster-final.log`.

Primera regresión ampliada: 331 en 213,631 s, 15 errores y 3 omisiones. Causas: fixtures sintéticos antiguos con tablas acompañantes nuevas, fixtures de pago sin cuenta y reapertura con cabecera local de bitácora dañada. Primer arreglo: fixtures actualizados y conservación de consulta con escrituras bloqueadas ante bitácora dañada; 57 dirigidas correctas y repetición completa correcta. Roster inicial falló por no elegir cuenta; ajustado el flujo real, sin omitir la validación. La prueba dirigida inicial de Consulta recibió 428: se confirmó la tasa diaria por el flujo vigente, sin quitar el control.

## Próximo bloque

1. Recoger resultado y logs Windows; actualizar informe y pruebas reales. No reutilizar el resultado anterior del núcleo aislado como validación de Fase 1.
2. Fase 2: importaciones y perfiles persistidos, duplicados entre archivos, conciliación y clasificaciones. Las reglas puras existen; no constituyen el flujo operativo.
3. Fase 3: cierre mensual protegido, relación para contador y conciliación contra extracto. Después, Fase 4 completa si alcanza el uso.

No existe instalador nuevo. No se hicieron instalación/actualización/desinstalación de esta rama ni impresión física. NO VERIFICADO: Provincial, formulario/calibración y confirmación fiscal. No hay aprobación pendiente.

## Punto de Fase 2

- Código `e6b40ee`: commits `0b5d11c` (esquema 14), `7f10cea` (servidor/confidencialidad/pruebas), `e6b40ee` (interfaz). Esquema 13 sigue siendo el punto previo de reversión, no el esquema actual de este código.
- Cuatro suites Linux: unittest **343 en 219,629 s, 340 correctas y tres nativas omitidas**; normal, demo y roster **salida 0**. Logs `phase2-final-*.log` en `/workspace/work/noche2/`.
- Diez pruebas nuevas de conciliación/migración, incluido proceso terminado realmente en cinco puntos y respaldo previo 13 cifrado abierto con contraseña y recuperación. Interfaz de perfil, CSV con ñ, vista previa, confirmación, cruce y totales correctos.
- Primer dirigido: una referencia ficticia repetida sin confirmar; corregida mediante el control vigente. Primera suite completa: 343 en 219,262 s, un fallo por contrato de permisos que esperaba 400 ante cruce válido vacío; contrato corregido (200 y cero vínculos), 12 dirigidas correctas en 14,778 s y repetición completa correcta. Primer navegador falló por selector ambiguo de diálogos; selector específico y repetición correcta.
- Perfil real Provincial **NO VERIFICADO**. Cruces entre cuentas o monedas y depósitos de efectivo con conversión: pendientes; nunca inferirlos. Conciliación integrada limitada a 20.000 movimientos por lado. No usar una prueba pura para declarar rendimiento HTTP.
- Preparados `colegio/month_schema.py` y `colegio/accounting.py` sin importación desde el producto y todavía sin commit: Fase 3 no activa. Integrar y probar antes de incluirlos en el punto verde; descartar estos archivos propios si no se completa la fase.
