"""
Control de calidad de idioma visible al espectador.

Meta del usuario (03-sep-2026): que el canal NO mezcle español con inglés en
ningún texto humano-visible:
- títulos
- descripciones
- texto de portadas / covers

La única excepción deliberada sigue siendo el campo interno `visual`, porque
ese texto nunca lo ve el espectador y los bancos de imágenes responden mejor
en inglés.
"""

import re

# Solo palabras/frases CLARAMENTE inglesas. Evitamos falsos positivos con
# cognados válidos en español como "natural" o "real".
_PATRONES_INGLES_VISIBLES = [
    (r"\balways\b", "always"),
    (r"\bwaking\b", "waking"),
    (r"\bsleep\b", "sleep"),
    (r"\bfall\s+back\b", "fall back"),
    (r"\bsenior\s+health\s+tips\b", "senior health tips"),
    (r"\bdoctors?\s+won'?t\s+tell\s+you\b", "doctors won't tell you"),
    (r"\bmorning\s+habits?\b", "morning habits"),
    (r"\bgut\s+health\b", "gut health"),
    (r"\bwhole\s+body\b", "whole body"),
    (r"\bblood\s+flow\b", "blood flow"),
    (r"\blower(?:s|ing)?\b", "lower"),
    (r"\bboost(?:s|ing)?\b", "boost"),
    (r"\bfixed\b", "fixed"),
    (r"\bhub\b", "hub"),
    (r"\bstress\b", "stress"),
    (r"\bsound(?:s)?\b", "sound"),
    (r"\bmusic\b", "music"),
    (r"\bfrequency\b", "frequency"),
    (r"\bfrequencies\b", "frequencies"),
    (r"\bnight\b", "night"),
    (r"\bback\s+asleep\b", "back asleep"),
    (r"\bresearch\b", "research"),
    (r"\bbenefits\b", "benefits"),
]

_REEMPLAZOS_PORTADA = {
    "STOP": "ALTO",
    "BEFORE": "ANTES",
    "AFTER": "DESPUÉS",
    "SLEEP": "DORMIR",
    "STRESS": "ESTRÉS",
    "MUSIC": "MÚSICA",
    "SOUND": "SONIDO",
    "SOUNDS": "SONIDOS",
    "FREQUENCY": "FRECUENCIA",
    "FREQUENCIES": "FRECUENCIAS",
    "BOOST": "MEJORA",
    "LOWER": "BAJA",
    "BODY": "CUERPO",
}


def _limpiar_para_revision(texto: str) -> str:
    texto = texto or ""
    texto = re.sub(r"https?://\S+", " ", texto)
    texto = re.sub(r"www\.\S+", " ", texto)
    texto = re.sub(r"#[0-9A-Za-zÁÉÍÓÚÑáéíóúñ_]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def detectar_hallazgos_ingles_visible(texto: str) -> list[str]:
    limpio = _limpiar_para_revision(texto)
    hallazgos = []
    for patron, etiqueta in _PATRONES_INGLES_VISIBLES:
        if re.search(patron, limpio, re.IGNORECASE):
            hallazgos.append(etiqueta)
    return hallazgos


def tiene_ingles_visible(texto: str) -> bool:
    return bool(detectar_hallazgos_ingles_visible(texto))



def filtrar_sugerencias_espanol(sugerencias: list[str]) -> list[str]:
    limpias = []
    for s in sugerencias or []:
        s = (s or "").strip()
        if not s:
            continue
        if tiene_ingles_visible(s):
            continue
        limpias.append(s)
    return limpias



def normalizar_linea_portada(linea: str) -> str:
    linea = re.sub(r"\s+", " ", (linea or "").upper()).strip(" -_.,:;!¡¿?")
    for en, es in _REEMPLAZOS_PORTADA.items():
        linea = re.sub(rf"\b{re.escape(en)}\b", es, linea)
    linea = re.sub(r"\s+", " ", linea).strip()
    return linea



def normalizar_lineas_portada(lineas: list[str]) -> list[str]:
    limpias = []
    for linea in lineas or []:
        ln = normalizar_linea_portada(linea)
        if not ln:
            continue
        if tiene_ingles_visible(ln):
            continue
        limpias.append(ln)
    return limpias
