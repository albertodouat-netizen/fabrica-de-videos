"""
AGENTE 18: SEO MULTILINGÜE ("SeoMultilingue")
----------------------------------------------------
Aplica una recomendación real y verificada (investigada a partir de la
entrevista a Iván Marquina + documentación oficial de YouTube): un mismo
video puede tener título y descripción TRADUCIDOS para otros idiomas
("localizations"), lo que lo hace más fácil de encontrar para audiencias
que buscan en otro idioma -- sin necesidad de subir un video aparte ni de
doblar el audio. Es 100% gratis vía la propia YouTube Data API
(videos.update), ya autorizada con las mismas credenciales que usamos
para publicar.

Esto es distinto y más simple que el doblaje completo de audio (que si se
hace, sí requiere subir el archivo de audio a mano en YouTube Studio,
porque la API pública no tiene un endpoint para eso todavía) -- aquí solo
tocamos texto (título/descripción), que la API sí permite 100% programado.
"""
import re

import googleapiclient.discovery
import requests

from agents.utils import load_config, log
from agents.publisher import _obtener_credenciales

AGENT = "SeoMultilingue"


def _traducir_con_gemini(titulo: str, descripcion: str, idioma_destino: str, gemini_key: str) -> dict:
    """Traduce título y descripción con Gemini, manteniendo el formato del
    índice de capítulos (los timestamps NO se traducen, son números)."""
    prompt = (
        f"Traduce el siguiente título y descripción de un video de YouTube sobre salud "
        f"natural al idioma con código '{idioma_destino}'. Mantén el tono natural y "
        f"atractivo (no traducción literal palabra por palabra). NO traduzcas números, "
        f"marcas de tiempo (como 00:00), URLs, ni nombres propios de estudios/revistas "
        f"científicas. Devuelve ÚNICAMENTE un JSON con esta forma exacta, sin texto "
        f"adicional:\n"
        f'{{"titulo": "...", "descripcion": "..."}}\n\n'
        f"Título original: {titulo}\n\n"
        f"Descripción original:\n{descripcion}"
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={gemini_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    r = requests.post(url, json=body, timeout=45)
    r.raise_for_status()
    texto = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    import json
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    datos = json.loads(match.group(0))
    # OJO: YouTube exige que las llaves de "localizations" sean literalmente
    # "title" y "description" (en inglés), sin importar el idioma del
    # contenido. Usar "titulo"/"descripcion" aquí (como en el resto de nuestro
    # código en español) rompe la actualización con un error confuso.
    return {"title": datos["titulo"][:100], "description": datos["descripcion"][:5000]}


def agregar_titulos_traducidos(video_id: str, titulo: str, descripcion: str, idiomas: list) -> None:
    """Agrega título/descripción traducidos al MISMO video (no crea videos
    nuevos), uno por cada código de idioma en 'idiomas' (ej: ['en', 'de']).
    Nunca bloquea el pipeline si algo falla."""
    cfg = load_config()
    gemini_key = cfg["apis"].get("gemini_api_key", "")
    if not gemini_key or "OBTENER_GRATIS" in gemini_key:
        log(AGENT, "Sin Gemini configurado: no se pueden generar traducciones. Se omite este paso.")
        return

    try:
        creds = _obtener_credenciales(cfg)
        youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        actual = youtube.videos().list(part="localizations,snippet", id=video_id).execute()
        items = actual.get("items", [])
        if not items:
            log(AGENT, f"No se encontró el video {video_id} para agregar traducciones.")
            return
        localizations = items[0].get("localizations", {}) or {}
        snippet_original = items[0]["snippet"]
        idioma_original = snippet_original.get("defaultLanguage") or "es"
        # YouTube a veces autogenera una entrada de 'localizations' para el
        # propio idioma original del video (ej. "es"), duplicando el
        # snippet principal. Si se reenvía tal cual, la API responde con el
        # confuso error "invalidVideoMetadata". La quitamos antes de tocar
        # nada: el idioma original ya se maneja por 'snippet', no hace
        # falta que también esté en 'localizations'.
        localizations.pop(idioma_original, None)
        # IMPORTANTE: no reenviamos el snippet completo tal cual lo devuelve
        # la API (causa el error "invalidVideoMetadata" porque incluye campos
        # de solo lectura como defaultAudioLanguage). Construimos uno limpio
        # solo con los campos que sí se pueden actualizar.
        snippet_limpio = {
            "title": snippet_original.get("title", ""),
            "description": snippet_original.get("description", ""),
            "categoryId": snippet_original.get("categoryId", "22"),
            "tags": snippet_original.get("tags") or [],
            "defaultLanguage": snippet_original.get("defaultLanguage") or "es",
        }
    except Exception as e:
        log(AGENT, f"Aviso: no se pudo leer el video {video_id} para traducir ({e}).")
        return

    for idioma in idiomas:
        try:
            traduccion = _traducir_con_gemini(titulo, descripcion, idioma, gemini_key)
            localizations[idioma] = traduccion
            log(AGENT, f"Traducción generada para '{idioma}': {traduccion['title']}")
        except Exception as e:
            log(AGENT, f"Aviso: no se pudo traducir a '{idioma}' ({e}); se omite ese idioma.")

    try:
        youtube.videos().update(
            part="localizations,snippet",
            body={
                "id": video_id,
                "snippet": snippet_limpio,
                "localizations": localizations,
            },
        ).execute()
        log(AGENT, f"Títulos/descripciones traducidos guardados en el video {video_id} "
                    f"({list(localizations.keys())}).")
    except Exception as e:
        log(AGENT, f"Aviso: no se pudieron guardar las traducciones en YouTube ({e}).")
