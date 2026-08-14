"""
AGENTE 22: LLAMADOS A SUSCRIPCIÓN GARANTIZADOS ("SuscripcionCTA")
------------------------------------------------------------------
El usuario pidió que TODOS los videos, sin excepción, tengan 3 momentos
pidiendo que se suscriban: uno al inicio, uno a la mitad y uno al final.

Por qué esto NO se le pide simplemente al Guionista (LLM) y ya:
un modelo de lenguaje puede olvidarlo, ponerlo en un lugar raro, o
redactarlo distinto de calidad cada vez. Como esto es una regla de negocio
NO NEGOCIABLE ("siempre", según el usuario), se implementa aquí de forma
determinística en código, después de que el guion ya está listo: así
funciona 100% de las veces, sin depender de que la IA "se acuerde".

NOTA IMPORTANTE (decisión tomada en la auditoría de agosto 2026): este
canal en un principio tuvo una presentadora fija generada con IA para
estos 3 momentos, pero se decidió QUITARLA por completo. Motivo real: el
16-jul-2026 YouTube aclaró que los canales con "personas de IA" dando
contenido en temas sensibles (salud, finanzas, temas médicos/legales)
pueden perder la monetización, y este es justamente un canal de salud.
Para no correr ese riesgo, se volvió a un formato 100% sin rostro: los 3
llamados a suscripción ahora se muestran con una TARJETA GRÁFICA (sin
ninguna persona, real o generada), dibujada con Pillow.

Cada llamado:
  - Es un beat más (mismo formato que el resto), así que se integra solo
    con Narrador, VisualScout, EditorVideo, Subtítulos, etc.
  - Se elige AL AZAR entre varias redacciones distintas (nunca la misma
    frase en todos los videos) para que el canal no se sienta "plantillado"
    -- justo lo que la política de "contenido inauténtico" de YouTube
    penaliza (investigado en este proyecto).
  - Usa una palabra clave visual NORMAL y segura (persona sonriendo en luz
    natural), para que aparezca un video/foto real de fondo; el aviso de
    "SUSCRÍBETE" se dibuja como un banner pequeño superpuesto en la parte de
    abajo (ver generar_overlay_suscripcion), nunca a pantalla completa.
  - Queda marcado con beat["es_llamado_suscripcion"] = True para que otros
    agentes (QA-Coherencia, ShortsCreator, EditorVideo) lo reconozcan y lo traten aparte.
"""
import os
import random

from PIL import Image, ImageDraw, ImageFont

from agents.utils import log

AGENT = "SuscripcionCTA"

# Palabra clave visual NORMAL (real, filmable, segura) para los 3 momentos
# de suscripción. Antes esto usaba un marcador especial que hacía aparecer
# una tarjeta A PANTALLA COMPLETA sin ningún video real detrás -- un
# experto en tráfico de YouTube señaló, con razón, que el aviso de
# suscripción NO debe tapar toda la pantalla, sobre todo en los primeros
# segundos (los más importantes para retener a alguien nuevo). Ahora este
# beat usa una escena real y agradable de fondo (como cualquier otro beat,
# pasa por el buscador de video/foto normal), y el aviso de "SUSCRÍBETE" se
# dibuja como un banner PEQUEÑO y transparente encima, solo en la parte de
# abajo (ver generar_overlay_suscripcion en agents/video_editor.py).
VISUAL_SEGURO_SUSCRIPCION = "person smiling warmly in soft natural light at home"

FRASES_INICIO = [
    "Antes de seguir, un segundo. Si te interesa cuidarte de forma natural, suscríbete gratis al canal ahora mismo.",
    "Dato rápido antes de empezar. Suscribirte es gratis y así no te pierdes los próximos videos de salud natural.",
    "Si es tu primera vez aquí, dale a suscribirte. Publicamos contenido nuevo sobre salud natural todos los días.",
    "Antes de entrar de lleno al tema, suscríbete al canal. Es gratis y te va a servir para lo que viene.",
]

FRASES_MITAD = [
    "Si este video te está sirviendo hasta ahora, aprovecha y suscríbete, así no te pierdes el resto.",
    "Vamos a la mitad. Si te gusta lo que estás aprendiendo, suscríbete al canal, es gratis y ayuda mucho.",
    "Antes de seguir con la siguiente parte, un favor rápido, suscríbete al canal si te está gustando el video.",
    "Seguimos. Si quieres más contenido como este, suscribirte es la mejor forma de asegurarte de verlo.",
]

FRASES_FINAL = [
    "Si llegaste hasta aquí, este contenido es para ti. Suscríbete gratis para el próximo video sobre salud natural.",
    "Eso fue todo por hoy. Suscríbete al canal para no perderte los próximos videos, es completamente gratis.",
    "Espero que te haya servido. Antes de irte, suscríbete al canal, así vuelves a encontrar contenido como este.",
    "Gracias por ver hasta el final. Suscríbete gratis al canal, así seguimos ayudándote a cuidar tu salud de forma natural.",
]

# Frase de marca (mantra de cierre): a diferencia de las frases de arriba
# (que rotan al azar para no sonar repetitivas), esta SIEMPRE es la misma,
# a propósito. Es una práctica de branding real y segura (igual que el
# "sign-off" de cualquier creador de verdad); ayuda a que el canal se sienta
# reconocible sin caer en la "plantilla idéntica" que sí penaliza YouTube
# (esta es solo 1 frase corta al final, no la estructura completa del video).
TAGLINE_DE_MARCA = "Recuerda, pequeños cambios naturales, grandes resultados. Nos vemos en el próximo video."


def _beat_cta(texto: str, momento: str) -> dict:
    return {
        "texto": texto,
        "visual": VISUAL_SEGURO_SUSCRIPCION,
        "es_llamado_suscripcion": True,
        "momento_suscripcion": momento,
    }


def insertar_antes_del_cierre(beats: list, beat_nuevo: dict) -> list:
    """Inserta 'beat_nuevo' justo ANTES del llamado final a suscripción
    (momento_suscripcion == 'final'), sin importar qué más se haya agregado
    después de ese beat (como la frase de marca, ver TAGLINE_DE_MARCA).

    Por qué existe esto (bug real encontrado y corregido en la auditoría):
    antes, otros agentes (ej. la mención a un video relacionado) solo
    revisaban si el ÚLTIMO beat de la lista era el llamado final; eso se
    rompió en cuanto se agregó la frase de marca DESPUÉS del llamado final
    (el último beat dejó de ser el de suscripción), y el video terminaba
    con el orden equivocado. Buscar por 'momento_suscripcion' explícito es
    a prueba de futuros agregados al final del guion."""
    for i, b in enumerate(beats):
        if b.get("es_llamado_suscripcion") and b.get("momento_suscripcion") == "final":
            beats.insert(i, beat_nuevo)
            return beats
    beats.append(beat_nuevo)
    return beats


def agregar_llamados_a_suscripcion(guion: dict) -> dict:
    """Inserta, SIEMPRE y de forma determinística, 3 beats de llamado a
    suscripción: inicio (primer capítulo), mitad (capítulo central) y
    final (último capítulo). No depende de que el LLM lo haya incluido."""
    capitulos = guion.get("capitulos", [])
    if not capitulos:
        return guion

    # --- INICIO: después de los primeros beats de contenido del capítulo 1.
    # CORRECCIÓN (auditoría con video real, agosto 2026): antes se insertaba
    # como PRIMER beat del capítulo 1, y como la voz del gancho se narra
    # encima del primer beat, el banner SUSCRÍBETE terminaba EN PANTALLA
    # durante los primeros 5-15 segundos del video (comprobado extrayendo
    # fotogramas reales del video publicado). Eso es exactamente uno de los
    # "asesinos de retención" que la investigación prohíbe: pedir
    # suscripción antes de dar valor. Ahora el aviso entra después de los
    # 2 primeros beats de contenido (~20-30 segundos), cuando el gancho ya
    # cumplió su trabajo.
    cap_inicio = capitulos[0]
    beats_inicio = cap_inicio.setdefault("beats", [])
    posicion_inicio = min(2, len(beats_inicio))
    beats_inicio.insert(posicion_inicio, _beat_cta(random.choice(FRASES_INICIO), "inicio"))

    # --- MITAD: al principio del capítulo que queda más cerca de la mitad
    # del video (si solo hay 1 capítulo, se reutiliza el mismo capítulo,
    # pero se inserta DESPUÉS del llamado de inicio para mantener el orden
    # cronológico correcto dentro del video).
    indice_mitad = len(capitulos) // 2
    if indice_mitad == 0 and len(capitulos) > 1:
        indice_mitad = 1
    cap_mitad = capitulos[indice_mitad]
    posicion_mitad = (posicion_inicio + 1) if cap_mitad is cap_inicio else 0
    cap_mitad.setdefault("beats", []).insert(posicion_mitad, _beat_cta(random.choice(FRASES_MITAD), "mitad"))

    # --- FINAL: al final del último capítulo.
    cap_final = capitulos[-1]
    cap_final.setdefault("beats", []).append(_beat_cta(random.choice(FRASES_FINAL), "final"))

    # --- MANTRA DE MARCA: una última frase, siempre la misma, para dar
    # identidad reconocible al canal (ver nota en TAGLINE_DE_MARCA). Usa un
    # visual normal de contexto (no la tarjeta de suscripción), para que no
    # se sienta como un cuarto aviso, sino como el cierre natural del video.
    cap_final["beats"].append({
        "texto": TAGLINE_DE_MARCA,
        "visual": "peaceful sunrise over calm nature landscape",
    })

    log(AGENT, "Los 3 llamados obligatorios a suscripción quedaron insertados "
                "(inicio, mitad y final), con tarjeta gráfica (sin rostro).")
    return guion


def _fuente(tam):
    ruta = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(ruta):
        return ImageFont.truetype(ruta, tam)
    return ImageFont.load_default()


# Un color de acento distinto por momento: le da algo de variedad visual
# entre los 3 avisos de un mismo video sin necesitar ninguna foto ni rostro.
_COLORES_ACENTO = {
    "inicio": (255, 210, 0),
    "mitad": (0, 210, 160),
    "final": (255, 90, 70),
}


def generar_overlay_suscripcion(momento: str, carpeta_salida: str, tag: str,
                                 resolucion=(1280, 720)) -> str:
    """Genera (100% con Pillow, sin IA, sin ninguna persona real o generada)
    un banner PEQUEÑO y transparente para el llamado a suscripción, pensado
    para superponerse sobre un video/foto real de fondo (nunca reemplazarlo
    por completo). Ocupa solo la franja inferior de la pantalla (~22% de
    alto), tal como recomienda la buena práctica de retención: en los
    primeros segundos del video no se debe tapar la imagen con avisos que
    ocupen toda la pantalla."""
    color_acento = _COLORES_ACENTO.get(momento, (255, 210, 0))
    w, h = resolucion
    overlay = Image.new("RGBA", resolucion, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    alto_banner = int(h * 0.22)
    y0 = h - alto_banner
    # Franja semitransparente (no un bloque sólido) para que se note que hay
    # video real detrás, no una tarjeta que reemplaza la pantalla completa.
    draw.rectangle([0, y0, w, h], fill=(10, 10, 15, 195))
    draw.rectangle([0, y0, w, y0 + 5], fill=color_acento + (255,))  # línea de acento arriba del banner

    # Campanita simple (mismo estilo en todo el proyecto)
    r = int(alto_banner * 0.28)
    cx, cy = int(w * 0.12), y0 + alto_banner // 2
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color_acento + (255,), width=4)
    br = int(r * 0.55)
    draw.pieslice([cx - br, cy - br, cx + br, cy + int(br * 0.6)], 180, 360, fill=color_acento + (255,))
    draw.rectangle([cx - br, cy - int(br * 0.2), cx + br, cy + int(br * 0.5)], fill=color_acento + (255,))

    font_grande = _fuente(int(alto_banner * 0.38))
    texto = "SUSCRÍBETE"
    tx = cx + r + int(w * 0.03)
    ty = y0 + int(alto_banner * 0.14)
    draw.text((tx, ty), texto, font=font_grande, fill=(255, 255, 255, 255))

    font_chica = _fuente(int(alto_banner * 0.18))
    pie = "Es gratis y ayuda mucho"
    draw.text((tx, ty + font_grande.size + int(alto_banner * 0.05)), pie, font=font_chica, fill=(210, 210, 210, 255))

    os.makedirs(carpeta_salida, exist_ok=True)
    destino = os.path.join(carpeta_salida, f"{tag}_overlay_suscripcion.png")
    overlay.save(destino)
    return destino
