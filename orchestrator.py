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

AGENT = "Orquestador"


def elegir_idea_no_usada(ideas, estado):
    usadas = set(estado.get("ideas_usadas", []))
    for idea in ideas:
        if idea["titulo"] not in usadas:
            return idea
    return ideas[0] if ideas else None


def ejecutar_pipeline_para_un_video(intentar_publicar: bool, generar_short: bool):
    cfg = load_config()
    estado = load_state()

    log(AGENT, "1/9 Buscando ideas potenciales (TrendScout)...")
    ideas = buscar_ideas_potenciales()
    if not ideas:
        log(AGENT, "No se encontraron ideas. Abortando esta ejecución.")
        return None

    idea = elegir_idea_no_usada(ideas, estado)
    log(AGENT, f"Idea elegida: '{idea['titulo']}' (outlier {idea['ratio_outlier']}x)")

    log(AGENT, "2/9 Redactando guion original en español, con reglas de retención (Guionista)...")
    guion = generar_guion(idea)

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
    primera_imagen = visuales_info["visuales_por_capitulo"][0][0]["ruta"]
    ruta_miniatura = generar_miniatura(guion["titulo"], primera_imagen,
                                        f"output/thumbnails/{nombre_base}.png")

    descripcion_final = construir_descripcion_publicacion(guion, timestamps_capitulos, cfg["canal"].get("nombre", ""))
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
    else:
        log(AGENT, "8/9 Publicación omitida (--no-publicar). Video listo en disco.")

    shutil.rmtree(carpeta_assets, ignore_errors=True)
    shutil.rmtree("output/video/_musica_tmp", ignore_errors=True)


    ruta_short = None
    short_id = None

    if generar_short:
        try:
            from agents.shorts_creator import crear_short
            log(AGENT, "9/9 Generando Short para atraer tráfico al video completo (ShortsCreator)...")
            url_largo = f"https://youtube.com/watch?v={video_id}" if video_id else ""
            ruta_short, titulo_short, descripcion_short = crear_short(
                guion, "output/video", nombre_base, url_video_largo=url_largo
            )
            if intentar_publicar:
                from agents.publisher import publicar_video
                guion_short = {"titulo": titulo_short,
                               "tags": (guion.get("tags", []) + ["Shorts"])[:10],
                               "disclaimer": guion.get("disclaimer", "")}
                log(AGENT, "Publicando el Short en YouTube...")
                short_id = publicar_video(ruta_short, None, guion_short, descripcion_short)
        except Exception as e:
            log(AGENT, f"No se pudo generar/publicar el Short: {e}")
            traceback.print_exc()
    else:
        log(AGENT, "9/9 Generación de Short omitida (--sin-short).")

    estado.setdefault("ideas_usadas", []).append(idea["titulo"])
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos", type=int, default=1, help="Cuántos videos generar en esta ejecución")
    parser.add_argument("--no-publicar", action="store_true", help="No subir a YouTube, solo generar")
    parser.add_argument("--sin-short", action="store_true", help="No generar el Short, solo el video largo")
    args = parser.parse_args()

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
