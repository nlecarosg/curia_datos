#!/usr/bin/env python3
"""Pruebas locales del validador y de la publicación.

No descarga nada. Usa la serie ya guardada y directorios temporales.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from publicar import publicar
from validar import ValidacionError, validar

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "datos" / "ine" / "ir2023"


def _exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise SystemExit(mensaje)


def _bytes(directorio: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directorio).as_posix(): path.read_bytes()
        for path in sorted(directorio.rglob("*"))
        if path.is_file()
    }


def _minimo(destino: Path, cuerpo: bytes, estado: str = "vigente") -> None:
    digest = hashlib.sha256(cuerpo).hexdigest()
    obs = {
        "valor": 1.5,
        "unidad": "índice (base promedio 2023=100)",
        "fuente": "prueba",
        "fecha_dato": "2024-01",
        "fecha_captura": "2026-10-23T00:00:00Z",
        "hash_crudo": f"sha256:{digest}",
        "estado": estado,
    }
    (destino / "crudo").mkdir(parents=True)
    (destino / "crudo" / digest).write_bytes(cuerpo)
    (destino / "serie.json").write_text(
        json.dumps([obs], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    captura = {
        "fecha_captura": obs["fecha_captura"],
        "hash_crudo": obs["hash_crudo"],
        "estado": estado,
        "observaciones": [obs],
    }
    (destino / "historial.jsonl").write_text(
        json.dumps(captura, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    info = validar(DATOS)
    _exigir(info["serie"], "la serie real está vacía")
    _exigir(all(obs["estado"] == "vigente" for obs in info["serie"]), "la carga inicial no está vigente")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        copia = tmp_path / "copia"
        shutil.copytree(DATOS, copia)
        antes = _bytes(copia)

        roto = tmp_path / "roto"
        shutil.copytree(DATOS, roto)
        serie = json.loads((roto / "serie.json").read_text(encoding="utf-8"))
        del serie[0]["valor"]
        (roto / "serie.json").write_text(json.dumps(serie), encoding="utf-8")
        try:
            validar(roto)
        except ValidacionError:
            pass
        else:
            raise SystemExit("una serie sin valor pasó la validación")
        _exigir(_bytes(copia) == antes, "validar un directorio roto modificó la copia buena")

        try:
            publicar(copia, roto)
        except ValidacionError:
            pass
        else:
            raise SystemExit("se publicó una salida inválida")
        _exigir(_bytes(copia) == antes, "una salida inválida modificó los datos publicados")

        _exigir(publicar(copia, DATOS) is False, "volvió a publicar el mismo cuerpo")
        _exigir(_bytes(copia) == antes, "publicar el mismo cuerpo reescribió archivos")

        nuevo = tmp_path / "nuevo"
        _minimo(nuevo, b"cuerpo-distinto\n", estado="no actualizado")
        # La serie de prueba no trae los meses reales: debe rechazarse.
        try:
            publicar(copia, nuevo)
        except ValidacionError:
            pass
        else:
            raise SystemExit("se aceptó una salida que borra observaciones")
        _exigir(_bytes(copia) == antes, "el rechazo por omisión modificó los datos")

        # Sobre un directorio mínimo, una segunda captura se agrega y la primera sigue.
        base = tmp_path / "base"
        _minimo(base, b"cuerpo-inicial\n")
        validar(base)
        segundo = tmp_path / "segundo"
        _minimo(segundo, b"cuerpo-siguiente\n")
        _exigir(publicar(base, segundo) is True, "no publicó un cuerpo nuevo")
        publicado = validar(base)
        _exigir(len(publicado["historial"]) == 2, "el historial no conservó la captura anterior")
        _exigir(len(publicado["hashes"]) == 2, "se borró el cuerpo crudo anterior")
        _exigir(publicado["serie"][0]["estado"] == "vigente", "la serie mínima perdió el estado")
        _exigir(publicado["historial"][0]["hash_crudo"] != publicado["historial"][1]["hash_crudo"], "las capturas quedaron iguales")

        estado = tmp_path / "estado"
        _minimo(estado, b"cuerpo-estado\n", estado="no actualizado")
        marcado = validar(estado)
        _exigir(marcado["serie"][0]["estado"] == "no actualizado", "el esquema rechazó «no actualizado»")

    print("ok: pruebas de validación y de publicación")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
