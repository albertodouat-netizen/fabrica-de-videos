"""
AGENTE 27: CITAS CIENTÍFICAS EN PANTALLA ("CitasCientificas")
----------------------------------------------------------------
El usuario (auditoría agosto 2026) señaló un problema real y justo: aunque
agents/investigacion_cientifica.py YA busca estudios reales y verifica
cada cifra puntual contra ellos, en la práctica muchos videos terminan sin
mencionar NUNCA en voz alta que la información tiene respaldo científico,
sin mostrar en pantalla ningún documento/portada de estudio, y sin que el
espectador vea el enlace de la fuente en ningún momento salvo que abra la
descripción completa (que casi nadie hace). Esto le resta peso y
veracidad al canal, sobre todo siendo un canal de salud (tema "YMYL" -
Your Money or Your Life - donde Google/YouTube y el propio espectador
exigen más pruebas de que la información es confiable).

Por qué esto se hace en CÓDIGO y no se le deja solo al Guionista (LLM):
igual que con los 3 llamados a suscripción (ver agents/suscripcion_cta.py),
un LLM puede olvidarse de citar la fuente, citarla en un lugar raro, o
inventar una redacción distinta cada vez con distinto nivel de precisión.
Aquí se generan frases 100% deterministas (sin inventar NINGÚN dato nuevo:
solo se usa el nombre real de la revista y el año real, que ya vienen
verificados por agents/investigacion_cientifica.py) y se insertan siempre
en el mismo tipo de posición del video.

Qué hace, en concreto:
  1) Si el Investigador Científico encontró estudios reales sobre el tema
     (aunque ninguna cifra puntual del guion haya podido verificarse
     palabra por palabra), igual se insertan 1 o 2 "beats de cita" que
     mencionan en voz alta, de forma natural, que la información tiene
     respaldo científico real, con el nombre de la revista y el año
     reales. Esto es honesto: nunca se inventa un hallazgo, solo se
     comunica que SÍ existe un estudio real detrás (que además queda
     citado en la descripción con su enlace).
  2) Cada beat de cita usa una palabra clave visual de la lista
     DOCUMENTO_VISUALES (documentos, artículos científicos, informes,
     personas leyendo un estudio) para que el espectador vea en pantalla
     una toma real de "papel/documento científico", no solo una escena
     genérica sin relación con lo que se está diciendo.
  3) Se asegura de que esos estudios queden en guion["referencias"] (con
     su PMID verificado de verdad contra NCBI, igual que ya hace
     agents/investigacion_cientifica.py) para que su enlace aparezca
     siempre en la descripción de YouTube.
"""
import random

from agents.utils import log

AGENT = "CitasCientificas"

# Palabras clave visuales EN INGLÉS (para Pexels/Pixabay), 100% reales y
# filmables (nunca diagramas ni animaciones, según la regla del Estratega
# Viral): tomas de documentos, artículos, portadas de revistas científicas
# y personas leyendo o revisando estudios. Esto es justo lo que el usuario
# pidió: "que se muestren tomas de los documentos o portadas".
DOCUMENTO_VISUALES = [
    "close up of scientific research paper on desk",
    "person reading medical journal article closeup",
    "open medical journal pages close up",
    "researcher reviewing printed study report",
    "stack of scientific papers and documents on desk",
    "doctor reading clinical research document",
    "hands holding printed medical research report",
    "laboratory report on clipboard close up",
    "person highlighting text on a printed scientific article",
    "medical journal cover close up on wooden desk",
]

# Frases 100% deterministas (no las escribe el LLM): solo insertan datos
# YA verificados como reales (nombre de revista real, año real). Nunca se
# inventa un hallazgo ni una cifra nueva aquí.
FRASES_CON_REVISTA_Y_ANIO = [
    "Esto no es una opinión mía, es ciencia real. Estos hallazgos fueron publicados en la revista {revista}, en el año {anio}.",
    "Para que confíes en lo que te estoy contando, este dato viene de un estudio real, publicado en la revista {revista}, en {anio}.",
    "Vale la pena aclararlo, esta información tiene respaldo científico. Fue publicada en la revista {revista}, en el año {anio}.",
    "Si quieres revisarlo tú mismo, dejo el enlace al estudio original en la descripción. Fue publicado en la revista {revista}, en {anio}.",
]

FRASES_SOLO_REVISTA = [
    "Esto tiene respaldo científico real, publicado en la revista {revista}. Dejo el enlace al estudio original en la descripción.",
    "Este dato no me lo estoy inventando, proviene de una investigación real publicada en la revista {revista}.",
]

FRASES_GENERICAS = [
    "Esto tiene respaldo científico real y verificable, dejo el enlace al estudio original en la descripción para que lo revises tú mismo.",
    "Esta información no es solo una opinión, está basada en investigación científica real, con el enlace disponible en la descripción.",
]


def _elegir_visual_no_repetido(guion: dict, visuales_ya_asignados: set) -> str:
    """Evita repetir la misma palabra clave visual dos veces en el mismo
    guion (regla del Estratega Viral), revisando tanto los visuales que ya
    existían como los que este mismo agente ya haya asignado antes."""
    visuales_existentes = {
        b.get("visual", "").strip().lower()
        for cap in guion.get("capitulos", [])
        for b in cap.get("beats", [])
    }
    disponibles = [v for v in DOCUMENTO_VISUALES
                   if v.lower() not in visuales_existentes and v.lower() not in visuales_ya_asignados]
    if not disponibles:
        disponibles = DOCUMENTO_VISUALES  # respaldo: mejor repetir una vez que quedarse sin visual
    elegido = random.choice(disponibles)
    visuales_ya_asignados.add(elegido.lower())
    return elegido


def _texto_de_cita(estudio: dict) -> str:
    revista = (estudio.get("revista") or "").strip()
    anio = str(estudio.get("anio") or "").strip()
    if revista and anio:
        return random.choice(FRASES_CON_REVISTA_Y_ANIO).format(revista=revista, anio=anio)
    if revista:
        return random.choice(FRASES_SOLO_REVISTA).format(revista=revista)
    return random.choice(FRASES_GENERICAS)


def _construir_beat_cita(estudio: dict, visual: str) -> dict:
    autores = (estudio.get("autores") or "").strip()
    return {
        "texto": _texto_de_cita(estudio),
        "visual": visual,
        "es_cita_cientifica": True,
        "cifra_verificada": None,
        "cita_fuente": {
            "revista": (estudio.get("revista") or "").strip(),
            "anio": str(estudio.get("anio") or "").strip(),
            "autor_corto": autores.split(",")[0] if autores else "",
            "url": estudio.get("url", ""),
        },
        "_pmid": estudio.get("pmid"),
    }


def _elegir_estudios_para_citar(estudios: list, ya_citados_pmid: set, max_n: int = 2) -> list:
    """Prioriza estudios con revista Y año reales (cita más creíble en
    pantalla), evitando repetir uno que ya haya quedado citado por la
    verificación de cifras (agents/investigacion_cientifica.py)."""
    candidatos = [e for e in estudios if e.get("pmid") not in ya_citados_pmid]
    con_revista_y_anio = [e for e in candidatos if e.get("revista") and e.get("anio")]
    resto = [e for e in candidatos if e not in con_revista_y_anio]
    ordenados = con_revista_y_anio + resto
    return ordenados[:max_n]


def _insertar_en_capitulo(capitulos: list, indice_capitulo: int, beat_nuevo: dict):
    indice_capitulo = max(0, min(indice_capitulo, len(capitulos) - 1))
    cap = capitulos[indice_capitulo]
    beats = cap.setdefault("beats", [])
    # Se inserta después del primer beat del capítulo (nunca como primerísimo
    # beat, para no chocar con un llamado a suscripción que pueda ir ahí, ni
    # como último, para no chocar con el mini-gancho de cierre del capítulo).
    posicion = 1 if len(beats) > 1 else len(beats)
    beats.insert(posicion, beat_nuevo)


def agregar_citas_cientificas_en_guion(guion: dict, estudios: list) -> dict:
    """Punto de entrada de este agente. Si no hay estudios reales
    disponibles para el tema, no hace nada (mejor no citar nada que citar
    algo sin verificar; esto respeta la misma regla de honestidad de todo
    el proyecto)."""
    if not estudios:
        log(AGENT, "No hay estudios científicos reales disponibles para este tema: "
                    "no se insertan citas en pantalla (mejor así que inventar algo).")
        return guion

    capitulos = guion.get("capitulos", [])
    if len(capitulos) < 1:
        return guion

    # PMIDs que ya quedaron citados por la verificación de cifras puntuales
    # (agents/investigacion_cientifica.verificar_y_filtrar_guion), para no
    # citar el mismo estudio dos veces de formas distintas en el video.
    ya_citados_pmid = {r.get("pmid") for r in guion.get("referencias", [])}

    estudios_a_citar = _elegir_estudios_para_citar(estudios, ya_citados_pmid, max_n=2)
    if not estudios_a_citar:
        return guion

    # Verificación real ANTES de citar en voz alta (no después): mismo
    # criterio de honestidad que el resto del proyecto. Si el PMID no se
    # puede confirmar contra NCBI, mejor no citar ese estudio en absoluto
    # (ni en audio ni en descripción) que mencionar una fuente que no se
    # pudo verificar del todo.
    from agents.investigacion_cientifica import pmid_es_real
    estudios_verificados = []
    for estudio in estudios_a_citar:
        pmid = estudio.get("pmid")
        if pmid and pmid_es_real(pmid, estudio.get("titulo", "")):
            estudios_verificados.append(estudio)
        else:
            log(AGENT, f"Estudio candidato a citar descartado: el PMID {pmid} no se pudo "
                        f"confirmar como real contra NCBI.")
    if not estudios_verificados:
        log(AGENT, "Ningún estudio candidato pasó la verificación real contra NCBI: "
                    "no se insertan citas en pantalla para este video.")
        return guion

    visuales_asignados = set()

    # Posiciones aproximadas: una cita cerca del primer cuarto del video
    # (refuerza credibilidad temprano, sin debilitar el gancho inicial) y,
    # si hay una segunda, cerca de los dos tercios (antes del cierre).
    n = len(capitulos)
    posiciones = [max(1, n // 4)]
    if len(estudios_verificados) > 1:
        posiciones.append(max(posiciones[0] + 1, (n * 2) // 3))

    referencias_nuevas = list(guion.get("referencias", []))
    citas_insertadas = 0
    for estudio, indice_cap in zip(estudios_verificados, posiciones):
        visual = _elegir_visual_no_repetido(guion, visuales_asignados)
        beat_cita = _construir_beat_cita(estudio, visual)
        _insertar_en_capitulo(capitulos, indice_cap, beat_cita)
        citas_insertadas += 1

        pmid = estudio.get("pmid")
        if pmid and pmid not in ya_citados_pmid:
            referencias_nuevas.append(estudio)
            ya_citados_pmid.add(pmid)

    guion["referencias"] = referencias_nuevas
    log(AGENT, f"{citas_insertadas} cita(s) científica(s) real(es) insertada(s) en el video "
                f"(mención en voz alta + toma de documento/estudio en pantalla + enlace real "
                f"en la descripción).")
    return guion
