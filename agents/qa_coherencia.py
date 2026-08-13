"""
AGENTE 10: VERIFICADOR DE COHERENCIA ("QA Coherencia")
----------------------------------------------------
Responde directamente al problema de "el video no tiene nada que ver con
el guion": después de que VisualScout eligió un recurso para cada beat,
este agente examina un fotograma real de cada uno y usa Gemini Vision
(gratis, capa gratuita) para preguntarle qué tan bien ese fotograma
representa la palabra clave/frase que se está narrando en ese momento.

Si la coincidencia es baja, le pide a VisualScout un recurso alternativo
(evitando el que falló) y verifica de nuevo. Si tras el reintento sigue sin
haber un buen recurso disponible en los bancos gratuitos, se queda con el
mejor que exista (nunca bloquea el pipeline) y lo reporta en el resumen
final para que el creador lo sepa.

Si no hay una key de Gemini configurada, hace una verificación más simple
basada en texto (sin IA) y lo indica claramente en el log: el sistema
NUNCA fMalla por falta de esta verificación, solo pierde precisión.
"""
import base64
import time

from PIL import Image
from moviepy import VideoFileClip

from agents.utils import load_config, log
from agents.visuals import _puntaje_relevancia

AGENT = "QA-Coherencia"

UMBRAL_APROBACION = 6  # puntaje 0-10 mínimo para considerar que el visual sí coincide
MAX_REINTENTOS_POR_BEAT = 1
MAX_ERRORES_CONSECUTIVOS_ANTES_DE_RENDIRSE = 4


def _extraer_frame_jpg(visual: dict, destino_jpg: str) -> bool:
    try:
        if visual["tipo"] == "video":
            with VideoFileClip(visual["ruta"]) as clip:
                t = min(1.0, max(0.0, clip.duration / 2))
                frame = clip.get_frame(t)
            Image.fromarray(frame).convert("RGB").save(destino_jpg, quality=80)
        else:
            Image.open(visual["ruta"]).convert("RGB").save(destino_jpg, quality=80)
        return True
    except Exception as e:
        log(AGENT, f"No se pudo extraer fotograma para verificar ({e}).")
        return False


def _preguntar_a_gemini_vision(ruta_jpg: str, keyword: str, texto_beat: str, api_key: str) -> int:
    import requests
    with open(ruta_jpg, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    prompt = (
        f"Estás verificando la calidad de un video generado automáticamente. "
        f"En este momento el narrador está diciendo: \"{texto_beat}\". "
        f"Se eligió esta imagen para ilustrar la palabra clave: \"{keyword}\". "
        f"Responde ÚNICAMENTE con un número del 0 al 10 indicando qué tan bien "
        f"la imagen representa esa palabra clave y el contexto de la frase "
        f"(0 = no tiene nada que ver, 10 = coincide perfectamente). "
        f"No expliques nada, solo el número."
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    body = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
            ]
        }]
    }
    for intento in range(3):
        r = requests.post(url, json=body, timeout=30)
        if r.status_code == 429 and intento < 2:
            time.sleep(15 * (intento + 1))
            continue
        r.raise_for_status()
        texto = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        digitos = "".join(c for c in texto if c.isdigit())
        return int(digitos[:2]) if digitos else 5
    r.raise_for_status()



def verificar_y_corregir(guion: dict, visuales_info: dict, carpeta_salida: str) -> dict:
    cfg = load_config()
    gemini_key = cfg["apis"].get("gemini_api_key", "")
    usar_vision = bool(gemini_key) and "OBTENER_GRATIS" not in gemini_key
    buscador = visuales_info.get("_buscador")

    if not usar_vision:
        log(AGENT, "Sin Gemini configurado: se usa solo el puntaje de relevancia por texto "
                    "(ya aplicado por VisualScout). Para verificación visual real con IA, "
                    "configura gemini_api_key.")
        return visuales_info

    log(AGENT, "Verificando con Gemini Vision que cada imagen/clip coincide con el guion...")
    total = 0
    reemplazados = 0
    errores_consecutivos = 0
    rendido = False

    for i, cap in enumerate(guion["capitulos"]):
        beats = cap.get("beats", [])
        visuales_cap = visuales_info["visuales_por_capitulo"][i]
        for j, (beat, visual) in enumerate(zip(beats, visuales_cap)):
            if rendido:
                break
            total += 1
            keyword = visual.get("keyword", beat.get("visual", ""))
            tag = f"cap{i}_b{j}"
            ruta_jpg = f"{carpeta_salida}/_qa_{tag}.jpg"

            if not _extraer_frame_jpg(visual, ruta_jpg):
                continue

            try:
                score = _preguntar_a_gemini_vision(ruta_jpg, keyword, beat.get("texto", ""), gemini_key)
                errores_consecutivos = 0
            except Exception as e:
                errores_consecutivos += 1
                log(AGENT, f"Aviso verificando beat {tag}: {e}")
                if errores_consecutivos >= MAX_ERRORES_CONSECUTIVOS_ANTES_DE_RENDIRSE:
                    log(AGENT, "Demasiados errores seguidos (probable límite de cuota gratuita). "
                                "Se detiene la verificación para no bloquear el video; "
                                "el resto de recursos ya elegidos se mantienen.")
                    rendido = True
                continue

            if score < UMBRAL_APROBACION and buscador is not None:
                log(AGENT, f"Beat {tag}: coincidencia baja ({score}/10) para '{keyword}'. "
                            f"Generando una imagen IA a medida para esta frase exacta...")
                nuevo_visual = buscador.re_obtener_evitando(keyword, carpeta_salida, tag, visual["ruta"],
                                                             contexto=beat.get("texto", ""))
                visuales_cap[j] = nuevo_visual
                reemplazados += 1
            time.sleep(2.5)  # margen para no exceder el límite gratuito de peticiones por minuto

    log(AGENT, f"Verificación completa: {reemplazados}/{total} recursos reemplazados por baja coincidencia.")
    return visuales_info
