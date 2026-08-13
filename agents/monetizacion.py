"""
AGENTE 15: MONETIZACIÓN POR AFILIADOS ("Monetizacion")
----------------------------------------------------
Recomienda automáticamente, en la descripción del video, 1-2 productos de
un catálogo curado por ti (config/productos_afiliados.yaml) que estén
relacionados con el tema exacto del video, con tus enlaces de afiliado de
Amazon Associates y/o Mercado Libre Afiliados.

Reglas seguidas (investigadas, no improvisadas, para no arriesgar la
cuenta de afiliado ni la del canal):
  - Amazon exige un texto EXACTO de identificación como afiliado en tu
    sitio/canal (Operating Agreement, sección 5) + un aviso "claro y
    visible" junto a cada enlace (la FTC acepta algo tan simple como
    "(enlace de afiliado)"). Ambos se agregan automáticamente aquí.
  - Amazon PROHÍBE frases tipo "apoya el canal comprando aquí" (lo
    consideran incentivar clics de forma indebida) -> nunca se usa esa
    redacción, solo se presenta el producto de forma informativa.
  - Si ningún producto del catálogo coincide lo suficiente con el tema del
    video, no se muestra nada (mejor cero recomendaciones que una
    irrelevante que reste confianza).
  - Si un producto del catálogo todavía no tiene enlace real (sigue en
    "PENDIENTE"), se ignora automáticamente sin romper nada.
"""
import re

import yaml

from agents.utils import log

AGENT = "Monetizacion"
RUTA_CATALOGO = "config/productos_afiliados.yaml"


def _cargar_catalogo(ruta: str = RUTA_CATALOGO) -> dict:
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        log(AGENT, f"No se encontró {ruta}; se omite la recomendación de productos.")
        return {}


def _tiene_enlace_real(url: str) -> bool:
    return bool(url) and url.strip().upper() not in ("PENDIENTE", "OBTENER_TU_ENLACE_AQUI", "")


def _puntaje(palabras_clave_producto: list, texto_video: str) -> float:
    texto_video = texto_video.lower()
    if not palabras_clave_producto:
        return 0.0
    coincidencias = sum(1 for kw in palabras_clave_producto if kw.lower() in texto_video)
    return coincidencias / len(palabras_clave_producto)


def seleccionar_productos(guion: dict, ruta_catalogo: str = RUTA_CATALOGO) -> list:
    """Devuelve una lista de productos (dicts) del catálogo que coinciden
    con el tema del video, ordenados de mejor a peor coincidencia, ya
    filtrados por los que sí tienen al menos un enlace real configurado."""
    datos = _cargar_catalogo(ruta_catalogo)
    productos = datos.get("productos", [])
    cfg = datos.get("configuracion", {})
    max_productos = cfg.get("max_productos_por_video", 2)
    umbral = cfg.get("umbral_relevancia_minima", 0.15)

    texto_video = " ".join([
        guion.get("keyword_principal", ""),
        guion.get("titulo", ""),
        guion.get("descripcion", ""),
        " ".join(guion.get("tags", [])),
    ])

    candidatos = []
    for p in productos:
        tiene_amazon = _tiene_enlace_real(p.get("amazon_url", ""))
        tiene_ml = _tiene_enlace_real(p.get("mercadolibre_url", ""))
        if not tiene_amazon and not tiene_ml:
            continue  # producto de ejemplo sin enlaces reales todavía: se ignora
        score = _puntaje(p.get("palabras_clave", []), texto_video)
        if score >= umbral:
            candidatos.append((score, p))

    candidatos.sort(key=lambda t: t[0], reverse=True)
    seleccionados = [p for _, p in candidatos[:max_productos]]
    if seleccionados:
        log(AGENT, f"Productos recomendados para este video: {[p['nombre'] for p in seleccionados]}")
    else:
        log(AGENT, "Ningún producto del catálogo coincide lo suficiente con este video (o faltan enlaces reales); no se recomienda ninguno.")
    return seleccionados


def construir_bloque_afiliados(productos: list, ruta_catalogo: str = RUTA_CATALOGO) -> str:
    """Arma el bloque de texto para la descripción de YouTube, con el
    aviso legal exacto que exige Amazon + el aviso de "enlace de afiliado"
    junto a cada link (requisito de la FTC), sin ninguna frase de presión
    para hacer clic (prohibido por Amazon)."""
    if not productos:
        return ""

    datos = _cargar_catalogo(ruta_catalogo)
    cfg = datos.get("configuracion", {})
    texto_amazon = cfg.get("amazon_disclosure_text",
                            "Como Afiliado de Amazon, obtengo ingresos por las compras adscritas que cumplen los requisitos aplicables.")
    texto_ml = cfg.get("mercadolibre_disclosure_text",
                        "Como afiliado de Mercado Libre, puedo recibir una comisión por las compras realizadas a través de estos enlaces.")

    lineas = ["🛒 PRODUCTOS RELACIONADOS CON ESTE VIDEO:"]
    hay_amazon = False
    hay_ml = False
    for p in productos:
        nombre = p.get("nombre", "Producto")
        nota = p.get("nota", "")
        sufijo_nota = f" — {nota}" if nota else ""
        lineas.append(f"• {nombre}{sufijo_nota}")
        if _tiene_enlace_real(p.get("amazon_url", "")):
            lineas.append(f"   Amazon (enlace de afiliado): {p['amazon_url']}")
            hay_amazon = True
        if _tiene_enlace_real(p.get("mercadolibre_url", "")):
            lineas.append(f"   Mercado Libre (enlace de afiliado): {p['mercadolibre_url']}")
            hay_ml = True
    lineas.append("")

    avisos = []
    if hay_amazon:
        avisos.append(texto_amazon)
    if hay_ml:
        avisos.append(texto_ml)
    if avisos:
        lineas.append(" ".join(avisos))
        lineas.append("")

    return "\n".join(lineas)


if __name__ == "__main__":
    guion_demo = {
        "keyword_principal": "reducir inflamación naturalmente",
        "titulo": "7 Claves Naturales Contra la Inflamación",
        "descripcion": "Aprende a combatir la inflamación crónica con alimentos y hábitos.",
        "tags": ["inflamación", "dieta antiinflamatoria", "articulaciones"],
    }
    productos = seleccionar_productos(guion_demo)
    print(construir_bloque_afiliados(productos))
