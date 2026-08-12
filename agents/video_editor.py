"""
AGENTE 5: EDITOR DE VIDEO ("Video Editor")
----------------------------------------------------
Ensambla el video final: narración (audio) + un clip/imagen DISTINTO por
cada "beat" del guion (cortes frecuentes, dinámicos, nunca un mismo plano
sostenido por mucho tiempo) + tarjeta de título por capítulo. Sigue las
reglas de ritmo del Agente Estratega Viral (agents/viral_strategist.py):
ningún corte dura menos de 3s ni más de 9s.

Soporta cualquier resolución (se usa tanto para el video largo 16:9 como
para el Short vertical 9:16 del agente shorts_creator.py). Cuando el
recurso original no tiene la misma proporción, se hace un recorte centrado
("cover crop") en vez de estirar la imagen, para que nunca se vea deformada.

Nota de rendimiento/memoria: se renderiza y CIERRA cada capítulo por
separado a disco, y al final solo se concatenan los .mp4 ya resueltos.
Esto evita agotar la RAM en videos largos con muchos clips de stock.
"""
import os
import gc
from PIL import Image, ImageDraw, ImageFont
from moviepy import AudioFileClip, ImageClip, VideoFileClip, concatenate_videoclips

from agents.utils import load_config, log
from agents.viral_strategist import DURACION_MIN_CORTE_SEG, DURACION_MAX_CORTE_SEG

AGENT = "EditorVideo"
RESOLUCION = (1280, 720)  # resolución por defecto del video largo (16:9)
DURACION_TARJETA_TITULO = 2.0  # segundos; expuesto para que agents/subtitulos.py calcule tiempos exactos


def _fuente(tam):
    ruta = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(ruta):
        return ImageFont.truetype(ruta, tam)
    return ImageFont.load_default()


def _cubrir_resolucion(clip, resolucion):
    """Redimensiona + recorta al centro (cover crop) para llenar exactamente
    la resolución objetivo SIN deformar la imagen/video, sin importar si el
    recurso original es horizontal o vertical."""
    w_obj, h_obj = resolucion
    w_actual, h_actual = clip.size
    escala = max(w_obj / w_actual, h_obj / h_actual)
    clip = clip.resized(escala)
    w_nuevo, h_nuevo = clip.size
    x0 = max(0, (w_nuevo - w_obj) / 2)
    y0 = max(0, (h_nuevo - h_obj) / 2)
    return clip.cropped(x1=x0, y1=y0, x2=x0 + w_obj, y2=y0 + h_obj)


def _tarjeta_titulo_capitulo(nombre_capitulo: str, carpeta_tmp: str, indice: int, resolucion=RESOLUCION) -> str:
    img = Image.new("RGB", resolucion, (20, 20, 25))
    draw = ImageDraw.Draw(img)
    tam_fuente = max(28, resolucion[0] // 22)
    font = _fuente(tam_fuente)
    texto = nombre_capitulo.upper()
    max_w = resolucion[0] * 0.85
    while draw.textlength(texto, font=font) > max_w and font.size > 20:
        font = _fuente(font.size - 4)
    tw = draw.textlength(texto, font=font)
    x = (resolucion[0] - tw) / 2
    y = resolucion[1] / 2 - font.size
    draw.text((x, y), texto, font=font, fill=(255, 210, 0))
    draw.line([(resolucion[0]/2 - 80, y + font.size + 20), (resolucion[0]/2 + 80, y + font.size + 20)],
              fill=(255, 210, 0), width=4)
    ruta = os.path.join(carpeta_tmp, f"titulo_cap{indice}.png")
    img.save(ruta)
    return ruta


def _ajustar_duraciones_a_ritmo(duraciones: list, total_real: float,
                                 min_seg=DURACION_MIN_CORTE_SEG, max_seg=DURACION_MAX_CORTE_SEG) -> list:
    """Aplica los límites de ritmo (ni muy corto/caótico ni muy largo/aburrido)
    definidos por el Estratega Viral. En vez de un simple reescalado
    proporcional (que puede deshacer el límite máximo si algún beat es muy
    largo) o concentrar todo el ajuste en un solo corte, reparte la
    diferencia necesaria para cuadrar con el audio real usando "water
    filling": primero se le da espacio a los cortes que tienen más margen
    disponible, respetando siempre el mínimo y el máximo. Así el ritmo se
    mantiene dinámico en TODOS los cortes, no solo en algunos."""
    n = len(duraciones)
    if n == 0:
        return duraciones
    valores = [min(max(d, min_seg), max_seg) for d in duraciones]

    for _ in range(4):
        diff = total_real - sum(valores)
        if abs(diff) < 0.05:
            break
        margenes = [(max_seg - v) for v in valores] if diff > 0 else [(v - min_seg) for v in valores]
        total_margen = sum(margenes)
        if total_margen <= 0.01:
            valores[-1] = max(0.5, valores[-1] + diff)  # último recurso: absorbe lo que quede
            break
        for i in range(n):
            valores[i] += diff * (margenes[i] / total_margen)
        valores = [min(max(v, min_seg), max_seg) for v in valores]

    return valores


def _fondo_respaldo_simple(destino_png, resolucion=RESOLUCION):
    """Último recurso absoluto (archivo corrupto/no descargable): un fondo
    neutro simple, 100% local, para que el video nunca falle por completo."""
    img = Image.new("RGB", resolucion, (35, 35, 40))
    img.save(destino_png)
    return destino_png


def _clip_desde_visual(visual, duracion, carpeta_tmp, resolucion=RESOLUCION):
    if visual["tipo"] == "video":
        try:
            clip = VideoFileClip(visual["ruta"])
            _ = clip.get_frame(0)  # detecta archivos corruptos aquí, con fallback controlado
            if clip.duration >= duracion:
                clip = clip.subclipped(0, duracion)
            else:
                copias = int(duracion // clip.duration) + 1
                clip = concatenate_videoclips([clip] * copias, method="chain").subclipped(0, duracion)
            clip = clip.without_audio().with_duration(duracion)
            return _cubrir_resolucion(clip, resolucion)
        except Exception as e:
            log(AGENT, f"Clip de video dañado/no legible, generando fondo de respaldo: {e}")
            ruta_fallback = os.path.join(carpeta_tmp, f"_fallback_{os.path.basename(visual['ruta'])}.png")
            _fondo_respaldo_simple(ruta_fallback, resolucion)
            return ImageClip(ruta_fallback).with_duration(duracion)

    try:
        clip = ImageClip(visual["ruta"]).with_duration(duracion)
        return _cubrir_resolucion(clip, resolucion)
    except Exception as e:
        log(AGENT, f"Imagen dañada/no legible, generando fondo de respaldo: {e}")
        ruta_fallback = os.path.join(carpeta_tmp, f"_fallback_{os.path.basename(visual['ruta'])}.png")
        _fondo_respaldo_simple(ruta_fallback, resolucion)
        return ImageClip(ruta_fallback).with_duration(duracion)


def _renderizar_capitulo(cap, audio_cap_info, visuales_cap, carpeta_salida, indice,
                          resolucion=RESOLUCION, con_tarjeta_titulo=True):
    """Renderiza UN capítulo a un .mp4 en disco, con un corte visual nuevo
    por cada beat (ritmo dinámico), y cierra todos sus recursos antes de
    devolver la ruta, para mantener el uso de memoria bajo control."""
    audio_clip = AudioFileClip(audio_cap_info["audio"])
    duracion_cap = audio_cap_info["duracion_total"]
    duraciones_beats = _ajustar_duraciones_a_ritmo(audio_cap_info["duraciones_beats"], duracion_cap)
    duracion_visual_real = sum(duraciones_beats)  # puede diferir en milisegundos del audio; usamos esta

    sub_clips = [_clip_desde_visual(v, d, carpeta_salida, resolucion)
                 for v, d in zip(visuales_cap, duraciones_beats)]
    video_capitulo = concatenate_videoclips(sub_clips, method="chain") if len(sub_clips) > 1 else sub_clips[0]
    # Usamos la duración REAL de lo ya renderizado (no la del audio) para evitar
    # pedirle a moviepy frames más allá de lo que el clip visual realmente tiene.
    audio_clip = audio_clip.with_duration(min(duracion_cap, duracion_visual_real)) if audio_clip.duration > duracion_visual_real else audio_clip
    video_capitulo = video_capitulo.with_duration(duracion_visual_real).with_audio(audio_clip)

    duracion_titulo = 0.0
    if con_tarjeta_titulo:
        ruta_tarjeta = _tarjeta_titulo_capitulo(cap["nombre"], carpeta_salida, indice, resolucion)
        duracion_titulo = DURACION_TARJETA_TITULO
        clip_titulo = ImageClip(ruta_tarjeta).with_duration(duracion_titulo).resized(resolucion)
        # Pista de audio silenciosa: evita que la concatenación se rompa si un
        # clip tiene audio (la narración) y otro no (la tarjeta de título).
        from moviepy import AudioClip as _AudioClip
        clip_titulo = clip_titulo.with_audio(_AudioClip(lambda t: 0, duration=duracion_titulo, fps=44100))
        capitulo_completo = concatenate_videoclips([clip_titulo, video_capitulo], method="chain")
    else:
        clip_titulo = None
        capitulo_completo = video_capitulo

    ruta_salida = os.path.join(carpeta_salida, f"_tmp_cap{indice}.mp4")
    capitulo_completo.write_videofile(
        ruta_salida, fps=24, codec="libx264", audio_codec="aac",
        threads=2, preset="veryfast", logger=None,
    )

    for c in sub_clips:
        try:
            c.close()
        except Exception:
            pass
    try:
        audio_clip.close()
        if clip_titulo:
            clip_titulo.close()
        video_capitulo.close()
        capitulo_completo.close()
    except Exception:
        pass
    gc.collect()

    return ruta_salida, duracion_titulo + duracion_visual_real


def construir_video(guion: dict, audio_info: dict, visuales_info: dict,
                     carpeta_salida: str, nombre_base: str,
                     resolucion=RESOLUCION, con_tarjetas_titulo=True,
                     ruta_musica_fondo: str = None, volumen_musica: float = 0.10):
    os.makedirs(carpeta_salida, exist_ok=True)
    carpeta_tmp = os.path.join(carpeta_salida, f"_tmp_{nombre_base}")
    os.makedirs(carpeta_tmp, exist_ok=True)
    rutas_capitulos = []
    timestamps_capitulos = []  # [(nombre, segundo_de_inicio), ...] para el índice de YouTube
    acumulado = 0.0

    total_caps = len(guion["capitulos"])
    for i, cap in enumerate(guion["capitulos"]):
        audio_cap_info = audio_info["capitulos"][i]
        visuales_cap = visuales_info["visuales_por_capitulo"][i]
        timestamps_capitulos.append((cap["nombre"], acumulado))

        ruta_cap, dur = _renderizar_capitulo(cap, audio_cap_info, visuales_cap, carpeta_tmp, i,
                                              resolucion, con_tarjetas_titulo)
        rutas_capitulos.append(ruta_cap)
        acumulado += dur
        log(AGENT, f"Capítulo {i+1}/{total_caps} listo con {len(visuales_cap)} cortes visuales "
                    f"({dur:.1f}s)")

    log(AGENT, "Uniendo todos los capítulos en el video final...")
    clips_finales = [VideoFileClip(p) for p in rutas_capitulos]
    video_final = concatenate_videoclips(clips_finales, method="chain")

    audio_musica = None
    if ruta_musica_fondo and os.path.exists(ruta_musica_fondo):
        try:
            import moviepy.audio.fx as afx
            from moviepy import CompositeAudioClip
            log(AGENT, "Mezclando música de fondo con la narración...")
            audio_musica = (AudioFileClip(ruta_musica_fondo)
                             .with_effects([afx.AudioLoop(duration=video_final.duration),
                                            afx.MultiplyVolume(volumen_musica)]))
            audio_mezclado = CompositeAudioClip([video_final.audio, audio_musica])
            video_final = video_final.with_audio(audio_mezclado)
        except Exception as e:
            log(AGENT, f"No se pudo mezclar la música de fondo ({e}). Se continúa solo con la narración.")

    salida = os.path.join(carpeta_salida, f"{nombre_base}.mp4")
    video_final.write_videofile(
        salida, fps=24, codec="libx264", audio_codec="aac",
        threads=2, preset="veryfast", logger=None,
    )

    for c in clips_finales:
        try:
            c.close()
        except Exception:
            pass
    if audio_musica:
        try:
            audio_musica.close()
        except Exception:
            pass
    video_final.close()

    import shutil
    shutil.rmtree(carpeta_tmp, ignore_errors=True)

    log(AGENT, "Render completado.")
    return salida, timestamps_capitulos




if __name__ == "__main__":
    from agents.trend_scout import buscar_ideas_potenciales
    from agents.scriptwriter import generar_guion
    from agents.voice import narrar_guion
    from agents.visuals import obtener_visuales_para_guion

    idea = buscar_ideas_potenciales()[0]
    guion = generar_guion(idea)
    audio_info = narrar_guion(guion, "output/audio", "demo_full4")
    visuales_info = obtener_visuales_para_guion(guion, "output/video/assets_demo_full4")
    ruta, timestamps = construir_video(guion, audio_info, visuales_info, "output/video", "demo_full4")
    print("Video generado en:", ruta)
    print("Timestamps:", timestamps)
