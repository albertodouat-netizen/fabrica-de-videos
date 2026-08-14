"""
AGENTE 6: EMPAQUETADOR DE MINIATURA ("Thumbnail Packager")
----------------------------------------------------
Genera la miniatura (thumbnail) 100% gratis, replicando el concepto de
"packaging" (fondo llamativo + texto corto y legible) que usan los canales
grandes:

  1) FONDO: en vez de usar un fotograma cualquiera del video (que muchas
     veces es aburrido o no representa el video), se genera una imagen IA
     A MEDIDA con Pollinations.ai (gratis, sin key) describiendo la keyword
     principal del video + una composición típica de miniatura viral
     (primer plano, expresión llamativa, colores saturados, alto contraste).
     Si por algún motivo la generación falla, se usa como respaldo un
     fotograma real del primer recurso visual del video (comportamiento
     anterior), y como último respaldo un fondo sólido.
  2) TEXTO: máximo 4-5 palabras (nunca el título completo, ilegible en
     miniatura), en mayúsculas, con contorno grueso para leerse incluso en
     pantallas pequeñas.
  3) ACENTOS VISUALES: si el título trae un número (ej. "7 Claves"), se
     dibuja una insignia circular con ese número (recurso clásico de
     miniaturas virales: los números concretos generan más clics), y una
     franja de color de acento para dar contraste.
"""
import os
import random
import re
import urllib.parse
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from agents.utils import log

AGENT = "Packaging"
TAMANO = (1280, 720)


def _fuente(tam, negrita=True):
    rutas = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for r in rutas:
        if os.path.exists(r):
            return ImageFont.truetype(r, tam)
    return ImageFont.load_default()


def _frase_corta_para_miniatura(titulo: str, keyword_principal: str = "") -> str:
    """El título completo casi nunca cabe legible en una miniatura pequeña.
    MÁXIMO 3 PALABRAS (actualizado 14-ago-2026): recomendación consistente
    de la investigación real analizada (grupo de grandes creadores citado
    por experta ex-YouTube: "la miniatura no debe tener más de tres
    palabras"; comprobado además en la miniatura real del 14-ago, que con
    5 palabras se veía redundante: "ALIMENTOS VISIÓN MEJORA VISIÓN ESTOS").
    Se eligen las 3 palabras más 'fuertes' SIN repetir (evitando conectores
    y duplicados como el doble "visión"). Los números se excluyen porque ya
    se destacan aparte con la insignia circular (ver _numero_en_titulo)."""
    conectores = {"de", "del", "la", "el", "los", "las", "para", "con", "en",
                  "y", "a", "un", "una", "que", "tu", "su", "al", "estos",
                  "estas", "este", "esta", "como", "cómo", "más", "sin"}
    palabras = re.findall(r"[\wÁÉÍÓÚÑáéíóúñ]+", titulo)
    palabras = [p for p in palabras if not p.isdigit()]
    fuertes, vistas = [], set()
    for p in palabras:
        pl = p.lower()
        if pl in conectores or pl in vistas:
            continue
        vistas.add(pl)
        fuertes.append(p)
    elegidas = fuertes[:3] if len(fuertes) >= 2 else palabras[:3]
    frase = " ".join(elegidas)
    return frase if frase else titulo[:30]


def _numero_en_titulo(titulo: str):
    m = re.search(r"\b(\d{1,2})\b", titulo)
    return m.group(1) if m else None


def _generar_fondo_ia_miniatura(keyword_principal: str, titulo: str, destino_jpg: str,
                                 tamano=TAMANO) -> bool:
    """Genera un fondo de miniatura llamativo con Pollinations.ai (100%
    gratis, sin key). Se pide explícitamente una composición típica de
    miniatura de YouTube (primer plano, expresión clara, colores
    saturados), nunca un dibujo/animación.

    Nota (auditoría agosto 2026): antes esto usaba SIEMPRE la misma persona
    fija (un "presentador" del canal) para dar reconocimiento de marca, pero
    se decidió quitarlo por el riesgo de la política de YouTube sobre
    "personas de IA" en temas sensibles como salud. Ahora cada miniatura
    genera una persona distinta relacionada con el tema del video (formato
    100% sin identidad fija, más seguro).

    Nota de seguridad (misma auditoría): se confirmó en vivo que el
    parámetro 'safe=true' de Pollinations NO bloquea de forma confiable
    contenido NSFW por sí solo. Por eso cada imagen generada aquí también
    se verifica con Gemini Vision antes de aceptarla (ver
    agents.visuals._imagen_es_segura_gemini), con reintentos si falla."""
    base = keyword_principal.strip() or titulo
    prompt = (
        f"fotografía editorial realista relacionada con {base}, primer plano de una "
        f"persona real sana y sonriente mirando a la cámara con expresión de alivio y "
        f"bienestar genuino, luz natural cálida de mañana, piel con textura realista, "
        f"fotografía de revista de salud, colores vibrantes, alto contraste, fondo "
        f"simple desenfocado, composición centrada tipo miniatura de youtube, "
        f"fotografía profesional de alta resolución, 8k, sin texto en la imagen, "
        f"sin logotipos, sin marca de agua, encuadre de los hombros hacia arriba, "
        f"persona completamente vestida con cuello alto o camiseta cerrada, sin "
        f"escote, sin piel descubierta más allá del rostro y el cuello, sin "
        f"desnudos, contenido apto para todo público, familiar, profesional"
    )
    prompt_codificado = urllib.parse.quote(prompt)

    for intento in range(3):
        semilla = random.randint(1, 999999)
        # safe=true + model=flux: ver la nota completa en agents/visuals.py
        # (hallazgo real de la auditoría de agosto 2026 sobre contenido NSFW).
        url = (f"https://image.pollinations.ai/prompt/{prompt_codificado}"
               f"?width={tamano[0]}&height={tamano[1]}&nologo=true&seed={semilla}"
               f"&safe=true&model=flux")
        try:
            r = requests.get(url, timeout=45)
            r.raise_for_status()
            if len(r.content) < 5000:
                continue
            with open(destino_jpg, "wb") as f:
                f.write(r.content)
        except Exception as e:
            log(AGENT, f"No se pudo generar fondo IA para miniatura ({e}); se usará respaldo.")
            continue

        try:
            from agents.visuals import _imagen_es_segura_gemini
            if _imagen_es_segura_gemini(destino_jpg):
                return True
            log(AGENT, f"Fondo de miniatura descartado por seguridad (intento {intento+1}/3); "
                        f"probando con otra semilla...")
        except Exception as e:
            log(AGENT, f"Aviso: no se pudo verificar la seguridad del fondo de miniatura ({e}); "
                        f"se descarta por precaución.")
        try:
            os.remove(destino_jpg)
        except OSError:
            pass

    log(AGENT, "No se logró un fondo de miniatura seguro tras 3 intentos; se usará un respaldo.")
    return False


def _fondo_desde_frame(imagen_base: str):
    if imagen_base.lower().endswith((".mp4", ".mov", ".webm", ".mkv")):
        from moviepy import VideoFileClip
        with VideoFileClip(imagen_base) as clip:
            t = min(1.0, clip.duration / 2)
            frame = clip.get_frame(t)
        return Image.fromarray(frame).convert("RGB")
    return Image.open(imagen_base).convert("RGB")


def generar_miniatura(guion, imagen_base: str, salida_png: str) -> str:
    """
    guion: puede ser el dict completo del guion (recomendado, permite usar
    keyword_principal para generar un fondo IA a medida) o directamente un
    string con el título (compatibilidad con versiones anteriores).
    imagen_base: ruta a un frame/imagen del video, usado SOLO como respaldo
    si la generación IA del fondo falla.
    """
    if isinstance(guion, dict):
        titulo = guion.get("titulo", "")
        keyword_principal = guion.get("keyword_principal", "")
    else:
        titulo = guion or ""
        keyword_principal = ""

    os.makedirs(os.path.dirname(salida_png) or ".", exist_ok=True)
    destino_ia = salida_png + "_fondo_ia.jpg"

    base = None
    if _generar_fondo_ia_miniatura(keyword_principal, titulo, destino_ia):
        try:
            base = Image.open(destino_ia).convert("RGB")
            log(AGENT, "Fondo de miniatura generado con IA (Pollinations), a medida del tema del video.")
        except Exception:
            base = None

    if base is None:
        try:
            base = _fondo_desde_frame(imagen_base)
            log(AGENT, "No se pudo generar fondo IA; se usó un fotograma real del video como respaldo.")
        except Exception as e:
            log(AGENT, f"No se pudo abrir imagen base ({e}), generando fondo sólido.")
            base = Image.new("RGB", TAMANO, (30, 30, 30))

    base = base.resize(TAMANO)
    base = ImageEnhance.Contrast(base).enhance(1.2)
    base = ImageEnhance.Color(base).enhance(1.3)
    base = ImageEnhance.Sharpness(base).enhance(1.4)

    # Viñeta oscura inferior para que el texto resalte (técnica estándar de thumbnails)
    overlay = Image.new("RGBA", TAMANO, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    for y in range(TAMANO[1] // 2, TAMANO[1]):
        alpha = int(190 * (y - TAMANO[1] // 2) / (TAMANO[1] / 2))
        draw_overlay.line([(0, y), (TAMANO[0], y)], fill=(0, 0, 0, alpha))
    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(base)
    color_acento = random.choice([(255, 210, 0), (255, 255, 255), (0, 230, 160), (255, 80, 60)])

    # --- Texto corto y llamativo (máximo 4-5 palabras, nunca el título completo) ---
    texto_miniatura = _frase_corta_para_miniatura(titulo, keyword_principal).upper()
    font = _fuente(90)
    palabras = texto_miniatura.split()
    linea, lineas = "", []
    for palabra in palabras:
        prueba = (linea + " " + palabra).strip()
        if draw.textlength(prueba, font=font) > TAMANO[0] * 0.9:
            lineas.append(linea)
            linea = palabra
        else:
            linea = prueba
    if linea:
        lineas.append(linea)
    lineas = lineas[:2]

    y = TAMANO[1] - 40 - len(lineas) * 100
    for ln in lineas:
        tw = draw.textlength(ln, font=font)
        x = (TAMANO[0] - tw) / 2
        # Franja semitransparente detrás del texto para que resalte en
        # cualquier fondo (recurso clásico de miniaturas virales).
        pad = 14
        franja = Image.new("RGBA", TAMANO, (0, 0, 0, 0))
        draw_franja = ImageDraw.Draw(franja)
        draw_franja.rectangle([x - pad, y - pad, x + tw + pad, y + font.size + pad], fill=(0, 0, 0, 140))
        base = Image.alpha_composite(base.convert("RGBA"), franja).convert("RGB")
        draw = ImageDraw.Draw(base)
        for dx in (-3, 3):
            for dy in (-3, 3):
                draw.text((x + dx, y + dy), ln, font=font, fill=(0, 0, 0))
        draw.text((x, y), ln, font=font, fill=color_acento)
        y += 100

    # --- Insignia circular con número (si el título trae uno, ej. "7 Claves") ---
    numero = _numero_en_titulo(titulo)
    if numero:
        cx, cy, radio = TAMANO[0] - 110, 110, 85
        draw.ellipse([cx - radio, cy - radio, cx + radio, cy + radio], fill=(230, 30, 40), outline=(255, 255, 255), width=6)
        font_num = _fuente(80)
        tw = draw.textlength(numero, font=font_num)
        draw.text((cx - tw / 2, cy - font_num.size / 1.7), numero, font=font_num, fill=(255, 255, 255))

    # --- Marca de agua/logo pequeño y consistente (auditoría SEO élite,
    # agosto 2026): varios de los canales que mejor posicionan en el nicho
    # (ej. FisioOnline) llevan un distintivo de marca pequeño y fijo en una
    # esquina en TODAS sus miniaturas -> ayuda al reconocimiento de marca
    # cuando el espectador ve varios videos tuyos en la misma pantalla de
    # resultados/sugeridos. Esquina superior izquierda, para no chocar con
    # el texto principal (abajo) ni la insignia de número (arriba derecha).
    marca_texto = "SALUD NATURAL DIARIA"
    try:
        from agents.utils import load_config
        marca_texto = load_config()["canal"].get("nombre", marca_texto).upper()
    except Exception:
        pass
    font_marca = _fuente(26)
    tw_marca = draw.textlength(marca_texto, font=font_marca)
    pad_marca = 12
    overlay_marca = Image.new("RGBA", TAMANO, (0, 0, 0, 0))
    draw_marca = ImageDraw.Draw(overlay_marca)
    draw_marca.rounded_rectangle(
        [20, 20, 20 + tw_marca + pad_marca * 2, 20 + font_marca.size + pad_marca * 2],
        radius=8, fill=(0, 0, 0, 150),
    )
    base = Image.alpha_composite(base.convert("RGBA"), overlay_marca).convert("RGB")
    draw = ImageDraw.Draw(base)
    draw.text((20 + pad_marca, 20 + pad_marca), marca_texto, font=font_marca, fill=(255, 255, 255))

    os.makedirs(os.path.dirname(salida_png) or ".", exist_ok=True)
    base.save(salida_png, quality=95)
    try:
        if os.path.exists(destino_ia):
            os.remove(destino_ia)
    except OSError:
        pass
    log(AGENT, f"Miniatura generada -> {salida_png}")
    return salida_png


if __name__ == "__main__":
    from agents.trend_scout import buscar_ideas_potenciales
    from agents.scriptwriter import generar_guion
    from agents.visuals import obtener_visuales_para_guion

    idea = buscar_ideas_potenciales()[0]
    guion = generar_guion(idea)
    visuales = obtener_visuales_para_guion(guion, "output/video/assets_thumb_demo")
    primera_imagen = visuales["visuales_por_capitulo"][0][0]["ruta"]
    generar_miniatura(guion, primera_imagen, "output/thumbnails/demo.png")
