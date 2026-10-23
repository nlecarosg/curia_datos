# curia_datos

Repositorio público de indicadores oficiales usados por [Curia Máxima](https://github.com/nlecarosg/curia_maxima). Aquí están los datos, con su fuente, su fecha y el cuerpo tal cual lo devolvió el organismo. El programa que los descarga vive en el otro repositorio.

La serie se puede leer sin instalar nada. Un archivo JSON por indicador, un historial de cada vez que el cuerpo cambió, y el archivo crudo contra el que se calculó el hash.

## De dónde sale cada dato

| Indicador | Organismo | Qué es | Dónde se baja |
| --- | --- | --- | --- |
| IR2023 | Instituto Nacional de Estadísticas | Índice nominal de remuneraciones, base promedio 2023=100, total nacional. También trae la variación a 12 meses. | Servicio SDMX público, sin clave: [`CL01:DF_IR2023(1.0)`](https://sdmx.ine.gob.cl/rest/data/CL01,DF_IR2023,1.0/all?format=csv) |

La operación estadística es la Encuesta Mensual de Remuneraciones y Costos Laborales. El mes del dato viene en `TIME_PERIOD` (`2026-M08` es agosto de 2026). El índice es la columna `UNIDAD=IX` y la variación a 12 meses es `UNIDAD=VAR12`. El INE declara dos decimales en la columna `DECIMALS`; el JSON guarda el `OBS_VALUE` completo para que coincida con el cuerpo.

El índice parte en enero de 2023. La variación a 12 meses parte en enero de 2024: en el año base el INE deja esas celdas vacías, así que no hay observación para ellas. Esas filas siguen en el cuerpo crudo. Cuando el organismo marca `Valor provisional`, la observación lleva ese texto en `nota`. Una captura posterior puede traer otro número; la anterior queda en el historial.

La primera carga se bajó directo de esa URL el 23 de octubre de 2026. `curia_maxima` todavía es privado y desde aquí no se puede instalar. Las cargas siguientes las debe escribir el recolector de ese repositorio, con el mismo formato.

## Cómo leer una observación

`datos/ine/ir2023/serie.json` es una lista. Cada elemento es una observación y tiene estos campos:

| Campo | Significado |
| --- | --- |
| `valor` | Cifra del organismo. |
| `unidad` | `índice (base promedio 2023=100)` o `variación a 12 meses (porcentaje)`. |
| `fuente` | Instituto, encuesta, dataflow y URL. |
| `fecha_dato` | Mes de la cifra, `AAAA-MM`. |
| `fecha_captura` | Momento UTC en que se guardó el cuerpo, `AAAA-MM-DDTHH:MM:SSZ`. |
| `hash_crudo` | `sha256:` y el SHA-256 del archivo que está en `crudo/`. |
| `estado` | `vigente` o `no actualizado`. |
| `nota` | Opcional. Texto del INE, hoy `Valor provisional`. |

El último mes del índice:

```bash
jq '[.[] | select(.unidad | startswith("índice"))] | last | {fecha_dato, valor, nota, estado}' datos/ine/ir2023/serie.json
```

La variación a 12 meses del mismo mes se filtra con `variación`. Para comprobar el hash:

```bash
sha256sum datos/ine/ir2023/crudo/*
```

La primera columna tiene que ser igual a `hash_crudo`, sin el prefijo `sha256:`. El archivo dentro de `crudo/` se llama con ese hexadecimal.

`historial.jsonl` tiene una línea por cuerpo distinto. La línea repite la serie completa de esa captura. `serie.json` es siempre igual a la última línea. Si el INE rectifica un mes provisional, la serie cambia y la captura anterior sigue en el historial, con su propio cuerpo.

El esquema está en [`esquema/observacion.schema.json`](esquema/observacion.schema.json). Para revisarlo:

```bash
python -m pip install "jsonschema==4.26.0"
python scripts/validar.py datos/ine/ir2023
```

## Qué significa «no actualizado»

`vigente` quiere decir que esa captura trajo un cuerpo que pasó el esquema y que el valor es el de ese cuerpo.

`no actualizado` conserva el último valor validado —el mismo número, la misma fuente, la misma fecha del dato y el mismo hash— y deja constancia de que una corrida posterior no pudo confirmar una publicación nueva. El historial y el cuerpo anterior siguen en el repositorio.

Si el SDMX no responde, el formato deja de calzar o la salida viene incompleta, la acción de GitHub termina con error para que llegue la alerta. Esa corrida no borra ni reescribe lo ya publicado. El estado `no actualizado` solo aparece cuando el recolector lo escribe en una salida que igual pasa la validación.

## Estructura de carpetas

```text
.
├── README.md
├── LICENCIA.md              explicación en español; hay que confirmarla con un abogado
├── LICENSE                    CC0 1.0, texto legal
├── esquema/
│   └── observacion.schema.json
├── scripts/
│   ├── validar.py             rechaza una salida que no cumple el esquema o el hash
│   ├── publicar.py            incorpora una salida nueva sin borrar capturas anteriores
│   └── probar.py              pruebas de ese comportamiento
├── .github/workflows/
│   ├── validar.yml            corre en cada pull request
│   └── actualizar.yml         una vez al día y a mano
└── datos/
    └── ine/
        └── ir2023/
            ├── serie.json
            ├── historial.jsonl
            └── crudo/
                └── <sha256>   cuerpo CSV exacto, con sus saltos de línea originales
```

Otro indicador entra como otra carpeta bajo `datos/<organismo>/<indicador>/`, con los mismos tres nombres.

## Actualización diaria

[`.github/workflows/actualizar.yml`](.github/workflows/actualizar.yml) corre todos los días a las 12:00 UTC y también se puede lanzar a mano (`workflow_dispatch`). Hace esto:

1. Comprueba que `https://github.com/nlecarosg/curia_maxima` responda como repositorio público.
2. Instala esa revisión con pip desde git, sin secretos: `git+https://github.com/nlecarosg/curia_maxima.git@<revisión>`.
3. Ejecuta `python -m curia_maxima --output <directorio temporal>`.
4. Valida esa salida. Si falla, el trabajo queda en rojo y `datos/` no se toca.
5. Publica solo si el hash del cuerpo todavía no estaba en el historial. Agrega el cuerpo nuevo, agrega la línea al historial y reemplaza la serie. No borra cuerpos ni líneas anteriores, y rechaza una serie que omita un mes ya publicado.
6. Hace commit únicamente cuando quedó un archivo distinto.

La revisión va en `CURIA_MAXIMA_REV`, al inicio del workflow. Tiene que ser un commit de 40 hexadecimales o un tag `v…`. Hoy dice `FIJAR_COMMIT_O_TAG` a propósito.

### Mientras curia_maxima siga privado

Un workflow de este repositorio no puede clonar el otro: GitHub responde 404 y no hay un token que poner. El workflow está escrito para el día en que el código sea público. Hasta ese día la corrida diaria falla en el primer paso, con un mensaje explícito, y los datos de esta rama siguen publicados.

La alternativa igual de simple, y también sin secretos, es no instalar el paquete y bajar el CSV desde la URL de arriba con un script de este repositorio. Esa API no pide clave. El costo es mantener el parser en dos sitios hasta que el recolector único viva en `curia_maxima`. Por eso el cron no usa esa vía: cuando el paquete sea público, el único comando que escribe datos es `python -m curia_maxima`.

Para que esa corrida publique sola, la salida del recolector tiene que traer:

- `serie.json`, lista de observaciones con las unidades escritas tal como en la tabla de arriba.
- `historial.jsonl`, una línea JSON por captura, con `fecha_captura`, `hash_crudo`, `estado` y `observaciones`. La última línea es la serie.
- `crudo/` con el cuerpo cuyos bytes dan el hash. El nombre del archivo da igual.

## Licencia

Propuesta CC0 para la compilación, citando siempre al INE. Hay que confirmarla con un abogado antes de tratarla como cerrada. El detalle está en [`LICENCIA.md`](LICENCIA.md).
