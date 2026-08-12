"""
AGENTE 14: MÚSICA DE FONDO ("Musica")
----------------------------------------------------
Agrega una pista instrumental de fondo (volumen bajo, debajo de la
narración) usando Jamendo, un catálogo gratuito de música con licencia
Creative Commons. Se filtran automáticamente las pistas para excluir
las que tengan licencia "No Comercial" (NC), ya que el video se va a
monetizar. Se añade el crédito correspondiente en la descripción
(requisito habitual de las licencias CC-BY).

100% gratis: solo requiere un client_id gratuito de https://devportal.jamendo.com/
Si no está configurado, el video se genera igual mente, solo que sin música
de fondo (nunca bloquea el pipeline).
"""
import os
import random
import requests

from agents.utils import load_config, log

AGENT = "Musica"

TAGS_INSTRUMENTAL_SUGERIDOS = ["inspiring", "calm", "corporate", "uplifting", "background"]


def _buscar_pistas_comerciales(client_id: str, tag: str, limite=10):
    url = "https://api.jamendo.com/v3.0/tracks/"
    params = {
        "client_id": client_id,
        "format": "json",
        "limit": limite,
        "tags": tag,
        "vocalinstrumental": "instrumental",
        "order": "popularity_total",
        "include": "musicinfo",
        "audioformat": "mp32",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    resultados = []
    for track in r.json().get("results", []):
        licencia = (track.get("license_ccurl") or "").lower()
        if "nc" in licencia:  # excluye explícitamente licencias "No Comercial"
            continue
        if not track.get("audio"):
            continue
        resultados.append({
            "nombre": track.get("name", "Untitled"),
            "artista": track.get("artist_name", "Desconocido"),
            "url_audio": track["audio"],
            "url_licencia": track.get("license_ccurl", ""),
        })
    return resultados


def obtener_musica_fondo(carpeta_salida: str) -> dict:
    """Devuelve {"ruta": ..., "credito": "..."} o None si no hay música
    disponible/configurada. Nunca lanza excepción hacia arriba."""
    cfg = load_config()
    client_id = cfg["apis"].get("jamendo_client_id", "")
    if not client_id or "OBTENER_GRATIS" in client_id:
        log(AGENT, "Sin jamendo_client_id configurado: el video se generará sin música de fondo.")
        return None

    try:
        tag = random.choice(TAGS_INSTRUMENTAL_SUGERIDOS)
        pistas = _buscar_pistas_comerciales(client_id, tag)
        if not pistas:
            log(AGENT, f"No se encontraron pistas comerciales para '{tag}'. Sin música de fondo.")
            return None

        pista = random.choice(pistas)
        os.makedirs(carpeta_salida, exist_ok=True)
        destino = os.path.join(carpeta_salida, "musica_fondo.mp3")
        r = requests.get(pista["url_audio"], stream=True, timeout=60)
        r.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)

        log(AGENT, f"Música de fondo: '{pista['nombre']}' de {pista['artista']} (licencia comercial verificada).")
        credito = f"Música: \"{pista['nombre']}\" de {pista['artista']} (Jamendo, licencia {pista['url_licencia']})"
        return {"ruta": destino, "credito": credito}

    except Exception as e:
        log(AGENT, f"No se pudo obtener música de fondo ({e}). El video se genera igual, sin música.")
        return None
