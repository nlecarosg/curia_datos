# Licencia de los datos

Propuesta, pendiente de un abogado: **CC0 1.0 Universal** para la compilación que arma este repositorio (el orden de los archivos, el esquema, los textos y los programas de validación). El texto legal está en [`LICENSE`](LICENSE). La explicación de abajo está en español; el instrumento CC0 queda en inglés, que es su redacción oficial.

## Qué cubre la propuesta

CC0 dedica al dominio público, hasta donde la ley lo permite, lo que este repositorio agrega: la serie ordenada, el historial de capturas, el esquema de la observación y el modo de leerlos. La idea es la más simple para reutilizar indicadores sin pedir permiso a Curia Máxima.

Cada observación cita la fuente original. Esa cita es parte del dato y este repositorio la mantiene aunque CC0 no obligue a atribución.

## Qué no puede cubrir

Los números los produce el Instituto Nacional de Estadísticas. CC0 sobre esta compilación no re-licencia el dato de origen ni autoriza a presentar las cifras como si fueran de otro organismo. Quien las use tiene que poder llegar al INE, a la encuesta y al cuerpo crudo guardado en `crudo/`.

No encontré condiciones de uso publicadas en la ruta habitual del sitio del INE. La política de datos abiertos del Estado y las condiciones del propio instituto pueden exigir atribución, o limitar el uso comercial o el uso que sugiera respaldo oficial. Si eso es así, CC0 no borra esa obligación.

## Qué tiene que confirmar un abogado

Esta elección no está revisada por un abogado. Antes de tratar el repositorio como dominio público hay que confirmar al menos esto:

1. Que el INE y la normativa chilena de datos públicos permiten redistribuir esta serie dentro de un repositorio git.
2. Que CC0 sobre la compilación es compatible con esas condiciones. Si la fuente exige atribución obligatoria, la alternativa igual de simple es **CC BY 4.0** para todo el repositorio, en vez de CC0.
3. Que hace falta una frase fija de cita. Mientras tanto, este repositorio usa la siguiente:

> Instituto Nacional de Estadísticas. Índice nominal de remuneraciones (base 2023=100), nacional. Encuesta Mensual de Remuneraciones y Costos Laborales. Dataflow SDMX `CL01:DF_IR2023(1.0)`.

La fecha de captura y el hash del cuerpo están en cada observación.
