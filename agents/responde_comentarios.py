"""
AGENTE 30: RESPONDEDOR DE COMENTARIOS ("RespondeComentarios")
-------------------------------------------------------------
Añadido el 16-ago-2026 como parte de la estrategia de crecimiento de
visualizaciones. Por qué existe (con datos reales de la investigación):

  - El algoritmo de YouTube usa la INTERACCIÓN (comentarios, respuestas,
    tiempo de sesión) como señal principal para recomendar un video.
  - Un canal que RESPONDE comentarios duplica la señal: cada respuesta es
    un comentario más, incentiva réplicas del espectador, y sube la
    probabilidad de que vuelva (retención de canal).
  - En un canal nuevo, además, es la diferencia entre parecer un canal
    "fantasma" y una comunidad viva: la gente comenta más donde ve que
    le responden.

Qué hace en cada corrida:
  1) Toma los últimos videos publicados (memoria del robot).
  2) Lee sus comentarios con la API oficial (misma autorización de siempre).
  3) Filtra: ignora comentarios del propio canal (los cross-promo) y los
     que ya respondió antes (registro en data/estado.json).
  4) Genera una respuesta BREVE, cálida y específica con el LLM gratuito
     (Groq/Gemini); si no hay LLM disponible, usa una plantilla amable.
  5) Publica la respuesta. Máximo MAX_RESPUESTAS_POR_CORRIDA por corrida
     (nunca parecer un bot que contesta 100 cosas en un minuto).

Seguridad/honestidad:
  - NUNCA da consejo médico personalizado en respuestas: si el comentario
    pide diagnóstico o tratamiento, responde con empatía y recomienda
    consultar a un profesional (regla YMYL).
  - No responde a spam ni enlaces.
"""
import re

import googleapiclient.discovery
import requests

from agents.utils import load_config, load_state, save_state, log, modelo_groq

AGENT = "RespondeComentarios"

MAX_RESPUESTAS_POR_CORRIDA = 10
MAX_VIDEOS_A_REVISAR = 6

RESPUESTAS_PLANTILLA = [
    "¡Gracias por comentar! Nos alegra que el contenido te sirva. 🌿",
    "¡Gracias por pasar por aquí! Si tienes alguna duda sobre el tema, cuéntanos. 🌿",
    "¡Qué bueno leerte! Gracias por apoyar el canal. 🌿",
    "¡Gracias por tu comentario! Cada día compartimos más contenido con respaldo científico real. 🌿",
]

RESPUESTA_TEMA_MEDICO = (
    "¡Gracias por compartir tu situación! Este canal es informativo y no puede "
    "dar consejos médicos personalizados: para tu caso concreto, lo más "
    "responsable es que lo consultes con tu médico o un profesional de salud. "
    "Un abrazo. 🌿"
)

_PALABRAS_CASO_MEDICO = re.compile(
    r"\b(tengo|padezco|sufro|me diagnosticaron|mi enfermedad|mis s[ií]ntomas|"
    r"qu[eé] dosis|cu[aá]nto tomo|puedo dejar|mi medicamento|estoy tomando)\b",
    re.IGNORECASE)


def _obtener_youtube(cfg):
    import pickle
    token_path = cfg["apis"]["oauth_token_path"]
    with open(token_path, "rb") as f:
        creds = pickle.load(f)
    from google.auth.transport.requests import Request
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)


def _canal_propio_id(cfg) -> str:
    return cfg.get("canal", {}).get("channel_id", "") or ""


def _generar_respuesta_llm(comentario: str, titulo_video: str, cfg) -> str:
    """Respuesta breve y específica con Groq (gratis). Si falla, plantilla."""
    import random
    if _PALABRAS_CASO_MEDICO.search(comentario):
        return RESPUESTA_TEMA_MEDICO

    groq_key = cfg["apis"].get("groq_api_key", "")
    if groq_key and "OBTENER_GRATIS" not in groq_key:
        try:
            prompt = (
                f"Eres el community manager cálido y humano de un canal de YouTube de "
                f"salud natural en español llamado Salud Natural Diaria. Un espectador "
                f"comentó esto en el video \"{titulo_video}\":\n\n\"{comentario[:400]}\"\n\n"
                f"Escribe UNA respuesta breve (máximo 40 palabras), cálida, específica al "
                f"comentario, en español neutro. REGLAS: nunca des consejo médico "
                f"personalizado ni dosis; nunca prometas curas; si pregunta algo del tema "
                f"general puedes responder en términos generales; termina invitando "
                f"sutilmente a seguir viendo el canal. Responde SOLO con el texto de la "
                f"respuesta, sin comillas."
            )
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={"model": modelo_groq(groq_key),
                      "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.7, "max_tokens": 120},
                timeout=30)
            r.raise_for_status()
            texto = r.json()["choices"][0]["message"]["content"].strip().strip('"')
            if 5 < len(texto) < 400:
                # Pasada de seguridad médica también sobre la respuesta
                try:
                    from agents.seguridad_medica import _revisar_texto
                    texto, _ = _revisar_texto(texto)
                except Exception:
                    pass
                return texto
        except Exception as e:
            log(AGENT, f"Aviso: LLM no disponible para respuestas ({e}); se usa plantilla.")
    return random.choice(RESPUESTAS_PLANTILLA)


def _es_spam(texto: str) -> bool:
    t = texto.lower()
    return ("http://" in t or "https://" in t or "whatsapp" in t or
            "telegram" in t or len(texto.strip()) < 2)


def responder_comentarios_pendientes() -> int:
    """Punto de entrada. Devuelve cuántas respuestas publicó."""
    cfg = load_config()
    estado = load_state()
    respondidos = set(estado.get("comentarios_respondidos", []))

    try:
        yt = _obtener_youtube(cfg)
    except Exception as e:
        log(AGENT, f"No se pudo conectar a YouTube ({e}); se omite esta ronda de respuestas.")
        return 0

    # Los videos a revisar se toman DIRECTO del canal real (no solo de la
    # memoria local, que puede quedar desactualizada si un push de la
    # memoria falló, como pasó el 14-ago-2026). Cuesta 1 unidad de cuota.
    videos = []
    canal_id_cfg = _canal_propio_id(cfg)
    try:
        playlist_subidas = "UU" + canal_id_cfg[2:] if canal_id_cfg.startswith("UC") else ""
        if playlist_subidas:
            r = yt.playlistItems().list(part="contentDetails",
                                         playlistId=playlist_subidas,
                                         maxResults=MAX_VIDEOS_A_REVISAR * 2).execute()
            videos = [it["contentDetails"]["videoId"] for it in r.get("items", [])]
    except Exception as e:
        log(AGENT, f"Aviso listando videos del canal ({e}); se usa la memoria local.")
    if not videos:
        videos = [v.get("video_id") for v in estado.get("videos_publicados", [])[-MAX_VIDEOS_A_REVISAR:]]
        videos += [v.get("short_id") for v in estado.get("videos_publicados", [])[-MAX_VIDEOS_A_REVISAR:]]
        videos = [v for v in videos if v]
    if not videos:
        log(AGENT, "No hay videos publicados registrados; nada que responder todavía.")
        return 0

    canal_id = _canal_propio_id(cfg)
    titulos = {v.get("video_id"): v.get("titulo", "") for v in estado.get("videos_publicados", [])}
    publicadas = 0

    for vid in videos:
        if publicadas >= MAX_RESPUESTAS_POR_CORRIDA:
            break
        try:
            r = yt.commentThreads().list(part="snippet,replies", videoId=vid,
                                          maxResults=50, textFormat="plainText").execute()
        except Exception as e:
            # Video sin comentarios habilitados o borrado: seguir con el resto
            continue

        for hilo in r.get("items", []):
            if publicadas >= MAX_RESPUESTAS_POR_CORRIDA:
                break
            top = hilo["snippet"]["topLevelComment"]
            comentario_id = top["id"]
            snippet = top["snippet"]
            autor_canal = (snippet.get("authorChannelId", {}) or {}).get("value", "")

            # Ignorar: nuestros propios comentarios (cross-promo), ya
            # respondidos, spam, y los hilos donde ya respondimos antes
            # (aunque el registro local se haya perdido).
            if autor_canal == canal_id:
                continue
            if comentario_id in respondidos:
                continue
            texto = snippet.get("textDisplay", "")
            if _es_spam(texto):
                continue
            ya_respondido_por_nosotros = any(
                (resp["snippet"].get("authorChannelId", {}) or {}).get("value", "") == canal_id
                for resp in hilo.get("replies", {}).get("comments", [])
            )
            if ya_respondido_por_nosotros:
                respondidos.add(comentario_id)
                continue

            respuesta = _generar_respuesta_llm(texto, titulos.get(vid, ""), cfg)
            try:
                yt.comments().insert(
                    part="snippet",
                    body={"snippet": {"parentId": comentario_id,
                                       "textOriginal": respuesta}},
                ).execute()
                respondidos.add(comentario_id)
                publicadas += 1
                log(AGENT, f"Respondido en {vid}: \"{texto[:50]}...\" -> \"{respuesta[:60]}...\"")
            except Exception as e:
                log(AGENT, f"Aviso: no se pudo responder un comentario en {vid} ({e}).")

    estado["comentarios_respondidos"] = sorted(respondidos)[-500:]  # limitar tamaño
    save_state(estado)
    if publicadas:
        log(AGENT, f"{publicadas} respuesta(s) publicada(s). Cada respuesta duplica la señal "
                    f"de interacción del video ante el algoritmo.")
    else:
        log(AGENT, "Sin comentarios nuevos de espectadores por responder en esta ronda.")
    return publicadas


if __name__ == "__main__":
    responder_comentarios_pendientes()
