#!/usr/bin/env python3
"""
Verificador de secretos (19-ago-2026): se ejecuta al inicio de cada corrida
del workflow e imprime en el log qué llaves llegaron desde GitHub Secrets y
cuáles faltan — SIN revelar jamás los valores (solo longitud y prefijo).

Por qué existe: los secretos de GitHub no se pueden leer desde afuera (ni
el dueño puede verlos una vez guardados), así que la única forma de saber
si un nombre quedó mal escrito es mirar este reporte en el log de Actions.
No falla nunca (exit 0 siempre): es solo informativo. El Vigía de Recursos
(scripts/vigia_recursos.py) es quien prueba las llaves EN VIVO y alerta.
"""
import os

ESPERADOS = {
    # nombre_en_github: (obligatoria?, para qué sirve)
    "YOUTUBE_API_KEY": (True, "API de datos de YouTube"),
    "GEMINI_API_KEY": (True, "guion/verificación (Gemini)"),
    "GROQ_API_KEY": (True, "guion (Groq)"),
    "PEXELS_API_KEY": (True, "clips de stock"),
    "PIXABAY_API_KEY": (False, "clips de stock (2a fuente)"),
    "JAMENDO_CLIENT_ID": (False, "música de fondo"),
    "MISTRAL_API_KEY": (False, "guion respaldo (Mistral Large)"),
    "OPENROUTER_API_KEY": (False, "guion respaldo (17 modelos)"),
    "CLOUDFLARE_API_TOKEN": (False, "imágenes FLUX/SDXL"),
    "CLOUDFLARE_ACCOUNT_ID": (False, "imágenes FLUX/SDXL (cuenta)"),
    "NVIDIA_API_KEY": (False, "guion respaldo (102 modelos)"),
    "CLIENT_SECRET_B64": (True, "OAuth de YouTube"),
    "TOKEN_JSON_B64": (True, "OAuth de YouTube (token)"),
}


def main():
    print("=" * 62)
    print("VERIFICADOR DE SECRETOS — qué llaves llegaron a esta corrida")
    print("=" * 62)
    faltan_obligatorias = []
    for nombre, (obligatoria, uso) in ESPERADOS.items():
        valor = os.environ.get(nombre, "")
        if valor and valor.strip():
            # Nunca imprimir el valor: solo longitud y 4 primeros caracteres
            print(f"  ✓ {nombre:<24} presente ({len(valor)} chars, "
                  f"empieza '{valor[:4]}...') — {uso}")
        else:
            marca = "✗ FALTA (OBLIGATORIA)" if obligatoria else "○ ausente (opcional)"
            print(f"  {marca} {nombre:<24} — {uso}")
            if obligatoria:
                faltan_obligatorias.append(nombre)
    print("=" * 62)
    if faltan_obligatorias:
        print(f"⚠️  ATENCIÓN: faltan obligatorias: {', '.join(faltan_obligatorias)}")
        print("   Revisa Settings -> Secrets and variables -> Actions en GitHub")
        print("   (el nombre debe ser EXACTO, en mayúsculas).")
    else:
        print("Todas las llaves obligatorias presentes. ✓")


if __name__ == "__main__":
    main()
