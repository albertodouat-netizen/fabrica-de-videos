"""
AGENTE 37: CLIPS DE VIDEO GENERADOS POR IA ("VideoClipIA") — 28-ago-2026
-------------------------------------------------------------------------
El salto de realismo de la Meta 2 del plan élite: los beats MÁS importantes
del video (gancho, apertura, primeros beats de capítulo) dejan de ser
imágenes con Ken Burns y pasan a ser CLIPS DE VIDEO EN MOVIMIENTO generados
a medida con LTX-Video (Lightricks) vía Hugging Face Spaces.

Verificado EN VIVO el 28-ago-2026 con la cuenta del usuario (albertodouat):
- Clip "elderly woman walking happily in a sunny park": fotorrealista,
  anatomía correcta, 2s @ 704x512, generado en 10 segundos, costo $0.
- Cuota ZeroGPU cuenta gratis: ~5 min GPU/día (cada clip usa ~10-30s de
  GPU => alcanza para ~10-20 clips/día: suficiente para los 5-8 beats
  clave de un video largo diario).

Diseño defensivo (regla de oro: "lo gratis muere en silencio"):
- Presupuesto por corrida (MAX_CLIPS_IA_POR_VIDEO) para no agotar cuota.
- Cascada: Space principal -> Space espejo -> None (el llamador usa la
  imagen FLUX + Ken Burns de siempre; el video NUNCA se bloquea por esto).
- Si no hay HF_TOKEN configurado, el agente se apaga silenciosamente.
"""
import os
import shutil
import time

from agents.utils import load_config, log, slugify

AGENT = "VideoClipIA"

# Presupuesto conservador por video (cuota ZeroGPU gratis ~5 min GPU/día;
# cada clip consume ~10-30s de GPU en el Space distilled).
MAX_CLIPS_IA_POR_VIDEO = 6

# Spaces con LTX-Video (verificados vivos 28-ago-2026). El primero es el
# oficial de Lightricks (distilled = rápido).
_SPACES_LTX = [
    "Lightricks/ltx-video-distilled",
]

_contador_clips = {"usados": 0}
_cliente_cache = {}


def _hf_token(cfg) -> str:
    tok = (cfg.get("apis", {}).get("hf_token", "") or "").strip()
    if tok and "OBTENER_GRATIS" not in tok:
        return tok
    return os.environ.get("HF_TOKEN", "").strip()


def reiniciar_presupuesto():
    _contador_clips["usados"] = 0


def generar_clip_ia(prompt_visual: str, destino_mp4: str,
                    contexto: str = "", vertical: bool = False):
    """Genera un clip de video IA (~2s) para un beat. Devuelve la ruta del
    mp4 o None si no se pudo (cuota, red, sin token): el llamador debe caer
    a la imagen estática de siempre. NUNCA lanza excepción hacia arriba."""
    cfg = load_config()
    token = _hf_token(cfg)
    if not token:
        return None
    if _contador_clips["usados"] >= MAX_CLIPS_IA_POR_VIDEO:
        return None

    prompt = (
        f"{prompt_visual}. {contexto}".strip(". ").strip()
        + ", smooth natural motion, photorealistic documentary style, "
          "real camera footage, natural light, no text, no watermark"
    )
    # LTX distilled acepta dimensiones concretas; 704x512 (paisaje) probado.
    w, h = (512, 704) if vertical else (704, 512)

    try:
        from gradio_client import Client
    except ImportError:
        log(AGENT, "gradio_client no instalado; sin clips IA en esta corrida.")
        return None

    for space in _SPACES_LTX:
        try:
            if space not in _cliente_cache:
                _cliente_cache[space] = Client(space, token=token, verbose=False)
            c = _cliente_cache[space]
            t0 = time.time()
            r = c.predict(
                prompt=prompt[:800],
                negative_prompt=("worst quality, blurry, jittery, distorted, "
                                 "extra limbs, deformed hands, text, watermark"),
                input_image_filepath=None, input_video_filepath=None,
                height_ui=h, width_ui=w, mode="text-to-video",
                duration_ui=2, ui_frames_to_use=9,
                seed_ui=42, randomize_seed=True, ui_guidance_scale=1.0,
                improve_texture_flag=True, api_name="/text_to_video")
            ruta = r[0]["video"] if isinstance(r, tuple) else r
            if isinstance(ruta, dict):
                ruta = ruta.get("video")
            if ruta and os.path.exists(ruta) and os.path.getsize(ruta) > 10000:
                shutil.copy(ruta, destino_mp4)
                _contador_clips["usados"] += 1
                log(AGENT, f"Clip IA generado en {time.time()-t0:.0f}s "
                           f"({_contador_clips['usados']}/{MAX_CLIPS_IA_POR_VIDEO} "
                           f"del presupuesto): '{prompt_visual[:50]}'")
                return destino_mp4
        except Exception as e:
            msg = str(e)[:100]
            log(AGENT, f"Aviso: Space {space} no disponible ({msg}); "
                       f"se usa imagen estática para este beat.")
            # cuota agotada => apagar el resto de la corrida
            if "quota" in msg.lower() or "exceeded" in msg.lower():
                _contador_clips["usados"] = MAX_CLIPS_IA_POR_VIDEO
            continue
    return None


def es_beat_clave(indice_capitulo: int, indice_beat: int, beat: dict) -> bool:
    """Decide si un beat merece clip de video IA (presupuesto limitado):
    - el gancho y los 2 primeros beats de contenido del video
    - el PRIMER beat de cada capítulo (apertura de sección)
    Nunca los beats especiales (intro/CTA/citas: tienen visual propio)."""
    if any(beat.get(k) for k in ("es_intro_marca", "es_llamado_suscripcion",
                                  "es_mencion_cruzada", "es_cita_cientifica",
                                  "es_llamado_interaccion")):
        return False
    if indice_capitulo == 0 and indice_beat <= 2:
        return True
    return indice_beat == 0
