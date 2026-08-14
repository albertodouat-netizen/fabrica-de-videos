"""
AGENTE 25: LLAMADO A INTERACCIÓN ("EngagementCTA")
----------------------------------------------------
El usuario pidió motivar/persuadir a que la gente comente, comparta el
video, y algo tipo "se recompense" la interacción.

Investigación real antes de construir esto (para no arriesgar el canal):
la política oficial de YouTube ("Fake engagement policy") dice EXPLÍCITAMENTE
dos cosas que hay que tomar en serio:
  1) "You're allowed to encourage viewers to subscribe, hit the like button,
     share, or leave a comment." -> Pedir directamente que comenten,
     compartan o den like SÍ está permitido, sin problema.
  2) "Content that solely exists to incentivize viewers for engagement
     (views, likes, comments, etc) is prohibited" -> Un sorteo, premio o
     truco tipo "comenta o no tendrás suerte" SÍ está prohibido y puede
     costar el canal.

Por eso este agente NUNCA promete premios, sorteos ni trucos. En su lugar,
usa las 2 técnicas que la investigación de 2026 muestra que sí funcionan y
sí son 100% permitidas:
  - Una PREGUNTA ESPECÍFICA relacionada con el tema exacto del video (no
    genérica tipo "comenta algo"), que invita a compartir una experiencia
    real. Esto es lo que de verdad genera comentarios de calidad (y los
    comentarios pesan más que los likes para el algoritmo de YouTube).
  - Un pedido directo de compartir, enfocado en ayudar a alguien más (no en
    "hazme un favor"), que es la forma de pedir que comparte más funciona
    sin sonar a manipulación.

Se agrega como UN beat más, después del contenido del video y antes del
llamado final a suscripción (ver agents/suscripcion_cta.py ->
insertar_antes_del_cierre), para no competir con el cierre principal.
"""
import random

from agents.utils import log

AGENT = "EngagementCTA"

# {tema} se reemplaza por la keyword_principal del guion, para que la
# pregunta se sienta específica del video y no una plantilla genérica
# (que es justo lo que la política de "contenido inauténtico" penaliza).
PLANTILLAS_COMENTARIO = [
    "Cuéntame en los comentarios, ¿ya intentaste algo relacionado con {tema}? Me gustaría saber cómo te fue.",
    "Te leo en los comentarios, ¿cuál de estos puntos sobre {tema} te llamó más la atención?",
    "Escribe en los comentarios qué parte de esto sobre {tema} vas a probar primero, así lo recuerdas.",
    "Si tienes una pregunta sobre {tema} que no resolví aquí, escríbela en los comentarios y la reviso.",
]

PLANTILLAS_COMPARTIR = [
    "Si conoces a alguien a quien esto sobre {tema} le pueda servir, comparte este video con esa persona.",
    "Comparte este video con alguien que también esté buscando mejorar su {tema}, seguro se lo va a agradecer.",
    "Guarda este video para consultarlo cuando lo necesites, y compártelo con quien creas que le puede ayudar.",
]


def agregar_llamado_interaccion(guion: dict) -> dict:
    """Inserta SIEMPRE un beat con (a) una pregunta específica para generar
    comentarios reales y (b) un pedido directo de compartir. Ambos 100%
    permitidos por la política de YouTube (nunca se ofrece premio ni
    sorteo a cambio)."""
    capitulos = guion.get("capitulos", [])
    if not capitulos:
        return guion

    tema = (guion.get("keyword_principal") or "tu salud").strip()
    pregunta = random.choice(PLANTILLAS_COMENTARIO).format(tema=tema)
    compartir = random.choice(PLANTILLAS_COMPARTIR).format(tema=tema)

    beat = {
        "texto": f"{pregunta} {compartir}",
        "visual": "person smiling and typing on smartphone at home",
        "es_llamado_interaccion": True,
    }

    from agents.suscripcion_cta import insertar_antes_del_cierre
    cap_final = capitulos[-1]
    insertar_antes_del_cierre(cap_final.setdefault("beats", []), beat)

    log(AGENT, "Llamado a comentar y compartir agregado (pregunta específica, "
                "sin premios ni sorteos, cumple la política de YouTube).")
    return guion
