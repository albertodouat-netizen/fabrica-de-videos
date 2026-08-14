"""
AGENTE 1: EXPLORADOR DE TENDENCIAS ("Trend Scout")
----------------------------------------------------
Sustituto 100% GRATUITO de herramientas de pago tipo Viralyt/TubeBuddy/VidIQ.
Usa la YouTube Data API v3 oficial (capa gratuita: 10,000 unidades/día,
una búsqueda cuesta 100 unidades => ~100 búsquedas gratis diarias).

Qué hace:
  1) Busca videos recientes (mercado en inglés, más datos disponibles) para las
     palabras clave del nicho.
  2) Descarta canales grandes (para encontrar ideas "virales por el tema", no
     por la audiencia ya construida) -> mismo criterio que usa Viralyt.
  3) Calcula el ratio vistas/suscriptores del canal (outlier score). Si un video
     tiene muchas más vistas que suscriptores tiene el canal, es señal de que
     el TEMA funciona independientemente de quién lo publique.
  4) Devuelve una lista ordenada de "ideas potenciales" con título original,
     canal, vistas, duración y el ratio-outlier.

Requiere: apis.youtube_api_key (gratis) en config.yaml
Si no hay key configurada, cae en modo DEMO con datos de ejemplo para que
el resto del pipeline se pueda probar sin coste ni cuenta.
"""
import datetime as dt
import re
try:
    import isodate
except ImportError:
    isodate = None
from googleapiclient.discovery import build

from agents.utils import load_config, log

AGENT = "TrendScout"


def _parse_duration_seconds(iso_duration: str) -> int:
    try:
        if isodate is None:
            raise ValueError("isodate no disponible")
        return int(isodate.parse_duration(iso_duration).total_seconds())
    except Exception:
        # fallback manual muy simple PT#H#M#S
        h = m = s = 0
        m_h = re.search(r"(\d+)H", iso_duration)
        m_m = re.search(r"(\d+)M", iso_duration)
        m_s = re.search(r"(\d+)S", iso_duration)
        if m_h:
            h = int(m_h.group(1))
        if m_m:
            m = int(m_m.group(1))
        if m_s:
            s = int(m_s.group(1))
        return h * 3600 + m * 60 + s


def _demo_resultados(cfg):
    """Datos de ejemplo realistas para probar el pipeline sin API key."""
    log(AGENT, "Sin 'youtube_api_key' configurada -> usando modo DEMO (datos de ejemplo).")
    ejemplos = [
        {
            "titulo": "5 Morning Habits That Fixed My Gut Health",
            "categoria": "salud digestiva e intestinal",
            "canal": "Wellness Outliers",
            "suscriptores": 42000,
            "vistas": 1850000,
            "duracion_min": 14.2,
            "ratio_outlier": round(1850000 / 42000, 1),
            "url": "https://www.youtube.com/watch?v=demo1",
        },
        {
            "titulo": "The Real Cause of Chronic Fatigue (Doctors Won't Tell You)",
            "categoria": "sistema inmunológico",
            "canal": "Health Signals",
            "suscriptores": 88000,
            "vistas": 2400000,
            "duracion_min": 18.5,
            "ratio_outlier": round(2400000 / 88000, 1),
            "url": "https://www.youtube.com/watch?v=demo2",
        },
        {
            "titulo": "Why You Should Stop Drinking Water Without Thirst",
            "categoria": "salud metabólica y glucosa",
            "canal": "Ancient Wellness",
            "suscriptores": 15000,
            "vistas": 640000,
            "duracion_min": 11.0,
            "ratio_outlier": round(640000 / 15000, 1),
            "url": "https://www.youtube.com/watch?v=demo3",
        },
    ]
    return sorted(ejemplos, key=lambda x: x["ratio_outlier"], reverse=True)


def _obtener_ejes_tematicos(cfg):
    """Lee la lista de ejes temáticos (categoría + palabras clave) del
    config. Soporta también el formato viejo (lista plana de palabras
    clave sin categoría), para no romper configuraciones anteriores."""
    ejes = cfg["canal"].get("ejes_tematicos")
    if ejes:
        return ejes
    plano = cfg["canal"].get("palabras_clave", [])
    return [{"categoria": "general", "palabras_clave": plano}] if plano else []


def buscar_ideas_potenciales(max_resultados=15, categorias_evitar=None):
    """categorias_evitar: lista opcional de categorías usadas recientemente
    (ver orchestrator.py) para dar prioridad a ejes temáticos distintos y
    que el canal no se sienta repetitivo."""
    cfg = load_config()
    api_key = cfg["apis"].get("youtube_api_key", "")
    if not api_key or "OBTENER_GRATIS" in api_key:
        return _demo_resultados(cfg)

    youtube = build("youtube", "v3", developerKey=api_key)
    estrategia = cfg["estrategia"]
    ejes = _obtener_ejes_tematicos(cfg)
    categorias_evitar = set(categorias_evitar or [])
    idioma = cfg["canal"]["idioma_investigacion"]

    # Priorizamos ejes temáticos que NO se hayan usado recientemente (rotación
    # para variedad); si todos se evitarían, igual los recorremos todos.
    ejes_ordenados = sorted(ejes, key=lambda e: e["categoria"] in categorias_evitar)

    publicado_despues = (
        dt.datetime.utcnow() - dt.timedelta(days=estrategia["dias_publicado_max"])
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    candidatos = []
    casi_candidatos = []  # guardamos todo lo visto, por si el filtro estricto no deja nada
    canal_cache = {}
    hubo_error_api = False

    for eje in ejes_ordenados:
        categoria = eje["categoria"]
        for kw in eje["palabras_clave"]:
            log(AGENT, f"Buscando: '{kw}' (eje: {categoria}) ...")
            try:
                search_resp = youtube.search().list(
                    q=kw,
                    part="snippet",
                    type="video",
                    maxResults=25,
                    order="viewCount",
                    relevanceLanguage=idioma,
                    publishedAfter=publicado_despues,
                ).execute()

                video_ids = [it["id"]["videoId"] for it in search_resp.get("items", [])]
                if not video_ids:
                    continue

                videos_resp = youtube.videos().list(
                    part="statistics,contentDetails,snippet",
                    id=",".join(video_ids),
                ).execute()

                for v in videos_resp.get("items", []):
                    duracion_seg = _parse_duration_seconds(v["contentDetails"]["duration"])
                    duracion_min = duracion_seg / 60
                    if duracion_min < estrategia["duracion_minima_min"]:
                        continue

                    vistas = int(v["statistics"].get("viewCount", 0))
                    channel_id = v["snippet"]["channelId"]

                    if channel_id not in canal_cache:
                        ch_resp = youtube.channels().list(part="statistics", id=channel_id).execute()
                        items = ch_resp.get("items", [])
                        subs = int(items[0]["statistics"].get("subscriberCount", 0)) if items else 0
                        canal_cache[channel_id] = subs
                    subs = canal_cache[channel_id]

                    if subs == 0 or subs > estrategia["max_suscriptores_referencia"]:
                        continue

                    ratio = vistas / subs
                    item = {
                        "titulo": v["snippet"]["title"],
                        "categoria": categoria,
                        "canal": v["snippet"]["channelTitle"],
                        "suscriptores": subs,
                        "vistas": vistas,
                        "duracion_min": round(duracion_min, 1),
                        "ratio_outlier": round(ratio, 1),
                        "url": f"https://www.youtube.com/watch?v={v['id']}",
                    }
                    casi_candidatos.append(item)

                    if ratio >= estrategia["ratio_minimo_vistas_subs"]:
                        candidatos.append(item)

            except Exception as e:
                hubo_error_api = True
                log(AGENT, f"Aviso: la búsqueda de '{kw}' falló ({e}). Se continúa con las demás palabras clave.")
                continue

    if not candidatos and casi_candidatos:
        log(AGENT, "Ningún video superó el ratio-outlier mínimo esta vez; "
                    "se muestran los mejores candidatos disponibles igualmente.")
        candidatos = casi_candidatos

    if not candidatos:
        motivo = ("la cuota diaria gratuita de la API de YouTube (100 búsquedas/día) probablemente "
                   "se agotó por hoy; se resetea en 24h" if hubo_error_api else
                   "la búsqueda en vivo no devolvió resultados esta vez (puede pasar por azar en el muestreo)")
        log(AGENT, f"Sin resultados reales disponibles: {motivo}. Usando datos DEMO para no detener el pipeline.")
        return _demo_resultados(cfg)

    # Ordena priorizando categorías NO usadas recientemente (variedad real),
    # y dentro de cada grupo por ratio-outlier (qué tan viral es el ángulo).
    candidatos.sort(key=lambda x: (x["categoria"] in categorias_evitar, -x["ratio_outlier"]))
    return candidatos[:max_resultados]

if __name__ == "__main__":
    ideas = buscar_ideas_potenciales()
    for i, idea in enumerate(ideas, 1):
        print(f"{i}. [{idea['ratio_outlier']}x outlier] {idea['titulo']} — {idea['canal']} "
              f"({idea['suscriptores']} subs, {idea['vistas']} vistas, {idea['duracion_min']} min)")
