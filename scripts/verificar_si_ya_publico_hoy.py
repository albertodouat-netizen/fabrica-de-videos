#!/usr/bin/env python3
"""
Candado de frecuencia de publicación (actualizado 16-ago-2026).

Hace DOS cosas antes de permitir que el robot genere un video:

1) FRECUENCIA CADA 2 DÍAS (decisión del usuario, para alejarse del perfil
   de "contenido producido en masa" de la política de contenido
   inauténtico de YouTube): solo se publica si han pasado al menos
   DIAS_ENTRE_VIDEOS días completos desde la última publicación exitosa.

2) ANTI-DUPLICADOS del mismo día (por el cron de respaldo de las 21:45
   UTC): si el horario principal ya publicó hoy, la corrida de respaldo
   termina sin hacer nada.

Lee data/estado.json (la memoria del robot, committeada al repo tras cada
corrida exitosa). Nunca bloquea por error: si algo falla leyendo el
estado, se asume que SÍ toca publicar (mejor arriesgar un video de más,
detectable, que perder el video que tocaba).
"""
import datetime as dt
import json
import os

SALIDA = os.environ.get("GITHUB_OUTPUT", "/dev/null")

# Cada cuántos días se publica un video. 2 = día por medio.
DIAS_ENTRE_VIDEOS = 2


def main():
    publicar = True
    motivo = "no hay registro de publicaciones previas"
    try:
        with open("data/estado.json", encoding="utf-8") as f:
            estado = json.load(f)
        ultima = estado.get("ultima_ejecucion", "")
        if ultima:
            fecha_ultima = dt.datetime.fromisoformat(ultima).date()
            hoy_utc = dt.datetime.now(dt.timezone.utc).date()
            dias_pasados = (hoy_utc - fecha_ultima).days
            if dias_pasados == 0:
                publicar = False
                motivo = "hoy ya se publicó (esta es la corrida de respaldo)"
            elif dias_pasados < DIAS_ENTRE_VIDEOS:
                publicar = False
                motivo = (f"solo ha(n) pasado {dias_pasados} día(s) desde el último video; "
                          f"la frecuencia configurada es 1 video cada {DIAS_ENTRE_VIDEOS} días")
            else:
                motivo = f"han pasado {dias_pasados} día(s) desde el último video: toca publicar"
    except Exception as e:
        print(f"Aviso leyendo estado ({e}); se asume que SÍ toca publicar.")

    with open(SALIDA, "a", encoding="utf-8") as f:
        # Se mantiene el nombre de la variable por compatibilidad con el
        # workflow: ya_publico=true significa "NO generar nada hoy".
        f.write(f"ya_publico={'false' if publicar else 'true'}\n")

    if publicar:
        print(f"Se continúa con la generación normal ({motivo}).")
    else:
        print(f"Esta corrida termina aquí, sin generar ni publicar nada: {motivo}.")


if __name__ == "__main__":
    main()
