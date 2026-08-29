"""
AGENTE 16: PROMOCIÓN CRUZADA ("PromocionCruzada")
----------------------------------------------------
Agrega en la descripción enlaces DIRECTOS y completos (https://...) a otros
videos ya publicados del propio canal que estén relacionados con el tema
del video actual, para fomentar tráfico orgánico entre tus propios videos
(cuando alguien ve uno, encuentra fácil el camino a otros 2-3 que también
le van a interesar).

Por qué se usa playlistItems() y no search():
  - El buscador (search().list) solo indexa contenido PÚBLICO, así que si
    tus videos están en privado/no listado no aparecerían ahí.
  - playlistItems() sobre la playlist de "subidos" del propio canal SÍ
    devuelve todos tus videos sin importar su privacidad, porque estás
    autenticado como el dueño. Así este agente funciona igual de bien
    mientras pruebas en privado que cuando ya publiques en público.

Nota honesta: la YouTube Data API NO permite crear pantallas finales
("end screens") ni tarjetas ("cards") de forma programática (no existe ese
endpoint), así que la única forma 100% automatizable de enlazar a otros
videos es aquí, en el texto de la descripción (que además YouTube convierte
automáticamente en un enlace en el que se puede hacer clic).
"""
import os
import random
import re

import googleapiclient.discovery
from PIL import Image, ImageDraw, ImageFont

from agents.utils import load_config, log
from agents.publisher import _obtener_credenciales

AGENT = "PromocionCruzada"

# Marcador especial usado en el campo "visual" del beat de mención cruzada
# (ver agregar_mencion_video_relacionado): en vez de buscar un clip de stock,
# VisualScout (agents/visuals.py) genera una tarjeta con el título del video
# recomendado, como sustituto casero de las "end screens" que la API de
# YouTube no permite crear de forma automática.
MARCADOR_VISUAL_CROSSPROMO = "TARJETA_VIDEO_RELACIONADO"

FRASES_MENCION_CRUZADA = [
    "Por cierto, si quieres profundizar más en esto, ya tengo un video completo sobre {titulo}.",
    "Y si te interesó este tema, no te pierdas el video donde hablo sobre {titulo}.",
    "Aviso rápido antes de terminar, también tengo un video dedicado a {titulo}, por si te sirve.",
    "Aprovecho para contarte que en el canal también hay un video completo sobre {titulo}.",
]


def _palabras_clave(texto: str) -> set:
    conectores = {"de", "del", "la", "el", "los", "las", "para", "con", "en", "y",
                  "a", "un", "una", "que", "su", "sus", "tu", "es", "al"}
    palabras = re.findall(r"[a-záéíóúñ]+", texto.lower())
    return {p for p in palabras if p not in conectores and len(p) > 2}


def _obtener_uploads_playlist_id(youtube) -> str:
    resp = youtube.channels().list(part="contentDetails", mine=True).execute()
    return resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def _listar_videos_del_canal(youtube, uploads_playlist_id: str, excluir_video_id: str = None, max_total: int = 50) -> list:
    """Devuelve [{'video_id':..., 'titulo':...}, ...] de todos los videos ya
    subidos al canal (funciona sin importar si están en privado)."""
    videos = []
    pagina = None
    while len(videos) < max_total:
        resp = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=pagina,
        ).execute()
        for item in resp.get("items", []):
            vid = item["snippet"]["resourceId"]["videoId"]
            if vid == excluir_video_id:
                continue
            videos.append({"video_id": vid, "titulo": item["snippet"]["title"]})
        pagina = resp.get("nextPageToken")
        if not pagina:
            break
    return videos


def obtener_videos_relacionados(keyword_principal: str, tags: list, video_actual_id: str = None,
                                 max_videos: int = 3) -> list:
    """Devuelve hasta 'max_videos' dicts {'video_id','titulo'} de OTROS
    videos del propio canal relacionados por palabras clave con el video
    actual. Si no hay ninguno relacionado (o es de los primeros videos del
    canal), devuelve una lista vacía sin romper el pipeline."""
    cfg = load_config()
    try:
        creds = _obtener_credenciales(cfg)
        youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        uploads_id = _obtener_uploads_playlist_id(youtube)
        videos = _listar_videos_del_canal(youtube, uploads_id, excluir_video_id=video_actual_id)
    except Exception as e:
        log(AGENT, f"No se pudo consultar el catálogo de videos del canal ({e}); se omite esta sección.")
        return []

    if not videos:
        log(AGENT, "Todavía no hay otros videos publicados en el canal; se omite esta sección.")
        return []

    palabras_tema = _palabras_clave(keyword_principal) | {p.lower() for t in tags for p in _palabras_clave(t)}

    puntuados = []
    for v in videos:
        palabras_titulo = _palabras_clave(v["titulo"])
        interseccion = palabras_tema & palabras_titulo
        score = len(interseccion) / max(len(palabras_tema), 1)
        puntuados.append((score, v))

    puntuados.sort(key=lambda t: t[0], reverse=True)
    relacionados = [v for score, v in puntuados if score > 0][:max_videos]

    # Si ninguno coincide por palabras clave, mostramos igual los más
    # recientes (mejor sugerir algo del canal que nada, para fomentar
    # tráfico interno) — pero solo si hay al menos 1 video disponible.
    if not relacionados and videos:
        relacionados = videos[:max_videos]
        log(AGENT, "Ningún video relacionado por tema; se sugieren los más recientes del canal.")
    else:
        log(AGENT, f"Videos relacionados encontrados: {[v['titulo'] for v in relacionados]}")

    return relacionados


def construir_bloque_mas_videos(videos_relacionados: list) -> str:
    if not videos_relacionados:
        return ""
    lineas = ["🔎 TAMBIÉN TE PUEDE INTERESAR:"]
    for v in videos_relacionados:
        lineas.append(f"• {v['titulo']}: {url_con_playlist(v['video_id'])}")
    lineas.append("")
    return "\n".join(lineas)


import random as _random

# Plantillas de PREGUNTA que invitan a comentar (pedido del usuario,
# 21-ago-2026: "algo así como ¿qué piensas sobre...?, ¿te ha pasado
# que...?, ¿crees que esto solucionaría...?, ¿conoces otras
# alternativas...?"). Los comentarios son señal directa de interacción
# para el algoritmo; una pregunta concreta multiplica las respuestas.
_PREGUNTAS_INTERACCION = [
    "🤔 ¿Qué piensas sobre {tema}? Te leo en los comentarios.",
    "🙋 ¿Te ha pasado algo relacionado con {tema}? Cuéntame tu experiencia.",
    "💬 ¿Crees que esto te ayudaría con {tema}? Dime tu opinión.",
    "🌿 ¿Conoces otras alternativas para {tema}? Compártelas aquí y aprendemos todos.",
    "👇 ¿Ya habías probado algo de esto para {tema}? ¿Qué tal te fue?",
    "🗣️ ¿Cuál de estos consejos sobre {tema} vas a probar primero? Cuéntame.",
    "❓ ¿Qué otro tema sobre {tema} te gustaría que investigue a fondo?",
]

# Banco de preguntas "cuéntame tu historia" (idea del usuario, 29-ago-2026):
# preguntas que invitan a CONTAR EXPERIENCIAS PROPIAS. Los comentarios largos
# y personales son la señal de interacción más valiosa para el algoritmo
# 2026 (satisfacción + conversación), mucho más que un "me gusta".
_PREGUNTAS_EXPERIENCIA = [
    "¿Te ha pasado? Cuéntame tu caso con {tema}, te leo y te respondo 🙌",
    "¿Cuánto tiempo llevas lidiando con esto? Comparte tu historia 👇",
    "¿Ya probaste algo parecido para {tema}? ¿Qué te funcionó y qué no?",
    "¿A qué edad empezaste a notar cambios con {tema}? Tu experiencia puede ayudar a otra persona 💚",
    "¿Qué es lo que MÁS te cuesta de {tema}? Sé sincero, aquí nadie juzga.",
    "Si pudieras hacerle UNA pregunta a un especialista sobre {tema}, ¿cuál sería? La investigo y hago un video 🎬",
    "¿Tu familia también sufre de esto? Cuéntame, ¿a quién le vas a compartir este video?",
    "¿Qué remedio casero te enseñaron tus abuelos para {tema}? Me encanta leer esas historias 🌿",
]


def comentario_conversacion(titulo_video: str, url_extra: str = "",
                             etiqueta_url: str = "") -> str:
    """Comentario 'semilla de conversación' (idea del usuario, 29-ago-2026):
    3 preguntas sugestivas EN UN SOLO comentario (varios comentarios propios
    seguidos parecen spam) que invitan a contar experiencias, + enlace
    opcional. Diseñado para fijarse manualmente en YouTube Studio."""
    tema = _tema_corto_de(titulo_video)
    preguntas = _random.sample(_PREGUNTAS_EXPERIENCIA, 3)
    numeros = ["1️⃣", "2️⃣", "3️⃣"]
    cuerpo = "💬 CUÉNTAME TU EXPERIENCIA 👇\n\n"
    cuerpo += "\n".join(f"{n} {p.format(tema=tema)}"
                         for n, p in zip(numeros, preguntas))
    cuerpo += "\n\nLeo y respondo todos los comentarios 💚"
    if url_extra:
        cuerpo += f"\n\n{etiqueta_url} {url_extra}"
    return cuerpo


def url_con_playlist(video_id: str, cfg=None, es_short: bool = False) -> str:
    """Construye el link de un video ANCLADO a la playlist del canal
    (idea del usuario, 27-ago-2026: 'que continúe otro video de mi canal
    hasta pasar por todos'). Con &list=, al terminar el video YouTube
    reproduce el SIGUIENTE de la playlist automáticamente: el espectador
    recorre el canal en cadena en vez de saltar a videos ajenos.
    El ID de la playlist se busca una vez y se guarda en estado.json."""
    try:
        if cfg is None:
            cfg = load_config()
        from agents.utils import load_state, save_state
        est = load_state()
        plid = est.get("playlist_canal_id", "")
        if not plid:
            creds = _obtener_credenciales(cfg)
            youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
            r = youtube.playlists().list(part="snippet", mine=True, maxResults=25).execute()
            objetivo = cfg["canal"]["nicho"].title().lower()
            for p in r.get("items", []):
                if p["snippet"]["title"].lower() == objetivo:
                    plid = p["id"]
                    break
            if not plid and r.get("items"):
                plid = r["items"][0]["id"]
            if plid:
                est["playlist_canal_id"] = plid
                save_state(est)
        base = f"https://www.youtube.com/watch?v={video_id}"
        return f"{base}&list={plid}" if plid else base
    except Exception:
        return f"https://www.youtube.com/watch?v={video_id}"


def _tema_corto_de(titulo: str) -> str:
    """Reduce el título a un tema natural para tejer en la pregunta
    (ej: '4 Señales Que Nunca Debes Ignorar Antes de Tomar Magnesio (Y...)'
    -> 'el magnesio'). Usa la parte más significativa del título."""
    t = (titulo or "").split(":")[0].split("(")[0].strip()
    # Limpiar signos de pregunta/exclamación y hashtags (títulos renovados
    # del 29-ago vienen como "¿Qué pasa si...?" y "#salud #Shorts"; sin esta
    # limpieza salían temas como "piernas a los 60?" con doble signo).
    t = re.sub(r"[¿?¡!]", "", t)
    t = re.sub(r"#\w+", "", t).strip()
    palabras = t.split()
    if len(palabras) > 6:
        t = " ".join(palabras[-4:])  # el final suele llevar el sustantivo clave
    t = t.lower().strip(" .,")
    # Quitar conectores iniciales que dejan la frase coja dentro de la
    # pregunta (bug visto en la prueba: "¿te ha pasado algo con ANTES DE
    # TOMAR magnesio?"). Se recortan hasta encontrar un sustantivo.
    # Ampliado 29-ago: también verbos conjugados de los títulos-pregunta
    # nuevos ("tomas esta bebida" → "esta bebida").
    _CONECTORES = ("antes de", "después de", "despues de", "para", "sobre",
                   "de", "del", "la", "el", "los", "las", "tu", "tus",
                   "tomar", "usar", "hacer", "y", "qué pasa si", "que pasa si",
                   "por qué", "por que", "esto pasa si", "tomas", "escuchas",
                   "ignoras", "reparas", "incluyes", "comes", "bebes",
                   "sufres", "si", "en", "esta", "este", "estos", "estas")
    cambiado = True
    while cambiado and t:
        cambiado = False
        for c in _CONECTORES:
            if t.startswith(c + " "):
                t = t[len(c) + 1:]
                cambiado = True
    t = t.strip(" .,")
    # Control de calidad final (29-ago-2026): si lo que quedó es muy corto,
    # puro número ("60") o sigue empezando con verbo raro, mejor un tema
    # genérico digno que una frase coja en la pregunta.
    if len(t) < 5 or t.replace(" ", "").isdigit():
        return "este tema"
    return t


def comentario_interactivo(titulo_video: str, url_extra: str = "",
                            etiqueta_url: str = "") -> str:
    """Construye un comentario que INVITA a interactuar (pregunta concreta
    sobre el tema) y, opcionalmente, añade un enlace (al Short o al video
    completo). Un comentario-pregunta genera más respuestas que un enlace
    seco, y cada respuesta es señal de interacción para el algoritmo."""
    tema = _tema_corto_de(titulo_video)
    pregunta = _random.choice(_PREGUNTAS_INTERACCION).format(tema=tema)
    if url_extra:
        pregunta += f"\n\n{etiqueta_url} {url_extra}"
    return pregunta


def publicar_comentario_cruzado(video_id: str, texto: str) -> bool:
    """Publica un comentario del propio canal en 'video_id' (funciona tanto
    para el video largo como para el Short). No sustituye a un comentario
    'fijado' de verdad (la API de YouTube NO permite fijar comentarios de
    forma automática, es una limitación confirmada de la plataforma, no
    nuestra), pero SÍ deja el enlace visible y clicable entre los primeros
    comentarios de un video recién publicado con pocos comentarios todavía,
    con cero configuración adicional: usa la misma autorización que ya
    tenemos para publicar videos."""
    cfg = load_config()
    try:
        creds = _obtener_credenciales(cfg)
        youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {"snippet": {"textOriginal": texto}},
                }
            },
        ).execute()
        log(AGENT, f"Comentario de enlace cruzado publicado en {video_id}.")
        return True
    except Exception as e:
        log(AGENT, f"Aviso: no se pudo publicar el comentario cruzado en {video_id} ({e}). "
                    f"No es grave, el video se publicó igual; los comentarios a veces están "
                    f"desactivados o tardan unos minutos en habilitarse tras la subida.")
        return False


def agregar_mencion_video_relacionado(guion: dict, video_relacionado: dict) -> dict:
    """Inserta, dentro del propio guion, un beat que menciona en voz alta un
    video ya publicado del canal relacionado con el tema actual (tráfico
    orgánico interno: alguien que ve un video encuentra fácil el camino a
    otro). Se coloca cerca del final, ANTES del llamado final a suscripción
    (ver agents/suscripcion_cta.py) para no romper el cierre del video.

    'video_relacionado': dict {'video_id':..., 'titulo':...} (el primero y
    mejor emparejado de agents.promocion_cruzada.obtener_videos_relacionados).
    Si es None/vacío, no hace nada (el canal puede no tener aún otros videos
    publicados, por ejemplo el primer día)."""
    if not video_relacionado:
        return guion
    capitulos = guion.get("capitulos", [])
    if not capitulos:
        return guion

    titulo_rel = video_relacionado.get("titulo", "").strip()
    if not titulo_rel:
        return guion

    # LIMPIEZA PARA VOZ (bug real oído por el usuario el 18-ago-2026: la
    # voz dijo "almohadilla... shorts" al final del video). Causa: el
    # título del video recomendado era un Short y traía "😱 #Shorts"; este
    # beat se agrega DESPUÉS de la sanitización del guionista, así que
    # nadie lo limpiaba. Se limpia aquí mismo: fuera emojis, hashtags y
    # cualquier símbolo no narrable.
    import re as _re
    titulo_narrable = titulo_rel
    titulo_narrable = _re.sub(r"#\w+", "", titulo_narrable)          # hashtags (#Shorts)
    titulo_narrable = _re.sub(r"[^\w\sáéíóúÁÉÍÓÚñÑüÜ¿?¡!,.:]", "", titulo_narrable)  # emojis/símbolos
    titulo_narrable = _re.sub(r"\s{2,}", " ", titulo_narrable).strip(" .,:")

    texto = random.choice(FRASES_MENCION_CRUZADA).format(titulo=titulo_narrable)
    beat = {
        "texto": texto,
        "visual": MARCADOR_VISUAL_CROSSPROMO,
        "es_mencion_cruzada": True,
        "titulo_video_relacionado": titulo_rel,
    }

    cap_final = capitulos[-1]
    beats = cap_final.setdefault("beats", [])
    from agents.suscripcion_cta import insertar_antes_del_cierre
    insertar_antes_del_cierre(beats, beat)

    log(AGENT, f"Mención cruzada agregada al guion, recomendando: '{titulo_rel}'")
    return guion


def _fuente_crosspromo(tam):
    ruta = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(ruta):
        return ImageFont.truetype(ruta, tam)
    return ImageFont.load_default()


def generar_tarjeta_video_relacionado(titulo_relacionado: str, carpeta_salida: str, tag: str,
                                       resolucion=(1280, 720)) -> str:
    """Genera (con Pillow, sin IA, siempre nítido) una tarjeta tipo 'también
    te puede interesar' con el título del video recomendado. Es el sustituto
    casero de las 'end screens' de YouTube, que la API no permite crear de
    forma programática (limitación confirmada de la plataforma)."""
    img = Image.new("RGB", resolucion, (20, 20, 25))
    draw = ImageDraw.Draw(img)
    font_chica = _fuente_crosspromo(38)
    font_grande = _fuente_crosspromo(54)

    encabezado = "TAMBIÉN TE PUEDE INTERESAR"
    tw = draw.textlength(encabezado, font=font_chica)
    draw.text(((resolucion[0] - tw) / 2, resolucion[1] / 2 - 150), encabezado,
               font=font_chica, fill=(255, 210, 0))
    draw.line([(resolucion[0] / 2 - 90, resolucion[1] / 2 - 100),
               (resolucion[0] / 2 + 90, resolucion[1] / 2 - 100)], fill=(255, 210, 0), width=4)

    max_w = resolucion[0] * 0.82
    palabras = titulo_relacionado.split()
    linea, lineas = "", []
    for palabra in palabras:
        prueba = (linea + " " + palabra).strip()
        if draw.textlength(prueba, font=font_grande) > max_w:
            lineas.append(linea)
            linea = palabra
        else:
            linea = prueba
    if linea:
        lineas.append(linea)
    lineas = lineas[:3]

    y0 = resolucion[1] / 2 - 40
    for i, ln in enumerate(lineas):
        tw = draw.textlength(ln, font=font_grande)
        draw.text(((resolucion[0] - tw) / 2, y0 + i * 66), ln, font=font_grande, fill=(255, 255, 255))

    pie = "Link en la descripción de este video"
    tw = draw.textlength(pie, font=font_chica)
    draw.text(((resolucion[0] - tw) / 2, y0 + len(lineas) * 66 + 30), pie,
               font=font_chica, fill=(200, 200, 200))

    os.makedirs(carpeta_salida, exist_ok=True)
    destino = os.path.join(carpeta_salida, f"{tag}_video_relacionado.jpg")
    img.save(destino, quality=90)
    return destino

