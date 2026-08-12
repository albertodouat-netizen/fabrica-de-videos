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
    # Guiones largos usados como pausas -> coma (para que no se lean como "guion")
    t = t.replace(" - ", ", ").replace("—", ",").replace("–", ",")
    # Colapsar espacios extra que hayan quedado
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t

