"""
AGENTE 22: LLAMADOS A SUSCRIPCIÓN GARANTIZADOS ("SuscripcionCTA")
------------------------------------------------------------------
El usuario pidió que TODOS los videos, sin excepción, tengan 3 momentos
pidiendo que se suscriban: uno al inicio, uno a la mitad y uno al final.

Por qué esto NO se le pide simplemente al Guionista (LLM) y ya:
un modelo de lenguaje puede olvidarlo, ponerlo en un lugar raro, o
redactarlo distinto de calidad cada vez. Como esto es una regla de negocio
NO NEGOCIABLE ("siempre", según el usuario), se implementa aquí de forma
determinística en código, después de que el guion ya está listo: así
funciona 100% de las veces, sin depender de que la IA "se acuerde".

Cada llamado:
  - Es un beat más (mismo formato que el resto), así que se integra solo
    con Narrador, VisualScout, EditorVideo, Subtítulos, etc.
  - Se elige AL AZAR entre varias redacciones distintas (nunca la misma
    frase en todos los videos) para que el canal no se sienta "plantillado"
    -- justo lo que la política de "contenido inauténtico" de YouTube
    penaliza (investigado en este proyecto).
  - Usa el marcador especial de agents/avatar_presentador.py como palabra
    visual, para que en pantalla aparezca el presentador fijo del canal
    pidiendo la suscripción (rostro humano real, consistente en todos los
    videos) en vez de un clip de stock genérico.
  - Queda marcado con beat["es_llamado_suscripcion"] = True para que otros
    agentes (QA-Coherencia, ShortsCreator) lo reconozcan y lo traten aparte.
"""
import random

from agents.avatar_presentador import MARCADOR_VISUAL_CTA
from agents.utils import log

AGENT = "SuscripcionCTA"

FRASES_INICIO = [
    "Antes de seguir, un segundo. Si te interesa cuidarte de forma natural, suscríbete gratis al canal ahora mismo.",
    "Dato rápido antes de empezar. Suscribirte es gratis y así no te pierdes los próximos videos de salud natural.",
    "Si es tu primera vez aquí, dale a suscribirte. Publicamos contenido nuevo sobre salud natural todos los días.",
    "Antes de entrar de lleno al tema, suscríbete al canal. Es gratis y te va a servir para lo que viene.",
]

FRASES_MITAD = [
    "Si este video te está sirviendo hasta ahora, aprovecha y suscríbete, así no te pierdes el resto.",
    "Vamos a la mitad. Si te gusta lo que estás aprendiendo, suscríbete al canal, es gratis y ayuda mucho.",
    "Antes de seguir con la siguiente parte, un favor rápido, suscríbete al canal si te está gustando el video.",
    "Seguimos. Si quieres más contenido como este, suscribirte es la mejor forma de asegurarte de verlo.",
]

FRASES_FINAL = [
    "Si llegaste hasta aquí, este contenido es para ti. Suscríbete gratis para el próximo video sobre salud natural.",
    "Eso fue todo por hoy. Suscríbete al canal para no perderte los próximos videos, es completamente gratis.",
    "Espero que te haya servido. Antes de irte, suscríbete al canal, así vuelves a encontrar contenido como este.",
    "Gracias por ver hasta el final. Suscríbete gratis al canal, así seguimos ayudándote a cuidar tu salud de forma natural.",
]


def _beat_cta(texto: str, momento: str) -> dict:
    return {
        "texto": texto,
        "visual": MARCADOR_VISUAL_CTA,
        "es_llamado_suscripcion": True,
        "momento_suscripcion": momento,
    }


def agregar_llamados_a_suscripcion(guion: dict) -> dict:
    """Inserta, SIEMPRE y de forma determinística, 3 beats de llamado a
    suscripción: inicio (primer capítulo), mitad (capítulo central) y
    final (último capítulo). No depende de que el LLM lo haya incluido."""
    capitulos = guion.get("capitulos", [])
    if not capitulos:
        return guion

    # --- INICIO: justo después del gancho, como primer beat del capítulo 1.
    # Se pone ahí (no antes del gancho) para no debilitar el gancho, que es
    # lo que retiene al espectador en los primeros segundos.
    cap_inicio = capitulos[0]
    cap_inicio.setdefault("beats", []).insert(0, _beat_cta(random.choice(FRASES_INICIO), "inicio"))

    # --- MITAD: al principio del capítulo que queda más cerca de la mitad
    # del video (si solo hay 1 capítulo, se reutiliza el mismo capítulo,
    # pero se inserta DESPUÉS del llamado de inicio para mantener el orden
    # cronológico correcto dentro del video).
    indice_mitad = len(capitulos) // 2
    if indice_mitad == 0 and len(capitulos) > 1:
        indice_mitad = 1
    cap_mitad = capitulos[indice_mitad]
    posicion_mitad = 1 if cap_mitad is cap_inicio else 0
    cap_mitad.setdefault("beats", []).insert(posicion_mitad, _beat_cta(random.choice(FRASES_MITAD), "mitad"))


    # --- FINAL: al final del último capítulo.
    cap_final = capitulos[-1]
    cap_final.setdefault("beats", []).append(_beat_cta(random.choice(FRASES_FINAL), "final"))

    log(AGENT, "Los 3 llamados obligatorios a suscripción quedaron insertados "
                "(inicio, mitad y final), con el presentador del canal en pantalla.")
    return guion
