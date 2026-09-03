#!/usr/bin/env python3
"""Detecta si hay un Short derivado pendiente por recuperar.

Usado por GitHub Actions en los días sin video largo: si existe un largo ya
publicado sin su Short derivado, el workflow debe intentar ese rescate ANTES
que publicar un Short independiente no relacionado.
"""
import json
import os

RUTA_ESTADO = os.path.join("data", "estado.json")


def _cargar_estado() -> dict:
    if not os.path.exists(RUTA_ESTADO):
        return {}
    with open(RUTA_ESTADO, encoding="utf-8") as f:
        return json.load(f)


def _pendientes_explicitos(estado: dict) -> list:
    pendientes = estado.get("shorts_derivados_pendientes")
    if isinstance(pendientes, list):
        return [p for p in pendientes if isinstance(p, dict) and p.get("video_id")]
    uno = estado.get("short_derivado_pendiente")
    if isinstance(uno, dict) and uno.get("video_id"):
        return [uno]
    return []


def _video_ya_tiene_short(estado: dict, video_id: str) -> bool:
    for v in estado.get("videos_publicados", []) or []:
        if isinstance(v, dict) and v.get("video_id") == video_id and v.get("short_id"):
            return True
    return False


def _ultimo_largo_sin_short(estado: dict):
    videos = estado.get("videos_publicados", []) or []
    for v in reversed(videos):
        if isinstance(v, dict) and v.get("video_id") and not v.get("short_id"):
            return v
    return None


def _set_output(nombre: str, valor: str):
    ruta = os.environ.get("GITHUB_OUTPUT")
    if not ruta:
        return
    with open(ruta, "a", encoding="utf-8") as f:
        f.write(f"{nombre}={valor}\n")


def main() -> int:
    estado = _cargar_estado()
    pendientes = _pendientes_explicitos(estado)
    pendientes = [p for p in pendientes if not _video_ya_tiene_short(estado, str(p.get("video_id", "")))]
    if pendientes:
        p = sorted(pendientes, key=lambda x: x.get("fecha_largo") or x.get("fecha_ultima_actualizacion") or "")[0]
        print(f"✅ Hay Short pendiente explícito para el largo: {p.get('titulo_largo', '')}")
        print(json.dumps(p, ensure_ascii=False, indent=2))
        _set_output("hay_pendiente", "true")
        _set_output("video_id", str(p.get("video_id", "")))
        return 0

    huerfano = _ultimo_largo_sin_short(estado)
    if huerfano:
        print(f"✅ Hay largo publicado sin short_id: {huerfano.get('titulo', '')}")
        print(json.dumps(huerfano, ensure_ascii=False, indent=2))
        _set_output("hay_pendiente", "true")
        _set_output("video_id", str(huerfano.get("video_id", "")))
        return 0

    print("ℹ️ No hay ningún Short derivado pendiente.")
    _set_output("hay_pendiente", "false")
    _set_output("video_id", "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
