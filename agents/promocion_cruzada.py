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
import re

import googleapiclient.discovery

from agents.utils import load_config, log
from agents.publisher import _obtener_credenciales

AGENT = "PromocionCruzada"


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
        lineas.append(f"• {v['titulo']}: https://youtube.com/watch?v={v['video_id']}")
    lineas.append("")
    return "\n".join(lineas)


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
