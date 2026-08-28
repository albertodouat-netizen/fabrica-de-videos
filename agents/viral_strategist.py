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

import re

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

0-BIS. FÓRMULA DE TÍTULO 2026 (validada con datos del propio canal: los
   títulos de curiosidad/mito promedian 674-727 vistas vs 50 de los
   descriptivos; y la investigación del algoritmo 2026 confirma que el
   Browse feed premia especificidad + beneficio claro):
   - El título DEBE combinar: (a) el ERROR/MITO/SECRETO como gancho +
     (b) la keyword buscable + (c) el beneficio o consecuencia concreta.
   - Patrones ganadores: "El Error Que [empeora X] (Y Lo Que Sí Funciona)",
     "Nadie Te Dijo Esto Sobre [keyword]", "[keyword]: El Mito Que Te Está
     [costando Y]", "Por Qué [síntoma común] No Mejora (Y Cómo Cambiarlo)".
   - PROHIBIDO el título puramente descriptivo tipo "Beneficios de X: Guía".
   - Los PRIMEROS 30 SEGUNDOS son señal de ranking DIRECTA en 2026: el
     gancho debe abrir con cifra + síntoma en segunda persona ("¿Sabías
     que el 50% de quienes sienten X...?") y prometer el desenlace
     concreto del video, sin saludos ni presentaciones.

0. PROHIBIDO despedirse o sonar a cierre ("eso fue todo", "gracias por
   ver", "nos vemos", "para terminar", "ya para finalizar", "espero que te
   haya servido") en CUALQUIER beat que no sea el último del último
   capítulo. El video fluye continuo: cada sección termina ANUNCIANDO lo
   que viene ("y ahora viene lo más importante..."), nunca despidiéndose.

1. GANCHO (los primeros 15 segundos deciden si la persona se queda o se va,
   según datos reales de retención de YouTube 2026; síguelo con precisión
   quirúrgica, no es "una sugerencia más"):

   - EL DATO CLAVE: en un análisis real de miles de guiones de YouTube, los
     que entregan una promesa de valor CONCRETA dentro de los primeros 15
     segundos retienen en promedio 52% de la audiencia; los que no, solo
     44%. La caída más brusca de espectadores de todo el video ocurre entre
     el segundo 10 y el 20. Es decir: tienes hasta el segundo 15, no 30,
     para "ganarte" al espectador.
   - ESTRUCTURA OBLIGATORIA EN 3 FASES (basada en esa misma investigación):
       Fase 1 (segundos 0-5, el "gancho" propiamente dicho, primera frase):
         una interrupción de patrón. Debe sonar distinto a como empiezan
         el 90% de los videos de salud. Usa una cifra concreta, una
         afirmación que rompa una creencia común, o una pregunta directa
         e incómoda. NUNCA una afirmación genérica tipo "hoy vamos a
         hablar de...".
       Fase 2 (segundos 5-15, segunda frase del gancho): la promesa de
         valor CONCRETA y específica ("vas a aprender exactamente cómo...",
         "al final de este video vas a saber cuáles 3 alimentos..."). Debe
         quedar clarísimo QUÉ se lleva el espectador si se queda, no solo
         "de qué trata" el video.
       Fase 3 (primer beat del capítulo 1, justo después del gancho): el
         "gancho de compromiso": plantea la pregunta o el problema exacto
         que el resto del video va a resolver (un "bucle abierto" que solo
         se cierra si sigue viendo), o arranca ya con el primer paso del
         contenido. NUNCA otra frase de introducción/relleno aquí.
   - PROHIBIDO ABSOLUTO en los primeros 15 segundos (los "7 asesinos de
     retención" documentados en la investigación de 2026, cada uno de
     estos por sí solo puede hundir la retención inicial): saludo genérico
     ("Hola a todos", "Bienvenidos de nuevo al canal"), presentar el canal
     o sus credenciales, explicar de qué "va a tratar" el video en vez de
     entregar ya la promesa concreta, cualquier disculpa o descargo de
     responsabilidad, pedir suscribirse ANTES de dar valor, frases de
     relleno tipo "en el video de hoy", y cualquier cliché que el
     espectador ya haya escuchado cientos de veces en otros canales.
   - LA CIFRA AYUDA: agregar un número concreto en los primeros 15 segundos
     ("el 80% de las personas...", "en solo 3 pasos...") da más credibilidad
     inmediata que una descripción vaga. Si tienes una fuente científica
     real para esa cifra (ver bloque de fuentes más abajo), úsala aquí
     mismo en el gancho si encaja de forma natural.
   - HONESTIDAD DEL GANCHO (no es solo ética, es estrategia): el gancho
     debe prometer EXACTAMENTE lo que el video cumple. Un gancho engañoso
     puede subir el clic momentáneamente pero hunde la retención a mitad
     de video en cuanto el espectador nota que no se cumplió la promesa, y
     eso pesa más para el algoritmo que un buen inicio.
   - VISUAL DEL GANCHO: el campo "visual" del gancho y del primer beat debe
     ser el más llamativo, específico y con más "movimiento/acción real"
     de todo el guion (nunca una escena genérica y pasiva como "persona
     sonriendo a cámara"). Piensa en una escena que por sí sola, sin
     sonido, ya genere curiosidad: una acción en curso, un resultado
     visible, un close-up impactante relacionado exactamente con la
     promesa del gancho. Evita reutilizar esta misma idea visual más
     adelante en el video (debe sentirse única, la "carta de presentación").

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
   - PROHIBIDO ABSOLUTO (regla de seguridad real, agosto 2026): nunca sugieras
     escenas de "masaje", "spa", personas sin camisa/con la espalda descubierta,
     ropa de baño, lencería, ni cualquier escena que pueda mostrar piel
     descubierta de forma no apropiada. Aunque el tema sea relajación muscular
     o estrés, usa alternativas seguras y siempre con ropa: "persona respirando
     profundamente con los ojos cerrados", "persona estirando el cuello con
     ropa deportiva", "persona meditando sentada vestida cómodamente", "manos
     sosteniendo una taza de té caliente". La salud del canal depende de esto.
   - PROHIBIDO ABSOLUTO #2 (hallazgo real, agosto 2026): NUNCA describas a una
     persona solo por su "cuerpo" o "figura" en abstracto (ejemplos prohibidos:
     "body figure", "human body", "cuerpo humano", "silueta"). Ese tipo de
     descripción aislada generó una imagen de desnudo real al probarlo. Cuando
     el tema sea sobre el cuerpo/anatomía (ej. "cómo el cuerpo absorbe el
     magnesio"), describe SIEMPRE una acción o escena concreta y vestida en su
     lugar: "persona tomando un suplemento con un vaso de agua en la cocina",
     "primer plano de una tableta de magnesio en la mano", nunca una persona
     descrita solo por su anatomía.

5. ESTRUCTURA EN "BEATS" (no bloques largos de texto):
   - Divide cada capítulo en varios "beats" cortos (no un solo bloque de texto).
   - Cada beat = 1 a 2 frases + 1 palabra clave visual específica.
   - Un capítulo típico de 60-90 segundos hablados debe tener entre 8 y 14 beats.

6. MINI-GANCHOS: aproximadamente cada {MINUTOS_ENTRE_MINI_GANCHOS} minutos de
   contenido, agrega una frase tipo "reset" de atención (una pregunta directa
   al espectador, una cifra sorprendente, o un adelanto de lo que viene) para
   evitar que la audiencia se aburra y se vaya.

7. MUY PRÁCTICO, CERO RELLENO ARGUMENTATIVO (regla añadida tras auditoría
   de 2026; síguela con la misma exigencia que las demás):
   - Nada de introducciones largas explicando POR QUÉ algo es importante
     antes de decir QUÉ hacer. Máximo 1 frase de contexto/justificación por
     idea, después ve directo a la acción concreta.
   - Aplica el patrón "resultado primero, después el cómo": en vez de "hoy
     te voy a explicar por qué el magnesio ayuda a dormir", usa algo como
     "el magnesio antes de dormir puede ayudarte a conciliar el sueño más
     rápido, y así lo tomas". El beneficio y la acción van antes que la
     explicación teórica.
   - PROHIBIDO usar frases de puro relleno argumentativo tipo "es
     importante entender que...", "muchos estudios sugieren que...", "cabe
     destacar que...", "como mencionamos anteriormente..." -> elimínalas,
     ve directo al dato o a la acción.
   - El video entero debe sentirse como una guía que se puede EJECUTAR, no
     una charla teórica. Cada capítulo debe dejar algo que el espectador
     pueda hacer literalmente hoy mismo, no solo "entender mejor" el tema.

8. GUÍA PRÁCTICA OBLIGATORIA (el "plus" que el espectador se lleva):
   - Uno de los capítulos (idealmente el penúltimo, justo antes del cierre)
     DEBE ser una guía de acción concreta y numerada: "Primero...",
     "Segundo...", "Tercero..." (dicho con palabras, nunca con números o
     viñetas escritas, ver regla 3). Nombra ese capítulo algo como "Tu plan
     de acción" o "Guía rápida para hoy".
   - Cada paso de esa guía debe ser algo que la persona pueda hacer HOY
     MISMO, sin comprar nada especial ni necesitar conocimientos previos.
   - Esta guía es el motivo por el que alguien se queda hasta el final y
     vuelve a ver tus próximos videos: entrega SIEMPRE valor accionable
     real, nunca la dejes fuera del guion.

9. CREDIBILIDAD CIENTÍFICA VISIBLE (regla añadida tras auditoría de 2026;
   un canal de salud vive o muere de esto, es lo que Google/YouTube llaman
   "E-E-A-T" -experiencia, pericia, autoridad y confiabilidad- y es
   todavía más exigente en temas de salud):
   - No basta con que la información sea correcta "por dentro": el
     espectador necesita PERCIBIR que hay ciencia real detrás, en el
     momento mismo en que la escucha, no solo si abre la descripción.
   - Cuando el bloque de "FUENTES CIENTÍFICAS REALES" de arriba SÍ tenga
     estudios disponibles, menciona de forma natural, al menos un par de
     veces en el guion, que la información viene de una fuente real (por
     ejemplo: "esto lo confirma un estudio publicado en la revista..." o
     "la evidencia científica reciente respalda que..."), usando SOLO el
     nombre de revista/año que aparezca en esas fuentes reales, nunca
     inventado. (Nota: el sistema además garantiza esto por código en
     otro paso posterior, así que esta regla es un refuerzo, no la única
     protección.)

10. SEGURIDAD MÉDICA ABSOLUTA (regla añadida 16-ago-2026 tras investigar
   la política de desinformación médica de YouTube, la ÚNICA que puede
   borrar un canal de salud con strikes, no solo desmonetizarlo):
   - PROHIBIDO ABSOLUTO afirmar o insinuar que un alimento, hierba,
     suplemento o práctica CURA, ELIMINA o REEMPLAZA el tratamiento de
     ninguna enfermedad (cáncer, diabetes, hipertensión, depresión,
     COVID, etc.). Ejemplos prohibidos: "el ajo cura el cáncer", "toma
     esto en vez de tu medicamento", "olvídate de la insulina".
   - PROHIBIDO sugerir abandonar, reducir o sustituir medicamentos
     recetados o tratamientos médicos. Ni siquiera como pregunta
     retórica.
   - PROHIBIDO contradecir el consenso de la OMS o autoridades
     sanitarias sobre prevención o tratamiento de enfermedades.
   - Palabras SEGURAS y honestas que sí puedes usar: "puede APOYAR",
     "puede CONTRIBUIR a", "se ha ASOCIADO con", "puede COMPLEMENTAR
     (nunca reemplazar) las indicaciones de tu médico", "la evidencia
     SUGIERE".
   - Al hablar de cualquier condición médica seria, recuerda de forma
     natural que el video no sustituye al médico tratante.
   - Esta regla está POR ENCIMA de cualquier regla de gancho o retención:
     un gancho llamativo jamás justifica una promesa médica prohibida.
     "Este alimento puede apoyar tu visión" es un gancho válido;
     "este alimento te curará la vista" puede costar el canal entero.
   - Nunca describas una fuente como "los expertos dicen" o "estudios
     demuestran" sin más: si tienes el nombre real de la revista o el año,
     dilo explícitamente, es lo que separa un canal serio de uno genérico.
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

    # CORRECCIÓN (auditoría video magnesio, 21-ago-2026): antes bastaba con
    # que primer_bloque tuviera la keyword añadida al final para que "no
    # fuera igual" al resumen y este se pegara COMPLETO otra vez (descripción
    # con el mismo párrafo duplicado, visto en el video real). Ahora solo se
    # añade si el resumen NO está ya contenido en el primer bloque.
    if resumen and resumen.strip() not in primer_bloque:
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

    # Contacto comercial (añadido 16-ago-2026, pedido del usuario): puerta
    # de entrada para que marcas relacionadas con salud natural puedan
    # proponer patrocinios/menciones mientras el canal alcanza los
    # requisitos de AdSense. Es la práctica estándar de los canales que
    # consiguen sus primeras marcas: el contacto visible en CADA video.
    lineas.append("🤝 ¿Representas una marca de salud/bienestar y quieres colaborar "
                  "con este canal? Escríbenos: albertodouat@gmail.com")
    lineas.append("")

    tags = guion.get("tags", [])
    if tags:
        # Primer hashtag = palabra clave principal, luego variaciones (según
        # investigación: el orden de las primeras etiquetas pesa más).
        ordenados = []
        if keyword_principal:
            ordenados.append(keyword_principal)
        ordenados += [t for t in tags if t.lower() != keyword_principal.lower()]
        # Bug real encontrado en auditoría (agosto 2026): un tag con comas o
        # paréntesis (ej. el nicho completo usado como tag de respaldo) hacía
        # un hashtag roto tipo "#saludnatural,alternativa,(...)"; ahora se
        # limpia todo lo que no sea letra/número antes de armar el hashtag.
        hashtags_validos = []
        for t in ordenados[:8]:
            limpio = re.sub(r"[^0-9A-Za-zÁÉÍÓÚÑáéíóúñ]", "", t)
            if limpio:
                hashtags_validos.append(f"#{limpio}")
            if len(hashtags_validos) >= 5:
                break
        if hashtags_validos:
            lineas.append(" ".join(hashtags_validos))
            lineas.append("")

    disclaimer = guion.get("disclaimer", "")
    if disclaimer:
        lineas.append(f"⚠️ {disclaimer}")

    # Divulgación explícita de contenido generado con IA (auditoría agosto
    # 2026: descubrimos que el campo "containsSyntheticMedia" de la API de
    # YouTube NO se está guardando de verdad en los videos reales del canal
    # pese a que la llamada no da error -- limitación real de la API, no un
    # bug nuestro. Mientras eso se resuelve del lado de YouTube, dejamos
    # esta divulgación en texto, bien visible, como respaldo: es honesta,
    # cumple con lo que pide la política de contenido sintético, y además
    # reduce el riesgo de que el algoritmo "sospeche" de contenido no
    # declarado.
    lineas.append("")
    lineas.append("🤖 Este video usa guion, narración por voz y algunas imágenes generadas "
                  "o asistidas por inteligencia artificial, siempre basados en evidencia "
                  "científica real y verificada (ver referencias arriba).")

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
    # Límite subido de 15 a 20 (auditoría SEO élite, agosto 2026): analicé en
    # vivo las tags REALES -no públicas en la interfaz, solo vía API- de los
    # videos que mejor posicionan en el nicho (varios usan 18-29 tags,
    # incluyendo muchas variaciones long-tail tipo pregunta: "a que hora
    # tomar X", "como tomar X"). YouTube permite hasta 500 caracteres en
    # total, no un límite fijo de cantidad, así que subir el tope aprovecha
    # ese espacio en vez de dejarlo sin usar.
    resultado_final = []
    total_caracteres = 0
    for t in resultado[:20]:
        if total_caracteres + len(t) + 2 > 480:  # margen de seguridad bajo 500
            break
        resultado_final.append(t)
        total_caracteres += len(t) + 2
    return resultado_final

