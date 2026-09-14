"""
Estrategia de audiencia prioritaria del canal.

Objetivo:
traducir las estadísticas reales del canal (14-sep-2026) a decisiones
operativas para la fábrica:
- priorizar ideas sobre condiciones frecuentes en mujeres 55+/65+
- dar más peso a los clusters que ya demostraron tracción en Shorts
- hablarle con claridad a una audiencia mayor y muy móvil

La idea NO es volver el canal "solo femenino" en lo biológico, sino orientar
la selección de temas hacia la persona que hoy más está mirando el canal.
"""
import json
import os
import re

from agents.utils import BASE_DIR

RUTA_ESTRATEGIA = os.path.join(BASE_DIR, "data", "temas_prioritarios_mujer55plus.json")


_DEFAULT = {
    "audiencia": {
        "sexo_principal": "mujeres",
        "edad_principal": ["55-64", "65+"],
        "dispositivo_principal": "movil",
        "paises_principales": ["Mexico", "Estados Unidos hispano", "Espana", "Colombia"],
    },
    "clusters": [
        {"categoria": "sueno_cortisol_nocturno", "prioridad": 10,
         "terminos": ["sueno", "sueño", "dormir", "insomnio", "cortisol", "sleep", "insomnia", "waking"]},
        {"categoria": "piernas_circulacion_movilidad", "prioridad": 10,
         "terminos": ["piernas", "circulacion", "caminar", "pies", "legs", "circulation", "mobility"]},
        {"categoria": "inflamacion_dolor_articular_artritis", "prioridad": 9,
         "terminos": ["inflamacion", "inflamación", "artritis", "joint", "arthritis", "inflammation"]},
        {"categoria": "huesos_osteoporosis_caidas", "prioridad": 9,
         "terminos": ["osteoporosis", "huesos", "fractura", "caidas", "bone", "fracture", "falls"]},
        {"categoria": "presion_corazon_colesterol_ictus", "prioridad": 9,
         "terminos": ["presion", "hipertension", "corazon", "colesterol", "ictus", "heart", "stroke"]},
        {"categoria": "azucar_prediabetes_diabetes", "prioridad": 8,
         "terminos": ["glucosa", "azucar", "prediabetes", "diabetes", "blood sugar"]},
        {"categoria": "vejiga_incontinencia_nocturia", "prioridad": 8,
         "terminos": ["vejiga", "orina", "incontinencia", "nocturia", "bladder", "urinary"]},
        {"categoria": "memoria_cognicion_demencia", "prioridad": 8,
         "terminos": ["memoria", "olvidos", "demencia", "alzheimer", "memory", "cognition"]},
        {"categoria": "menopausia_sintomas_urogenitales", "prioridad": 8,
         "terminos": ["menopausia", "postmenopausia", "sofocos", "sequedad", "sexualidad", "intimidad", "menopause", "postmenopause"]},
        {"categoria": "musculo_sarcopenia_fuerza_gluteos", "prioridad": 8,
         "terminos": ["sarcopenia", "masa muscular", "fuerza", "debilidad", "tonificación", "glúteos", "muscle", "strength"]},
        {"categoria": "tiroides_fatiga_peso_estrenimiento", "prioridad": 7,
         "terminos": ["tiroides", "hipotiroidismo", "fatiga", "estreñimiento", "thyroid", "hashimoto"]},
        {"categoria": "piel_rostro_cuello_cabello_envejecimiento", "prioridad": 7,
         "terminos": ["piel", "cabello", "rostro", "arrugas", "cuello", "papada", "párpados", "wrinkles", "hair"]},
        {"categoria": "vision_cataratas_glaucoma_macular", "prioridad": 6,
         "terminos": ["vision", "ojos", "cataratas", "glaucoma", "macular", "eyes"]},
        {"categoria": "sexualidad_intimidad_postmenopausia", "prioridad": 6,
         "terminos": ["sexualidad", "intimidad", "libido", "sequedad vaginal", "dolor al tener relaciones", "intimacy"]},
    ],
}


def cargar_estrategia_audiencia() -> dict:
    try:
        with open(RUTA_ESTRATEGIA, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("clusters"):
                return data
    except Exception:
        pass
    return _DEFAULT



def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", (texto or "").lower()).strip()



def puntaje_tema_para_audiencia(titulo: str, categoria: str = "") -> int:
    """Puntaje simple de afinidad con la audiencia real del canal.

    Se usa para:
    - ordenar ideas del TrendScout
    - escoger mejores bases para Shorts independientes
    """
    estrategia = cargar_estrategia_audiencia()
    txt = _normalizar(f"{titulo} {categoria}")
    score = 0
    for cluster in estrategia.get("clusters", []):
        prioridad = int(cluster.get("prioridad", 0) or 0)
        terminos = [_normalizar(t) for t in cluster.get("terminos", [])]
        if any(t and t in txt for t in terminos):
            score += prioridad

    # Bonos por patrones probados en las estadísticas del canal.
    if any(x in txt for x in ["señal", "senal", "mito", "dato", "a los 60", "después de los 60", "despues de los 60"]):
        score += 2
    if any(x in txt for x in ["testosterone", "erectile", "disfuncion erectil", "testosterona"]):
        score -= 8
    if any(x in txt for x in ["music", "música", "musica", "frequency", "frecuencia", "frequencies", "asmr"]):
        score -= 6
    return score



def categoria_prioritaria_de_titulo(titulo: str) -> str:
    estrategia = cargar_estrategia_audiencia()
    txt = _normalizar(titulo)
    mejor = (0, "")
    for cluster in estrategia.get("clusters", []):
        hits = sum(1 for t in cluster.get("terminos", []) if _normalizar(t) and _normalizar(t) in txt)
        score = hits * int(cluster.get("prioridad", 0) or 0)
        if score > mejor[0]:
            mejor = (score, cluster.get("categoria", ""))
    return mejor[1]



def ejes_prioritarios_audiencia() -> list:
    estrategia = cargar_estrategia_audiencia()
    salida = []
    for cluster in estrategia.get("clusters", []):
        kws = [k.strip() for k in cluster.get("keywords_busqueda", []) if k.strip()]
        if not kws:
            continue
        salida.append({
            "categoria": cluster.get("categoria", "general"),
            "palabras_clave": kws,
            "prioridad": int(cluster.get("prioridad", 0) or 0),
        })
    salida.sort(key=lambda x: -x.get("prioridad", 0))
    return salida



def combinar_ejes_con_audiencia(ejes_cfg: list) -> list:
    """Prepone ejes de audiencia y luego añade los del config sin perderlos.

    Si una categoría ya existe, fusiona palabras clave para aprovechar tanto
    el conocimiento manual del usuario como lo visto en las estadísticas.
    """
    base = []
    vistos = {}
    for eje in ejes_prioritarios_audiencia() + list(ejes_cfg or []):
        cat = eje.get("categoria", "general")
        key = _normalizar(cat)
        palabras = [p for p in eje.get("palabras_clave", []) if p]
        if key not in vistos:
            vistos[key] = {"categoria": cat, "palabras_clave": []}
            base.append(vistos[key])
        actuales = vistos[key]["palabras_clave"]
        for p in palabras:
            if p not in actuales:
                actuales.append(p)
    return base



def bloque_prompt_audiencia() -> str:
    estrategia = cargar_estrategia_audiencia()
    aud = estrategia.get("audiencia", {})
    top = [c.get("categoria", "") for c in estrategia.get("clusters", [])[:6]]
    top_txt = ", ".join(t.replace("_", " ") for t in top if t)
    return (
        "AUDIENCIA REAL DEL CANAL (obligatoria):\n"
        f"- Público principal: {aud.get('sexo_principal', 'mujeres')} de {', '.join(aud.get('edad_principal', ['55+']))}.\n"
        f"- El canal se consume sobre todo en {aud.get('dispositivo_principal', 'movil')}; habla claro, concreto y sin tecnicismos innecesarios.\n"
        f"- Países principales: {', '.join(aud.get('paises_principales', []))}. Usa español neutro.\n"
        "- Prioriza problemas FRECUENTES y muy sentibles para calidad de vida, sueño, movilidad, dolor, vejiga, corazón, azúcar y memoria.\n"
        "- También permite líneas de SALUD + BELLEZA con base real: piel, cabello, rostro, cuello, tono muscular, sarcopenia, menopausia e intimidad sin lenguaje explícito.\n"
        f"- Clusters prioritarios hoy: {top_txt}.\n"
        "- Si el tema no encaja con esta audiencia, NO lo fuerces: busca otro ángulo más útil para una mujer de 55+/65+.\n"
        "- Da soluciones prácticas, simples y aplicables hoy mismo. No te quedes en teoría.\n"
        "- Evita ángulos masculinos (testosterona, disfunción eréctil) y evita sonar a 'consejo para cualquiera'. Habla a la persona real que hoy te está viendo."
    )
