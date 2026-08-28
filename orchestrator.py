#!/usr/bin/env python3
"""
ORQUESTADOR PRINCIPAL — El "jefe de equipo" que coordina a todos los agentes
================================================================================
Ejecuta el pipeline completo una vez:
  TrendScout -> Guionista (+ reglas del Estratega Viral) -> Narrador
  -> VisualScout -> QA-Coherencia (verifica que el video SÍ coincida con el
     guion) -> EditorVideo -> Packaging -> Estratega Viral (descripción +
     índice) -> Publicador (video largo) -> ShortsCreator -> Publicador (short)

Diseñado para correr 100% en automático y GRATIS mediante un cron:
  - En tu propia PC/servidor: cron de Linux/Mac o Programador de Tareas de Windows.
  - 100% en la nube y gratis: GitHub Actions (cron) o un Worker gratuito de Render/Railway.
  (Instrucciones completas en README.md)

Uso manual:
    python3 orchestrator.py                 # genera y publica 1 video + su short
    python3 orchestrator.py --videos 4      # genera 4 videos en esta ejecución
    python3 orchestrator.py --no-publicar   # genera todo pero NO sube a YouTube (modo prueba)
    python3 orchestrator.py --sin-short     # omite la generación del Short
"""
import argparse
import datetime as dt
import os
import shutil
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.utils import load_config, load_state, save_state, slugify, log
from agents.trend_scout import buscar_ideas_potenciales
from agents.scriptwriter import generar_guion
from agents.voice import narrar_guion
from agents.visuals import obtener_visuales_para_guion
from agents.qa_coherencia import verificar_y_corregir
from agents.video_editor import construir_video
from agents.thumbnail import generar_miniatura
from agents.viral_strategist import construir_descripcion_publicacion
from agents.musica import obtener_musica_fondo
from agents.monetizacion import seleccionar_productos, construir_bloque_afiliados
from agents.promocion_cruzada import (
    obtener_videos_relacionados, construir_bloque_mas_videos, agregar_mencion_video_relacionado,
)


AGENT = "Orquestador"


CATEGORIAS_RECIENTES_A_EVITAR = 4  # cuántos videos anteriores se toman en cuenta para variar el tema


def _titulos_ya_publicados_en_canal(cfg) -> set:
    """Títulos REALES ya publicados en el canal, CON FECHA (auditoría
    17-ago-2026 + ventanas de tiempo del 19-ago): la memoria local puede
    quedar desactualizada si un push falla, así que el canal real es la
    fuente de verdad. Devuelve un set de tuplas (titulo_lower, dias_desde
    _publicacion) para que el filtro anti-repetidos pueda aplicar ventanas
    de tiempo (un tema similar vuelve a ser elegible cuando su video
    "envejece"; decisión del usuario: variedad en caliente, reciclaje con
    el tiempo)."""
    import datetime as _dt
    titulos = set()
    try:
        import pickle
        import googleapiclient.discovery
        from google.auth.transport.requests import Request
        with open(cfg["apis"]["oauth_token_path"], "rb") as f:
            creds = pickle.load(f)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        yt = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        canal_id = cfg.get("canal", {}).get("channel_id", "")
        playlist = "UU" + canal_id[2:] if canal_id.startswith("UC") else ""
        if playlist:
            r = yt.playlistItems().list(part="snippet,contentDetails", playlistId=playlist,
                                         maxResults=50).execute()
            ahora = _dt.datetime.now(_dt.timezone.utc)
            for it in r.get("items", []):
                pub = it["contentDetails"].get("videoPublishedAt") or it["snippet"].get("publishedAt", "")
                try:
                    fecha = _dt.datetime.fromisoformat(pub.replace("Z", "+00:00"))
                    dias = (ahora - fecha).days
                except Exception:
                    dias = 0  # sin fecha legible: tratarlo como reciente (cauteloso)
                titulos.add((it["snippet"]["title"].lower(), dias))
    except Exception as e:
        log(AGENT, f"Aviso: no se pudieron leer los títulos reales del canal ({e}); "
                    f"se usa solo la memoria local.")
    return titulos



# Mapa bilingüe de CONCEPTOS temáticos (bug real del 18-ago-2026: las ideas
# del trend_scout vienen EN INGLÉS y los títulos del canal EN ESPAÑOL, así
# que la comparación por palabras daba cero coincidencias y "Relaxing
# Music..." pasaba como tema nuevo aunque el canal ya tuviera DOS videos de
# "Música Relajante..."). Cada fila agrupa términos equivalentes en ambos
# idiomas; si la idea y un título del canal comparten un mismo CONCEPTO
# central, el tema se considera repetido sin importar el idioma.
_CONCEPTOS_BILINGUES = [
    {"music", "musica", "música", "song", "songs", "sound", "sounds",
     "sonido", "sonidos", "mantra", "mantras", "frequency", "frequencies",
     "frecuencia", "frecuencias", "asmr",
     # AMPLIADO 28-ago-2026 (fallo real: se generó "Dormir con Lluvia de
     # Tres Minutos" — contenido de SONIDOS de lluvia, primo directo del
     # tema música/sonidos borrado 2 veces; el filtro no lo cazaba porque
     # faltaban estos términos de "audio ambiental"):
     "rain", "lluvia", "white noise", "ruido blanco", "binaural",
     "binaurales", "hz", "hertz", "ambient sounds", "nature sounds",
     "sonidos de la naturaleza", "thunder", "truenos", "ocean waves",
     "olas del mar", "binaural", "hz"},
    {"relaxing", "relajante", "relajación", "relajacion", "calm", "calma",
     "calming", "meditation", "meditación", "meditacion", "zen"},
    {"stress", "estrés", "estres", "anxiety", "ansiedad"},
    {"sleep", "dormir", "sueño", "sueno", "insomnia", "insomnio"},
    {"gut", "intestino", "intestinal", "digestion", "digestión", "digestivo",
     "microbiome", "microbioma"},
    {"mushroom", "mushrooms", "seta", "setas", "hongo", "hongos", "oyster",
     "ostra", "reishi", "shiitake"},
    {"magnesium", "magnesio"},
    {"turmeric", "cúrcuma", "curcuma", "curcumin", "curcumina"},
    {"inflammation", "inflamación", "inflamacion", "antiinflamatoria",
     "anti-inflammatory", "antiinflamatorio"},
    {"vision", "visión", "vista", "eye", "eyes", "ojos", "ocular"},
    {"fasting", "ayuno"},
    {"ginger", "jengibre"},
    {"honey", "miel"},
    {"garlic", "ajo"},
    {"tea", "té", "infusion", "infusión"},
]


def _conceptos_de(texto: str) -> set:
    """Conjunto de índices de conceptos bilingües presentes en un texto.
    CORRECCIÓN 28-ago-2026: los términos de VARIAS palabras ("white noise",
    "ruido blanco") no se detectaban comparando palabra por palabra; ahora
    también se buscan como frase dentro del texto completo."""
    texto_bajo = " " + texto.lower() + " "
    palabras = set(texto.lower().split())
    palabras |= {p.strip("¿?¡!.,:;()") for p in palabras}
    encontrados = set()
    for i, grupo in enumerate(_CONCEPTOS_BILINGUES):
        for termino in grupo:
            if " " in termino:
                if termino in texto_bajo:
                    encontrados.add(i)
                    break
            elif termino in palabras:
                encontrados.add(i)
                break
    return encontrados


# EXPLOTACION_DE_EXITO (estudio 28-ago-2026): los canales gemelos que
# explotan (Vital Health HQ: 0->248K vistas en 4 semanas) ITERAN el tema
# de su video ganador con ángulos nuevos de inmediato, en vez de esperar.
# Regla: si un video del canal supera 10x la mediana de vistas de los
# largos, su tema queda EXENTO del anti-repetidos (se permite una variante
# con ángulo distinto). El anti-repetidos normal sigue para todo lo demás.
UMBRAL_EXITO_OUTLIER = 10.0


def _temas_de_exitos_del_canal(cfg) -> set:
    """Títulos de videos propios cuyo rendimiento es outlier (>10x la
    mediana del canal): sus temas pueden revisitarse sin esperar los 90
    días. Nunca lanza excepción."""
    try:
        import statistics
        import googleapiclient.discovery
        from agents.publisher import _obtener_credenciales
        creds = _obtener_credenciales(cfg)
        yt = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        canal_id = cfg["canal"].get("channel_id", "")
        pl = "UU" + canal_id[2:]
        r = yt.playlistItems().list(part="snippet", playlistId=pl, maxResults=30).execute()
        ids = [i["snippet"]["resourceId"]["videoId"] for i in r.get("items", [])]
        r2 = yt.videos().list(part="statistics,snippet,contentDetails", id=",".join(ids)).execute()
        import isodate
        vistas_largos, titulos_vistas = [], []
        for v in r2.get("items", []):
            dur = isodate.parse_duration(v["contentDetails"]["duration"]).total_seconds()
            vistas = int(v["statistics"].get("viewCount", 0))
            titulos_vistas.append((v["snippet"]["title"], vistas))
            if dur > 65:
                vistas_largos.append(vistas)
        if not vistas_largos:
            return set()
        mediana = max(1, statistics.median(vistas_largos))
        return {t for t, vis in titulos_vistas if vis >= UMBRAL_EXITO_OUTLIER * mediana}
    except Exception:
        return set()


def _tema_parece_repetido(titulo_idea: str, titulos_canal: set) -> bool:
    """Compara idea vs títulos ya publicados, CON VENTANA DE TIEMPO
    (decisión del usuario 19-ago-2026: variedad en caliente, reciclaje
    después). titulos_canal es un set de tuplas (titulo, dias_desde_pub).
    Un título del canal solo bloquea si su video tiene MENOS de
    VENTANA_TEMA_SIMILAR_DIAS días; los videos viejos liberan su tema.

    Dos capas de comparación:
    1) CONCEPTOS BILINGÜES: si comparten 2+ conceptos centrales (o 1 si es
       el único concepto de la idea), es repetido aunque estén en idiomas
       distintos ("Relaxing Music for Stress" vs "Música Relajante Para
       Reducir El Estrés" comparten música+relajación+estrés).
    2) Palabras literales (para temas fuera del mapa): si ≥50% de las
       palabras clave de la idea aparecen en un título del canal."""
    # Compatibilidad: aceptar tanto tuplas (titulo, dias) como strings sueltos
    normalizados = []
    for item in titulos_canal:
        if isinstance(item, tuple):
            normalizados.append(item)
        else:
            normalizados.append((str(item), 0))

    # Solo los títulos RECIENTES bloquean (ventana de tiempo)
    recientes = [(t, d) for t, d in normalizados if d < VENTANA_TEMA_SIMILAR_DIAS]

    conceptos_idea = _conceptos_de(titulo_idea)
    for titulo_canal, _dias in recientes:
        conceptos_canal = _conceptos_de(titulo_canal)
        comunes = conceptos_idea & conceptos_canal
        if len(comunes) >= 2:
            return True
        if len(comunes) == 1 and len(conceptos_idea) == 1:
            return True

    stop = {"de", "del", "la", "el", "los", "las", "para", "con", "en", "y",
            "a", "un", "una", "que", "tu", "su", "al", "cómo", "como", "por",
            "qué", "the", "for", "your", "to", "of", "and", "in", "how"}
    palabras_idea = {p for p in titulo_idea.lower().split() if p not in stop and len(p) > 3}
    if not palabras_idea:
        return False
    for titulo_canal, _dias in recientes:
        # Solo palabras con contenido real también del lado del canal (bug
        # visto en prueba del 19-ago: "tu" de "...Para Tu Salud" coincidía
        # como subcadena dentro de "TUrmeric" y bloqueaba un tema nuevo).
        palabras_canal = {p for p in titulo_canal.split() if len(p) > 3 and p not in stop}
        coincidencias = sum(1 for p in palabras_idea
                            if any(p in pc or pc in p for pc in palabras_canal))
        if coincidencias / len(palabras_idea) >= 0.5:
            return True
    return False


# VENTANAS DE TIEMPO PARA REPETIR TEMAS (ajustado 19-ago-2026 por decisión
# explícita del usuario: "los videos siguientes deben ser diferentes a los
# publicados, pero después de un tiempo se puede publicar un video similar,
# obviamente no del tema exacto").
#
#   - VENTANA_TEMA_SIMILAR_DIAS: un tema que comparte conceptos con un video
#     ya publicado vuelve a ser ELEGIBLE cuando ese video cumple esta edad.
#     Con 90 días, el canal puede revisitar "magnesio" con otro ángulo un
#     trimestre después, que es lo que hacen los canales grandes.
#   - VENTANA_TEMA_MUSICA_DIAS: ventana MÁS LARGA para el caso especial de
#     música/sonidos/mantras (el usuario borró esos videos DOS veces; no es
#     un veto eterno, pero sí una cuarentena larga). Pasado ese tiempo, una
#     idea de música podría volver a considerarse (p. ej. una NOTICIA sobre
#     musicoterapia), y siempre con el anti-repetidos normal encima.
VENTANA_TEMA_SIMILAR_DIAS = 90
VENTANA_TEMA_MUSICA_DIAS = 180

_CONCEPTO_MUSICA = 0  # índice 0 del mapa: music/song/sound/mantra/...

# Fecha del último incidente de música (los 2 borrados): la cuarentena de
# música corre desde aquí aunque los videos ya no existan en el canal.
_INICIO_CUARENTENA_MUSICA = "2026-08-18"


def _tema_esta_vetado(titulo_idea: str) -> bool:
    """Cuarentena de música: activa solo mientras no hayan pasado
    VENTANA_TEMA_MUSICA_DIAS desde el último incidente. No es eterna."""
    if _CONCEPTO_MUSICA not in _conceptos_de(titulo_idea):
        return False
    import datetime as _dt
    inicio = _dt.date.fromisoformat(_INICIO_CUARENTENA_MUSICA)
    dias_pasados = (_dt.date.today() - inicio).days
    return dias_pasados < VENTANA_TEMA_MUSICA_DIAS


def elegir_idea_no_usada(ideas, estado):
    """Elige la mejor idea que (a) no se haya usado antes NI se parezca a
    un video ya publicado en el canal real, y (b) tenga estudios
    científicos reales disponibles para respaldarla (ver
    agents/investigacion_cientifica.py) — si un tema no se puede validar
    con evidencia real, se descarta y se prueba con el siguiente candidato."""
    usadas = set(estado.get("ideas_usadas", []))
    from agents.investigacion_cientifica import buscar_estudios
    cfg = load_config()
    titulos_canal = _titulos_ya_publicados_en_canal(cfg)
    # Exención por éxito (28-ago-2026): los temas de videos-outlier del
    # propio canal (>10x la mediana) pueden revisitarse con ángulo nuevo.
    exentos_por_exito = _temas_de_exitos_del_canal(cfg)
    if exentos_por_exito:
        conceptos_exentos = set()
        for t in exentos_por_exito:
            conceptos_exentos |= _conceptos_de(t)
        titulos_canal = {(t, d) for (t, d) in titulos_canal
                          if not (_conceptos_de(t) and _conceptos_de(t) <= conceptos_exentos)}
        log(AGENT, f"Explotación de éxito: {len(exentos_por_exito)} tema(s) outlier "
                    f"exento(s) del anti-repetidos (iterar lo que funciona).")

    for idea in ideas:
        if idea["titulo"] in usadas:
            continue
        if _tema_esta_vetado(idea["titulo"]):
            log(AGENT, f"Idea descartada por TEMA VETADO (música/sonidos/mantras, "
                        f"borrado 2 veces por el usuario): '{idea['titulo']}'")
            continue
        if _tema_parece_repetido(idea["titulo"], titulos_canal):
            log(AGENT, f"Idea descartada por parecerse a un video YA publicado en el "
                        f"canal real: '{idea['titulo']}'")
            continue
        try:
            estudios = buscar_estudios(idea["titulo"])
        except Exception as e:
            log(AGENT, f"Aviso: no se pudo validar evidencia científica para "
                        f"'{idea['titulo']}' ({e}); se prueba el siguiente candidato.")
            continue
        if estudios:
            idea["_estudios_validados"] = estudios
            return idea
        log(AGENT, f"Idea descartada por falta de respaldo científico verificable: '{idea['titulo']}'")

    # Si NINGÚN candidato nuevo tiene evidencia real disponible, es mejor
    # repetir con cautela que forzar un tema sin ningún respaldo: se devuelve
    # el de mejor ratio-outlier de todos modos (el guionista igual no podrá
    # inventar cifras, solo hablará en términos generales).
    log(AGENT, "Ningún candidato nuevo tiene estudios científicos disponibles; "
                "se usa el mejor disponible de todos modos (sin cifras específicas).")
    # CORRECCIÓN (27-ago-2026, fallo real): este atajo devolvía ideas[0]
    # SIN pasar el veto de cuarentena ni el anti-repetidos, y así se
    # publicó "Esta Música Reduce el Estrés" (23-ago) con la cuarentena de
    # música ACTIVA. Ahora el respaldo también respeta ambos filtros.
    for idea in ideas:
        if _tema_esta_vetado(idea["titulo"]):
            continue
        if _tema_parece_repetido(idea["titulo"], titulos_canal):
            continue
        return idea
    log(AGENT, "Todos los candidatos están vetados o repetidos. Se aborta (mejor "
                "ningún video que otro video de música en cuarentena).")
    return None


def _categorias_recientes(estado):
    return estado.get("categorias_usadas", [])[-CATEGORIAS_RECIENTES_A_EVITAR:]




def _anotar_tarea_video_relacionado(short_id: str, largo_id: str, titulo: str):
    """La API de YouTube NO permite configurar el botón 'Vídeo relacionado'
    de los Shorts (verificado 27-ago-2026: ni videos.update ni ningún
    endpoint lo expone; Stack Overflow lo confirma). Lo máximo
    automatizable: dejar la tarea A UN CLIC en el resumen de la corrida de
    GitHub Actions y registrada en estado.json."""
    import os as _os
    url_editor = f"https://studio.youtube.com/video/{short_id}/edit"
    linea = (f"🔗 TAREA MANUAL (30 seg): abre {url_editor} , pulsa "
             f"'Vídeo relacionado' y elige el largo ({largo_id}).")
    log(AGENT, linea)
    resumen = _os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        try:
            with open(resumen, "a", encoding="utf-8") as fh:
                fh.write(f"\n### 🔗 Vincular video relacionado (30 seg)\n"
                         f"- Short: **{titulo[:60]}**\n"
                         f"- [Abrir editor del Short en Studio]({url_editor}) → "
                         f"botón **Vídeo relacionado** → elegir el video largo\n")
        except Exception:
            pass
    try:
        est = load_state()
        est.setdefault("tareas_video_relacionado", []).append(
            {"short": short_id, "largo": largo_id, "url": url_editor})
        save_state(est)
    except Exception:
        pass

def ejecutar_pipeline_para_un_video(intentar_publicar: bool, generar_short: bool):
    cfg = load_config()
    estado = load_state()

    categorias_evitar = _categorias_recientes(estado)
    log(AGENT, f"1/9 Buscando ideas potenciales (TrendScout)... "
                f"(evitando repetir: {categorias_evitar or 'ninguna aún'})")
    ideas = buscar_ideas_potenciales(categorias_evitar=categorias_evitar)
    if not ideas:
        log(AGENT, "No se encontraron ideas. Abortando esta ejecución.")
        return None

    idea = elegir_idea_no_usada(ideas, estado)
    if idea is None:
        log(AGENT, "No se pudo elegir ninguna idea válida. Abortando esta ejecución.")
        return None
    log(AGENT, f"Idea elegida: '{idea['titulo']}' (outlier {idea['ratio_outlier']}x, "
                f"categoría: {idea.get('categoria', 'general')})")

    log(AGENT, "2/9 Redactando guion original en español, con reglas de retención (Guionista)...")
    guion = generar_guion(idea)

    # Tráfico orgánico interno: buscamos AHORA (antes de narrar) otros videos
    # ya publicados del canal relacionados con este tema, para poder
    # mencionar uno por voz dentro del propio video (ver
    # agents/promocion_cruzada.py) además de enlazarlo en la descripción más
    # abajo. Si el canal todavía no tiene otros videos (por ejemplo el
    # primer día), esto simplemente no agrega nada y el pipeline sigue igual.
    relacionados = []
    try:
        relacionados = obtener_videos_relacionados(guion.get("keyword_principal", ""), guion.get("tags", []))
        if relacionados:
            guion = agregar_mencion_video_relacionado(guion, relacionados[0])
    except Exception as e:
        log(AGENT, f"Aviso: no se pudo buscar videos relacionados del canal para mencionar ({e}).")

    nombre_base = slugify(guion["titulo"]) + "_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    log(AGENT, "3/9 Narrando el guion (Narrador, voz gratuita)...")
    audio_info = narrar_guion(guion, "output/audio", nombre_base)

    log(AGENT, "4/9 Buscando recursos visuales reales por cada beat (VisualScout)...")
    carpeta_assets = f"output/video/assets_{nombre_base}"
    visuales_info = obtener_visuales_para_guion(guion, carpeta_assets)
    log(AGENT, f"Fuente de visuales usada: {visuales_info['fuente']}")

    log(AGENT, "5/9 Verificando que cada imagen/clip SÍ coincide con lo narrado (QA-Coherencia)...")
    visuales_info = verificar_y_corregir(guion, visuales_info, carpeta_assets)

    log(AGENT, "6/9 Ensamblando el video final con cortes dinámicos (EditorVideo)...")
    musica = obtener_musica_fondo("output/video/_musica_tmp")
    ruta_musica = musica["ruta"] if musica else None
    ruta_video, timestamps_capitulos = construir_video(guion, audio_info, visuales_info,
                                                        "output/video", nombre_base,
                                                        ruta_musica_fondo=ruta_musica)

    log(AGENT, "7/9 Generando miniatura (Packaging)...")
    # Bug real encontrado en producción (agosto 2026): desde que el primer
    # beat del video es casi siempre el llamado a suscripción (ver
    # agents/suscripcion_cta.py), tomar "el primer visual del video" a
    # ciegas usaba la TARJETA de "SUSCRÍBETE" como base de la miniatura en
    # vez de una imagen real de contenido -- se veía superpuesta y rota.
    # Ahora se busca el primer beat de contenido real (sin marcas de CTA).
    primera_imagen = None
    for i, cap in enumerate(guion["capitulos"]):
        for j, beat in enumerate(cap.get("beats", [])):
            if beat.get("es_llamado_suscripcion") or beat.get("es_mencion_cruzada") or beat.get("es_llamado_interaccion") or beat.get("es_cita_cientifica") or beat.get("es_intro_marca"):
                continue
            primera_imagen = visuales_info["visuales_por_capitulo"][i][j]["ruta"]
            break
        if primera_imagen:
            break
    if not primera_imagen:  # respaldo por si un video quedara sin ningún beat normal
        primera_imagen = visuales_info["visuales_por_capitulo"][0][0]["ruta"]
    ruta_miniatura = generar_miniatura(guion, primera_imagen,
                                        f"output/thumbnails/{nombre_base}.png")

    try:
        productos = seleccionar_productos(guion)
        bloque_afiliados = construir_bloque_afiliados(productos)
    except Exception as e:
        log(AGENT, f"Aviso: no se pudo armar la recomendación de productos ({e}).")
        bloque_afiliados = ""

    bloque_mas_videos = construir_bloque_mas_videos(relacionados)

    descripcion_final = construir_descripcion_publicacion(guion, timestamps_capitulos, cfg["canal"].get("nombre", ""),
                                                           url_canal=cfg["canal"].get("url", ""),
                                                           bloque_afiliados=bloque_afiliados,
                                                           bloque_mas_videos=bloque_mas_videos)
    if musica:
        descripcion_final += f"\n\n🎵 {musica['credito']}"

    video_id = None
    if intentar_publicar:
        try:
            from agents.publisher import publicar_video
            log(AGENT, "8/9 Publicando video largo en YouTube (Publicador)...")
            video_id = publicar_video(ruta_video, ruta_miniatura, guion, descripcion_final)
        except Exception as e:
            log(AGENT, f"No se pudo publicar el video: {e}")
            log(AGENT, "El video quedó listo en disco para subirlo manualmente si lo prefieres.")

        if video_id:
            try:
                from agents.subtitulos import generar_srt, subir_subtitulos
                ruta_srt = generar_srt(guion, audio_info, f"output/video/{nombre_base}.srt")
                subir_subtitulos(video_id, ruta_srt)
            except Exception as e:
                log(AGENT, f"Aviso: no se pudieron generar/subir los subtítulos ({e}).")

            try:
                from agents.playlist_manager import agregar_a_playlist
                nombre_playlist = cfg["canal"]["nicho"].title()
                agregar_a_playlist(video_id, nombre_playlist)
            except Exception as e:
                log(AGENT, f"Aviso: no se pudo agregar a la playlist ({e}).")

            try:
                from agents.seo_multilingue import agregar_titulos_traducidos
                idiomas_seo = cfg["canal"].get("idiomas_seo_adicionales", [])
                if idiomas_seo:
                    agregar_titulos_traducidos(video_id, guion["titulo"], descripcion_final, idiomas_seo)
            except Exception as e:
                log(AGENT, f"Aviso: no se pudieron agregar títulos/descripciones traducidos ({e}).")

            try:
                idioma_doblaje = cfg["canal"].get("idioma_doblaje", "")
                if idioma_doblaje:
                    from agents.doblaje_audio import generar_doblaje, escribir_instrucciones
                    from agents.utils import obtener_duracion_video
                    duracion_real = obtener_duracion_video(ruta_video)
                    doblaje = generar_doblaje(guion, duracion_real, "output/doblajes", nombre_base, idioma_doblaje)
                    if doblaje:
                        ruta_instrucciones = f"output/doblajes/{nombre_base}_COMO_SUBIR.txt"
                        escribir_instrucciones(ruta_instrucciones, idioma_doblaje, doblaje["titulo"],
                                                doblaje["descripcion"], os.path.basename(doblaje["audio"]))
                        log(AGENT, f"Doblaje listo para subir a mano: {doblaje['audio']} "
                                    f"(instrucciones en {ruta_instrucciones}).")
            except Exception as e:
                log(AGENT, f"Aviso: no se pudo generar el doblaje de audio ({e}).")
    else:
        log(AGENT, "8/9 Publicación omitida (--no-publicar). Video listo en disco.")

    # CORRECCIÓN (auditoría Short sin imágenes, 21-ago-2026): la carpeta de
    # visuales del largo se borraba ANTES de crear el Short; si la búsqueda
    # vertical fallaba (cuota Gemini agotada para verificar personas), el
    # Short no tenía NADA que reusar y salía con fondo degradado vacío.
    # Ahora se borra DESPUÉS del Short, y el Short la recibe como fuente de
    # visuales ya verificados (ver crear_short carpeta_visuales_largo).
    shutil.rmtree("output/video/_musica_tmp", ignore_errors=True)


    ruta_short = None
    short_id = None

    if generar_short:
        try:
            from agents.shorts_creator import crear_short
            log(AGENT, "9/9 Generando Short para atraer tráfico al video completo (ShortsCreator)...")
            from agents.promocion_cruzada import url_con_playlist
            url_largo = url_con_playlist(video_id, cfg) if video_id else ""
            ruta_short, titulo_short, descripcion_short = crear_short(
                guion, "output/video", nombre_base, url_video_largo=url_largo,
                carpeta_visuales_largo=carpeta_assets
            )
            if intentar_publicar:
                from agents.publisher import publicar_video
                guion_short = {"titulo": titulo_short,
                               "tags": (guion.get("tags", []) + ["Shorts"])[:10],
                               "disclaimer": guion.get("disclaimer", "")}
                log(AGENT, "Publicando el Short en YouTube...")
                short_id = publicar_video(ruta_short, None, guion_short, descripcion_short)
                # Playlist compartida con el largo (21-ago-2026): al terminar
                # el Short, YouTube prioriza el siguiente video de la misma
                # playlist/canal en el feed => más tráfico interno propio.
                if short_id:
                    try:
                        from agents.playlist_manager import agregar_a_playlist
                        agregar_a_playlist(short_id, cfg["canal"]["nicho"].title())
                    except Exception as e:
                        log(AGENT, f"Aviso: no se pudo añadir el Short a la playlist ({e}).")
                    if video_id:
                        _anotar_tarea_video_relacionado(short_id, video_id, guion.get("titulo", ""))

                # Enlace cruzado por comentarios (100% gratis, sin configuración
                # nueva): el video largo recibe un comentario con el link al
                # Short, y el Short recibe uno con el link al video completo.
                if video_id and short_id:
                    from agents.promocion_cruzada import (publicar_comentario_cruzado,
                                                           comentario_interactivo)
                    # Si los videos quedaron PROGRAMADOS (privados hasta la
                    # hora pico), los comentarios se ENCOLAN y el paso diario
                    # de comentarios los publica cuando ya sean públicos
                    # (YouTube no acepta comentarios en videos privados).
                    _programados = load_state().get("videos_programados", {})
                    _encolar = video_id in _programados or short_id in _programados
                    if _encolar:
                        _est = load_state()
                        cola = _est.setdefault("comentarios_cruzados_pendientes", [])
                        cola.append({"video_id": video_id, "texto": comentario_interactivo(
                            guion.get("titulo", ""),
                            url_extra=f"https://youtube.com/shorts/{short_id}",
                            etiqueta_url="🎬 ¿Prefieres el resumen rápido? Mira el Short:")})
                        cola.append({"video_id": short_id, "texto": comentario_interactivo(
                            guion.get("titulo", ""),
                            url_extra=url_con_playlist(video_id, cfg),
                            etiqueta_url="👉 Mira el video COMPLETO aquí ▶️")})
                        save_state(_est)
                        log(AGENT, "Videos programados: comentarios cruzados ENCOLADOS "
                                   "(se publicarán automáticamente cuando el video sea público).")
                    # MEJORA 21-ago-2026 (pedido del usuario): el comentario
                    # del video largo ahora ABRE CONVERSACIÓN (pregunta
                    # concreta sobre el tema) además de enlazar el Short.
                    if not _encolar:
                        publicar_comentario_cruzado(
                            video_id, comentario_interactivo(
                                guion.get("titulo", ""),
                                url_extra=f"https://youtube.com/shorts/{short_id}",
                                etiqueta_url="🎬 ¿Prefieres el resumen rápido? Mira el Short:"))
                        publicar_comentario_cruzado(
                            short_id, comentario_interactivo(
                                guion.get("titulo", ""),
                                url_extra=url_con_playlist(video_id, cfg),
                                etiqueta_url="👉 Mira el video COMPLETO aquí ▶️"))
        except Exception as e:
            log(AGENT, f"No se pudo generar/publicar el Short: {e}")
            traceback.print_exc()
    else:
        log(AGENT, "9/9 Generación de Short omitida (--sin-short).")

    # Limpieza de visuales del largo: AHORA sí (el Short ya los aprovechó).
    shutil.rmtree(carpeta_assets, ignore_errors=True)

    estado.setdefault("ideas_usadas", []).append(idea["titulo"])
    estado.setdefault("categorias_usadas", []).append(idea.get("categoria", "general"))
    estado.setdefault("videos_publicados", []).append({
        "titulo": guion["titulo"],
        "ruta_video": ruta_video,
        "ruta_miniatura": ruta_miniatura,
        "video_id": video_id,
        "ruta_short": ruta_short,
        "short_id": short_id,
        "descripcion": descripcion_final,
        "fecha": dt.datetime.now().isoformat(),
    })
    estado["ultima_ejecucion"] = dt.datetime.now().isoformat()
    save_state(estado)

    log(AGENT, f"✅ Video completo: {ruta_video}")
    if video_id:
        log(AGENT, f"🔗 Video largo: https://youtube.com/watch?v={video_id}")
    if short_id:
        log(AGENT, f"🔗 Short: https://youtube.com/watch?v={short_id}")
    return ruta_video


def publicar_short_independiente():
    """Modo de los días SIN video largo (ver --solo-short-independiente):
    genera y publica un Short con contenido completo y propio, alineado a
    un video largo ya existente (ver agents/short_independiente.py)."""
    from agents.short_independiente import crear_short_independiente
    resultado = crear_short_independiente()
    if not resultado:
        log(AGENT, "Hoy no se publica Short independiente (sin material o sin LLM).")
        return

    from agents.publisher import publicar_video
    from agents.promocion_cruzada import url_con_playlist
    guion_short = {"titulo": resultado["titulo"],
                   "tags": ["Salud Natural Diaria", "salud natural", "Shorts"],
                   "disclaimer": "Este contenido es informativo y no sustituye una consulta médica."}
    log(AGENT, "Publicando el Short independiente en YouTube...")
    short_id = publicar_video(resultado["ruta"], None, guion_short, resultado["descripcion"])
    if short_id and resultado.get("video_largo_id"):
        from agents.promocion_cruzada import publicar_comentario_cruzado
        publicar_comentario_cruzado(
            short_id, f"👉 Mira el video COMPLETO del tema aquí: "
                      f"{url_con_playlist(resultado['video_largo_id'])}"
        )
        log(AGENT, f"🔗 Short independiente publicado: https://youtube.com/shorts/{short_id}")
        # Tarea a-un-clic para el botón "Vídeo relacionado" (no automatizable
        # por API; ver _anotar_tarea_video_relacionado).
        _anotar_tarea_video_relacionado(short_id, resultado["video_largo_id"],
                                        resultado.get("titulo", ""))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos", type=int, default=1, help="Cuántos videos generar en esta ejecución")
    parser.add_argument("--no-publicar", action="store_true", help="No subir a YouTube, solo generar")
    parser.add_argument("--sin-short", action="store_true", help="No generar el Short, solo el video largo")
    parser.add_argument("--solo-short-independiente", action="store_true",
                        help="Publicar solo un Short independiente (días sin video largo)")
    args = parser.parse_args()

    if args.solo_short_independiente:
        try:
            publicar_short_independiente()
        except Exception:
            log(AGENT, "❌ Error publicando el Short independiente:")
            traceback.print_exc()
        return

    for i in range(args.videos):
        log(AGENT, f"===== Generando video {i+1}/{args.videos} =====")
        try:
            ejecutar_pipeline_para_un_video(intentar_publicar=not args.no_publicar,
                                             generar_short=not args.sin_short)
        except Exception:
            log(AGENT, "❌ Error en esta ejecución:")
            traceback.print_exc()


if __name__ == "__main__":
    main()
