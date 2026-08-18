#!/usr/bin/env python3
"""
VIGILANTE DE PUBLICACIONES v2 (corregido 16-ago-2026 tras una FALSA
ALARMA real esa misma mañana).

Qué pasó (diagnóstico honesto): la v1 leía data/estado.json (la memoria
local del robot), pero esa memoria estaba desactualizada (el push de la
memoria falló el 14-ago por un choque de git, y las corridas siguientes
publicaron bien SIN lograr actualizar el archivo en el repo). Resultado:
el canal SÍ estaba publicando, pero el vigilante veía una memoria vieja
del 9-ago y alarmó por nada.

La v2 mira LA FUENTE DE VERDAD REAL: el feed RSS público del canal de
YouTube (https://www.youtube.com/feeds/videos.xml?channel_id=...), que
refleja lo publicado de verdad, sin API key, sin cuota y sin depender de
la memoria local. Probado en vivo: el feed muestra los videos con su
fecha exacta de publicación.

Funcionamiento:
  - Lee el feed RSS del canal.
  - Toma la fecha del video más reciente.
  - Si es más vieja que DIAS_ENTRE_VIDEOS + DIAS_DE_GRACIA, termina con
    error A PROPÓSITO -> GitHub envía el correo/notificación de alerta.
  - La memoria local queda solo como respaldo si el RSS fallara.
"""
import datetime as dt
import json
import re
import sys
import urllib.request

# Debe coincidir con scripts/verificar_si_ya_publico_hoy.py
DIAS_ENTRE_VIDEOS = 2
DIAS_DE_GRACIA = 1

CHANNEL_ID = "UCp96gCIthtbOAnhFpezcAHg"
RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"


def _ultima_publicacion_desde_rss():
    """Fecha (date) del video más reciente según el feed público del canal.
    Se parsea CADA <entry> por separado (la primera <published> del feed
    es la del canal, no de un video)."""
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        xml = r.read().decode("utf-8", errors="replace")
    mas_reciente = None
    for bloque in re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL):
        m_fecha = re.search(r"<published>([^<]+)</published>", bloque)
        if not m_fecha:
            continue
        try:
            d = dt.datetime.fromisoformat(m_fecha.group(1)).date()
            if mas_reciente is None or d > mas_reciente:
                mas_reciente = d
        except ValueError:
            continue
    return mas_reciente


def _ultima_publicacion_desde_memoria():
    try:
        with open("data/estado.json", encoding="utf-8") as f:
            estado = json.load(f)
        ultima = estado.get("ultima_ejecucion", "")
        if ultima:
            return dt.datetime.fromisoformat(ultima).date()
    except Exception:
        pass
    return None


def main():
    fecha_ultima = None
    fuente = ""
    try:
        fecha_ultima = _ultima_publicacion_desde_rss()
        fuente = "feed RSS público del canal (fuente de verdad real)"
    except Exception as e:
        print(f"Aviso: no se pudo leer el feed RSS del canal ({e}); "
              f"se usa la memoria local como respaldo.")
        fecha_ultima = _ultima_publicacion_desde_memoria()
        fuente = "memoria local (respaldo; puede estar desactualizada)"

    if fecha_ultima is None:
        print("No se pudo determinar la última publicación por ninguna vía.")
        print("🚨 ALERTA por precaución: revisa la pestaña Actions y el canal.")
        return 1

    hoy_utc = dt.datetime.now(dt.timezone.utc).date()
    dias_pasados = (hoy_utc - fecha_ultima).days
    limite = DIAS_ENTRE_VIDEOS + DIAS_DE_GRACIA

    print(f"Última publicación según {fuente}: {fecha_ultima} "
          f"({dias_pasados} día(s) atrás). Límite antes de alarmar: {limite} días.")

    if dias_pasados > limite:
        print()
        print(f"🚨 ALERTA: el canal NO ha publicado nada en {dias_pasados} días "
              f"(lo esperado es al menos un Short diario y un video largo cada "
              f"{DIAS_ENTRE_VIDEOS} días).")
        print("Qué hacer: entra a la pestaña Actions del repositorio, revisa la "
              "última corrida (busca pasos con ❌) y, si no hubo corrida, lanza "
              "una manual con 'Run workflow'.")
        print()
        print("(Este error es INTENCIONAL: hace que GitHub te envíe el "
              "correo/notificación de alerta que estás leyendo.)")
        return 1

    print("Todo en orden: la última publicación está dentro de lo esperado. ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
