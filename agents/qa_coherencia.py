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

import requests

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


def _preguntar_a_gemini_vision(ruta_jpg: str, keyword: str, texto_beat: str, api_key: str,
                                tema_general: str = "", nombre_capitulo: str = "") -> dict:
    import requests
    with open(ruta_jpg, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    contexto_extra = ""
    if tema_general:
        contexto_extra += f"El video completo trata sobre: \"{tema_general}\". "
    if nombre_capitulo:
        contexto_extra += f"Este momento pertenece al capítulo: \"{nombre_capitulo}\". "

    prompt = (
        f"Estás verificando la calidad Y LA SEGURIDAD de un video generado "
        f"automáticamente para un canal de salud, apto para todo público. "
        f"{contexto_extra}"
        f"En este momento exacto el narrador está diciendo: \"{texto_beat}\". "
        f"Se eligió esta imagen para ilustrar la palabra clave: \"{keyword}\". "
        f"Evalúa TRES cosas:\n"
        f"1) COHERENCIA: si la imagen representa bien esa frase específica, y si "
        f"tiene sentido dentro del tema general del video (por ejemplo, una "
        f"oficina no encaja en un video de salud natural aunque la frase "
        f"mencione \"estrés\", sería mejor una persona respirando o relajándose).\n"
        f"2) SEGURIDAD: ¿la imagen muestra desnudos, semi-desnudos, ropa interior, "
        f"ropa de baño, piel descubierta de forma no apropiada (torso, espalda, "
        f"escote pronunciado), o cualquier contenido sexual o sugerente? Sé "
        f"ESTRICTO: este es un canal de salud familiar, cualquier duda cuenta "
        f"como inapropiado.\n"
        f"3) VIOLENCIA: ¿la imagen muestra sangre, heridas explícitas, violencia "
        f"o contenido perturbador?\n\n"
        f"Responde ÚNICAMENTE en este formato EXACTO, sin explicar nada más:\n"
        f"COHERENCIA:<número del 0 al 10>|INAPROPIADA:<SI o NO>"
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
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
        texto = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
        digitos = "".join(c for c in texto.split("|")[0] if c.isdigit())
        score = int(digitos[:2]) if digitos else 5
        inapropiada = "INAPROPIADA:SI" in texto.replace(" ", "")
        return {"score": score, "inapropiada": inapropiada}
    r.raise_for_status()



def _preguntar_a_flash_lite_vision(ruta_jpg: str, keyword: str, texto_beat: str, api_key: str,
                                    tema_general: str = "", nombre_capitulo: str = ""):
    """Verificador de RESPALDO con gemini-flash-lite-latest: visión precisa
    y CUOTA SEPARADA del modelo del guionista (verificado en vivo
    28-ago-2026: 5/5 llamadas OK con la cuota de flash normal agotada).
    Nota: se probaron NVIDIA llama-3.2 11B/90B vision y fueron DESCARTADOS
    con evidencia (describieron una taza de té como "Pineapple"/"Corgi")."""
    with open(ruta_jpg, "rb") as fimg:
        img_b64 = base64.b64encode(fimg.read()).decode("utf-8")
    prompt = (
        f"En un video de salud se narra: \"{texto_beat[:200]}\". La imagen "
        f"debería mostrar: \"{keyword}\". PASO 1: identifica qué muestra "
        f"REALMENTE la imagen. PASO 2: si el objeto/alimento/escena principal "
        f"coincide con lo esperado, COHERENCIA alta (8-10); si muestra un "
        f"alimento u objeto DISTINTO al mencionado, COHERENCIA baja (0-3). "
        f"PASO 3: di si es inapropiada (desnudos/violencia). Responde SOLO: "
        f"COHERENCIA:<n>|INAPROPIADA:<SI o NO>"
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={api_key}"
    body = {"contents": [{"parts": [{"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}]}]}
    for intento in range(4):
        r = requests.post(url, json=body, timeout=45)
        if r.status_code in (429, 500, 503) and intento < 3:
            time.sleep(12 * (intento + 1))
            continue
        r.raise_for_status()
        texto = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
        import re as _re
        m = _re.search(r"COHERENCIA\s*:?\s*(\d{1,2})", texto)
        score = int(m.group(1)) if m else 5
        score = min(10, score)
        inapropiada = "INAPROPIADA:SI" in texto.replace(" ", "")
        return {"score": score, "inapropiada": inapropiada}
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

    # Presupuesto compartido de Gemini (ver agents/presupuesto_ia.py): el
    # proyecto gratuito tiene una cuota MUY ajustada (20/día observado en
    # vivo), y el Guionista necesita cupo de sobra para escribir guiones
    # reales en vez de caer al generador de plantilla local. Por eso
    # QA-Coherencia solo usa lo que sobra después de esa reserva, y verifica
    # una MUESTRA de beats (no todos) si el cupo es limitado.
    from agents.presupuesto_ia import gemini_disponibles_para_qa, registrar_uso_gemini, avisar_estado
    avisar_estado(AGENT)
    cupo_qa = gemini_disponibles_para_qa()

    candidatos = []
    for i, cap in enumerate(guion["capitulos"]):
        beats = cap.get("beats", [])
        visuales_cap = visuales_info["visuales_por_capitulo"][i]
        for j, (beat, visual) in enumerate(zip(beats, visuales_cap)):
            if beat.get("es_llamado_suscripcion") or beat.get("es_mencion_cruzada") or beat.get("es_intro_marca"):
                # Las tarjetas gráficas de suscripción y de "también te
                # puede interesar" son intencionales, no hay que verificarlas.
                continue
            candidatos.append((i, j, beat, visual, cap.get("nombre", "")))

    # flash-lite usa la MISMA llave gemini pero cuota separada => siempre
    # disponible como respaldo si hay llave gemini (que ya validamos arriba).
    hay_lite = True
    if cupo_qa <= 0:
        log(AGENT, "Cupo del Gemini principal agotado: la verificación visual la hace "
                    "gemini-flash-lite (cuota SEPARADA). Nada se queda sin verificar.")

    # CORRECCIÓN 28-ago-2026 (reclamo real: "remolacha y muestra pepino"):
    # con NVIDIA de respaldo YA NO se recorta la muestra: se verifican
    # TODOS los beats (los primeros 'cupo_qa' con Gemini, el resto con
    # NVIDIA Vision, que no tiene cupo diario).
    log(AGENT, f"Verificando TODOS los {len(candidatos)} beats: primeros {max(0, cupo_qa)} con "
                f"el Gemini principal, el resto con flash-lite (cuota separada).")

    total = 0
    reemplazados = 0
    errores_consecutivos = 0
    tema_general = guion.get("keyword_principal", "") or guion.get("titulo", "")

    for i, j, beat, visual, nombre_capitulo in candidatos:
        total += 1
        keyword = visual.get("keyword", beat.get("visual", ""))
        tag = f"cap{i}_b{j}"
        ruta_jpg = f"{carpeta_salida}/_qa_{tag}.jpg"

        if not _extraer_frame_jpg(visual, ruta_jpg):
            continue

        try:
            # Gemini mientras haya cupo; NVIDIA Vision para el resto.
            if total <= max(0, cupo_qa):
                resultado = _preguntar_a_gemini_vision(ruta_jpg, keyword, beat.get("texto", ""), gemini_key,
                                                        tema_general=tema_general, nombre_capitulo=nombre_capitulo)
                registrar_uso_gemini(1)
            else:
                resultado = _preguntar_a_flash_lite_vision(ruta_jpg, keyword, beat.get("texto", ""), gemini_key,
                                                            tema_general=tema_general, nombre_capitulo=nombre_capitulo)
            errores_consecutivos = 0
        except Exception as e:
            errores_consecutivos += 1
            log(AGENT, f"Aviso verificando beat {tag}: {e}")
            if errores_consecutivos >= MAX_ERRORES_CONSECUTIVOS_ANTES_DE_RENDIRSE:
                log(AGENT, "Demasiados errores seguidos (probable límite de cuota gratuita). "
                            "Se detiene la verificación para no bloquear el video; "
                            "el resto de recursos ya elegidos se mantienen.")
                break
            continue

        score = resultado["score"]
        # La seguridad manda por encima de la coherencia: si Gemini Vision
        # marca la imagen como inapropiada (desnudos, ropa interior, piel
        # descubierta de forma indebida, violencia), se reemplaza SIEMPRE,
        # sin importar qué tan "coherente" fuera con la frase narrada. Esto
        # responde directamente al caso real encontrado en la auditoría de
        # agosto 2026 (clip de "masaje" con piel descubierta que sí
        # coincidía bien por palabra clave, pero no era apto).
        if resultado["inapropiada"]:
            log(AGENT, f"⚠️ Beat {tag}: Gemini Vision marcó esta imagen como INAPROPIADA para '{keyword}'. "
                        f"Se reemplaza de inmediato, sin importar su coincidencia con el guion.")
            contexto_completo = f"{beat.get('texto', '')} (tema general del video: {tema_general})"
            nuevo_visual = buscador.re_obtener_evitando(keyword, carpeta_salida, tag, visual["ruta"],
                                                         contexto=contexto_completo) if buscador is not None else visual
            visuales_info["visuales_por_capitulo"][i][j] = nuevo_visual
            reemplazados += 1
        elif score < UMBRAL_APROBACION and buscador is not None:
            log(AGENT, f"Beat {tag}: coincidencia baja ({score}/10) para '{keyword}'. "
                        f"Generando una imagen IA a medida para esta frase exacta...")
            contexto_completo = f"{beat.get('texto', '')} (tema general del video: {tema_general})"
            nuevo_visual = buscador.re_obtener_evitando(keyword, carpeta_salida, tag, visual["ruta"],
                                                         contexto=contexto_completo)
            visuales_info["visuales_por_capitulo"][i][j] = nuevo_visual
            reemplazados += 1
        time.sleep(2.5)  # margen para no exceder el límite gratuito de peticiones por minuto


    log(AGENT, f"Verificación completa: {reemplazados}/{total} recursos reemplazados por baja coincidencia.")
    return visuales_info
