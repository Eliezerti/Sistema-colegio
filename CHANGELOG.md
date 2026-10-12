# Historial de cambios

## Sin publicar · Fase 1, punto 1 · 11 de octubre de 2026

- Aviso persistente para Administrador y Caja cuando falta el segundo destino, no hay copia externa confirmada, la copia externa tiene más de tres días o el último respaldo falló. Visible también antes de confirmar la tasa; permanece al buscar y filtrar, sin botón de cierre.
- Estado de respaldos calculado con la hora del servidor; cambiar la carpeta externa invalida la confirmación del destino anterior. Los errores al guardar el estado permanecen visibles hasta completar una copia nueva.
- Revisión de ACL y BitLocker en segundo plano, de solo lectura, sin elevación. Si Windows no permite la consulta, el resultado es «No se pudo comprobar».
- Guías y pruebas de estados, límites de antigüedad, permisos por perfil, actualización del aviso y diagnóstico de Windows.
- Sin migración de esquema ni cambios en datos existentes, carpeta de datos, transacciones de cobros, respaldos de cinco minutos, móvil/PWA o módulo de nómina.
- Validación: Linux, 158 descubiertas (157 correctas y una omitida); Windows, 158 correctas. Navegadores normal, Pruebas e importación correctos. Instalador 1.0.26 en borrador, con validación nativa y conservación de datos.
- Pendiente: comprobación de BitLocker/ACL en la PC del colegio y revisión de las alertas de Defender anteriores. Los análisis del runner no certifican esa PC.

## Seguimiento del punto 1

- Aclarado en pantalla: copia escrita en la carpeta, no subida a la nube.
- Aviso propio por mismo disco, y estado desconocido cuando no puede verificarse.
- Ayuda para comprobar BitLocker/ACL desde Windows con los permisos adecuados, sin elevar Aula.
- Prueba adicional: Pruebas no muestra avisos reales. Sin cambios de esquema ni datos existentes.

Validación del seguimiento: 161 descubiertas en Linux (160 correctas, una exclusiva de Windows omitida); navegadores normal, Pruebas e importación correctos. La consulta física de Windows y su revisión en la PC del colegio no se certifican con estas pruebas Linux.
