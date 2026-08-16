#!/usr/bin/env python3
"""
VIGILANTE DE PUBLICACIONES (añadido 16-ago-2026, pedido del usuario:
"¿cómo me entero si GitHub se salta la publicación?").

Cómo funciona la alerta (ingenioso pero simple):
  - GitHub envía automáticamente un CORREO al dueño del repositorio cada
    vez que un workflow FALLA (y una notificación push si tiene la app de
    GitHub en el celular).
  - Este script corre en su propio workflow (vigilante.yml) a una hora
    DISTINTA de las corridas de publicación. Revisa la memoria del robot
    (data/estado.json): si la última publicación es más vieja de lo que
    permite la frecuencia configurada (2 días) + 1 día de gracia,
    TERMINA CON ERROR a propósito.
  - Ese error hace que GitHub le mande al usuario el correo/notificación:
    "Vigilante de publicaciones: failed". Ese correo ES la alerta de que
    algo no se publicó cuando tocaba.

Si todo está en orden, termina en verde y no molesta a nadie.

Por qué un workflow separado y a otra hora: si GitHub se salta el cron de
publicación de las 19:30, casi nunca se salta TAMBIÉN otro cron distinto a
otra hora del día. Y aunque el vigilante se saltara un día, al día
siguiente vuelve a revisar (la condición mira días acumulados, no un
momento puntual).
"""
import datetime as dt
import json
import sys

# Debe coincidir con scripts/verificar_si_ya_publico_hoy.py
DIAS_ENTRE_VIDEOS = 2
# Margen de gracia: 1 día extra antes de alarmar (evita falsas alarmas por
# desfases de zona horaria o corridas tardías del cron de respaldo).
DIAS_DE_GRACIA = 1


def main():
    try:
        with open("data/estado.json", encoding="utf-8") as f:
            estado = json.load(f)
        ultima = estado.get("ultima_ejecucion", "")
        if not ultima:
            print("Aún no hay ninguna publicación registrada; el vigilante no alarma "
                  "en un canal recién configurado.")
            return 0
        fecha_ultima = dt.datetime.fromisoformat(ultima).date()
        hoy_utc = dt.datetime.now(dt.timezone.utc).date()
        dias_pasados = (hoy_utc - fecha_ultima).days
        limite = DIAS_ENTRE_VIDEOS + DIAS_DE_GRACIA

        print(f"Última publicación registrada: {fecha_ultima} "
              f"({dias_pasados} día(s) atrás). Límite antes de alarmar: {limite} días.")

        if dias_pasados > limite:
            print()
            print("🚨 ALERTA: el robot NO ha publicado ningún video en "
                  f"{dias_pasados} días (lo esperado es 1 video cada "
                  f"{DIAS_ENTRE_VIDEOS} días).")
            print("Posibles causas: GitHub se saltó los dos horarios del cron, "
                  "una corrida falló a mitad de camino, o hay un secret vencido.")
            print("Qué hacer: entra a la pestaña Actions del repositorio, revisa "
                  "la última corrida (busca pasos con ❌) y, si simplemente no "
                  "hubo corrida, lanza una manual con 'Run workflow'.")
            print()
            print("(Este error es INTENCIONAL: hace que GitHub te envíe el "
                  "correo/notificación de alerta que estás leyendo.)")
            return 1

        print("Todo en orden: la última publicación está dentro de lo esperado. ✓")
        return 0
    except Exception as e:
        # Si no se puede leer el estado, mejor alarmar que callar.
        print(f"🚨 ALERTA: no se pudo verificar el estado de publicaciones ({e}).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
