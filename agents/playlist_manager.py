"""
AGENTE 13: GESTOR DE PLAYLISTS ("Playlist Manager")
----------------------------------------------------
Agrupa automáticamente los videos del canal en una playlist por nicho/tema.
YouTube favorece a los canales donde una persona ve VARIOS videos seguidos
(watch time de sesión), y las playlists son la forma más simple y 100%
gratuita de fomentar eso: cuando termina un video, YouTube sugiere el
siguiente de la misma playlist automáticamente.

100% automatizable con tu misma cuenta ya autorizada, sin cuentas nuevas.
"""
import googleapiclient.discovery

from agents.utils import load_config, log
from agents.publisher import _obtener_credenciales

AGENT = "PlaylistManager"


def _buscar_o_crear_playlist(youtube, titulo: str, descripcion: str) -> str:
    resp = youtube.playlists().list(part="snippet", mine=True, maxResults=50).execute()
    for item in resp.get("items", []):
        if item["snippet"]["title"].strip().lower() == titulo.strip().lower():
            return item["id"]

    creada = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {"title": titulo, "description": descripcion},
            "status": {"privacyStatus": "public"},
        },
    ).execute()
    log(AGENT, f"Playlist creada: '{titulo}'")
    return creada["id"]


def agregar_a_playlist(video_id: str, nombre_playlist: str) -> bool:
    cfg = load_config()
    try:
        creds = _obtener_credenciales(cfg)
        youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        playlist_id = _buscar_o_crear_playlist(
            youtube, nombre_playlist,
            f"Todos los videos sobre {cfg['canal']['nicho']} en un solo lugar."
        )
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }
            },
        ).execute()
        log(AGENT, f"Video agregado a la playlist '{nombre_playlist}'.")
        return True
    except Exception as e:
        log(AGENT, f"No se pudo agregar a la playlist ({e}).")
        return False
