"""
AGENTE 24: CALLOUTS DE CIFRAS VERIFICADAS ("CalloutCifras")
------------------------------------------------------------
El usuario pidió explícitamente: cuando el video presente una estadística,
esta debe (a) salir de una fuente primaria real, validada y verificada
(esto ya lo hace agents/investigacion_cientifica.py: busca en Europe PMC,
verifica cada cifra contra el resumen real del estudio, y solo dejar el
enlace en la descripción si además carga de verdad), y (b) mostrarse en
pantalla de forma fácil de entender para quien está viendo el video (no
solo mencionada de pasada en el audio).

Este agente se encarga de la parte (b): genera un pequeño recuadro gráfico
("callout") con la cifra en grande, para los beats cuya cifra ya fue
verificada contra una fuente real por el Investigador Científico. Se
dibuja con Pillow (sin IA, siempre legible), y se superpone sobre el video
del beat correspondiente sin taparlo por completo (esquina inferior
izquierda, para no chocar con los subtítulos que van centrados abajo).
"""
import os

from PIL import Image, ImageDraw, ImageFont

AGENT = "CalloutCifras"


def _fuente(tam):
    ruta = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(ruta):
        return ImageFont.truetype(ruta, tam)
    return ImageFont.load_default()


def generar_overlay_cifra(cifra: str, carpeta_salida: str, tag: str,
                           resolucion=(1280, 720)) -> str:
    """Genera un PNG TRANSPARENTE con la cifra destacada en grande, listo
    para superponerse sobre el video del beat (no reemplaza el video, solo
    se agrega encima). Estilo simple y legible: recuadro semi-transparente
    + icono de barras + la cifra + 'dato verificado' como pie de página."""
    w, h = resolucion
    img = Image.new("RGBA", resolucion, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    ancho_caja = int(w * 0.40)
    alto_caja = int(h * 0.22)
    x0, y0 = int(w * 0.04), h - alto_caja - int(h * 0.06)
    x1, y1 = x0 + ancho_caja, y0 + alto_caja

    draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(10, 10, 15, 205),
                            outline=(255, 210, 0, 255), width=4)

    # Icono simple de barras ascendentes (dibujado a mano, sin depender de
    # ninguna fuente de emoji ni de IA generativa).
    base_x = x0 + 24
    base_y = y1 - 24
    alturas = [0.30, 0.55, 0.85]
    ancho_barra = 14
    for k, factor in enumerate(alturas):
        bx0 = base_x + k * (ancho_barra + 8)
        by1 = base_y
        by0 = base_y - int((alto_caja - 60) * factor)
        draw.rectangle([bx0, by0, bx0 + ancho_barra, by1], fill=(255, 210, 0, 255))

    texto_x = base_x + 3 * (ancho_barra + 8) + 14
    font_cifra = _fuente(max(30, int(alto_caja * 0.36)))
    draw.text((texto_x, y0 + 14), cifra, font=font_cifra, fill=(255, 255, 255, 255))

    font_pie = _fuente(max(14, int(alto_caja * 0.13)))
    pie = "Dato verificado con estudios reales"
    # Envolver el pie de página si no cabe en el ancho de la caja
    max_w_pie = (x1 - texto_x) - 10
    palabras = pie.split()
    linea, lineas = "", []
    for palabra in palabras:
        prueba = (linea + " " + palabra).strip()
        if draw.textlength(prueba, font=font_pie) > max_w_pie:
            lineas.append(linea)
            linea = palabra
        else:
            linea = prueba
    if linea:
        lineas.append(linea)
    y_pie = y0 + 14 + font_cifra.size + 10
    for ln in lineas[:2]:
        draw.text((texto_x, y_pie), ln, font=font_pie, fill=(220, 220, 220, 255))
        y_pie += font_pie.size + 4

    os.makedirs(carpeta_salida, exist_ok=True)
    destino = os.path.join(carpeta_salida, f"{tag}_callout_cifra.png")
    img.save(destino)
    return destino
