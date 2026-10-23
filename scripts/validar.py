#!/usr/bin/env python3
"""Valida un directorio de datos contra el esquema de la observación.

Uso:
    python scripts/validar.py datos/ine/ir2023
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

RAIZ = Path(__file__).resolve().parents[1]
ESQUEMA_RUTA = RAIZ / "esquema" / "observacion.schema.json"


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


def validar(directorio: Path) -> dict:
    """Revisa la serie, el historial y los cuerpos. Devuelve lo leído."""
    directorio = Path(directorio)
    if not directorio.is_dir():
        raise ValidacionError(f"no existe el directorio {directorio}")

    try:
        esquema = json.loads(ESQUEMA_RUTA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(esquema)
    except (OSError, json.JSONDecodeError, SchemaError) as exc:
        raise ValidacionError(f"el esquema no se puede usar: {exc}") from exc

    validador = Draft202012Validator(esquema)
    estados = set(esquema["properties"]["estado"]["enum"])

    crudo = directorio / "crudo"
    if not crudo.is_dir():
        raise ValidacionError("falta el directorio crudo/")
    archivos = [path for path in crudo.iterdir() if path.is_file() and not path.name.startswith(".")]
    if not archivos:
        raise ValidacionError("crudo/ no tiene ningún cuerpo")
    hashes: dict[str, Path] = {}
    for path in archivos:
        if path.stat().st_size == 0:
            raise ValidacionError(f"el cuerpo {path.name} está vacío")
        digest = _sha256(path)
        hashes.setdefault(digest, path)

    serie = _cargar_json(directorio / "serie.json")
    if not isinstance(serie, list) or not serie:
        raise ValidacionError("serie.json debe ser una lista con observaciones")

    historial_path = directorio / "historial.jsonl"
    if not historial_path.is_file():
        raise ValidacionError("falta historial.jsonl")
    lineas = []
    for numero, linea in enumerate(historial_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not linea.strip():
            continue
        try:
            captura = json.loads(linea)
        except json.JSONDecodeError as exc:
            raise ValidacionError(f"historial.jsonl línea {numero} no es JSON: {exc.msg}") from exc
        if not isinstance(captura, dict):
            raise ValidacionError(f"historial.jsonl línea {numero} no es un objeto")
        lineas.append(captura)
    if not lineas:
        raise ValidacionError("historial.jsonl no tiene capturas")

    def revisar_observacion(obs, donde: str) -> None:
        if not isinstance(obs, dict):
            raise ValidacionError(f"{donde} no es un objeto")
        try:
            validador.validate(obs)
        except ValidationError as exc:
            camino = ".".join(str(parte) for parte in exc.absolute_path)
            detalle = f"{camino}: {exc.message}" if camino else exc.message
            raise ValidacionError(f"{donde}: {detalle}") from exc
        digest = obs["hash_crudo"].removeprefix("sha256:")
        if digest not in hashes:
            raise ValidacionError(f"{donde}: no está el cuerpo {obs['hash_crudo']}")

    for indice, obs in enumerate(serie):
        revisar_observacion(obs, f"serie[{indice}]")

    for numero, captura in enumerate(lineas, start=1):
        donde = f"historial línea {numero}"
        for campo in ("fecha_captura", "hash_crudo", "estado", "observaciones"):
            if campo not in captura:
                raise ValidacionError(f"{donde}: falta {campo}")
        if captura["estado"] not in estados:
            raise ValidacionError(f"{donde}: estado desconocido")
        if not isinstance(captura["observaciones"], list) or not captura["observaciones"]:
            raise ValidacionError(f"{donde}: observaciones debe tener elementos")
        digest = str(captura["hash_crudo"]).removeprefix("sha256:")
        if digest not in hashes:
            raise ValidacionError(f"{donde}: no está el cuerpo {captura['hash_crudo']}")
        for indice, obs in enumerate(captura["observaciones"]):
            revisar_observacion(obs, f"{donde} observación {indice}")
            if obs["fecha_captura"] != captura["fecha_captura"]:
                raise ValidacionError(f"{donde} observación {indice}: la fecha de captura no coincide")
            if obs["hash_crudo"] != captura["hash_crudo"]:
                raise ValidacionError(f"{donde} observación {indice}: el hash no coincide")
            if obs["estado"] != captura["estado"]:
                raise ValidacionError(f"{donde} observación {indice}: el estado no coincide")

    if lineas[-1]["observaciones"] != serie:
        raise ValidacionError("serie.json no es la última captura del historial")

    return {"serie": serie, "historial": lineas, "hashes": hashes}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Uso: python scripts/validar.py <directorio>", file=sys.stderr)
        return 2
    try:
        info = validar(Path(argv[1]))
    except ValidacionError as exc:
        print(f"validación fallida: {exc}", file=sys.stderr)
        return 1
    def cantidad(n: int, uno: str, varios: str) -> str:
        return f"{n} {uno if n == 1 else varios}"

    print(
        "ok: "
        + ", ".join(
            [
                cantidad(len(info["serie"]), "observación", "observaciones"),
                cantidad(len(info["historial"]), "captura", "capturas"),
                cantidad(len(info["hashes"]), "cuerpo", "cuerpos"),
            ]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
