#!/usr/bin/env python3
"""
EJECUTAR UNA SOLA VEZ, EN TU PROPIA COMPUTADORA (no en la nube).
------------------------------------------------------------------
Este script abre tu navegador para autorizar el acceso a TU canal de
YouTube. Al terminar, genera config/token.json. Ese archivo es la "llave"
que luego usará el robot para publicar sin volver a pedirte nada.

Requisitos previos (gratis, una sola vez):
1) Crear un proyecto en https://console.cloud.google.com/
2) Activar "YouTube Data API v3" (Library > buscar > Enable)
3) Ir a "APIs & Services > Credentials > Create credentials > OAuth client ID"
   - Tipo de aplicación: "Desktop app"
   - Descargar el JSON generado y guardarlo como: config/client_secret.json
4) Ejecutar este script:  python3 setup_youtube_auth.py
5) Se abrirá tu navegador, inicia sesión con la cuenta de Google dueña del
   canal de YouTube y acepta los permisos.
6) Listo. Sube config/token.json a un lugar seguro (ver README sobre cómo
   usarlo en GitHub Actions para automatización 100% en la nube).
"""
import os
import pickle
import google_auth_oauthlib.flow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube",
          "https://www.googleapis.com/auth/youtube.force-ssl"]  # necesario para subir subtítulos

CLIENT_SECRET = "config/client_secret.json"
TOKEN_PATH = "config/token.json"


def main():
    if not os.path.exists(CLIENT_SECRET):
        print(f"❌ No se encontró {CLIENT_SECRET}.")
        print("   Descárgalo desde Google Cloud Console (ver instrucciones arriba) y vuelve a intentar.")
        return

    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(TOKEN_PATH, "wb") as f:
        pickle.dump(creds, f)

    print(f"✅ Autorización completada. Se guardó {TOKEN_PATH}.")
    print("   A partir de ahora, orchestrator.py puede publicar en tu canal sin pedirte nada más.")


if __name__ == "__main__":
    main()
