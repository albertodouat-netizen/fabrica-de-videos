"""
AGENTE 23: PRESUPUESTO DIARIO DE IA GRATUITA ("PresupuestoIA")
----------------------------------------------------------------
Descubrimiento real de esta auditoría (agosto 2026): el proyecto de Google
Cloud usado para la llave gratuita de Gemini tiene, en la práctica, una
cuota de apenas 20 solicitudes/día para el modelo gemini-2.5-flash
(confirmado con una llamada real que devolvió el error 429
"RESOURCE_EXHAUSTED... limit: 20"). Antes de este agente, el sistema no se
enteraba de esto hasta que ya había gastado esa cuota en verificaciones de
coherencia visual (QA-Coherencia llama a Gemini una vez POR CADA beat, y un
video largo puede tener 40-70 beats), dejando sin cupo al Guionista para el
resto del día -> el pipeline caía al generador de plantilla local (sin IA),
produciendo videos genéricos y cortos. Esto es justamente el patrón que la
política de "contenido inauténtico" de YouTube (julio 2026) penaliza.

Este agente lleva la cuenta de cuántas llamadas a Gemini se han hecho HOY
(persistido en data/estado.json, así sobrevive entre agentes y entre
ejecuciones del mismo día) y dictamina cuántas le quedan disponibles a
quien pregunte, para que el sistema decida usar ese cupo donde más importa
(el guion) en vez de gastarlo todo verificando imágenes.
"""
import datetime as dt

from agents.utils import load_state, save_state, log

AGENT = "PresupuestoIA"

# Un poco por debajo del límite real observado (20/día), para dejar margen
# de seguridad (el límite exacto puede variar según el proyecto/momento).
LIMITE_DIARIO_GEMINI_CONSERVADOR = 16

# Cupo que SIEMPRE se reserva para el Guionista y la verificación científica
# (lo más importante: un guion real vale más que verificar todas las
# imágenes). QA-Coherencia solo puede usar lo que sobre de esta reserva.
RESERVA_PARA_GUION_Y_CIENCIA = 6


def _fecha_hoy_utc() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%d")


def _leer_contador(estado: dict) -> dict:
    contador = estado.get("uso_gemini", {})
    if contador.get("fecha") != _fecha_hoy_utc():
        contador = {"fecha": _fecha_hoy_utc(), "usados": 0}
    return contador


def gemini_usados_hoy() -> int:
    estado = load_state()
    return _leer_contador(estado)["usados"]


def registrar_uso_gemini(cantidad: int = 1) -> None:
    """Súmalo SOLO después de una llamada que de verdad respondió 200 (una
    llamada rechazada con 429 no gastó cuota real, así que no cuenta)."""
    estado = load_state()
    contador = _leer_contador(estado)
    contador["usados"] = contador.get("usados", 0) + cantidad
    estado["uso_gemini"] = contador
    save_state(estado)


def gemini_disponibles_para_qa() -> int:
    """Cuántas llamadas de Gemini le quedan disponibles a QA-Coherencia
    HOY, después de reservar cupo para el Guionista y la ciencia. Nunca
    negativo."""
    usados = gemini_usados_hoy()
    restante_total = max(0, LIMITE_DIARIO_GEMINI_CONSERVADOR - usados)
    disponible_qa = max(0, restante_total - RESERVA_PARA_GUION_Y_CIENCIA)
    return disponible_qa


def avisar_estado(agent_name: str) -> None:
    usados = gemini_usados_hoy()
    log(agent_name, f"Uso de Gemini hoy: {usados}/{LIMITE_DIARIO_GEMINI_CONSERVADOR} "
                     f"(cupo conservador; el límite real observado del proyecto es 20/día).")
