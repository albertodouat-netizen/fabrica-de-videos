#!/usr/bin/env python3
"""
Candado anti doble publicación (añadido 15-ago-2026, junto con el cron de
respaldo del workflow). Como ahora hay DOS horarios programados por día
(el principal 19:30 UTC y el respaldo 21:45 UTC, porque GitHub a veces se
salta el primero), este script se ejecuta ANTES de generar nada:

  - Lee data/estado.json (la memoria del robot, ya committeada al repo).
  - Si la última ejecución exitosa fue HOY (fecha UTC), significa que el
    horario principal sí corrió: escribe "ya_publico=true" en la salida de
    GitHub Actions y el workflow se salta la generación (0 minutos
    gastados, sin video duplicado).
  - Si no hay publicación hoy, deja continuar normalmente.

Nunca bloquea por error: si algo falla leyendo el estado, se asume que NO
se ha publicado (mejor arriesgar un duplicado detectable que perder el
video del día).
"""
import datetime as dt
import json
import os

SALIDA = os.environ.get("GITHUB_OUTPUT", "/dev/null")


def main():
    ya_publico = False
    try:
        with open("data/estado.json", encoding="utf-8") as f:
            estado = json.load(f)
        ultima = estado.get("ultima_ejecucion", "")
        if ultima:
            fecha_ultima = dt.datetime.fromisoformat(ultima).date()
            hoy_utc = dt.datetime.utcnow().date()
            ya_publico = (fecha_ultima == hoy_utc)
    except Exception as e:
        print(f"Aviso leyendo estado ({e}); se asume que NO se ha publicado hoy.")

    with open(SALIDA, "a", encoding="utf-8") as f:
        f.write(f"ya_publico={'true' if ya_publico else 'false'}\n")

    if ya_publico:
        print("Hoy ya se publicó un video (horario principal OK). Esta corrida de "
              "respaldo termina aquí, sin generar ni publicar nada duplicado.")
    else:
        print("No hay publicación registrada hoy: se continúa con la generación normal.")


if __name__ == "__main__":
    main()
