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


def _publish_at_hora_pico(cfg) -> str:
    """Devuelve el timestamp ISO-8601 UTC para programar la publicación en
    la hora pico del día, o None si no aplica (función apagada, o la hora
    pico ya pasó => publicar de inmediato)."""
    import datetime as _dt
    pub = cfg.get("publicacion", {})
    if not pub.get("programar_para_hora_pico", False):
        return None
    hora_txt = str(pub.get("programar_hora_utc", "19:30")).strip()
    try:
        hh, mm = (int(x) for x in hora_txt.split(":"))
    except Exception:
        return None
    ahora = _dt.datetime.now(_dt.timezone.utc)
    objetivo = ahora.replace(hour=hh, minute=mm, second=0, microsecond=0)
    # margen de 10 min: si falta menos de eso (o ya pasó), publicar ya
    if objetivo <= ahora + _dt.timedelta(minutes=10):
        return None
    return objetivo.strftime("%Y-%m-%dT%H:%M:%S.0Z")


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
            # PUBLICACIÓN PROGRAMADA (idea del usuario, 21-ago-2026):
            # generar temprano y publicar a la hora pico. Si
            # publicacion.programar_para_hora_pico es true y la hora actual
            # es ANTERIOR a la hora pico del día, el video se sube PRIVADO
            # con publishAt => YouTube lo vuelve público exactamente a esa
            # hora (función nativa). Si ya pasó la hora pico, se publica
            # de inmediato como siempre. Ver _publish_at_hora_pico().
            # Declaración honesta de contenido sintético/alterado (soportado
            # por la API desde oct-2024). Nuestro video usa voz IA, guion IA
            # y (a veces) imágenes generadas por IA, así que lo correcto y lo
            # que reduce riesgo de sanción por "contenido inauténtico" es
            # declararlo siempre, no ocultarlo.
            "containsSyntheticMedia": True,
        },
    }


    # Aplicar programación si corresponde (nunca rompe: si algo falla,
    # se publica de inmediato como siempre)
    try:
        publish_at = _publish_at_hora_pico(cfg)
        if publish_at:
            body["status"]["privacyStatus"] = "private"
            body["status"]["publishAt"] = publish_at
            log(AGENT, f"Video PROGRAMADO: se sube privado y YouTube lo hará "
                       f"público automáticamente a las {publish_at} (hora pico).")
    except Exception as e:
        log(AGENT, f"Aviso: no se pudo programar la publicación ({e}); se publica ya.")

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

    # Registrar si quedó PROGRAMADO (privado hasta la hora pico): otros
    # agentes lo consultan para no comentar un video aún privado.
    if body["status"].get("publishAt"):
        try:
            from agents.utils import load_state, save_state
            estado = load_state()
            estado.setdefault("videos_programados", {})[video_id] = body["status"]["publishAt"]
            save_state(estado)
        except Exception:
            pass

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
