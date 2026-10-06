"""Rendering degli Shorts verticali 1080x1920 con Pillow + ffmpeg (tutto gratuito)."""
from __future__ import annotations

import math
import os
import random
import subprocess
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .util import log

W, H = 1080, 1920
THEMES = {
    "midnight": ("#0f172a", "#1e3a8a", "#facc15", "#ffffff"),
    "sunset": ("#f97316", "#be185d", "#fff7ad", "#ffffff"),
    "mint": ("#064e3b", "#0d9488", "#fde047", "#ffffff"),
    "neon": ("#0b0f1a", "#6d28d9", "#22d3ee", "#ffffff"),
    "candy": ("#fbcfe8", "#fde68a", "#db2777", "#3b0764"),
    "sky": ("#7dd3fc", "#e0f2fe", "#1d4ed8", "#0c4a6e"),
    "meadow": ("#86efac", "#fef9c3", "#15803d", "#14532d"),
}
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def hex2rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gradient(c1: str, c2: str, seed: int) -> Image.Image:
    a, b = hex2rgb(c1), hex2rgb(c2)
    strip = Image.new("RGB", (1, 256))
    for y in range(256):
        t = y / 255
        strip.putpixel((0, y), tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3)))
    img = strip.resize((W, H), Image.BILINEAR)
    # cerchi morbidi decorativi
    rnd = random.Random(seed)
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    for _ in range(6):
        r = rnd.randint(120, 380)
        x, y = rnd.randint(-100, W + 100), rnd.randint(-100, H + 100)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, rnd.randint(10, 28)))
    over = over.filter(ImageFilter.GaussianBlur(40))
    return Image.alpha_composite(img.convert("RGBA"), over)


def wrap(draw, text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= maxw:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_text(draw, text, maxw, maxh, start=96, minimum=48):
    size = start
    while size >= minimum:
        f = font(size)
        lines = wrap(draw, text, f, maxw)
        if len(lines) * size * 1.25 <= maxh:
            return f, lines
        size -= 4
    f = font(minimum)
    return f, wrap(draw, text, f, maxw)


def text_card(img, text, theme, y_center=H // 2, highlight=True, size=96):
    _, _, accent, fg = THEMES[theme]
    d = ImageDraw.Draw(img, "RGBA")
    f, lines = fit_text(d, text, W - 160, 900, start=size)
    key = max(text.split(), key=len).strip(".,!?:;") if highlight else None
    lh = int(f.size * 1.25)
    y = y_center - lh * len(lines) // 2
    for line in lines:
        x = (W - d.textlength(line, font=f)) // 2
        for word in line.split(" "):
            col = accent if key and word.strip(".,!?:;") == key else fg
            d.text((x + 4, y + 5), word, font=f, fill=(0, 0, 0, 120))
            d.text((x, y), word, font=f, fill=col)
            x += d.textlength(word + " ", font=f)
        y += lh


def header(img, label, theme, idx, total):
    _, _, accent, fg = THEMES[theme]
    d = ImageDraw.Draw(img, "RGBA")
    f = font(40)
    tw = d.textlength(label, font=f)
    d.rounded_rectangle(((W - tw) / 2 - 30, 150, (W + tw) / 2 + 30, 222), 36, fill=accent)
    dark = "#111111" if fg == "#ffffff" else "#ffffff"
    d.text(((W - tw) / 2, 162), label, font=f, fill=dark)
    # puntini di avanzamento
    gap = 34
    x0 = (W - gap * (total - 1)) / 2
    for i in range(total):
        r = 9 if i == idx else 6
        d.ellipse((x0 + i * gap - r, 1640 - r, x0 + i * gap + r, 1640 + r), fill=fg if i <= idx else (255, 255, 255, 90))


def draw_shape(d, kind, cx, cy, r, color):
    if kind == "circle":
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color, outline="white", width=6)
    elif kind == "square":
        d.rounded_rectangle((cx - r, cy - r, cx + r, cy + r), 18, fill=color, outline="white", width=6)
    elif kind == "triangle":
        d.polygon([(cx, cy - r), (cx - r, cy + r * 0.8), (cx + r, cy + r * 0.8)], fill=color, outline="white")
    elif kind == "star":
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.45
            pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
        d.polygon(pts, fill=color, outline="white")
    elif kind == "heart":
        d.ellipse((cx - r, cy - r * 0.7, cx, cy + r * 0.2), fill=color)
        d.ellipse((cx, cy - r * 0.7, cx + r, cy + r * 0.2), fill=color)
        d.polygon([(cx - r * 0.98, cy - r * 0.15), (cx + r * 0.98, cy - r * 0.15), (cx, cy + r)], fill=color)


def kids_scene(img, scene, line, theme):
    d = ImageDraw.Draw(img, "RGBA")
    kind = scene.get("kind")
    if kind == "count":
        n, cols = scene["n"], 3 if scene["n"] <= 9 else 4
        r = 95 if cols == 3 else 80
        rows = math.ceil(n / cols)
        for i in range(n):
            row, col = divmod(i, cols)
            in_row = min(cols, n - row * cols)
            cx = W / 2 + (col - (in_row - 1) / 2) * (r * 2.4)
            cy = 760 + (row - (rows - 1) / 2) * (r * 2.4)
            draw_shape(d, scene["shape"], cx, cy, r, scene["color"])
        f = font(220)
        txt = str(n)
        d.text(((W - d.textlength(txt, font=f)) / 2, 1180), txt, font=f, fill=THEMES[theme][2])
        text_card(img, line, theme, y_center=1520, highlight=False, size=80)
        return
    if kind in ("color", "shape"):
        draw_shape(d, "circle" if kind == "color" else scene["shape"], W / 2, 820, 300, scene["color"])
    elif kind == "letter":
        f = font(620)
        L = scene["letter"]
        d.text(((W - d.textlength(L, font=f)) / 2, 420), L, font=f, fill=scene["color"], stroke_width=10, stroke_fill="white")
    elif kind == "animal":
        f = font(130)
        lab = scene.get("label", "").capitalize()
        d.text(((W - d.textlength(lab, font=f)) / 2, 700), lab, font=f, fill=THEMES[theme][2], stroke_width=6, stroke_fill="white")
    else:
        text_card(img, line, theme, highlight=False, size=110)
        return
    text_card(img, line, theme, y_center=1440, highlight=False, size=84)


def tshirt_mockup(img, design: Image.Image, y=420):
    d = ImageDraw.Draw(img, "RGBA")
    cx, w = W // 2, 640
    body = [(cx - w / 2, y + 140), (cx - w / 2 - 170, y + 300), (cx - w / 2 - 80, y + 420), (cx - w / 2, y + 360),
            (cx - w / 2, y + 1000), (cx + w / 2, y + 1000), (cx + w / 2, y + 360), (cx + w / 2 + 80, y + 420),
            (cx + w / 2 + 170, y + 300), (cx + w / 2, y + 140), (cx + 110, y + 100), (cx - 110, y + 100)]
    d.polygon(body, fill="#1f2937")
    d.ellipse((cx - 110, y + 60, cx + 110, y + 150), fill=None, outline="#374151", width=10)
    dz = design.copy()
    dz.thumbnail((520, 600))
    img.paste(dz, (cx - dz.width // 2, y + 300), dz)


def _pexels_background(query: str, workdir: Path) -> Path | None:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return None
    try:
        r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": key},
                         params={"query": query, "orientation": "portrait", "per_page": 15}, timeout=30)
        vids = r.json().get("videos", [])
        random.shuffle(vids)
        for v in vids:
            files = [f for f in v["video_files"] if f.get("height", 0) >= 1280 and f.get("width", 0) < f.get("height", 0)]
            if files:
                f = min(files, key=lambda x: x["height"])
                p = workdir / "bg.mp4"
                with requests.get(f["link"], stream=True, timeout=60) as resp:
                    resp.raise_for_status()
                    with open(p, "wb") as fh:
                        for chunk in resp.iter_content(1 << 16):
                            fh.write(chunk)
                return p
    except Exception as e:  # noqa: BLE001
        log(f"Pexels non disponibile: {e}")
    return None


def render(item: dict, audio: list[tuple[Path, float]], workdir: Path, out_path: Path,
           label: str, kids: bool = False, pod_images: list | None = None, bg_query: str | None = None) -> Path:
    """Crea il video finale. item: {lines, scenes?, variant:{theme}}."""
    theme = item["variant"]["theme"]
    c1, c2, *_ = THEMES[theme]
    seed = sum(map(ord, item["title"]))
    bg_video = None if kids else _pexels_background(bg_query or label, workdir)
    base = gradient(c1, c2, seed)
    lines = item["lines"]
    scenes = item.get("scenes") or [{}] * len(lines)
    slides = []
    for i, line in enumerate(lines):
        if bg_video:
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            shade = Image.new("RGBA", (W, H), (0, 0, 0, 110))
            img = Image.alpha_composite(img, shade)
        else:
            img = base.copy()
        header(img, label, theme, i, len(lines))
        if kids:
            kids_scene(img, scenes[i] if i < len(scenes) else {}, line, theme)
        elif pod_images and 0 < i <= len(pod_images):
            tshirt_mockup(img, pod_images[i - 1], y=320)
            text_card(img, line, theme, y_center=1500, size=66)
        else:
            text_card(img, line, theme, size=104 if i == 0 else 92)
        p = workdir / f"slide_{i:02d}.png"
        (img if bg_video else img.convert("RGB")).save(p)
        slides.append(p)

    # elenco concat (immagini + audio)
    total = sum(d for _, d in audio) + 0.25 * len(audio)
    with open(workdir / "slides.txt", "w") as f:
        for p, (_, dur) in zip(slides, audio):
            f.write(f"file '{p.resolve()}'\nduration {dur + 0.25:.3f}\n")
        f.write(f"file '{slides[-1].resolve()}'\n")
    with open(workdir / "audio.txt", "w") as f:
        for a, _ in audio:
            f.write(f"file '{a.resolve()}'\n")
    pad = workdir / "pad.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                    "-t", "0.25", str(pad)], check=True)
    with open(workdir / "audio.txt", "w") as f:
        for a, _ in audio:
            f.write(f"file '{a.resolve()}'\nfile '{pad.resolve()}'\n")
    voice = workdir / "voice.m4a"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(workdir / "audio.txt"),
                    "-c:a", "aac", "-b:a", "128k", str(voice)], check=True)

    accent = THEMES[theme][2].lstrip("#")
    bar = f"drawbox=x=0:y=ih-18:w='iw*t/{total:.2f}':h=18:color=0x{accent}@0.9:t=fill"
    if bg_video:
        inputs = ["-stream_loop", "-1", "-i", str(bg_video), "-f", "concat", "-safe", "0", "-i", str(workdir / "slides.txt"), "-i", str(voice)]
        fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=30[bg];"
              f"[1:v]format=rgba,fps=30[ov];[bg][ov]overlay=0:0:shortest=1,{bar},format=yuv420p[v]")
        amap = "2:a"
    else:
        inputs = ["-f", "concat", "-safe", "0", "-i", str(workdir / "slides.txt"), "-i", str(voice)]
        fc = f"[0:v]fps=30,scale={W}:{H},setsar=1,{bar},format=yuv420p[v]"
        amap = "1:a"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc, "-map", "[v]", "-map", amap,
           "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-c:a", "aac",
           "-movflags", "+faststart", str(out_path)]
    subprocess.run(cmd, check=True)
    return out_path
