"""
EQUIPO DE DISEÑO DE PORTADAS (Agentes 38, 39 y 40)
==================================================
Nace del pedido del usuario (28-ago-2026): "cuando la portada es muy
llamativa atrae mucho a activarla así el título no sea lo que está
buscando". Se hizo una investigación EXCLUSIVA de portadas:

EVIDENCIA REAL (no teoría) — análisis de las miniaturas descargadas de los
151 videos ganadores del estudio de 1.630 videos (canales <5K subs con
1K+ vistas en 15 días), comparadas con las de nuestro propio canal:

  1) Los mega-ganadores del nicho salud usan TEXTO GIGANTE en bloques de
     color: amarillo sobre negro/rojo ("STOP Taking Magnesium..." 248K,
     "SÓ 1 COLHER NO CAFÉ" 58K, "AÑADE ESTO A TU AGUA" 55K,
     "107 AÑOS ELIMINA CUALQUIER DOLOR" 152K). El texto ocupa 40-60% de
     la imagen y se lee PERFECTO a tamaño de celular (168x94 px).
  2) Rostro NO es obligatorio (solo 44% de ganadores lo tienen; el
     aguacate en macro hizo 1.26M): lo que SÍ es constante es UN solo
     sujeto protagonista (alimento en macro o persona mayor feliz) +
     bloque de texto + saturación alta. Los mega-ganadores (top 20)
     tienen saturación medida 116 vs 101 del resto.
  3) Nuestras portadas actuales (verificadas bajando las 15 del canal):
     texto pequeño, gris, fondos oscuros apagados → exactamente lo
     contrario de los ganadores. Es el eslabón más débil del canal.
  4) Investigación externa 2026 coincide: texto 3-4 palabras máx, fuente
     bold 700+, contraste alto, un solo elemento director (flecha/círculo),
     diseñar para 168x94, y probar variantes (A/B).

EL EQUIPO:
  - Agente 38 DIRECTOR DE PORTADA: usa la cascada LLM para diseñar el
    CONCEPTO (estilo, palabras exactas, qué mostrar en el fondo) siguiendo
    los patrones validados. Devuelve 2 conceptos distintos (variantes).
  - Agente 39 FÁBRICA DE PORTADA: renderiza cada concepto: fondo IA
    (Pollinations flux → respaldo Cloudflare FLUX → respaldo fotograma),
    tipografía Anton (la misma familia visual de los canales virales),
    bloques amarillo/negro/rojo, cifra gigante, saturación reforzada,
    marca del canal.
  - Agente 40 AUDITOR DE PORTADA: mira las 2 variantes con Gemini
    flash-lite VISION (cuota separada, verificado) con una rúbrica de CTR
    y elige la ganadora; si no hay visión disponible, decide con métricas
    locales (saturación/viveza medidas con la misma técnica del estudio).

Si TODO el equipo falla, se cae con gracia a la miniatura clásica
(agents/thumbnail.py), así que nunca se queda un video sin portada.
"""
import base64
import json
import os
import random
import re
import time
import urllib.parse

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from agents.utils import log, load_config

TAMANO = (1280, 720)

AMARILLO = (255, 214, 0)
ROJO = (222, 30, 30)
NEGRO = (12, 12, 12)
BLANCO = (255, 255, 255)


# ---------------------------------------------------------------------------
# Utilidades compartidas
# ---------------------------------------------------------------------------

def _ruta_fuente_titulo():
    """Anton: tipografía condensada ultra-negra, la misma familia visual que
    usan las miniaturas ganadoras analizadas. Viaja con el proyecto."""
    aqui = os.path.dirname(os.path.abspath(__file__))
    candidatos = [
        os.path.join(aqui, "..", "assets", "fonts", "Anton-Regular.ttf"),
        os.path.join(aqui, "..", "assets", "fonts", "ArchivoBlack-Regular.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for c in candidatos:
        if os.path.exists(c):
            return c
    return None


def _fuente(tam):
    ruta = _ruta_fuente_titulo()
    if ruta:
        return ImageFont.truetype(ruta, tam)
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# AGENTE 38: DIRECTOR DE PORTADA
# ---------------------------------------------------------------------------
AGENT_DIRECTOR = "DirectorPortada"

_PROMPT_DIRECTOR = """Eres el director de arte de miniaturas de un canal de YouTube de salud natural en español para adultos mayores de 50 años. Diseñas portadas que compiten con las de los canales virales del nicho.

PATRONES VALIDADOS CON DATOS REALES (estudio 28-ago-2026 de 151 videos ganadores de canales pequeños):
- Texto GIGANTE de 4 a 7 palabras TOTALES repartidas en 2-3 líneas cortas (máx 3 palabras por línea, mejor 1-2).
- Las palabras deben abrir CURIOSIDAD sin repetir el título: "AÑADE ESTO", "STOP", "NUNCA HAGAS", "SOLO 1 CUCHARADA", "ELIMINA EL DOLOR".
- Si el tema tiene una CIFRA potente (edad, %, cantidad), destácala.
- El fondo muestra UN SOLO protagonista: o el alimento/remedio en primer plano macro apetitoso, o una persona mayor hispana feliz/sorprendida. Nada de collages.
- PROHIBIDO: frases genéricas ("salud natural", "bienestar"), más de 7 palabras, revelar toda la respuesta.

TITULO DEL VIDEO: "{titulo}"
TEMA/PALABRA CLAVE: "{keyword}"

Devuelve SOLO un JSON válido (sin markdown, sin explicación) con 2 variantes distintas:
{{"variantes": [
 {{"estilo": "bloque_amarillo", "lineas": ["LINEA 1", "LINEA 2", "LINEA 3"], "linea_destacada": 1, "cifra": "", "prompt_fondo": "descripcion en INGLES de la foto de fondo, un solo sujeto, subject positioned on the right half of the frame, dark simple background on the left half, vivid saturated colors, professional photography"}},
 {{"estilo": "cifra_gigante" o "alerta_roja", "lineas": [...], "linea_destacada": 0, "cifra": "60" o "", "prompt_fondo": "..."}}
]}}

Reglas del JSON:
- "lineas": 2 o 3 líneas, cada una de 1 a 3 palabras, EN MAYÚSCULAS, español.
- "linea_destacada": índice (0-based) de la línea que va en bloque amarillo.
- "cifra": solo si el estilo es cifra_gigante (un número corto, ej "60", "90%", "1"). Si no, "".
- "prompt_fondo": en inglés, foto realista, sujeto a la DERECHA del encuadre, fondo simple oscuro a la izquierda, colores vivos, sin texto, persona completamente vestida si aparece alguien, apto para todo público."""


def _extraer_json(texto: str):
    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?", "", texto).strip()
    texto = re.sub(r"```$", "", texto).strip()
    ini, fin = texto.find("{"), texto.rfind("}")
    if ini < 0 or fin <= ini:
        raise ValueError("sin JSON")
    return json.loads(texto[ini:fin + 1])


def _concepto_local(titulo: str, keyword: str):
    """Respaldo sin LLM: concepto decente construido con reglas locales."""
    conectores = {"de", "del", "la", "el", "los", "las", "para", "con", "en", "y",
                  "a", "un", "una", "que", "tu", "su", "al", "como", "cómo", "más",
                  "sin", "este", "esta", "estos", "estas", "lo", "te", "se", "si"}
    palabras = [p for p in re.findall(r"[\wÁÉÍÓÚÑáéíóúñ%]+", titulo)
                if p.lower() not in conectores and not p.isdigit()]
    vistas, fuertes = set(), []
    for p in palabras:
        if p.lower() in vistas:
            continue
        vistas.add(p.lower())
        fuertes.append(p.upper())
    fuertes = fuertes[:4] or [keyword.upper() or "SALUD"]
    lineas = []
    if len(fuertes) >= 3:
        lineas = [" ".join(fuertes[:1]), " ".join(fuertes[1:3])]
        if len(fuertes) > 3:
            lineas.append(fuertes[3])
    else:
        lineas = [fuertes[0], " ".join(fuertes[1:])] if len(fuertes) > 1 else [fuertes[0]]
    lineas = [l for l in lineas if l.strip()][:3]
    m = re.search(r"\b(\d{1,3}%?)\b", titulo)
    base = (keyword or titulo).strip()
    prompt_fondo = (
        f"extreme close-up professional photo of {base}, single main subject "
        f"positioned on the right half of the frame, dark simple background on "
        f"the left half, vivid saturated colors, dramatic warm lighting, "
        f"appetizing, high detail, no text, no watermark, family friendly"
    )
    variantes = [
        {"estilo": "bloque_amarillo", "lineas": lineas,
         "linea_destacada": min(1, len(lineas) - 1), "cifra": "",
         "prompt_fondo": prompt_fondo},
        {"estilo": "cifra_gigante" if m else "alerta_roja", "lineas": lineas,
         "linea_destacada": 0, "cifra": m.group(1) if m else "",
         "prompt_fondo": prompt_fondo},
    ]
    return {"variantes": variantes}


def disenar_conceptos(titulo: str, keyword: str) -> dict:
    """Agente 38: pide a la cascada LLM 2 conceptos de portada según los
    patrones validados. Si la cascada falla, concepto local por reglas."""
    try:
        from agents.llm_cascada import llamar_llm
        respuesta = llamar_llm(
            _PROMPT_DIRECTOR.format(titulo=titulo, keyword=keyword or titulo),
            temperatura=0.9,
        )
        data = _extraer_json(respuesta)
        variantes = data.get("variantes") or []
        limpias = []
        for v in variantes[:2]:
            lineas = [str(l).strip().upper() for l in (v.get("lineas") or []) if str(l).strip()]
            # regla dura: máx 3 líneas, máx 3 palabras por línea, máx 7 palabras totales
            lineas = [" ".join(l.split()[:3]) for l in lineas][:3]
            total = 0
            recortadas = []
            for l in lineas:
                pal = l.split()
                pal = pal[:max(0, 7 - total)]
                total += len(pal)
                if pal:
                    recortadas.append(" ".join(pal))
            if not recortadas:
                continue
            limpias.append({
                "estilo": v.get("estilo", "bloque_amarillo"),
                "lineas": recortadas,
                "linea_destacada": min(int(v.get("linea_destacada", 0) or 0), len(recortadas) - 1),
                "cifra": str(v.get("cifra", "") or "")[:4],
                "prompt_fondo": str(v.get("prompt_fondo", "") or "")[:600],
            })
        if limpias:
            log(AGENT_DIRECTOR, f"{len(limpias)} concepto(s) diseñados por la cascada LLM.")
            while len(limpias) < 2:
                limpias.append(dict(limpias[0], estilo="alerta_roja"))
            return {"variantes": limpias[:2]}
    except Exception as e:
        log(AGENT_DIRECTOR, f"Cascada LLM no disponible para el concepto ({type(e).__name__}); "
                            f"uso el diseñador local por reglas.")
    return _concepto_local(titulo, keyword)


# ---------------------------------------------------------------------------
# AGENTE 39: FÁBRICA DE PORTADA
# ---------------------------------------------------------------------------
AGENT_FABRICA = "FabricaPortada"


def _fondo_pollinations(prompt_fondo: str, destino: str, tamano=TAMANO) -> bool:
    seguro = (prompt_fondo + ", photorealistic, no text, no watermark, fully "
              "clothed if person, family friendly, safe for work")
    codificado = urllib.parse.quote(seguro)
    for _ in range(2):
        semilla = random.randint(1, 999999)
        url = (f"https://image.pollinations.ai/prompt/{codificado}"
               f"?width={tamano[0]}&height={tamano[1]}&nologo=true&seed={semilla}"
               f"&safe=true&model=flux")
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            if len(r.content) < 5000:
                continue
            with open(destino, "wb") as f:
                f.write(r.content)
            try:
                from agents.visuals import _imagen_es_segura_gemini
                if not _imagen_es_segura_gemini(destino):
                    os.remove(destino)
                    continue
            except Exception:
                pass  # sin verificador disponible: el prompt ya es estricto
            return True
        except Exception:
            continue
    return False


def _fondo_cloudflare(prompt_fondo: str, destino: str, tamano=TAMANO) -> bool:
    """Respaldo: FLUX-1 schnell de Cloudflare Workers AI (gratis)."""
    try:
        cfg = load_config()["apis"]
        token = cfg.get("cloudflare_api_token", "")
        cuenta = cfg.get("cloudflare_account_id", "")
        if not token or not cuenta or "OBTENER" in token:
            return False
        url = (f"https://api.cloudflare.com/client/v4/accounts/{cuenta}"
               f"/ai/run/@cf/black-forest-labs/flux-1-schnell")
        r = requests.post(url, headers={"Authorization": f"Bearer {token}"},
                          json={"prompt": prompt_fondo + ", photorealistic, no text"},
                          timeout=60)
        r.raise_for_status()
        b64 = r.json()["result"]["image"]
        img = Image.open(__import__("io").BytesIO(base64.b64decode(b64))).convert("RGB")
        # FLUX de Cloudflare solo entrega 1024x1024: recortar a 16:9
        w, h = img.size
        if tamano[0] >= tamano[1]:  # horizontal: recortar franjas arriba/abajo
            alto = int(w * tamano[1] / tamano[0])
            arriba = max(0, (h - alto) // 2)
            img = img.crop((0, arriba, w, min(h, arriba + alto)))
        else:  # vertical: recortar los costados
            ancho = int(h * tamano[0] / tamano[1])
            izq = max(0, (w - ancho) // 2)
            img = img.crop((izq, 0, min(w, izq + ancho), h))
        img = img.resize(tamano)
        img.save(destino, quality=92)
        return True
    except Exception:
        return False


def _fondo_desde_frame(imagen_base: str, destino: str, tamano=TAMANO) -> bool:
    try:
        if imagen_base and imagen_base.lower().endswith((".mp4", ".mov", ".webm", ".mkv")):
            from moviepy import VideoFileClip
            with VideoFileClip(imagen_base) as clip:
                frame = clip.get_frame(min(1.0, clip.duration / 2))
            Image.fromarray(frame).convert("RGB").resize(tamano).save(destino, quality=92)
            return True
        if imagen_base and os.path.exists(imagen_base):
            Image.open(imagen_base).convert("RGB").resize(tamano).save(destino, quality=92)
            return True
    except Exception:
        pass
    return False


def _preparar_lienzo(fondo_path: str, tamano=TAMANO) -> Image.Image:
    """Fondo + refuerzo de saturación (los mega-ganadores miden saturación
    116 vs 101: la viveza ES parte de la fórmula) + gradiente oscuro a la
    izquierda para que el texto explote."""
    if fondo_path and os.path.exists(fondo_path):
        base = Image.open(fondo_path).convert("RGB").resize(tamano)
    else:
        base = Image.new("RGB", tamano, (18, 40, 34))
    base = ImageEnhance.Color(base).enhance(1.35)
    base = ImageEnhance.Contrast(base).enhance(1.15)
    base = ImageEnhance.Sharpness(base).enhance(1.3)
    if tamano[0] >= tamano[1]:
        # horizontal: gradiente izquierda oscura (zona de texto), derecha libre
        grad = Image.new("L", (tamano[0], 1), 0)
        for x in range(tamano[0]):
            t = max(0.0, 1.0 - x / (tamano[0] * 0.62))
            grad.putpixel((x, 0), int(200 * t))
    else:
        # vertical (Short): gradiente abajo oscuro (el texto va en el tercio
        # inferior, lejos de la interfaz de Shorts que tapa la parte baja
        # extrema y el costado derecho)
        grad = Image.new("L", (1, tamano[1]), 0)
        for y in range(tamano[1]):
            t = max(0.0, (y / tamano[1] - 0.45) / 0.55)
            grad.putpixel((0, y), int(190 * t))
    grad = grad.resize(tamano)
    negro = Image.new("RGB", tamano, (0, 0, 0))
    base = Image.composite(negro, base, grad)
    return base


def _ajustar_tamano_fuente(lineas, max_ancho, tam_inicial=190, tam_minimo=70):
    """Busca el tamaño de fuente más grande donde TODAS las líneas caben."""
    tam = tam_inicial
    dibujo = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    while tam > tam_minimo:
        f = _fuente(tam)
        if all(dibujo.textlength(l, font=f) <= max_ancho for l in lineas):
            return tam
        tam -= 8
    return tam_minimo


def _dibujar_bloques_texto(base, lineas, idx_destacada, color_bloque=AMARILLO,
                            color_texto_bloque=NEGRO, y_inicio=None, x=46,
                            max_ancho=None):
    """El corazón del estilo ganador: cada línea sobre su propio bloque de
    color (destacada: texto negro sobre amarillo, o blanco sobre rojo; resto:
    texto blanco sobre bloque negro). Texto gigante, legible a 168x94."""
    W, H = base.size
    if max_ancho is None:
        max_ancho = int(W * 0.58) if W >= H else int(W * 0.90)
    tam = _ajustar_tamano_fuente(lineas, max_ancho)
    f = _fuente(tam)
    dr = ImageDraw.Draw(base)
    interlinea = int(tam * 1.22)
    pad = max(10, tam // 9)
    alto_total = (interlinea + pad) * len(lineas)
    if y_inicio is not None:
        y = y_inicio
    elif W >= H:
        y = max(20, (H - alto_total) // 2)
    else:
        # vertical: tercio inferior, sin tocar el 12% final (interfaz Shorts)
        y = max(20, int(H * 0.86) - alto_total)
    for i, linea in enumerate(lineas):
        # bbox REAL del texto (la fuente Anton dibuja por debajo de y+tam;
        # con el bbox el bloque de color siempre cubre el texto completo)
        bx0, by0, bx1, by1 = dr.textbbox((x, y), linea, font=f)
        rect = [bx0 - pad, by0 - pad // 2, bx1 + pad, by1 + pad // 2]
        if i == idx_destacada:
            dr.rectangle(rect, fill=color_bloque)
            dr.text((x, y), linea, font=f, fill=color_texto_bloque)
        else:
            dr.rectangle(rect, fill=(0, 0, 0))
            dr.text((x, y), linea, font=f, fill=BLANCO,
                    stroke_width=max(2, tam // 40), stroke_fill=(0, 0, 0))
        y += interlinea + pad
    return base, y


def _dibujar_marca(base):
    """Distintivo pequeño del canal (reconocimiento de marca, esquina
    superior izquierda, sin chocar con el texto principal)."""
    marca = "SALUD NATURAL DIARIA"
    try:
        marca = load_config()["canal"].get("nombre", marca).upper()
    except Exception:
        pass
    W, H = base.size
    tam_m = 26 if W >= H else 30
    f = _fuente(tam_m)
    dr = ImageDraw.Draw(base)
    tw = dr.textlength(marca, font=f)
    dr.rounded_rectangle([18, 16, 18 + tw + 22, 16 + tam_m + 16], radius=8,
                         fill=(0, 0, 0))
    dr.text((29, 24), marca, font=f, fill=(120, 230, 170))
    return base


def _componer(concepto: dict, fondo_path: str, salida: str, tamano=TAMANO) -> str:
    estilo = concepto.get("estilo", "bloque_amarillo")
    lineas = concepto.get("lineas") or ["SALUD"]
    idx = concepto.get("linea_destacada", 0)
    base = _preparar_lienzo(fondo_path, tamano)

    if estilo == "cifra_gigante" and concepto.get("cifra"):
        # Estilo "107 AÑOS" (152K vistas): número descomunal amarillo arriba
        cifra = concepto["cifra"]
        W, H = base.size
        tam_cifra = int(H * 0.42)
        f_cifra = _fuente(tam_cifra)
        dr = ImageDraw.Draw(base)
        if W >= H:
            dr.text((46, 8), cifra, font=f_cifra, fill=AMARILLO,
                    stroke_width=10, stroke_fill=(0, 0, 0))
            base, _ = _dibujar_bloques_texto(base, lineas, idx_destacada=-1,
                                             y_inicio=int(tam_cifra * 1.12))
        else:
            # vertical: cifra arriba centrada, texto en el tercio inferior
            tw_c = dr.textlength(cifra, font=f_cifra)
            dr.text(((W - tw_c) / 2, int(H * 0.10)), cifra, font=f_cifra,
                    fill=AMARILLO, stroke_width=10, stroke_fill=(0, 0, 0))
            base, _ = _dibujar_bloques_texto(base, lineas, idx_destacada=-1)
    elif estilo == "alerta_roja":
        # Estilo "STOP/NUNCA" (248K vistas): línea destacada en bloque ROJO
        # con texto blanco (misma combinación del mega-ganador del nicho)
        base, _ = _dibujar_bloques_texto(base, lineas, idx_destacada=idx,
                                         color_bloque=ROJO,
                                         color_texto_bloque=BLANCO)
    else:  # bloque_amarillo (estilo por defecto, el más repetido en ganadores)
        base, _ = _dibujar_bloques_texto(base, lineas, idx_destacada=idx)

    base = _dibujar_marca(base)
    os.makedirs(os.path.dirname(salida) or ".", exist_ok=True)
    base.save(salida, quality=95)
    return salida


def fabricar_variante(concepto: dict, imagen_base: str, salida: str, tamano=TAMANO) -> str:
    """Agente 39: genera el fondo (IA → respaldos) y compone la portada."""
    fondo_tmp = salida + "_fondo.jpg"
    ok = _fondo_pollinations(concepto.get("prompt_fondo", ""), fondo_tmp, tamano)
    if not ok:
        ok = _fondo_cloudflare(concepto.get("prompt_fondo", ""), fondo_tmp, tamano)
        if ok:
            log(AGENT_FABRICA, "Fondo generado con Cloudflare FLUX (respaldo).")
    else:
        log(AGENT_FABRICA, "Fondo generado con Pollinations flux.")
    if not ok:
        ok = _fondo_desde_frame(imagen_base, fondo_tmp, tamano)
        if ok:
            log(AGENT_FABRICA, "Fondo tomado de un fotograma real del video (respaldo).")
    ruta = _componer(concepto, fondo_tmp if ok else "", salida, tamano)
    try:
        if os.path.exists(fondo_tmp):
            os.remove(fondo_tmp)
    except OSError:
        pass
    return ruta


# ---------------------------------------------------------------------------
# AGENTE 40: AUDITOR DE PORTADA (elige la variante ganadora)
# ---------------------------------------------------------------------------
AGENT_AUDITOR = "AuditorPortada"


def _score_local(ruta: str) -> float:
    """Métrica local (misma técnica del estudio de miniaturas ganadoras):
    saturación media + % de píxeles vivos. Sirve de desempate sin visión."""
    try:
        import numpy as np
        img = Image.open(ruta).convert("HSV").resize((320, 180))
        a = np.asarray(img).astype("float32")
        sat = a[:, :, 1].mean()
        vivid = float(((a[:, :, 1] > 150) & (a[:, :, 2] > 150)).mean())
        return sat / 255.0 + vivid * 2.0
    except Exception:
        return 0.0


def _auditar_con_vision(rutas, titulo: str):
    """Una sola llamada a gemini-flash-lite (cuota separada verificada) con
    las 2 variantes: rúbrica de CTR según los criterios validados."""
    cfg = load_config()["apis"]
    key = cfg.get("gemini_api_key", "")
    if not key or "OBTENER" in key:
        return None
    partes = [{"text": (
        f"Eres auditor experto de miniaturas de YouTube para el nicho salud "
        f"50+. Video: \"{titulo}\". Te muestro 2 miniaturas (A y B). "
        f"Evalúa cada una de 0 a 10 según: (1) ¿el texto se leería en un "
        f"celular a tamaño pequeño?, (2) contraste y colores vivos, "
        f"(3) un solo protagonista claro y apetitoso/emotivo, (4) abre "
        f"curiosidad sin ser engañosa, (5) parece de canal grande y "
        f"profesional. Responde SOLO: GANADORA:<A o B>|CTR_A:<n>|CTR_B:<n>"
    )}]
    for ruta in rutas:
        with open(ruta, "rb") as f:
            partes.append({"inline_data": {"mime_type": "image/png",
                                           "data": base64.b64encode(f.read()).decode()}})
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"gemini-flash-lite-latest:generateContent?key={key}")
    for intento in range(3):
        try:
            r = requests.post(url, json={"contents": [{"parts": partes}]}, timeout=60)
            if r.status_code in (429, 500, 503) and intento < 2:
                time.sleep(10 * (intento + 1))
                continue
            r.raise_for_status()
            texto = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
            m = re.search(r"GANADORA\s*:?\s*([AB])", texto)
            sa = re.search(r"CTR_A\s*:?\s*(\d{1,2})", texto)
            sb = re.search(r"CTR_B\s*:?\s*(\d{1,2})", texto)
            if m:
                return {"ganadora": 0 if m.group(1) == "A" else 1,
                        "score_a": int(sa.group(1)) if sa else -1,
                        "score_b": int(sb.group(1)) if sb else -1}
        except Exception:
            break
    return None


def elegir_ganadora(rutas, titulo: str) -> str:
    """Agente 40: decide qué variante se publica."""
    rutas = [r for r in rutas if r and os.path.exists(r)]
    if not rutas:
        raise RuntimeError("ninguna variante de portada existe")
    if len(rutas) == 1:
        return rutas[0]
    veredicto = _auditar_con_vision(rutas[:2], titulo)
    if veredicto:
        idx = veredicto["ganadora"]
        log(AGENT_AUDITOR, f"Visión IA eligió la variante {'A' if idx == 0 else 'B'} "
                           f"(CTR estimado A={veredicto['score_a']}, B={veredicto['score_b']}).")
        return rutas[idx]
    scores = [_score_local(r) for r in rutas]
    idx = scores.index(max(scores))
    log(AGENT_AUDITOR, f"Sin visión disponible: elegida variante {'A' if idx == 0 else 'B'} "
                       f"por métricas locales de viveza ({scores[0]:.2f} vs {scores[1]:.2f}).")
    return rutas[idx]


# ---------------------------------------------------------------------------
# ENTRADA PRINCIPAL DEL EQUIPO
# ---------------------------------------------------------------------------

def generar_portada_elite(guion, imagen_base: str, salida_png: str,
                          vertical: bool = False) -> str:
    """Pipeline completo del equipo: Director → Fábrica (x2) → Auditor.
    vertical=True produce 720x1280 para Shorts (texto en tercio inferior,
    fuera de la zona que tapa la interfaz de Shorts).
    Lanza excepción si nada funcionó (el llamador cae a la miniatura
    clásica, ver agents/thumbnail.py)."""
    tamano = (720, 1280) if vertical else TAMANO
    if isinstance(guion, dict):
        titulo = guion.get("titulo", "")
        keyword = guion.get("keyword_principal", "")
    else:
        titulo, keyword = (guion or ""), ""

    conceptos = disenar_conceptos(titulo, keyword)["variantes"]
    rutas = []
    for i, concepto in enumerate(conceptos[:2]):
        destino = salida_png + f"_v{'AB'[i]}.png"
        try:
            rutas.append(fabricar_variante(concepto, imagen_base, destino, tamano))
            log(AGENT_FABRICA, f"Variante {'AB'[i]} lista: estilo {concepto.get('estilo')} "
                               f"| texto: {' / '.join(concepto.get('lineas', []))}")
        except Exception as e:
            log(AGENT_FABRICA, f"Variante {'AB'[i]} falló ({type(e).__name__}).")

    ganadora = elegir_ganadora(rutas, titulo)
    os.makedirs(os.path.dirname(salida_png) or ".", exist_ok=True)
    Image.open(ganadora).save(salida_png, quality=95)
    # limpiar variantes intermedias (la ganadora ya quedó copiada)
    for r in rutas:
        try:
            os.remove(r)
        except OSError:
            pass
    log(AGENT_AUDITOR, f"Portada élite final -> {salida_png}")
    return salida_png
