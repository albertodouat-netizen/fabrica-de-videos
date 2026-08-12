#!/usr/bin/env python3
"""
Script usado por el workflow de GitHub Actions (.github/workflows/fabrica_videos.yml)
para inyectar las llaves gratuitas guardadas como "Secrets" de GitHub dentro de
config/config.yaml justo antes de cada corrida. Así el archivo que vive en el
repositorio NUNCA contiene una llave real (siempre placeholders), y las llaves
de verdad solo existen en la memoria de esa ejecución puntual.
"""
import os
import yaml

RUTA_CONFIG = "config/config.yaml"


def main():
    with open(RUTA_CONFIG, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    mapeo = {
        "youtube_api_key": "YOUTUBE_API_KEY",
        "gemini_api_key": "GEMINI_API_KEY",
        "groq_api_key": "GROQ_API_KEY",
        "pexels_api_key": "PEXELS_API_KEY",
        "pixabay_api_key": "PIXABAY_API_KEY",
        "jamendo_client_id": "JAMENDO_CLIENT_ID",
    }

    for clave_config, nombre_env in mapeo.items():
        valor = os.environ.get(nombre_env)
        if valor:
            cfg["apis"][clave_config] = valor

    with open(RUTA_CONFIG, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)

    print("Configuración actualizada con los secretos disponibles en este workflow.")


if __name__ == "__main__":
    main()
