"""
AGENTE 28: PORTADA REAL DEL ESTUDIO ("PortadaEstudio")
------------------------------------------------------
Nace de la auditoría élite del 14-ago-2026, pedida explícitamente por el
usuario: hasta entonces, la "toma del documento" en las citas científicas
era METRAJE DE STOCK de una persona leyendo un paper cualquiera, no el
estudio citado. Eso es ambientación, no evidencia. Este agente muestra la
PRIMERA PÁGINA REAL del estudio científico citado, renderizada del PDF
oficial de acceso abierto, para que el espectador vea con sus propios ojos
el título, los autores y la revista del estudio que respalda el video.

Cómo funciona (100% gratis, verificado en vivo):
  1) Con el PMID del estudio se consulta Europe PMC y se obtiene el PMCID
     y si el artículo es de ACCESO ABIERTO (isOpenAccess == 'Y').
  2) Si es de acceso abierto, se descarga el PDF real desde
     https://europepmc.org/articles/{PMCID}?pdf=render (endpoint público
     de Europe PMC, probado en vivo con varios estudios).
  3) Se renderiza la PRIMERA PÁGINA con PyMuPDF y se compone una imagen
     16:9 estilo "documento sobre escritorio": la portada real, levemente
     inclinada, con sombra, sobre un fondo oscuro elegante, con una franja
     que dice "ESTUDIO CIENTÍFICO REAL" + revista y año.
  4) Esa imagen reemplaza el visual de stock del beat de cita científica.

Honestidad ante todo:
  - SOLO se muestra la portada del estudio que de verdad se cita (mismo
    PMID que va a la descripción). Nunca una portada "decorativa".
  - Si el estudio NO es de acceso abierto (no hay PDF legal disponible),
    se usa el visual de stock de siempre: mostrar la portada de un PDF
    pirateado no es una opción. La licencia de los artículos OA de Europe
    PMC (CC BY y similares) permite reproducir la primera página citando
    la fuente, que es exactamente lo que hacemos (cita en pantalla + enlace
    en la descripción).
"""
import os

import requests

from agents.utils import log

AGENT = "PortadaEstudio"

EUROPEPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def _pmcid_y_acceso_abierto(pmid: str):
    """Devuelve (pmcid, es_open_access) para un PMID, consultando Europe PMC."""
    try:
        r = requests.get(EUROPEPMC_SEARCH,
                         params={"query": f"EXT_ID:{pmid} AND SRC:MED",
                                 "format": "json", "resultType": "core"},
                         timeout=20)
        r.raise_for_status()
        for it in r.json().get("resultList", {}).get("result", []):
            return it.get("pmcid"), (it.get("isOpenAccess") == "Y")
    except Exception as e:
        log(AGENT, f"Aviso consultando PMCID de {pmid}: {e}")
    return None, False


def _descargar_pdf(pmcid: str, destino_pdf: str) -> bool:
    """Descarga el PDF real de un artículo de acceso abierto de Europe PMC."""
    try:
        r = requests.get(f"https://europepmc.org/articles/{pmcid}?pdf=render",
                         timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        ct = (r.headers.get("Content-Type") or "").lower()
        if r.status_code == 200 and "pdf" in ct and len(r.content) > 20000:
            with open(destino_pdf, "wb") as f:
                f.write(r.content)
            return True
        log(AGENT, f"El PDF de {pmcid} no está disponible ({r.status_code}, {ct}).")
    except Exception as e:
        log(AGENT, f"Aviso descargando PDF de {pmcid}: {e}")
    return False


def _render_primera_pagina(ruta_pdf: str, destino_png: str, dpi: int = 120) -> bool:
    try:
        import pymupdf
        doc = pymupdf.open(ruta_pdf)
        if len(doc) < 1:
            return False
        pix = doc[0].get_pixmap(dpi=dpi)
        pix.save(destino_png)
        doc.close()
        return True
    except Exception as e:
        log(AGENT, f"Aviso renderizando primera página: {e}")
        return False


def _componer_escena_documento(ruta_pagina_png: str, destino_jpg: str,
                                revista: str = "", anio: str = "",
                                resolucion=(1280, 720)) -> bool:
    """Compone la escena final 16:9: portada real centrada con leve
    rotación y sombra sobre fondo oscuro + franja inferior con la fuente."""
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont

        w, h = resolucion
        # Fondo: degradado oscuro azulado (serio, estilo documental)
        fondo = Image.new("RGB", (w, h), (16, 22, 34))
        d = ImageDraw.Draw(fondo)
        for y in range(h):
            t = y / h
            d.line([(0, y), (w, y)],
                   fill=(int(16 + 14 * t), int(22 + 18 * t), int(34 + 26 * t)))

        pagina = Image.open(ruta_pagina_png).convert("RGB")
        # La página ocupa ~86% de la altura del cuadro
        alto_pag = int(h * 0.86)
        escala = alto_pag / pagina.height
        pagina = pagina.resize((int(pagina.width * escala), alto_pag), Image.LANCZOS)

        # Marco blanco fino + rotación leve (efecto "documento sobre la mesa")
        margen = 6
        con_marco = Image.new("RGB", (pagina.width + margen * 2, pagina.height + margen * 2), (255, 255, 255))
        con_marco.paste(pagina, (margen, margen))
        rotada = con_marco.rotate(-2.2, expand=True, resample=Image.BICUBIC,
                                   fillcolor=None)
        # Sombra suave
        sombra = Image.new("RGBA", rotada.size, (0, 0, 0, 0))
        alpha = rotada.convert("L").point(lambda p: 160)
        sombra.putalpha(alpha)
        sombra = sombra.filter(ImageFilter.GaussianBlur(14))

        cx = (w - rotada.width) // 2
        cy = (h - rotada.height) // 2 - int(h * 0.02)
        fondo.paste((0, 0, 0), (cx + 12, cy + 16), sombra)

        mascara = Image.new("L", rotada.size, 0)
        md = ImageDraw.Draw(mascara)
        md.rectangle([0, 0, rotada.width, rotada.height], fill=255)
        mascara = rotada.convert("L").point(lambda p: 255 if p > 0 else 0)
        fondo.paste(rotada, (cx, cy), mascara)

        # Franja inferior con la fuente real
        franja_h = int(h * 0.11)
        franja = Image.new("RGBA", (w, franja_h), (8, 10, 16, 216))
        fondo.paste(Image.alpha_composite(
            fondo.crop((0, h - franja_h, w, h)).convert("RGBA"), franja).convert("RGB"),
            (0, h - franja_h))

        def _fuente(tam):
            try:
                return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", tam)
            except Exception:
                return ImageFont.load_default()

        d = ImageDraw.Draw(fondo)
        etiqueta = "ESTUDIO CIENTÍFICO REAL"
        fuente_et = _fuente(int(franja_h * 0.34))
        d.text((int(w * 0.03), h - franja_h + int(franja_h * 0.12)), etiqueta,
               font=fuente_et, fill=(120, 220, 160))
        pie = ""
        if revista and anio:
            pie = f"{revista}, {anio} — enlace en la descripción"
        elif revista:
            pie = f"{revista} — enlace en la descripción"
        else:
            pie = "Enlace al estudio en la descripción"
        fuente_pie = _fuente(int(franja_h * 0.26))
        # recortar si no cabe
        max_w = w * 0.94
        while d.textlength(pie, font=fuente_pie) > max_w and len(pie) > 12:
            pie = pie[:-2]
        d.text((int(w * 0.03), h - franja_h + int(franja_h * 0.55)), pie,
               font=fuente_pie, fill=(225, 225, 230))

        fondo.save(destino_jpg, quality=90)
        return True
    except Exception as e:
        log(AGENT, f"Aviso componiendo la escena del documento: {e}")
        return False


def generar_visual_portada_estudio(estudio: dict, carpeta_salida: str, tag: str,
                                    resolucion=(1280, 720)):
    """Punto de entrada: intenta crear la imagen con la PORTADA REAL del
    estudio citado. Devuelve la ruta del .jpg listo para el editor, o None
    si no fue posible (estudio sin acceso abierto, PDF no disponible...):
    en ese caso quien llama usa el visual de stock de siempre. Nunca rompe
    la generación del video."""
    pmid = str(estudio.get("pmid") or "").strip()
    if not pmid:
        return None
    os.makedirs(carpeta_salida, exist_ok=True)

    pmcid, es_oa = _pmcid_y_acceso_abierto(pmid)
    if not pmcid or not es_oa:
        log(AGENT, f"El estudio PMID {pmid} no es de acceso abierto: se usará el "
                    f"visual de documento genérico (mostrar un PDF sin licencia no es una opción).")
        return None

    ruta_pdf = os.path.join(carpeta_salida, f"_estudio_{tag}.pdf")
    ruta_pag = os.path.join(carpeta_salida, f"_pagina_{tag}.png")
    ruta_final = os.path.join(carpeta_salida, f"portada_estudio_{tag}.jpg")

    if not _descargar_pdf(pmcid, ruta_pdf):
        return None
    if not _render_primera_pagina(ruta_pdf, ruta_pag):
        return None
    ok = _componer_escena_documento(ruta_pag, ruta_final,
                                     revista=(estudio.get("revista") or "").strip(),
                                     anio=str(estudio.get("anio") or "").strip(),
                                     resolucion=resolucion)
    # limpieza de temporales pesados
    for ruta in (ruta_pdf, ruta_pag):
        try:
            os.remove(ruta)
        except OSError:
            pass
    if ok:
        log(AGENT, f"Portada REAL del estudio PMID {pmid} ({pmcid}) renderizada del PDF "
                    f"oficial de acceso abierto -> {os.path.basename(ruta_final)}")
        return ruta_final
    return None


if __name__ == "__main__":
    est = {"pmid": "40418260", "revista": "Nutrition Reviews", "anio": "2025"}
    print(generar_visual_portada_estudio(est, "/tmp/test_portada", "demo"))
