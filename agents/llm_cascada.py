"""
CASCADA UNIVERSAL DE PROVEEDORES DE IA (creada 19-ago-2026)
------------------------------------------------------------
Nace del desastre del 19-ago-2026: Groq eliminó su modelo sin aviso y la
cuota gratuita de Gemini estaba agotada; el sistema se quedó sin cerebro
y publicó un video de plantilla genérica que dañó el canal.

Este módulo es la solución definitiva: UNA sola función `llamar_llm(prompt)`
que prueba EN ORDEN todos los proveedores gratuitos verificados hasta que
uno responda. Si todos fallan, lanza excepción (nunca degrada a plantilla).

Proveedores (todos verificados EN VIVO el 19-ago-2026 con las llaves del
usuario):
  1. Groq        - 1.000 req/día, modelo elegido en vivo (utils.modelo_groq)
  2. Gemini      - gemini-flash-latest (alias siempre vigente)
  3. Mistral     - mistral-large-latest, 1.000M tokens/mes, 4 req/min
  4. OpenRouter  - modelos :free (varios, se prueban en orden)
  5. NVIDIA NIM  - 102 modelos, sin tope diario, 40 req/min

Notas de diseño:
- Cada proveedor se salta silenciosamente si su llave no está configurada
  (placeholder "OBTENER_GRATIS"). Así el mismo código funciona en local y
  en GitHub Actions aunque falte algún secreto.
- Mistral va ANTES que OpenRouter porque su modelo (Large) es más capaz y
  su cuota mensual es gigante; OpenRouter y NVIDIA cierran la fila porque
  sus modelos gratis varían de calidad.
- NVIDIA sufre "arranque en frío" (la 1a petición a un modelo puede tardar
  >90s o dar timeout): por eso usa timeout amplio y 2 intentos.
- Los modelos con razonamiento (gpt-oss, nemotron) a veces devuelven su
  cadena de pensamiento; quien llama debe extraer el JSON con las
  utilidades existentes (_extraer_json de scriptwriter ya lo hace).
"""
import time

import requests

from agents.utils import load_config, log, modelo_groq

AGENT = "LLM-Cascada"

# Modelos :free de OpenRouter en orden de preferencia (verificados 19-ago-2026;
# la lista completa cambia seguido, por eso se prueban varios).
_OPENROUTER_MODELOS_FREE = [
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "z-ai/glm-5.2:free",
]

# Modelos de NVIDIA NIM en orden de preferencia (verificados 19-ago-2026).
_NVIDIA_MODELOS = [
    "nvidia/nemotron-3.5-lightning-30b-a3b",   # respondió en 2.4s en la prueba
    "meta/llama-3.3-70b-instruct",
    "moonshotai/kimi-k2.6",
]


def _llamar_groq_cascada(prompt, key, temperatura=0.8):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": modelo_groq(key),
              "messages": [{"role": "user", "content": prompt}],
              "temperature": temperatura},
        timeout=90)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _llamar_gemini_cascada(prompt, key, temperatura=0.8):
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={key}",
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": temperatura}},
        timeout=120)
    r.raise_for_status()
    try:
        from agents.presupuesto_ia import registrar_uso_gemini
        registrar_uso_gemini(1)
    except Exception:
        pass
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _llamar_mistral_cascada(prompt, key, temperatura=0.8):
    # Mistral gratis: 4 req/min. Si responde 429, espera y reintenta 1 vez.
    for intento in range(2):
        r = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": "mistral-large-latest",
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": temperatura},
            timeout=120)
        if r.status_code == 429 and intento == 0:
            log(AGENT, "Mistral en límite por minuto (4 req/min); esperando 20s...")
            time.sleep(20)
            continue
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    raise RuntimeError("Mistral no respondió tras reintento")


def _llamar_openrouter_cascada(prompt, key, temperatura=0.8):
    ultimo_error = None
    for modelo in _OPENROUTER_MODELOS_FREE:
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": modelo,
                      "messages": [{"role": "user", "content": prompt}],
                      "temperature": temperatura},
                timeout=120)
            r.raise_for_status()
            contenido = r.json()["choices"][0]["message"].get("content") or ""
            if contenido.strip():
                return contenido
        except Exception as e:
            ultimo_error = e
            continue  # el siguiente modelo :free
    raise ultimo_error or RuntimeError("Ningún modelo :free de OpenRouter respondió")


def _llamar_deepseek_cascada(prompt, key, temperatura=0.8):
    """DeepSeek API (investigado 21-ago-2026 tras el video del usuario):
    5 MILLONES de tokens gratis al registrarse (sin tarjeta), válidos 30
    días. API compatible con OpenAI. OJO: NO es ilimitado — lo gratis
    ilimitado es su chat web (sin API) y su Harness (herramienta de
    programación, no aplicable aquí). Se usa como cerebro adicional
    mientras duren los tokens; cuando se agoten, la cascada simplemente
    lo salta (error → siguiente proveedor)."""
    r = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": "deepseek-v4-flash",
              "messages": [{"role": "user", "content": prompt}],
              "temperature": temperatura},
        timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _llamar_nvidia_cascada(prompt, key, temperatura=0.8):
    ultimo_error = None
    for modelo in _NVIDIA_MODELOS:
        # 2 intentos por modelo: el primero puede morir por arranque en frío
        for intento in range(2):
            try:
                r = requests.post(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}",
                             "Accept": "application/json"},
                    json={"model": modelo,
                          "messages": [{"role": "user", "content": prompt}],
                          "temperature": temperatura,
                          "max_tokens": 4096},
                    timeout=150)
                r.raise_for_status()
                contenido = r.json()["choices"][0]["message"].get("content") or ""
                if contenido.strip():
                    return contenido
                break  # respuesta vacía: probar otro modelo
            except requests.exceptions.Timeout:
                ultimo_error = RuntimeError(f"timeout con {modelo}")
                continue  # reintentar el mismo modelo una vez
            except Exception as e:
                ultimo_error = e
                break  # error real: probar otro modelo
    raise ultimo_error or RuntimeError("Ningún modelo de NVIDIA respondió")


# Orden de la cascada. Cada entrada: (nombre, clave_en_config, función).
_CASCADA = [
    ("groq", "groq_api_key", _llamar_groq_cascada),
    ("gemini", "gemini_api_key", _llamar_gemini_cascada),
    ("deepseek", "deepseek_api_key", _llamar_deepseek_cascada),
    ("mistral", "mistral_api_key", _llamar_mistral_cascada),
    ("openrouter", "openrouter_api_key", _llamar_openrouter_cascada),
    ("nvidia", "nvidia_api_key", _llamar_nvidia_cascada),
]


def llamar_llm(prompt: str, temperatura: float = 0.8,
               preferido: str = None) -> str:
    """Prueba todos los proveedores en orden hasta que uno responda.
    `preferido` (opcional) se intenta primero. Lanza RuntimeError si TODOS
    fallan: quien llama decide qué hacer (nunca degradar a plantilla)."""
    cfg = load_config()
    apis = cfg.get("apis", {})

    orden = list(_CASCADA)
    if preferido:
        orden.sort(key=lambda t: 0 if t[0] == preferido else 1)

    errores = []
    for nombre, clave_cfg, funcion in orden:
        key = apis.get(clave_cfg, "") or ""
        if not key or "OBTENER_GRATIS" in key:
            continue
        try:
            respuesta = funcion(prompt, key, temperatura)
            if respuesta and respuesta.strip():
                log(AGENT, f"Respuesta obtenida de '{nombre}'.")
                return respuesta
        except Exception as e:
            errores.append(f"{nombre}: {type(e).__name__} {str(e)[:80]}")
            log(AGENT, f"Proveedor '{nombre}' falló ({type(e).__name__}); probando el siguiente...")
            continue

    raise RuntimeError(
        "TODOS los proveedores de IA fallaron. Detalle: " + " | ".join(errores)
    )
