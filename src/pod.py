"""Print on Demand: crea file grafici pronti per Redbubble/Spreadshirt/Teepublic.

Le piattaforme POD gratuite non offrono API pubbliche di caricamento, quindi il sistema
prepara tutto (PNG 4500x5400 trasparente + titolo/tag/descrizione in listing.csv) nella
cartella pod/<settimana>/ e ti apre una issue: caricarli richiede ~2 minuti a design.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

from PIL import Image, ImageDraw

from .render import font, wrap
from .util import DOCS, OUT, ROOT, iso_week, log, short_hash, slugify, today

PALETTES = [("#111827", "#f59e0b"), ("#ffffff", "#22d3ee"), ("#fde68a", "#f472b6"), ("#ffffff", "#a3e635"),
            ("#1f2937", "#ef4444")]


def design_png(slogan: str, seed: int, size=(4500, 5400)) -> Image.Image:
    rnd = random.Random(seed)
    main, accent = rnd.choice(PALETTES)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    Wd, Hd = size
    words = slogan.upper()
    fsize = 520
    while fsize > 160:
        f = font(fsize)
        lines = wrap(d, words, f, Wd - 600)
        if len(lines) * fsize * 1.15 < Hd * 0.6 and len(lines) <= 4:
            break
        fsize -= 20
    lh = int(fsize * 1.15)
    y = (Hd - lh * len(lines)) // 2
    # elemento decorativo
    d.rounded_rectangle((Wd * 0.2, y - 260, Wd * 0.8, y - 200), 30, fill=accent)
    d.rounded_rectangle((Wd * 0.2, y + lh * len(lines) + 140, Wd * 0.8, y + lh * len(lines) + 200), 30, fill=accent)
    for i, line in enumerate(lines):
        col = accent if i == len(lines) - 1 and len(lines) > 1 else main
        x = (Wd - d.textlength(line, font=f)) / 2
        stroke = "#000000" if main != "#111827" and main != "#1f2937" else "#ffffff"
        d.text((x, y), line, font=f, fill=col, stroke_width=14, stroke_fill=stroke)
        y += lh
    return img


def build_week(designs: list[dict], lang: str) -> list[dict]:
    # file grandi -> out/pod (scaricabili come "artifact" dalla pagina Actions, non appesantiscono il repo)
    # anteprime piccole -> docs/pod (usate dal sito e dai video)
    week_dir = OUT / "pod" / iso_week(today()) / lang
    prev_dir = DOCS / "pod" / iso_week(today()) / lang
    week_dir.mkdir(parents=True, exist_ok=True)
    prev_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, dsg in enumerate(designs):
        name = slugify(dsg["slogan"], 40)
        img = design_png(dsg["slogan"], seed=int(short_hash(dsg["slogan"]), 16))
        path = week_dir / f"{name}.png"
        img.save(path, optimize=True)
        # anteprima piccola per i video e il sito
        prev = img.copy()
        prev.thumbnail((900, 1080))
        prev_path = prev_dir / f"{name}.png"
        prev.save(prev_path, optimize=True)
        rows.append({**dsg, "file": path.name, "preview": str(prev_path.relative_to(ROOT))})
    with open(week_dir / "listing.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "listing_title", "slogan", "audience", "tags", "description"])
        w.writeheader()
        for r in rows:
            w.writerow({"file": r["file"], "listing_title": r.get("listing_title", r["slogan"]), "slogan": r["slogan"],
                        "audience": r.get("audience", ""), "tags": ", ".join(r.get("tags", [])),
                        "description": r.get("description", "")})
    log(f"POD: {len(rows)} design pronti ({lang})")
    return rows
