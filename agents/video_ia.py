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

# Presupuesto por video. HISTORIA: 6 con cuenta gratis (5 min GPU/día).
# Desde 29-ago-2026 la cuenta albertodouat es HF PRO ($9/mes, verificado
# por API isPro=True): 40 MINUTOS de GPU al día + prioridad máxima de cola
# + extensible con créditos. 22 clips ~= 8-11 min de GPU, deja de sobra
# para el Short y reintentos, y la vía anónima suma aparte.
MAX_CLIPS_IA_POR_VIDEO = 22

# Spaces con LTX (verificados vivos 29-ago-2026). Orden = calidad:
#   1) Lightricks/LTX-2.5 (OFICIAL, ago-2026): decoder de difusión nuevo
#      (0.28 fallos/clip vs 0.74 del 2.3), 4K HDR, multi-shot nativo,
#      duración automática. Endpoint /run.
#   2) Lightricks/ltx-video-distilled (el original probado). /text_to_video.
_SPACE_LTX25 = "Lightricks/LTX-2.5"
_SPACES_LTX = [
    "Lightricks/ltx-video-distilled",
]

_contador_clips = {"usados": 0}
_cliente_cache = {}

# CORTACIRCUITOS (30-ago-2026, corrida real de 2h44m diagnosticada): con la
# cuota agotada, CADA beat esperaba rechazos de LTX + hasta 300s de cola
# ZSky => ~2h de esperas inútiles acumuladas. Ahora, al primer síntoma
# claro de "no hay más clips hoy", el proveedor se apaga para el RESTO de
# la corrida y los beats caen a imagen al instante.
_apagados = {"ltx": False, "zsky_fallos": 0}
_MAX_FALLOS_ZSKY = 2


def _clientes_para(space: str, token: str):
    """Doble cuota v2 (era PRO, 29-ago-2026): con HF PRO el token da
    40 min/día y PRIORIDAD MÁXIMA de cola => se usa PRIMERO (rápido y
    casi sin abortos). La cuota anónima por IP queda de RESPALDO para
    cuando la de la cuenta se agote en corridas maratónicas."""
    from gradio_client import Client
    claves = [(space, token), (space, None)] if token else [(space, None)]
    for space_id, tok in claves:
        cache_key = f"{space_id}|{'tok' if tok else 'anon'}"
        try:
            if cache_key not in _cliente_cache:
                _cliente_cache[cache_key] = Client(space_id, token=tok,
                                                   verbose=False)
            yield _cliente_cache[cache_key], ("token" if tok else "anónimo")
        except Exception:
            continue


def _intentar_ltx25(prompt: str, destino_mp4: str, vertical: bool,
                    token: str):
    """LTX-2.5 oficial: mejor calidad open source de agosto 2026."""
    if _apagados["ltx"]:
        return None
    w, h = (768, 1152) if vertical else (1152, 768)
    for cliente, modo in _clientes_para(_SPACE_LTX25, token):
        try:
            t0 = time.time()
            r = cliente.predict(
                prompt=prompt[:900], image_path=None,
                height=h, width=w, duration_s=4,
                seed=42, decoder="diffusion", auto_len=False,
                randomize_seed=True, do_enhance=False,
                api_name="/run")
            ruta = r[0] if isinstance(r, (tuple, list)) else r
            if isinstance(ruta, dict):
                ruta = ruta.get("video") or ruta.get("path")
            if ruta and os.path.exists(ruta) and os.path.getsize(ruta) > 10000:
                shutil.copy(ruta, destino_mp4)
                log(AGENT, f"Clip LTX-2.5 ({modo}) en {time.time()-t0:.0f}s.")
                return destino_mp4
        except Exception as e:
            msg = str(e)[:90]
            log(AGENT, f"LTX-2.5 ({modo}) no disponible ({msg}).")
            if modo == "token" and ("quota" in msg.lower() or "exceeded" in msg.lower()):
                # cuota del token agotada; si el anónimo tampoco puede
                # (lo dirá su propio error), el bucle terminará y el
                # cortacircuitos de abajo hará el resto.
                pass
            continue
    return None


def _hf_token(cfg) -> str:
    tok = (cfg.get("apis", {}).get("hf_token", "") or "").strip()
    if tok and "OBTENER_GRATIS" not in tok:
        return tok
    return os.environ.get("HF_TOKEN", "").strip()


def reiniciar_presupuesto():
    _contador_clips["usados"] = 0
    _apagados["ltx"] = False
    _apagados["zsky_fallos"] = 0


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
    # RELOJ GLOBAL (31-ago-2026): pasado el presupuesto de generación,
    # cero clips IA nuevos — el video termina con lo que ya tiene.
    try:
        from agents.reloj import apurado
        if apurado():
            return None
    except Exception:
        pass

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

    # PRIMERO: LTX-2.5 oficial (mejor calidad ago-2026, decoder difusión,
    # menos artefactos). Con doble vía de cuota (anónima → token).
    ruta25 = _intentar_ltx25(prompt, destino_mp4, vertical, token)
    if ruta25:
        _contador_clips["usados"] += 1
        log(AGENT, f"Clip IA (LTX-2.5) {_contador_clips['usados']}/"
                   f"{MAX_CLIPS_IA_POR_VIDEO}: '{prompt_visual[:50]}'")
        return ruta25

    for space in _SPACES_LTX:
        if _apagados["ltx"]:
            break  # cortacircuitos: no insistir con cuota agotada
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
            # cuota agotada => CORTACIRCUITOS: apagar TODO LTX (2.5 y
            # distilled) para el resto de la corrida. OJO: ya NO se pone
            # usados=MAX (eso también bloqueaba a ZSky, que tiene SU propia
            # capacidad ilimitada independiente de ZeroGPU).
            if "quota" in msg.lower() or "exceeded" in msg.lower():
                _apagados["ltx"] = True
                log(AGENT, "Cuota ZeroGPU agotada: LTX apagado por el resto "
                           "de la corrida (los beats caen a ZSky/imagen al instante).")
            continue

    # RESPALDO ZSKY (Agente 42, 29-ago-2026): fuente gratis ilimitada
    # adicional de clips de 5s con audio, verificada en vivo. Se usa cuando
    # LTX/ZeroGPU no pudo (cuota agotada o Spaces caídos). El clip trae la
    # placa "MADE WITH zsky.ai" (free tier) y el QA visual decide si pasa.
    # Timeout de cola corto para nunca eternizar la corrida.
    if _apagados["zsky_fallos"] >= _MAX_FALLOS_ZSKY:
        return None
    try:
        from agents.proveedor_zsky import generar_clip
        # timeout corto (120s): si la cola gratuita de ZSky está lenta hoy,
        # mejor perder el clip que arrastrar la corrida (lección de la
        # corrida de 2h44m). 2 timeouts seguidos => ZSky apagado por hoy.
        ruta = generar_clip(prompt, destino_mp4, vertical=vertical,
                            timeout_cola=120)
        if ruta:
            _contador_clips["usados"] += 1
            _apagados["zsky_fallos"] = 0
            log(AGENT, f"Clip de respaldo ZSky usado "
                       f"({_contador_clips['usados']}/{MAX_CLIPS_IA_POR_VIDEO}).")
            return ruta
    except Exception as e:
        _apagados["zsky_fallos"] += 1
        log(AGENT, f"Respaldo ZSky no disponible ({str(e)[:80]}); "
                   f"fallo {_apagados['zsky_fallos']}/{_MAX_FALLOS_ZSKY} "
                   f"(al llegar al máximo se apaga por hoy).")
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
