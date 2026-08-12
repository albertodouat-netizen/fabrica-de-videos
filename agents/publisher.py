"""
AGENTE 7: PUBLICADOR ("Publisher")
----------------------------------------------------
Sube el video final a TU canal de YouTube usando la YouTube Data API v3
(100% GRATIS, cuota diaria gratuita de sobra para 4 videos/semana).

IMPORTANTE sobre "automatización total":
YouTube (como cualquier plataforma) exige que exista un dueño humano
verificado del canal. Por políticas de Google, la primera autorización
(OAuth) la debes dar TÚ una sola vez, abriendo un enlace y aceptando con tu
cuenta de Google. Después de eso, el token se guarda localmente y TODAS las
subidas siguientes son 100% automáticas, sin volver a tocar nada.
Esto no es una limitación del sistema: es la única puerta de seguridad que
pone la propia plataforma y no se puede -ni se debe- saltar.
"""
import os
import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.http
import google.auth.transport.requests

from agents.utils import load_config, log

AGENT = "Publicador"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube",
          "https://www.googleapis.com/auth/youtube.force-ssl"]  # necesario para subir subtítulos


def _obtener_credenciales(cfg):
    token_path = cfg["apis"]["oauth_token_path"]
    client_secret_path = cfg["apis"]["oauth_client_secret_path"]

    creds = None
    if os.path.exists(token_path):
        with open(token_path, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            if not os.path.exists(client_secret_path):
                raise FileNotFoundError(
                    f"No se encontró {client_secret_path}. Descárgalo gratis desde "
                    f"Google Cloud Console (OAuth Client ID > Desktop App) y colócalo ahí. "
                    f"Ver README para el paso a paso."
                )
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                client_secret_path, SCOPES
            )
            log(AGENT, "Autorización única requerida: se abrirá un enlace/navegador. "
                       "Esto solo pasa la PRIMERA vez.")
            creds = flow.run_local_server(port=0)
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    return creds


def publicar_video(ruta_video: str, ruta_miniatura: str, guion: dict, descripcion_final: str = None) -> str:
    cfg = load_config()
    creds = _obtener_credenciales(cfg)
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)

    from agents.viral_strategist import construir_tags_seo
    descripcion = descripcion_final if descripcion_final else (
        guion.get("descripcion", "") + "\n\n" + guion.get("disclaimer", "")
    )

    body = {
        "snippet": {
            "title": guion["titulo"][:100],
            "description": descripcion[:5000],  # YouTube limita la descripción a 5000 caracteres
            "tags": construir_tags_seo(guion, cfg["canal"].get("nombre", "")),
            "categoryId": cfg["publicacion"].get("categoria_youtube", "22"),
        },
        "status": {
            "privacyStatus": cfg["publicacion"].get("privacidad_default", "private"),
            "selfDeclaredMadeForKids": False,

        },
    }


    media = googleapiclient.http.MediaFileUpload(ruta_video, chunksize=-1, resumable=True)
    log(AGENT, f"Subiendo video a YouTube: {guion['titulo']}")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            log(AGENT, f"Progreso de subida: {int(status.progress() * 100)}%")

    video_id = response["id"]
    log(AGENT, f"Video subido: https://youtube.com/watch?v={video_id}")

    if ruta_miniatura and os.path.exists(ruta_miniatura):
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=ruta_miniatura).execute()
            log(AGENT, "Miniatura personalizada asignada.")
        except Exception as e:
            log(AGENT, f"Aviso: no se pudo asignar la miniatura personalizada ({e}). "
                        f"El video ya está publicado igual; puedes subir la miniatura manualmente "
                        f"desde YouTube Studio si quieres (queda guardada en disco).")

    return video_id


if __name__ == "__main__":
    print("Este módulo se usa desde orchestrator.py. Requiere client_secret.json "
          "(ver config.yaml -> oauth_client_secret_path) para funcionar de verdad.")
