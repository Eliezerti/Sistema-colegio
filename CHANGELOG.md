# Historial de cambios

## Sin publicar · Fase 1, punto 1 · 11 de octubre de 2026

- Aviso persistente para Administrador y Caja cuando falta el segundo destino, no hay copia externa confirmada, la copia externa tiene más de tres días o el último respaldo falló. Visible también antes de confirmar la tasa; permanece al buscar y filtrar, sin botón de cierre.
- Estado de respaldos calculado con la hora del servidor; cambiar la carpeta externa invalida la confirmación del destino anterior. Los errores al guardar el estado permanecen visibles hasta completar una copia nueva.
- Revisión de ACL y BitLocker en segundo plano, de solo lectura, sin elevación. Si Windows no permite la consulta, el resultado es «No se pudo comprobar».
- Guías y pruebas de estados, límites de antigüedad, permisos por perfil, actualización del aviso y diagnóstico de Windows.
- Sin migración de esquema ni cambios en datos existentes, carpeta de datos, transacciones de cobros, respaldos de cinco minutos, móvil/PWA o módulo de nómina.
- Pendiente: ejecución nativa en Windows y validación del instalador. Este cambio no certifica BitLocker ni los permisos de la PC del colegio.
