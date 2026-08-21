#!/usr/bin/env python3
"""
AGENTE 35: VIGÍA DE RECURSOS ("VigiaRecursos") — creado 19-ago-2026
--------------------------------------------------------------------
Nace de dos desastres reales:
 1. Groq eliminó su modelo sin aviso (19-ago-2026) -> video de plantilla.
 2. Cerebras cambió su política a "tarjeta obligatoria" semanas después de
    que las guías decían "gratis sin tarjeta".

Moraleja: los recursos gratuitos MUEREN EN SILENCIO. Este script los prueba
EN VIVO (petición real, no suposición) y falla a propósito (exit code 1) si
algún recurso CRÍTICO está caído, para que GitHub Actions envíe el correo de
alerta al dueño (mismo mecanismo del vigilante de publicaciones).

Criticidad:
 - CRÍTICO: si TODOS los proveedores de guion fallan, o si Pexels+Pixabay
   fallan a la vez, o si edge-tts falla (sin voz no hay video).
 - AVISO: cualquier proveedor individual caído (la cascada lo cubre, pero
   conviene saberlo antes de que caigan todos).

Se ejecuta semanalmente (cron en .github/workflows/vigia_recursos.yml) y
puede lanzarse manualmente con Run workflow.
"""
import os
import sys

# Permite ejecutarlo desde la raíz del repo (como hace el workflow)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from agents.utils import load_config, log

AGENT = "VigiaRecursos"

RESULTADOS = []  # (nombre, ok, detalle)


def _reg(nombre, ok, detalle=""):
    RESULTADOS.append((nombre, ok, detalle))
    log(AGENT, f"{'✓' if ok else '✗'} {nombre}: {detalle if detalle else ('OK' if ok else 'FALLÓ')}")


def probar_groq(cfg):
    key = cfg["apis"].get("groq_api_key", "") or ""
    if not key or "OBTENER_GRATIS" in key:
        _reg("Groq", False, "sin llave configurada")
        return False
    try:
        from agents.utils import modelo_groq
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                          headers={"Authorization": f"Bearer {key}"},
                          json={"model": modelo_groq(key),
                                "messages": [{"role": "user", "content": "ok"}],
                                "max_tokens": 5}, timeout=30)
        ok = r.status_code == 200
        _reg("Groq", ok, f"HTTP {r.status_code}")
        return ok
    except Exception as e:
        _reg("Groq", False, str(e)[:80])
        return False


def probar_gemini(cfg):
    key = cfg["apis"].get("gemini_api_key", "") or ""
    if not key or "OBTENER_GRATIS" in key:
        _reg("Gemini", False, "sin llave configurada")
        return False
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={key}",
            json={"contents": [{"parts": [{"text": "ok"}]}]}, timeout=45)
        # 429 = llave viva pero cuota del día agotada: cuenta como VIVO
        ok = r.status_code in (200, 429)
        _reg("Gemini", ok, f"HTTP {r.status_code}" + (" (cuota diaria agotada, llave viva)" if r.status_code == 429 else ""))
        return ok
    except Exception as e:
        _reg("Gemini", False, str(e)[:80])
        return False


def probar_mistral(cfg):
    key = cfg["apis"].get("mistral_api_key", "") or ""
    if not key or "OBTENER_GRATIS" in key:
        _reg("Mistral", False, "sin llave configurada")
        return False
    try:
        r = requests.get("https://api.mistral.ai/v1/models",
                         headers={"Authorization": f"Bearer {key}"}, timeout=30)
        ok = r.status_code == 200
        _reg("Mistral", ok, f"HTTP {r.status_code}")
        return ok
    except Exception as e:
        _reg("Mistral", False, str(e)[:80])
        return False


def probar_openrouter(cfg):
    key = cfg["apis"].get("openrouter_api_key", "") or ""
    if not key or "OBTENER_GRATIS" in key:
        _reg("OpenRouter", False, "sin llave configurada")
        return False
    try:
        r = requests.get("https://openrouter.ai/api/v1/auth/key",
                         headers={"Authorization": f"Bearer {key}"}, timeout=30)
        ok = r.status_code == 200
        _reg("OpenRouter", ok, f"HTTP {r.status_code}")
        return ok
    except Exception as e:
        _reg("OpenRouter", False, str(e)[:80])
        return False


def probar_nvidia(cfg):
    key = cfg["apis"].get("nvidia_api_key", "") or ""
    if not key or "OBTENER_GRATIS" in key:
        _reg("NVIDIA", False, "sin llave configurada")
        return False
    try:
        r = requests.get("https://integrate.api.nvidia.com/v1/models",
                         headers={"Authorization": f"Bearer {key}"}, timeout=30)
        ok = r.status_code == 200
        _reg("NVIDIA", ok, f"HTTP {r.status_code}")
        return ok
    except Exception as e:
        _reg("NVIDIA", False, str(e)[:80])
        return False


def probar_deepseek(cfg):
    key = cfg["apis"].get("deepseek_api_key", "") or ""
    if not key or "OBTENER_GRATIS" in key:
        _reg("DeepSeek", False, "sin llave (opcional)")
        return False
    try:
        r = requests.get("https://api.deepseek.com/user/balance",
                         headers={"Authorization": f"Bearer {key}"}, timeout=30)
        if r.status_code == 200:
            info = r.json().get("balance_infos", [{}])
            saldo = info[0].get("total_balance", "?") if info else "?"
            _reg("DeepSeek", True, f"saldo: {saldo}")
            return True
        _reg("DeepSeek", False, f"HTTP {r.status_code}")
        return False
    except Exception as e:
        _reg("DeepSeek", False, str(e)[:80])
        return False


def probar_pexels(cfg):
    key = cfg["apis"].get("pexels_api_key", "") or ""
    if not key or "OBTENER_GRATIS" in key:
        _reg("Pexels", False, "sin llave configurada")
        return False
    try:
        r = requests.get("https://api.pexels.com/videos/search?query=nature&per_page=1",
                         headers={"Authorization": key}, timeout=30)
        ok = r.status_code == 200
        restante = r.headers.get("X-Ratelimit-Remaining", "?")
        _reg("Pexels", ok, f"HTTP {r.status_code}, quedan {restante} peticiones/mes")
        return ok
    except Exception as e:
        _reg("Pexels", False, str(e)[:80])
        return False


def probar_pixabay(cfg):
    key = cfg["apis"].get("pixabay_api_key", "") or ""
    if not key or "OBTENER_GRATIS" in key:
        _reg("Pixabay", False, "sin llave configurada")
        return False
    try:
        r = requests.get("https://pixabay.com/api/videos/",
                         params={"key": key, "q": "nature", "per_page": 3}, timeout=30)
        ok = r.status_code == 200
        _reg("Pixabay", ok, f"HTTP {r.status_code}")
        return ok
    except Exception as e:
        _reg("Pixabay", False, str(e)[:80])
        return False


def probar_cloudflare(cfg):
    token = cfg["apis"].get("cloudflare_api_token", "") or ""
    account = cfg["apis"].get("cloudflare_account_id", "") or ""
    if not token or "OBTENER_GRATIS" in token or not account:
        _reg("Cloudflare", False, "sin llaves configuradas")
        return False
    try:
        r = requests.get("https://api.cloudflare.com/client/v4/user/tokens/verify",
                         headers={"Authorization": f"Bearer {token}"}, timeout=30)
        ok = r.status_code == 200 and r.json().get("result", {}).get("status") == "active"
        _reg("Cloudflare", ok, "token activo" if ok else f"HTTP {r.status_code}")
        return ok
    except Exception as e:
        _reg("Cloudflare", False, str(e)[:80])
        return False


def probar_pollinations():
    try:
        r = requests.get("https://image.pollinations.ai/prompt/test?width=64&height=64&nologo=true",
                         timeout=60)
        ok = r.status_code == 200 and len(r.content) > 1000
        _reg("Pollinations(img)", ok, f"HTTP {r.status_code}")
        return ok
    except Exception as e:
        _reg("Pollinations(img)", False, str(e)[:80])
        return False


def probar_jamendo(cfg):
    cid = cfg["apis"].get("jamendo_client_id", "") or ""
    if not cid or "OBTENER_GRATIS" in cid:
        _reg("Jamendo", False, "sin client_id configurado")
        return False
    try:
        r = requests.get("https://api.jamendo.com/v3.0/tracks/",
                         params={"client_id": cid, "format": "json", "limit": 1,
                                 "tags": "calm", "ccnc": "false"}, timeout=30)
        ok = r.status_code == 200 and r.json().get("headers", {}).get("status") == "success"
        _reg("Jamendo", ok, "responde" if ok else f"HTTP {r.status_code}")
        return ok
    except Exception as e:
        _reg("Jamendo", False, str(e)[:80])
        return False


def probar_edge_tts():
    try:
        import asyncio
        import edge_tts
        ruta = "/tmp/vigia_tts.mp3"

        async def _t():
            c = edge_tts.Communicate("prueba", "es-MX-JorgeNeural")
            await c.save(ruta)
        asyncio.run(_t())
        ok = os.path.exists(ruta) and os.path.getsize(ruta) > 1000
        _reg("edge-tts", ok, f"{os.path.getsize(ruta)//1024} KB" if ok else "audio vacío")
        return ok
    except Exception as e:
        _reg("edge-tts", False, str(e)[:80])
        return False


def probar_europepmc():
    try:
        r = requests.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                         params={"query": "chamomile sleep", "format": "json", "pageSize": 1},
                         timeout=30)
        ok = r.status_code == 200
        _reg("EuropePMC", ok, f"HTTP {r.status_code}")
        return ok
    except Exception as e:
        _reg("EuropePMC", False, str(e)[:80])
        return False


def main():
    cfg = load_config()
    log(AGENT, "=== INSPECCIÓN SEMANAL DEL ARSENAL (todo probado EN VIVO) ===")

    # Cerebros (guion)
    cerebros_vivos = sum([probar_groq(cfg), probar_gemini(cfg), probar_mistral(cfg),
                          probar_openrouter(cfg), probar_nvidia(cfg),
                          probar_deepseek(cfg)])
    # Visuales
    stock_vivo = sum([probar_pexels(cfg), probar_pixabay(cfg)])
    ia_img_viva = sum([probar_cloudflare(cfg), probar_pollinations()])
    # Voz, música, ciencia
    voz_viva = probar_edge_tts()
    probar_jamendo(cfg)
    probar_europepmc()

    log(AGENT, f"=== RESUMEN: {sum(1 for _, ok, _ in RESULTADOS if ok)}/{len(RESULTADOS)} recursos vivos ===")

    fallas_criticas = []
    if cerebros_vivos == 0:
        fallas_criticas.append("NINGÚN proveedor de guion responde (se repetiría el 19-ago)")
    elif cerebros_vivos <= 1:
        fallas_criticas.append(f"Solo {cerebros_vivos} cerebro vivo de 5: margen de seguridad agotándose")
    if stock_vivo == 0:
        fallas_criticas.append("Pexels Y Pixabay caídos: sin clips de stock")
    if ia_img_viva == 0:
        fallas_criticas.append("Cloudflare Y Pollinations caídos: sin imágenes IA")
    if not voz_viva:
        fallas_criticas.append("edge-tts caído: SIN VOZ no hay videos")

    if fallas_criticas:
        log(AGENT, "🚨 FALLAS CRÍTICAS DETECTADAS:")
        for f in fallas_criticas:
            log(AGENT, f"   - {f}")
        log(AGENT, "Este workflow falla A PROPÓSITO para que te llegue el correo de alerta de GitHub.")
        sys.exit(1)

    log(AGENT, "Arsenal sano. Nada que hacer esta semana. 💪")


if __name__ == "__main__":
    main()
