"""
AGENTE 26: MODERACIÓN VISUAL / CONTENIDO SEGURO ("ModeracionVisual")
----------------------------------------------------------------------
Hallazgo real (agosto 2026): un video publicado incluyó un clip de stock
de "masaje" con la espalda/hombros descubiertos en primer plano --
descubierto por el propio dueño del canal viendo el video ya publicado.
Se investigó descargando el video real y revisando los fotogramas:
confirmado, el clip venía de un banco de stock (Pexels/Pixabay) para una
keyword relacionada con "relajación muscular", y ningún filtro existente
lo bloqueaba.

HONESTIDAD TÉCNICA IMPORTANTE (para que quede documentado, no se oculta):
la primera versión de este agente intentó un filtro automático basado en
detectar "proporción de piel" por color de píxeles (primero en RGB, luego
en YCbCr). Se probó rigurosamente contra el fotograma real problemático Y
contra fotogramas normales del mismo video (manos con frascos, rostros,
comida). Resultado real de la prueba: el heurístico de color NO distingue
bien piel real de fondos cálidos/beige/rosados -- una foto de un frasco de
pastillas sobre fondo rosa midió MÁS "piel" (86%) que el clip real del
masaje (52-55%). Un filtro que no discrimina bien es peor que no tener
filtro (da falsa confianza), así que se DESCARTÓ esa idea en vez de
dejarla a medias.

La solución real que sí funciona, en 2 capas:
  1) Lista negra de palabras (determinística, sin falsos negativos posibles
     para los términos que sí contiene): nunca se busca ni se genera
     contenido con términos de riesgo, y si un resultado de Pexels/Pixabay
     trae esos términos en su descripción/tags, se descarta ANTES de
     descargarlo, aunque coincidiera bien con la keyword pedida.
  2) Gemini Vision (ya integrado en agents/qa_coherencia.py para verificar
     coherencia) ahora TAMBIÉN pregunta explícitamente si la imagen
     contiene desnudos o contenido inapropiado, en la MISMA llamada que ya
     se hacía (no consume cuota extra de Gemini). Esto sí es una
     verificación semántica real hecha por un modelo que entiende el
     contenido de la imagen, no una aproximación de color.
  3) Los prompts de generación de imágenes con IA (Pollinations) piden
     explícitamente ropa apropiada / nada de desnudos en cada generación,
     y el Guionista tiene prohibido sugerir escenas de masaje/spa/piel
     descubierta desde el origen (ver agents/viral_strategist.py).
"""
PALABRAS_INSEGURAS = [
    # Desnudos / contenido explícito
    "nude", "naked", "nudity", "topless", "desnud", "desnuda", "desnudo",
    "sin ropa", "sensual", "erotic", "erótic", "sexy", "provocative",
    # Masajes / spa con piel descubierta (causa real detectada)
    "massage", "masaje", "spa treatment", "bare back", "bare shoulders",
    "shirtless", "sin camisa", "torso desnudo", "espalda desnuda",
    # Ropa de baño / lencería (alto riesgo de imágenes no aptas)
    "bikini", "swimsuit", "traje de baño", "lingerie", "lenceria", "lencería",
    "underwear", "ropa interior", "bra only", "in bed together",
]


def es_texto_inseguro(texto: str) -> bool:
    """Revisa un texto (descripción/tags de un resultado de Pexels/Pixabay,
    o una palabra clave que se esté por buscar/generar) contra la lista
    negra. Siempre en minúsculas para que la comparación no falle por
    mayúsculas/acentos raros. Esta comparación de texto SÍ es 100%
    confiable para los términos que contiene (a diferencia del heurístico
    de color que se probó y se descartó, ver docstring del módulo)."""
    if not texto:
        return False
    texto_normalizado = texto.lower()
    return any(palabra in texto_normalizado for palabra in PALABRAS_INSEGURAS)
