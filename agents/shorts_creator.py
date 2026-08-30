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
MAX_BEATS_SHORT = 4          # HISTORIA: 4→2 el 14-ago (retención), 2→4 el
                             # 30-ago-2026 por pedido del usuario: "el short
                             # puede ser un poco más largo con mayor
                             # información, que sea un verdadero abrebocas".
                             # Con la era PRO cada beat lleva clip IA en
                             # movimiento => un Short de 35-45s ya no aburre
                             # como el de imágenes fijas del 14-ago.
DURACION_MAX_OBJETIVO = 45   # segundos, sin contar la tarjeta final de CTA
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
    tw2 = draw.textlength("Link en los comentarios", font=font_chica)
    draw.text(((resolucion[0]-tw2)/2, resolucion[1]/2 + int(10*escala)), "Link en los comentarios",
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
    agents/suscripcion_cta.py), de mención cruzada a otro video (ver
    agents/promocion_cruzada.py) y de llamado a interacción (ver
    agents/engagement_cta.py): esos momentos son para el video LARGO;
    el Short ya tiene su propia tarjeta final de cierre (ver
    _tarjeta_cta_final), que además ahora también invita a suscribirse."""
    primer_capitulo = guion["capitulos"][0]
    beats_disponibles = [b for b in primer_capitulo.get("beats", [])
                          if not b.get("es_llamado_suscripcion")
                          and not b.get("es_mencion_cruzada")
                          and not b.get("es_llamado_interaccion")
                          and not b.get("es_cita_cientifica")
                          and not b.get("es_intro_marca")]
    beats_originales = beats_disponibles[:MAX_BEATS_SHORT]

    beats_short = []
    if guion.get("gancho"):
        beats_short.append({
            "texto": limpiar_texto_para_voz(guion["gancho"]),
            "visual": beats_originales[0]["visual"] if beats_originales else "surprised person looking at camera bright room",
        })
    beats_short.extend(beats_originales)
    # CIERRE CON CLIFFHANGER ESPECÍFICO (21-ago-2026, pedido del usuario:
    # "los shorts no están llevando a los suscriptores a los videos
    # largos"). Un cierre genérico no da razón para saltar; ahora el
    # cierre PROMETE algo concreto que quedó pendiente y dice CÓMO llegar
    # (los espectadores de Shorts no ven descripciones: hay que decírselo
    # con la voz).
    import random as _rnd
    tema_cierre = (guion.get("keyword_principal") or guion.get("titulo", "este tema")).split("(")[0].strip()
    # CIERRES-LOOP (investigación élite 28-ago-2026): los cierres largos con
    # instrucciones ("toca mi perfil y búscalo...") rompen el loop y matan
    # replays — y el replay es LA señal #1 del algoritmo de Shorts 2026
    # (retención >100% = distribución compuesta). Nuevo diseño: cierre de
    # UNA frase corta que RE-ABRE la pregunta del gancho (loop narrativo:
    # el final conecta con el inicio y el cerebro vuelve a ver). El CTA al
    # video largo vive en el comentario fijado y la descripción (donde el
    # link es clicable y no cuesta segundos de video).
    # ABREBOCAS SUGESTIVO v2 (30-ago-2026, pedido del usuario: "que sea un
    # verdadero abrebocas sugestionando, incitando a que se suscriban, le
    # den like y vayan realmente al video largo"). El cierre ahora tiene
    # DOS beats: (1) el anzuelo — una promesa CONCRETA de lo que se pierde
    # quien no va al largo; (2) el CTA directo — suscríbete + like + el
    # video completo, en lenguaje hablado natural.
    anzuelos = [
        f"Pero espera: lo que NO te conté es el error que casi todos cometen con {tema_cierre}... y ese sí te puede costar caro.",
        f"Y esto es apenas el comienzo. En el video completo te muestro el paso exacto, con las cantidades y los tiempos, que aquí no caben.",
        f"Lo que sigue es lo mejor: la señal que casi nadie nota de {tema_cierre}... y que puede cambiar tu día a día.",
        f"Te dejé lo más sorprendente para el video completo: el detalle de {tema_cierre} que hasta los médicos olvidan mencionar.",
    ]
    ctas_finales = [
        "Suscríbete y dale like, que es gratis. El video completo te espera en mi canal.",
        "Si esto te sirvió, suscríbete y deja tu like. El video completo está en mi canal.",
        "Suscríbete para no perderte lo que viene, dale like, y mira el video completo en mi canal.",
    ]
    beats_short.append({
        "texto": limpiar_texto_para_voz(_rnd.choice(anzuelos)),
        "visual": "close-up of surprised curious senior person raising eyebrows warm light",
    })
    beats_short.append({
        "texto": limpiar_texto_para_voz(_rnd.choice(ctas_finales)),
        # En inglés SIEMPRE (auditoría con Short real, 14-ago-2026: esta
        # keyword estaba en español, los bancos de stock no devolvían nada
        # y el Short terminaba con un fondo genérico que mostraba el texto
        # crudo "…iendo y señalando con el dedo" en pantalla).
        "visual": "smiling person pointing finger upward bright room",
    })

    return {
        "titulo": guion["titulo"],
        "capitulos": [{"nombre": "short", "beats": beats_short}],
    }


def crear_short(guion: dict, carpeta_salida: str, nombre_base: str, url_video_largo: str = "",
                carpeta_visuales_largo: str = None) -> tuple:
    """Genera el Short completo. Devuelve (ruta_mp4, titulo_short, descripcion_short).

    carpeta_visuales_largo (nuevo, 21-ago-2026): carpeta con los visuales YA
    descargados/verificados del video largo. Si la búsqueda vertical de un
    beat termina en fondo degradado vacío (defecto real del Short de
    magnesio: pantalla verde sin imágenes), se rescata copiando un visual
    real del largo en su lugar. Un visual horizontal recortado a 9:16 es
    infinitamente mejor que un degradado vacío."""
    os.makedirs(carpeta_salida, exist_ok=True)
    mini_guion = _armar_mini_guion(guion)

    log(AGENT, "Narrando el guion reducido del Short...")
    audio_info = narrar_guion(mini_guion, os.path.join(carpeta_salida, "audio"), nombre_base)

    log(AGENT, "Buscando visuales verticales (9:16) para el Short...")
    visuales_info = obtener_visuales_para_guion(
        mini_guion, os.path.join(carpeta_salida, f"assets_{nombre_base}"), orientacion="portrait"
    )

    # RESCATE ANTI-DEGRADADO (21-ago-2026): si algún beat quedó con el fondo
    # de respaldo (_fallback = degradado vacío), sustituirlo por un visual
    # REAL del video largo (ya verificado y del mismo tema).
    if carpeta_visuales_largo and os.path.isdir(carpeta_visuales_largo):
        import random as _rnd
        reales_largo = [os.path.join(carpeta_visuales_largo, f)
                        for f in os.listdir(carpeta_visuales_largo)
                        if f.lower().endswith((".jpg", ".jpeg", ".png", ".mp4"))
                        and "_fallback" not in f and "intro_marca" not in f]
        _ya_usados_rescate = set()
        for visuales_cap_i in visuales_info["visuales_por_capitulo"]:
            for k, v in enumerate(visuales_cap_i):
                ruta_v = (v.get("ruta") or "")
                if "_fallback" in os.path.basename(ruta_v) and reales_largo:
                    pool = [r for r in reales_largo if r not in _ya_usados_rescate] or reales_largo
                    elegido = _rnd.choice(pool)
                    _ya_usados_rescate.add(elegido)
                    tipo = "video" if elegido.lower().endswith(".mp4") else "imagen"
                    log(AGENT, f"Short: beat {k} tenía fondo degradado vacío; rescatado con "
                                f"visual real del video largo ({os.path.basename(elegido)}).")
                    visuales_cap_i[k] = {"tipo": tipo, "ruta": elegido, "keyword": v.get("keyword", "")}

    beats = mini_guion["capitulos"][0]["beats"]
    audio_cap = audio_info["capitulos"][0]
    visuales_cap = visuales_info["visuales_por_capitulo"][0]

    # CLIPS IA PRECISOS POR BEAT (30-ago-2026, pedido del usuario: "que los
    # clips sean precisos de lo que se está hablando, interactúa entre los
    # clips y las imágenes, no importa cuánto se demore"). Con la era PRO
    # (40 min GPU/día) el Short se merece sus propios clips generados A
    # MEDIDA del texto de cada beat, en vez de solo stock. El prompt del
    # clip usa el TEXTO NARRADO (no solo la keyword) => coherencia visual
    # exacta con lo que se dice. Se intercalan: los beats pares buscan clip
    # IA, los impares conservan el visual verificado del largo/stock (esa
    # mezcla clip-imagen da ritmo visual y reparte la cuota).
    try:
        from agents.video_ia import generar_clip_ia
        for k, (beat_k, visual_k) in enumerate(zip(beats, visuales_cap)):
            es_video_ya = (visual_k.get("tipo") == "video")
            if k % 2 == 1 and es_video_ya:
                continue  # impar y ya tiene video: se queda (mezcla)
            destino_ia = os.path.join(carpeta_salida, f"assets_{nombre_base}",
                                       f"ia_short_beat{k}.mp4")
            prompt_preciso = (f"{visual_k.get('keyword', '')}. "
                              f"Scene illustrating: {beat_k.get('texto', '')[:180]}")
            ruta_ia = generar_clip_ia(prompt_preciso, destino_ia,
                                       contexto="vertical smartphone video",
                                       vertical=True)
            if ruta_ia:
                visuales_cap[k] = {"tipo": "video", "ruta": ruta_ia,
                                    "keyword": visual_k.get("keyword", "")}
                log(AGENT, f"Short: beat {k} ahora lleva clip IA a medida del texto narrado.")
    except Exception as e:
        log(AGENT, f"Clips IA del Short no disponibles ({type(e).__name__}); "
                   f"se usan los visuales de stock verificados.")

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
                                        threads=4, preset="superfast", logger=None)
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


    # PORTADA COMO PRIMER FOTOGRAMA, DENTRO DEL RENDER (30-ago-2026, pedido
    # del usuario: "procura que la primera imagen sea la portada del short
    # ... dentro del video para que quede como portada"). La portada élite
    # (Agentes 38-40) se genera ANTES del render y se antepone como clip de
    # 0.6s con zoom sutil (gancho visual + frame0 del feed de Shorts = la
    # portada). Así se esquiva de raíz el impedimento de YouTube.
    clips_secuencia = []
    try:
        from agents.equipo_portadas import generar_portada_elite
        ruta_portada_short = generar_portada_elite(
            {"titulo": guion.get("titulo", ""),
             "keyword_principal": guion.get("keyword_principal", "")},
            "", os.path.join(carpeta_tmp, "portada_short.png"), vertical=True)
        import moviepy.video.fx as _vfx
        clip_portada = (ImageClip(ruta_portada_short)
                        .with_duration(0.6)
                        .with_effects([_vfx.Resize(lambda t: 1.0 + 0.06 * t)]))
        clip_portada = clip_portada.resized(RESOLUCION_SHORT)  # asegurar tamaño
        silencio_p = _AudioClip(lambda t: 0, duration=0.6, fps=44100)
        clip_portada = clip_portada.with_audio(silencio_p)
        clips_secuencia.append(clip_portada)
        log(AGENT, "Portada élite integrada como primer fotograma del Short (0.6s).")
    except Exception as e:
        log(AGENT, f"Aviso: portada inicial no disponible ({type(e).__name__}); "
                   f"el Short arranca directo con el gancho.")

    clips_secuencia += [video_narrado, clip_cta]
    video_final = concatenate_videoclips(clips_secuencia, method="chain")

    salida = os.path.join(carpeta_salida, f"{nombre_base}_short.mp4")
    log(AGENT, f"Renderizando Short -> {salida} ...")
    video_final.write_videofile(
        salida, fps=30, codec="libx264", audio_codec="aac",
        threads=4, preset="superfast", logger=None,
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

    # TÍTULO DE CURIOSIDAD (auditoría 28-ago-2026): los shorts derivados con
    # título=copia del largo promedian 50 vistas; los de formato curiosidad/
    # mito promedian 674-727 (el ganador de 1.334 es "El Mito Más Común
    # De..."). El short derivado ahora usa gancho de curiosidad + tema corto.
    import random as _rnd
    try:
        from agents.promocion_cruzada import _tema_corto_de
        _tema = _tema_corto_de(guion["titulo"]).title()
    except Exception:
        _tema = guion["titulo"].split(":")[0].split("(")[0].strip()
    _prefijos = ["Lo Que Nadie Te Dice De", "El Error Más Común Con",
                 "La Verdad Sobre", "Esto Cambia Todo Sobre"]
    titulo_short = f"{_rnd.choice(_prefijos)} {_tema}"[:85] + " #Shorts"
    # HONESTIDAD TÉCNICA (auditoría 14-ago-2026): YouTube NO hace clicables
    # los enlaces en las descripciones de Shorts (limitación oficial de la
    # plataforma, verificada). El enlace clicable REAL va en el comentario
    # que publica agents/promocion_cruzada.py. La descripción lo dice
    # claro para que nadie intente copiar un texto plano, y aun así se
    # incluye la URL (YouTube la usa como señal de relación entre videos,
    # y en escritorio sí se puede copiar).
    descripcion_short = (
        f"{guion.get('gancho', '')}\n\n"
        f"👉 El video COMPLETO está en el PRIMER COMENTARIO (link directo) 📌\n"
        f"También puedes buscarlo en mi canal: {url_video_largo}\n"
        f"📲 Suscríbete y YouTube te mostrará el video completo: https://www.youtube.com/@saludnaturaldiaria\n\n"
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
