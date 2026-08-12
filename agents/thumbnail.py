"""
AGENTE 6: EMPAQUETADOR DE MINIATURA ("Thumbnail Packager")
----------------------------------------------------
Genera la miniatura (thumbnail) 100% gratis y local con Pillow, replicando
el concepto de "packaging" (título + imagen llamativa) del video analizado,
pero sin depender de Canva ni de herramientas de pago con IA de rostro.
"""
import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from agents.utils import log

AGENT = "Packaging"
TAMANO = (1280, 720)


def _fuente(tam):
    rutas = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for r in rutas:
        if os.path.exists(r):
            return ImageFont.truetype(r, tam)
    return ImageFont.load_default()


def generar_miniatura(titulo: str, imagen_base: str, salida_png: str) -> str:
    """
    imagen_base: ruta a un frame/imagen ya generada por el VisualScout, o a un
    clip de video (en cuyo caso se extrae un fotograma automáticamente).
    """
    try:
        if imagen_base.lower().endswith((".mp4", ".mov", ".webm", ".mkv")):
            from moviepy import VideoFileClip
            with VideoFileClip(imagen_base) as clip:
                t = min(1.0, clip.duration / 2)
                frame = clip.get_frame(t)
            base = Image.fromarray(frame).convert("RGB")
        else:
            base = Image.open(imagen_base).convert("RGB")
        base = base.resize(TAMANO)
        base = ImageEnhance.Contrast(base).enhance(1.15)
        base = ImageEnhance.Color(base).enhance(1.2)
    except Exception as e:
        log(AGENT, f"No se pudo abrir imagen base ({e}), generando fondo sólido.")
        base = Image.new("RGB", TAMANO, (30, 30, 30))


    # Viñeta oscura inferior para que el texto resalte (técnica estándar de thumbnails)
    overlay = Image.new("RGBA", TAMANO, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    for y in range(TAMANO[1] // 2, TAMANO[1]):
        alpha = int(180 * (y - TAMANO[1] // 2) / (TAMANO[1] / 2))
        draw_overlay.line([(0, y), (TAMANO[0], y)], fill=(0, 0, 0, alpha))
    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(base)
    font = _fuente(80)

    palabras = titulo.upper().split()
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
    if len(palabras) > sum(len(l.split()) for l in lineas):
        ultima = lineas[-1]
        while draw.textlength(ultima + "...", font=font) > TAMANO[0] * 0.9 and " " in ultima:
            ultima = ultima.rsplit(" ", 1)[0]
        lineas[-1] = ultima + "..."

    color_acento = random.choice([(255, 210, 0), (255, 255, 255), (0, 230, 160)])
    y = TAMANO[1] - 40 - len(lineas) * 95
    for ln in lineas:
        tw = draw.textlength(ln, font=font)
        x = (TAMANO[0] - tw) / 2
        # contorno negro (outline) para legibilidad en cualquier fondo
        for dx in (-3, 3):
            for dy in (-3, 3):
                draw.text((x + dx, y + dy), ln, font=font, fill=(0, 0, 0))
        draw.text((x, y), ln, font=font, fill=color_acento)
        y += 95

    os.makedirs(os.path.dirname(salida_png), exist_ok=True)
    base.save(salida_png, quality=95)
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
    generar_miniatura(guion["titulo"], primera_imagen, "output/thumbnails/demo.png")
