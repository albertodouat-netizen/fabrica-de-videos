"""
AGENTE 4: VISUALES ("Visual Scout")
----------------------------------------------------
Descarga videoclips (y si no hay, fotos) libres de derechos y GRATIS para
ilustrar cada "beat" del guion, usando la palabra clave visual específica
que generó el Guionista. Diseñado para producir un video DINÁMICO y
COHERENTE con lo narrado:

  - Pide VARIOS candidatos por palabra clave y se queda con el que más se
    parece semánticamente a la palabra clave (usando los propios
    metadatos/tags que devuelven Pexels y Pixabay), en vez de aceptar
    ciegamente el primer resultado.
  - Un clip/foto distinto por cada beat (cortes frecuentes, nunca un mismo
    plano sostenido por mucho tiempo).
  - Nunca repite el mismo recurso dos veces dentro del mismo video.
  - Prioriza siempre metraje/foto REAL (nunca ilustraciones ni dibujos):
    Pexels/Pixabay (video) -> Pexels/Pixabay (foto) -> fondo local generado
    (solo como último recurso, si de verdad no hay nada disponible).
  - Soporta orientación horizontal (video largo) o vertical (Shorts).

Fuentes 100% gratuitas (con key gratis, sin tarjeta de crédito):
  - Pexels Video/Photo API   -> https://www.pexels.com/api/
  - Pixabay Video/Photo API  -> https://pixabay.com/api/docs/
"""
import os
import random
import re
import requests
from PIL import Image, ImageDraw, ImageFont

from agents.utils import load_config, log, slugify

AGENT = "VisualScout"

_PALABRAS_PROHIBIDAS = [
    "ilustracion", "ilustración", "ilustraciones", "animacion", "animación",
    "animaciones", "dibujo", "dibujos", "diagrama", "diagramas", "grafico",
    "gráfico", "graficos", "gráficos", "caricatura", "cartoon", "clipart",
    "vector", "icono", "iconos", "infografia", "infografía",
]


def _limpiar_palabra_clave(keyword: str) -> str:
    """Red de seguridad: si el guion (por error del LLM) pide una ilustración,
    diagrama o animación, se limpia el término para buscar en su lugar una
    escena real y filmable, tal como pide el usuario (nada de dibujitos)."""
    palabras = keyword.split()
    limpio = [p for p in palabras if p.lower().strip(",.") not in _PALABRAS_PROHIBIDAS]
    resultado = " ".join(limpio).strip()
    return resultado if resultado else "persona en la vida real, fotografía realista"


def _puntaje_relevancia(keyword: str, texto_meta: str) -> float:
    """Puntúa cuánto se parece el texto descriptivo/tags que devuelve la API
    a la palabra clave que pedimos (superposición de palabras). 0 a 1."""
    if not texto_meta:
        return 0.0
    palabras_kw = set(re.findall(r"[a-záéíóúñ]+", keyword.lower()))
    palabras_meta = set(re.findall(r"[a-záéíóúñ]+", texto_meta.lower()))
    if not palabras_kw:
        return 0.0
    interseccion = palabras_kw & palabras_meta
    return len(interseccion) / len(palabras_kw)


def _buscar_pexels_video(query, api_key, por_pagina=6, orientacion="landscape"):
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {"query": query, "per_page": por_pagina, "orientation": orientacion}
    r = requests.get(url, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    resultados = []
    for video in r.json().get("videos", []):
        archivos = sorted(video["video_files"], key=lambda f: f.get("width", 0))
        objetivo = (960, 1290) if orientacion == "landscape" else (540, 900)
        candidato = next((f for f in archivos if objetivo[0] <= f.get("width", 0) <= objetivo[1]), None)
        if not candidato and archivos:
            candidato = archivos[0]
        if candidato:
            # Pexels no da descripción textual del contenido, pero el "alt"
            # a veces sí viene informado; usamos lo que haya disponible.
            texto_meta = video.get("url", "") + " " + str(video.get("tags", ""))
            resultados.append((candidato["link"], texto_meta))
    return resultados


def _buscar_pexels_foto(query, api_key, por_pagina=6, orientacion="landscape"):
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": api_key}
    params = {"query": query, "per_page": por_pagina, "orientation": orientacion}
    r = requests.get(url, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    resultados = []
    for p in r.json().get("photos", []):
        texto_meta = p.get("alt", "") or ""
        resultados.append((p["src"]["large"], texto_meta))
    return resultados


def _buscar_pixabay_video(query, api_key, por_pagina=6):
    url = "https://pixabay.com/api/videos/"
    params = {"key": api_key, "q": query, "per_page": por_pagina}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    resultados = []
    for hit in r.json().get("hits", []):
        video_url = hit["videos"].get("medium", {}).get("url") or hit["videos"].get("small", {}).get("url")
        if video_url:
            texto_meta = hit.get("tags", "")
            resultados.append((video_url, texto_meta))
    return resultados


def _buscar_pixabay_foto(query, api_key, por_pagina=6):
    url = "https://pixabay.com/api/"
    params = {"key": api_key, "q": query, "per_page": por_pagina, "image_type": "photo"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    resultados = []
    for h in r.json().get("hits", []):
        if "largeImageURL" in h:
            resultados.append((h["largeImageURL"], h.get("tags", "")))
    return resultados


def _descargar(url, destino):
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    with open(destino, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 16):
            f.write(chunk)
    # Validación básica: un video/foto real casi nunca pesa unos pocos KB.
    # Si la descarga quedó truncada o el servidor devolvió un error disfrazado
    # de 200 OK, mejor descartarlo aquí que fallar más tarde en el render.
    tamano_minimo = 20_000 if destino.lower().endswith((".mp4", ".mov", ".webm")) else 3_000
    if os.path.getsize(destino) < tamano_minimo:
        os.remove(destino)
        raise ValueError(f"Descarga sospechosamente pequeña, descartada: {url}")
    return destino


def _generar_fondo_local(texto, destino_png, tamano=(1280, 720)):
    """Último recurso: fondo local generado (solo si no hubo NINGÚN resultado
    real disponible en los bancos gratuitos para esa palabra clave)."""
    colores = [
        ((25, 42, 86), (60, 110, 180)),
        ((15, 60, 45), (50, 140, 90)),
        ((70, 25, 60), (150, 60, 110)),
        ((40, 40, 40), (100, 100, 100)),
    ]
    c1, c2 = random.choice(colores)
    img = Image.new("RGB", tamano, c1)
    draw = ImageDraw.Draw(img)
    w, h = tamano
    for y in range(h):
        t = y / h
        color = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
        draw.line([(0, y), (w, y)], fill=color)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except Exception:
        font = ImageFont.load_default()
    palabras = texto.split()
    linea, lineas = "", []
    for palabra in palabras:
        prueba = (linea + " " + palabra).strip()
        if draw.textlength(prueba, font=font) > w * 0.8:
            lineas.append(linea)
            linea = palabra
        else:
            linea = prueba
    if linea:
        lineas.append(linea)
    alto_total = len(lineas) * 55
    y0 = (h - alto_total) // 2
    for i, ln in enumerate(lineas[:5]):
        tw = draw.textlength(ln, font=font)
        draw.text(((w - tw) / 2, y0 + i * 55), ln, font=font, fill=(255, 255, 255))
    img.save(destino_png)
    return destino_png


class BuscadorVisualesUnicos:
    """Envuelve la búsqueda para garantizar que NINGÚN recurso se repita
    dentro del mismo video, que siempre se priorice metraje/foto real antes
    que el fondo generado localmente, y que el resultado elegido sea el que
    MEJOR coincide semánticamente con la palabra clave pedida (no el primero
    que aparezca)."""

    def __init__(self, cfg, orientacion="landscape"):
        self.pexels_key = cfg["apis"].get("pexels_api_key", "")
        self.pixabay_key = cfg["apis"].get("pixabay_api_key", "")
        self.usar_pexels = bool(self.pexels_key) and "OBTENER_GRATIS" not in self.pexels_key
        self.usar_pixabay = bool(self.pixabay_key) and "OBTENER_GRATIS" not in self.pixabay_key
        self.urls_usadas = set()
        self.orientacion = orientacion  # "landscape" (16:9) o "portrait" (9:16, para Shorts)

    def _mejor_no_usado(self, candidatos, keyword):
        """candidatos: lista de (url, texto_meta). Devuelve el de mejor
        puntaje de relevancia que no se haya usado ya en este video."""
        disponibles = [(u, t) for u, t in candidatos if u not in self.urls_usadas]
        if not disponibles:
            return None
        disponibles.sort(key=lambda ut: _puntaje_relevancia(keyword, ut[1]), reverse=True)
        return disponibles[0][0]

    def obtener(self, keyword: str, carpeta_salida: str, tag: str) -> dict:
        orient_pexels = self.orientacion
        intentos = []
        if self.usar_pexels:
            intentos.append(("video", lambda: _buscar_pexels_video(keyword, self.pexels_key, orientacion=orient_pexels)))
        if self.usar_pixabay:
            intentos.append(("video", lambda: _buscar_pixabay_video(keyword, self.pixabay_key)))
        if self.usar_pexels:
            intentos.append(("foto", lambda: _buscar_pexels_foto(keyword, self.pexels_key, orientacion=orient_pexels)))
        if self.usar_pixabay:
            intentos.append(("foto", lambda: _buscar_pixabay_foto(keyword, self.pixabay_key)))

        for tipo, buscar in intentos:
            try:
                candidatos = buscar()
            except Exception as e:
                log(AGENT, f"Aviso buscando '{keyword}': {e}")
                continue
            url = self._mejor_no_usado(candidatos, keyword)
            if not url:
                continue
            ext = ".mp4" if tipo == "video" else ".jpg"
            destino = os.path.join(carpeta_salida, f"{tag}_{slugify(keyword)}{ext}")
            try:
                _descargar(url, destino)
                self.urls_usadas.add(url)
                return {"tipo": "video" if tipo == "video" else "imagen", "ruta": destino, "keyword": keyword}
            except Exception as e:
                log(AGENT, f"No se pudo descargar '{keyword}': {e}")
                self.urls_usadas.add(url)  # no reintentar la misma URL rota

        # Último recurso: nada disponible en ningún banco para esta keyword
        destino_png = os.path.join(carpeta_salida, f"{tag}_{slugify(keyword)}_fallback.png")
        _generar_fondo_local(keyword, destino_png)
        return {"tipo": "imagen", "ruta": destino_png, "keyword": keyword}

    def re_obtener_evitando(self, keyword: str, carpeta_salida: str, tag: str, ruta_evitar: str) -> dict:
        """Usado por el Verificador de Coherencia: pide un candidato distinto
        al que ya se probó (porque no coincidía con lo narrado)."""
        try:
            if os.path.exists(ruta_evitar):
                os.remove(ruta_evitar)
        except OSError:
            pass
        return self.obtener(keyword, carpeta_salida, tag)


def obtener_visuales_para_guion(guion: dict, carpeta_salida: str, orientacion="landscape") -> dict:
    """
    Devuelve un visual DISTINTO por cada beat (no por capítulo), para permitir
    cortes frecuentes y dinámicos. Estructura:
    {"visuales_por_capitulo": [[visual_beat_0, visual_beat_1, ...], ...]}
    """
    cfg = load_config()
    os.makedirs(carpeta_salida, exist_ok=True)
    buscador = BuscadorVisualesUnicos(cfg, orientacion=orientacion)

    visuales_por_capitulo = []
    for i, cap in enumerate(guion["capitulos"]):
        beats = cap.get("beats", [])
        visuales_cap = []
        for j, beat in enumerate(beats):
            keyword = _limpiar_palabra_clave(beat.get("visual") or cap["nombre"])
            visual = buscador.obtener(keyword, carpeta_salida, tag=f"cap{i}_b{j}")
            visuales_cap.append(visual)
            log(AGENT, f"Cap {i+1} beat {j+1}/{len(beats)}: '{keyword}' -> {visual['tipo']}")
        visuales_por_capitulo.append(visuales_cap)

    fuente = "pexels/pixabay (real)" if (buscador.usar_pexels or buscador.usar_pixabay) else "local"
    return {"visuales_por_capitulo": visuales_por_capitulo, "fuente": fuente, "_buscador": buscador}


if __name__ == "__main__":
    from agents.trend_scout import buscar_ideas_potenciales
    from agents.scriptwriter import generar_guion

    idea = buscar_ideas_potenciales()[0]
    guion = generar_guion(idea)
    visuales = obtener_visuales_para_guion(guion, "output/video/assets_demo")
    print(visuales)
