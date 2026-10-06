"""Checklist automatica di controllo qualità prima della pubblicazione."""
from __future__ import annotations

import difflib
import re

BANNED = [
    # rischio policy / spam / promesse false
    "guaranteed", "garantito", "get rich", "diventa ricco", "cure", "cura definitiva", "miracle", "miracolo",
    "100% free money", "soldi facili", "click here", "clicca qui", "subscribe or", "kill", "uccid",
    "sex", "sesso", "drug", "droga", "gambling", "scommess", "casino",
    # marchi/personaggi più comuni (copyright)
    "disney", "pokemon", "pokémon", "marvel", "peppa", "paw patrol", "minecraft", "fortnite",
    "coca-cola", "lego", "barbie", "spongebob", "bluey", "cocomelon",
]
URL_RE = re.compile(r"https?://|www\.", re.I)


def check(item: dict, past_titles: list, kids: bool = False) -> list[str]:
    """Restituisce l'elenco dei problemi. Lista vuota = OK."""
    problems = []
    title = (item.get("title") or "").strip()
    lines = item.get("lines") or []
    text = " ".join([title, item.get("description", "")] + lines).lower()

    if not title or len(title) > 100:
        problems.append("titolo mancante o troppo lungo")
    if not (4 <= len(lines) <= 16):
        problems.append(f"numero di righe anomalo ({len(lines)})")
    if any(len(l.split()) > 22 for l in lines):
        problems.append("riga troppo lunga per lo schermo")
    for w in BANNED:
        if re.search(r"\b" + re.escape(w), text):
            problems.append(f"parola a rischio: '{w}'")
    if URL_RE.search(text):
        problems.append("contiene link esterni nel testo")
    if float(item.get("facts_confidence", 0) or 0) < 0.8:
        problems.append("affidabilità dei fatti bassa")
    for t in past_titles[-300:]:
        if difflib.SequenceMatcher(None, title.lower(), t.lower()).ratio() > 0.85:
            problems.append(f"troppo simile a un titolo già pubblicato: '{t}'")
            break
    if len(set(l.lower() for l in lines)) < len(lines) * 0.7 and not kids:
        problems.append("righe ripetitive")
    if kids:
        if re.search(r"link|bio|profil|subscribe|iscriviti|compra|buy", text):
            problems.append("contenuto bambini con invito all'azione/link (vietato)")
    return problems


FACTCHECK_SYSTEM = (
    "You are a strict fact-checker and editor for short educational videos. You reject anything that is "
    "false, disputed, a myth or legend presented as fact, internally contradictory, misleading, "
    "unsafe advice, or confusing. You are conservative: when unsure, reject."
)


def fact_check(item: dict, ask_json) -> list[str]:
    """Seconda verifica con l'AI. Restituisce i problemi trovati (lista vuota = OK)."""
    script = "\n".join(f"{n + 1}. {l}" for n, l in enumerate(item.get("lines", [])))
    prods = item.get("products") or []
    extra = "\nProducts:\n" + "\n".join(f"- {p.get('name')}: {p.get('why')}" for p in prods) if prods else ""
    res = ask_json(FACTCHECK_SYSTEM,
                   f"Title: {item.get('title')}\nScript:\n{script}{extra}\n\n"
                   "Check every claim. Return JSON: {\"verdict\": \"ok\" or \"reject\", \"issues\": [short strings]}",
                   temperature=0.1)
    if not isinstance(res, dict):
        return ["verifica dei fatti non disponibile"]
    if str(res.get("verdict", "")).lower() != "ok":
        return ["verifica fatti: " + "; ".join(map(str, res.get("issues") or ["respinto"]))[:300]]
    return []
