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
        # Arsenal de respaldo (investigación 19-ago-2026): proveedores
        # gratuitos adicionales para que ningún fallo de Groq/Gemini vuelva
        # a dejar al sistema sin cerebro. Si el secreto no existe en GitHub,
        # simplemente se ignora (no rompe nada).
        "cerebras_api_key": "CEREBRAS_API_KEY",
        "mistral_api_key": "MISTRAL_API_KEY",
        "openrouter_api_key": "OPENROUTER_API_KEY",
        "cloudflare_api_token": "CLOUDFLARE_API_TOKEN",
        "cloudflare_account_id": "CLOUDFLARE_ACCOUNT_ID",
        "nvidia_api_key": "NVIDIA_API_KEY",
        "deepseek_api_key": "DEEPSEEK_API_KEY",
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
