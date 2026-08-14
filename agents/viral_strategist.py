"""
AGENTE 9: ESTRATEGA VIRAL / RETENCIÓN ("Viral Strategist")
----------------------------------------------------
Este agente NO improvisa: encapsula reglas de retención de audiencia basadas
en investigación real sobre edición y guionismo de YouTube (estudios de
creadores, guías de edición de retención, y documentación de la propia
plataforma). Su trabajo es:

  1) Inyectar reglas de guion (ritmo, gancho, cero relleno) al Guionista.
  2) Definir cuánto debe durar cada corte visual (para que VisualScout y
     EditorVideo generen un video dinámico, no aburrido).
  3) Construir el título/descripción/índice con capítulos para publicar.

Fuentes de las reglas (resumen; ver conversación/README para detalle):
  - El "gancho" debe entregar una promesa de valor clara en los primeros
    5-15 segundos, sin muletillas de relleno ("hola a todos, bienvenidos...").
  - Para video LARGO (10-18 min, nuestro caso) el cambio visual recomendado
    es cada 5-15 segundos (no cada 2-3s, eso aplica a Shorts). Un mismo clip
    NUNCA debería sostenerse más de ~10s sin cambiar.
  - Insertar "mini-ganchos" / cambios de ritmo cada 2-4 minutos para
    resetear la atención en videos largos.
  - Cero relleno: frases cortas (ideal <20 palabras), sin pausas muertas,
    sin repetir la misma idea con otras palabras.
"""

# --- Parámetros de ritmo (todo esto es configurable y basado en la
#     investigación resumida arriba) ---
DURACION_MIN_CORTE_SEG = 3.0     # ningún corte visual dura menos de esto (evita caos)
DURACION_MAX_CORTE_SEG = 9.0     # ningún corte visual dura más de esto (evita aburrimiento)
DURACION_GANCHO_SEG_OBJETIVO = 12  # el "hook" debe leerse en ~10-15s
PALABRAS_MAX_POR_FRASE = 20        # frases cortas = mejor ritmo y subtítulos más legibles
MINUTOS_ENTRE_MINI_GANCHOS = 3     # cada cuánto insertar un "reset" de atención


REGLAS_PARA_GUIONISTA = f"""
REGLAS DE RETENCIÓN DE AUDIENCIA (basadas en investigación real de edición
y guionismo de YouTube; síguelas de forma estricta):

1. GANCHO (primeras 2-3 frases / ~{DURACION_GANCHO_SEG_OBJETIVO} segundos hablados):
   - Debe prometer un valor CONCRETO y específico (no genérico).
   - PROHIBIDO empezar con muletillas de relleno como "Hola a todos",
     "Bienvenidos de nuevo a mi canal", "En el video de hoy vamos a hablar de".
   - Empieza directo con la promesa, una cifra, o una afirmación que genere
     curiosidad o urgencia.

2. RITMO Y CERO RELLENO:
   - Frases cortas, de máximo {PALABRAS_MAX_POR_FRASE} palabras.
   - Nunca repitas la misma idea con otras palabras ("dicho de otro modo...",
     "es decir...", "en otras palabras..." -> PROHIBIDO, elimínalo).
   - Cada frase debe aportar información nueva. Si una frase no aporta nada
     nuevo, no la escribas.

3. TEXTO 100% PARA VOZ HABLADA (muy importante, léelo con cuidado):
   - El campo "texto" de cada beat se va a leer en voz alta con un sintetizador
     de voz TAL CUAL como lo escribas, palabra por palabra y símbolo por símbolo.
   - Por lo tanto el campo "texto" debe ser SOLO texto plano narrable:
     únicamente letras, espacios, y estos signos de puntuación: punto (.),
     coma (,), signos de interrogación y exclamación (¿? ¡!).
   - PROHIBIDO usar: asteriscos (*), guiones (-), marcas de tiempo (0:45, 12:30),
     numerales/hashtags (#), guiones bajos (_), viñetas o listas con símbolos,
     paréntesis con acotaciones, comillas de énfasis, o cualquier formato tipo
     Markdown. Si quieres enumerar algo, dilo con palabras: "El primer punto
     es... El segundo punto es...", nunca con "1)", "-", o "*".
   - Los nombres de capítulo (campo "nombre") NO llevan marca de tiempo (el
     sistema la calcula automáticamente); solo un título corto sin símbolos.

4. VISUALES 100% REALES (nunca dibujos ni animaciones):
   - Cada "beat" (fragmento corto de 1-2 frases, ~4 a 8 segundos hablados)
     debe tener su propia palabra clave visual MUY específica y FILMABLE
     con cámara real: una acción concreta, un objeto concreto, una escena
     de la vida real. Ejemplos buenos: "manos cortando vegetales frescos en
     tabla de madera", "persona corriendo al amanecer en el parque",
     "primer plano de un plato de salmón con verduras".
   - Ejemplos PROHIBIDOS (demasiado vagos o no filmables): "gráfico de salud",
     "animación del sistema inmune", "diagrama", "ilustración", "dibujo".
   - No repitas la misma palabra clave visual dos veces en el guion completo.

5. ESTRUCTURA EN "BEATS" (no bloques largos de texto):
   - Divide cada capítulo en varios "beats" cortos (no un solo bloque de texto).
   - Cada beat = 1 a 2 frases + 1 palabra clave visual específica.
   - Un capítulo típico de 60-90 segundos hablados debe tener entre 8 y 14 beats.

6. MINI-GANCHOS: aproximadamente cada {MINUTOS_ENTRE_MINI_GANCHOS} minutos de
   contenido, agrega una frase tipo "reset" de atención (una pregunta directa
   al espectador, una cifra sorprendente, o un adelanto de lo que viene) para
   evitar que la audiencia se aburra y se vaya.
"""

REGLAS_SEO_PARA_GUIONISTA = """
REGLAS DE SEO DE YOUTUBE 2026 (basadas en investigación real, no
improvisadas; síguelas para maximizar que el video aparezca en buscadores):

1. PALABRA CLAVE PRINCIPAL: define una sola "keyword_principal" (2-4
   palabras) que represente exactamente lo que alguien buscaría en YouTube
   para encontrar este video. Todo el título, descripción y tags giran
   alrededor de ella.

2. TÍTULO: la keyword_principal debe estar dentro de las primeras 5
   palabras del título. Máximo 60 caracteres (se corta en móvil si es más
   largo). Usa Title Case (Cada Palabra Importante Con Mayúscula). Evita el
   "keyword stuffing" (repetir la palabra clave varias veces suena a spam y
   YouTube lo penaliza). El título debe prometer solo lo que el video
   realmente cumple: el clickbait sube el clic pero hunde la retención, y
   la retención pesa más que el clic solo.

3. LA KEYWORD DEBE DECIRSE EN VOZ ALTA: YouTube analiza el audio
   transcrito del video, no solo el título y la descripción. Menciona la
   keyword_principal de forma natural dentro de los primeros 60 segundos
   hablados del guion.

4. DESCRIPCIÓN: los primeros ~150 caracteres son los que se muestran como
   snippet en los resultados de búsqueda, así que la keyword_principal debe
   aparecer en la primera frase. El resto de la descripción debe tener
   200-300 palabras en lenguaje natural (nunca una lista de palabras clave
   repetidas), incluir 2-3 variaciones relacionadas de forma orgánica.

5. TAGS: 10 a 15, nunca más. El primero debe ser la keyword_principal
   exacta. Incluye variaciones y términos relacionados reales (no tags
   irrelevantes ni de moda que no describan el video: YouTube penaliza eso).
"""


def calcular_duraciones_de_corte(num_beats: int, duracion_total_seg: float) -> list:
    """
    Devuelve una lista de duraciones (segundos) para cada beat, respetando
    los límites de duración de corte (ni muy largo/aburrido ni tan corto que
    sea caótico). Si hay pocos beats para la duración total, se reparte el
    tiempo entre cortes de duración media; si hay muchos beats (guion bien
    fragmentado), cada corte queda naturalmente corto y dinámico.
    """
    if num_beats <= 0:
        return []
    duracion_pareja = duracion_total_seg / num_beats
    duracion_ajustada = min(max(duracion_pareja, DURACION_MIN_CORTE_SEG), DURACION_MAX_CORTE_SEG)
    # Si el ajuste cambia el total, repartimos la diferencia proporcionalmente
    total_ajustado = duracion_ajustada * num_beats
    factor = duracion_total_seg / total_ajustado if total_ajustado > 0 else 1
    return [duracion_ajustada * factor for _ in range(num_beats)]


def construir_descripcion_publicacion(guion: dict, timestamps_capitulos: list, nombre_canal: str = "",
                                       url_canal: str = "", bloque_afiliados: str = "",
                                       bloque_mas_videos: str = "") -> str:
    """
    Arma la descripción final de YouTube siguiendo las reglas de SEO 2026
    investigadas (no improvisadas):
      - Los primeros ~150 caracteres deben incluir la palabra clave principal
        y el valor concreto del video (eso es lo que Google/YouTube muestran
        como snippet de búsqueda).
      - Cuerpo de 200+ palabras en lenguaje natural (nunca relleno de
        palabras clave repetidas).
      - Capítulos con tiempos reales (además de navegación, hace elegible
        al video para aparecer como "chapters" en resultados de Google).
      - 3-5 hashtags al final (los primeros 3 se muestran arriba del título).
    timestamps_capitulos: lista de tuplas (nombre_capitulo, segundos_inicio).
    """
    resumen = guion.get("descripcion", "").strip()
    gancho = guion.get("gancho", "").strip()
    keyword_principal = guion.get("keyword_principal", "").strip()

    lineas = []

    # Primeros ~150 caracteres: gancho + keyword principal si no viene ya incluida
    primer_bloque = gancho if gancho else resumen
    if keyword_principal and keyword_principal.lower() not in primer_bloque.lower():
        primer_bloque = f"{primer_bloque} {keyword_principal}."
    lineas.append(f"🔥 {primer_bloque}")
    lineas.append("")

    if resumen and resumen.strip() != primer_bloque.strip():
        lineas.append(resumen)
        lineas.append("")

    lineas.append("📌 ÍNDICE DEL VIDEO (haz clic en cualquier minuto para saltar ahí):")
    for nombre, segundos in timestamps_capitulos:
        minutos = int(segundos // 60)
        seg = int(segundos % 60)
        lineas.append(f"{minutos:02d}:{seg:02d} {nombre}")
    lineas.append("")

    referencias = guion.get("referencias", [])
    if referencias:
        lineas.append("📚 REFERENCIAS CIENTÍFICAS (verificadas, revísalas tú mismo):")
        for r in referencias:
            autores = r.get("autores", "").strip()
            autor_corto = autores.split(",")[0] if autores else ""
            lineas.append(f"• {r['titulo']} — {autor_corto} et al., {r.get('revista','')} "
                          f"({r.get('anio','')}): {r['url']}")
        lineas.append("")

    if bloque_afiliados:
        lineas.append(bloque_afiliados)

    if bloque_mas_videos:
        lineas.append(bloque_mas_videos)

    if url_canal:
        lineas.append(f"👉 Suscríbete gratis para más videos: {url_canal}")
        lineas.append("")

    tags = guion.get("tags", [])
    if tags:
        # Primer hashtag = palabra clave principal, luego variaciones (según
        # investigación: el orden de las primeras etiquetas pesa más).
        ordenados = []
        if keyword_principal:
            ordenados.append(keyword_principal)
        ordenados += [t for t in tags if t.lower() != keyword_principal.lower()]
        lineas.append(" ".join(f"#{t.replace(' ', '')}" for t in ordenados[:5]))
        lineas.append("")

    disclaimer = guion.get("disclaimer", "")
    if disclaimer:
        lineas.append(f"⚠️ {disclaimer}")

    return "\n".join(lineas)


def construir_tags_seo(guion: dict, nombre_canal: str = "") -> list:
    """
    Orden de tags según la investigación de SEO 2026:
    1) palabra clave EXACTA principal, 2) nombre del canal (ayuda a que tus
    otros videos aparezcan como sugeridos), 3) variaciones y términos
    relacionados. Sin relleno ni tags irrelevantes.
    """
    keyword_principal = guion.get("keyword_principal", "").strip()
    tags = guion.get("tags", [])
    resultado = []
    if keyword_principal:
        resultado.append(keyword_principal)
    if nombre_canal:
        resultado.append(nombre_canal)
    for t in tags:
        if t.lower() not in [r.lower() for r in resultado]:
            resultado.append(t)
    return resultado[:15]

