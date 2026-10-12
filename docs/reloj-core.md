# Control persistente del reloj · componente de seguridad

El controlador guarda la última fecha y hora observada en `clock-status.json`, junto a la base. Es información de seguridad separada: no cambia el esquema SQLite, alumnos, importes, mensualidades existentes ni recibos históricos.

Política aprobada: siete días de avance máximo entre aperturas y dos minutos de tolerancia para ajustes. Durante la ejecución se compara con tiempo monotónico. Un retroceso mayor de dos minutos o un avance inesperado mayor de dos minutos durante el uso exige revisión administrativa.

Una anomalía queda pendiente aunque se corrija Windows o se cierre Aula. La confirmación necesita perfil Administrador, revisión explícita y la fecha mostrada todavía vigente. Primero se guarda la bitácora; solo después se publica el control que permite continuar. Un fallo de escritura mantiene el bloqueo.

Si la base ya tiene actividad y falta el archivo de control, se requiere revisión inicial del administrador, incluso cuando la fecha parece correcta. Si el control está dañado, no se reemplaza silenciosamente: se exige revisión y se conserva el archivo original antes de aceptar la confirmación.

El archivo se publica mediante reemplazo atómico y sincronización. No es una autoridad externa de hora ni protege frente a alguien que controle Windows y modifique los archivos. No lo borres ni lo edites para quitar un aviso.

Este componente tiene pruebas propias. La integración del servidor y la interfaz aplica su bloqueo a las operaciones y explica los pasos al usuario; la retención de respaldos tiene un control independiente de secuencia.
