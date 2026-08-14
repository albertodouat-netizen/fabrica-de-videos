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
  - Usa el marcador especial MARCADOR_VISUAL_SUSCRIPCION como palabra
    visual, para que VisualScout (agents/visuals.py) muestre la tarjeta
    gráfica de suscripción en vez de buscar un clip de stock.
  - Queda marcado con beat["es_llamado_suscripcion"] = True para que otros
    agentes (QA-Coherencia, ShortsCreator) lo reconozcan y lo traten aparte.
"""
import os
import random

from PIL import Image, ImageDraw, ImageFont

from agents.utils import log

AGENT = "SuscripcionCTA"

# Marcador especial usado en el campo "visual" del beat: en vez de buscar un
# clip de stock, VisualScout genera la tarjeta gráfica de suscripción.
MARCADOR_VISUAL_SUSCRIPCION = "TARJETA_LLAMADO_SUSCRIPCION"

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
        "visual": MARCADOR_VISUAL_SUSCRIPCION,
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

    # --- INICIO: justo después del gancho, como primer beat del capítulo 1.
    # Se pone ahí (no antes del gancho) para no debilitar el gancho, que es
    # lo que retiene al espectador en los primeros segundos.
    cap_inicio = capitulos[0]
    cap_inicio.setdefault("beats", []).insert(0, _beat_cta(random.choice(FRASES_INICIO), "inicio"))

    # --- MITAD: al principio del capítulo que queda más cerca de la mitad
    # del video (si solo hay 1 capítulo, se reutiliza el mismo capítulo,
    # pero se inserta DESPUÉS del llamado de inicio para mantener el orden
    # cronológico correcto dentro del video).
    indice_mitad = len(capitulos) // 2
    if indice_mitad == 0 and len(capitulos) > 1:
        indice_mitad = 1
    cap_mitad = capitulos[indice_mitad]
    posicion_mitad = 1 if cap_mitad is cap_inicio else 0
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


def generar_tarjeta_suscripcion(momento: str, carpeta_salida: str, tag: str,
                                 resolucion=(1280, 720)) -> str:
    """Genera (100% con Pillow, sin IA, sin ninguna persona real o generada)
    una tarjeta gráfica para el llamado a suscripción. Formato 100% sin
    rostro, a propósito (ver nota al inicio del archivo)."""
    color_acento = _COLORES_ACENTO.get(momento, (255, 210, 0))
    img = Image.new("RGB", resolucion, (18, 18, 22))
    draw = ImageDraw.Draw(img)

    cx, cy = resolucion[0] // 2, resolucion[1] // 2 - 60
    r = 90
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color_acento, width=8)
    # Campana simple dibujada a mano (mismo estilo en todo el proyecto).
    br = int(r * 0.55)
    draw.pieslice([cx - br, cy - br, cx + br, cy + int(br * 0.6)], 180, 360, fill=color_acento)
    draw.rectangle([cx - br, cy - int(br * 0.2), cx + br, cy + int(br * 0.5)], fill=color_acento)
    draw.ellipse([cx - int(br * 0.25), cy + int(br * 0.5), cx + int(br * 0.25), cy + int(br * 0.9)],
                 fill=color_acento)

    font_grande = _fuente(74)
    texto = "SUSCRÍBETE"
    tw = draw.textlength(texto, font=font_grande)
    draw.text(((resolucion[0] - tw) / 2, cy + r + 40), texto, font=font_grande, fill=(255, 255, 255))

    font_chica = _fuente(34)
    pie = "Es gratis y ayuda mucho"
    tw2 = draw.textlength(pie, font=font_chica)
    draw.text(((resolucion[0] - tw2) / 2, cy + r + 130), pie, font=font_chica, fill=(190, 190, 190))

    os.makedirs(carpeta_salida, exist_ok=True)
    destino = os.path.join(carpeta_salida, f"{tag}_tarjeta_suscripcion.jpg")
    img.save(destino, quality=92)
    return destino
