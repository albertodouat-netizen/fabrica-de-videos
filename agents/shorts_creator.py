"""
AGENTE 11: CREADOR DE SHORTS ("Shorts Creator")
----------------------------------------------------
Responde al punto 2 del pedido: además del video largo, genera un YouTube
Short (vertical, 9:16, <60s) pensado para enganchar y llevar tráfico hacia
el video completo. Reutiliza el mismo guion/ángulo del video largo (el
gancho + los primeros beats más "jugosos" del capítulo 1) para no duplicar
trabajo de guion, pero:

  - Es 100% vertical (9:16), con recorte inteligente de los mismos clips.
  - Lleva subtítulos incrustados grandes (los Shorts se ven mayormente sin
    sonido, así que el texto en pantalla es clave para retener).
  - Termina con una tarjeta de llamada a la acción clara hacia el video
    largo ("Mira el video completo, link en la descripción").
  - Se sube por separado, con su propio título/descripción que enlaza al
    video largo y la etiqueta #Shorts.
"""
import os
import gc
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip, VideoFileClip

from agents.utils import load_config, log, limpiar_texto_para_voz
from agents.video_editor import _clip_desde_visual, _fondo_respaldo_simple, _ajustar_duraciones_a_ritmo
from agents.visuals import obtener_visuales_para_guion
from agents.voice import narrar_guion

AGENT = "ShortsCreator"
RESOLUCION_SHORT = (720, 1280)   # 720p vertical: se ve nítido en móvil y usa mucha menos RAM/CPU
MAX_BEATS_SHORT = 4          # cuántos beats del capítulo 1 se reutilizan (antes del CTA)
DURACION_MAX_OBJETIVO = 50   # segundos, sin contar la tarjeta final de CTA
DURACION_MIN_CORTE_SHORT = 2.0   # cortes más rápidos que el video largo (ideal para Shorts)
DURACION_MAX_CORTE_SHORT = 5.0


def _fuente(tam):
    ruta = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(ruta):
        return ImageFont.truetype(ruta, tam)
    return ImageFont.load_default()


def _generar_subtitulo_png(texto: str, destino_png: str, resolucion=RESOLUCION_SHORT):
    """Genera un PNG transparente con el subtítulo grande estilo Shorts,
    para superponerlo sobre el clip de fondo de ese beat."""
    escala = resolucion[1] / 1920  # las medidas base están pensadas para 1920px de alto
    img = Image.new("RGBA", resolucion, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _fuente(int(64 * escala))
    texto = texto.upper()

    max_w = resolucion[0] * 0.85
    palabras = texto.split()
    linea, lineas = "", []
    for palabra in palabras:
        prueba = (linea + " " + palabra).strip()
        if draw.textlength(prueba, font=font) > max_w:
            lineas.append(linea)
            linea = palabra
        else:
            linea = prueba
    if linea:
        lineas.append(linea)
    lineas = lineas[:4]

    alto_linea = int(78 * escala)
    alto_bloque = len(lineas) * alto_linea
    y0 = resolucion[1] - int(420 * escala) - alto_bloque
    for i, ln in enumerate(lineas):
        tw = draw.textlength(ln, font=font)
        x = (resolucion[0] - tw) / 2
        y = y0 + i * alto_linea
        borde = max(2, int(3 * escala))
        for dx in (-borde, borde):
            for dy in (-borde, borde):
                draw.text((x + dx, y + dy), ln, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), ln, font=font, fill=(255, 255, 255, 255))

    img.save(destino_png)
    return destino_png


def _tarjeta_cta_final(destino_png, titulo_video_largo: str, resolucion=RESOLUCION_SHORT):
    escala = resolucion[1] / 1920
    img = Image.new("RGB", resolucion, (15, 15, 20))
    draw = ImageDraw.Draw(img)
    font_grande = _fuente(int(72 * escala))
    font_chica = _fuente(int(40 * escala))

    texto1 = "MIRA EL VIDEO"
    texto2 = "COMPLETO ⬆️"
    for i, (texto, font) in enumerate([(texto1, font_grande), (texto2, font_grande)]):
        tw = draw.textlength(texto, font=font)
        draw.text(((resolucion[0]-tw)/2, resolucion[1]/2 - int(220*escala) + i*int(90*escala)), texto,
                   font=font, fill=(255, 210, 0))

    tw = draw.textlength("Y suscríbete, es gratis", font=font_chica)
    draw.text(((resolucion[0]-tw)/2, resolucion[1]/2 - int(60*escala)), "Y suscríbete, es gratis",
               font=font_chica, fill=(255, 255, 255))
    tw2 = draw.textlength("Link en la descripción", font=font_chica)
    draw.text(((resolucion[0]-tw2)/2, resolucion[1]/2 + int(10*escala)), "Link en la descripción",
               font=font_chica, fill=(200, 200, 200))

    # título del video largo, envuelto en varias líneas
    max_w = resolucion[0] * 0.8
    palabras = titulo_video_largo.split()
    linea, lineas = "", []
    for palabra in palabras:
        prueba = (linea + " " + palabra).strip()
        if draw.textlength(prueba, font=font_chica) > max_w:
            lineas.append(linea)
            linea = palabra
        else:
            linea = prueba
    if linea:
        lineas.append(linea)
    y0 = resolucion[1]/2 + int(60*escala)
    for i, ln in enumerate(lineas[:3]):
        tw = draw.textlength(ln, font=font_chica)
        draw.text(((resolucion[0]-tw)/2, y0 + i*int(48*escala)), ln, font=font_chica, fill=(200, 200, 200))

    img.save(destino_png)
    return destino_png



def _armar_mini_guion(guion: dict) -> dict:
    """Construye un guion reducido para el Short: gancho + primeros beats
    jugosos del capítulo 1 + un beat final de llamada a la acción.

    Se excluyen a propósito los beats de llamado a suscripción (ver
    agents/suscripcion_cta.py): esos 3 momentos son para el video LARGO;
    el Short ya tiene su propia tarjeta final de cierre (ver
    _tarjeta_cta_final), que además ahora también invita a suscribirse."""
    primer_capitulo = guion["capitulos"][0]
    beats_disponibles = [b for b in primer_capitulo.get("beats", []) if not b.get("es_llamado_suscripcion")]
    beats_originales = beats_disponibles[:MAX_BEATS_SHORT]

    beats_short = []
    if guion.get("gancho"):
        beats_short.append({
            "texto": limpiar_texto_para_voz(guion["gancho"]),
            "visual": beats_originales[0]["visual"] if beats_originales else "persona sorprendida mirando a cámara",
        })
    beats_short.extend(beats_originales)
    beats_short.append({
        "texto": "Te cuento todos los detalles en el video completo de mi canal.",
        "visual": "persona sonriendo y señalando hacia arriba con el dedo",
    })

    return {
        "titulo": guion["titulo"],
        "capitulos": [{"nombre": "short", "beats": beats_short}],
    }


def crear_short(guion: dict, carpeta_salida: str, nombre_base: str, url_video_largo: str = "") -> tuple:
    """Genera el Short completo. Devuelve (ruta_mp4, titulo_short, descripcion_short)."""
    os.makedirs(carpeta_salida, exist_ok=True)
    mini_guion = _armar_mini_guion(guion)

    log(AGENT, "Narrando el guion reducido del Short...")
    audio_info = narrar_guion(mini_guion, os.path.join(carpeta_salida, "audio"), nombre_base)

    log(AGENT, "Buscando visuales verticales (9:16) para el Short...")
    visuales_info = obtener_visuales_para_guion(
        mini_guion, os.path.join(carpeta_salida, f"assets_{nombre_base}"), orientacion="portrait"
    )

    beats = mini_guion["capitulos"][0]["beats"]
    audio_cap = audio_info["capitulos"][0]
    visuales_cap = visuales_info["visuales_por_capitulo"][0]
    # Ritmo más rápido que el video largo (2 a 5s por corte, como recomienda
    # la investigación de retención para formato Short/vertical).
    duraciones = _ajustar_duraciones_a_ritmo(audio_cap["duraciones_beats"], audio_cap["duracion_total"],
                                              min_seg=DURACION_MIN_CORTE_SHORT, max_seg=DURACION_MAX_CORTE_SHORT)

    carpeta_tmp = os.path.join(carpeta_salida, f"_tmp_{nombre_base}")
    os.makedirs(carpeta_tmp, exist_ok=True)

    rutas_beats_mp4 = []
    duraciones_reales_usadas = []
    for idx, (beat, visual, dur) in enumerate(zip(beats, visuales_cap, duraciones)):
        dur = max(1.5, dur)
        duraciones_reales_usadas.append(dur)
        clip_fondo = _clip_desde_visual(visual, dur, carpeta_tmp, RESOLUCION_SHORT)
        ruta_sub = os.path.join(carpeta_tmp, f"sub_{idx}.png")
        _generar_subtitulo_png(beat["texto"], ruta_sub)
        clip_sub = ImageClip(ruta_sub).with_duration(dur)
        clip_compuesto = CompositeVideoClip([clip_fondo, clip_sub], size=RESOLUCION_SHORT).with_duration(dur)

        ruta_beat_mp4 = os.path.join(carpeta_tmp, f"_beat{idx}.mp4")
        clip_compuesto.write_videofile(ruta_beat_mp4, fps=30, codec="libx264", audio_codec="aac",
                                        threads=2, preset="veryfast", logger=None)
        rutas_beats_mp4.append(ruta_beat_mp4)

        try:
            clip_fondo.close()
            clip_sub.close()
            clip_compuesto.close()
        except Exception:
            pass
        del clip_fondo, clip_sub, clip_compuesto
        gc.collect()
        log(AGENT, f"Beat {idx+1}/{len(beats)} del Short listo y renderizado a disco ({dur:.1f}s)")

    log(AGENT, "Uniendo los beats narrados con audio...")
    clips_video_beats = [VideoFileClip(p) for p in rutas_beats_mp4]
    # Usamos la duración REAL ya codificada de cada archivo (puede variar unos
    # milisegundos por redondeo de frames respecto a lo solicitado), no la
    # duración teórica que pedimos antes de renderizar.
    duracion_visual_real = sum(c.duration for c in clips_video_beats)
    video_narrado = concatenate_videoclips(clips_video_beats, method="chain")
    audio_clip = AudioFileClip(audio_cap["audio"])
    # Usamos la duración REAL de lo ya renderizado (no la cruda del audio) para
    # evitar pedirle a moviepy frames más allá de lo que el video visual tiene.
    if audio_clip.duration > duracion_visual_real:
        audio_clip = audio_clip.with_duration(duracion_visual_real)
    video_narrado = video_narrado.with_duration(duracion_visual_real).with_audio(audio_clip)

    ruta_cta = _tarjeta_cta_final(os.path.join(carpeta_tmp, "cta.png"), guion["titulo"])
    duracion_cta = 3.0
    clip_cta = ImageClip(ruta_cta).with_duration(duracion_cta)
    # Le agregamos una pista de audio silenciosa: si un clip de la concatenación
    # tiene audio y otro no, moviepy puede romperse al armar la pista final.
    from moviepy import AudioClip as _AudioClip
    silencio_cta = _AudioClip(lambda t: 0, duration=duracion_cta, fps=44100)
    clip_cta = clip_cta.with_audio(silencio_cta)


    video_final = concatenate_videoclips([video_narrado, clip_cta], method="chain")

    salida = os.path.join(carpeta_salida, f"{nombre_base}_short.mp4")
    log(AGENT, f"Renderizando Short -> {salida} ...")
    video_final.write_videofile(
        salida, fps=30, codec="libx264", audio_codec="aac",
        threads=2, preset="veryfast", logger=None,
    )

    for c in clips_video_beats:
        try:
            c.close()
        except Exception:
            pass
    audio_clip.close()
    video_narrado.close()
    video_final.close()

    import shutil
    shutil.rmtree(carpeta_tmp, ignore_errors=True)
    shutil.rmtree(os.path.join(carpeta_salida, f"assets_{nombre_base}"), ignore_errors=True)
    shutil.rmtree(os.path.join(carpeta_salida, "audio"), ignore_errors=True)

    titulo_short = (guion["titulo"][:80] + " 😱 #Shorts").strip()
    descripcion_short = (
        f"{guion.get('gancho', '')}\n\n"
        f"👉 Mira el video COMPLETO en mi canal: {url_video_largo}\n\n"
        f"#Shorts #{mini_guion['titulo'][:20].replace(' ', '')}"
    )

    log(AGENT, "Render del Short completado.")
    return salida, titulo_short, descripcion_short



if __name__ == "__main__":
    from agents.trend_scout import buscar_ideas_potenciales
    from agents.scriptwriter import generar_guion

    idea = buscar_ideas_potenciales()[0]
    guion = generar_guion(idea)
    ruta, titulo, descripcion = crear_short(guion, "output/video", "demo_short",
                                             url_video_largo="https://youtube.com/watch?v=EJEMPLO")
    print(ruta)
    print(titulo)
    print(descripcion)
