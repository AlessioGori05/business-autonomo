"""Sito statico gratuito (GitHub Pages, cartella docs/): pagina "link in bio", liste affiliate,
guide gratuite con raccolta email, vetrina design POD, privacy e trasparenza affiliazioni."""
from __future__ import annotations

import html
import urllib.parse

from .util import DOCS, ledger, read_json, settings, site_base_url, today
from .leadmagnet import GUIDES

T = {
    "en": {"picks": "Latest picks", "guides": "Free guides", "designs": "New designs", "shop": "See the shop",
           "disclosure": "As an Amazon Associate we earn from qualifying purchases. Links open a store search so you can compare options and current prices.",
           "check": "Check before buying", "search": "See options", "download": "Download the free guide",
           "email": "Your email", "send": "Send me the guide", "privacy": "Privacy",
           "privacy_text": "We only store the email you give us to send you the guide and occasional tips. You can unsubscribe with one click in every email. Anonymous visit counts may be collected to improve the site. No data is sold.",
           "tagline": "Useful ideas from our Shorts, in one place.", "back": "All links", "inside": "Inside the guide"},
    "it": {"picks": "Ultime selezioni", "guides": "Guide gratuite", "designs": "Nuovi design", "shop": "Vai al negozio",
           "disclosure": "In qualità di Affiliato Amazon riceviamo un guadagno dagli acquisti idonei. I link aprono una ricerca nel negozio per confrontare opzioni e prezzi aggiornati.",
           "check": "Da controllare prima di comprare", "search": "Vedi le opzioni", "download": "Scarica la guida gratuita",
           "email": "La tua email", "send": "Inviami la guida", "privacy": "Privacy",
           "privacy_text": "Conserviamo solo l'email che ci fornisci per inviarti la guida e qualche consiglio. Puoi disiscriverti con un clic da ogni email. Possono essere raccolti conteggi anonimi delle visite per migliorare il sito. Nessun dato viene venduto.",
           "tagline": "Le idee utili dei nostri Shorts, in un unico posto.", "back": "Tutti i link", "inside": "Cosa trovi nella guida"},
}

CSS = """
:root{--bg:#f8fafc;--fg:#0f172a;--muted:#475569;--card:#fff;--line:#e2e8f0;--accent:#1d4ed8;--accent-fg:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#0b1120;--fg:#e2e8f0;--muted:#94a3b8;--card:#111827;--line:#1f2937;--accent:#60a5fa;--accent-fg:#0b1120}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:680px;margin:0 auto;padding:32px 16px 64px}h1{font-size:28px;line-height:1.2;margin:0 0 8px}h2{font-size:20px;margin:32px 0 12px}
p.muted,.muted{color:var(--muted)}a{color:var(--accent)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:12px 0}
.card h3{margin:0 0 6px;font-size:18px}.btn{display:inline-block;background:var(--accent);color:var(--accent-fg);padding:10px 16px;border-radius:10px;text-decoration:none;font-weight:600;border:0;cursor:pointer;font-size:16px}
.list a.card{display:block;text-decoration:none;color:var(--fg)}.small{font-size:13px}
input[type=email]{width:100%;padding:12px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--fg);font-size:16px;margin:8px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}.grid img{width:100%;border-radius:12px;background:#334155}
footer{margin-top:48px;font-size:13px;color:var(--muted)}
"""


def page(title: str, body: str, lang: str, depth: int = 1) -> str:
    cfg = settings()["site"]
    gc = cfg.get("goatcounter_code")
    up = "../" * depth
    tracker = (f'<script data-goatcounter="https://{gc}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>'
               if gc else "")
    t = T[lang]
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<style>{CSS}</style>{tracker}</head><body><main>{body}
<footer><a href="{up}{lang}/index.html">{t['back']}</a> · <a href="{up}{lang}/privacy.html">{t['privacy']}</a> · {today().year}</footer>
</main></body></html>"""


def amazon_link(lang: str, query: str) -> str:
    cfg = settings()["site"]
    params = {"k": query}
    tag = cfg.get(f"amazon_tag_{lang}")
    if tag:
        params["tag"] = tag
    return f"https://www.{cfg[f'amazon_domain_{lang}']}/s?{urllib.parse.urlencode(params)}"


def build():
    cfg = settings()["site"]
    items = ledger()
    guides = read_json(GUIDES, {})
    (DOCS / ".nojekyll").write_text("")
    for lang in ("en", "it"):
        t = T[lang]
        brand = cfg[f"brand_name_{lang}"]
        out = DOCS / lang
        out.mkdir(parents=True, exist_ok=True)

        # pagine affiliate
        picks = [i for i in items if i.get("lang") == lang and i.get("products") and i.get("landing")]
        for it in picks:
            cards = "".join(
                f'<div class="card"><h3>{html.escape(p["name"])}</h3><p>{html.escape(p.get("why", ""))}</p>'
                f'<p class="small muted"><b>{t["check"]}:</b> {html.escape(p.get("check_before_buying", ""))}</p>'
                f'<a class="btn" rel="sponsored nofollow noopener" target="_blank" data-goatcounter-click="aff-{html.escape(it["id"])}" '
                f'href="{html.escape(amazon_link(lang, p.get("search_query", p["name"])))}">{t["search"]}</a></div>'
                for p in it["products"])
            body = (f'<p class="muted small">{html.escape(brand)}</p><h1>{html.escape(it["title"])}</h1>'
                    f'<p>{html.escape(it.get("page_intro", ""))}</p>{cards}'
                    + (f'<p class="small muted">{t["disclosure"]}</p>' if cfg.get(f"amazon_tag_{lang}") else ""))
            (DOCS / f'{it["landing"]}.html').write_text(page(it["title"], body, lang), encoding="utf-8")

        # pagine guide
        lg = [g for g in guides.values() if g["lang"] == lang]
        action = cfg.get(f"newsletter_form_action_{lang}")
        for g in lg:
            chapters = "".join(f"<li>{html.escape(c)}</li>" for c in g.get("chapters", []))
            if action:
                cta = (f'<form class="card" method="post" action="{html.escape(action)}" data-goatcounter-click="lead-{g["slug"]}">'
                       f'<label>{t["email"]}<input type="email" required name="{html.escape(cfg.get("newsletter_email_field", "email"))}"></label>'
                       f'<button class="btn" type="submit">{t["send"]}</button>'
                       f'<p class="small muted">{t["privacy_text"]}</p></form>')
            else:
                cta = f'<p><a class="btn" data-goatcounter-click="lead-{g["slug"]}" href="../{g["pdf"]}">{t["download"]}</a></p>'
            body = (f'<p class="muted small">{html.escape(brand)}</p><h1>{html.escape(g["title"])}</h1>'
                    f'<p class="muted">{html.escape(g.get("subtitle", ""))}</p><p>{html.escape(g.get("intro", ""))}</p>'
                    f'<h2>{t["inside"]}</h2><ul>{chapters}</ul>{cta}')
            (out / f'guide-{g["slug"]}.html').write_text(page(g["title"], body, lang), encoding="utf-8")

        # vetrina POD
        pod_dir = DOCS / "pod"
        previews = sorted(pod_dir.glob(f"*/{lang}/*.png"), reverse=True)[:12] if pod_dir.exists() else []
        store = cfg.get(f"pod_store_url_{lang}")

        # hub "link in bio"
        sec = [f'<h1>{html.escape(brand)}</h1><p class="muted">{t["tagline"]}</p>']
        if lg:
            sec.append(f'<h2>{t["guides"]}</h2><div class="list">' + "".join(
                f'<a class="card" href="guide-{g["slug"]}.html"><h3>{html.escape(g["title"])}</h3>'
                f'<span class="muted small">{html.escape(g.get("subtitle", ""))}</span></a>' for g in reversed(lg[-6:])) + "</div>")
        if picks:
            sec.append(f'<h2>{t["picks"]}</h2><div class="list">' + "".join(
                f'<a class="card" href="{it["landing"].split("/", 1)[1]}.html"><h3>{html.escape(it["title"])}</h3></a>'
                for it in reversed(picks[-15:])) + "</div>")
        if previews and store:
            sec.append(f'<h2>{t["designs"]}</h2><div class="grid">' + "".join(
                f'<img loading="lazy" alt="" src="../{p.relative_to(DOCS).as_posix()}">' for p in previews) +
                f'</div><p><a class="btn" rel="noopener" target="_blank" href="{html.escape(store)}">{t["shop"]}</a></p>')
        (out / "index.html").write_text(page(brand, "".join(sec), lang), encoding="utf-8")
        (out / "privacy.html").write_text(page(t["privacy"], f'<h1>{t["privacy"]}</h1><p>{t["privacy_text"]}</p>' + (f'<p>{t["disclosure"]}</p>' if cfg.get(f"amazon_tag_{lang}") else ""), lang), encoding="utf-8")

    root = (f'<h1>{html.escape(cfg["brand_name_en"])}</h1><div class="list">'
            f'<a class="card" href="en/index.html"><h3>English</h3></a><a class="card" href="it/index.html"><h3>Italiano</h3></a></div>')
    (DOCS / "index.html").write_text(page(cfg["brand_name_en"], root, "en", depth=0), encoding="utf-8")
    return site_base_url(settings())
