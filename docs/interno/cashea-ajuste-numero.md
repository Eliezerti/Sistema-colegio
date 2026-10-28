# Ajuste Cashea: número de recibo e inicial en Bs

Rama `cashea`, Aula 1.0.74 en desarrollo, esquema 14. Base del ajuste: `e3ba2d6`. Sin fusión a main ni publicación de una versión final.

Se implementaron número R- real de inicial, CA- sin inicial, configuración Recibo/Manual, copia del número, conversión visible de bolívares, advertencia mayor al 1 % y migración aditiva 13 → 14. El código de `record_payment` no cambia, ni se reescriben recibos o snapshots históricos.

Validación en curso. La línea base del código anterior pasó 345 unittest (tres nativas omitidas en Linux) y los tres navegadores. La primera ejecución del sandbox terminó con 150 errores de sockets; se repitió por el mecanismo autorizado con sockets locales. No se omitieron casos. Las 13 pruebas nuevas de numeración y migración pasaron; se están ejecutando las cuatro suites completas del ajuste. Se conservaron los 345 casos de prueba originales.

[Diseño](../../DISENO_CASHEA.md) · [Guía](../cashea.md). La evidencia final reemplazará esta nota de estado; no se declara Windows ni impresión física como verificados antes de ejecutarlos.
