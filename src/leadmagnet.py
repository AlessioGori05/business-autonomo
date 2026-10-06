"""Lead magnet: mini-guida PDF gratuita + sequenza email da incollare una volta in MailerLite/Brevo."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .render import font, wrap
from .util import DATA, DOCS, ROOT, log, read_json, slugify, write_json

GUIDES = DATA / "guides.json"
PW, PH, M = 1240, 1754, 110  # A4 a 150 dpi


class _Doc:
    def __init__(self, accent="#1e3a8a"):
        self.pages, self.accent = [], accent
        self.new_page()

    def new_page(self):
        self.img = Image.new("RGB", (PW, PH), "white")
        self.d = ImageDraw.Draw(self.img)
        self.y = M
        self.pages.append(self.img)

    def text(self, txt, size=30, color="#1f2937", gap=14, indent=0, bullet=False):
        f = font(size)
        lines = wrap(self.d, txt, f, PW - 2 * M - indent - (40 if bullet else 0))
        for i, line in enumerate(lines):
            if self.y + size * 1.4 > PH - M:
                self.new_page()
            x = M + indent
            if bullet and i == 0:
                self.d.ellipse((x + 6, self.y + size * 0.35, x + 20, self.y + size * 0.35 + 14), fill=self.accent)
            self.d.text((x + (40 if bullet else 0), self.y), line, font=f, fill=color)
            self.y += int(size * 1.4)
        self.y += gap

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        for i, p in enumerate(self.pages):  # numeri di pagina
            ImageDraw.Draw(p).text((PW - M - 40, PH - 70), str(i + 1), font=font(22), fill="#9ca3af")
        self.pages[0].save(path, save_all=True, append_images=self.pages[1:], resolution=150)


def build_pdf(guide: dict, path: Path, brand: str):
    doc = _Doc()
    # copertina
    doc.d.rectangle((0, 0, PW, 620), fill=doc.accent)
    doc.d.text((M, 120), brand.upper(), font=font(30), fill="#facc15")
    doc.y = 200
    for line in wrap(doc.d, guide["title"], font(72), PW - 2 * M):
        doc.d.text((M, doc.y), line, font=font(72), fill="white")
        doc.y += 92
    doc.y = 680
    doc.text(guide.get("subtitle", ""), size=36, color="#374151", gap=40)
    doc.text(guide.get("intro", ""), size=30, gap=30)
    for n, ch in enumerate(guide.get("chapters", []), 1):
        doc.new_page() if doc.y > PH * 0.6 else None
        doc.text(f"{n}. {ch['heading']}", size=44, color=doc.accent, gap=20)
        for tip in ch.get("tips", []):
            doc.text(tip, size=29, bullet=True, gap=10)
        doc.y += 30
    doc.new_page()
    doc.text("Checklist", size=48, color=doc.accent, gap=24)
    for item in guide.get("checklist", []):
        doc.d.rectangle((M, doc.y + 6, M + 26, doc.y + 32), outline=doc.accent, width=3)
        doc.text(item, size=30, indent=50, gap=12)
    doc.save(path)


def ensure_guide(lang: str, topic: str, brand: str, generate_fn) -> dict | None:
    """Restituisce la guida per (lingua, argomento), creandola se non esiste."""
    guides = read_json(GUIDES, {})
    key = f"{lang}:{topic}"
    if key in guides:
        return guides[key]
    data = generate_fn(lang, topic)
    if not data or not data.get("chapters"):
        return None
    slug = slugify(data["title"], 50)
    pdf_rel = f"guides/{lang}/{slug}.pdf"
    build_pdf(data, DOCS / pdf_rel, brand)
    # sequenza email da copiare una volta nell'automazione del tuo servizio email gratuito
    md = [f"# Sequenza email - {data['title']}\n",
          "Incolla queste email nell'automazione di benvenuto del tuo servizio email gratuito "
          "(MailerLite: Automations > New > 'When subscriber joins a group').\n"]
    for i, e in enumerate(data.get("emails", []), 1):
        md.append(f"\n## Email {i} (giorno {[0, 2, 4, 7][min(i - 1, 3)]})\n\n**Oggetto:** {e['subject']}\n\n{e['body']}\n")
    funnel = ROOT / "funnels" / lang / f"{slug}.md"
    funnel.parent.mkdir(parents=True, exist_ok=True)
    funnel.write_text("".join(md), encoding="utf-8")
    entry = {"lang": lang, "topic": topic, "title": data["title"], "subtitle": data.get("subtitle", ""),
             "intro": data.get("intro", ""), "slug": slug, "pdf": pdf_rel,
             "funnel": str(funnel.relative_to(ROOT)),
             "chapters": [c["heading"] for c in data.get("chapters", [])]}
    guides[key] = entry
    write_json(GUIDES, guides)
    log(f"Lead magnet creato: {data['title']} ({lang})")
    return entry
