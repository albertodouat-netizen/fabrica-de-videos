"""
AGENTE 2: GUIONISTA ("Scriptwriter")
----------------------------------------------------
Redacta el guion en español a partir de una "idea potencial" detectada por el
TrendScout. NO copia el video original: se le pide explícitamente inspirarse
en el tema/ángulo pero crear contenido propio (evita problemas de derechos de
autor y de la política de YouTube contra "contenido repetitivo/reciclado").

El guion se estructura en "beats" (fragmentos cortos de 1-2 frases, cada uno
con su propia palabra clave visual muy específica y filmable) siguiendo las
reglas de retención de audiencia del Agente Estratega Viral
(agents/viral_strategist.py): esto permite cortes visuales frecuentes,
dinámicos y bien sincronizados con lo que se está narrando, en vez de un
mismo clip aburrido sostenido por muchos segundos.

Proveedores 100% gratuitos soportados (elige uno en config.yaml -> llm_provider):
  - "gemini": Google Gemini API (capa gratuita)      https://aistudio.google.com/app/apikey
  - "groq":   Groq API con Llama 3 (capa gratuita)   https://console.groq.com/keys
  - "ollama": Modelo local en tu propia máquina, sin internet ni cuenta.
  - "none":   Generador de plantilla local (sin IA) — funciona siempre, sin cuentas.
"""
import json
import re
import time
import requests

from agents.utils import load_config, log, limpiar_texto_para_voz
from agents.viral_strategist import REGLAS_PARA_GUIONISTA, REGLAS_SEO_PARA_GUIONISTA

AGENT = "Guionista"

PROMPT_BASE = """Eres guionista experto en videos de YouTube de larga duración (10-18 min) \
sobre {nicho}, y también experto en retención de audiencia. Vas a escribir un guion \
ORIGINAL en español (nunca traducción literal) inspirado en el ÁNGULO de este video de \
referencia (no copies frases ni datos inventados que no puedas verificar, y no des \
consejos médicos peligrosos sin matizarlos):

Título de referencia: "{titulo_ref}"

{reglas_retencion}

{reglas_seo}

Instrucciones de formato:
0) Primero decide UNA "keyword_principal": la frase de búsqueda de 2-4 palabras
   que una persona real escribiría en YouTube para encontrar este video
   (ej: "dieta antiinflamatoria", "como bajar el colesterol"). Todo lo demás
   se construye alrededor de ella.
1) Un título propio en español que CONTENGA la keyword_principal dentro de las
   primeras 5 palabras, formato Title Case, máximo 60 caracteres, con un
   beneficio o cifra concreta (nunca clickbait que no cumples en el video).
2) Un "gancho" (hook) de los primeros segundos: 1-2 frases, texto narrable puro (ver reglas arriba).
3) El guion completo dividido en 5 a 9 capítulos. Cada capítulo tiene:
   - "nombre": título corto del capítulo, SIN marca de tiempo y sin símbolos.
   - "beats": lista de 8 a 14 fragmentos cortos, cada uno con:
       - "texto": 1-2 frases, SOLO texto narrable puro (ver regla 3 arriba, nada de
         asteriscos, guiones, numerales ni marcas de tiempo).
       - "visual": UNA palabra clave visual específica, real y filmable (nunca dibujos,
         diagramas ni animaciones).
   Pensado para que el conjunto dure entre {dur_min} y {dur_max} minutos hablado en total
   (aprox 140 palabras/min). Menciona la keyword_principal DE FORMA NATURAL y hablada
   dentro de los primeros 60 segundos del guion (primer o segundo beat del capítulo 1):
   YouTube analiza las palabras realmente narradas, no solo el título.
4) Una descripción para YouTube de 200-300 palabras en lenguaje NATURAL (nunca lista de
   palabras clave repetidas): la keyword_principal debe aparecer en la primera frase.
   Además, 10 a 15 tags: el primero debe ser la keyword_principal exacta, luego
   variaciones y términos relacionados (sin relleno ni tags que no describan el video).
5) Un disclaimer breve al final si el tema es de salud, finanzas u otro tema sensible.

Devuélvelo en JSON con esta forma EXACTA (sin texto fuera del JSON):
{{
  "keyword_principal": "...",
  "titulo": "...",
  "gancho": "...",
  "capitulos": [
    {{"nombre": "...", "beats": [{{"texto": "...", "visual": "..."}}, ...]}}
  ],
  "descripcion": "...",
  "tags": ["...","..."],
  "disclaimer": "..."

}}
"""


def _llamar_gemini(prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    ultimo_error = None
    for intento in range(3):
        try:
            r = requests.post(url, json=body, timeout=90)
            if r.status_code in (429, 500, 503) and intento < 2:
                espera = 5 * (intento + 1)
                log(AGENT, f"Gemini respondió {r.status_code} (sobrecarga temporal), "
                           f"reintentando en {espera}s...")
                time.sleep(espera)
                continue
            r.raise_for_status()
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except requests.exceptions.RequestException as e:
            ultimo_error = e
            if intento < 2:
                time.sleep(5 * (intento + 1))
                continue
            raise
    raise ultimo_error



def _llamar_groq(prompt, api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    body = {
        "model": "llama-3.1-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
    }
    r = requests.post(url, headers=headers, json=body, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _llamar_ollama(prompt, modelo):
    url = "http://localhost:11434/api/generate"
    body = {"model": modelo, "prompt": prompt, "stream": False}
    r = requests.post(url, json=body, timeout=120)
    r.raise_for_status()
    return r.json()["response"]


def _extraer_json(texto):
    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio == -1 or fin == -1:
        raise ValueError("La respuesta del modelo no contiene JSON válido")
    return json.loads(texto[inicio:fin + 1])


def _sanitizar_guion(guion: dict) -> dict:
    """Aplica la limpieza anti-símbolos a TODO el texto narrable, sin importar
    si vino de un LLM externo o de la plantilla local. Defensa en profundidad."""
    guion["gancho"] = limpiar_texto_para_voz(guion.get("gancho", ""))
    guion["titulo"] = (guion.get("titulo", "") or "").replace("*", "").replace("#", "").strip()
    for cap in guion.get("capitulos", []):
        cap["nombre"] = re.sub(r"^\s*\d{1,2}:\d{2}(:\d{2})?\s*[-|]\s*", "", cap.get("nombre", ""))
        cap["nombre"] = cap["nombre"].replace("*", "").replace("#", "").strip()
        for beat in cap.get("beats", []):
            beat["texto"] = limpiar_texto_para_voz(beat.get("texto", ""))
    return guion


def _plantilla_local(idea, cfg):
    """Generador SIN IA externa: 100% gratis y funciona sin ninguna cuenta.
    Calidad menor, pero deja el pipeline operativo end-to-end para pruebas
    o como respaldo si todas las APIs gratuitas fallan o se acaba la cuota.
    Ya usa la estructura de beats para mantener consistencia con el resto
    del sistema."""
    nicho = cfg["canal"]["nicho"]
    titulo = f"La verdad sobre {idea['titulo'].split('(')[0].strip()}"[:70]
    capitulos = [
        {
            "nombre": "Lo que nadie te dice",
            "beats": [
                {"texto": f"Esto sobre {nicho} está cambiando la vida de miles de personas.",
                 "visual": "persona sonriendo al aire libre en la mañana"},
                {"texto": "Y probablemente tú estás cometiendo el mismo error todos los días.",
                 "visual": "persona revisando el teléfono con cara de cansancio"},
                {"texto": "Te voy a mostrar exactamente qué hacer, paso a paso.",
                 "visual": "manos escribiendo en una libreta sobre una mesa de madera"},
            ],
        },
        {
            "nombre": "El problema real",
            "beats": [
                {"texto": "La mayoría de las personas atacan el síntoma, no la causa.",
                 "visual": "persona sosteniendo pastillas en la mano"},
                {"texto": "Por eso el problema siempre regresa.",
                 "visual": "reloj de pared en una cocina"},
                {"texto": "Aquí está lo que la evidencia realmente muestra.",
                 "visual": "doctor hablando con un paciente en consultorio"},
            ],
        },
        {
            "nombre": "Qué hacer hoy mismo",
            "beats": [
                {"texto": "Primero, cambia esta rutina en tus mañanas.",
                 "visual": "persona preparando un desayuno saludable en la cocina"},
                {"texto": "Segundo, elimina este hábito que te está afectando.",
                 "visual": "persona alejando un vaso de refresco de la mesa"},
                {"texto": "Tercero, agrega esta costumbre simple antes de dormir.",
                 "visual": "persona leyendo un libro en la cama con luz cálida"},
            ],
        },
        {
            "nombre": "Antes de irte",
            "beats": [
                {"texto": "Esto es información general y no reemplaza una consulta profesional.",
                 "visual": "persona caminando en un parque al atardecer"},
                {"texto": "Si te sirvió este video, suscríbete para más contenido como este.",
                 "visual": "persona sonriendo directo a la cámara"},
            ],
        },
    ]
    return {
        "keyword_principal": nicho,
        "titulo": titulo,
        "gancho": f"Esto sobre {nicho} podría estar afectándote sin que lo notes.",
        "capitulos": capitulos,
        "descripcion": (
            f"Descubre todo sobre {nicho}: en este video te explicamos {idea['titulo']} "
            f"y cómo aplicarlo hoy mismo, con cambios simples y respaldados por la evidencia "
            f"disponible. Si te interesa {nicho}, este contenido es para ti."
        ),
        "tags": [nicho, "consejos", "hábitos saludables", "bienestar", "rutina diaria"],
        "disclaimer": "Este video es solo informativo y no sustituye una consulta médica o profesional.",
    }


def generar_guion(idea: dict) -> dict:
    cfg = load_config()
    provider_preferido = cfg["apis"].get("llm_provider", "none")
    nicho = cfg["canal"]["nicho"]
    dur_min = cfg["estrategia"]["duracion_minima_min"]
    dur_max = cfg["estrategia"]["duracion_objetivo_min"]

    prompt = PROMPT_BASE.format(
        nicho=nicho, titulo_ref=idea["titulo"], dur_min=dur_min, dur_max=dur_max,
        reglas_retencion=REGLAS_PARA_GUIONISTA, reglas_seo=REGLAS_SEO_PARA_GUIONISTA,
    )

    # Cascada de respaldo: si el proveedor preferido falla (cuota agotada,
    # sobrecarga temporal, etc.), se intenta automáticamente con el
    # siguiente proveedor gratuito disponible antes de caer a la plantilla
    # local. Esto es justamente lo que evita que un límite temporal de un
    # solo proveedor baje la calidad de todo el video.
    orden_proveedores = [provider_preferido] + [p for p in ("gemini", "groq", "ollama") if p != provider_preferido]

    guion = None
    for provider in orden_proveedores:
        try:
            if provider == "gemini":
                key = cfg["apis"].get("gemini_api_key", "")
                if not key or "OBTENER_GRATIS" in key:
                    continue
                log(AGENT, "Generando guion con Gemini (gratuito), con reglas de retención...")
                texto = _llamar_gemini(prompt, key)
                guion = _extraer_json(texto)

            elif provider == "groq":
                key = cfg["apis"].get("groq_api_key", "")
                if not key or "OBTENER_GRATIS" in key:
                    continue
                log(AGENT, "Generando guion con Groq/Llama 3 (gratuito), con reglas de retención...")
                texto = _llamar_groq(prompt, key)
                guion = _extraer_json(texto)

            elif provider == "ollama":
                modelo = cfg["apis"].get("ollama_model", "llama3.1")
                log(AGENT, f"Generando guion con Ollama local ({modelo})...")
                texto = _llamar_ollama(prompt, modelo)
                guion = _extraer_json(texto)

            if guion is not None:
                break

        except Exception as e:
            log(AGENT, f"Aviso: fallo con proveedor '{provider}' ({e}). "
                        f"Probando el siguiente proveedor gratuito disponible...")
            continue

    if guion is None:

        log(AGENT, "Usando generador de plantilla local (sin IA externa, 100% gratis).")
        guion = _plantilla_local(idea, cfg)

    return _sanitizar_guion(guion)


if __name__ == "__main__":
    from agents.trend_scout import buscar_ideas_potenciales
    idea = buscar_ideas_potenciales()[0]
    guion = generar_guion(idea)
    print(json.dumps(guion, ensure_ascii=False, indent=2))
