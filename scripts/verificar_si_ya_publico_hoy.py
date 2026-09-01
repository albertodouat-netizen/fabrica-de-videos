#!/usr/bin/env python3
"""
Candado de frecuencia de publicación v3 (01-sep-2026).

La v2 ya no dependía SOLO de data/estado.json, pero aún tenía un hueco
real: si un video largo quedaba subido PRIVADO y PROGRAMADO para las 2:30
pm, ese video todavía NO aparecía en el feed RSS público de YouTube. En
ese caso, una corrida de respaldo posterior podía creer que "no hay video
hoy" y arrancar OTRO largo, duplicando trabajo o incluso subidas.

La v3 cruza DOS señales:
  1) feed RSS público del canal (fuente de verdad de lo YA público)
  2) memoria local del robot (ultima_ejecucion), que sí registra largos ya
     generados/subidos hoy aunque sigan privados o programados.

Además, el workflow ahora corre con concurrency para que la corrida de
respaldo no se solape con la principal; cuando la de respaldo arranque,
esta memoria ya debería estar actualizada si la principal terminó bien.

Decisiones que toma (salida ya_publico para el workflow):
  - ya_publico=true  -> HOY NO se genera video largo (o ya se generó/subió
                        hoy, o aún no han pasado los 2 días).
  - ya_publico=false -> toca video largo hoy.
Nunca bloquea por error: si ninguna fuente responde, deja publicar.
"""
import datetime as dt
import json
import os
import re
import urllib.request

SALIDA = os.environ.get("GITHUB_OUTPUT", "/dev/null")

# Cada cuántos días se publica un video largo. 2 = día por medio.
DIAS_ENTRE_VIDEOS = 2

CHANNEL_ID = "UCp96gCIthtbOAnhFpezcAHg"
RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"


def _ultimo_largo_desde_rss():
    """Fecha del último video LARGO (no Short) según el feed público.

    Nota (bug real corregido el mismo 16-ago): en el feed de YouTube,
    <published> viene ANTES de <media:title> dentro de cada <entry>, así
    que un regex que busque título->fecha "cruza" entradas y desfasa las
    fechas. Por eso aquí se parsea CADA <entry> por separado."""
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        xml = r.read().decode("utf-8", errors="replace")
    mas_reciente = None
    for bloque in re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL):
        m_titulo = re.search(r"<media:title>([^<]*)</media:title>", bloque) or \
                   re.search(r"<title>([^<]*)</title>", bloque)
        m_fecha = re.search(r"<published>([^<]+)</published>", bloque)
        if not m_titulo or not m_fecha:
            continue
        if "#shorts" in m_titulo.group(1).lower():
            continue
        try:
            d = dt.datetime.fromisoformat(m_fecha.group(1)).date()
            if mas_reciente is None or d > mas_reciente:
                mas_reciente = d
        except ValueError:
            continue
    return mas_reciente


def _ultimo_largo_desde_memoria():
    """Fecha del último largo según la memoria local del robot.

    Esta memoria SÍ se actualiza cuando un largo se generó y se subió hoy,
    incluso si quedó privado/programado y todavía no existe en el RSS."""
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
    hoy_utc = dt.datetime.now(dt.timezone.utc).date()
    fecha_rss = None
    fecha_memoria = _ultimo_largo_desde_memoria()
    error_rss = None

    try:
        fecha_rss = _ultimo_largo_desde_rss()
    except Exception as e:
        error_rss = e
        print(f"Aviso: feed RSS no disponible ({e}); se usará la memoria local como respaldo.")

    # PRIORIDAD ABSOLUTA: si la memoria local ya dice que hoy se ejecutó un
    # largo, bloquear aunque el RSS todavía no lo muestre por estar privado o
    # programado.
    if fecha_memoria == hoy_utc:
        publicar = False
        motivo = ("ya se generó/subió un video largo hoy según memoria local "
                  "(incluye privados/programados que aún no salen en el RSS)")
    else:
        fechas = []
        if fecha_rss is not None:
            fechas.append((fecha_rss, "feed RSS del canal"))
        if fecha_memoria is not None:
            fechas.append((fecha_memoria, "memoria local"))

        fecha_ultimo_largo = None
        fuente = ""
        if fechas:
            fecha_ultimo_largo, fuente = max(fechas, key=lambda x: x[0])
            if fecha_memoria is not None and fecha_ultimo_largo == fecha_memoria and fecha_memoria != fecha_rss:
                fuente = "memoria local (más nueva que el RSS; puede ser un programado privado)"

        publicar = True
        motivo = "no hay registro de videos largos previos"
        if fecha_ultimo_largo is not None:
            dias_pasados = (hoy_utc - fecha_ultimo_largo).days
            if dias_pasados == 0:
                publicar = False
                motivo = f"hoy ya existe un video largo registrado (según {fuente})"
            elif dias_pasados < DIAS_ENTRE_VIDEOS:
                publicar = False
                motivo = (f"solo ha(n) pasado {dias_pasados} día(s) desde el último video "
                          f"largo (según {fuente}); la frecuencia es 1 cada {DIAS_ENTRE_VIDEOS} días")
            else:
                motivo = (f"han pasado {dias_pasados} día(s) desde el último video largo "
                          f"(según {fuente}): toca publicar")

    with open(SALIDA, "a", encoding="utf-8") as f:
        f.write(f"ya_publico={'false' if publicar else 'true'}\n")

    if publicar:
        print(f"Se continúa con la generación del video largo ({motivo}).")
    else:
        print(f"Hoy no toca video largo: {motivo}. "
              f"(El workflow publicará el Short independiente del día.)")


if __name__ == "__main__":
    main()
