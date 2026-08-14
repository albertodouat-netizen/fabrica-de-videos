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
import random
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

{fuentes_cientificas}

REGLA DE HONESTIDAD CIENTÍFICA (OBLIGATORIA, sin excepción): si mencionas una cifra, \
porcentaje o "estudios muestran que...", DEBE coincidir con una de las fuentes reales \
de arriba (si las hay). Está PROHIBIDO inventar estudios, porcentajes o estadísticas \
que no aparezcan en esas fuentes. Si no tienes una fuente real para respaldar algo, \
dilo en términos generales sin inventar un número.

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
         diagramas ni animaciones), escrita EN INGLÉS (aunque todo lo demás del guion
         esté en español). Motivo: esta palabra clave se usa para buscar en bancos de
         video/foto gratuitos (Pexels, Pixabay) cuyo catálogo y etiquetas están
         mayoritariamente en inglés, así que una keyword en inglés encuentra escenas
         MUCHO más precisas y relacionadas que la misma frase en español. Ejemplos
         buenos: "hands chopping fresh garlic on wooden cutting board", "person
         running at sunrise in the park", "woman drinking a glass of water in the
         kitchen". El espectador NUNCA ve este texto, así que el idioma no importa
         para él, solo para la búsqueda.
         IMPORTANTE: el "visual" no debe pensarse solo para esa frase aislada, sino
         que debe encajar con el TEMA GENERAL del video (la keyword_principal). Por
         ejemplo, en un video sobre salud intestinal, si un beat menciona "estrés",
         mejor usa "person meditating calmly at home" que "stressed businessman in
         office" (la oficina no encaja con un canal de salud natural). Todas las
         escenas del guion deben poder pertenecer al mismo video sin sentirse fuera
         de lugar entre sí.
   Pensado para que el conjunto dure entre {dur_min} y {dur_max} minutos hablado en total
   (aprox 140 palabras/min). Menciona la keyword_principal DE FORMA NATURAL y hablada
   dentro de los primeros 60 segundos del guion (primer o segundo beat del capítulo 1):
   YouTube analiza las palabras realmente narradas, no solo el título.
4) Una descripción para YouTube de 200-300 palabras en lenguaje NATURAL (nunca lista de
   palabras clave repetidas): la keyword_principal debe aparecer en la primera frase.
   Además, 15 a 20 tags (auditoría real de la competencia, agosto 2026: los videos que
   mejor posicionan en este nicho usan entre 18 y 29 tags, no solo 10): el primero debe
   ser la keyword_principal exacta, luego variaciones reales tipo pregunta que la gente
   escribe de verdad ("cómo tomar...", "a qué hora tomar...", "para qué sirve...",
   "beneficios de...", "cuánto tiempo tarda..."), y términos relacionados. Sin relleno
   ni tags que no describan el video.
5) Un disclaimer breve al final si el tema es de salud, finanzas u otro tema sensible.
6) Un campo "audiencia_exclusiva": escribe "mujeres" SOLO si el tema es
   biológica o temáticamente exclusivo de mujeres (ej: menstruación,
   menopausia, embarazo, lactancia, salud ginecológica). Para CUALQUIER otro
   tema de salud general (que le sirve tanto a hombres como a mujeres),
   escribe "ninguna". La mayoría de los videos deben ser "ninguna": no lo
   marques como exclusivo solo porque el tema sea más popular entre mujeres.

Devuélvelo en JSON con esta forma EXACTA (sin texto fuera del JSON; recuerda:
"visual" siempre en inglés, todo lo demás en español):
{{
  "keyword_principal": "...",
  "titulo": "...",
  "gancho": "...",
  "capitulos": [
    {{"nombre": "...", "beats": [{{"texto": "...", "visual": "english visual keyword here"}}, ...]}}
  ],
  "descripcion": "...",
  "tags": ["...","..."],
  "disclaimer": "...",
  "audiencia_exclusiva": "ninguna"

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
            from agents.presupuesto_ia import registrar_uso_gemini
            registrar_uso_gemini(1)  # se registra en el presupuesto compartido (ver agents/presupuesto_ia.py)
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
        # "llama-3.1-70b-versatile" fue DESCONTINUADO por Groq (confirmado
        # en vivo en la auditoría de agosto 2026: la API devolvía 400
        # "model_decommissioned"). Reemplazado por su sucesor recomendado.
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
    }
    ultimo_error = None
    for intento in range(3):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=60)
            if r.status_code in (429, 500, 503) and intento < 2:
                espera = 5 * (intento + 1)
                log(AGENT, f"Groq respondió {r.status_code} (sobrecarga temporal), "
                           f"reintentando en {espera}s...")
                time.sleep(espera)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            ultimo_error = e
            if intento < 2:
                time.sleep(5 * (intento + 1))
                continue
            raise
    raise ultimo_error


def _llamar_ollama(prompt, modelo):
    url = "http://localhost:11434/api/generate"
    body = {"model": modelo, "prompt": prompt, "stream": False}
    r = requests.post(url, json=body, timeout=120)
    r.raise_for_status()
    return r.json()["response"]


# --- Extensión automática cuando el guion sale corto (bug real encontrado en
# la auditoría de agosto 2026): el LLM a veces no respeta "8 a 14 beats por
# capítulo" y entrega guiones de apenas ~2 minutos, muy por debajo del
# objetivo de 8-15 minutos (el mínimo real para que YouTube habilite
# anuncios intermedios, que suben el RPM 40-100%). En vez de solo pedirlo
# más fuerte en el prompt (no garantiza nada), se MIDE la duración real del
# guion ya escrito y, si falta, se le pide al LLM contenido NUEVO adicional
# (nunca relleno/repetición) hasta acercarse al objetivo. ---
PALABRAS_POR_MINUTO_HABLADO = 140

# Versión CONDENSADA de las reglas, solo para las rondas de extensión.
# Por qué existe (hallazgo real de la auditoría): la versión completa
# (agents/viral_strategist.REGLAS_PARA_GUIONISTA) pesa ~1200 tokens: al
# repetirla completa en cada una de hasta 10 rondas de extensión por video,
# se choca con el límite de Groq de tokens-por-minuto (confirmado en vivo:
# errores 429 durante pruebas con varias rondas seguidas). Esta versión
# corta mantiene solo las reglas que de verdad hay que recordar en cada
# ronda, ahorrando tokens sin perder calidad.
REGLAS_EXTENSION_RESUMIDAS = """
Recuerda (resumen de las reglas ya usadas en este guion):
- Frases cortas (máximo 20 palabras), sin relleno tipo "es importante
  entender que...", directo a la acción.
- El campo "texto" es SOLO texto plano narrable: nada de asteriscos,
  guiones, numerales, ni marcas de tiempo.
- Cada beat = 1-2 frases + su propio "visual" en INGLÉS, específico y
  filmable con cámara real (nunca dibujos ni animaciones ni diagramas).
- Nunca repitas una palabra clave visual ya usada.
"""


def _fuentes_recortadas_para_extension(fuentes_texto: str, max_caracteres: int = 900) -> str:
    """Versión corta de las fuentes científicas, solo para no repetir el
    bloque completo (a veces >2000 caracteres) en cada ronda de extensión."""
    if len(fuentes_texto) <= max_caracteres:
        return fuentes_texto
    return fuentes_texto[:max_caracteres] + "\n[...resto de fuentes ya usadas en capítulos anteriores...]"


PROMPT_EXTENSION = """Ya escribiste este guion en español sobre {nicho}, inspirado en el ángulo de: "{titulo_ref}".

Título ya elegido: "{titulo}"

Capítulos YA ESCRITOS (no los repitas ni los reformules con otras palabras, continúa desde aquí con información NUEVA):
{resumen_capitulos}

ADVERTENCIA (léela con cuidado): en intentos anteriores algunos capítulos "nuevos" terminaron siendo casi el mismo \
tema que uno ya escrito arriba, solo con el título reformulado. Antes de escribir cada capítulo nuevo, revisa la \
lista de arriba y asegúrate de que su tema central sea GENUINAMENTE distinto (no una variación del mismo punto). \
Si ya se habló de un remedio o alimento específico, no le dediques otro capítulo entero, elige otro ángulo real \
que falte (por ejemplo: cómo empezar sin dinero extra, qué evitar, cómo mantenerlo a largo plazo, señales de que \
está funcionando, o un remedio/hábito que aún no se haya mencionado).

El guion completo lleva hasta ahora aproximadamente {palabras_actuales} palabras habladas (~{duracion_actual:.1f} \
minutos a 140 palabras/min), pero el objetivo real es llegar a entre {dur_min} y {dur_max} minutos (entre \
{palabras_min} y {palabras_max} palabras en total). Escribe {n_capitulos_nuevos} capítulo(s) ADICIONAL(es) que \
sigan el mismo video, con información REAL, específica y práctica que NO se haya mencionado todavía (más consejos \
concretos y accionables, precauciones importantes, errores comunes al aplicar esto, o un ángulo distinto de lo ya \
dicho). Nunca inventes una cifra que no esté en las fuentes de abajo.

MUY IMPORTANTE: cada uno de estos capítulos nuevos debe tener EN TOTAL al menos {palabras_por_capitulo_nuevo} \
palabras habladas repartidas en varios beats cortos (8 a 14 beats por capítulo, como indican las reglas de abajo). \
Los intentos anteriores quedaron demasiado cortos, así que desarrolla cada punto con más profundidad real \
(ejemplos concretos, el mecanismo de por qué funciona, cómo aplicarlo paso a paso) en vez de resumir en 2 o 3 \
frases.

{fuentes_cientificas}

{reglas_retencion}

Devuelve ÚNICAMENTE un JSON con esta forma exacta, sin nada de texto fuera del JSON (recuerda: "visual" siempre en \
inglés, todo lo demás en español):
{{"capitulos_nuevos": [{{"nombre": "...", "beats": [{{"texto": "...", "visual": "english visual keyword here"}}]}}]}}
"""


def _contar_palabras_guion(guion: dict) -> int:
    total = len((guion.get("gancho") or "").split())
    for cap in guion.get("capitulos", []):
        for beat in cap.get("beats", []):
            total += len((beat.get("texto") or "").split())
    return total


def _resumen_capitulos_para_extension(guion: dict, max_detallados: int = 6) -> str:
    """Resumen de los capítulos ya escritos, para que el LLM no los repita.
    Para no hacer crecer el prompt sin límite en rondas avanzadas de
    extensión (varios capítulos ya escritos), solo se detallan los más
    recientes; los más antiguos solo aparecen por su título (suficiente
    para evitar que se repita el mismo tema, sin gastar tantos tokens)."""
    capitulos = guion.get("capitulos", [])
    lineas = []
    antiguos = capitulos[:-max_detallados] if len(capitulos) > max_detallados else []
    recientes = capitulos[-max_detallados:] if len(capitulos) > max_detallados else capitulos
    if antiguos:
        titulos = ", ".join(c.get("nombre", "") for c in antiguos)
        lineas.append(f"(Temas ya cubiertos antes, no los repitas: {titulos})")
    for cap in recientes:
        resumen_texto = " ".join(b.get("texto", "") for b in cap.get("beats", []))[:280]
        lineas.append(f"- {cap.get('nombre', '')}: {resumen_texto}")
    return "\n".join(lineas)


def _intentar_llamar_llm(prompt: str, cfg: dict, provider_preferido: str):
    """Igual que la cascada principal, pero reutilizable para la extensión:
    prueba el proveedor preferido y cae a los demás disponibles."""
    orden = [provider_preferido] + [p for p in ("gemini", "groq", "ollama") if p != provider_preferido]
    for provider in orden:
        try:
            if provider == "gemini":
                key = cfg["apis"].get("gemini_api_key", "")
                if not key or "OBTENER_GRATIS" in key:
                    continue
                return _llamar_gemini(prompt, key)
            elif provider == "groq":
                key = cfg["apis"].get("groq_api_key", "")
                if not key or "OBTENER_GRATIS" in key:
                    continue
                return _llamar_groq(prompt, key)
            elif provider == "ollama":
                modelo = cfg["apis"].get("ollama_model", "llama3.1")
                return _llamar_ollama(prompt, modelo)
        except Exception as e:
            log(AGENT, f"Aviso: fallo extendiendo el guion con '{provider}' ({e}). Probando el siguiente...")
            continue
    return None


def _asegurar_duracion_minima(guion: dict, cfg: dict, idea: dict, fuentes_texto: str,
                               max_intentos: int = 8) -> dict:
    dur_min = cfg["estrategia"]["duracion_minima_min"]
    dur_max = cfg["estrategia"]["duracion_objetivo_min"]
    palabras_min = int(dur_min * PALABRAS_POR_MINUTO_HABLADO)
    palabras_max = int(dur_max * PALABRAS_POR_MINUTO_HABLADO)
    provider_preferido = cfg["apis"].get("llm_provider", "gemini")

    for intento in range(max_intentos):
        palabras_antes = _contar_palabras_guion(guion)
        if palabras_antes >= palabras_min:
            break

        faltan_palabras = palabras_min - palabras_antes
        # Se pide un poco más de lo que falta (los LLM casi siempre entregan
        # menos de lo pedido), y se reparte en varios capítulos cortos para
        # que cada uno tenga espacio de sobra para 8-14 beats reales.
        n_nuevos = min(5, max(2, round(faltan_palabras / 200)))
        log(AGENT, f"El guion quedó corto (~{palabras_antes/PALABRAS_POR_MINUTO_HABLADO:.1f} min de las "
                    f"{dur_min}-{dur_max} min objetivo, intento {intento+1}/{max_intentos}). "
                    f"Pidiendo {n_nuevos} capítulo(s) más con contenido nuevo real (nunca relleno)...")

        prompt_ext = PROMPT_EXTENSION.format(
            nicho=cfg["canal"]["nicho"], titulo_ref=idea["titulo"], titulo=guion.get("titulo", ""),
            resumen_capitulos=_resumen_capitulos_para_extension(guion),
            palabras_actuales=palabras_antes, duracion_actual=palabras_antes / PALABRAS_POR_MINUTO_HABLADO,
            dur_min=dur_min, dur_max=dur_max, palabras_min=palabras_min, palabras_max=palabras_max,
            n_capitulos_nuevos=n_nuevos,
            fuentes_cientificas=_fuentes_recortadas_para_extension(fuentes_texto),
            reglas_retencion=REGLAS_EXTENSION_RESUMIDAS,
            palabras_por_capitulo_nuevo=max(180, round(faltan_palabras / n_nuevos)),
        )
        try:
            texto = _intentar_llamar_llm(prompt_ext, cfg, provider_preferido)
            if not texto:
                log(AGENT, "No hay ningún proveedor de IA disponible para extender el guion; se deja como está.")
                break
            nuevos = _extraer_json(texto).get("capitulos_nuevos", [])
            if not nuevos:
                log(AGENT, "La extensión no trajo capítulos nuevos; se deja el guion como está.")
                break
            guion.setdefault("capitulos", []).extend(nuevos)
            guion = _sanitizar_guion(guion)
        except Exception as e:
            log(AGENT, f"Aviso: no se pudo extender el guion ({e}); se deja como está (nunca bloquea el video).")
            break

        # Si una ronda casi no agregó nada (el LLM se está quedando corto de
        # ideas nuevas de verdad), mejor parar aquí que insistir sin sentido
        # y arriesgar contenido relleno/repetitivo.
        palabras_despues = _contar_palabras_guion(guion)
        if palabras_despues - palabras_antes < 40:
            log(AGENT, "La última extensión aportó muy poco contenido nuevo; se deja el guion como está "
                        "(mejor esto que arriesgar relleno repetitivo).")
            break

        # Pausa breve entre rondas: Groq limita tokens-por-MINUTO (no solo
        # por día); varias llamadas grandes seguidas sin pausa son la causa
        # real de los 429 vistos en pruebas. Con esta pausa se reparte mejor
        # el uso y se evita esperar los reintentos más largos (5-10s) que
        # dispara el propio backoff cuando sí choca con el límite.
        time.sleep(3)

    palabras_finales = _contar_palabras_guion(guion)
    log(AGENT, f"Duración final estimada del guion: ~{palabras_finales / PALABRAS_POR_MINUTO_HABLADO:.1f} min "
                f"({palabras_finales} palabras habladas), objetivo {dur_min}-{dur_max} min.")
    return guion


def _extraer_json(texto):
    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio == -1 or fin == -1:
        raise ValueError("La respuesta del modelo no contiene JSON válido")
    return json.loads(texto[inicio:fin + 1])


def _quitar_lenguaje_meta(texto: str) -> str:
    """Elimina 'lenguaje meta' de SEO que el LLM a veces cuela en el texto
    narrado (bug real visto en un Short publicado el 14-ago-2026: la voz
    decía literalmente «La keyword principal 'alimentos para la visión' es
    crucial para entender...»). Un espectador jamás debe oír palabras como
    'keyword', 'SEO' o 'palabra clave': son instrucciones internas, no
    contenido. Se reescribe de forma determinista, sin gastar llamadas IA."""
    if not texto:
        return texto
    t = texto
    # «la keyword principal 'X' es/son...» -> «X es/son...» (con o sin comillas)
    t = re.sub(r"(?i)\bla\s+keyword[\s_]?principal\s*,?\s*['\"«]?([^'\"»]{3,60})['\"»]?\s*,?\s*",
               r"\1 ", t)
    t = re.sub(r"(?i)\bla\s+palabra\s+clave\s*(principal)?\s*,?\s*['\"«]?([^'\"»]{3,60})['\"»]?\s*,?\s*",
               r"\2 ", t)
    # Menciones sueltas de jerga interna que no deben narrarse jamás
    t = re.sub(r"(?i)\b(keyword[\s_]?principal|keyword|palabras?\s+claves?|seo|t[ií]tulo\s+del\s+video|meta\s*descripci[oó]n)\b",
               "", t)
    # Limpieza de espacios dobles/residuos de puntuación tras los reemplazos
    t = re.sub(r"\s{2,}", " ", t).strip(" ,;:")
    return t.strip()


def _sanitizar_guion(guion: dict) -> dict:
    """Aplica la limpieza anti-símbolos a TODO el texto narrable, sin importar
    si vino de un LLM externo o de la plantilla local. Defensa en profundidad."""
    guion["gancho"] = limpiar_texto_para_voz(_quitar_lenguaje_meta(guion.get("gancho", "")))
    guion["titulo"] = (guion.get("titulo", "") or "").replace("*", "").replace("#", "").strip()
    for cap in guion.get("capitulos", []):
        cap["nombre"] = re.sub(r"^\s*\d{1,2}:\d{2}(:\d{2})?\s*[-|]\s*", "", cap.get("nombre", ""))
        cap["nombre"] = cap["nombre"].replace("*", "").replace("#", "").strip()
        for beat in cap.get("beats", []):
            beat["texto"] = limpiar_texto_para_voz(_quitar_lenguaje_meta(beat.get("texto", "")))

    # Red de seguridad para "audiencia_exclusiva": si el LLM olvidó marcarlo
    # (pasa a veces), lo deducimos por palabras clave del propio tema. Mejor
    # pecar de cauteloso (usar la voz femenina) en un tema realmente
    # exclusivo de mujeres, que dejarlo al azar.
    PALABRAS_EXCLUSIVAS_MUJERES = [
        "menstrua", "menopaus", "embaraz", "lactancia materna", "ginecolog",
        "ovario", "óvulo", "ovulo", "vaginal", "climaterio", "parto", "posparto",
        "endometriosis", "sop ", "síndrome de ovario poliquístico",
        # Agregado al sumar el nuevo eje de salud sexual/hormonal (para que la
        # voz siga siendo siempre Dalia en contenido exclusivo de mujeres):
        "libido femenina", "deseo sexual femenino", "deseo sexual en la mujer",
        "salud hormonal femenina",
    ]
    if not guion.get("audiencia_exclusiva"):
        texto_para_detectar = " ".join([
            guion.get("keyword_principal", ""), guion.get("titulo", ""),
            guion.get("descripcion", ""), " ".join(guion.get("tags", [])),
        ]).lower()
        if any(p in texto_para_detectar for p in PALABRAS_EXCLUSIVAS_MUJERES):
            guion["audiencia_exclusiva"] = "mujeres"
        else:
            guion["audiencia_exclusiva"] = "ninguna"

    return guion


def _plantilla_local(idea, cfg):
    """Generador SIN IA externa: 100% gratis y funciona sin ninguna cuenta.
    Calidad menor, pero deja el pipeline operativo end-to-end para pruebas
    o como respaldo si todas las APIs gratuitas fallan o se acaba la cuota.
    Ya usa la estructura de beats para mantener consistencia con el resto
    del sistema."""
    nicho = cfg["canal"]["nicho"]
    titulos_generico = [
        f"Hábitos Naturales Para Tu {nicho.title()}",
        f"La Verdad Sobre {nicho.title()}",
        f"Cambios Simples Para Tu {nicho.title()} Hoy",
    ]
    titulo_elegido = random.choice(titulos_generico)
    if len(titulo_elegido) > 60:
        titulo_elegido = titulo_elegido[:60].rsplit(" ", 1)[0]  # corta en la última palabra completa
    titulo = titulo_elegido
    capitulos = [
        {
            "nombre": "Lo que nadie te dice",
            "beats": [
                {"texto": f"Esto sobre {nicho} está cambiando la vida de miles de personas.",
                 "visual": "person smiling outdoors in the morning sunlight"},
                {"texto": "Y probablemente tú estás cometiendo el mismo error todos los días.",
                 "visual": "tired person looking at phone screen"},
                {"texto": "Te voy a mostrar exactamente qué hacer, paso a paso.",
                 "visual": "hands writing in a notebook on a wooden table"},
            ],
        },
        {
            "nombre": "El problema real",
            "beats": [
                {"texto": "La mayoría de las personas atacan el síntoma, no la causa.",
                 "visual": "hand holding pills close up"},
                {"texto": "Por eso el problema siempre regresa.",
                 "visual": "wall clock in a kitchen"},
                {"texto": "Aquí está lo que la evidencia realmente muestra.",
                 "visual": "doctor talking with a patient in office"},
            ],
        },
        {
            "nombre": "Qué hacer hoy mismo",
            "beats": [
                {"texto": "Primero, cambia esta rutina en tus mañanas.",
                 "visual": "person preparing a healthy breakfast in the kitchen"},
                {"texto": "Segundo, elimina este hábito que te está afectando.",
                 "visual": "person pushing away a soda glass on the table"},
                {"texto": "Tercero, agrega esta costumbre simple antes de dormir.",
                 "visual": "person reading a book in bed with warm light"},
            ],
        },
        {
            "nombre": "Antes de irte",
            "beats": [
                {"texto": "Esto es información general y no reemplaza una consulta profesional.",
                 "visual": "person walking in a park at sunset"},
                {"texto": "Si te sirvió este video, suscríbete para más contenido como este.",
                 "visual": "person smiling directly at the camera"},
            ],
        },
    ]
    return {
        "keyword_principal": nicho,
        "titulo": titulo,
        "gancho": f"Esto sobre {nicho} podría estar afectándote sin que lo notes.",
        "capitulos": capitulos,
        "descripcion": (
            f"Descubre todo sobre {nicho}: en este video te explicamos hábitos simples y prácticos "
            f"que puedes aplicar hoy mismo, con cambios respaldados por la evidencia "
            f"disponible. Si te interesa {nicho}, este contenido es para ti."
        ),
        "tags": [nicho, "consejos", "hábitos saludables", "bienestar", "rutina diaria"],
        "disclaimer": "Este video es solo informativo y no sustituye una consulta médica o profesional.",
        "audiencia_exclusiva": "ninguna",

    }


def generar_guion(idea: dict) -> dict:
    cfg = load_config()
    provider_preferido = cfg["apis"].get("llm_provider", "none")
    nicho = cfg["canal"]["nicho"]
    dur_min = cfg["estrategia"]["duracion_minima_min"]
    dur_max = cfg["estrategia"]["duracion_objetivo_min"]

    # Investigación científica ANTES de escribir (nunca al revés): se buscan
    # estudios reales sobre el tema exacto para que el guionista solo pueda
    # citar cifras que existan de verdad. Si esto falla por cualquier motivo
    # (sin internet, API caída), seguimos sin bloquear el video: simplemente
    # el guion no incluirá cifras específicas (ver instrucción en el prompt).
    # Si el Orquestador ya validó estudios al elegir esta idea (ver
    # orchestrator.elegir_idea_no_usada), los reutilizamos en vez de volver
    # a consultar Europe PMC (ahorra tiempo y llamadas).
    estudios = idea.get("_estudios_validados", [])
    try:
        from agents.investigacion_cientifica import buscar_estudios, construir_bloque_fuentes_para_prompt
        if not estudios:
            estudios = buscar_estudios(idea["titulo"])
        fuentes_texto = construir_bloque_fuentes_para_prompt(estudios)
    except Exception as e:
        log(AGENT, f"Aviso: no se pudo investigar estudios científicos previos ({e}). "
                    f"El guion no incluirá cifras específicas por seguridad.")
        fuentes_texto = (
            "No hay fuentes científicas disponibles en este momento. REGLA OBLIGATORIA: "
            "NO inventes cifras, porcentajes ni estudios; habla en términos generales."
        )

    prompt = PROMPT_BASE.format(
        nicho=nicho, titulo_ref=idea["titulo"], dur_min=dur_min, dur_max=dur_max,
        reglas_retencion=REGLAS_PARA_GUIONISTA, reglas_seo=REGLAS_SEO_PARA_GUIONISTA,
        fuentes_cientificas=fuentes_texto,
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

    guion = _sanitizar_guion(guion)

    # Si el guion quedó corto (bug real: el LLM a veces ignora la cantidad
    # de beats pedida), se extiende con contenido nuevo real antes de
    # seguir, para que el video sí llegue al mínimo que YouTube exige para
    # habilitar anuncios intermedios (8 minutos) y al objetivo configurado.
    try:
        guion = _asegurar_duracion_minima(guion, cfg, idea, fuentes_texto)
    except Exception as e:
        log(AGENT, f"Aviso: no se pudo verificar/extender la duración del guion ({e}). "
                    f"El video se genera igual con el guion que ya se tiene.")

    # Verificación final OBLIGATORIA: cualquier cifra puntual que haya quedado
    # en el guion se confirma contra los resúmenes reales encontrados antes de
    # escribir. Lo que no se pueda confirmar se suaviza (nunca se inventa un
    # reemplazo). Esto nunca bloquea el video si algo falla.
    try:
        from agents.investigacion_cientifica import verificar_y_filtrar_guion
        guion = verificar_y_filtrar_guion(guion, estudios)
    except Exception as e:
        log(AGENT, f"Aviso: no se pudo completar la verificación científica final ({e}). "
                    f"Por seguridad, no se incluirán referencias en este video.")
        guion["referencias"] = []

    # Refuerzo de credibilidad pedido explícitamente por el usuario
    # (auditoría agosto 2026): que el video SÍ mencione en voz alta que la
    # información tiene respaldo científico real, con toma de un
    # documento/estudio en pantalla, y con el enlace real disponible en la
    # descripción. Esto se agrega incluso si ninguna cifra puntual del
    # guion pudo verificarse palabra por palabra arriba (ver
    # agents/citas_cientificas.py: nunca inventa un hallazgo nuevo, solo
    # comunica que el estudio real existe).
    try:
        from agents.citas_cientificas import agregar_citas_cientificas_en_guion
        guion = agregar_citas_cientificas_en_guion(guion, estudios)
    except Exception as e:
        log(AGENT, f"Aviso: no se pudieron insertar las citas científicas en pantalla ({e}). "
                    f"El video se genera igual, solo sin ese refuerzo de credibilidad.")

    # Regla de negocio NO NEGOCIABLE del canal: SIEMPRE 3 momentos pidiendo
    # suscripción (inicio, mitad, final). Se aplica aquí en código (no se le
    # deja la tarea solo al LLM) para que ocurra el 100% de las veces, con el
    # presentador fijo del canal en pantalla. Ver agents/suscripcion_cta.py.
    try:
        from agents.suscripcion_cta import agregar_llamados_a_suscripcion
        guion = agregar_llamados_a_suscripcion(guion)
    except Exception as e:
        log(AGENT, f"Aviso: no se pudieron insertar los llamados a suscripción ({e}). "
                    f"El video se genera igual, pero revisa este punto.")

    # Llamado a comentar y compartir (pregunta específica del tema + pedido
    # directo de compartir, sin premios ni sorteos -- ver
    # agents/engagement_cta.py, cumple con la política de YouTube).
    try:
        from agents.engagement_cta import agregar_llamado_interaccion
        guion = agregar_llamado_interaccion(guion)
    except Exception as e:
        log(AGENT, f"Aviso: no se pudo insertar el llamado a interacción ({e}). "
                    f"El video se genera igual, pero revisa este punto.")

    return guion


if __name__ == "__main__":
    from agents.trend_scout import buscar_ideas_potenciales
    idea = buscar_ideas_potenciales()[0]
    guion = generar_guion(idea)
    print(json.dumps(guion, ensure_ascii=False, indent=2))
