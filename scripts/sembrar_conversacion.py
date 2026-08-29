"""
SEMBRADOR DE CONVERSACIÓN + REACTIVADOR DE GANADORES
====================================================
Dos ideas del usuario (29-ago-2026):

IDEA 2 (este script la ejecuta): añadir a TODOS los videos (largos y
shorts) un comentario "semilla de conversación": 3 preguntas sugestivas
que invitan a contar experiencias propias. Por qué en UN solo comentario:
varios comentarios propios seguidos parecen spam y YouTube puede
marcarlos. Las respuestas de espectadores son la señal de interacción
más valiosa del algoritmo 2026 (conversación + tiempo en la página).

IDEA 1 (reactivar ganadores SIN arriesgar): a los videos GANADORES no se
les toca título ni portada (regla de oro: el empaque que ya demostró
funcionar no se cambia; cambiar la portada de un video con 1.334 vistas
reinicia su prueba y puede MATAR lo ganado). Lo que SÍ es seguro y
reactiva señales:
  - Comentario nuevo de conversación (este script) → mueve el video en
    "ordenar por más recientes" de la pestaña de comentarios y genera
    respuestas nuevas.
  - La descripción se completa con el link de playlist si falta (tráfico
    encadenado) — cambio invisible al algoritmo de portada/título.
  - La VERDADERA reactivación de un ganador es la "explotación de éxito"
    que ya está integrada en la fábrica: el sistema puede volver a hacer
    videos NUEVOS del mismo tema ganador (magnesio, setas) — así lo hace
    Vital Health HQ, que repite su hit una y otra vez con variantes.

Anti-duplicado: si el video ya tiene un comentario propio de conversación
("CUÉNTAME TU EXPERIENCIA"), no se repite.

Uso:
  python scripts/sembrar_conversacion.py --simular
  python scripts/sembrar_conversacion.py
"""
import argparse
import json
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from agents.utils import log, load_config, load_state

AGENT = "SembradorConversacion"

MARCA_CONVERSACION = "CUÉNTAME TU EXPERIENCIA"


def _youtube():
    cfg = load_config()
    ruta_token = cfg["apis"].get("oauth_token_path", "config/token.json")
    with open(ruta_token, "rb") as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def _videos_del_canal(yt):
    ch = yt.channels().list(part="contentDetails,id", mine=True).execute()
    mi_canal = ch["items"][0]["id"]
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, pt = [], None
    while True:
        r = yt.playlistItems().list(part="contentDetails", playlistId=uploads,
                                    maxResults=50, pageToken=pt).execute()
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        pt = r.get("nextPageToken")
        if not pt:
            break
    videos = []
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet,status,statistics",
                             id=",".join(ids[i:i + 50])).execute()
        for v in r["items"]:
            videos.append({
                "id": v["id"],
                "titulo": v["snippet"]["title"],
                "descripcion": v["snippet"].get("description", ""),
                "tags": v["snippet"].get("tags", []),
                "categoria": v["snippet"].get("categoryId", "27"),
                "privacy": v["status"]["privacyStatus"],
                "vistas": int(v["statistics"].get("viewCount", 0)),
            })
    return mi_canal, videos


def _ya_tiene_conversacion(yt, video_id: str, mi_canal: str) -> bool:
    try:
        r = yt.commentThreads().list(part="snippet", videoId=video_id,
                                     maxResults=50).execute()
        for it in r.get("items", []):
            s = it["snippet"]["topLevelComment"]["snippet"]
            if (s.get("authorChannelId", {}).get("value") == mi_canal
                    and MARCA_CONVERSACION in s.get("textOriginal", "")):
                return True
    except Exception:
        pass
    return False


def sembrar(simular: bool = False):
    yt = _youtube()
    mi_canal, videos = _videos_del_canal(yt)
    log(AGENT, f"{len(videos)} videos en el canal.")

    from agents.promocion_cruzada import comentario_conversacion

    playlist_id = load_state().get("playlist_canal_id", "")
    sembrados, saltados, desc_arregladas = 0, 0, 0

    for v in videos:
        if v["privacy"] != "public":
            log(AGENT, f"⏭️ No público aún ({v['privacy']}): {v['titulo'][:45]}")
            continue

        # --- IDEA 1 (parte segura): completar playlist en la descripción de
        # CUALQUIER video donde falte, incluidos los ganadores (no toca
        # título ni portada, cero riesgo para el empaque ganador).
        if playlist_id and playlist_id not in v["descripcion"]:
            if simular:
                log(AGENT, f"  [SIM] añadiría playlist a: {v['titulo'][:45]}")
            else:
                try:
                    yt.videos().update(part="snippet", body={
                        "id": v["id"],
                        "snippet": {
                            "title": v["titulo"],
                            "description": (v["descripcion"].rstrip() +
                                            f"\n\n📺 Todos los videos del canal, uno tras otro:\n"
                                            f"https://www.youtube.com/playlist?list={playlist_id}")[:4900],
                            "tags": v["tags"],
                            "categoryId": v["categoria"],
                            "defaultLanguage": "es",
                            "defaultAudioLanguage": "es",
                        },
                    }).execute()
                    desc_arregladas += 1
                except Exception as e:
                    log(AGENT, f"  Aviso: descripción no actualizada ({str(e)[:60]})")

        # --- IDEA 2: comentario semilla de conversación
        if _ya_tiene_conversacion(yt, v["id"], mi_canal):
            log(AGENT, f"⏭️ Ya tiene conversación: {v['titulo'][:45]}")
            saltados += 1
            continue

        texto = comentario_conversacion(v["titulo"])
        if simular:
            log(AGENT, f"  [SIM] comentaría en '{v['titulo'][:40]}':\n{texto[:150]}...")
            continue
        try:
            yt.commentThreads().insert(part="snippet", body={
                "snippet": {
                    "videoId": v["id"],
                    "topLevelComment": {"snippet": {"textOriginal": texto}},
                },
            }).execute()
            sembrados += 1
            log(AGENT, f"💬 Sembrado en [{v['vistas']}v] {v['titulo'][:45]}")
            time.sleep(3)  # respiro anti-spam entre comentarios
        except Exception as e:
            log(AGENT, f"  ❌ No se pudo comentar ({str(e)[:80]})")

    log(AGENT, f"FIN: {sembrados} conversaciones sembradas, {saltados} ya tenían, "
                f"{desc_arregladas} descripciones completadas con playlist.")
    log(AGENT, "RECUERDA (1 sola vez, a un clic): en YouTube Studio puedes FIJAR "
                "cada comentario de conversación (⋮ → Fijar). La API no permite "
                "fijar automáticamente — limitación real de YouTube.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--simular", action="store_true")
    args = ap.parse_args()
    sembrar(simular=args.simular)
