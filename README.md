# curia_datos

Repositorio público de indicadores oficiales usados por [Curia Máxima](https://github.com/nlecarosg/curia_maxima). Aquí están los datos, con su fuente, su fecha y el cuerpo tal cual lo devolvió el organismo. El programa que los descarga vive en el otro repositorio.

La serie se lee sin instalar nada. El recolector escribe directamente en esta raíz.

## De dónde sale cada dato

| Serie | Organismo | Qué es | Dónde se baja |
| --- | --- | --- | --- |
| `ine.ir2023.nacional.indice` | Instituto Nacional de Estadísticas | Índice nominal de remuneraciones, base 2023=100, total nacional, frecuencia mensual. Unidad SDMX `IX`. | SDMX público, sin clave: `https://sdmx.ine.gob.cl/rest/data/CL01,DF_IR2023,1.0` con `Accept: application/vnd.sdmx.data+json; version=1.0` |

La operación estadística es la Encuesta Mensual de Remuneraciones y Costos Laborales. El recolector, fijado en el commit `a3a8574575866423bec62e9b4b2ddc909cf8db44` de `curia_maxima`, guarda solo el índice (`IX`), redondeado a los decimales que declara el propio INE (hoy 2). La variación a 12 meses viaja en la misma respuesta y no se publica como observación.

El índice parte en enero de 2023. La fecha del dato es el primer día de ese mes (`2026-08-01` es agosto de 2026).

## Cómo leer una observación

`series/ine.ir2023.nacional.indice.json` es el archivo de la serie. El historial es la lista `observations`, una cifra por mes. Los nombres de los campos están en inglés, como los escribe el recolector:

| Campo | Significado |
| --- | --- |
| `value` | Cifra publicada, ya redondeada. |
| `unit` | `índice (base 2023=100)`. |
| `source.organism` | Instituto Nacional de Estadísticas (INE). |
| `source.url` | URL HTTPS de la consulta que produjo la captura. |
| `data_date` | Fecha del dato, `AAAA-MM-DD`. |
| `captured_at` | Momento UTC de la captura, `AAAA-MM-DDTHH:MM:SSZ`. |
| `raw_hash` | `sha256:` y el SHA-256 de `raw/ine.ir2023.nacional.indice.body`. |
| `status` | `vigente` o `no actualizado`. |
| `series_id` | `ine.ir2023.nacional.indice`. |

La última observación:

```bash
jq '.observations[-1] | {data_date, value, status}' series/ine.ir2023.nacional.indice.json
```

Para comprobar el hash:

```bash
sha256sum raw/ine.ir2023.nacional.indice.body
```

La primera columna tiene que ser igual a `raw_hash`, sin el prefijo `sha256:`. El archivo `.body` es la respuesta JSON de la última captura vigente. El sobre del INE cambia `meta.id` y `meta.prepared` en cada consulta, así que el hash cambia aunque el índice no se mueva. Las observaciones de esa captura apuntan a ese cuerpo. Un mes que una pasada posterior ya no traiga conserva su observación anterior; el archivo `.body` guardado sigue siendo solo el de la última captura que sí publicó.

Los esquemas están en [`esquema/observacion.schema.json`](esquema/observacion.schema.json) y [`esquema/serie.schema.json`](esquema/serie.schema.json). Son copia del commit fijado de `curia_maxima`. Para revisarlos:

```bash
python -m pip install "jsonschema==4.26.0"
python scripts/validar.py .
```

## Qué significa «no actualizado»

En una observación, `vigente` quiere decir que esa captura publicó el valor que está en el archivo.

`no actualizado` es el estado de la serie cuando la fuente no responde o el formato deja de calzar. El recolector no agrega ni modifica observaciones y no reemplaza el cuerpo crudo. Deja el motivo en el campo `error`.

En la acción diaria, ese caso termina con código 1. El trabajo queda en rojo, para que llegue la alerta de GitHub, y no hay push: `main` conserva la última serie vigente ya commiteada.

## Estructura de carpetas

```text
.
├── README.md
├── LICENCIA.md
├── LICENSE
├── esquema/
│   ├── observacion.schema.json
│   └── serie.schema.json
├── scripts/
│   ├── validar.py
│   └── probar.py
├── .github/workflows/
│   ├── validar.yml
│   └── actualizar.yml
├── series/
│   └── ine.ir2023.nacional.indice.json
└── raw/
    └── ine.ir2023.nacional.indice.body
```

Otra serie entra como otro archivo en `series/` y su cuerpo en `raw/`, que es donde `python -m curia_maxima --output <esta raíz>` escribe.

## Qué cambió respecto de la primera carga

La primera carga, armada antes de poder leer el recolector, usaba `datos/ine/ir2023/serie.json`, `historial.jsonl` y `crudo/`, con campos en español (`valor`, `fecha_dato` en `AAAA-MM`, `fuente` como texto) y guardaba también la variación a 12 meses con todos los decimales del CSV. El recolector real no escribe esos archivos. Esta raíz ahora es la ruta `--output` del paquete.

## Actualización diaria

[`.github/workflows/actualizar.yml`](.github/workflows/actualizar.yml) corre todos los días a las 12:00 UTC y también a mano (`workflow_dispatch`).

1. Instala `git+https://github.com/nlecarosg/curia_maxima.git@a3a8574575866423bec62e9b4b2ddc909cf8db44`, sin secretos.
2. Ejecuta `python -m curia_maxima --output` en la raíz de este repositorio.
3. Valida `series/` y `raw/`. Si el recolector sale con código 1, o la validación falla, no hay commit.
4. Hace commit y push con `GITHUB_TOKEN` solo cuando `series/` o `raw/` quedaron distintos de `main`. Si no hay diferencia, no crea un commit vacío.

`permissions: contents: write` está en el workflow. `main` no tiene protección de rama ni rulesets. Si el push del bot respondiera 403, el ajuste está en el repositorio: Settings → Actions → General → Workflow permissions → «Read and write permissions».

## Licencia

Propuesta CC0 para la compilación, citando siempre al INE. Hay que confirmarla con un abogado antes de tratarla como cerrada. El detalle está en [`LICENCIA.md`](LICENCIA.md).
