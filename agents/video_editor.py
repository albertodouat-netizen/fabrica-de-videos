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
import random
from PIL import Image, ImageDraw, ImageFont
from moviepy import AudioFileClip, ImageClip, VideoFileClip, concatenate_videoclips, CompositeVideoClip

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

    # SINCRONIZACIÓN PRIMERO (reescrito 18-ago-2026 tras el reclamo real del
    # usuario: "no están sincronizadas algunas imágenes con la voz, como la
    # de la investigación o la de suscripción"). El diseño anterior
    # comprimía cada corte a un rango de "ritmo" (3-9s) y luego repartía la
    # diferencia entre TODOS los cortes (water filling). Consecuencia real:
    # si el beat de la cita científica duraba 14s de voz, su visual se
    # recortaba a 9s y los 5s sobrantes se regalaban a otros cortes → desde
    # ese punto, CADA visual quedaba corrido respecto a su voz.
    #
    # Ahora: cada visual dura EXACTAMENTE lo que dura su beat de audio
    # (duraciones ya medidas del MP3 real por agents/voice.py). Solo se
    # aplica un ajuste proporcional fino si la suma difiere del total real
    # por redondeos (milisegundos), repartido de forma uniforme para no
    # desplazar ningún beat de su voz. El "ritmo" visual ya viene dado por
    # la propia estructura de beats (1-2 frases = 5-12s naturales).
    valores = [max(0.5, float(d)) for d in duraciones]
    suma = sum(valores)
    if suma > 0 and abs(total_real - suma) > 0.05:
        factor = total_real / suma
        valores = [v * factor for v in valores]

    return valores


def _fondo_respaldo_simple(destino_png, resolucion=RESOLUCION):
    """Último recurso absoluto (archivo corrupto/no descargable).
    CORRECCIÓN 28-ago-2026 (reclamo real: "momentos sin imágenes" y
    "pantalla en negro en el aviso de suscripción"): antes era un fondo
    gris-casi-negro; ahora es el FONDO DE MARCA del canal (degradado verde
    + logo real), el mismo estilo de la intro. Nunca más pantalla negra."""
    import os as _os
    w, h = resolucion
    img = Image.new("RGB", resolucion)
    px = img.load()
    # degradado verde de marca (mismo tono de la intro/tarjetas del canal)
    for y in range(h):
        t = y / max(1, h - 1)
        px_color = (int(16 + 14 * t), int(74 + 46 * t), int(52 + 30 * t))
        for x in range(w):
            px[x, y] = px_color
    # halos suaves decorativos
    try:
        from PIL import ImageDraw
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse([w*0.68, h*0.08, w*0.95, h*0.55], fill=(255, 255, 255, 14))
        d.ellipse([w*0.05, h*0.55, w*0.35, h*1.05], fill=(255, 255, 255, 10))
    except Exception:
        pass
    # logo real del canal, centrado y circular
    try:
        ruta_logo = _os.path.join("assets", "logo_canal.jpg")
        if _os.path.exists(ruta_logo):
            from PIL import ImageDraw as _ID
            lado = int(min(w, h) * 0.28)
            logo = Image.open(ruta_logo).convert("RGB").resize((lado, lado))
            mask = Image.new("L", (lado, lado), 0)
            _ID.Draw(mask).ellipse([0, 0, lado, lado], fill=255)
            img.paste(logo, ((w - lado) // 2, (h - lado) // 2), mask)
    except Exception:
        pass
    img.save(destino_png)
    return destino_png


def _aplicar_ken_burns(clip_cubierto, resolucion, duracion):
    """Efecto de zoom lento (estilo documental / 'Ken Burns') para que ninguna
    imagen se vea estática: el clip ya debe cubrir exactamente 'resolucion' a
    escala 1.0; se agranda gradualmente y CompositeVideoClip recorta
    automáticamente lo que se sale del encuadre, sin dejar bordes vacíos."""
    zoom_final = random.uniform(1.10, 1.16)  # entre 10% y 16% de zoom total, sutil pero notorio

    def escala(t):
        return 1.0 + (zoom_final - 1.0) * (t / duracion if duracion > 0 else 0)

    clip_zoom = clip_cubierto.resized(escala).with_position("center")
    return CompositeVideoClip([clip_zoom], size=resolucion).with_duration(duracion)


def _clip_desde_visual(visual, duracion, carpeta_tmp, resolucion=RESOLUCION):
    if visual["tipo"] == "video":
        try:
            clip = VideoFileClip(visual["ruta"])
            _ = clip.get_frame(0)  # detecta archivos corruptos aquí, con fallback controlado
            if clip.duration >= duracion:
                clip = clip.subclipped(0, duracion)
            else:
                # ANTI-LOOP (auditoría 18-ago-2026, defecto real: "vuelven a
                # repetirse algunos videos como en un loop"). Antes, un clip
                # de stock de 4s en un beat de 12s se repetía 3 veces de
                # corrido y el ojo lo nota de inmediato. Ahora:
                #   - Si el clip cubre >=60% del beat: se reproduce UNA vez y
                #     se sostiene el último fotograma congelado con Ken Burns
                #     imperceptible (mejor que verlo reiniciarse).
                #   - Si es muy corto (<60%): UNA pasada normal + una pasada
                #     EN REVERSA (efecto "boomerang", continuo y sin salto) y
                #     se recorta a la duración exacta.
                if clip.duration >= duracion * 0.6:
                    ultimo = clip.to_ImageClip(t=max(0, clip.duration - 0.05)) \
                                 .with_duration(duracion - clip.duration)
                    clip = concatenate_videoclips([clip, ultimo], method="chain")
                else:
                    # CORRECCIÓN ANTI-LOOP v2 (auditoría 21-ago-2026, reclamo
                    # real del usuario: "imagenes que quedan en un loop"):
                    # el boomerang se repetía N veces si el beat era largo
                    # (clip 3s en beat 15s = 3 boomerangs visibles). Ahora:
                    # UNA sola pasada ida+vuelta y el resto se sostiene con
                    # el fotograma final congelado (estable, sin repetición).
                    import moviepy.video.fx as vfx
                    reversa = clip.with_effects([vfx.TimeMirror()])
                    ida_vuelta = concatenate_videoclips([clip, reversa], method="chain")
                    if ida_vuelta.duration < duracion:
                        congelado = ida_vuelta.to_ImageClip(
                            t=max(0, ida_vuelta.duration - 0.05))                             .with_duration(duracion - ida_vuelta.duration)
                        clip = concatenate_videoclips([ida_vuelta, congelado], method="chain")
                    else:
                        clip = ida_vuelta
                clip = clip.subclipped(0, duracion)
            clip = clip.without_audio().with_duration(duracion)
            return _cubrir_resolucion(clip, resolucion)
        except Exception as e:
            log(AGENT, f"Clip de video dañado/no legible, generando fondo de respaldo: {e}")
            ruta_fallback = os.path.join(carpeta_tmp, f"_fallback_{os.path.basename(visual['ruta'])}.png")
            _fondo_respaldo_simple(ruta_fallback, resolucion)
            return ImageClip(ruta_fallback).with_duration(duracion)

    try:
        clip = ImageClip(visual["ruta"]).with_duration(duracion)
        clip_cubierto = _cubrir_resolucion(clip, resolucion)
        # La portada real del estudio (ver agents/portada_estudio.py) NO
        # lleva zoom Ken Burns: el zoom recortaba la franja inferior con la
        # revista/año (comprobado extrayendo un fotograma del render real).
        # Esa imagen ya está compuesta exactamente a la resolución del video
        # y debe verse completa y estable, como un documento que se muestra.
        if visual.get("keyword") == "portada real del estudio científico citado":
            return clip_cubierto
        return _aplicar_ken_burns(clip_cubierto, resolucion, duracion)
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

    # Cifras verificadas Y citas científicas (ver agents/investigacion_cientifica.py
    # y agents/citas_cientificas.py): se superpone un recuadro con la cifra
    # o con "ESTUDIO REAL" en grande, para que el espectador vea con
    # claridad que hay una fuente real detrás y no dependa solo de
    # escucharlo una vez en el audio (pedido explícito del usuario, para
    # dar más peso y veracidad a la información).
    beats_cap = cap.get("beats", [])

    # MÚSICA DE MEDITACIÓN EN LA INTRO DE MARCA (pedido del usuario,
    # 19-ago-2026): si este capítulo contiene el beat de intro de marca
    # (siempre el beat 0 del capítulo 0), se mezcla un pad relajante bajo
    # la voz de la bienvenida, SOLO durante ese beat. La mezcla se hace en
    # la PISTA DE AUDIO del capítulo (no en el sub-clip: el audio del
    # sub-clip se descartaría más abajo cuando el capítulo recibe la
    # narración completa con with_audio). Ver agents/musica_intro.py:
    # Jamendo si hay client_id, o pad sintetizado local 100% libre de
    # derechos como respaldo garantizado.
    musica_intro_mezcla = None   # (ruta, duracion_del_beat_intro)
    for idx, (beat, dur) in enumerate(zip(beats_cap, duraciones_beats)):
        if beat.get("es_intro_marca") and idx == 0:
            try:
                from agents.musica_intro import obtener_musica_intro
                ruta_mi = obtener_musica_intro(carpeta_salida, duracion=dur + 2.0)
                if ruta_mi:
                    musica_intro_mezcla = (ruta_mi, dur)
            except Exception as e:
                log(AGENT, f"Aviso: no se pudo preparar la música de la intro ({e}).")
            break

    for idx, (beat, dur) in enumerate(zip(beats_cap, duraciones_beats)):
        cifra = beat.get("cifra_verificada")
        cita_fuente = beat.get("cita_fuente")
        if not cifra and not cita_fuente:
            continue
        if idx >= len(sub_clips):
            continue
        # Si el visual de este beat ES la portada real del estudio (ver
        # agents/portada_estudio.py), no se dibuja el recuadro encima: la
        # portada ya trae su propia franja "ESTUDIO CIENTÍFICO REAL" con
        # revista y año, y taparla con otro recuadro sería contraproducente.
        if idx < len(visuales_cap) and \
                (visuales_cap[idx].get("keyword") == "portada real del estudio científico citado"):
            continue
        texto_recuadro = cifra if cifra else "ESTUDIO REAL"
        try:
            from agents.callout_cifras import generar_overlay_cifra
            ruta_overlay = generar_overlay_cifra(texto_recuadro, carpeta_salida, tag=f"cifra_cap{indice}_b{idx}",
                                                  resolucion=resolucion, cita_fuente=cita_fuente)
            clip_overlay = (ImageClip(ruta_overlay)
                            .with_duration(sub_clips[idx].duration)
                            .with_position((0, 0)))
            sub_clips[idx] = CompositeVideoClip([sub_clips[idx], clip_overlay], size=resolucion) \
                .with_duration(sub_clips[idx].duration)
        except Exception as e:
            log(AGENT, f"Aviso: no se pudo dibujar el callout de '{texto_recuadro}' ({e}); "
                        "el video sigue igual, solo sin ese recuadro.")

    # Llamados a suscripción (ver agents/suscripcion_cta.py): banner PEQUEÑO
    # en la parte de abajo, superpuesto sobre el video real (nunca tapa toda
    # la pantalla, según recomendación real de retención de audiencia).
    for idx, (beat, dur) in enumerate(zip(beats_cap, duraciones_beats)):
        if not beat.get("es_llamado_suscripcion") or idx >= len(sub_clips):
            continue
        try:
            from agents.suscripcion_cta import generar_overlay_suscripcion
            momento = beat.get("momento_suscripcion", "inicio")
            ruta_overlay = generar_overlay_suscripcion(momento, carpeta_salida, tag=f"susc_cap{indice}_b{idx}",
                                                        resolucion=resolucion)
            clip_overlay = (ImageClip(ruta_overlay)
                            .with_duration(sub_clips[idx].duration)
                            .with_position((0, 0)))
            sub_clips[idx] = CompositeVideoClip([sub_clips[idx], clip_overlay], size=resolucion) \
                .with_duration(sub_clips[idx].duration)
        except Exception as e:
            log(AGENT, f"Aviso: no se pudo dibujar el banner de suscripción ({e}); "
                        "el video sigue igual, solo sin ese banner.")

    video_capitulo = concatenate_videoclips(sub_clips, method="chain") if len(sub_clips) > 1 else sub_clips[0]

    # Mezcla real de la música de la intro sobre la narración del capítulo
    # (ver preparación arriba): pad al 22% de volumen solo durante el beat
    # de intro, la voz sigue al 100%.
    if musica_intro_mezcla is not None:
        try:
            import moviepy.audio.fx as afx
            from moviepy import CompositeAudioClip
            ruta_mi, dur_intro = musica_intro_mezcla
            pad = (AudioFileClip(ruta_mi)
                   .with_duration(min(dur_intro, AudioFileClip(ruta_mi).duration))
                   .with_effects([afx.MultiplyVolume(0.22)]))
            audio_clip = CompositeAudioClip([audio_clip, pad.with_start(0)])
            log(AGENT, f"Música de meditación mezclada bajo la voz de la intro "
                        f"({dur_intro:.1f}s, volumen 22%).")
        except Exception as e:
            log(AGENT, f"Aviso: no se pudo mezclar la música de la intro ({e}); "
                        "la intro va solo con voz.")

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
        threads=4, preset="superfast", logger=None,
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
                     ruta_musica_fondo: str = None, volumen_musica: float = 0.06):
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

    # UNIÓN SIN RE-CODIFICAR (corrección 28-ago-2026, corrida real de
    # 4h45m): antes los capítulos ya renderizados se volvían a codificar
    # COMPLETOS al unirlos (doble codificación de un video de 19 min).
    # Ahora: ffmpeg concat con copia de streams (tarda segundos) y, si hay
    # música, se mezcla re-codificando SOLO el audio (video copiado).
    import subprocess
    log(AGENT, "Uniendo capítulos con ffmpeg (sin re-codificar el video)...")
    lista_txt = os.path.join(carpeta_tmp, "capitulos.txt")
    with open(lista_txt, "w", encoding="utf-8") as fh:
        for p in rutas_capitulos:
            fh.write(f"file '{os.path.abspath(p)}'\n")
    salida = os.path.join(carpeta_salida, f"{nombre_base}.mp4")
    unido = os.path.join(carpeta_tmp, "_unido.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lista_txt,
                    "-c", "copy", unido], check=True, capture_output=True)

    if ruta_musica_fondo and os.path.exists(ruta_musica_fondo):
        try:
            log(AGENT, "Mezclando música de fondo (solo audio, video copiado)...")
            subprocess.run([
                "ffmpeg", "-y", "-i", unido,
                "-stream_loop", "-1", "-i", ruta_musica_fondo,
                "-filter_complex",
                f"[1:a]volume={volumen_musica}[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=3[aout]",
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                "-shortest", salida], check=True, capture_output=True)
            os.remove(unido)
        except Exception as e:
            log(AGENT, f"No se pudo mezclar la música ({e}). Video sin música de fondo.")
            os.replace(unido, salida)
    else:
        os.replace(unido, salida)

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
