"""
AGENTE 8: ANALISTA ("Analytics Agent")
----------------------------------------------------
Cierra el ciclo de mejora continua (lo que en el video llamaban "mirar
métricas cuando ya hay tracción"). Usa la YouTube Analytics API (gratis)
para traer vistas/CTR/tiempo de retención de los últimos videos publicados
por el propio sistema y así decidir automáticamente qué tipo de idea repetir.
"""
import datetime as dt
import googleapiclient.discovery

from agents.utils import load_config, load_state, log

AGENT = "Analista"


def analizar_rendimiento(creds):
    yt_analytics = googleapiclient.discovery.build("youtubeAnalytics", "v2", credentials=creds)
    estado = load_state()
    ids = [v["video_id"] for v in estado.get("videos_publicados", [])][-20:]
    if not ids:
        log(AGENT, "Aún no hay videos publicados por el sistema para analizar.")
        return []

    hoy = dt.date.today()
    hace_30 = hoy - dt.timedelta(days=30)

    resultados = []
    for vid in ids:
        try:
            resp = yt_analytics.reports().query(
                ids="channel==MINE",
                startDate=hace_30.isoformat(),
                endDate=hoy.isoformat(),
                metrics="views,averageViewPercentage,estimatedRevenue",
                filters=f"video=={vid}",
            ).execute()
            filas = resp.get("rows", [[0, 0, 0]])
            vistas, retencion, ingresos = filas[0] if filas else (0, 0, 0)
            resultados.append({
                "video_id": vid,
                "vistas_30d": vistas,
                "retencion_pct": retencion,
                "ingresos_estimados": ingresos,
            })
        except Exception as e:
            log(AGENT, f"No se pudo obtener analítica de {vid}: {e}")

    resultados.sort(key=lambda r: r["vistas_30d"], reverse=True)
    return resultados


if __name__ == "__main__":
    print("Este módulo requiere credenciales OAuth ya autorizadas (ver publisher.py).")
