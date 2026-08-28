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
import time
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
# Subido de 0.34 a 0.50 (auditoría con video real, 18-ago-2026): con 0.34
# seguían pasando visuales que coincidían en UNA palabra suelta con la
# keyword ("leaves" para "calming sound of leaves") pero no con la idea.
# Con 0.50 el stock debe coincidir en al menos la mitad de las palabras
# clave; si no, se genera imagen IA a medida (más fiel a la idea).
UMBRAL_RELEVANCIA_MINIMA_STOCK = 0.50


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


_PALABRAS_PERSONA = re.compile(
    r"\b(person|people|man|men|woman|women|human|face|body|girl|boy|child|"
    r"children|kid|lady|guy|hand|hands|arm|leg|skin|portrait|selfie|"
    r"persona|gente|hombre|mujer|niñ[oa]|rostro|cara|cuerpo|piel|mano)\b",
    re.IGNORECASE)


def _prompt_tiene_persona(texto: str) -> bool:
    """¿La escena pedida incluye personas o partes del cuerpo? Se usa para
    decidir si una imagen IA necesita verificación visual obligatoria
    (ver nota de verificación selectiva en _generar_imagen_ia)."""
    return bool(_PALABRAS_PERSONA.search(texto or ""))


def _generar_imagen_cloudflare(prompt: str, destino_jpg: str,
                               tamano=(1280, 720)) -> bool:
    """Genera una imagen con Cloudflare Workers AI (10.000 neurons/día
    gratis, verificado en vivo el 19-ago-2026 con la cuenta del usuario).

    Estrategia de modelos (ambos probados en vivo):
      - FLUX.1 Schnell: la mejor calidad, pero SOLO genera 1024x1024
        (la API rechaza width/height). Para 16:9 se recorta el centro.
      - SDXL: acepta width/height nativos (probado 1024x576), calidad buena.
    Para paisaje (videos largos) se usa FLUX + recorte (calidad manda);
    para retrato (Shorts, 720x1280) se usa SDXL nativo (evita recortar
    demasiado). Devuelve False sin romper nada si no hay llaves o falla."""
    cfg = load_config()
    token = cfg["apis"].get("cloudflare_api_token", "") or ""
    account = cfg["apis"].get("cloudflare_account_id", "") or ""
    if (not token or "OBTENER_GRATIS" in token or
            not account or "OBTENER_GRATIS" in account):
        return False

    es_paisaje = tamano[0] >= tamano[1]
    try:
        if es_paisaje:
            # FLUX 1024x1024 -> recorte central a la proporción pedida
            r = requests.post(
                f"https://api.cloudflare.com/client/v4/accounts/{account}"
                f"/ai/run/@cf/black-forest-labs/flux-1-schnell",
                headers={"Authorization": f"Bearer {token}"},
                json={"prompt": prompt[:2000], "steps": 8},
                timeout=90)
            r.raise_for_status()
            img_b64 = r.json().get("result", {}).get("image", "")
            if not img_b64:
                return False
            import base64 as _b64
            from io import BytesIO
            img = Image.open(BytesIO(_b64.b64decode(img_b64))).convert("RGB")
        else:
            # SDXL con dimensiones nativas (múltiplos de 8)
            w = (tamano[0] // 8) * 8
            h = (tamano[1] // 8) * 8
            r = requests.post(
                f"https://api.cloudflare.com/client/v4/accounts/{account}"
                f"/ai/run/@cf/stabilityai/stable-diffusion-xl-base-1.0",
                headers={"Authorization": f"Bearer {token}"},
                json={"prompt": prompt[:2000], "width": w, "height": h},
                timeout=120)
            r.raise_for_status()
            if "image" not in (r.headers.get("content-type") or ""):
                return False
            from io import BytesIO
            img = Image.open(BytesIO(r.content)).convert("RGB")

        # Ajuste exacto al tamaño pedido (recorte central + reescalado)
        ratio_obj = tamano[0] / tamano[1]
        ratio_img = img.width / img.height
        if abs(ratio_img - ratio_obj) > 0.01:
            if ratio_img > ratio_obj:  # muy ancha -> recortar lados
                nuevo_w = int(img.height * ratio_obj)
                x0 = (img.width - nuevo_w) // 2
                img = img.crop((x0, 0, x0 + nuevo_w, img.height))
            else:  # muy alta -> recortar arriba/abajo
                nuevo_h = int(img.width / ratio_obj)
                y0 = (img.height - nuevo_h) // 2
                img = img.crop((0, y0, img.width, y0 + nuevo_h))
        img = img.resize(tamano, Image.LANCZOS)
        img.save(destino_jpg, "JPEG", quality=92)
        log(AGENT, f"Imagen generada con Cloudflare Workers AI "
                   f"({'FLUX' if es_paisaje else 'SDXL'}) ✓")
        return True
    except Exception as e:
        log(AGENT, f"Aviso: Cloudflare Workers AI no disponible ({type(e).__name__}); "
                   f"se usa Pollinations como respaldo.")
        return False


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
    # PROMPT CONDICIONAL (auditoría con video real, 18-ago-2026): antes el
    # prompt SIEMPRE añadía "persona real... persona vestida con camiseta...
    # ambiente tipo cocina", incluso para escenas de plantas, comida o
    # paisajes. Resultado real visto por el usuario: imágenes incoherentes
    # (pedías "calma/sonido" y salían hojas con encuadres raros). Ahora el
    # refuerzo de "persona vestida" solo se añade si la escena SÍ incluye
    # personas; si no, se pide explícitamente una escena SIN personas.
    if _prompt_tiene_persona(base):
        refuerzo = (
            "persona real (no dibujo, no animación, no 3D), "
            "encuadre de la cintura hacia arriba o solo manos/rostro, persona vestida "
            "con camiseta o camisa casual, ambiente cotidiano y cálido, "
            "nunca un estudio de figura ni retrato de cuerpo aislado, "
        )
    else:
        refuerzo = "escena sin personas, enfoque en el objeto o ambiente descrito, "
    # ANTI-TEXTO-INVENTADO (auditoría video magnesio, 21-ago-2026): la IA
    # escribió "Citirato de Magnisim" y "El magnesio paterrese de absorción
    # antibiotici" en frascos/carteles. Los modelos de imagen NO saben
    # escribir: se exige explícitamente cero texto, etiquetas en blanco y
    # envases genéricos.
    prompt = (
        f"{base}, fotografía realista tipo documental, cámara real, luz natural, "
        f"alta definición, composición cinematográfica, "
        f"ABSOLUTELY NO TEXT anywhere in the image, no words, no letters, "
        f"no labels with writing, plain unlabeled containers, blank labels, "
        f"no signs, no captions, no watermark, no logos, {refuerzo}"
        f"contenido apto para todo público, familiar, profesional"
    )

    # PROVEEDOR PREFERIDO NUEVO (19-ago-2026): Cloudflare Workers AI.
    # Verificado en vivo con la cuenta del usuario: FLUX.1 Schnell (calidad
    # claramente superior a Pollinations, ~230 imágenes/día gratis) y SDXL
    # (acepta 16:9 nativo). Pollinations queda como respaldo: su API de
    # texto ya empezó a cobrar (402 verificado), señal de que la de
    # imágenes podría seguir el mismo camino.
    if _generar_imagen_cloudflare(prompt, destino_jpg, tamano):
        if not _prompt_tiene_persona(base):
            return True
        # Escenas con personas siguen pasando por la verificación Gemini
        # (fallan cerradas, igual que con Pollinations).
        try:
            if _imagen_es_segura_gemini(destino_jpg):
                return True
            log(AGENT, "Imagen de Cloudflare rechazada por la verificación de seguridad; "
                        "se intenta con Pollinations...")
        except Exception:
            # Sin cupo de Gemini para verificar: política conservadora,
            # probar con el siguiente proveedor.
            pass

    prompt_codificado = urllib.parse.quote(prompt)

    # Hasta 3 intentos con semillas distintas: cada imagen se verifica de
    # verdad con Gemini Vision (ver _imagen_es_segura_gemini) antes de
    # aceptarla. safe=true y model=flux se dejan puestos como ayuda
    # adicional, aunque la auditoría de agosto 2026 confirmó en vivo que
    # 'safe=true' NO bloquea de forma confiable el contenido NSFW por sí
    # solo -- por eso la verificación con Gemini es la que de verdad manda.
    # ANTI-429 (auditoría 18-ago-2026, defecto real "espacios sin imágenes"):
    # Pollinations se satura con ráfagas (50 beats seguidos = 429 en cadena
    # y el video quedaba lleno de degradados vacíos). Tres defensas nuevas:
    #   1) PAUSA entre peticiones (2s): reparte la carga, evita el rate-limit.
    #   2) Si un intento devuelve 429, espera creciente (5s, 10s) y reintenta.
    #   3) Doble modelo: si "flux" falla los 3 intentos, se prueba "turbo"
    #      (mismo servicio, cola distinta y más rápida; verificado en vivo).
    time.sleep(2)
    for intento in range(4):
        semilla = random.randint(1, 999999)
        modelo = "flux" if intento < 3 else "turbo"
        url = (f"https://image.pollinations.ai/prompt/{prompt_codificado}"
               f"?width={tamano[0]}&height={tamano[1]}&nologo=true&seed={semilla}"
               f"&safe=true&model={modelo}")
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 429:
                espera = 5 * (intento + 1)
                log(AGENT, f"Pollinations saturado (429); esperando {espera}s antes de reintentar...")
                time.sleep(espera)
                r = requests.get(url, timeout=60)
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
            # VERIFICACIÓN SELECTIVA (auditoría con video real, 18-ago-2026):
            # antes, si Gemini no estaba disponible (cuota agotada: pasa
            # siempre, un video tiene ~50 beats y la cuota son 16 llamadas),
            # se descartaban TODAS las imágenes IA "por precaución", y el
            # video quedaba lleno de fondos degradados vacíos (defecto real
            # visto por el usuario). El riesgo real de NSFW solo existe en
            # imágenes CON PERSONAS (incidente original: "human body
            # figure"). Ahora: si el prompt NO pide personas (comida,
            # plantas, objetos, paisajes), la imagen se acepta sin
            # verificación (riesgo ~cero); si pide personas y no hay
            # Gemini, se descarta como antes (la seguridad manda).
            if not _prompt_tiene_persona(base):
                log(AGENT, f"Imagen IA aceptada sin verificación Gemini (escena sin "
                            f"personas, riesgo mínimo): '{descripcion[:50]}'")
                return True
            log(AGENT, f"Aviso: no se pudo verificar la seguridad de la imagen IA ({e}); "
                        f"se descarta por precaución (la escena incluye personas).")
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
    # AMPLIADO (auditoría 21-ago-2026, defecto real: mujer con TRES brazos
    # al inicio del video de magnesio): además de contenido inapropiado,
    # ahora también se rechazan deformidades anatómicas típicas de IA.
    prompt = (
        "Responde ÚNICAMENTE con SI o NO, sin nada más. "
        "¿Esta imagen tiene ALGUNO de estos problemas? "
        "(1) desnudos, semi-desnudos, ropa interior/baño, piel descubierta "
        "de forma sexual o sugerente, o contenido no apto para un canal de "
        "salud familiar; "
        "(2) deformidades anatómicas de IA: más o menos de 2 brazos, más o "
        "menos de 2 manos, más o menos de 5 dedos por mano, extremidades "
        "fusionadas o retorcidas, caras deformes, dientes anormales; "
        "(3) texto ilegible o palabras inventadas/mal escritas en etiquetas "
        "o carteles. Sé estricto: cualquier duda razonable cuenta como SI."
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={gemini_key}"
    body = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}]}]}
    r = requests.post(url, json=body, timeout=30)
    r.raise_for_status()
    registrar_uso_gemini(1)
    texto = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
    return not texto.startswith("SI")


def _generar_fondo_local(texto, destino_png, tamano=(1280, 720)):
    """Último recurso: fondo local. CORRECCIÓN 28-ago-2026 (reclamo real
    del usuario: "momentos sin imágenes"): ya no es un degradado vacío
    anónimo sino el FONDO DE MARCA del canal (verde + logo real), idéntico
    al del editor. Delega en video_editor._fondo_respaldo_simple para que
    haya UN solo estilo de respaldo en todo el sistema."""
    try:
        from agents.video_editor import _fondo_respaldo_simple
        return _fondo_respaldo_simple(destino_png, tamano)
    except Exception:
        img = Image.new("RGB", tamano, (16, 74, 52))
        img.save(destino_png)
        return destino_png

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
            # agents/suscripcion_cta.py) YA NO usan una tarjeta a pantalla
            # completa: un experto en tráfico de YouTube señaló que el
            # aviso de suscripción no debe tapar toda la pantalla, sobre
            # todo en los primeros segundos. Ahora este beat usa una escena
            # real (búsqueda normal, como cualquier otro beat) y solo se le
            # superpone un banner pequeño en la parte de abajo, ya en
            # agents/video_editor.py (igual que el callout de cifras).

            # Mención cruzada a otro video del canal (tráfico orgánico
            # interno, ver agents/promocion_cruzada.py): se muestra una
            # tarjeta con el título del video recomendado en vez de buscar
            # stock (nada de la vida real representa "otro video del canal").
            # Intro de marca (ver agents/intro_marca.py): tarjeta con el
            # LOGO REAL del canal + promesa científica. Es la primerísima
            # escena del video (pedido del usuario, 19-ago-2026).
            if beat.get("es_intro_marca"):
                try:
                    from agents.intro_marca import generar_tarjeta_intro
                    ruta_intro = generar_tarjeta_intro(carpeta_salida)
                    visuales_cap.append({"tipo": "imagen", "ruta": ruta_intro,
                                          "keyword": "tarjeta de intro de marca del canal"})
                    log(AGENT, f"Cap {i+1} beat {j+1}/{len(beats)}: intro de marca -> tarjeta con logo real")
                    continue
                except Exception as e:
                    log(AGENT, f"Aviso: no se pudo generar la tarjeta de intro ({e}); "
                                "se busca un visual normal para este beat.")
                    beat = dict(beat)
                    beat["visual"] = "fresh green herbs and plants bright natural light"

            # Cita científica (ver agents/citas_cientificas.py): desde la
            # auditoría élite del 14-ago-2026, si el estudio citado es de
            # ACCESO ABIERTO se muestra la PORTADA REAL del estudio
            # (renderizada del PDF oficial de Europe PMC), no un stock
            # genérico de "persona leyendo papeles". El espectador ve el
            # título, autores y revista reales del estudio que respalda el
            # video. Si no hay PDF legal disponible, se usa el visual de
            # documento de siempre (nunca un PDF sin licencia).
            if beat.get("es_cita_cientifica") and beat.get("_pmid"):
                try:
                    from agents.portada_estudio import generar_visual_portada_estudio
                    cita = beat.get("cita_fuente") or {}
                    estudio_min = {"pmid": beat.get("_pmid"),
                                   "revista": cita.get("revista", ""),
                                   "anio": cita.get("anio", "")}
                    ruta_portada = generar_visual_portada_estudio(
                        estudio_min, carpeta_salida, tag=f"cap{i}_b{j}")
                    if ruta_portada:
                        visuales_cap.append({"tipo": "imagen", "ruta": ruta_portada,
                                              "keyword": "portada real del estudio científico citado"})
                        log(AGENT, f"Cap {i+1} beat {j+1}/{len(beats)}: cita científica -> "
                                    f"PORTADA REAL del estudio (PDF oficial)")
                        continue
                except Exception as e:
                    log(AGENT, f"Aviso: no se pudo renderizar la portada real del estudio ({e}); "
                                "se usa el visual de documento genérico.")

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

            # AGENTE 37 (Meta 2 del plan élite, 28-ago-2026): los beats
            # CLAVE (gancho + aperturas de capítulo) se intentan primero
            # como CLIP DE VIDEO IA en movimiento (LTX vía HF Spaces,
            # probado en vivo con la cuenta del usuario). Si no se puede
            # (sin token, cuota agotada, Space caído), cae a la búsqueda
            # normal de siempre sin bloquear nada.
            try:
                from agents.video_ia import generar_clip_ia, es_beat_clave
                if es_beat_clave(i, j, beat):
                    destino_ia_mp4 = os.path.join(
                        carpeta_salida, f"cap{i}_b{j}_{slugify(keyword)[:40]}_videoia.mp4")
                    ruta_clip = generar_clip_ia(
                        keyword, destino_ia_mp4, contexto=beat.get("texto", ""),
                        vertical=(orientacion == "portrait"))
                    if ruta_clip:
                        visuales_cap.append({"tipo": "video", "ruta": ruta_clip,
                                              "keyword": keyword})
                        log(AGENT, f"Cap {i+1} beat {j+1}/{len(beats)}: '{keyword}' -> "
                                    f"🎬 CLIP DE VIDEO IA (movimiento real)")
                        continue
            except Exception as e:
                log(AGENT, f"Aviso VideoClipIA ({e}); búsqueda normal para este beat.")

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
