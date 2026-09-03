#!/usr/bin/env python3
"""
Candado de frecuencia de publicación v2 (corregido 16-ago-2026).

Igual que el vigilante, la v1 dependía SOLO de data/estado.json, que puede
quedar desactualizada si el push de la memoria falla (pasó de verdad el
14-ago: la memoria quedó en el 9-ago aunque el canal siguió publicando).
Con la memoria vieja, el candado daría luz verde al video largo TODOS los
días (creería que llevamos una semana sin publicar), rompiendo la
frecuencia de "1 largo cada 2 días" decidida por el usuario.

La v2 mira el feed RSS público del canal (fuente de verdad real, sin API
key ni cuota): identifica el último VIDEO LARGO publicado de verdad
(los Shorts se distinguen por el marcador '#Shorts' en el título, como
los genera este mismo sistema) y decide con esa fecha.

Decisiones que toma (salida ya_publico para el workflow):
  - ya_publico=true  -> HOY NO se genera video largo (o ya se publicó hoy,
                        o aún no han pasado los 2 días).
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
    fecha_ultimo_largo = None
    fuente = ""
    try:
        fecha_ultimo_largo = _ultimo_largo_desde_rss()
        fuente = "feed RSS del canal"
    except Exception as e:
        print(f"Aviso: feed RSS no disponible ({e}); se usa la memoria local.")
        fecha_ultimo_largo = _ultimo_largo_desde_memoria()
        fuente = "memoria local"

    publicar = True
    motivo = "no hay registro de videos largos previos"
    if fecha_ultimo_largo is not None:
        hoy_utc = dt.datetime.now(dt.timezone.utc).date()
        dias_pasados = (hoy_utc - fecha_ultimo_largo).days
        if dias_pasados == 0:
            publicar = False
            motivo = f"hoy ya se publicó un video largo (según {fuente})"
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
