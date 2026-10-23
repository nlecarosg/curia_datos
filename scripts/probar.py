#!/usr/bin/env python3
"""Pruebas locales del validador. No descarga nada ni llama al recolector."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validar import ValidacionError, validar

RAIZ = Path(__file__).resolve().parents[1]
SERIE = "ine.ir2023.nacional.indice"


def _exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise SystemExit(mensaje)


def _copiar(destino: Path) -> None:
    shutil.copytree(RAIZ / "series", destino / "series")
    shutil.copytree(RAIZ / "raw", destino / "raw")


def _bytes(directorio: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directorio).as_posix(): path.read_bytes()
        for path in sorted(directorio.rglob("*"))
        if path.is_file()
    }


def _leer(directorio: Path) -> dict:
    return json.loads((directorio / "series" / f"{SERIE}.json").read_text(encoding="utf-8"))


def _guardar(directorio: Path, documento: dict) -> None:
    path = directorio / "series" / f"{SERIE}.json"
    path.write_text(json.dumps(documento, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    info = validar(RAIZ)
    _exigir(len(info["series"]) == 1, "se esperaba una serie publicada")
    publicada = info["series"][0]
    _exigir(publicada["series_id"] == SERIE, "el identificador de la serie cambió")
    _exigir(publicada["status"] == "vigente", "la serie publicada no está vigente")
    _exigir(publicada["observations"], "la serie publicada no tiene observaciones")
    ultima = publicada["observations"][-1]
    _exigir(isinstance(ultima["value"], (int, float)), "el último valor no es numérico")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        copia = tmp_path / "copia"
        _copiar(copia)
        antes = _bytes(copia)

        roto = tmp_path / "roto"
        _copiar(roto)
        documento = _leer(roto)
        del documento["observations"][0]["value"]
        _guardar(roto, documento)
        try:
            validar(roto)
        except ValidacionError:
            pass
        else:
            raise SystemExit("una observación sin valor pasó la validación")
        _exigir(_bytes(copia) == antes, "validar una copia rota modificó la serie buena")

        cuerpo = tmp_path / "cuerpo"
        _copiar(cuerpo)
        raw = cuerpo / "raw" / f"{SERIE}.body"
        raw.write_bytes(raw.read_bytes() + b" ")
        try:
            validar(cuerpo)
        except ValidacionError:
            pass
        else:
            raise SystemExit("un cuerpo alterado pasó la validación")
        _exigir(_bytes(copia) == antes, "validar un cuerpo alterado modificó la serie buena")

        marcado = tmp_path / "marcado"
        _copiar(marcado)
        documento = _leer(marcado)
        documento["status"] = "no actualizado"
        documento["error"] = "Fuente no disponible: prueba"
        _guardar(marcado, documento)
        resultado = validar(marcado)
        _exigir(resultado["series"][0]["status"] == "no actualizado", "el esquema rechazó «no actualizado»")
        _exigir(_bytes(copia) == antes, "marcar una copia cambió la serie buena")

    print("ok: pruebas de validación")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
