"""
AGENTE 3: NARRADOR ("Voice Agent")
----------------------------------------------------
100% GRATIS y SIN API KEY: usa edge-tts (motor de voces neuronales de
Microsoft Edge expuesto públicamente). Reemplaza a ElevenLabs (de pago)
que se usaba en el video original.

Narra el texto completo de cada capítulo (para que la voz suene natural y
fluida) pero calcula, para cada "beat" dentro del capítulo, cuánto dura
aproximadamente su porción de audio (proporcional a su cantidad de
caracteres). Esto le permite al EditorVideo cortar a un clip visual nuevo
cada pocos segundos, sincronizado con lo que se está narrando en ese
momento, en vez de sostener una sola imagen/clip por mucho tiempo.
"""
import asyncio
import os
import random
import edge_tts
from mutagen.mp3 import MP3

from agents.utils import load_config, log

AGENT = "Narrador"

# Grupo de voces entre las que se elige AL AZAR para cada video nuevo (dan
# variedad al canal: no todos los videos "suenan igual", lo cual además
# ayuda a que YouTube no perciba el canal como contenido plantillado/repetitivo).
VOCES_POOL_DEFECTO = ["es-CO-GonzaloNeural", "es-MX-JorgeNeural", "es-US-AlonsoNeural", "es-MX-DaliaNeural"]

# Cuando el guion es exclusivo para audiencia femenina (guion["audiencia_exclusiva"]
# == "mujeres"), se usa SIEMPRE esta voz, sin aleatoriedad, sin excepción.
VOZ_EXCLUSIVA_MUJERES_DEFECTO = "es-MX-DaliaNeural"


def _elegir_voz(guion: dict, cfg: dict) -> str:
    pool = cfg["apis"].get("voz_narrador_pool") or VOCES_POOL_DEFECTO
    voz_mujeres = cfg["apis"].get("voz_narrador_exclusiva_mujeres", VOZ_EXCLUSIVA_MUJERES_DEFECTO)
    audiencia = (guion.get("audiencia_exclusiva") or "").strip().lower()

    if audiencia in ("mujer", "mujeres", "femenino", "femenina"):
        log(AGENT, f"Video de audiencia EXCLUSIVA femenina: se usa siempre '{voz_mujeres}' (sin azar).")
        return voz_mujeres

    voz = random.choice(pool)
    log(AGENT, f"Voz elegida al azar para este video (de {len(pool)} disponibles): {voz}")
    return voz


async def _sintetizar(texto: str, voz: str, salida_mp3: str, rate: str = "-8%", pitch: str = "+0Hz"):
    # rate="-8%": las voces neuronales por defecto narran un poco más rápido
    # de lo que se ve natural/cálido en un video hablado; bajar el ritmo un
    # 8% (investigado empíricamente) sin tocar el tono sigue sonando a la
    # misma persona, pero se percibe más pausada y natural, no leída de corrido.
    comunicador = edge_tts.Communicate(texto, voice=voz, rate=rate, pitch=pitch)
    await comunicador.save(salida_mp3)


def _duracion_mp3(ruta_mp3: str) -> float:
    try:
        return MP3(ruta_mp3).info.length
    except Exception:
        # Respaldo aproximado si mutagen fallara por algún motivo
        return max(1.0, os.path.getsize(ruta_mp3) / 4000)


def narrar_guion(guion: dict, carpeta_salida: str, nombre_base: str) -> dict:
    cfg = load_config()
    voz = _elegir_voz(guion, cfg)
    rate = cfg["apis"].get("voz_narrador_rate", "-8%")
    pitch = cfg["apis"].get("voz_narrador_pitch", "+0Hz")
    os.makedirs(carpeta_salida, exist_ok=True)

    capitulos_info = []

    for i, cap in enumerate(guion["capitulos"]):
        beats = cap.get("beats", [])
        texto_capitulo = cap.get("gancho_previo", "") if i == 0 and "gancho" in guion else ""
        # El gancho se narra pegado al inicio del primer capítulo para no
        # generar un archivo de audio adicional/una pausa extraña.
        textos_beats = [b["texto"] for b in beats]
        if i == 0 and guion.get("gancho"):
            textos_beats = [guion["gancho"]] + textos_beats

        texto_capitulo_completo = " ".join(textos_beats).strip()
        salida = os.path.join(carpeta_salida, f"{nombre_base}_cap{i}.mp3")

        log(AGENT, f"Narrando capítulo {i+1}/{len(guion['capitulos'])}: {cap['nombre']} "
                    f"({len(beats)} beats)")
        asyncio.run(_sintetizar(texto_capitulo_completo, voz, salida, rate=rate, pitch=pitch))

        duracion_total = _duracion_mp3(salida)

        # Repartimos la duración real del audio entre los beats, proporcional
        # a la cantidad de caracteres de cada uno (aproximación robusta y
        # gratuita; no requiere marcas de tiempo palabra por palabra).
        pesos = [max(1, len(t)) for t in textos_beats]
        total_pesos = sum(pesos)
        duraciones_beats = [duracion_total * (p / total_pesos) for p in pesos]

        # Si agregamos el gancho al primer capítulo, esa duración extra no
        # corresponde a ningún beat real del guion original: la fusionamos
        # con la duración del primer beat para no desalinear la lista.
        if i == 0 and guion.get("gancho"):
            duraciones_beats = [duraciones_beats[0] + duraciones_beats[1] if len(duraciones_beats) > 1
                                 else duraciones_beats[0]] + duraciones_beats[2:]

        capitulos_info.append({
            "audio": salida,
            "duracion_total": duracion_total,
            "duraciones_beats": duraciones_beats,
        })

    return {"capitulos": capitulos_info, "voz_usada": voz}


if __name__ == "__main__":
    from agents.trend_scout import buscar_ideas_potenciales
    from agents.scriptwriter import generar_guion

    idea = buscar_ideas_potenciales()[0]
    guion = generar_guion(idea)
    resultado = narrar_guion(guion, "output/audio", "demo")
    for c in resultado["capitulos"]:
        print(c["audio"], round(c["duracion_total"], 1), [round(d, 1) for d in c["duraciones_beats"]])
