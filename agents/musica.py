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

# SOLO música RELAJANTE (orden del usuario, 21-ago-2026, tras oír rock con
# guitarra eléctrica en el video de magnesio: "siempre debe ser musica
# relajante... no el rock que sonaba"). Tags verificados EN VIVO con la
# llave real: meditation, piano, soft y calm devuelven pistas CC aptas.
TAGS_INSTRUMENTAL_SUGERIDOS = ["meditation", "relaxing", "piano", "calm", "soft", "ambient"]

# Géneros/instrumentos PROHIBIDOS aunque el tag principal coincida (el bug
# real: "Hope" de Jimi Sobara salía con tag inspiring pero sus géneros
# reales en Jamendo eran corporate+ROCK con guitarra eléctrica).
_GENEROS_PROHIBIDOS = ("rock", "metal", "punk", "electro", "techno", "dance",
                        "hiphop", "rap", "dubstep", "hardcore", "industrial")
_INSTRUMENTOS_PROHIBIDOS = ("electricguitar", "distortion", "drums")


def _buscar_pistas_comerciales(client_id: str, tag: str, limite=10):
    url = "https://api.jamendo.com/v3.0/tracks/"
    params = {
        "client_id": client_id,
        "format": "json",
        "limit": limite,
        "tags": tag,
        "vocalinstrumental": "instrumental",
        # FILTRO DEL LADO DEL SERVIDOR (corrección 19-ago-2026, probada en
        # vivo con la llave real): sin 'ccnc=false' Jamendo devuelve las 10
        # pistas más populares que casi siempre son licencia NC (No
        # Comercial) y el filtro local las descartaba TODAS -> videos sin
        # música. Con ccnc=false el servidor solo devuelve pistas aptas
        # para un canal monetizable (probado: 10/10 usables con
        # tag=uplifting). ccsa se deja libre: BY y BY-SA sirven ambas
        # acreditando al artista (los créditos ya van en la descripción).
        "ccnc": "false",
        # ccnd=false también (19-ago-2026): las licencias ND (No Derivadas)
        # prohíben obras derivadas, y sincronizar la pista dentro de un
        # video puede contar como derivada. Solo CC-BY y CC-BY-SA = 100%
        # seguras para un canal monetizable (mismo criterio que la intro).
        "ccnd": "false",
        "order": "popularity_total",
        "include": "musicinfo",
        "audioformat": "mp32",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    # Pistas con temática de temporada/festiva que NO pegan en un video de
    # salud natural (hallazgo real 19-ago-2026: la primera prueba en vivo
    # eligió "Happy Holiday Christmas" para un video de bienestar).
    _PALABRAS_FUERA_DE_CONTEXTO = (
        "christmas", "navidad", "holiday", "halloween", "xmas", "santa",
        "jingle", "easter", "valentine", "wedding", "birthday", "party",
    )
    resultados = []
    for track in r.json().get("results", []):
        licencia = (track.get("license_ccurl") or "").lower()
        if "nc" in licencia:  # excluye explícitamente licencias "No Comercial"
            continue
        if not track.get("audio"):
            continue
        nombre_bajo = (track.get("name") or "").lower()
        if any(p in nombre_bajo for p in _PALABRAS_FUERA_DE_CONTEXTO):
            continue
        # Filtro por géneros/instrumentos REALES de la pista (musicinfo):
        # nada de rock/metal/electrónica ni guitarra eléctrica/batería.
        mi = (track.get("musicinfo") or {}).get("tags", {})
        generos = [g.lower() for g in (mi.get("genres") or [])]
        instrumentos = [i.lower() for i in (mi.get("instruments") or [])]
        tiene_genero_prohibido = any(
            gp in g for g in generos for gp in _GENEROS_PROHIBIDOS)
        tiene_instrumento_prohibido = any(
            ip in i for i in instrumentos for ip in _INSTRUMENTOS_PROHIBIDOS)
        if tiene_genero_prohibido or tiene_instrumento_prohibido:
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
        # ROTACIÓN DE TAGS (corrección 19-ago-2026): antes se elegía UN tag
        # al azar y si no tenía pistas comerciales el video quedaba sin
        # música (probado en vivo: 'corporate' devuelve 0 con ccnc=false).
        # Ahora se prueban todos los tags en orden aleatorio hasta que uno
        # tenga pistas.
        tags_orden = random.sample(TAGS_INSTRUMENTAL_SUGERIDOS, len(TAGS_INSTRUMENTAL_SUGERIDOS))
        pistas, tag = [], None
        for tag in tags_orden:
            pistas = _buscar_pistas_comerciales(client_id, tag)
            if pistas:
                break
        if not pistas:
            log(AGENT, "Ningún tag tiene pistas comerciales disponibles hoy. Sin música de fondo.")
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
