"""
AGENTE 32: INTRO DE MARCA ("IntroMarca")
-----------------------------------------
Pedido del usuario (19-ago-2026): el video largo debe abrir con una
presentación breve del canal con su LOGOTIPO real, dando la bienvenida,
declarando la promesa del canal (solo información real basada en estudios
científicos, con los enlaces en la descripción) e invitando a suscribirse
— todo con un mensaje impactante que enganche. Después de eso, el gancho
del video y la mención temprana de la investigación científica base.

DISEÑO CON DATOS (para no matar la retención, que es el riesgo #1 de las
intros — la investigación de agosto 2026 lista "logo/channel bumper" como
uno de los 7 asesinos de retención cuando es larga o genérica):
  - DURACIÓN TOTAL: ~8-11 segundos narrados. Nunca más.
  - No es un "bumper" mudo: la voz YA está dando la promesa de valor
    mientras se ve el logo (la intro ES parte del gancho).
  - El texto es una PROMESA DE CREDIBILIDAD, no un saludo genérico:
    "aquí no repetimos rumores: cada dato viene de un estudio científico
    real, con el enlace para que lo compruebes tú mismo".
  - La invitación a suscribirse es una sola frase, ligada a la promesa.
  - Variantes rotativas (anti-plantilla) que mantienen las mismas 3 ideas:
    bienvenida + promesa científica + suscripción.

Visual: tarjeta 16:9 generada con el logo real del canal (descargado de
YouTube y guardado en assets/logo_canal.jpg) sobre fondo con degradado
suave de marca, nombre del canal y subtítulo de promesa.
"""
import os
import random

from agents.utils import log

AGENT = "IntroMarca"

RUTA_LOGO = os.path.join("assets", "logo_canal.jpg")

# Cada variante: (texto_bienvenida_promesa, con las 3 ideas en ~28-38 palabras)
FRASES_INTRO = [
    ("Bienvenido a Salud Natural Diaria. Aquí no repetimos rumores: cada dato "
     "que escuchas viene de estudios científicos reales, y te dejamos los "
     "enlaces para que los compruebes tú mismo. Suscríbete, esto te interesa."),
    ("Estás en Salud Natural Diaria, el canal donde la naturaleza y la ciencia "
     "van de la mano: todo lo que te contamos está respaldado por estudios "
     "reales, con los enlaces a la vista. Suscríbete y compruébalo."),
    ("Bienvenido a Salud Natural Diaria. Antes de empezar, una promesa: nada de "
     "mitos ni humo; solo información con respaldo científico verificable, con "
     "las fuentes enlazadas. Si valoras eso, suscríbete ahora."),
    ("Esto es Salud Natural Diaria, donde cada consejo tiene un estudio "
     "científico real detrás, y te mostramos las fuentes para que no confíes a "
     "ciegas. Suscríbete: aquí tu salud se toma en serio."),
]


def generar_tarjeta_intro(carpeta_salida: str, resolucion=(1280, 720)) -> str:
    """Tarjeta visual de la intro: logo real centrado sobre degradado de
    marca + nombre del canal + subtítulo de promesa científica."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    os.makedirs(carpeta_salida, exist_ok=True)
    destino = os.path.join(carpeta_salida, "intro_marca.jpg")
    w, h = resolucion

    # Fondo: degradado verde suave (colores de la marca del logo)
    fondo = Image.new("RGB", (w, h), (18, 38, 24))
    d = ImageDraw.Draw(fondo)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)],
               fill=(int(18 + 22 * t), int(38 + 42 * t), int(24 + 28 * t)))

    # Logo real del canal, circular, centrado arriba
    try:
        logo = Image.open(RUTA_LOGO).convert("RGB")
        lado = int(h * 0.52)
        logo = logo.resize((lado, lado), Image.LANCZOS)
        mascara = Image.new("L", (lado, lado), 0)
        dm = ImageDraw.Draw(mascara)
        dm.ellipse([0, 0, lado, lado], fill=255)
        # halo suave detrás del logo
        halo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dh = ImageDraw.Draw(halo)
        cx, cy = w // 2, int(h * 0.36)
        dh.ellipse([cx - lado // 2 - 22, cy - lado // 2 - 22,
                    cx + lado // 2 + 22, cy + lado // 2 + 22],
                   fill=(255, 255, 255, 60))
        halo = halo.filter(ImageFilter.GaussianBlur(18))
        fondo.paste(Image.alpha_composite(fondo.convert("RGBA"), halo).convert("RGB"), (0, 0))
        fondo.paste(logo, (cx - lado // 2, cy - lado // 2), mascara)
    except Exception as e:
        log(AGENT, f"Aviso: no se pudo usar el logo real ({e}); la tarjeta va sin logo.")

    def _fuente(tam):
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", tam)
        except Exception:
            return ImageFont.load_default()

    d = ImageDraw.Draw(fondo)
    titulo = "SALUD NATURAL DIARIA"
    f1 = _fuente(int(h * 0.075))
    tw = d.textlength(titulo, font=f1)
    d.text(((w - tw) / 2, int(h * 0.68)), titulo, font=f1, fill=(255, 255, 255))

    sub = "Información real, respaldada por estudios científicos"
    f2 = _fuente(int(h * 0.037))
    tw2 = d.textlength(sub, font=f2)
    d.text(((w - tw2) / 2, int(h * 0.79)), sub, font=f2, fill=(190, 235, 200))

    sub2 = "Fuentes enlazadas en la descripción"
    f3 = _fuente(int(h * 0.03))
    tw3 = d.textlength(sub2, font=f3)
    d.text(((w - tw3) / 2, int(h * 0.865)), sub2, font=f3, fill=(150, 210, 165))

    fondo.save(destino, quality=92)
    return destino


def agregar_intro_marca(guion: dict) -> dict:
    """Inserta la intro de marca como PRIMERÍSIMO beat y reordena el gancho
    para que suene INMEDIATAMENTE DESPUÉS de la intro (orden pedido por el
    usuario: intro de marca → gancho → mención científica → contenido).

    Detalle técnico importante: agents/voice.py narra guion["gancho"]
    ANTES del primer beat del capítulo 1. Si dejáramos el gancho ahí, el
    orden quedaría gancho → intro (al revés). Por eso aquí el gancho se
    CONVIERTE en un beat normal en la posición 1 (justo tras la intro) y
    guion["gancho"] se vacía. El visual del gancho reutiliza el del primer
    beat de contenido (la escena más llamativa, según las reglas del
    estratega viral)."""
    capitulos = guion.get("capitulos", [])
    if not capitulos:
        return guion
    beats = capitulos[0].setdefault("beats", [])

    beat_intro = {
        "texto": random.choice(FRASES_INTRO),
        "visual": "brand intro card",   # marcador; visuals.py lo intercepta
        "es_intro_marca": True,
    }
    beats.insert(0, beat_intro)

    gancho = (guion.get("gancho") or "").strip()
    if gancho:
        visual_gancho = ""
        for b in beats[1:]:
            if not any(b.get(k) for k in ("es_llamado_suscripcion", "es_mencion_cruzada",
                                           "es_llamado_interaccion", "es_cita_cientifica",
                                           "es_intro_marca")):
                visual_gancho = b.get("visual", "")
                break
        beats.insert(1, {
            "texto": gancho,
            "visual": visual_gancho or "surprising close up scene related to natural health",
        })
        guion["gancho"] = ""  # ya está como beat; que voice.py no lo duplique

    log(AGENT, "Intro de marca insertada (logo + bienvenida + promesa científica "
                "+ suscripción, ~10s) con el gancho reordenado justo después.")
    return guion


if __name__ == "__main__":
    ruta = generar_tarjeta_intro("/tmp/test_intro")
    print("tarjeta:", ruta)
