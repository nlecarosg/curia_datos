#!/usr/bin/env python3
"""Valida la salida de curia_maxima en la raíz de este repositorio.

Uso:
    python scripts/validar.py .
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource

RAIZ = Path(__file__).resolve().parents[1]
ESQUEMA_OBSERVACION = RAIZ / "esquema" / "observacion.schema.json"
ESQUEMA_SERIE = RAIZ / "esquema" / "serie.schema.json"


class ValidacionError(Exception):
    """El directorio no se puede publicar."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cargar_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidacionError(f"falta {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise ValidacionError(f"{path.name} no es JSON: {exc.msg}") from exc


def _validador_serie() -> Draft202012Validator:
    try:
        observacion = json.loads(ESQUEMA_OBSERVACION.read_text(encoding="utf-8"))
        serie = json.loads(ESQUEMA_SERIE.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(observacion)
        Draft202012Validator.check_schema(serie)
    except (OSError, json.JSONDecodeError, SchemaError) as exc:
        raise ValidacionError(f"el esquema no se puede usar: {exc}") from exc
    registry = Registry().with_resources(
        [
            (observacion["$id"], Resource.from_contents(observacion)),
            (serie["$id"], Resource.from_contents(serie)),
        ]
    )
    return Draft202012Validator(serie, registry=registry)


def validar(directorio: Path) -> dict:
    """Revisa cada serie y el cuerpo crudo de la última captura vigente."""
    directorio = Path(directorio)
    series_dir = directorio / "series"
    if not series_dir.is_dir():
        raise ValidacionError("falta el directorio series/")
    archivos = sorted(
        path for path in series_dir.glob("*.json") if path.is_file() and not path.name.startswith(".")
    )
    if not archivos:
        raise ValidacionError("series/ no tiene ninguna serie")

    validador = _validador_serie()
    documentos = []
    cuerpos = 0
    for path in archivos:
        documento = _cargar_json(path)
        if not isinstance(documento, dict):
            raise ValidacionError(f"{path.name} no es un objeto")
        errores = sorted(
            validador.iter_errors(documento),
            key=lambda error: ([str(parte) for parte in error.absolute_path], error.message),
        )
        if errores:
            error = errores[0]
            camino = ".".join(str(parte) for parte in error.absolute_path) or "raíz"
            raise ValidacionError(f"{path.name} ({camino}): {error.message}")

        series_id = documento["series_id"]
        if path.stem != series_id:
            raise ValidacionError(f"{path.name} no se llama como su series_id ({series_id})")

        observaciones = documento["observations"]
        cuerpo = directorio / "raw" / f"{series_id}.body"
        if observaciones:
            if not cuerpo.is_file():
                raise ValidacionError(f"falta el cuerpo crudo raw/{series_id}.body")
            if cuerpo.stat().st_size == 0:
                raise ValidacionError(f"el cuerpo raw/{series_id}.body está vacío")
            digest = f"sha256:{_sha256(cuerpo)}"
            cuerpos += 1
            coinciden = [obs for obs in observaciones if obs["raw_hash"] == digest]
            if not coinciden:
                raise ValidacionError(
                    f"{path.name}: ninguna observación tiene el hash del cuerpo {digest}"
                )
            if documento["status"] == "vigente":
                de_esta_captura = [
                    obs for obs in observaciones if obs["captured_at"] == documento["captured_at"]
                ]
                if not de_esta_captura:
                    raise ValidacionError(f"{path.name}: la captura vigente no publicó observaciones")
                distintas = [obs for obs in de_esta_captura if obs["raw_hash"] != digest]
                if distintas:
                    raise ValidacionError(
                        f"{path.name}: el hash de la captura vigente no es el del cuerpo crudo"
                    )
        documentos.append(documento)

    return {"series": documentos, "cuerpos": cuerpos}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Uso: python scripts/validar.py <directorio>", file=sys.stderr)
        return 2
    try:
        info = validar(Path(argv[1]))
    except ValidacionError as exc:
        print(f"validación fallida: {exc}", file=sys.stderr)
        return 1
    observaciones = sum(len(serie["observations"]) for serie in info["series"])
    print(
        f"ok: {len(info['series'])} serie(s), {observaciones} observaciones, "
        f"{info['cuerpos']} cuerpo(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
