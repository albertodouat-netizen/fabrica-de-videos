"""
AGENTE 21: PRESENTADOR / ROSTRO HUMANO DEL CANAL ("Avatar Presentador")
----------------------------------------------------------------------
Por qué existe este agente (léelo antes de tocar nada):

En 2026 el algoritmo de YouTube favorece videos con un rostro humano real
en cámara (dato investigado y documentado en este proyecto). Un canal
100% "faceless" (sin nadie en pantalla) parte con una desventaja
algorítmica, aunque el contenido sea igual de bueno.

SOLUCIÓN HONESTA (lee esto para no prometer de más al usuario):
Contratar un presentador real, o generar un AVATAR HABLANTE con
sincronización labial perfecta (lip-sync) de calidad broadcast, requiere
herramientas de pago (HeyGen, D-ID, Synthesia) o infraestructura con GPU
que NO es gratis ni corre de forma confiable en GitHub Actions (que solo
tiene CPU y un límite de minutos gratis al mes). Prometer un "avatar
hablando perfectamente sincronizado, 100% gratis, todos los días" sería
faltar a la regla de este proyecto de nunca prometer algo que no se puede
cumplir de verdad.

LO QUE SÍ SE PUEDE HACER, 100% gratis y de forma confiable:
  1) Generar (UNA sola vez, no en cada video) una foto realista de un
     presentador/presentadora fijo para el canal, con Pollinations.ai
     (gratis, sin key). Se usa SIEMPRE la misma persona (misma semilla +
     misma descripción) para que el canal tenga una cara reconocible y
     consistente en el tiempo, como cualquier canal con "host" fijo.
  2) Esa foto se muestra en pantalla (con el mismo efecto de zoom lento
     "Ken Burns" que ya usa el resto del video, para que no se vea
     estática) exactamente en los 3 momentos obligatorios de pedir
     suscripción (inicio, mitad, final), con un botón de suscripción
     dibujado encima (no generado por IA, así nunca sale con texto
     deforme o ilegible).
  3) La misma persona/estilo se reutiliza como protagonista de las
     miniaturas (ver agents/thumbnail.py), reforzando el reconocimiento
     de marca del canal.

Esto NO es un avatar hablando con los labios sincronizados: es una foto
fija de un presentador consistente, con movimiento de cámara sutil,
usada en los momentos clave. Es una mejora real y honesta hacia "rostro
humano en el video", no una simulación de algo que no podemos entregar
gratis todos los días.

Si el usuario quiere en el futuro subir el nivel a un avatar hablante de
verdad, la vía realista sería contratar un presentador humano por
Fiverr/Upwork para grabar tomas cortas reutilizables, o pagar una
herramienta de avatar con lip-sync — ambas opciones dejan de ser 100%
gratis, así que no se activan automáticamente aquí.
"""
import os
import random
import urllib.parse

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from agents.utils import load_config, log

AGENT = "Presentador"

# Ruta FIJA (no depende del video actual): así el mismo archivo se reutiliza
# en todos los videos futuros, dando consistencia de marca al canal.
CARPETA_ASSETS_PERSISTENTES = "assets/presentador"
RUTA_AVATAR_BASE = os.path.join(CARPETA_ASSETS_PERSISTENTES, "avatar_base.jpg")

TAMANO_AVATAR = (1280, 720)

# Descripción y semilla POR DEFECTO del presentador del canal. El usuario
# puede cambiar esto en config.yaml -> canal.presentador (descripcion /
# semilla) en cualquier momento; si lo cambia, borra también
# assets/presentador/avatar_base.jpg para forzar que se genere de nuevo con
# la nueva descripción (si no, se sigue usando la imagen ya cacheada).
DESCRIPCION_PRESENTADOR_DEFECTO = (
    "mujer latina de unos 35 anios, cabello oscuro ondulado hasta los hombros, "
    "sonrisa calida y genuina, mirada cercana y segura, piel con textura realista, "
    "aspecto saludable, ropa casual de color verde salvia o beige, "
    "presentadora de un canal de salud y bienestar natural"
)
SEMILLA_PRESENTADOR_DEFECTO = 583920  # fija a propósito: misma cara en cada generación

# Marcador especial que el Guionista usa en el campo "visual" de los beats de
# llamado a suscripción, para que VisualScout (agents/visuals.py) sepa que
# debe usar al presentador en vez de buscar un video/foto de stock.
MARCADOR_VISUAL_CTA = "PRESENTADOR_LLAMADO_SUSCRIPCION"


def _config_presentador(cfg: dict) -> dict:
    bloque = (cfg.get("canal", {}) or {}).get("presentador", {}) or {}
    return {
        "activar": bloque.get("activar", True),
        "descripcion": bloque.get("descripcion") or DESCRIPCION_PRESENTADOR_DEFECTO,
        "semilla": bloque.get("semilla") or SEMILLA_PRESENTADOR_DEFECTO,
    }


def descripcion_presentador_para_miniaturas() -> str:
    """Expone la descripción del presentador para que agents/thumbnail.py
    pueda reutilizar el mismo perfil de persona y así las miniaturas y los
    momentos de suscripción del video muestren a alguien consistente entre
    sí (branding de canal), en vez de una persona distinta generada al azar
    en cada miniatura."""
    try:
        cfg = load_config()
        return _config_presentador(cfg)["descripcion"]
    except Exception:
        return DESCRIPCION_PRESENTADOR_DEFECTO


def _generar_avatar_base(destino_jpg: str, descripcion: str, semilla: int,
                          tamano=TAMANO_AVATAR) -> bool:
    prompt = (
        f"unretouched candid dslr photograph of {descripcion}, sitting in a bright "
        f"kitchen with a blurred background, natural window light, looking at the "
        f"camera with a warm genuine smile, visible skin pores and fine natural "
        f"texture, shot on a Canon EOS R5 85mm f1.8 lens, photojournalism style, "
        f"no beauty filter, no airbrushing, raw photo, ultra realistic, real person, "
        f"not an illustration, not anime, not a painting, not 3d render"
    )
    prompt_codificado = urllib.parse.quote(prompt)
    url = (f"https://image.pollinations.ai/prompt/{prompt_codificado}"
           f"?width={tamano[0]}&height={tamano[1]}&nologo=true&seed={semilla}&model=flux")
    try:
        r = requests.get(url, timeout=45)
        r.raise_for_status()
        if len(r.content) < 5000:
            return False
        os.makedirs(os.path.dirname(destino_jpg) or ".", exist_ok=True)
        with open(destino_jpg, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        log(AGENT, f"No se pudo generar la foto del presentador ({e}).")
        return False


def obtener_avatar_base() -> str:
    """Devuelve la ruta a la foto fija del presentador del canal,
    generándola UNA sola vez y reutilizándola siempre (misma persona en
    todos los videos, para dar consistencia de marca). Si por algún motivo
    no se puede generar, devuelve None (el llamado se hace sin foto de
    presentador, cae a un visual normal, nunca rompe el pipeline)."""
    cfg = load_config()
    conf = _config_presentador(cfg)
    if not conf["activar"]:
        return None

    if os.path.exists(RUTA_AVATAR_BASE):
        return RUTA_AVATAR_BASE

    log(AGENT, "Generando por primera vez la foto fija del presentador del canal "
                "(se reutilizará en todos los videos futuros para dar consistencia de marca)...")
    if _generar_avatar_base(RUTA_AVATAR_BASE, conf["descripcion"], conf["semilla"]):
        log(AGENT, f"Presentador del canal listo -> {RUTA_AVATAR_BASE}")
        return RUTA_AVATAR_BASE
    return None


def _fuente(tam):
    ruta = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(ruta):
        return ImageFont.truetype(ruta, tam)
    return ImageFont.load_default()


def _dibujar_boton_suscribete(base: Image.Image, momento: str) -> Image.Image:
    """Dibuja (con PIL, no con IA generativa) un botón de 'SUSCRÍBETE' con
    campana, siempre nítido y legible -- a diferencia de pedirle texto a un
    generador de imágenes, que casi nunca escribe letras correctamente."""
    base = base.convert("RGBA")
    w, h = base.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Viñeta suave en la esquina donde va el botón, para que resalte
    # siempre, sin importar el fondo de la foto.
    esquina_derecha = momento != "final"  # variar el lado da un poco de variedad visual
    pad = 30
    ancho_boton, alto_boton = int(w * 0.34), int(h * 0.14)
    x1 = w - ancho_boton - pad if esquina_derecha else pad
    y1 = h - alto_boton - pad
    x2 = x1 + ancho_boton
    y2 = y1 + alto_boton

    draw.rounded_rectangle([x1, y1, x2, y2], radius=18, fill=(204, 0, 0, 235),
                            outline=(255, 255, 255, 255), width=4)

    # Campanita simple dibujada a mano (círculo + triángulo), no depende de
    # ninguna fuente de emoji del sistema (evita cuadraditos rotos).
    cx, cy = x1 + int(alto_boton * 0.55), y1 + alto_boton // 2
    r = int(alto_boton * 0.22)
    draw.pieslice([cx - r, cy - r, cx + r, cy + int(r * 0.6)], 180, 360, fill=(255, 255, 255, 255))
    draw.rectangle([cx - r, cy - int(r * 0.2), cx + r, cy + int(r * 0.5)], fill=(255, 255, 255, 255))
    draw.ellipse([cx - int(r * 0.25), cy + int(r * 0.5), cx + int(r * 0.25), cy + int(r * 0.9)],
                 fill=(255, 255, 255, 255))

    font = _fuente(max(20, int(alto_boton * 0.32)))
    texto = "SUSCRÍBETE"
    tx = cx + r + 14
    ty = cy - font.size // 2
    draw.text((tx, ty), texto, font=font, fill=(255, 255, 255, 255))

    # Etiqueta de transparencia "Presentadora generada con IA" (siempre
    # visible, arriba, lejos del botón): esto NO es opcional-decorativo,
    # responde a un hallazgo real de la auditoría de agosto 2026 -- YouTube
    # restringe la MONETIZACIÓN de "personas de IA" que dan consejos en
    # temas sensibles como salud (política aclarada el 16-jul-2026). Nuestra
    # presentadora NUNCA da consejos de salud (solo pide la suscripción), y
    # esta etiqueta lo deja explícito e inconfundible para cualquier
    # espectador o revisor humano/automático de YouTube.
    font_etq = _fuente(max(16, int(h * 0.032)))
    etiqueta = "PRESENTADORA GENERADA CON IA"
    tw = draw.textlength(etiqueta, font=font_etq)
    ex1, ey1 = pad, pad
    ex2, ey2 = ex1 + tw + 20, ey1 + font_etq.size + 14
    draw.rounded_rectangle([ex1, ey1, ex2, ey2], radius=8, fill=(0, 0, 0, 160))
    draw.text((ex1 + 10, ey1 + 7), etiqueta, font=font_etq, fill=(255, 255, 255, 255))

    resultado = Image.alpha_composite(base, overlay).convert("RGB")
    return resultado


def generar_frame_llamado_suscripcion(momento: str, carpeta_salida: str, tag: str) -> dict:
    """Construye el visual para uno de los 3 momentos obligatorios de pedir
    suscripción (momento: 'inicio' | 'mitad' | 'final'): la foto fija del
    presentador del canal + un botón de suscripción dibujado encima.

    Devuelve un dict compatible con el resto del pipeline
    ({"tipo": "imagen", "ruta": ..., "keyword": ...}). Si el presentador no
    está disponible por cualquier motivo, devuelve None y quien llama debe
    usar el flujo normal de VisualScout como respaldo (el pipeline nunca se
    bloquea por esto)."""
    ruta_base = obtener_avatar_base()
    if not ruta_base:
        return None
    try:
        base = Image.open(ruta_base).convert("RGB")
        compuesta = _dibujar_boton_suscribete(base, momento)
        os.makedirs(carpeta_salida, exist_ok=True)
        destino = os.path.join(carpeta_salida, f"{tag}_presentador_{momento}.jpg")
        compuesta.save(destino, quality=92)
        return {"tipo": "imagen", "ruta": destino,
                "keyword": "presentador del canal pidiendo suscripcion"}
    except Exception as e:
        log(AGENT, f"No se pudo componer el frame del presentador ({e}).")
        return None


if __name__ == "__main__":
    ruta = obtener_avatar_base()
    print("Avatar base:", ruta)
    for momento in ("inicio", "mitad", "final"):
        v = generar_frame_llamado_suscripcion(momento, "output/_test_presentador", "demo")
        print(momento, "->", v)
