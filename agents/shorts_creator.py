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
import re
import gc
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip, VideoFileClip

from agents.utils import load_config, log, limpiar_texto_para_voz
from agents.video_editor import _clip_desde_visual, _fondo_respaldo_simple, _ajustar_duraciones_a_ritmo
from agents.visuals import obtener_visuales_para_guion
from agents.voice import narrar_guion

AGENT = "ShortsCreator"
RESOLUCION_SHORT = (720, 1280)   # 720p vertical: se ve nítido en móvil y usa mucha menos RAM/CPU
MAX_BEATS_SHORT = 3          # 31-ago-2026: volvemos a 3 beats de contenido
                             # real. El Short del día quedó en 1:10 y perdió
                             # ritmo/loop. Con 3 beats + un cierre fuerte se
                             # queda en la franja agresiva de 30-45s.
DURACION_MAX_OBJETIVO = 34   # segundos de narración antes de la tarjeta final
DURACION_MIN_CORTE_SHORT = 1.8
DURACION_MAX_CORTE_SHORT = 4.0
PORTADA_INICIAL_SEG = 3.2    # se cubren varios segundos del arranque con la
                             # MISMA portada exacta para que YouTube y la
                             # selección manual sigan viendo esa imagen.
DURACION_CTA_FINAL_SEG = 1.2


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
    # CIERRE CORTO Y AGRESIVO (31-ago-2026): el cierre anterior usaba DOS
    # beats + tarjeta larga y llevó el Short real a 1:10. Volvemos a un
    # único beat final: cliffhanger concreto + CTA breve, para proteger el
    # loop y la retención sin perder la invitación al largo.
    import random as _rnd
    tema_cierre = (guion.get("keyword_principal") or guion.get("titulo", "este tema")).split("(")[0].strip()
    cierres = [
        f"Pero el error que más te roba sueño con {tema_cierre} te lo dejé en el video completo. Suscríbete y míralo en mi canal.",
        f"Aquí solo viste la punta del iceberg. En el video completo te muestro el paso exacto para usar {tema_cierre} sin fallar.",
        f"Lo más importante quedó fuera de este Short. Si quieres evitar el error más común con {tema_cierre}, ve ahora al video completo.",
    ]
    beats_short.append({
        "texto": limpiar_texto_para_voz(_rnd.choice(cierres)),
        # En inglés SIEMPRE: los bancos de stock responden mucho mejor y se
        # evita el fondo genérico roto que apareció en auditorías previas.
        "visual": "smiling person pointing finger upward bright room",
    })

    return {
        "titulo": guion["titulo"],
        "capitulos": [{"nombre": "short", "beats": beats_short}],
    }


def crear_short(guion: dict, carpeta_salida: str, nombre_base: str, url_video_largo: str = "",
                carpeta_visuales_largo: str = None, titulo_short_override: str = "") -> tuple:
    """Genera el Short completo.

    Devuelve (ruta_mp4, titulo_short, descripcion_short, ruta_portada_short).

    carpeta_visuales_largo (nuevo, 21-ago-2026): carpeta con los visuales YA
    descargados/verificados del video largo. Si la búsqueda vertical de un
    beat termina en fondo degradado vacío (defecto real del Short de
    magnesio: pantalla verde sin imágenes), se rescata copiando un visual
    real del largo en su lugar. Un visual horizontal recortado a 9:16 es
    infinitamente mejor que un degradado vacío."""
    os.makedirs(carpeta_salida, exist_ok=True)

    # TÍTULO DEL SHORT ANTES DEL RENDER: así la portada integrada, la
    # miniatura oficial y el título publicado nacen ALINEADOS y dejan de
    # pelearse entre sí.
    import random as _rnd
    try:
        from agents.promocion_cruzada import _tema_corto_de
        _tema = _tema_corto_de(guion["titulo"]).title()
    except Exception:
        _tema = guion["titulo"].split(":")[0].split("(")[0].strip()
    _prefijos = ["Lo Que Nadie Te Dice De", "El Error Más Común Con",
                 "La Verdad Sobre", "Esto Cambia Todo Sobre"]
    titulo_short = (titulo_short_override or (f"{_rnd.choice(_prefijos)} {_tema}"[:85] + " #Shorts")).strip()
    titulo_portada = re.sub(r"\s+#\w+.*$", "", titulo_short).strip()

    mini_guion = _armar_mini_guion(guion)

    log(AGENT, "Narrando el guion reducido del Short...")
    audio_info = narrar_guion(mini_guion, os.path.join(carpeta_salida, "audio"), nombre_base)
    # Tope duro de duración del Short: si aun así se alarga, se recorta el
    # último beat de contenido y se vuelve a narrar. Nunca se toca el
    # gancho ni el cierre final.
    while (audio_info["capitulos"][0]["duracion_total"] > DURACION_MAX_OBJETIVO
           and len(mini_guion["capitulos"][0]["beats"]) > 2):
        idx_quitar = max(1, len(mini_guion["capitulos"][0]["beats"]) - 2)
        quitado = mini_guion["capitulos"][0]["beats"].pop(idx_quitar)
        log(AGENT, f"Short demasiado largo ({audio_info['capitulos'][0]['duracion_total']:.1f}s). "
                    f"Se recorta un beat para proteger el loop: {quitado.get('texto','')[:70]}")
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
        # CERO REPETICIONES (30-ago-2026, condición del usuario): cada
        # visual del largo se usa MÁXIMO UNA VEZ en el Short y, además, se
        # excluyen los que el largo ya mostró de forma prominente no es
        # posible rastrear aquí, así que la regla dura es: un rescate por
        # visual, jamás dos beats del Short con el mismo archivo. Si el
        # pool se agota, el beat conserva su fondo y el paso de clips IA
        # de más abajo lo cubrirá con un clip ÚNICO generado a medida.
        _ya_usados_rescate = set()
        for visuales_cap_i in visuales_info["visuales_por_capitulo"]:
            for k, v in enumerate(visuales_cap_i):
                ruta_v = (v.get("ruta") or "")
                if "_fallback" in os.path.basename(ruta_v) and reales_largo:
                    pool = [r for r in reales_largo if r not in _ya_usados_rescate]
                    if not pool:
                        log(AGENT, f"Short: beat {k} sin rescate disponible "
                                    f"(regla cero-repeticiones); lo cubrirá el clip IA.")
                        continue
                    elegido = _rnd.choice(pool)
                    _ya_usados_rescate.add(elegido)
                    tipo = "video" if elegido.lower().endswith(".mp4") else "imagen"
                    log(AGENT, f"Short: beat {k} tenía fondo degradado vacío; rescatado con "
                                f"visual real del video largo ({os.path.basename(elegido)}), "
                                f"uso único garantizado.")
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

    ruta_cta = _tarjeta_cta_final(os.path.join(carpeta_tmp, "cta.png"), titulo_portada)
    duracion_cta = DURACION_CTA_FINAL_SEG
    clip_cta = ImageClip(ruta_cta).with_duration(duracion_cta)
    # Le agregamos una pista de audio silenciosa: si un clip de la concatenación
    # tiene audio y otro no, moviepy puede romperse al armar la pista final.
    from moviepy import AudioClip as _AudioClip
    silencio_cta = _AudioClip(lambda t: 0, duration=duracion_cta, fps=44100)
    clip_cta = clip_cta.with_audio(silencio_cta)


    # PORTADA ÚNICA DEL SHORT: se guarda FUERA de la carpeta temporal para
    # reutilizar EXACTAMENTE la misma imagen en tres sitios: overlay inicial,
    # miniatura oficial y selección manual en Studio. Sin regenerar variantes.
    ruta_portada_short = None
    try:
        from agents.equipo_portadas import generar_portada_elite
        os.makedirs("output/thumbnails", exist_ok=True)
        ruta_portada_destino = os.path.join("output/thumbnails", f"{nombre_base}_short_cover.png")
        ruta_portada_short = generar_portada_elite(
            {"titulo": titulo_portada,
             "keyword_principal": guion.get("keyword_principal", "")},
            "", ruta_portada_destino, vertical=True)
        log(AGENT, f"Portada élite del Short lista: {ruta_portada_short}")
    except Exception as e:
        log(AGENT, f"Aviso: portada del Short no disponible ({type(e).__name__}); "
                   f"se usará miniatura por fotograma si hace falta.")
        ruta_portada_short = None

    video_final = concatenate_videoclips([video_narrado, clip_cta], method="chain")

    salida = os.path.join(carpeta_salida, f"{nombre_base}_short.mp4")
    log(AGENT, f"Renderizando Short -> {salida} ...")
    video_final.write_videofile(
        salida, fps=30, codec="libx264", audio_codec="aac",
        threads=4, preset="superfast", logger=None,
    )

    # Refuerzo final: además del archivo de miniatura, se superpone ESA misma
    # portada sobre los primeros segundos del mp4 ya renderizado. Así el
    # audio arranca desde el segundo 0, pero visualmente el Short mantiene
    # la portada exacta durante varios frames/segundos.
    if ruta_portada_short:
        try:
            from agents.equipo_portadas import incrustar_portada_como_primer_frame
            incrustar_portada_como_primer_frame(salida, ruta_portada_short, segundos=PORTADA_INICIAL_SEG)
        except Exception as e:
            log(AGENT, f"Aviso: no se pudo reforzar la portada dentro del mp4 ({type(e).__name__}).")

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

    # HONESTIDAD TÉCNICA (auditoría 14-ago-2026): YouTube NO hace clicables
    # los enlaces en las descripciones de Shorts (limitación oficial de la
    # plataforma, verificada). El enlace clicable REAL va en el comentario
    # que publica agents/promocion_cruzada.py. La descripción lo dice
    # claro para que nadie intente copiar un texto plano, y aun así se
    # incluye la URL (YouTube la usa como señal de relación entre videos,
    # y en escritorio sí se puede copiar).
    hashtag_tema = re.sub(r"[^0-9A-Za-zÁÉÍÓÚÑáéíóúñ]", "", (_tema or "SaludNaturalDiaria"))[:24]
    if not hashtag_tema:
        hashtag_tema = "SaludNaturalDiaria"
    descripcion_short = (
        f"{guion.get('gancho', '')}\n\n"
        f"👉 El video COMPLETO está en el PRIMER COMENTARIO FIJADO.\n"
        f"También puedes verlo aquí: {url_video_largo}\n"
        f"📲 Suscríbete gratis para ver el largo completo: https://www.youtube.com/@saludnaturaldiaria\n\n"
        f"#Shorts #{hashtag_tema}"
    )

    log(AGENT, "Render del Short completado.")
    return salida, titulo_short, descripcion_short, ruta_portada_short



if __name__ == "__main__":
    from agents.trend_scout import buscar_ideas_potenciales
    from agents.scriptwriter import generar_guion

    idea = buscar_ideas_potenciales()[0]
    guion = generar_guion(idea)
    ruta, titulo, descripcion, miniatura = crear_short(
        guion, "output/video", "demo_short",
        url_video_largo="https://youtube.com/watch?v=EJEMPLO"
    )
    print(ruta)
    print(titulo)
    print(descripcion)
    print(miniatura)
