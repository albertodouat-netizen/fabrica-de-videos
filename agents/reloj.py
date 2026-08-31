"""
RELOJ GLOBAL DE LA CORRIDA ("deadline duro")
============================================
Nace de la auditoría del 31-ago-2026: TRES corridas seguidas murieron en
el tope de 5h de GitHub Actions SIN publicar. Causa: sin un límite de
tiempo global, los reintentos por-beat (Pollinations 429, Gemini 429,
colas ZSky, regeneraciones de la barrera cero-repeticiones) se acumulan
sin techo. Un video imperfecto PUBLICADO vale infinitamente más que un
video perfecto CANCELADO.

Uso:
    from agents.reloj import apurado, tiempo_restante_min
    if apurado():   # True cuando quedan menos de RESERVA para el render
        ...saltar extras, ir directo a terminar...

El reloj arranca cuando el orquestador importa este módulo (primer import
del proceso). PRESUPUESTO_MINUTOS por defecto 120: a partir de ahí, TODOS
los agentes entran en "modo apurado" (cero reintentos, cero verificaciones
opcionales, cero clips IA nuevos) y el pipeline corre directo al render y
la publicación. Con render (~40-60 min) + subida, cabe siempre en las 5h
con margen enorme.
"""
import os
import time

_INICIO = time.time()

PRESUPUESTO_MINUTOS = float(os.environ.get("PRESUPUESTO_MINUTOS", "120"))


def minutos_transcurridos() -> float:
    return (time.time() - _INICIO) / 60.0


def tiempo_restante_min() -> float:
    return max(0.0, PRESUPUESTO_MINUTOS - minutos_transcurridos())


def apurado() -> bool:
    """True cuando el presupuesto de generación se agotó: los agentes deben
    dejar de intentar extras y terminar con lo que hay."""
    return minutos_transcurridos() >= PRESUPUESTO_MINUTOS


def muy_apurado() -> bool:
    """True 30 min después del presupuesto: ni siquiera reintentos simples."""
    return minutos_transcurridos() >= PRESUPUESTO_MINUTOS + 30
