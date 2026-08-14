"""
AGENTE 3: NARRADOR ("Voice Agent")
----------------------------------------------------
100% GRATIS y SIN API KEY: usa edge-tts (motor de voces neuronales de
Microsoft Edge expuesto públicamente). Reemplaza a ElevenLabs (de pago)
que se usaba en el video original.

CAMBIO IMPORTANTE (auditoría agosto 2026, comentario real de un experto en
tráfico de YouTube): antes se narraba TODO un capítulo de un tirón, en una
sola llamada a la IA de voz, y se ESTIMABA cuánto duraba cada beat según su
cantidad de letras. Eso sonaba corrido/monótono (sin pausas reales entre
ideas) y desalineaba un poco los cortes visuales con lo que se narraba de
verdad. Ahora cada beat se narra POR SEPARADO, con una pausa real y breve
entre uno y otro (como respiraría un narrador humano entre frases), y la
duración de cada uno ya no se estima: se MIDE de verdad con el archivo de
audio real. Esto también deja los cortes visuales perfectamente
sincronizados con el audio real, no una aproximación.
"""
import asyncio
import os
import random
import edge_tts
from mutagen.mp3 import MP3
from moviepy import AudioFileClip, AudioClip, concatenate_audioclips

from agents.utils import load_config, log

AGENT = "Narrador"

# Grupo de voces entre las que se elige AL AZAR para cada video nuevo (dan
# variedad al canal: no todos los videos "suenan igual", lo cual además
# ayuda a que YouTube no perciba el canal como contenido plantillado/repetitivo).
VOCES_POOL_DEFECTO = ["es-CO-GonzaloNeural", "es-MX-JorgeNeural", "es-US-AlonsoNeural", "es-MX-DaliaNeural"]

# Cuando el guion es exclusivo para audiencia femenina (guion["audiencia_exclusiva"]
# == "mujeres"), se usa SIEMPRE esta voz, sin aleatoriedad, sin excepción.
VOZ_EXCLUSIVA_MUJERES_DEFECTO = "es-MX-DaliaNeural"

# Pausa real entre beats (segundos): simula la respiración/silencio natural
# que deja un narrador humano entre una idea y la siguiente. Sin esto, el
# texto sonaba "todo pegado" aunque tuviera comas y puntos.
PAUSA_ENTRE_BEATS_SEG = 0.35
# Pausa un poco más larga entre el gancho y el primer beat de contenido
# (un respiro más notorio, como el que se usa al empezar a explicar algo).
PAUSA_TRAS_GANCHO_SEG = 0.55


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


def _asegurar_puntuacion(texto: str) -> str:
    """Si un beat llegó sin signo de puntuación final (a veces pasa con
    guiones de IA), le agrega un punto. Sin esto, edge-tts a veces no deja
    ninguna pausa natural al unir ese beat con el siguiente."""
    texto = texto.strip()
    if texto and texto[-1] not in ".?!…":
        texto += "."
    return texto


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


def _concatenar_con_pausas(rutas_mp3: list, pausas_seg: list, salida_mp3: str) -> None:
    """Une varios archivos de audio ya generados, insertando un silencio
    real (no solo puntuación) entre cada uno. 'pausas_seg[i]' es la pausa
    que va DESPUÉS del audio i (la última entrada se ignora)."""
    clips = []
    abiertos = []
    for idx, ruta in enumerate(rutas_mp3):
        clip = AudioFileClip(ruta)
        abiertos.append(clip)
        clips.append(clip)
        if idx < len(rutas_mp3) - 1:
            pausa = pausas_seg[idx] if idx < len(pausas_seg) else PAUSA_ENTRE_BEATS_SEG
            silencio = AudioClip(lambda t: 0, duration=pausa, fps=24000)
            clips.append(silencio)

    combinado = concatenate_audioclips(clips)
    combinado.write_audiofile(salida_mp3, logger=None)
    combinado.close()
    for c in abiertos:
        try:
            c.close()
        except Exception:
            pass


def narrar_guion(guion: dict, carpeta_salida: str, nombre_base: str) -> dict:
    cfg = load_config()
    voz = _elegir_voz(guion, cfg)
    rate = cfg["apis"].get("voz_narrador_rate", "-8%")
    pitch = cfg["apis"].get("voz_narrador_pitch", "+0Hz")
    os.makedirs(carpeta_salida, exist_ok=True)

    capitulos_info = []

    for i, cap in enumerate(guion["capitulos"]):
        beats = cap.get("beats", [])
        textos_beats = [_asegurar_puntuacion(b["texto"]) for b in beats]
        if i == 0 and guion.get("gancho"):
            textos_beats = [_asegurar_puntuacion(guion["gancho"])] + textos_beats

        log(AGENT, f"Narrando capítulo {i+1}/{len(guion['capitulos'])}: {cap['nombre']} "
                    f"({len(beats)} beats, cada uno por separado con pausas reales)...")

        # Cada beat se sintetiza POR SEPARADO: así la duración de cada uno
        # se MIDE de verdad (no se estima por letras) y se puede insertar
        # una pausa real y controlada entre ideas.
        rutas_beats_mp3 = []
        duraciones_habla = []
        for k, texto in enumerate(textos_beats):
            ruta_beat = os.path.join(carpeta_salida, f"{nombre_base}_cap{i}_beat{k}.mp3")
            asyncio.run(_sintetizar(texto, voz, ruta_beat, rate=rate, pitch=pitch))
            rutas_beats_mp3.append(ruta_beat)
            duraciones_habla.append(_duracion_mp3(ruta_beat))

        pausas = [PAUSA_TRAS_GANCHO_SEG if (k == 0 and i == 0 and guion.get("gancho"))
                  else PAUSA_ENTRE_BEATS_SEG for k in range(len(rutas_beats_mp3))]

        salida = os.path.join(carpeta_salida, f"{nombre_base}_cap{i}.mp3")
        _concatenar_con_pausas(rutas_beats_mp3, pausas, salida)
        duracion_total = _duracion_mp3(salida)  # duración REAL ya con las pausas incluidas

        # Cada beat "dura" su audio real + la pausa que le sigue (excepto el
        # último, que no lleva pausa después dentro de este capítulo). Esto
        # deja los cortes visuales alineados con el audio real, milímetro a
        # milímetro, en vez de una aproximación por cantidad de letras.
        duraciones_beats = [duraciones_habla[k] + (pausas[k] if k < len(rutas_beats_mp3) - 1 else 0.0)
                             for k in range(len(rutas_beats_mp3))]

        # Limpieza: ya no hacen falta los mp3 individuales por beat, solo el
        # del capítulo completo (ya concatenado).
        for ruta in rutas_beats_mp3:
            try:
                os.remove(ruta)
            except OSError:
                pass

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
