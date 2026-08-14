"""
AGENTE 19: DOBLAJE DE AUDIO ("DoblajeAudio")
----------------------------------------------------
Prepara un archivo de audio DOBLADO (narración completa traducida) listo
para subir como "pista de audio adicional" (Multi-Language Audio Track) en
YouTube Studio -> [tu video] -> Idiomas. YouTube confirmado NO tiene
endpoint público en su API para subir esa pista de audio todavía (a
diferencia del título/descripción, que sí se puede vía API -- ver
agents/seo_multilingue.py). Por eso este agente deja el trabajo pesado
100% listo, y solo falta que subas el archivo con un par de clics.

Qué hace, en orden:
 1) Traduce el guion COMPLETO (gancho + todos los beats) al idioma pedido,
    con un tono natural para narrar (no traducción literal), sin tocar
    cifras, porcentajes ni nombres propios de estudios/revistas.
 2) Genera la narración doblada gratis con edge-tts.
 3) Mide cuánto duró y AJUSTA el ritmo de la voz (más rápido o más lento)
    para que la duración final quede lo más cercana posible a la duración
    real del video ya publicado -- así no se desincroniza en el reproductor
    cuando alguien elige ese idioma.
 4) Deja el .mp3 final + el título/descripción también traducidos (para
    pegarlos en el mismo formulario de YouTube Studio) en una carpeta de
    salida que queda disponible para descargar.
"""
import asyncio
import os

import edge_tts
import requests
from mutagen.mp3 import MP3

from agents.utils import load_config, log

AGENT = "DoblajeAudio"

# Voces neuronales gratuitas (edge-tts) recomendadas por idioma. Puedes
# agregar más códigos de idioma aquí si algún día quieres otro.
VOCES_POR_IDIOMA = {
    "en": "en-US-GuyNeural",
    "de": "de-DE-ConradNeural",
    "ko": "ko-KR-InJoonNeural",
    "da": "da-DK-JeppeNeural",
    "fr": "fr-FR-HenriNeural",
    "pt": "pt-BR-AntonioNeural",
}

LIMITE_AJUSTE_RITMO_PCT = 30  # no forzar la voz más allá de esto (sonaría robótico)


def _texto_completo_narrable(guion: dict) -> str:
    partes = [guion.get("gancho", "")]
    for cap in guion.get("capitulos", []):
        for beat in cap.get("beats", []):
            partes.append(beat.get("texto", ""))
    return " ".join(p for p in partes if p).strip()


def _traducir_guion_completo(texto: str, idioma_destino: str, gemini_key: str) -> str:
    prompt = (
        f"Traduce el siguiente guion narrado de un video de YouTube de salud al idioma "
        f"con código de idioma '{idioma_destino}'. Usa un tono natural y cálido, pensado "
        f"para ser LEÍDO EN VOZ ALTA (nunca una traducción literal palabra por palabra). "
        f"NO traduzcas cifras, porcentajes, ni nombres propios de estudios o revistas "
        f"científicas: déjalos exactamente igual. El resultado debe ser SOLO texto plano "
        f"narrable (sin asteriscos, sin símbolos markdown, sin numerales de lista). "
        f"Devuelve ÚNICAMENTE el texto traducido, sin comillas ni explicaciones "
        f"adicionales.\n\nGuion original en español:\n{texto}"
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    r = requests.post(url, json=body, timeout=60)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _sintetizar(texto: str, voz: str, salida_mp3: str, rate: str = "+0%"):
    com = edge_tts.Communicate(texto, voice=voz, rate=rate)
    await com.save(salida_mp3)


def _duracion_mp3(ruta: str):
    try:
        return MP3(ruta).info.length
    except Exception:
        return None


def generar_doblaje(guion: dict, duracion_objetivo_seg: float, carpeta_salida: str,
                     nombre_base: str, idioma_destino: str = "en") -> dict:
    """Devuelve {"audio": ruta_mp3, "titulo": ..., "descripcion": ...} o
    None si no se pudo generar (nunca lanza excepción hacia arriba)."""
    cfg = load_config()
    gemini_key = cfg["apis"].get("gemini_api_key", "")
    if not gemini_key or "OBTENER_GRATIS" in gemini_key:
        log(AGENT, "Sin Gemini configurado: no se puede generar el doblaje.")
        return None

    voz = VOCES_POR_IDIOMA.get(idioma_destino, "en-US-GuyNeural")
    os.makedirs(carpeta_salida, exist_ok=True)

    try:
        texto_original = _texto_completo_narrable(guion)
        texto_traducido = _traducir_guion_completo(texto_original, idioma_destino, gemini_key)
    except Exception as e:
        log(AGENT, f"Aviso: no se pudo traducir el guion para el doblaje ({e}).")
        return None

    ruta_prueba = os.path.join(carpeta_salida, f"{nombre_base}_{idioma_destino}_prueba.mp3")
    try:
        asyncio.run(_sintetizar(texto_traducido, voz, ruta_prueba, rate="+0%"))
    except Exception as e:
        log(AGENT, f"Aviso: no se pudo generar el audio del doblaje ({e}).")
        return None

    duracion_prueba = _duracion_mp3(ruta_prueba)
    ruta_final = os.path.join(carpeta_salida, f"{nombre_base}_doblaje_{idioma_destino}.mp3")

    if duracion_prueba and duracion_objetivo_seg:
        # Ajustamos el ritmo de la voz para que la duración total quede lo
        # más cerca posible del video real (evita que se desincronice en
        # el reproductor cuando alguien elija este idioma).
        factor = duracion_prueba / duracion_objetivo_seg
        cambio_pct = max(-LIMITE_AJUSTE_RITMO_PCT, min(LIMITE_AJUSTE_RITMO_PCT, (factor - 1) * 100))
        rate_ajustado = f"{'+' if cambio_pct >= 0 else ''}{cambio_pct:.0f}%"
        try:
            asyncio.run(_sintetizar(texto_traducido, voz, ruta_final, rate=rate_ajustado))
            duracion_final = _duracion_mp3(ruta_final)
            log(AGENT, f"Doblaje ajustado (ritmo {rate_ajustado}): {duracion_final:.1f}s "
                        f"lograda vs {duracion_objetivo_seg:.1f}s del video original.")
        except Exception as e:
            log(AGENT, f"Aviso ajustando el ritmo del doblaje ({e}); se usa la versión sin ajustar.")
            os.replace(ruta_prueba, ruta_final)
    else:
        os.replace(ruta_prueba, ruta_final)

    if os.path.exists(ruta_prueba):
        try:
            os.remove(ruta_prueba)
        except OSError:
            pass

    try:
        from agents.seo_multilingue import _traducir_con_gemini
        traduccion_meta = _traducir_con_gemini(
            guion.get("titulo", ""), guion.get("descripcion", ""), idioma_destino, gemini_key)
    except Exception as e:
        log(AGENT, f"Aviso: no se pudo traducir título/descripción para el doblaje ({e}).")
        traduccion_meta = {"title": "", "description": ""}

    log(AGENT, f"Doblaje en '{idioma_destino}' listo para subir: {ruta_final}")
    return {"audio": ruta_final, "titulo": traduccion_meta.get("title", ""),
            "descripcion": traduccion_meta.get("description", "")}


def escribir_instrucciones(ruta_txt: str, idioma_destino: str, titulo_traducido: str,
                            descripcion_traducida: str, nombre_audio: str) -> None:
    """Deja un archivo de texto explicando EXACTAMENTE cómo subir el
    doblaje a mano en YouTube Studio (el único paso que la API no permite
    automatizar todavía)."""
    contenido = f"""CÓMO SUBIR ESTE DOBLAJE A YOUTUBE (2-3 minutos)
================================================

1) Ve a YouTube Studio -> Contenido -> abre este video -> pestaña "Detalles".
2) Busca la sección "Idiomas" (o "Traducciones"). Si no la ves, busca el
   ícono de un globo terráqueo cerca del título/descripción.
3) Click en "Agregar idioma" -> elige el idioma con código '{idioma_destino}'.
4) En el campo de AUDIO / DOBLAJE de esa sección, sube el archivo:
   {nombre_audio}
5) En los campos de título y descripción de ese mismo idioma, pega esto:

   TÍTULO ({idioma_destino}):
   {titulo_traducido}

   DESCRIPCIÓN ({idioma_destino}):
   {descripcion_traducida}

6) Guarda / Publica esa sección. Listo: los espectadores que vean el video
   en ese idioma van a poder elegir escucharlo con esta voz doblada.
"""
    with open(ruta_txt, "w", encoding="utf-8") as f:
        f.write(contenido)
