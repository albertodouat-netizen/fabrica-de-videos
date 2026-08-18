"""
AGENTE 33: MÚSICA DE LA INTRO ("MusicaIntro")
----------------------------------------------
Pedido del usuario (19-ago-2026): la intro de marca (logo + promesa
científica, ver agents/intro_marca.py) debe llevar una música de fondo
relajante estilo meditación.

Doble vía, siempre gratis:
  1) JAMENDO (si hay client_id configurado): busca pistas con licencia
     comercial de tags meditation/ambient/zen y usa una al azar.
  2) RESPALDO LOCAL SINTETIZADO (siempre disponible, sin internet ni
     licencias): genera un "pad" ambiental suave con acordes largos
     (progresión C - Am - F - G con armónicos suaves y fundido de
     entrada/salida), estilo cuenco de meditación. Es determinista,
     100% original (generado matemáticamente, sin copyright de terceros)
     y suena limpio bajo la voz.

DESCUBRIMIENTO de la auditoría de este mismo día: el jamendo_client_id
nunca fue configurado (placeholder), así que TODOS los videos publicados
hasta ahora salieron sin música de fondo general. Este módulo garantiza
que al menos la intro siempre tenga su música, con o sin Jamendo.
"""
import math
import os
import random
import struct
import wave

from agents.utils import load_config, log

AGENT = "MusicaIntro"

TAGS_MEDITACION = ["meditation", "ambient", "zen", "relaxation"]


def _buscar_jamendo_meditacion(client_id: str, carpeta_salida: str):
    """Intenta descargar una pista de meditación de Jamendo (licencia
    comercial). Devuelve ruta o None."""
    import requests
    try:
        tag = random.choice(TAGS_MEDITACION)
        r = requests.get("https://api.jamendo.com/v3.0/tracks/", params={
            "client_id": client_id, "format": "json", "limit": 10,
            "tags": tag, "audioformat": "mp32", "include": "licenses",
            "ccnc": "false", "ccnd": "false"}, timeout=30)
        r.raise_for_status()
        pistas = r.json().get("results", [])
        if not pistas:
            return None
        pista = random.choice(pistas)
        destino = os.path.join(carpeta_salida, "musica_intro.mp3")
        rr = requests.get(pista["audio"], stream=True, timeout=60)
        rr.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in rr.iter_content(chunk_size=1 << 16):
                f.write(chunk)
        log(AGENT, f"Música de intro desde Jamendo: '{pista.get('name','')}' "
                    f"de {pista.get('artist_name','')} (tag {tag}).")
        return destino
    except Exception as e:
        log(AGENT, f"Aviso: Jamendo no disponible para la música de intro ({e}).")
        return None


def _sintetizar_pad_meditacion(destino_wav: str, duracion: float = 14.0,
                                sample_rate: int = 44100) -> str:
    """Pad ambiental suave generado localmente: acordes C-Am-F-G con
    senos y armónicos de baja intensidad, ataque lento y fundidos.
    100% original y libre de derechos (es matemática, no una obra ajena)."""
    # Acordes (frecuencias fundamentales, octava baja para calidez)
    acordes = [
        [130.81, 164.81, 196.00],   # C3 mayor (C-E-G)
        [110.00, 130.81, 164.81],   # A2 menor (A-C-E)
        [87.31, 130.81, 174.61],    # F2 mayor (F-C-F3)
        [98.00, 123.47, 146.83],    # G2 mayor (G-B-D)
    ]
    n_total = int(duracion * sample_rate)
    dur_acorde = duracion / len(acordes)
    n_acorde = int(dur_acorde * sample_rate)

    muestras = [0.0] * n_total
    for a_idx, acorde in enumerate(acordes):
        inicio = a_idx * n_acorde
        for i in range(n_acorde):
            t = i / sample_rate
            # envolvente por acorde: ataque y liberación suaves (solapado)
            pos = i / n_acorde
            env = min(1.0, pos / 0.25) * min(1.0, (1.0 - pos) / 0.35 + 0.15)
            v = 0.0
            for f in acorde:
                v += math.sin(2 * math.pi * f * t)          # fundamental
                v += 0.35 * math.sin(2 * math.pi * f * 2 * t)  # octava suave
                v += 0.12 * math.sin(2 * math.pi * f * 3 * t)  # quinta arriba
            # vibrato lentísimo global (respiración)
            v *= 1.0 + 0.06 * math.sin(2 * math.pi * 0.15 * (inicio / sample_rate + t))
            idx = inicio + i
            if idx < n_total:
                muestras[idx] += v * env / (len(acorde) * 1.6)

    # Fundido global de entrada (1.2s) y salida (2.5s)
    n_in, n_out = int(1.2 * sample_rate), int(2.5 * sample_rate)
    for i in range(min(n_in, n_total)):
        muestras[i] *= i / n_in
    for i in range(min(n_out, n_total)):
        muestras[n_total - 1 - i] *= i / n_out

    # Normalizar con margen amplio (es fondo, no protagonista)
    pico = max(abs(m) for m in muestras) or 1.0
    factor = 0.55 / pico

    with wave.open(destino_wav, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        frames = b"".join(struct.pack("<h", int(m * factor * 32767)) for m in muestras)
        w.writeframes(frames)
    log(AGENT, f"Pad de meditación sintetizado localmente ({duracion:.0f}s, "
                f"100% original y libre de derechos).")
    return destino_wav


def obtener_musica_intro(carpeta_salida: str, duracion: float = 14.0):
    """Punto de entrada: devuelve la ruta de un audio de meditación para la
    intro (Jamendo si está configurado; si no, pad local sintetizado).
    Nunca lanza excepción hacia arriba."""
    try:
        os.makedirs(carpeta_salida, exist_ok=True)
        cfg = load_config()
        client_id = cfg["apis"].get("jamendo_client_id", "")
        if client_id and "OBTENER_GRATIS" not in client_id:
            ruta = _buscar_jamendo_meditacion(client_id, carpeta_salida)
            if ruta:
                return ruta
        return _sintetizar_pad_meditacion(
            os.path.join(carpeta_salida, "musica_intro.wav"), duracion)
    except Exception as e:
        log(AGENT, f"No se pudo obtener música para la intro ({e}); la intro va sin música.")
        return None


if __name__ == "__main__":
    print(obtener_musica_intro("/tmp/test_musica_intro"))
