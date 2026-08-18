"""
Utilidades compartidas por todos los agentes.
"""
import os
import yaml
import json
import re
import unicodedata

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:60] if text else "video"


def state_path():
    return os.path.join(BASE_DIR, "data", "estado.json")


def load_state():
    p = state_path()
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"ideas_usadas": [], "videos_publicados": [], "ultima_ejecucion": None}


def save_state(state):
    with open(state_path(), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def log(agent_name: str, msg: str):
    print(f"[{agent_name}] {msg}")


def limpiar_texto_para_voz(texto: str) -> str:
    """
    Red de seguridad para que el narrador NUNCA lea símbolos en voz alta.
    Elimina marcado tipo Markdown, marcas de tiempo, numerales de lista y
    cualquier símbolo que no sea letra/número/puntuación básica, incluso si
    el guion (por error del LLM) los incluyó.
    """
    if not texto:
        return texto
    t = texto
    # Marcas de tiempo tipo 0:45, 12:30, 1:02:33
    t = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", "", t)
    # Numerales de lista tipo "1)", "2.", "- ", "* "
    t = re.sub(r"(?m)^\s*[\-\*\u2022]\s+", "", t)
    t = re.sub(r"\b\d+\)\s+", "", t)
    # Markdown de énfasis
    t = t.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
    t = t.replace("#", "").replace("`", "")
    # EMOJIS (bug real oído el 18-ago-2026: la voz narró el título de un
    # Short con "😱 #Shorts" y edge-tts leyó el emoji y la almohadilla en
    # voz alta: "...cara de terror, almohadilla, shorts"). Se eliminan
    # todos los emojis y pictogramas del texto narrable.
    t = re.sub(r"[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
               r"\U00002190-\U000021FF\U00002B00-\U00002BFF\uFE0F]+", " ", t)
    # Guiones largos usados como pausas -> coma (para que no se lean como "guion")
    t = t.replace(" - ", ", ").replace("—", ",").replace("–", ",")
    # Colapsar espacios extra que hayan quedado
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t


def obtener_duracion_video(ruta_video: str):
    """Duración real (segundos) de un archivo de video ya renderizado,
    usando ffprobe (ya viene instalado junto a ffmpeg). Devuelve None si
    no se pudo determinar, nunca lanza excepción hacia arriba."""
    import subprocess
    try:
        resultado = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", ruta_video],
            capture_output=True, text=True, timeout=20,
        )
        return float(resultado.stdout.strip())
    except Exception:
        return None

