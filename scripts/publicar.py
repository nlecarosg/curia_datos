#!/usr/bin/env python3
"""Incorpora una salida ya validada del recolector sin borrar lo publicado.

Uso:
    python scripts/publicar.py datos/ine/ir2023 /ruta/de/la/salida

Si el cuerpo crudo ya estaba en el historial, no toca los archivos.
Si la salida es inválida o trae menos observaciones que las ya publicadas,
termina con error y deja el directorio publicado como estaba.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

from validar import ValidacionError, validar


def _clave(obs: dict) -> tuple:
    return (obs["fecha_dato"], obs["unidad"])


def _escribir(destino: Path, serie: list, historial: list, archivos: dict[str, Path]) -> None:
    if destino.exists():
        shutil.rmtree(destino)
    (destino / "crudo").mkdir(parents=True)
    for digest, origen in archivos.items():
        shutil.copyfile(origen, destino / "crudo" / digest)
    (destino / "serie.json").write_text(
        json.dumps(serie, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lineas = [
        json.dumps(captura, ensure_ascii=False, separators=(",", ":"))
        for captura in historial
    ]
    (destino / "historial.jsonl").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def _reemplazar(actual: Path, staging: Path) -> None:
    padre = actual.parent
    padre.mkdir(parents=True, exist_ok=True)
    respaldo = Path(tempfile.mkdtemp(prefix="curia-respaldo-", dir=padre))
    movido = respaldo / "anterior"
    try:
        if actual.exists():
            actual.rename(movido)
        shutil.copytree(staging, actual)
    except Exception:
        if actual.exists():
            shutil.rmtree(actual)
        if movido.exists():
            movido.rename(actual)
        raise
    finally:
        shutil.rmtree(respaldo, ignore_errors=True)


def publicar(actual: Path, nuevo: Path) -> bool:
    """Devuelve True si quedó una captura nueva publicada."""
    actual = Path(actual)
    nuevo = Path(nuevo)
    if actual.exists() and actual.resolve() == nuevo.resolve():
        raise ValidacionError("la salida y el directorio publicado son el mismo")

    datos_nuevos = validar(nuevo)
    hash_nuevo = datos_nuevos["historial"][-1]["hash_crudo"]

    if not actual.exists():
        staging = Path(tempfile.mkdtemp(prefix="curia-publicar-"))
        try:
            _escribir(staging, datos_nuevos["serie"], datos_nuevos["historial"], datos_nuevos["hashes"])
            validar(staging)
            _reemplazar(actual, staging)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return True

    datos_actuales = validar(actual)
    conocidos = {captura["hash_crudo"] for captura in datos_actuales["historial"]}
    if hash_nuevo in conocidos:
        guardada = next(
            captura
            for captura in datos_actuales["historial"]
            if captura["hash_crudo"] == hash_nuevo
        )
        if guardada["observaciones"] != datos_nuevos["serie"]:
            raise ValidacionError(
                "ese cuerpo crudo ya estaba publicado y la serie nueva no coincide con esa captura"
            )
        return False

    faltan = {_clave(obs) for obs in datos_actuales["serie"]} - {
        _clave(obs) for obs in datos_nuevos["serie"]
    }
    if faltan:
        muestra = ", ".join(f"{fecha} / {unidad}" for fecha, unidad in sorted(faltan)[:3])
        raise ValidacionError(
            f"la salida omite {len(faltan)} observaciones ya publicadas ({muestra})"
        )

    historial = list(datos_actuales["historial"])
    for captura in datos_nuevos["historial"]:
        if captura["hash_crudo"] not in conocidos:
            historial.append(captura)
            conocidos.add(captura["hash_crudo"])
    archivos = dict(datos_actuales["hashes"])
    archivos.update(datos_nuevos["hashes"])

    staging = Path(tempfile.mkdtemp(prefix="curia-publicar-"))
    try:
        _escribir(staging, datos_nuevos["serie"], historial, archivos)
        validar(staging)
        _reemplazar(actual, staging)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return True


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "Uso: python scripts/publicar.py <directorio-publicado> <salida-del-recolector>",
            file=sys.stderr,
        )
        return 2
    try:
        cambio = publicar(Path(argv[1]), Path(argv[2]))
    except ValidacionError as exc:
        print(f"no se publicó: {exc}", file=sys.stderr)
        return 1
    print("datos nuevos publicados" if cambio else "sin datos nuevos")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main(sys.argv))
