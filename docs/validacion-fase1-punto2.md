# Validación · seguimiento del punto 1 y punto 2

## Respuestas y corrección previa

Se respondió con evidencia antes de modificar archivos. El aviso original confirmaba escritura en la carpeta, no subida a la nube; faltaba detectar mismo disco. BitLocker se consulta sin elevación y puede no permitir la consulta a una cuenta estándar; ACL usa esa misma cuenta. Pruebas estaba excluido correctamente. Las guías originales se publicaron en `a71fc55` y los resultados en `d2f11d3`.

El seguimiento `c2c0cda` aclara el límite en pantalla, compara disco del segundo destino (o indica desconocido), añade ayuda de Windows sin elevar Aula y comprueba en navegador que Pruebas no muestra el aviso. Suite: 161 descubiertas, 160 correctas y una exclusiva de Windows omitida en Linux; navegadores normal, Pruebas e importación correctos. Después se comenzó el punto 2.

## Cambios y decisiones

- Política aprobada por el propietario: siete días entre aperturas y dos minutos para ajustes. Durante el uso se compara con tiempo monotónico.
- Estado persistido junto a la base; sin migración de esquema SQLite. Con actividad anterior y sin control, se exige revisión inicial.
- Bloqueo en servidor y motor, incluido inicio, consultas, cobros, generación y documentos. Solo Administrador confirma, con CSRF; bitácora antes de desbloquear. Revisión final antes del commit financiero.
- No se modifican cargos, importes, alumnos ni documentos históricos. La confirmación limita sesiones con vencimientos excesivos y nunca extiende otras.
- Orden de conservación de respaldos persistido por publicación. Registro ilegible no autoriza borrar; una copia verificada continúa al segundo destino aunque falle el registro de conservación.
- Limitación de intentos de login con tiempo monotónico, aún en memoria.

Commits funcionales: `4f20199` (controlador), `b15ee0a` (servidor/motor/interfaz), `2648251` (retención).

## Comandos ejecutados y resultados en Linux

| Comando | Resultado |
|---|---|
| `python -m unittest discover -s tests -v` | 186 descubiertas, 185 correctas y una exclusiva de Windows omitida; 59,551 segundos. |
| `python tests/run_browser.py` | Correcto; flujos anteriores más bloqueo visual, roles, confirmación, impresión comprobada y aviso de respaldo dentro de la pantalla del reloj. |
| `python tests/run_browser.py --demo` | Correcto; aislamiento, documentos de prueba y borrado al cerrar. |
| `python tests/run_browser.py --roster` | Correcto; Excel/CSV, estados, documentos y conservación de origen. |

Se añadieron 25 pruebas en el punto 2: persistencia, límites, retroceso, avance, tolerancia, medianoche, confirmación administrativa, rechazo de Caja/Consulta, CSRF, datos mostrados vencidos, control dañado/no publicable, inicio adelantado sin mensualidades, esquema intacto, bloqueo de reportes/recibos, intento de login con reloj cambiado, rollback de pago al saltar antes del commit, límites de sesiones, retención con fechas/nombres futuros, inventario corrupto y copia externa pese a fallo del inventario. Incluye el 29 de febrero, redondeo y ausencia de duplicados.

Las pruebas de recuperación dirigen la falla al archivo de copia externo en vez de asumir que el segundo fsync siempre es USB: ahora también se sincroniza el registro de conservación. Siguen verificando descriptor escribible de Windows, pagos del WAL, integridad, conservación de copias previas y restauración.

## Windows y límites

Pendiente de la compilación y pruebas nativas de GitHub Actions. Linux no prueba el mutex ni la ventana de Windows, y tampoco certifica BitLocker, discos físicos ni ACL de la PC del colegio.

No se verificó la hora por internet ni se hicieron cortes eléctricos en una PC real. La primera fecha de una instalación sin actividad no tiene referencia externa. Las copias antiguas sin registro de orden solo tienen una estimación inicial basada en metadatos. Quien controle Windows puede modificar archivos: este control no reemplaza seguridad del sistema ni la bitácora protegida del punto 5.

## Archivos y prueba manual

- Seguridad: `colegio/clock_guard.py`, `colegio/backup_retention.py`, `colegio/backup_health.py`, `colegio/protection.py`.
- Integración: `colegio/db.py`, `colegio/server.py`, `colegio/storage.py`, `static/app.js`.
- Pruebas: `tests/test_clock_guard.py`, `tests/test_clock_endpoints.py`, `tests/test_backup_retention.py`, `tests/test_monthly_automation.py`, `tests/test_recovery.py`, `tests/test_backup_alerts.py`, `tests/test_protection.py`, `tests/browser.cjs`, `tests/demo_browser.cjs`.
- Guías: README, CHANGELOG, mantenimiento, protección de respaldos, controlador del reloj, protección del reloj y este informe. Las guías de usuario tienen versión HTML para instalarse.
- Entrega: notas/título en `.github/workflows/windows-desktop.yml`.

Consulta [Protección del reloj](proteccion-reloj.md#qué-comprobar-en-el-colegio) y [Avisos de respaldos](proteccion-respaldos.md#prueba-manual-con-el-administrador-y-caja). No provoques cambios de fecha con datos reales. Revisa como administrador la fecha inicial y tasa; verifica último recibo y saldo; Caja no puede confirmar. Conserva respaldo externo antes de instalar con la misma cuenta de Windows.

No se comenzó el punto 3: los respaldos siguen sin cifrar.
