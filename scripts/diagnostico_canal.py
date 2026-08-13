#!/usr/bin/env python3
"""
Script de diagnóstico: confirma en segundos a qué canal de YouTube están
conectadas las credenciales actuales, ANTES de gastar 15-20 minutos
generando un video completo. Se usa desde el workflow de GitHub Actions.
"""
import pickle
import sys
import googleapiclient.discovery


def main():
    try:
        with open("config/token.json", "rb") as f:
            creds = pickle.load(f)
    except Exception as e:
        print(f"❌ No se pudo leer config/token.json: {e}")
        sys.exit(1)

    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
    resp = youtube.channels().list(part="snippet,statistics", mine=True).execute()

    items = resp.get("items", [])
    if not items:
        print("❌ Las credenciales no devolvieron ningún canal.")
        sys.exit(1)

    canal = items[0]
    print("=" * 60)
    print("DIAGNÓSTICO DE CANAL CONECTADO")
    print("=" * 60)
    print(f"Nombre del canal: {canal['snippet']['title']}")
    print(f"ID del canal:     {canal['id']}")
    print(f"Suscriptores:     {canal['statistics'].get('subscriberCount')}")
    print("=" * 60)

    if canal["snippet"]["title"] != "Salud Natural Diaria":
        print("⚠️ ADVERTENCIA: este NO es el canal 'Salud Natural Diaria'.")
        print("   El video que se va a generar ahora se publicará en el canal de arriba.")
    else:
        print("✅ Canal correcto confirmado: Salud Natural Diaria.")


if __name__ == "__main__":
    main()
