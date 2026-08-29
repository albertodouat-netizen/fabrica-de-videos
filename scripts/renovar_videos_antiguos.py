"""
RENOVADOR DE VIDEOS ANTIGUOS ("Re-empaquetado masivo")
======================================================
Pedido del usuario (28-ago-2026): "¿Es posible actualizar los videos
anteriores, tanto largos como cortos, con todo lo que tenemos?"

Lo que SÍ permite YouTube sin resubir (y este script hace):
  1) PORTADA nueva (thumbnails.set) → Equipo de Portadas élite (Agentes
     38-40): bloques amarillo/negro/rojo, tipografía Anton, 2 variantes
     auditadas con visión IA. Vertical 720x1280 para Shorts.
  2) TÍTULO nuevo (videos.update) → fórmula validada del estudio de 1.630
     videos: pregunta x2.6, STOP/NUNCA x1.85, error/mito + keyword +
     beneficio; hashtags #salud #Shorts en los cortos.
  3) DESCRIPCIÓN → se conserva la original y se asegura el link de la
     playlist del canal (reproducción encadenada).
  4) TAGS → se completan si están pobres.

Lo que NO se puede (limitación real de la API de YouTube):
  - Reemplazar el archivo de video (imágenes/voz/música). Para eso habría
    que borrar y resubir, perdiendo vistas, comentarios y antigüedad.

REGLA DE ORO (estrategia de los canales gemelos, ej. Vital Health HQ):
  - NUNCA se toca el empaque de un video GANADOR (>= UMBRAL_PROTECCION
    vistas). Si algo funciona, no se cambia: se protege y se itera en
    videos nuevos. Solo se renuevan los de bajo rendimiento, que es
    exactamente lo que recomienda el propio YouTube ("re-packaging").

Uso:
  python scripts/renovar_videos_antiguos.py --simular   (solo muestra plan)
  python scripts/renovar_videos_antiguos.py             (aplica de verdad)
  python scripts/renovar_videos_antiguos.py --solo VIDEO_ID (uno solo)
"""
import argparse
import json
import os
import pickle
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import requests
import isodate
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from agents.utils import log, load_config

AGENT = "Renovador"

# Videos con >= este número de vistas NO se tocan (ganadores protegidos)
UMBRAL_PROTECCION = 500

CARPETA_SALIDA = "output/renovacion"


def _youtube():
    cfg = load_config()
    ruta_token = cfg["apis"].get("oauth_token_path", "config/token.json")
    with open(ruta_token, "rb") as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def _inventario(yt):
    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, pt = [], None
    while True:
        r = yt.playlistItems().list(part="contentDetails", playlistId=uploads,
                                    maxResults=50, pageToken=pt).execute()
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        pt = r.get("nextPageToken")
        if not pt:
            break
    inv = []
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet,statistics,contentDetails,status",
                             id=",".join(ids[i:i + 50])).execute()
        for v in r["items"]:
            dur = isodate.parse_duration(v["contentDetails"]["duration"]).total_seconds()
            inv.append({
                "id": v["id"],
                "titulo": v["snippet"]["title"],
                "descripcion": v["snippet"].get("description", ""),
                "tags": v["snippet"].get("tags", []),
                "categoria": v["snippet"].get("categoryId", "27"),
                "idioma": v["snippet"].get("defaultLanguage", "es"),
                "dur": dur,
                "es_short": dur <= 183,
                "vistas": int(v["statistics"].get("viewCount", 0)),
                "pub": v["snippet"]["publishedAt"][:10],
            })
    inv.sort(key=lambda x: x["pub"])
    return inv


# ---------------------------------------------------------------------------
# Título nuevo con la fórmula validada
# ---------------------------------------------------------------------------
_PROMPT_TITULO = """Eres el estratega de títulos de un canal de YouTube de salud natural en español para mayores de 50 años.

PATRONES VALIDADOS CON DATOS REALES (estudio de 1.630 videos, 28-ago-2026):
- Título PREGUNTA rinde x2.6 ("¿Por qué...?", "¿Sabías que...?")
- STOP / NUNCA / DEJA DE rinde x1.85
- "Esto pasa si..." rinde x1.8
- Fórmula error/mito: "El Error Que Comete el 90% al..." / "El Mito de..."
- Cifra concreta en el título (90%, 7 días, a los 60) sube el CTR
- Segunda persona (tu cuerpo, te pasa)
- NO usar listas numeradas simples ("5 consejos") — rinden PEOR
- Máximo 95 caracteres. Debe ser 100% FIEL al contenido (nada de engaños).
- PROHIBIDO INVENTAR CIFRAS O PORCENTAJES que no estén ya en el título
  actual. Si el patrón pide una cifra y no la hay, usa "la mayoría" o
  reformula sin cifra. Un dato inventado destruye la confianza y viola
  las políticas de YouTube.

TÍTULO ACTUAL (el contenido del video trata EXACTAMENTE de esto): "{titulo}"
TIPO: {tipo}
PATRÓN OBLIGATORIO PARA ESTE VIDEO: {patron}
(No uses otro patrón: en el canal cada video renueva con un patrón distinto para que no se vean todos iguales.)

Devuelve SOLO un JSON válido:
{{"titulo": "nuevo título aplicando el patrón obligatorio", "keyword": "tema central en 1-3 palabras"}}"""

# Rotación de patrones para que el canal no quede con 17 títulos iguales
_PATRONES_ROTACION = [
    "PREGUNTA (¿Por qué...? / ¿Qué pasa si...?) — evita '¿Sabías que' salvo que sea perfecto",
    "STOP / NUNCA / DEJA DE + acción concreta",
    "'Esto pasa si...' + consecuencia concreta",
    "El Error Que Comete el X% al... (error/mito con cifra)",
    "Lo Que Nadie Te Dice De... (curiosidad)",
]


def _titulo_nuevo(titulo_actual: str, es_short: bool, indice: int = 0) -> dict:
    from agents.llm_cascada import llamar_llm
    tipo = "Short (video corto)" if es_short else "video largo"
    patron = _PATRONES_ROTACION[indice % len(_PATRONES_ROTACION)]
    try:
        resp = llamar_llm(_PROMPT_TITULO.format(titulo=titulo_actual, tipo=tipo,
                                                patron=patron),
                          temperatura=0.85)
        ini, fin = resp.find("{"), resp.rfind("}")
        data = json.loads(resp[ini:fin + 1])
        titulo = str(data.get("titulo", "")).strip()
        keyword = str(data.get("keyword", "")).strip()
        if not titulo or len(titulo) < 15:
            raise ValueError("título vacío/corto")
        titulo = titulo[:95]
        if es_short and "#" not in titulo and len(titulo) <= 80:
            titulo += " #salud #Shorts"
        return {"titulo": titulo[:100], "keyword": keyword}
    except Exception as e:
        log(AGENT, f"Sin LLM para el título ({type(e).__name__}); se conserva el actual.")
        return {"titulo": titulo_actual, "keyword": ""}


def _descripcion_mejorada(desc: str) -> str:
    cfg = load_config()
    try:
        from agents.utils import load_state
        playlist_id = load_state().get("playlist_canal_id", "")
    except Exception:
        playlist_id = ""
    if playlist_id and playlist_id not in desc:
        desc = (desc.rstrip() +
                f"\n\n📺 Todos los videos del canal, uno tras otro:\n"
                f"https://www.youtube.com/playlist?list={playlist_id}")
    return desc[:4900]


def _tags_mejorados(tags: list, keyword: str, es_short: bool) -> list:
    base = list(tags)
    extras = ["salud natural", "salud despues de los 50", "remedios naturales",
              "bienestar", "vida sana"]
    if keyword:
        extras.insert(0, keyword)
    if es_short:
        extras.append("shorts")
    for e in extras:
        if e and e.lower() not in [t.lower() for t in base]:
            base.append(e)
    return base[:15]


def _descargar_thumb_actual(video_id: str, destino: str) -> str:
    for q in ("maxresdefault", "hqdefault"):
        try:
            r = requests.get(f"https://i.ytimg.com/vi/{video_id}/{q}.jpg", timeout=15)
            if r.status_code == 200 and len(r.content) > 2000:
                with open(destino, "wb") as f:
                    f.write(r.content)
                return destino
        except Exception:
            pass
    return ""


def renovar(simular: bool = False, solo_id: str = None, excluir=None):
    excluir = set(excluir or [])
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    yt = _youtube()
    inv = _inventario(yt)
    log(AGENT, f"Inventario: {len(inv)} videos en el canal.")

    reporte = []
    for v in inv:
        if solo_id and v["id"] != solo_id:
            continue
        if v["id"] in excluir:
            log(AGENT, f"⏭️ Excluido (ya renovado antes): {v['titulo'][:50]}")
            reporte.append({**v, "accion": "excluido"})
            continue
        if v["vistas"] >= UMBRAL_PROTECCION:
            log(AGENT, f"🛡️ PROTEGIDO (ganador, {v['vistas']} vistas): {v['titulo'][:50]}")
            reporte.append({**v, "accion": "protegido"})
            continue

        log(AGENT, f"♻️ Renovando [{'SHORT' if v['es_short'] else 'LARGO'}] "
                    f"{v['vistas']}v: {v['titulo'][:55]}")

        # 1) Título nuevo con fórmula (patrón rotado: cada video uno distinto)
        nuevo = _titulo_nuevo(v["titulo"], v["es_short"], indice=len(reporte))
        titulo_final = nuevo["titulo"]
        keyword = nuevo["keyword"] or v["titulo"]

        # 2) Portada élite (Agentes 38-40); el fotograma de respaldo es la
        #    miniatura ACTUAL del video (para no partir de cero si la IA falla)
        #    En SIMULACIÓN no se generan portadas (tardan ~1 min cada una):
        #    solo se planifica el título para revisar el plan rápido.
        ruta_portada = ""
        if simular:
            log(AGENT, f"  [SIMULACIÓN] Título: {nuevo['titulo'][:70]}")
            reporte.append({**v, "accion": "simulado",
                            "titulo_nuevo": nuevo["titulo"]})
            continue
        try:
            from agents.equipo_portadas import generar_portada_elite
            base_actual = _descargar_thumb_actual(
                v["id"], os.path.join(CARPETA_SALIDA, f"{v['id']}_actual.jpg"))
            ruta_portada = generar_portada_elite(
                {"titulo": titulo_final, "keyword_principal": keyword},
                base_actual,
                os.path.join(CARPETA_SALIDA, f"{v['id']}_nueva.png"),
                vertical=v["es_short"])
        except Exception as e:
            log(AGENT, f"  Portada élite falló ({type(e).__name__}); "
                        f"este video conservará su miniatura actual.")

        # 3) Descripción y tags
        desc_final = _descripcion_mejorada(v["descripcion"])
        tags_final = _tags_mejorados(v["tags"], nuevo["keyword"], v["es_short"])

        item = {**v, "accion": "renovado", "titulo_nuevo": titulo_final,
                "portada": ruta_portada,
                "desc_cambio": desc_final != v["descripcion"],
                "n_tags": len(tags_final)}

        # 4) Aplicar en YouTube
        try:
            yt.videos().update(part="snippet", body={
                "id": v["id"],
                "snippet": {
                    "title": titulo_final,
                    "description": desc_final,
                    "tags": tags_final,
                    "categoryId": v["categoria"] or "27",
                    "defaultLanguage": v["idioma"] or "es",
                    "defaultAudioLanguage": "es",
                },
            }).execute()
            log(AGENT, f"  ✅ Título/desc/tags actualizados: {titulo_final[:60]}")
        except Exception as e:
            log(AGENT, f"  ❌ videos.update falló: {e}")
            item["accion"] = "error_update"

        if ruta_portada and os.path.exists(ruta_portada):
            try:
                yt.thumbnails().set(videoId=v["id"], media_body=ruta_portada).execute()
                log(AGENT, "  ✅ Portada nueva asignada.")
            except Exception as e:
                log(AGENT, f"  ❌ thumbnails.set falló: {e}")
                item["accion"] = item["accion"] + "+error_thumb"

        reporte.append(item)
        time.sleep(2)  # respiro entre videos (cortesía con la API)

    with open(os.path.join(CARPETA_SALIDA, "reporte_renovacion.json"), "w",
              encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=1)

    renovados = sum(1 for r in reporte if r["accion"].startswith("renovado"))
    protegidos = sum(1 for r in reporte if r["accion"] == "protegido")
    log(AGENT, f"FIN: {renovados} renovados, {protegidos} protegidos (ganadores), "
                f"{len(reporte) - renovados - protegidos} otros. "
                f"Reporte: {CARPETA_SALIDA}/reporte_renovacion.json")
    return reporte


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--simular", action="store_true", help="No aplica cambios")
    ap.add_argument("--solo", default=None, help="Renovar solo este video ID")
    ap.add_argument("--excluir", default="", help="IDs separados por coma que NO se tocan")
    args = ap.parse_args()
    renovar(simular=args.simular, solo_id=args.solo,
            excluir=[x for x in args.excluir.split(",") if x.strip()])
