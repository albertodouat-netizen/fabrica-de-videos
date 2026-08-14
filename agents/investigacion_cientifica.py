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


def buscar_estudios(tema: str, max_resultados: int = 6) -> list:
    """Busca estudios REALES en Europe PMC (gratis, sin key, base de datos
    médica reconocida). Descarta cualquier resultado sin resumen real
    disponible: sin resumen no hay forma de verificar nada, así que no sirve.
    """
    params = {
        "query": f"{tema} AND (SRC:MED)",
        "format": "json",
        "pageSize": max_resultados * 3,
        "resultType": "core",
    }
    try:
        r = requests.get(EUROPEPMC_URL, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log(AGENT, f"No se pudo consultar Europe PMC para '{tema}': {e}. "
                    f"Este video no incluirá cifras específicas (por seguridad).")
        return []

    estudios = []
    for item in data.get("resultList", {}).get("result", []):
        abstract = item.get("abstractText")
        pmid = item.get("pmid")
        if not abstract or not pmid:
            continue
        estudios.append({
            "pmid": pmid,
            "titulo": (item.get("title") or "").strip(),
            "autores": item.get("authorString", ""),
            "revista": (item.get("journalInfo", {}) or {}).get("journal", {}).get("title")
                       or item.get("journalTitle", "") or "",
            "anio": item.get("pubYear", ""),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "resumen": _limpiar_html(abstract),
        })
        if len(estudios) >= max_resultados:
            break
    log(AGENT, f"'{tema}': {len(estudios)} estudio(s) real(es) con resumen disponible.")
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
