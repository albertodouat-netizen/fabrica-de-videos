"""
AGENTE 12: SUBTÍTULOS ("Subtitulos")
----------------------------------------------------
Genera un archivo .srt con los tiempos REALES de cada beat (reconstruidos
exactamente igual que el EditorVideo, para que coincidan al milisegundo con
el video final) y lo sube como subtítulo/closed-caption oficial del video
vía la YouTube Data API (100% gratis, con tu misma cuenta ya autorizada).

Por qué importa (no es solo "por si acaso"):
  - Mejora el SEO: YouTube indexa cada palabra hablada, lo que ayuda a
    aparecer en más búsquedas.
  - Mejora la retención: muchos espectadores ven con el sonido apagado.
  - Los subtítulos SUBIDOS MANUALMENTE (o por API) pesan más para el
    algoritmo que los autogenerados automáticamente por YouTube.

Requiere el scope OAuth "youtube.force-ssl" (ya incluido). Si autorizaste
tu cuenta ANTES de este cambio, tendrás que volver a ejecutar
setup_youtube_auth.py una sola vez para que el permiso quede activo.
"""
import os

from agents.utils import log
from agents.video_editor import (
    DURACION_TARJETA_TITULO, DURACION_MIN_CORTE_SEG, DURACION_MAX_CORTE_SEG,
    _ajustar_duraciones_a_ritmo,
)

AGENT = "Subtitulos"


def _formato_srt_tiempo(segundos: float) -> str:
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    ms = int((segundos - int(segundos)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generar_srt(guion: dict, audio_info: dict, ruta_salida: str) -> str:
    """Reconstruye la misma línea de tiempo que usó el EditorVideo (tarjeta
    de título + duraciones de cada beat ajustadas al mismo ritmo) para que
    el .srt quede perfectamente sincronizado con el video final."""
    lineas = []
    numero = 1
    acumulado = 0.0

    for cap in guion["capitulos"]:
        acumulado += DURACION_TARJETA_TITULO  # la tarjeta de título no lleva subtítulo

    acumulado = 0.0
    for i, cap in enumerate(guion["capitulos"]):
        acumulado += DURACION_TARJETA_TITULO
        audio_cap = audio_info["capitulos"][i]
        duraciones = _ajustar_duraciones_a_ritmo(
            audio_cap["duraciones_beats"], audio_cap["duracion_total"],
            DURACION_MIN_CORTE_SEG, DURACION_MAX_CORTE_SEG,
        )
        beats = cap.get("beats", [])
        for beat, dur in zip(beats, duraciones):
            inicio = acumulado
            fin = acumulado + dur
            lineas.append(f"{numero}")
            lineas.append(f"{_formato_srt_tiempo(inicio)} --> {_formato_srt_tiempo(fin)}")
            lineas.append(beat["texto"])
            lineas.append("")
            numero += 1
            acumulado = fin

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))

    log(AGENT, f"Subtítulos generados -> {ruta_salida} ({numero - 1} líneas)")
    return ruta_salida


def subir_subtitulos(video_id: str, ruta_srt: str, idioma: str = "es") -> bool:
    import googleapiclient.discovery
    import googleapiclient.http
    from agents.publisher import _obtener_credenciales
    from agents.utils import load_config

    cfg = load_config()
    try:
        creds = _obtener_credenciales(cfg)
        youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        media = googleapiclient.http.MediaFileUpload(ruta_srt, mimetype="application/octet-stream")
        youtube.captions().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "language": idioma,
                    "name": "Español (automático)",
                    "isDraft": False,
                }
            },
            media_body=media,
        ).execute()
        log(AGENT, f"Subtítulos subidos correctamente al video {video_id}.")
        return True
    except Exception as e:
        log(AGENT, f"No se pudieron subir los subtítulos ({e}). "
                    f"Si acabas de agregar el scope 'youtube.force-ssl', vuelve a ejecutar "
                    f"setup_youtube_auth.py una sola vez para renovar el permiso.")
        return False
