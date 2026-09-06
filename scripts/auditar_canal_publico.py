#!/usr/bin/env python3
"""Audita públicamente el canal de YouTube.

Uso:
    python3 scripts/auditar_canal_publico.py --canal https://www.youtube.com/@SaludNaturalDiaria

Qué hace:
- Lee /videos y /shorts del canal con yt-dlp.
- Descarga miniaturas públicas.
- Genera metadata.json y un reporte Markdown.
- Crea contact sheets para revisión visual rápida.
- Marca posibles mezclas español/inglés en títulos y descripciones.

No modifica el canal. Solo produce evidencia local para auditoría.
"""

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.control_calidad_idioma import detectar_hallazgos_ingles_visible


FUENTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _run_json(args):
    out = subprocess.check_output(args, stderr=subprocess.STDOUT, timeout=300).decode("utf-8", "replace")
    ini = out.find("{")
    if ini < 0:
        raise RuntimeError("No se encontró JSON en la salida de yt-dlp")
    return json.loads(out[ini:])



def _flat(url: str):
    return _run_json([sys.executable, "-m", "yt_dlp", "--no-warnings", "--flat-playlist", "--dump-single-json", url])



def _full_meta(video_id: str):
    return _run_json([sys.executable, "-m", "yt_dlp", "--no-warnings", "--dump-single-json", f"https://www.youtube.com/watch?v={video_id}"])



def _mejor_thumb(meta: dict) -> str:
    thumbs = [t for t in (meta.get("thumbnails") or []) if t.get("url")]
    if not thumbs:
        return ""
    mejor = max(thumbs, key=lambda t: ((t.get("preference") or 0), (t.get("width") or 0), (t.get("height") or 0)))
    return mejor.get("url", "")



def _descargar(url: str, destino: Path) -> str:
    if not url:
        return ""
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        destino.write_bytes(r.content)
        return str(destino)
    except Exception:
        return ""



def _fuente(tam: int):
    if os.path.exists(FUENTE):
        return ImageFont.truetype(FUENTE, tam)
    return ImageFont.load_default()



def _contact_sheet(items: list, destino: Path, vertical: bool = False):
    tarjetas = []
    font = _fuente(14)
    for i, item in enumerate(items, 1):
        ruta = item.get("thumbnail_path")
        if not ruta or not os.path.exists(ruta):
            continue
        try:
            im = Image.open(ruta).convert("RGB")
        except Exception:
            continue
        tw = 180 if vertical else 240
        th = int(im.height * (tw / im.width))
        im = im.resize((tw, th))
        canvas = Image.new("RGB", (tw, th + 62), (18, 18, 18))
        canvas.paste(im, (0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.text((6, th + 4), f"{i}. {item['id']}", font=font, fill=(255, 255, 255))
        titulo = (item.get("title") or "")[:55]
        palabras = titulo.split()
        lineas, linea = [], ""
        for palabra in palabras:
            prueba = (linea + " " + palabra).strip()
            if draw.textlength(prueba, font=font) > tw - 12:
                if linea:
                    lineas.append(linea)
                linea = palabra
                if len(lineas) >= 2:
                    break
            else:
                linea = prueba
        if len(lineas) < 2 and linea:
            lineas.append(linea)
        for n, ln in enumerate(lineas[:2]):
            draw.text((6, th + 22 + n * 16), ln, font=font, fill=(220, 220, 220))
        tarjetas.append(canvas)
    if not tarjetas:
        return
    cols = 3 if vertical else 2
    rows = math.ceil(len(tarjetas) / cols)
    w, h = tarjetas[0].size
    out = Image.new("RGB", (cols * w + (cols - 1) * 10, rows * h + (rows - 1) * 10), (30, 30, 30))
    for idx, card in enumerate(tarjetas):
        out.paste(card, ((idx % cols) * (w + 10), (idx // cols) * (h + 10)))
    out.save(destino)



def _auditar_lista(entries: list, carpeta_thumbs: Path) -> list:
    resultados = []
    carpeta_thumbs.mkdir(parents=True, exist_ok=True)
    for e in entries:
        vid = e["id"]
        meta = _full_meta(vid)
        thumb_url = _mejor_thumb(meta)
        thumb_path = _descargar(thumb_url, carpeta_thumbs / f"{vid}.jpg") if thumb_url else ""
        resultados.append({
            "id": vid,
            "title": meta.get("title"),
            "description": meta.get("description") or "",
            "thumbnail_url": thumb_url,
            "thumbnail_path": thumb_path,
            "webpage_url": meta.get("webpage_url"),
            "duration": meta.get("duration"),
            "view_count": meta.get("view_count"),
            "upload_date": meta.get("upload_date"),
            "title_hits": detectar_hallazgos_ingles_visible(meta.get("title") or ""),
            "description_hits": detectar_hallazgos_ingles_visible(meta.get("description") or ""),
        })
    return resultados



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canal", required=True, help="URL base del canal o @handle")
    ap.add_argument("--salida", default="output/auditoria_canal_publico", help="Carpeta de salida")
    args = ap.parse_args()

    base = args.canal.rstrip("/")
    if not base.startswith("http"):
        base = "https://www.youtube.com/" + base.lstrip("/")

    out_dir = ROOT / args.salida
    out_dir.mkdir(parents=True, exist_ok=True)

    videos = _flat(base + "/videos").get("entries", [])
    shorts = _flat(base + "/shorts").get("entries", [])

    data = {
        "videos": _auditar_lista(videos, out_dir / "thumbs_videos"),
        "shorts": _auditar_lista(shorts, out_dir / "thumbs_shorts"),
    }

    (out_dir / "metadata.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    _contact_sheet(data["videos"], out_dir / "contactsheet_videos.jpg", vertical=False)
    _contact_sheet(data["shorts"], out_dir / "contactsheet_shorts.jpg", vertical=True)

    hallazgos = [
        {
            "kind": kind,
            "id": item["id"],
            "title": item["title"],
            "title_hits": item["title_hits"],
            "description_hits": item["description_hits"],
            "duration": item["duration"],
            "views": item["view_count"],
            "upload_date": item["upload_date"],
        }
        for kind in ("video", "short")
        for item in data["videos" if kind == "video" else "shorts"]
        if item["title_hits"] or item["description_hits"]
    ]
    (out_dir / "english_audit.json").write_text(json.dumps(hallazgos, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Auditoría pública del canal",
        "",
        f"- Canal: {base}",
        f"- Videos auditados: {len(data['videos'])}",
        f"- Shorts auditados: {len(data['shorts'])}",
        "",
        "## Posible mezcla español/inglés detectada",
    ]
    if hallazgos:
        for h in hallazgos:
            md.append(f"- {h['kind']} {h['id']} — {h['title']}")
            if h["title_hits"]:
                md.append(f"  - título: {', '.join(h['title_hits'])}")
            if h["description_hits"]:
                md.append(f"  - descripción: {', '.join(h['description_hits'])}")
    else:
        md.append("- No se detectaron mezclas obvias con la heurística usada.")
    md += [
        "",
        "## Archivos generados",
        "- metadata.json",
        "- english_audit.json",
        "- contactsheet_videos.jpg",
        "- contactsheet_shorts.jpg",
        "",
        "## Nota",
        "Esta auditoría usa reglas heurísticas. Sirve para encontrar problemas visibles rápido,",
        "pero siempre conviene revisar visualmente las contact sheets antes de tomar decisiones finales.",
    ]
    (out_dir / "AUDITORIA_PUBLICA.md").write_text("\n".join(md), encoding="utf-8")
    print(f"OK -> {out_dir}")


if __name__ == "__main__":
    main()
