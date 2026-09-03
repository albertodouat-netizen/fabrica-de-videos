#!/usr/bin/env python3
"""
Verificador final de corrida (02-sep-2026).

Problema real corregido: GitHub Actions podía quedar en verde aunque el
orquestador hubiera abortado temprano o no hubiera publicado nada útil.
Este script lee output/resultado_corrida.json y falla el job si no existe
la evidencia mínima esperada para ese modo de ejecución.
"""
import argparse
import json
import os
import sys

RUTA = os.path.join("output", "resultado_corrida.json")


def _cargar():
    if not os.path.exists(RUTA):
        raise FileNotFoundError(f"No existe {RUTA}")
    with open(RUTA, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=["largo", "short-independiente", "short-pendiente"], required=True)
    args = ap.parse_args()

    try:
        data = _cargar()
    except Exception as e:
        print(f"❌ Verificación final falló: no se pudo leer {RUTA} ({e}).")
        return 1

    print(json.dumps(data, ensure_ascii=False, indent=2))

    if args.modo == "largo":
        if data.get("modo") != "largo":
            print("❌ El resultado de corrida no corresponde al modo 'largo'.")
            return 1
        if data.get("status") != "ok":
            print("❌ La corrida de largo NO terminó en estado 'ok'.")
            return 1
        if not data.get("ruta_video"):
            print("❌ Falta ruta_video en el resultado de la corrida larga.")
            return 1
        if data.get("intentar_publicar", True) and not data.get("video_id"):
            print("❌ La corrida larga debía publicar, pero no devolvió video_id.")
            return 1
        if data.get("generar_short", True) and not data.get("ruta_short"):
            print("❌ La corrida larga debía generar Short, pero no dejó ruta_short.")
            return 1
        if data.get("intentar_publicar", True) and data.get("generar_short", True) and not data.get("short_id"):
            print("❌ La corrida larga debía publicar el Short derivado, pero no devolvió short_id.")
            return 1
        print("✅ Verificación final OK: hubo largo y Short con evidencia mínima.")
        return 0

    if args.modo == "short-pendiente":
        if data.get("modo") != "short_pendiente":
            print("❌ El resultado de corrida no corresponde al modo 'short_pendiente'.")
            return 1
        if data.get("status") == "sin_pendientes":
            print("✅ Verificación final OK: no había ningún Short pendiente por recuperar.")
            return 0
        if data.get("status") != "ok":
            print("❌ La corrida de Short pendiente NO terminó en estado 'ok'.")
            return 1
        if not data.get("video_id"):
            print("❌ El Short pendiente no indica a qué video largo quedó vinculado.")
            return 1
        if not data.get("short_id"):
            print("❌ El Short pendiente no devolvió short_id.")
            return 1
        print("✅ Verificación final OK: el Short pendiente quedó recuperado con evidencia mínima.")
        return 0

    if data.get("modo") != "short_independiente":
        print("❌ El resultado de corrida no corresponde al modo 'short_independiente'.")
        return 1
    if data.get("status") == "ya_publicado_hoy":
        print("✅ Verificación final OK: el Short independiente ya se había publicado hoy.")
        return 0
    if data.get("status") != "ok":
        print("❌ La corrida de Short independiente NO terminó en estado 'ok'.")
        return 1
    if not data.get("short_id"):
        print("❌ El Short independiente no devolvió short_id.")
        return 1
    print("✅ Verificación final OK: hubo Short independiente con evidencia mínima.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
