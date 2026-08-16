"""
AGENTE 29: SEGURIDAD MÉDICA ("SeguridadMedica")
------------------------------------------------
Añadido el 16-ago-2026 tras investigar a fondo qué puede hacer que YouTube
penalice o CIERRE un canal de salud. Hallazgo central de esa investigación:

  - La política de "contenido inauténtico" (masivo/repetitivo) solo quita
    la MONETIZACIÓN, no cierra el canal.
  - La política de DESINFORMACIÓN MÉDICA sí genera strikes y puede
    TERMINAR el canal: afirmar que algo "cura" enfermedades, recomendar
    sustituir tratamientos médicos, o contradecir a la OMS/autoridades
    sanitarias (ejemplos oficiales de YouTube: "el ajo cura el cáncer",
    "toma vitamina C en vez de radioterapia").

Este agente es la ÚLTIMA LÍNEA DE DEFENSA en código (no depende del LLM):
revisa TODO el texto narrable del guion y, si encuentra una afirmación
médica prohibida, la reescribe de forma segura y determinista o la marca.
Nunca bloquea la generación del video: corrige y avisa en el log.

Capas de defensa completas del sistema (defensa en profundidad):
  1) Regla 10 en REGLAS_PARA_GUIONISTA (el LLM recibe la prohibición).
  2) Este agente (revisión determinista post-guion).
  3) El disclaimer obligatorio en video y descripción.
  4) Las referencias científicas reales verificadas contra NCBI.
"""
import re

from agents.utils import log

AGENT = "SeguridadMedica"

# Enfermedades serias: cualquier promesa de "cura" sobre ellas es
# exactamente lo que la política de desinformación médica de YouTube
# usa como ejemplo de contenido que se elimina.
_ENFERMEDADES = (
    r"c[aá]ncer|tumor(es)?|diabetes|hipertensi[oó]n|presi[oó]n alta|"
    r"alzheimer|demencia|parkinson|depresi[oó]n|ansiedad cl[ií]nica|"
    r"covid|coronavirus|vih|sida|artritis|asma|epilepsia|"
    r"enfermedad(es)? card[ií]aca(s)?|infarto|derrame|ictus|"
    r"insuficiencia renal|cirrosis|hepatitis|tiroides|lupus|esclerosis"
)

# Patrones de CURA prohibidos: "cura/elimina/revierte/sana + enfermedad"
_PATRONES_CURA = [
    re.compile(rf"\b(cura[nr]?|curar[aá]?|elimina[nr]?|revierte[n]?|revertir|"
               rf"sana[nr]?|destruye[n]?|erradica[nr]?|desaparece[rn]?)\b[^.!?]{{0,60}}\b({_ENFERMEDADES})\b",
               re.IGNORECASE),
    re.compile(rf"\b({_ENFERMEDADES})\b[^.!?]{{0,40}}\b(se cura|desaparece|se elimina|se revierte)\b",
               re.IGNORECASE),
]

# Patrones de SUSTITUCIÓN de tratamiento médico (lo más grave para YouTube)
_TRATAMIENTOS = (
    r"medicamento[s]?|medicina[s]?|tratamiento[s]?|pastilla[s]?|insulina|"
    r"quimioterapia|radioterapia|antibi[oó]tico[s]?|antidepresivo[s]?|"
    r"vacuna[s]?|receta[s]?|f[aá]rmaco[s]?|terapia m[eé]dica|medicaci[oó]n"
)
_PATRONES_SUSTITUCION = [
    re.compile(rf"\b(en (vez|lugar) de|reemplaza[nr]?|sustituye[n]?|olv[ií]date de|"
               rf"deja[r]?\s+(de\s+tomar\s+)?(el|la|los|las|tus?|sus?)?\s*|abandona[r]?|suspende[r]?)"
               rf"[^.!?]{{0,60}}?\b({_TRATAMIENTOS})\b",
               re.IGNORECASE),
    re.compile(rf"\b(no necesitas?|ya no (necesitar[aá]s|tomar[aá]s))\b[^.!?]{{0,50}}"
               rf"\b(m[eé]dico|{_TRATAMIENTOS})\b",
               re.IGNORECASE),
]

# Reemplazos seguros deterministas para promesas de cura detectadas.
_REEMPLAZOS_CURA = {
    "cura": "puede apoyar el bienestar en",
    "curan": "pueden apoyar el bienestar en",
    "curar": "apoyar el bienestar en",
    "curará": "puede apoyar el bienestar en",
    "elimina": "puede ayudar a manejar",
    "eliminan": "pueden ayudar a manejar",
    "revierte": "puede ayudar a manejar",
    "revierten": "pueden ayudar a manejar",
    "sana": "puede apoyar",
    "sanan": "pueden apoyar",
}


def _revisar_texto(texto: str) -> tuple:
    """Devuelve (texto_corregido, lista_de_problemas_encontrados)."""
    problemas = []
    corregido = texto

    for patron in _PATRONES_CURA:
        m = patron.search(corregido)
        if m:
            problemas.append(f"promesa de cura: \"{m.group(0)[:70]}\"")
            # Reemplazo determinista del verbo prohibido
            def _sustituir(match):
                frase = match.group(0)
                for verbo, seguro in _REEMPLAZOS_CURA.items():
                    frase_nueva = re.sub(rf"\b{verbo}\b", seguro, frase, count=1,
                                          flags=re.IGNORECASE)
                    if frase_nueva != frase:
                        return frase_nueva
                return frase
            corregido = patron.sub(_sustituir, corregido)

    for patron in _PATRONES_SUSTITUCION:
        m = patron.search(corregido)
        if m:
            problemas.append(f"sugerencia de sustituir tratamiento: \"{m.group(0)[:70]}\"")
            # Aquí no hay reescritura parcial segura: se reemplaza la frase
            # completa por el mensaje responsable estándar.
            corregido = patron.sub(
                "siempre como complemento y nunca en reemplazo de lo que te indique tu médico",
                corregido)

    return corregido, problemas


def verificar_guion_seguro(guion: dict) -> dict:
    """Punto de entrada: revisa gancho + todos los beats + título +
    descripción. Corrige en el lugar y deja registro en el log."""
    total_problemas = 0

    gancho = guion.get("gancho", "")
    if gancho:
        nuevo, problemas = _revisar_texto(gancho)
        if problemas:
            total_problemas += len(problemas)
            log(AGENT, f"Gancho corregido por seguridad médica: {problemas}")
            guion["gancho"] = nuevo

    for cap in guion.get("capitulos", []):
        for beat in cap.get("beats", []):
            texto = beat.get("texto", "")
            if not texto:
                continue
            nuevo, problemas = _revisar_texto(texto)
            if problemas:
                total_problemas += len(problemas)
                log(AGENT, f"Beat corregido por seguridad médica: {problemas}")
                beat["texto"] = nuevo

    for campo in ("titulo", "descripcion"):
        valor = guion.get(campo, "")
        if valor:
            nuevo, problemas = _revisar_texto(valor)
            if problemas:
                total_problemas += len(problemas)
                log(AGENT, f"{campo} corregido por seguridad médica: {problemas}")
                guion[campo] = nuevo

    if total_problemas:
        log(AGENT, f"{total_problemas} afirmación(es) médica(s) de riesgo corregida(s). "
                    f"Estas frases podían activar la política de desinformación médica "
                    f"de YouTube (la única que genera strikes/cierre en canales de salud).")
    else:
        log(AGENT, "Guion revisado: sin afirmaciones médicas de riesgo. ✓")
    return guion


if __name__ == "__main__":
    pruebas = [
        "El ajo cura el cáncer según estudios.",
        "Toma esta hierba en vez de tu medicamento para la presión.",
        "El magnesio puede apoyar un mejor descanso nocturno.",
        "Deja de tomar tus pastillas y usa jengibre.",
        "Este té elimina la diabetes en 30 días.",
    ]
    for p in pruebas:
        nuevo, problemas = _revisar_texto(p)
        print(f"'{p}' -> '{nuevo}' | problemas: {problemas}")
