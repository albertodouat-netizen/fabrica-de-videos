"""
AGENTE 17: INVESTIGADOR CIENTÍFICO ("InvestigadorCientifico")
----------------------------------------------------
Responde a un requisito estricto: toda estadística o afirmación respaldada
"por estudios" que aparezca en el guion debe corresponder a un estudio
científico REAL, verificable, con enlace que funcione. Nunca se inventa
nada ("fantasear" queda explícitamente prohibido).

Cómo se garantiza esto (en ese orden, nunca al revés):
  1) ANTES de escribir el guion, se buscan estudios reales en Europe PMC
     (gratis, sin API key, misma base de datos médica que PubMed) sobre el
     tema exacto del video, con su resumen (abstract) REAL.
  2) Esos resúmenes reales (no la "memoria" del modelo, que es donde
     ocurren las alucinaciones) se le entregan al Guionista como las ÚNICAS
     fuentes de las que puede tomar cifras concretas.
  3) DESPUÉS de escribir el guion, se vuelve a verificar cada frase con una
     cifra puntual (%, "1 de cada X", etc.) contra esos mismos resúmenes
     reales. Si no se puede confirmar, se SUAVIZA la frase (se quita la
     cifra) en vez de inventar un reemplazo o dejarla sin respaldo.
  4) Antes de publicar, se comprueba que cada enlace de referencia
     realmente cargue (no un link roto).

Si en algún punto no hay estudios reales disponibles para el tema, el
guion simplemente no incluye cifras específicas (mejor generalizar que
inventar).
"""
import re
import time

import requests

from agents.utils import load_config, log, limpiar_texto_para_voz

AGENT = "InvestigadorCientifico"
EUROPEPMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

# Patrón para detectar afirmaciones con cifra puntual que DEBEN estar
# respaldadas por una fuente real (porcentajes, proporciones, "X veces más").
_PATRON_CIFRA = re.compile(
    r"\d+(\.\d+)?\s*%|\d+\s*de\s*cada\s*\d+|\d+\s*veces\s*m[aá]s"
)


def _limpiar_html(texto: str) -> str:
    return re.sub(r"<[^>]+>", "", texto or "").strip()


# ---------------------------------------------------------------------------
# CORRECCIÓN CRÍTICA (auditoría con evidencia real, agosto 2026):
# antes se buscaba en Europe PMC con el TÍTULO EN ESPAÑOL del video
# ("Alimentos Para La Visión...") y la base de datos, que está en INGLÉS,
# devolvía estudios de revistas hispanas SIN NINGUNA RELACIÓN con el tema
# (comprobado en vivo: para el video de visión devolvió un estudio de
# "salud planetaria" y otro de enfermería sobre cuidadores). Por eso los
# videos publicados NO llevaban referencias reales en la descripción.
# Solución en 3 pasos, todo gratis y sin API key:
#   1) Traducir el tema a inglés (endpoint gratuito de Google Translate).
#   2) Buscar con palabras clave en inglés + HAS_ABSTRACT:y.
#   3) FILTRAR POR RELEVANCIA: solo se aceptan estudios cuyo título/resumen
#      realmente contengan las palabras clave del tema. Si un estudio no
#      tiene relación clara, se descarta (mejor 0 referencias que citar en
#      pantalla una revista que no habla del tema: eso destruiría la
#      credibilidad que se quiere construir).
# ---------------------------------------------------------------------------

_STOPWORDS_EN = {
    "the", "a", "an", "and", "or", "with", "for", "your", "you", "these",
    "this", "that", "those", "of", "to", "in", "on", "how", "why", "what",
    "is", "are", "it", "its", "from", "at", "by", "my", "our", "their",
    "than", "more", "most", "best", "improve", "improves", "improving",
    "better", "boost", "boosts", "day", "days", "step", "steps", "tips",
    "guide", "naturally", "natural", "health", "healthy", "will", "can",
    "into", "about", "without", "just", "only", "every", "daily",
}


def _traducir_a_ingles(texto: str) -> str:
    """Traducción gratuita ES->EN (mismo endpoint público que usa el widget
    de Google Translate, sin API key). Si falla, devuelve el texto original
    para no bloquear nunca la generación del video."""
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "es", "tl": "en", "dt": "t", "q": texto},
            timeout=12,
        )
        r.raise_for_status()
        data = r.json()
        traduccion = " ".join(seg[0] for seg in data[0] if seg and seg[0]).strip()
        return traduccion or texto
    except Exception as e:
        log(AGENT, f"Aviso: no se pudo traducir el tema a inglés ({e}); "
                    f"se busca con el texto original.")
        return texto


def _palabras_clave_en(texto_en: str, max_palabras: int = 5) -> list:
    """Extrae las palabras con contenido real (sin stopwords ni números)
    del tema ya traducido al inglés."""
    palabras = re.findall(r"[a-zA-Z]{4,}", texto_en.lower())
    vistas, resultado = set(), []
    for p in palabras:
        if p in _STOPWORDS_EN or p in vistas:
            continue
        vistas.add(p)
        resultado.append(p)
        if len(resultado) >= max_palabras:
            break
    return resultado


# Estudios que NO sirven para un canal de salud humana aunque compartan
# palabras clave con el tema (comprobado en vivo: buscar "foods vision"
# devolvía un paper de inteligencia artificial por "computer vision", y
# "oyster mushroom" devolvía papers de cultivo agrícola y alimentación
# animal). Si alguno de estos términos aparece en el TÍTULO, se descarta.
_LISTA_NEGRA_TITULO = [
    "artificial intelligence", "machine learning", "deep learning",
    "computer vision", "neural network", "food industry", "packaging",
    "supply chain", "cultivation", "veterinary", "poultry", "livestock",
    "cattle", "broiler", "feed additive", "mushroom-based feed",
    "in vitro", "cell line", "mice", "rats", "murine", "zebrafish",
    # Tecnología/industria de alimentos (no es salud humana):
    "feature extraction", "rt-detr", "detection model", "coating",
    "by-product", "by-products", "agri-food", "cold plasma", "uvc",
    "shelf life", "shelf-life", "contamination", "postharvest",
    "post-harvest", "biosensor", "spectroscopy", "food safety",
]

# Señales de que el estudio SÍ es de salud/nutrición humana (al menos una
# debe aparecer en el título o el resumen).
_SENALES_SALUD_HUMANA = [
    "patient", "human", "adult", "participant", "clinical", "randomized",
    "trial", "diet", "dietary", "nutrition", "nutrient", "supplement",
    "intake", "consumption", "cohort", "meta-analysis", "systematic review",
    "health outcome", "symptom", "treatment", "therapy", "prevention",
]


def _estudio_es_relevante(keywords: list, titulo: str, resumen: str) -> bool:
    """Un estudio solo se acepta si:
      a) su título/resumen contiene al menos 2 de las palabras clave del
         tema (o todas, si el tema tiene menos de 2),
      b) su título no cae en la lista negra (IA, agricultura, animales...),
      c) tiene al menos una señal de ser un estudio de salud humana.
    Se toleran plurales simples (vision/visions) comparando también la raíz."""
    titulo_l = (titulo or "").lower()
    texto = f"{titulo_l} {(resumen or '').lower()}"

    for prohibido in _LISTA_NEGRA_TITULO:
        if prohibido in titulo_l:
            return False

    if not any(senal in texto for senal in _SENALES_SALUD_HUMANA):
        return False

    if not keywords:
        return True
    aciertos = 0
    aciertos_en_titulo = 0
    for k in keywords:
        raiz = k[:-1] if k.endswith("s") else k
        if raiz in texto:
            aciertos += 1
        if raiz in titulo_l:
            aciertos_en_titulo += 1
    necesarios = min(2, len(keywords))
    # Al menos una palabra clave del tema debe estar en el TÍTULO del
    # estudio (comprobado en vivo: sin esta condición se colaban papers de
    # otros campos cuyo resumen mencionaba las palabras de pasada).
    return aciertos >= necesarios and aciertos_en_titulo >= 1


def _consultar_europepmc(query: str, page_size: int) -> list:
    params = {
        "query": query,
        "format": "json",
        "pageSize": page_size,
        "resultType": "core",
    }
    r = requests.get(EUROPEPMC_URL, params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("resultList", {}).get("result", [])


def buscar_estudios(tema: str, max_resultados: int = 6) -> list:
    """Busca estudios REALES en Europe PMC (gratis, sin key, base de datos
    médica reconocida), traduciendo primero el tema a inglés (el idioma real
    de la base) y quedándose SOLO con estudios relevantes al tema. Descarta
    cualquier resultado sin resumen real disponible: sin resumen no hay
    forma de verificar nada, así que no sirve.
    """
    tema_en = _traducir_a_ingles(tema)
    keywords = _palabras_clave_en(tema_en)

    intentos = []
    if keywords:
        intentos.append(" AND ".join(keywords) + " AND (SRC:MED) AND HAS_ABSTRACT:y")
        if len(keywords) > 3:
            # Segundo intento menos estricto, con las 3 palabras más importantes
            intentos.append(" AND ".join(keywords[:3]) + " AND (SRC:MED) AND HAS_ABSTRACT:y")
    # Último recurso: comportamiento anterior (tema tal cual), por si la
    # traducción falló por completo. El filtro de relevancia sigue aplicando.
    intentos.append(f"{tema} AND (SRC:MED)")

    items = []
    for query in intentos:
        try:
            items = _consultar_europepmc(query, max_resultados * 4)
        except Exception as e:
            log(AGENT, f"No se pudo consultar Europe PMC ('{query[:60]}...'): {e}.")
            items = []
        if len(items) >= 2:
            break

    estudios = []
    descartados = 0
    for item in items:
        abstract = item.get("abstractText")
        pmid = item.get("pmid")
        if not abstract or not pmid:
            continue
        titulo = (item.get("title") or "").strip()
        resumen = _limpiar_html(abstract)
        if not _estudio_es_relevante(keywords, titulo, resumen):
            descartados += 1
            continue
        estudios.append({
            "pmid": pmid,
            "titulo": titulo,
            "autores": item.get("authorString", ""),
            "revista": (item.get("journalInfo", {}) or {}).get("journal", {}).get("title")
                       or item.get("journalTitle", "") or "",
            "anio": item.get("pubYear", ""),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "resumen": resumen,
        })
        if len(estudios) >= max_resultados * 2:
            break

    # Capa final de precisión: UNA sola llamada a Gemini que lee títulos y
    # resúmenes y responde cuáles estudios hablan DE VERDAD del tema del
    # video (comprobado en vivo: el filtro por palabras clave dejaba pasar
    # p.ej. un paper de huella de carbono para un video de visión, porque
    # las palabras coincidían de casualidad). Si Gemini no está disponible,
    # se usa el resultado del filtro por palabras tal cual (nunca bloquea).
    estudios = _filtrar_relevancia_con_gemini(tema, estudios)[:max_resultados]

    # Segundo intento inteligente: si el revisor rechazó todo (o no se
    # encontró nada), se le pide al MISMO LLM gratuito una consulta de
    # búsqueda médica en inglés bien formulada (p.ej. para "Alimentos para
    # la visión" propone términos como "eye health" o "macular
    # degeneration" que la traducción literal no contiene) y se busca de
    # nuevo. El resultado pasa por el mismo revisor de relevancia.
    if not estudios:
        estudios = _reintento_con_query_de_llm(tema, max_resultados)

    log(AGENT, f"'{tema}' (buscado en inglés como '{tema_en[:60]}'): "
                f"{len(estudios)} estudio(s) relevante(s) con resumen disponible"
                + (f", {descartados} descartado(s) por no tener relación clara con el tema." if descartados else "."))
    return estudios


def _reintento_con_query_de_llm(tema: str, max_resultados: int) -> list:
    """Pide al LLM una consulta PubMed/Europe PMC óptima en inglés para el
    tema y busca de nuevo. La consulta solo define QUÉ se busca; los
    estudios devueltos siguen siendo 100% reales (vienen de Europe PMC) y
    siguen pasando por el revisor de relevancia."""
    prompt = (
        f"Tema de un video de salud en español: \"{tema}\".\n\n"
        f"Escribe UNA consulta de búsqueda para PubMed en inglés que encuentre "
        f"estudios en humanos sobre este tema. Usa 2-4 términos médicos "
        f"conectados con AND (puedes agrupar sinónimos con OR entre "
        f"paréntesis). Ejemplo de formato: (spinach OR lutein) AND \"eye health\". "
        f"Responde ÚNICAMENTE con la consulta, sin explicaciones."
    )
    try:
        cfg = load_config()
        respuesta = None
        groq_key = cfg["apis"].get("groq_api_key", "")
        gemini_key = cfg["apis"].get("gemini_api_key", "")
        if groq_key and "OBTENER_GRATIS" not in groq_key:
            try:
                respuesta = _relevancia_con_groq(prompt, groq_key)
            except Exception:
                respuesta = None
        if respuesta is None and gemini_key and "OBTENER_GRATIS" not in gemini_key:
            try:
                from agents.presupuesto_ia import gemini_disponible
                if gemini_disponible(1):
                    respuesta = _relevancia_con_gemini(prompt, gemini_key)
            except Exception:
                respuesta = None
        if not respuesta:
            return []
        query_llm = respuesta.strip().strip('`').splitlines()[0].strip()
        if not query_llm or len(query_llm) > 300:
            return []
        log(AGENT, f"Reintentando búsqueda científica con consulta experta: {query_llm}")
        items = _consultar_europepmc(f"({query_llm}) AND (SRC:MED) AND HAS_ABSTRACT:y",
                                      max_resultados * 3)
        estudios = []
        for item in items:
            abstract = item.get("abstractText")
            pmid = item.get("pmid")
            if not abstract or not pmid:
                continue
            titulo = (item.get("title") or "").strip()
            titulo_l = titulo.lower()
            if any(p in titulo_l for p in _LISTA_NEGRA_TITULO):
                continue
            estudios.append({
                "pmid": pmid,
                "titulo": titulo,
                "autores": item.get("authorString", ""),
                "revista": (item.get("journalInfo", {}) or {}).get("journal", {}).get("title")
                           or item.get("journalTitle", "") or "",
                "anio": item.get("pubYear", ""),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "resumen": _limpiar_html(abstract),
            })
            if len(estudios) >= max_resultados * 2:
                break
        return _filtrar_relevancia_con_gemini(tema, estudios)[:max_resultados]
    except Exception as e:
        log(AGENT, f"Aviso: el reintento con consulta experta no funcionó ({e}); "
                    f"este video irá sin citas específicas.")
        return []


def _prompt_relevancia(tema: str, estudios: list) -> str:
    lineas = []
    for i, e in enumerate(estudios, 1):
        lineas.append(f"[{i}] \"{e['titulo']}\" — {e['resumen'][:220]}")
    return (
        f"Tema de un video de salud en español: \"{tema}\".\n\n"
        f"Estudios científicos candidatos (título y comienzo del resumen):\n\n"
        + "\n\n".join(lineas)
        + "\n\n¿Cuáles de estos estudios tratan DIRECTAMENTE sobre el tema del "
        f"video (mismo alimento/nutriente/práctica Y mismo beneficio de salud "
        f"en humanos)? Sé estricto: si un estudio es de otro campo (industria, "
        f"agricultura, animales, tecnología) o solo coincide de pasada, NO lo "
        f"incluyas. Responde ÚNICAMENTE con los números separados por comas "
        f"(ej: 1,3) o con NINGUNO si ningún estudio es directamente relevante."
    )


def _interpretar_respuesta_relevancia(texto: str, estudios: list):
    """Devuelve la lista elegida, [] si NINGUNO, o None si no se entendió."""
    texto = (texto or "").strip().upper()
    if "NINGUNO" in texto:
        return []
    indices = [int(n) - 1 for n in re.findall(r"\d+", texto)]
    elegidos = [estudios[i] for i in indices if 0 <= i < len(estudios)]
    return elegidos if elegidos else None


def _relevancia_con_gemini(prompt: str, gemini_key: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
    r = None
    for espera in (0, 5, 10):
        if espera:
            log(AGENT, f"Gemini respondió 429 (sobrecarga temporal) refinando relevancia; "
                        f"reintentando en {espera}s...")
            time.sleep(espera)
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        if r.status_code != 429:
            break
    r.raise_for_status()
    try:
        from agents.presupuesto_ia import registrar_uso_gemini
        registrar_uso_gemini(1)
    except Exception:
        pass
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _relevancia_con_groq(prompt: str, groq_key: str) -> str:
    r = None
    for espera in (0, 5, 10):
        if espera:
            log(AGENT, f"Groq respondió 429 (sobrecarga temporal) refinando relevancia; "
                        f"reintentando en {espera}s...")
            time.sleep(espera)
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            },
            timeout=30,
        )
        if r.status_code != 429:
            break
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _filtrar_relevancia_con_gemini(tema: str, estudios: list) -> list:
    """Selección final de relevancia temática con UNA llamada a un LLM
    gratuito (Gemini primero; si falla o no hay cuota, Groq de respaldo).
    Es tarea de LECTURA/COMPARACIÓN (no de generación), así que no puede
    'inventar' estudios: solo puede elegir entre los reales encontrados.
    Se revisa INCLUSO si quedó un solo candidato (comprobado en vivo: para
    el video de visión, el único candidato que pasó el filtro de palabras
    era un paper de huella de carbono sin relación con la salud ocular)."""
    if not estudios:
        return estudios

    cfg = load_config()
    prompt = _prompt_relevancia(tema, estudios)

    # 1) Gemini (respetando el presupuesto diario real de 20 llamadas/día).
    gemini_key = cfg["apis"].get("gemini_api_key", "")
    if gemini_key and "OBTENER_GRATIS" not in gemini_key:
        puede = True
        try:
            from agents.presupuesto_ia import gemini_disponible
            puede = gemini_disponible(1)
        except Exception:
            pass
        if puede:
            try:
                resultado = _interpretar_respuesta_relevancia(
                    _relevancia_con_gemini(prompt, gemini_key), estudios)
                if resultado is not None:
                    if not resultado:
                        log(AGENT, "El revisor IA confirmó que ningún candidato trata directamente "
                                    "el tema: este video irá sin cifras/citas específicas "
                                    "(mejor que citar algo sin relación).")
                    else:
                        log(AGENT, f"El revisor IA (Gemini) confirmó {len(resultado)} de "
                                    f"{len(estudios)} candidato(s) como directamente relevantes.")
                    return resultado
            except Exception as e:
                log(AGENT, f"Aviso: Gemini no pudo refinar la relevancia ({e}); se prueba con Groq.")

    # 2) Groq de respaldo (misma capa gratuita que usa el Guionista).
    groq_key = cfg["apis"].get("groq_api_key", "")
    if groq_key and "OBTENER_GRATIS" not in groq_key:
        try:
            resultado = _interpretar_respuesta_relevancia(
                _relevancia_con_groq(prompt, groq_key), estudios)
            if resultado is not None:
                if not resultado:
                    log(AGENT, "El revisor IA confirmó que ningún candidato trata directamente "
                                "el tema: este video irá sin cifras/citas específicas "
                                "(mejor que citar algo sin relación).")
                else:
                    log(AGENT, f"El revisor IA (Groq) confirmó {len(resultado)} de "
                                f"{len(estudios)} candidato(s) como directamente relevantes.")
                return resultado
        except Exception as e:
            log(AGENT, f"Aviso: Groq tampoco pudo refinar la relevancia ({e}).")

    log(AGENT, "Sin revisor IA disponible: se usa solo el filtro por palabras clave "
                "(los estudios igual fueron verificados como reales).")
    return estudios


def construir_bloque_fuentes_para_prompt(estudios: list) -> str:
    """Texto de 'fuentes verificadas' que se inserta en el prompt del
    Guionista, con resúmenes REALES (recortados) para citar con precisión."""
    if not estudios:
        return (
            "No se encontraron estudios científicos verificables para este tema. "
            "REGLA OBLIGATORIA: NO inventes cifras, porcentajes, ni nombres de "
            "estudios. Habla en términos generales y cualitativos (\"la evidencia "
            "sugiere\", \"se ha observado en investigaciones\") SIN números "
            "específicos ni estudios inventados."
        )
    bloques = [
        "FUENTES CIENTÍFICAS REALES Y VERIFICADAS (son las ÚNICAS que puedes usar "
        "para citar cifras o hallazgos concretos; si citas algo, debe coincidir "
        "con lo que dice el resumen real de abajo, nunca inventes un dato que no "
        "esté aquí):"
    ]
    for i, e in enumerate(estudios, 1):
        resumen_corto = e["resumen"][:600]
        bloques.append(
            f"[Fuente {i}] \"{e['titulo']}\" ({e['revista']}, {e['anio']}).\n"
            f"Resumen real: {resumen_corto}"
        )
    return "\n\n".join(bloques)


def _preguntar_gemini_si_respalda(afirmacion: str, estudios: list, gemini_key: str) -> dict:
    """Tarea de VERIFICACIÓN (comparar texto contra texto real), no de
    generación: esto es mucho más seguro que pedirle a un LLM que 'recuerde'
    un estudio de su entrenamiento, que es justo donde ocurren las
    alucinaciones/estudios inventados."""
    contexto = construir_bloque_fuentes_para_prompt(estudios)
    prompt = (
        f"Tienes estos resúmenes REALES de estudios científicos:\n\n{contexto}\n\n"
        f"Afirmación a verificar (viene de un guion de video, en español): "
        f"\"{afirmacion}\"\n\n"
        f"¿Alguno de los resúmenes de arriba respalda ESPECÍFICAMENTE esta "
        f"afirmación (los mismos datos o cifras, no solo el tema en general)? "
        f"Responde ÚNICAMENTE con \"SI:<número de fuente>\" o \"NO\", sin nada "
        f"más. Sé estricto: si tienes cualquier duda, responde NO."
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(url, json=body, timeout=30)
        r.raise_for_status()
        from agents.presupuesto_ia import registrar_uso_gemini
        registrar_uso_gemini(1)
        texto = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if texto.upper().startswith("SI"):
            m = re.search(r"(\d+)", texto)
            if m:
                idx = int(m.group(1)) - 1
                if 0 <= idx < len(estudios):
                    return {"respaldada": True, "indice_fuente": idx}
        return {"respaldada": False, "indice_fuente": None}
    except Exception as e:
        log(AGENT, f"Aviso verificando afirmación ({e}); por seguridad se descarta la cifra.")
        return {"respaldada": False, "indice_fuente": None}


def _pmid_existe_de_verdad(pmid: str, titulo_esperado: str = "") -> bool:
    """Verificación REAL de que un PMID existe, usando la API oficial de
    NCBI E-utilities (gratis, sin key, pensada exactamente para esto).

    Por qué esto reemplaza a un simple 'requests.get' a la página de
    PubMed (bug real encontrado en la auditoría de agosto 2026): PubMed
    devuelve el MISMO HTML de "verificando que no eres un robot" (status
    203, sin contenido real) tanto para un PMID real como para uno
    completamente inventado -- confirmado probando en vivo con un PMID real
    y uno inventado, ambos "pasaban" el chequeo anterior. Con NCBI
    E-utilities (esummary), un PMID inventado devuelve un error explícito
    o no aparece en los resultados, así que sí distingue de verdad."""
    try:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        r = requests.get(url, params={"db": "pubmed", "id": pmid, "retmode": "json"}, timeout=15)
        r.raise_for_status()
        resultado = r.json().get("result", {})
        if pmid not in resultado.get("uids", []):
            return False
        info = resultado.get(pmid, {})
        if "error" in info or not info.get("title"):
            return False
        return True
    except Exception as e:
        log(AGENT, f"Aviso verificando PMID {pmid} contra NCBI ({e}); se descarta por seguridad.")
        return False


def pmid_es_real(pmid: str, titulo_esperado: str = "") -> bool:
    """Versión pública de _pmid_existe_de_verdad, para que otros agentes
    (ej. agents/citas_cientificas.py) puedan reutilizar la misma
    verificación real contra NCBI sin duplicar código."""
    return _pmid_existe_de_verdad(pmid, titulo_esperado)


def _url_funciona(url: str) -> bool:
    """Respaldo genérico (para enlaces que no sean de PubMed): comprueba
    que la URL cargue con un código de respuesta válido."""
    try:
        r = requests.get(url, timeout=12, allow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0"})
        return r.status_code < 400
    except Exception:
        return False


def _reescribir_sin_cifra(texto: str, gemini_key: str) -> str:
    """Cuando una cifra no se puede verificar, es más seguro pedirle a Gemini
    que reescriba la MISMA frase sin esa cifra específica (tarea de edición,
    no de invención de datos) que hacer un reemplazo de texto a ciegas, que
    puede dejar frases gramaticalmente raras."""
    prompt = (
        f"Reescribe esta frase en español, manteniendo la misma idea general, pero "
        f"SIN mencionar ninguna cifra, porcentaje o número específico (porque no se "
        f"pudo verificar con una fuente real). No inventes otro dato para reemplazarlo, "
        f"solo generaliza. Debe sonar natural al leerse en voz alta, texto plano sin "
        f"símbolos ni comillas. Responde ÚNICAMENTE con la frase reescrita, nada más.\n\n"
        f"Frase original: \"{texto}\""
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(url, json=body, timeout=30)
        r.raise_for_status()
        from agents.presupuesto_ia import registrar_uso_gemini
        registrar_uso_gemini(1)
        reescrita = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"')
        # Verificación de seguridad: si por algún motivo la reescritura todavía
        # trae una cifra, mejor usamos un respaldo simple (nunca deberíamos
        # llegar aquí, pero es mejor prevenir que dejar pasar un número sin
        # verificar).
        if _PATRON_CIFRA.search(reescrita):
            return limpiar_texto_para_voz(_PATRON_CIFRA.sub("una parte importante", texto))
        return limpiar_texto_para_voz(reescrita)
    except Exception as e:
        log(AGENT, f"Aviso reescribiendo frase sin cifra ({e}); se usa un respaldo simple.")
        return limpiar_texto_para_voz(_PATRON_CIFRA.sub("una parte importante", texto))


def verificar_y_filtrar_guion(guion: dict, estudios: list) -> dict:
    """Segunda pasada de seguridad OBLIGATORIA: revisa cada beat con una
    cifra puntual y la confirma contra los resúmenes reales. Si no se puede
    confirmar, SUAVIZA la frase (nunca inventa un reemplazo). Al final,
    solo deja como 'referencias' del video las fuentes que sí se usaron Y
    cuyo enlace realmente carga."""
    cfg = load_config()
    gemini_key = cfg["apis"].get("gemini_api_key", "")
    if not gemini_key or "OBTENER_GRATIS" in gemini_key:
        log(AGENT, "Sin Gemini configurado: no se puede verificar cifras contra las "
                    "fuentes reales. No se incluirán referencias en este video (para "
                    "no arriesgar citar algo sin confirmar).")
        guion["referencias"] = []
        return guion

    if not estudios:
        guion["referencias"] = []
        return guion

    referencias_usadas = set()
    for cap in guion.get("capitulos", []):
        for beat in cap.get("beats", []):
            texto = beat.get("texto", "")
            match = _PATRON_CIFRA.search(texto)
            if not match:
                continue
            resultado = _preguntar_gemini_si_respalda(texto, estudios, gemini_key)
            if resultado["respaldada"]:
                referencias_usadas.add(resultado["indice_fuente"])
                # El usuario pidió que las cifras se muestren en pantalla de
                # forma fácil de entender, no solo mencionadas en el audio.
                # Se marca aquí (después de confirmar que es una cifra REAL
                # y verificada) para que agents/video_editor.py dibuje un
                # recuadro con la cifra encima del video en ese momento
                # exacto (ver agents/callout_cifras.py).
                beat["cifra_verificada"] = match.group(0).strip()
                # Hallazgo real (auditoría agosto 2026, SEO/credibilidad):
                # el usuario pidió que se note de dónde sale la información,
                # no solo la cifra suelta. Se adjunta aquí la cita real
                # (revista + año) para que el callout en pantalla y el
                # buscador de video (agents/visuals.py) puedan mostrar,
                # respectivamente, "Revista, Año" en vez de un texto
                # genérico, y una escena real de un documento/estudio en
                # vez de una escena sin relación con la fuente.
                estudio_citado = estudios[resultado["indice_fuente"]]
                autores = (estudio_citado.get("autores") or "").strip()
                beat["cita_fuente"] = {
                    "revista": estudio_citado.get("revista", "").strip(),
                    "anio": str(estudio_citado.get("anio", "")).strip(),
                    "autor_corto": autores.split(",")[0] if autores else "",
                    "url": estudio_citado.get("url", ""),
                }
            else:
                texto_suave = _reescribir_sin_cifra(texto, gemini_key)
                log(AGENT, f"Cifra no verificable descartada: \"{texto}\" -> \"{texto_suave}\"")
                beat["texto"] = texto_suave
            time.sleep(1.5)  # margen para no exceder límites gratuitos de Gemini

    referencias_finales = []
    for idx in sorted(referencias_usadas):
        estudio = estudios[idx]
        # Verificación real contra NCBI (ver _pmid_existe_de_verdad): esto
        # SÍ distingue un PMID real de uno inventado, a diferencia del
        # chequeo anterior que probaba solo cargar la página de PubMed.
        if _pmid_existe_de_verdad(estudio["pmid"], estudio.get("titulo", "")):
            referencias_finales.append(estudio)
        else:
            log(AGENT, f"Referencia descartada: el PMID {estudio['pmid']} no se pudo "
                        f"confirmar como real contra NCBI ({estudio['url']}).")

    guion["referencias"] = referencias_finales
    log(AGENT, f"{len(referencias_finales)} referencia(s) científica(s) verificada(s), "
                f"con enlace funcionando, para este video.")
    return guion


if __name__ == "__main__":
    estudios = buscar_estudios("cúrcuma inflamación")
    for e in estudios:
        print(e["titulo"], "-", e["revista"], e["anio"], "-", e["url"])
