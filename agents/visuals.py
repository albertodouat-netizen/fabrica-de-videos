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
  - Pollinations.ai (imagen IA, sin key, sin límite) -> cuando el stock no
    tiene la escena exacta que pide el guion, se genera una imagen realista
    a medida en vez de conformarse con algo "parecido" o un fondo genérico.
"""
import os
import random
import re
import urllib.parse
import requests
from PIL import Image, ImageDraw, ImageFont

from agents.utils import load_config, log, slugify

AGENT = "VisualScout"

_PALABRAS_PROHIBIDAS = [
    "ilustracion", "ilustración", "ilustraciones", "animacion", "animación",
    "animaciones", "dibujo", "dibujos", "diagrama", "diagramas", "grafico",
    "gráfico", "graficos", "gráficos", "caricatura", "cartoon", "clipart",
    "vector", "icono", "iconos", "infografia", "infografía",
    # Equivalentes en inglés (los "visual" ahora se piden en inglés para
    # buscar mejor en Pexels/Pixabay, así que filtramos también en ese idioma):
    "illustration", "illustrations", "animation", "animations", "drawing",
    "drawings", "diagram", "diagrams", "graphic", "graphics", "chart",
    "charts", "icon", "icons", "infographic", "infographics", "sketch",
    "render", "3d", "painting", "anime", "clip-art",
]


def _limpiar_palabra_clave(keyword: str) -> str:
    """Red de seguridad: si el guion (por error del LLM) pide una ilustración,
    diagrama o animación, se limpia el término para buscar en su lugar una
    escena real y filmable, tal como pide el usuario (nada de dibujitos)."""
    palabras = keyword.split()
    limpio = [p for p in palabras if p.lower().strip(",.") not in _PALABRAS_PROHIBIDAS]
    resultado = " ".join(limpio).strip()
    return resultado if resultado else "persona en la vida real, fotografía realista"


_CONECTORES_BUSQUEDA = {
    "de", "del", "la", "el", "los", "las", "para", "con", "en", "y", "a",
    "un", "una", "que", "su", "sus", "muy", "más", "mas", "al", "es",
    # Stopwords en inglés (las keywords visuales ahora se generan en inglés):
    "the", "of", "in", "on", "at", "a", "an", "with", "and", "to", "for",
    "is", "her", "his", "their", "close", "up", "shot",
}


def _version_amplia_busqueda(keyword: str) -> str:
    """Devuelve una versión más simple/genérica de la palabra clave (2-3
    palabras núcleo), usada como segundo intento cuando la frase completa y
    muy específica no trae ningún resultado de VIDEO real en los bancos
    gratuitos. Preferimos siempre metraje real (aunque sea de una escena algo
    más genérica) antes que quedarnos solo con foto o imagen generada."""
    palabras = [p for p in re.findall(r"[a-záéíóúñ]+", keyword.lower()) if p not in _CONECTORES_BUSQUEDA]
    if not palabras:
        return keyword
    return " ".join(palabras[:3])


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


# Puntaje mínimo (0 a 1) para ACEPTAR un resultado de stock (Pexels/Pixabay).
# Antes de este cambio, el sistema aceptaba "el menos malo" de los candidatos
# aunque no tuviera casi nada que ver con la palabra clave (Pexels/Pixabay dan
# muy poco texto descriptivo real, así que el puntaje solía ser bajo de todas
# formas). Esa era la causa principal de que "las imágenes no tengan nada que
# ver con el contenido": preferimos SIEMPRE una imagen IA generada a medida
# para esa frase exacta (ver _generar_imagen_ia) antes que un video/foto de
# stock que coincide poco o nada.
UMBRAL_RELEVANCIA_MINIMA_STOCK = 0.34


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
    params = {"key": api_key, "q": query, "per_page": por_pagina, "safesearch": "true"}
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
    params = {"key": api_key, "q": query, "per_page": por_pagina, "image_type": "photo", "safesearch": "true"}
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


def _sanear_descripcion_para_ia(texto: str) -> str:
    """Quita términos abstractos de 'cuerpo/figura' que en la práctica
    inducen a los generadores de imágenes a crear estudios de figura
    desnuda (hallazgo real: 'body figure', 'cuerpo humano' como frase
    aislada generó desnudos explícitos en pruebas reales de esta auditoría).
    Se reemplazan por una escena concreta y con ropa, nunca una persona
    aislada descrita solo por su "cuerpo"."""
    texto_bajo = texto.lower()
    disparadores = ["body figure", "human figure", "person figure", "human body",
                    "cuerpo humano", "figura humana", "silueta humana", "the body",
                    "female body", "male body", "woman's body", "man's body"]
    if any(d in texto_bajo for d in disparadores):
        return "person in casual clothing smiling in a bright kitchen"
    return texto


def _generar_imagen_ia(descripcion: str, destino_jpg: str, tamano=(1280, 720),
                        contexto: str = "") -> bool:
    """Genera una imagen FOTORREALISTA a medida con Pollinations.ai (100%
    gratis, sin API key, sin límite de uso razonable). Se usa cuando ningún
    banco de stock tiene la escena exacta que pide el guion: en vez de
    conformarnos con algo "parecido" o un fondo de color genérico, se crea
    una imagen que representa EXACTAMENTE la frase, mejorando mucho la
    coincidencia entre lo narrado y lo que se ve en pantalla.

    'contexto' (opcional) es la frase completa del beat (lo que se está
    narrando en ese momento): ayuda al modelo a generar una escena más
    específica que la sola palabra clave (ej. keyword="manos" + contexto=
    "corta el ajo justo antes de cocinarlo" da una imagen mucho más precisa
    que "manos" sola).

    NOTA DE SEGURIDAD (auditoría agosto 2026): se descubrió que un beat con
    keyword abstracta tipo "body figure" generó un desnudo explícito real.
    Se corrigió en 3 capas: (1) se sanea la descripción para nunca describir
    a una persona solo por su "cuerpo/figura" en abstracto, (2) el prompt
    ahora pide encuadre de la cintura para arriba y ropa específica (mucho
    más efectivo que solo decir "con ropa"), (3) cada imagen generada se
    verifica con Gemini Vision antes de aceptarla (ver
    _imagen_es_seguro_gemini), con reintentos con otra semilla si falla."""
    descripcion = _sanear_descripcion_para_ia(descripcion)
    base = f"{descripcion}. {contexto}".strip(". ").strip()
    prompt = (
        f"{base}, fotografía realista tipo documental, cámara real, luz natural, "
        f"alta definición, composición cinematográfica, sin texto, sin marca de agua, "
        f"sin logotipos, persona real (no dibujo, no animación, no 3D), "
        f"encuadre de la cintura hacia arriba o solo manos/rostro, persona vestida "
        f"con camiseta o camisa casual, ambiente cotidiano tipo cocina u hogar, "
        f"nunca un estudio de figura ni retrato de cuerpo aislado, "
        f"contenido apto para todo público, familiar, profesional"
    )
    prompt_codificado = urllib.parse.quote(prompt)

    # Hasta 3 intentos con semillas distintas: cada imagen se verifica de
    # verdad con Gemini Vision (ver _imagen_es_segura_gemini) antes de
    # aceptarla. safe=true y model=flux se dejan puestos como ayuda
    # adicional, aunque la auditoría de agosto 2026 confirmó en vivo que
    # 'safe=true' NO bloquea de forma confiable el contenido NSFW por sí
    # solo -- por eso la verificación con Gemini es la que de verdad manda.
    for intento in range(3):
        semilla = random.randint(1, 999999)
        url = (f"https://image.pollinations.ai/prompt/{prompt_codificado}"
               f"?width={tamano[0]}&height={tamano[1]}&nologo=true&seed={semilla}"
               f"&safe=true&model=flux")
        try:
            r = requests.get(url, timeout=40)
            r.raise_for_status()
            if len(r.content) < 5000:  # respuesta sospechosamente pequeña (error disfrazado de imagen)
                continue
            with open(destino_jpg, "wb") as f:
                f.write(r.content)
        except Exception as e:
            log(AGENT, f"No se pudo generar imagen IA para '{descripcion}': {e}")
            continue

        try:
            if _imagen_es_segura_gemini(destino_jpg):
                return True
            log(AGENT, f"Imagen IA descartada por seguridad para '{descripcion}' "
                        f"(intento {intento+1}/3); probando con otra semilla...")
        except Exception as e:
            # Si la verificación de seguridad falla técnicamente (sin key de
            # Gemini, sin cuota, etc.), no podemos confirmar que sea segura,
            # así que por precaución NO se acepta esta imagen en concreto.
            log(AGENT, f"Aviso: no se pudo verificar la seguridad de la imagen IA ({e}); "
                        f"se descarta por precaución.")
        try:
            os.remove(destino_jpg)
        except OSError:
            pass

    log(AGENT, f"No se logró una imagen IA segura para '{descripcion}' tras 3 intentos; "
                f"se usará un fondo de respaldo en su lugar.")
    return False


def _imagen_es_segura_gemini(ruta_jpg: str) -> bool:
    """Verificación REAL (no un heurístico de color) de que una imagen no
    contiene desnudos ni contenido inapropiado, usando Gemini Vision -- el
    mismo modelo que ya usa agents/qa_coherencia.py. Se aplica SOLO a
    imágenes generadas por IA (el punto de mayor riesgo real, confirmado en
    esta auditoría: Pollinations puede generar desnudos explícitos incluso
    con 'safe=true' activado). Lanza excepción si no se puede verificar
    (sin key de Gemini configurada, cuota agotada, etc.), para que quien
    llama decida qué hacer (nunca se asume "seguro" por defecto)."""
    import base64
    cfg = load_config()
    gemini_key = cfg["apis"].get("gemini_api_key", "")
    if not gemini_key or "OBTENER_GRATIS" in gemini_key:
        raise RuntimeError("Sin gemini_api_key configurada: no se puede verificar la seguridad de esta imagen.")

    from agents.presupuesto_ia import registrar_uso_gemini
    with open(ruta_jpg, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    prompt = (
        "Responde ÚNICAMENTE con SI o NO, sin nada más. "
        "¿Esta imagen muestra desnudos, semi-desnudos, ropa interior, ropa de "
        "baño, piel descubierta de forma sexual o sugerente, o cualquier "
        "contenido no apto para un canal de salud familiar? Sé estricto: "
        "cualquier duda razonable cuenta como SI."
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
    body = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}]}]}
    r = requests.post(url, json=body, timeout=30)
    r.raise_for_status()
    registrar_uso_gemini(1)
    texto = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
    return not texto.startswith("SI")


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

    def _candidatos_ordenados_seguros(self, candidatos, keyword, umbral_minimo=0.0):
        """Como _mejor_no_usado, pero devuelve TODOS los candidatos válidos
        ordenados por relevancia (no solo el mejor), y descarta de entrada
        cualquiera cuyo texto descriptivo/tags contenga una palabra de la
        lista negra de seguridad (ver agents/moderacion_visual.py). Así, si
        el mejor candidato resulta riesgoso al revisar los píxeles después
        de descargarlo, hay más opciones para probar en su lugar."""
        from agents.moderacion_visual import es_texto_inseguro
        disponibles = [(u, t) for u, t in candidatos
                       if u not in self.urls_usadas and not es_texto_inseguro(t)]
        if not disponibles:
            return []
        disponibles.sort(key=lambda ut: _puntaje_relevancia(keyword, ut[1]), reverse=True)
        if umbral_minimo > 0:
            disponibles = [(u, t) for u, t in disponibles
                           if _puntaje_relevancia(keyword, t) >= umbral_minimo]
        return [u for u, t in disponibles]

    def _mejor_no_usado(self, candidatos, keyword, umbral_minimo=0.0):
        """candidatos: lista de (url, texto_meta). Devuelve el de mejor
        puntaje de relevancia que no se haya usado ya en este video, SIEMPRE
        que supere 'umbral_minimo' (si no, es preferible generar una imagen
        IA a medida en vez de aceptar algo que casi no tiene relación)."""
        ordenados = self._candidatos_ordenados_seguros(candidatos, keyword, umbral_minimo)
        return ordenados[0] if ordenados else None

    def obtener(self, keyword: str, carpeta_salida: str, tag: str, contexto: str = "") -> dict:
        orient_pexels = self.orientacion
        intentos = []
        # Video REAL (no generado) siempre tiene prioridad sobre imagen fija:
        # se ve más dinámico y "realista" de verdad. Si la keyword completa no
        # trae resultados de video, probamos una versión más simple (2-3
        # palabras clave del núcleo) antes de rendirnos e ir a foto/imagen IA:
        # a veces "manos cortando ajo fresco en tabla de madera" no da nada,
        # pero "cortando ajo" sí tiene metraje real disponible.
        variante_amplia = _version_amplia_busqueda(keyword)

        def _video_con_variante(buscar_fn):
            resultados = []
            try:
                resultados = buscar_fn(keyword)
            except Exception:
                resultados = []
            if not resultados and variante_amplia != keyword:
                try:
                    resultados = buscar_fn(variante_amplia)
                except Exception:
                    resultados = []
            return resultados

        if self.usar_pexels:
            intentos.append(("video", lambda: _video_con_variante(
                lambda q: _buscar_pexels_video(q, self.pexels_key, por_pagina=10, orientacion=orient_pexels))))
        if self.usar_pixabay:
            intentos.append(("video", lambda: _video_con_variante(
                lambda q: _buscar_pixabay_video(q, self.pixabay_key, por_pagina=10))))
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
            # Exigimos un mínimo de coincidencia real: preferimos generar una
            # imagen IA a medida (ver más abajo) antes que aceptar un
            # video/foto de stock que no tiene casi relación con la palabra
            # clave; esa era la causa principal de la incoherencia reportada.
            urls_candidatas = self._candidatos_ordenados_seguros(candidatos, keyword,
                                                                  umbral_minimo=UMBRAL_RELEVANCIA_MINIMA_STOCK)
            for url in urls_candidatas[:3]:  # hasta 3 intentos por proveedor antes de rendirse
                ext = ".mp4" if tipo == "video" else ".jpg"
                destino = os.path.join(carpeta_salida, f"{tag}_{slugify(keyword)}{ext}")
                try:
                    _descargar(url, destino)
                except Exception as e:
                    log(AGENT, f"No se pudo descargar '{keyword}': {e}")
                    self.urls_usadas.add(url)  # no reintentar la misma URL rota
                    continue

                self.urls_usadas.add(url)
                visual_candidato = {"tipo": "video" if tipo == "video" else "imagen", "ruta": destino, "keyword": keyword}
                return visual_candidato

        # Antes de resignarnos a un fondo genérico: generamos una imagen IA
        # hecha a medida para ESTA frase exacta (gratis, sin límite). Este es
        # ahora el camino MÁS FRECUENTE (no solo el último recurso), porque el
        # stock gratuito casi nunca tiene la escena exacta que pide el guion,
        # y una imagen mal relacionada es peor que una generada a propósito.
        destino_ia = os.path.join(carpeta_salida, f"{tag}_{slugify(keyword)}_ia.jpg")
        if _generar_imagen_ia(keyword, destino_ia, contexto=contexto):
            log(AGENT, f"'{keyword}': no había stock con buena coincidencia, se generó una imagen IA a medida.")
            return {"tipo": "imagen", "ruta": destino_ia, "keyword": keyword}

        # Último recurso: nada disponible en ningún banco para esta keyword
        destino_png = os.path.join(carpeta_salida, f"{tag}_{slugify(keyword)}_fallback.png")
        _generar_fondo_local(keyword, destino_png)
        return {"tipo": "imagen", "ruta": destino_png, "keyword": keyword}

    def re_obtener_evitando(self, keyword: str, carpeta_salida: str, tag: str, ruta_evitar: str,
                             contexto: str = "") -> dict:
        """Usado por el Verificador de Coherencia cuando Gemini Vision ya
        calificó el recurso actual con baja coincidencia: en vez de repetir
        otra búsqueda de stock (que ya demostró no tener nada mejor), vamos
        DIRECTO a generar una imagen IA a medida para esa frase exacta, la
        forma más confiable de garantizar coherencia real."""
        try:
            if os.path.exists(ruta_evitar):
                os.remove(ruta_evitar)
        except OSError:
            pass
        destino_ia = os.path.join(carpeta_salida, f"{tag}_{slugify(keyword)}_ia_v2.jpg")
        if _generar_imagen_ia(keyword, destino_ia, contexto=contexto):
            return {"tipo": "imagen", "ruta": destino_ia, "keyword": keyword}
        # Si por algún motivo Pollinations falla justo en este momento, como
        # red de seguridad reintentamos el flujo normal (stock -> IA -> fondo).
        return self.obtener(keyword, carpeta_salida, tag, contexto=contexto)


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
    tema_general = guion.get("keyword_principal", "") or guion.get("titulo", "")
    for i, cap in enumerate(guion["capitulos"]):
        beats = cap.get("beats", [])
        visuales_cap = []
        for j, beat in enumerate(beats):
            # Los 3 llamados obligatorios a suscripción (ver
            # agents/suscripcion_cta.py) no buscan stock: siempre muestran al
            # presentador fijo del canal (rostro humano real y consistente)
            # con el botón de suscripción, sin gastar cuota de Pexels/Pixabay.
            if beat.get("es_llamado_suscripcion"):
                # Los 3 llamados obligatorios a suscripción (ver
                # agents/suscripcion_cta.py) usan una tarjeta gráfica sin
                # ningún rostro (real o generado): decisión tomada en la
                # auditoría de agosto 2026 para no arriesgar la política de
                # "personas de IA en temas sensibles" (salud) de YouTube.
                from agents.suscripcion_cta import generar_tarjeta_suscripcion
                momento = beat.get("momento_suscripcion", "inicio")
                try:
                    ruta_tarjeta = generar_tarjeta_suscripcion(momento, carpeta_salida, tag=f"cap{i}_b{j}")
                    visuales_cap.append({"tipo": "imagen", "ruta": ruta_tarjeta,
                                          "keyword": "tarjeta grafica de suscripcion"})
                    log(AGENT, f"Cap {i+1} beat {j+1}/{len(beats)}: llamado a suscripción ({momento}) "
                                f"-> tarjeta gráfica (sin rostro)")
                    continue
                except Exception as e:
                    log(AGENT, f"Aviso: no se pudo generar la tarjeta de suscripción ({e}); "
                                "se busca un visual normal de respaldo para este beat.")
                    beat = dict(beat)
                    beat["visual"] = "person smiling warmly outdoors in natural light"

            # Mención cruzada a otro video del canal (tráfico orgánico
            # interno, ver agents/promocion_cruzada.py): se muestra una
            # tarjeta con el título del video recomendado en vez de buscar
            # stock (nada de la vida real representa "otro video del canal").
            if beat.get("es_mencion_cruzada"):
                from agents.promocion_cruzada import generar_tarjeta_video_relacionado
                titulo_rel = beat.get("titulo_video_relacionado", "")
                try:
                    ruta_tarjeta = generar_tarjeta_video_relacionado(titulo_rel, carpeta_salida, tag=f"cap{i}_b{j}")
                    visuales_cap.append({"tipo": "imagen", "ruta": ruta_tarjeta,
                                          "keyword": "tarjeta de video relacionado del canal"})
                    log(AGENT, f"Cap {i+1} beat {j+1}/{len(beats)}: mención cruzada -> tarjeta '{titulo_rel}'")
                    continue
                except Exception as e:
                    log(AGENT, f"Aviso: no se pudo generar la tarjeta de video relacionado ({e}); "
                                "se busca un visual normal de respaldo para este beat.")
                    beat = dict(beat)
                    beat["visual"] = "friendly person smiling and recommending something"

            keyword = _limpiar_palabra_clave(beat.get("visual") or cap["nombre"])
            # El contexto incluye la frase exacta Y el tema general del video
            # (para que, si hace falta generar una imagen IA, esta encaje con
            # el resto del video y no solo con la frase aislada).
            contexto = beat.get("texto", "")
            if tema_general:
                contexto = f"{contexto} (tema general del video: {tema_general})"
            visual = buscador.obtener(keyword, carpeta_salida, tag=f"cap{i}_b{j}", contexto=contexto)
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
