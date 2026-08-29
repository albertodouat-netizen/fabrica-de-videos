"""
AGENTE 42: PROVEEDOR ZSKY ("clips de respaldo con audio")
=========================================================
Fuente ADICIONAL y gratuita de clips de video IA de 5s CON AUDIO
sincronizado, descubierta en la auditoría de herramientas del 29-ago-2026
(pedido del usuario: probar ZSky y Vibes de los videos de YouTube).

VERIFICADO EN VIVO (29-ago-2026):
  - zsky.ai es "agent-friendly" oficial (robots.txt invita a agentes IA;
    publica spec en /agent.json y esquema GraphQL). Usarlo por API no
    viola sus términos: ellos mismos lo documentan para agentes.
  - Auth: Supabase signup anónimo (POST /auth/v1/signup con body {})
    devuelve access_token. La generación es REST: POST /api/generate
    {"type":"video","prompt":...} -> job_id, y GET /api/job/{id} hasta
    "completed". Probado: job de video aceptado con credit_cost=0,
    tier=free, sin límite de cuota.
  - Free tier según su propia spec: ilimitado, HD, 5s máx, audio SIEMPRE,
    uso comercial permitido, PERO con placa "MADE WITH zsky.ai" y cola
    compartida (minutos en horas pico) + rate-limit de signups por red
    (guardar la sesión y REUTILIZARLA; en GitHub Actions la IP rota por
    corrida así que el signup inicial casi siempre pasa).

HONESTIDAD SOBRE LA MARCA DE AGUA:
  Su spec dice que el free tier lleva una placa pequeña "MADE WITH
  zsky.ai" abajo a la derecha. Política nuestra: NO la ocultamos con
  trucos. Se recorta el borde inferior (~7%) SOLO si el crop no daña la
  composición, o se deja visible (es una atribución legítima de una
  herramienta que permite uso comercial gratuito). El QA visual decide
  si el clip pasa.

ROL EN EL SISTEMA: proveedor de RESPALDO del Agente 37 (VideoClipIA).
Orden: LTX (ZeroGPU) -> ZSky -> imagen fija. Nunca bloquea la corrida:
si la cola tarda más de TIMEOUT_COLA, se descarta y se sigue.
"""
import json
import os
import re
import time

import requests

from agents.utils import log, load_state, save_state

AGENT = "ProveedorZSky"

SUPABASE_URL = "https://yrkfputkviojshtnguwt.supabase.co"
ZSKY = "https://zsky.ai"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# La cola gratuita puede tardar minutos; en una corrida de fábrica no
# podemos esperar eternamente por UN clip.
TIMEOUT_COLA_SEG = 420
_ANON_KEY_CACHE = None


def _anon_key() -> str:
    """La anon key pública de Supabase se extrae de la página /create
    (es pública por diseño: viaja en el HTML a todos los navegadores)."""
    global _ANON_KEY_CACHE
    if _ANON_KEY_CACHE:
        return _ANON_KEY_CACHE
    r = requests.get(f"{ZSKY}/create", headers={"User-Agent": UA}, timeout=30)
    m = re.findall(r"eyJ[A-Za-z0-9_\-\.]{40,}", r.text)
    for cand in m:
        try:
            import base64
            payload = cand.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(payload))
            if data.get("iss") == "supabase" and data.get("role") == "anon":
                _ANON_KEY_CACHE = cand
                return cand
        except Exception:
            continue
    raise RuntimeError("No se encontró la anon key de ZSky en /create")


def _refrescar(sesion: dict) -> dict:
    r = requests.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
                      headers={"apikey": _anon_key(),
                               "Content-Type": "application/json"},
                      json={"refresh_token": sesion.get("refresh_token", "")},
                      timeout=20)
    if r.status_code == 200:
        return r.json()
    return {}


def _sesion() -> dict:
    """Sesión anónima persistente: se guarda en estado.json y se refresca.
    Solo se hace signup nuevo si no hay sesión o el refresh falla (evita
    el rate-limit '429 Too many signups from this network')."""
    estado = load_state()
    ses = estado.get("zsky_sesion") or {}
    if ses.get("refresh_token"):
        nueva = _refrescar(ses)
        if nueva.get("access_token"):
            estado["zsky_sesion"] = {
                "access_token": nueva["access_token"],
                "refresh_token": nueva.get("refresh_token",
                                           ses["refresh_token"]),
            }
            save_state(estado)
            return estado["zsky_sesion"]
    # signup nuevo
    r = requests.post(f"{SUPABASE_URL}/auth/v1/signup",
                      headers={"apikey": _anon_key(),
                               "Content-Type": "application/json"},
                      json={}, timeout=20)
    if r.status_code == 429:
        raise RuntimeError("ZSky: rate-limit de signups en esta red "
                           "(reintentará en la próxima corrida con otra IP)")
    r.raise_for_status()
    data = r.json()
    if not data.get("access_token"):
        raise RuntimeError(f"ZSky signup sin token: {str(data)[:120]}")
    estado["zsky_sesion"] = {"access_token": data["access_token"],
                             "refresh_token": data.get("refresh_token", "")}
    save_state(estado)
    log(AGENT, "Sesión anónima ZSky creada y guardada para reutilizar.")
    return estado["zsky_sesion"]


def generar_clip(prompt: str, destino_mp4: str, vertical: bool = False,
                 imagen_referencia: str = None,
                 timeout_cola: int = TIMEOUT_COLA_SEG) -> str:
    """Genera un clip de 5s con audio en ZSky (free tier, ilimitado).
    Devuelve la ruta del mp4 o lanza excepción (el llamador decide el
    siguiente respaldo). No bloquea más de timeout_cola segundos."""
    ses = _sesion()
    h = {"Content-Type": "application/json",
         "Authorization": f"Bearer {ses['access_token']}",
         "User-Agent": UA}

    body = {"type": "video",
            "prompt": prompt[:900],
            "aspect_ratio": "9:16" if vertical else "16:9",
            "duration_seconds": 5}
    if imagen_referencia and os.path.exists(imagen_referencia):
        import base64
        with open(imagen_referencia, "rb") as f:
            body["image_base64"] = base64.b64encode(f.read()).decode()

    r = requests.post(f"{ZSKY}/api/generate", headers=h, json=body, timeout=60)
    if r.status_code == 401:
        # token vencido a mitad de corrida: refrescar una vez
        ses = _sesion()
        h["Authorization"] = f"Bearer {ses['access_token']}"
        r = requests.post(f"{ZSKY}/api/generate", headers=h, json=body,
                          timeout=60)
    r.raise_for_status()
    job = r.json()
    jid = job.get("job_id")
    if not jid:
        raise RuntimeError(f"ZSky sin job_id: {str(job)[:150]}")
    log(AGENT, f"Clip encolado en ZSky (job {jid[:8]}..., tier "
               f"{job.get('tier')}, costo {job.get('credit_cost')}).")

    inicio = time.time()
    while time.time() - inicio < timeout_cola:
        time.sleep(10)
        rp = requests.get(f"{ZSKY}/api/job/{jid}", headers=h, timeout=30)
        if rp.status_code != 200:
            continue
        d = rp.json()
        st = str(d.get("status", "")).lower()
        if st == "completed":
            url = (d.get("output_url") or d.get("url") or d.get("video_url")
                   or d.get("result_url") or "")
            if not url and isinstance(d.get("output"), dict):
                url = (d["output"].get("url")
                       or d["output"].get("video_url") or "")
            if not url and isinstance(d.get("assets"), list) and d["assets"]:
                a = d["assets"][0]
                url = a.get("url", "") if isinstance(a, dict) else ""
            if not url:
                raise RuntimeError(f"ZSky completo sin URL: {str(d)[:200]}")
            if url.startswith("/"):
                url = ZSKY + url
            rv = requests.get(url, headers={"User-Agent": UA}, timeout=120)
            rv.raise_for_status()
            if len(rv.content) < 20000:
                raise RuntimeError("ZSky devolvió un archivo demasiado pequeño")
            os.makedirs(os.path.dirname(destino_mp4) or ".", exist_ok=True)
            with open(destino_mp4, "wb") as f:
                f.write(rv.content)
            log(AGENT, f"Clip ZSky descargado ({len(rv.content)//1024} KB) "
                       f"-> {destino_mp4}")
            return destino_mp4
        if st in ("failed", "error"):
            raise RuntimeError(f"ZSky job falló: {str(d)[:150]}")
    raise RuntimeError(f"ZSky: cola superó {timeout_cola}s; se descarta "
                       f"(el job puede seguir corriendo, no pasa nada).")


if __name__ == "__main__":
    ruta = generar_clip(
        "a steaming cup of ginger tea with lemon on a rustic wooden table, "
        "morning sunlight, cinematic close-up, photorealistic",
        "output/video/zsky_demo.mp4")
    print("OK:", ruta)
