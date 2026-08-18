"""
AGENTE 31: SHORT INDEPENDIENTE ("ShortIndependiente")
------------------------------------------------------
Añadido el 16-ago-2026 (estrategia de crecimiento acordada con el usuario):
los días en que NO toca video largo (frecuencia: largo cada 2 días), el
robot publica UN Short con CONTENIDO COMPLETO Y PROPIO, alineado con un
video largo YA EXISTENTE del canal, para mantener presencia diaria en el
feed de Shorts (el único canal de descubrimiento real de un canal nuevo)
sin aumentar la frecuencia de videos largos.

Decisiones de diseño pedidas por el usuario:
  1) CONTENIDO COMPLETO: el Short se entiende solo, de principio a fin
     (dato/consejo con valor real, no un teaser cortado).
  2) ALINEADO A UN LARGO EXISTENTE: el tema sale de un video largo ya
     publicado (rotando entre ellos), pero el CONTENIDO es nuevo: otro
     ángulo, otro dato, otro guion. Así el comentario con el link al
     video largo es coherente y el tráfico fluye hacia contenido real.
  3) HUMANIZADO: guion generado por LLM con instrucciones de oralidad
     (muletillas naturales controladas, preguntas retóricas, ritmo
     conversacional), voz rotativa, velocidad de narración levemente
     variable por video, y formatos rotativos para que ningún par de
     Shorts se sienta "de plantilla".

Defensas anti-"contenido inauténtico" (investigación 16-ago-2026):
  - 4 formatos que rotan (dato sorprendente / mito vs verdad / top 3 /
    mini consejo práctico).
  - Duración objetivo variable (20-45s).
  - Cierres variados (unos llaman al largo, otros a suscribirse, otros
    solo dejan curiosidad).
  - Tema único por Short, con verificación científica cuando hay estudios.
  - Pasa por el filtro de seguridad médica (agents/seguridad_medica.py).
"""
import datetime as dt
import json
import random
import re

import requests

from agents.utils import load_config, load_state, save_state, log, limpiar_texto_para_voz

AGENT = "ShortIndependiente"

# Formatos rotativos: cada uno produce una estructura de guion DISTINTA.
FORMATOS = ["dato_sorprendente", "mito_vs_verdad", "top_3", "consejo_practico"]

# Cierres variados: NO todos llaman a lo mismo (anti-plantilla).
CIERRES = [
    ("largo", "Si quieres la guía completa, está en el video largo de mi canal. Te dejo el link en el primer comentario."),
    ("suscribir", "Si te sirvió este dato, suscríbete. Publico contenido con respaldo científico real."),
    ("curiosidad", "Y esto es solo una parte. El tema completo es aún más interesante."),
    ("interaccion", "¿Ya lo sabías? Cuéntame en los comentarios."),
]

PROMPT_SHORT = """Eres guionista de YouTube Shorts en español para un canal de salud natural \
llamado Salud Natural Diaria. Escribe un guion COMPLETO y AUTOCONTENIDO (se entiende sin ver \
ningún otro video) de {duracion} segundos aproximadamente ({palabras} palabras habladas).

TEMA BASE (viene de un video largo ya publicado del canal): {tema}
FORMATO OBLIGATORIO de este Short: {formato_instruccion}

{fuentes}

REGLAS DE HUMANIZACIÓN (muy importantes, esto debe sonar a persona real, no a robot):
- Escribe como se HABLA, no como se escribe: frases cortas, contracciones naturales del español.
- Incluye UNA pregunta retórica dirigida al espectador (ej: "¿te ha pasado?").
- Usa máximo UNA expresión coloquial natural (ej: "ojo con esto", "aquí viene lo bueno", "esto te va a sorprender").
- Nada de lenguaje de folleto ("descubre los increíbles beneficios") ni de jerga técnica sin explicar.
- PROHIBIDO: saludos genéricos ("hola amigos"), presentar el canal, pedir suscripción (el cierre lo pongo yo).
- El primer segundo es TODO: arranca directo con el dato/pregunta más fuerte.

REGLA DE LOS PRIMEROS 3 SEGUNDOS (añadida 19-ago-2026 con datos REALES del canal:
un Short llegó a 710 personas pero el 66% deslizó en los primeros ~9 segundos;
otro Short con mejor arranque retuvo el 63%):
- El PRIMER beat debe ser IMPOSIBLE de ignorar: una afirmación que rompa una
  creencia común, una cifra concreta, o una pregunta que duela ("¿por qué sigues
  cansado si duermes 8 horas?").
- El primer beat NUNCA empieza con contexto ("la salud de nuestros ojos es
  importante...") ni con el nombre del tema. Empieza con el CHOQUE.
- Piensa así: la persona está deslizando Shorts a toda velocidad; tienes UNA
  frase para que el dedo se detenga.

REGLAS DE SEGURIDAD MÉDICA (obligatorias):
- NUNCA digas que algo cura, elimina o revierte una enfermedad.
- NUNCA sugieras reemplazar medicamentos o tratamientos.
- Usa "puede apoyar", "se ha asociado con", "la evidencia sugiere".

FORMATO DE RESPUESTA (JSON estricto, sin nada más):
{{"beats": [{{"texto": "...", "visual": "english visual keyword here"}}, ...]}}

Entre 3 y 5 beats. Cada "texto" de 1-2 frases narrables. Cada "visual" en INGLÉS, escena real \
filmable relacionada con el texto (nunca 'body figure' ni personas descritas solo por su cuerpo)."""

FORMATO_INSTRUCCIONES = {
    "dato_sorprendente": "UN dato sorprendente y verificable sobre el tema, explicado con claridad: por qué sorprende, qué significa en la práctica.",
    "mito_vs_verdad": "Toma UN mito común sobre el tema y contrástalo con lo que dice la evidencia real. Estructura: 'Se dice que X... pero la realidad es Y'.",
    "top_3": "Los 3 puntos más útiles del tema, contados con ritmo (el mejor al final, para que vean hasta el final).",
    "consejo_practico": "UN consejo práctico y accionable del tema que la persona pueda aplicar HOY, con el paso a paso mínimo.",
}


def _videos_largos_existentes(estado: dict, cfg: dict) -> list:
    """Videos largos reales del canal (del canal real vía API si se puede,
    con respaldo en la memoria local)."""
    videos = []
    try:
        import pickle
        import googleapiclient.discovery
        from google.auth.transport.requests import Request
        with open(cfg["apis"]["oauth_token_path"], "rb") as f:
            creds = pickle.load(f)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        yt = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        canal_id = cfg.get("canal", {}).get("channel_id", "")
        playlist = "UU" + canal_id[2:] if canal_id.startswith("UC") else ""
        if playlist:
            r = yt.playlistItems().list(part="snippet,contentDetails",
                                         playlistId=playlist, maxResults=20).execute()
            import isodate
            ids = [it["contentDetails"]["videoId"] for it in r.get("items", [])]
            if ids:
                r2 = yt.videos().list(part="snippet,contentDetails", id=",".join(ids)).execute()
                for it in r2.get("items", []):
                    dur = isodate.parse_duration(it["contentDetails"]["duration"]).total_seconds()
                    if dur >= 120:  # solo videos largos (>2 min), no Shorts
                        videos.append({"video_id": it["id"],
                                        "titulo": it["snippet"]["title"]})
    except Exception as e:
        log(AGENT, f"Aviso listando videos del canal ({e}); se usa la memoria local.")
    if not videos:
        for v in estado.get("videos_publicados", []):
            if v.get("video_id") and v.get("titulo"):
                videos.append({"video_id": v["video_id"], "titulo": v["titulo"]})
    return videos


def _generar_guion_short(tema: str, formato: str, cfg: dict) -> dict:
    """Genera el mini-guion con Groq/Gemini. Si no hay LLM, usa una
    estructura simple basada en los estudios encontrados."""
    duracion = random.randint(22, 42)  # duración objetivo variable (humanización)
    palabras = int(duracion * 2.4)     # ~145 palabras/min hablado

    # Estudios reales para el dato (si el tema los tiene disponibles)
    fuentes = ""
    estudios = []
    try:
        from agents.investigacion_cientifica import buscar_estudios, construir_bloque_fuentes_para_prompt
        estudios = buscar_estudios(tema, max_resultados=3)
        if estudios:
            fuentes = construir_bloque_fuentes_para_prompt(estudios)
    except Exception:
        pass

    prompt = PROMPT_SHORT.format(
        duracion=duracion, palabras=palabras, tema=tema,
        formato_instruccion=FORMATO_INSTRUCCIONES[formato],
        fuentes=fuentes or "No hay fuentes disponibles: habla en términos generales, sin cifras ni estudios inventados.",
    )

    texto_respuesta = None
    groq_key = cfg["apis"].get("groq_api_key", "")
    if groq_key and "OBTENER_GRATIS" not in groq_key:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={"model": "llama-3.3-70b-versatile",
                      "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.9},  # temperatura alta = más variación entre Shorts
                timeout=60)
            r.raise_for_status()
            texto_respuesta = r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log(AGENT, f"Aviso: Groq no disponible para el guion del Short ({e}).")

    if texto_respuesta is None:
        gemini_key = cfg["apis"].get("gemini_api_key", "")
        if gemini_key and "OBTENER_GRATIS" not in gemini_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
                r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
                r.raise_for_status()
                from agents.presupuesto_ia import registrar_uso_gemini
                registrar_uso_gemini(1)
                texto_respuesta = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                log(AGENT, f"Aviso: Gemini tampoco disponible ({e}).")

    beats = []
    if texto_respuesta:
        try:
            inicio, fin = texto_respuesta.find("{"), texto_respuesta.rfind("}")
            data = json.loads(texto_respuesta[inicio:fin + 1])
            beats = [b for b in data.get("beats", []) if b.get("texto")]
        except Exception as e:
            log(AGENT, f"Aviso: la respuesta del LLM no era JSON válido ({e}).")

    if not beats:
        # Respaldo sin LLM: no publicar un Short genérico de plantilla.
        # Mejor avisar y no publicar (el usuario pidió contenido completo
        # de calidad, no relleno).
        return None

    # Limpieza + seguridad médica sobre cada beat
    for b in beats:
        b["texto"] = limpiar_texto_para_voz(b.get("texto", ""))
    guion = {"titulo": tema, "capitulos": [{"nombre": "short", "beats": beats}],
             "referencias": [], "_estudios": estudios}
    try:
        from agents.seguridad_medica import verificar_guion_seguro
        guion = verificar_guion_seguro(guion)
    except Exception:
        pass
    return guion


def _titulo_short(tema: str, formato: str) -> str:
    base = tema.split(":")[0].strip()
    prefijos = {
        "dato_sorprendente": ["El Dato Que No Conocías De", "Lo Que Nadie Te Dijo De"],
        "mito_vs_verdad": ["El Mito Más Común De", "La Verdad Sobre"],
        "top_3": ["3 Claves De", "Lo Mejor De"],
        "consejo_practico": ["Haz Esto Hoy:", "El Consejo Práctico De"],
    }
    pref = random.choice(prefijos[formato])
    titulo = f"{pref} {base}"[:85]
    return titulo + " #Shorts"


def crear_short_independiente() -> dict:
    """Punto de entrada del orquestador en días sin video largo.
    Devuelve {'ruta': ..., 'titulo': ..., 'descripcion': ..., 'video_largo_id': ...}
    o None si no fue posible (sin videos largos aún, sin LLM, etc.)."""
    cfg = load_config()
    estado = load_state()

    # Candado anti-duplicado del día: el cron de respaldo (21:45 UTC)
    # ejecuta este mismo paso; si el horario principal ya publicó el Short
    # independiente de hoy, no se publica otro.
    hoy = dt.datetime.now(dt.timezone.utc).date().isoformat()
    if estado.get("ultimo_short_independiente") == hoy:
        log(AGENT, "Hoy ya se publicó el Short independiente (corrida de respaldo); no se duplica.")
        return None

    largos = _videos_largos_existentes(estado, cfg)
    if not largos:
        log(AGENT, "No hay videos largos publicados aún; no se genera Short independiente.")
        return None

    # Rotación: el largo menos recientemente usado para un Short independiente
    usados = estado.get("shorts_independientes_por_video", {})
    largos_ordenados = sorted(largos, key=lambda v: usados.get(v["video_id"], ""))
    elegido = largos_ordenados[0]

    # Rotación de formatos: nunca repetir el del día anterior
    ultimo_formato = estado.get("ultimo_formato_short", "")
    formatos_posibles = [f for f in FORMATOS if f != ultimo_formato] or FORMATOS
    formato = random.choice(formatos_posibles)

    log(AGENT, f"Short independiente: tema del video largo '{elegido['titulo'][:50]}' "
                f"con formato '{formato}'.")

    guion = _generar_guion_short(elegido["titulo"], formato, cfg)
    if not guion:
        log(AGENT, "No se pudo generar un guion de calidad (sin LLM disponible); "
                    "mejor no publicar relleno hoy.")
        return None

    # Cierre variado (anti-plantilla)
    tipo_cierre, texto_cierre = random.choice(CIERRES)
    guion["capitulos"][0]["beats"].append({
        "texto": texto_cierre,
        "visual": "smiling person in bright natural setting",
    })

    # Gancho = primer beat (el Short arranca directo, sin gancho aparte)
    guion["gancho"] = ""

    from agents.shorts_creator import crear_short
    nombre_base = "short_indep_" + dt.datetime.now().strftime("%Y%m%d_%H%M")
    url_largo = f"https://youtube.com/watch?v={elegido['video_id']}"
    ruta, titulo_auto, _desc = crear_short(guion, "output/video", nombre_base,
                                            url_video_largo=url_largo)

    titulo = _titulo_short(elegido["titulo"], formato)
    descripcion = (
        f"{guion['capitulos'][0]['beats'][0]['texto']}\n\n"
        f"👉 El video COMPLETO del tema está en el PRIMER COMENTARIO 📌\n"
        f"También en el canal: {url_largo}\n\n"
        f"#Shorts #SaludNatural"
    )

    # Registro de rotación + candado del día
    usados[elegido["video_id"]] = dt.datetime.now().isoformat()
    estado["shorts_independientes_por_video"] = usados
    estado["ultimo_formato_short"] = formato
    estado["ultimo_short_independiente"] = hoy
    save_state(estado)

    return {"ruta": ruta, "titulo": titulo, "descripcion": descripcion,
            "video_largo_id": elegido["video_id"]}


if __name__ == "__main__":
    print(crear_short_independiente())
