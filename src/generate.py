"""Generazione dei testi (script, titoli, descrizioni) per ogni metodo e variante."""
from __future__ import annotations

import random

from . import llm
from .util import log, short_hash, slugify, today

LANG_NAME = {"en": "English", "it": "Italian"}

HOOKS = {
    "question": "open with a curiosity question the viewer can't ignore",
    "shocking_fact": "open with the single most surprising fact, stated boldly",
    "countdown": "structure it as a fast countdown (3, 2, 1) with the best item last",
    "you_are_doing_it_wrong": "open with 'You're doing X wrong' style framing, then fix it",
    "mini_story": "open with a 1-sentence micro story that sets up the payoff",
    "problem_solution": "open with a relatable everyday problem, then show the solution",
    "sing_along": "gentle rhythmic rhyming lines a child can repeat",
    "guess_game": "ask the child to guess before revealing each answer",
    "learn_together": "warm teacher voice: 'let's learn together'",
}

LINES = {"short": (5, 7), "long": (9, 12)}

SYSTEM = (
    "You are a senior short-form video scriptwriter for a faceless YouTube Shorts channel. "
    "You write ORIGINAL, genuinely useful content. Rules: never invent statistics; only include "
    "facts that are widely established and verifiable; no medical, legal or financial advice beyond "
    "common-sense tips; no brand names, celebrities, copyrighted characters, song lyrics or quotes; "
    "no clickbait that the video does not deliver; family-friendly language."
)


def pick_variant(variants: list, usage: dict) -> dict | None:
    active = [v for v in variants if v["status"] in ("testing", "winner")]
    if not active:
        return None
    # vincitori pesano il doppio: meno utilizzi "effettivi" -> scelti prima
    return min(active, key=lambda v: (usage.get(v["code"], 0) / (2 if v["status"] == "winner" else 1), random.random()))


def pick_topic(method: dict, lang: str, recent_topics: list) -> str:
    pool = method["topics"][lang]
    fresh = [t for t in pool if t not in recent_topics[-len(pool) // 2:]] or pool
    return random.choice(fresh)


def _base_prompt(lang, topic, variant, past_titles):
    lo, hi = LINES[variant["length"]]
    avoid = "\n".join(f"- {t}" for t in past_titles[-40:]) or "- (none)"
    return (
        f"Language: {LANG_NAME[lang]} (write everything in this language).\n"
        f"Topic: {topic}\nHook style: {HOOKS[variant['hook']]}.\n"
        f"Script length: {lo}-{hi} lines, each line max 14 words, spoken in ~2.5 seconds.\n"
        f"Do NOT repeat these previous titles or their angle:\n{avoid}\n"
    )


def gen_viral(lang, topic, variant, past_titles):
    user = _base_prompt(lang, topic, variant, past_titles) + (
        "Return JSON: {\"title\": str (max 70 chars, no hashtags), \"lines\": [str], "
        "\"description\": str (2 sentences), \"tags\": [8 short tags], "
        "\"facts_confidence\": number 0-1 (how sure you are every claim is true)}"
    )
    return llm.ask_json(SYSTEM, user)


def gen_affiliate(lang, topic, variant, past_titles):
    cta = "Link in bio for the full list" if lang == "en" else "Link nel profilo per la lista completa"
    user = _base_prompt(lang, topic, variant, past_titles) + (
        "Pick exactly 3 GENERIC product types (no brand names, no model numbers, no prices) that solve a real need.\n"
        f"The last script line must be: '{cta}'.\n"
        "Return JSON: {\"title\": str (max 70 chars), \"lines\": [str], \"description\": str, \"tags\": [8], "
        "\"facts_confidence\": number 0-1, \"page_intro\": str (60-90 words), "
        "\"products\": [{\"name\": str, \"search_query\": str (2-5 words for a store search), "
        "\"why\": str (1-2 sentences), \"check_before_buying\": str (1 sentence)}]}"
    )
    return llm.ask_json(SYSTEM, user)


def gen_leadmagnet_short(lang, topic, variant, past_titles, guide_title):
    cta = (f"Free guide '{guide_title}' - link in bio" if lang == "en"
           else f"Guida gratis '{guide_title}' - link nel profilo")
    user = _base_prompt(lang, topic, variant, past_titles) + (
        f"Give 2-3 quick practical tips from a free guide called '{guide_title}'. Last line must be: '{cta}'.\n"
        "Return JSON: {\"title\": str, \"lines\": [str], \"description\": str, \"tags\": [8], \"facts_confidence\": number}"
    )
    return llm.ask_json(SYSTEM, user)


def gen_guide(lang, topic):
    user = (
        f"Language: {LANG_NAME[lang]}. Write a free practical mini-guide (lead magnet) about: {topic}.\n"
        "Return JSON: {\"title\": str (catchy, max 60 chars), \"subtitle\": str, \"intro\": str (80 words), "
        "\"chapters\": [{\"heading\": str, \"tips\": [4 actionable tips, 1-2 sentences each]}] (5 chapters), "
        "\"checklist\": [7 short items], "
        "\"emails\": [{\"subject\": str, \"body\": str (120-180 words, friendly, value first)}] (4 emails: welcome+guide, tip, story, soft offer of more guides)}"
    )
    return llm.ask_json(SYSTEM, user, temperature=0.7)


def gen_pod_designs(lang, topics, n, past_slogans):
    avoid = ", ".join(past_slogans[-60:]) or "(none)"
    user = (
        f"Language: {LANG_NAME[lang]}. Create {n} ORIGINAL short slogans for t-shirt/mug designs (print on demand).\n"
        f"Audiences to choose from: {', '.join(topics)}.\n"
        "Rules: max 6 words, witty and wholesome, no brand names, no famous quotes, no song/movie lines, "
        "no trademarked phrases. Avoid these previous slogans: " + avoid + "\n"
        "Return JSON: [{\"slogan\": str, \"audience\": str, \"listing_title\": str (max 60 chars), "
        "\"tags\": [10 tags], \"description\": str (2 sentences)}]"
    )
    return llm.ask_json(SYSTEM, user)


def gen_pod_short(lang, variant, designs, past_titles):
    cta = "Find them via the link in bio" if lang == "en" else "Le trovi col link nel profilo"
    slogans = "; ".join(d["slogan"] for d in designs)
    user = _base_prompt(lang, "new t-shirt designs: " + slogans, variant, past_titles) + (
        f"Present these designs playfully, one per line, with who they're perfect for. Last line: '{cta}'.\n"
        "Return JSON: {\"title\": str, \"lines\": [str], \"description\": str, \"tags\": [8], \"facts_confidence\": 1}"
    )
    return llm.ask_json(SYSTEM, user)


# ------------------------------------------------------------- bambini
COLORS = {
    "en": [("red", "#E53935"), ("blue", "#1E88E5"), ("yellow", "#FDD835"), ("green", "#43A047"),
           ("orange", "#FB8C00"), ("purple", "#8E24AA"), ("pink", "#EC407A")],
    "it": [("rosso", "#E53935"), ("blu", "#1E88E5"), ("giallo", "#FDD835"), ("verde", "#43A047"),
           ("arancione", "#FB8C00"), ("viola", "#8E24AA"), ("rosa", "#EC407A")],
}
SHAPES = {"en": ["circle", "square", "triangle", "star", "heart"],
          "it": ["cerchio", "quadrato", "triangolo", "stella", "cuore"]}
SHAPE_KEYS = ["circle", "square", "triangle", "star", "heart"]
NUM_WORDS = {"en": "one two three four five six seven eight nine ten".split(),
             "it": "uno due tre quattro cinque sei sette otto nove dieci".split()}


def gen_kids(lang, topic_idx, variant, past_titles):
    """Contenuti per bambini: procedurali (sicuri e verificabili) + animali via AI con QC."""
    t = topic_idx
    rnd = random.Random()
    if t == 0:  # contare
        k = rnd.choice([5, 6, 7, 8, 10])
        color, hexc = rnd.choice(COLORS[lang])
        shape = rnd.randrange(len(SHAPE_KEYS))
        sname = SHAPES[lang][shape]
        intro = (f"Let's count to {k} together!" if lang == "en" else f"Contiamo fino a {k} insieme!")
        lines, scenes = [intro], [{"kind": "title"}]
        for i in range(1, k + 1):
            lines.append(f"{NUM_WORDS[lang][i - 1].capitalize()}!")
            scenes.append({"kind": "count", "n": i, "shape": SHAPE_KEYS[shape], "color": hexc})
        lines.append("Great job! You counted to " + str(k) + "!" if lang == "en" else f"Bravissimo! Hai contato fino a {k}!")
        scenes.append({"kind": "count", "n": k, "shape": SHAPE_KEYS[shape], "color": hexc})
        title = (f"Count to {k} with {color} {sname}s" if lang == "en" else f"Contiamo fino a {k} con le forme {color}")
    elif t == 1:  # colori
        picks = rnd.sample(COLORS[lang], 5)
        lines = ["Let's learn colors!" if lang == "en" else "Impariamo i colori!"]
        scenes = [{"kind": "title"}]
        for name, hexc in picks:
            if variant["hook"] == "guess_game":
                lines.append(("What color is this? It's " if lang == "en" else "Che colore è? È ") + name + "!")
            else:
                lines.append(("This is " if lang == "en" else "Questo è il ") + name + "!")
            scenes.append({"kind": "color", "color": hexc, "label": name})
        lines.append("Well done!" if lang == "en" else "Bravissimo!")
        scenes.append({"kind": "title"})
        title = ("Learn colors: " if lang == "en" else "Impariamo i colori: ") + ", ".join(p[0] for p in picks[:3])
    elif t == 2:  # forme
        idx = rnd.sample(range(len(SHAPE_KEYS)), 4)
        lines = ["Let's find the shapes!" if lang == "en" else "Scopriamo le forme!"]
        scenes = [{"kind": "title"}]
        for i in idx:
            name = SHAPES[lang][i]
            color = rnd.choice(COLORS[lang])[1]
            art = "A" if lang == "en" else ("Una" if name == "stella" else "Un")
            lines.append(f"{art} {name}!")
            scenes.append({"kind": "shape", "shape": SHAPE_KEYS[i], "color": color, "label": name})
        lines.append("You know your shapes!" if lang == "en" else "Ora conosci le forme!")
        scenes.append({"kind": "title"})
        title = ("Shapes for kids: " if lang == "en" else "Forme per bambini: ") + ", ".join(SHAPES[lang][i] for i in idx[:3])
    elif t == 4:  # lettere
        start = rnd.randrange(0, 20)
        letters = [chr(65 + start + i) for i in range(5)]
        lines = ["Let's learn letters!" if lang == "en" else "Impariamo le lettere!"]
        scenes = [{"kind": "title"}]
        for L in letters:
            lines.append((f"This is the letter {L}!" if lang == "en" else f"Questa è la lettera {L}!"))
            scenes.append({"kind": "letter", "letter": L, "color": rnd.choice(COLORS[lang])[1]})
        lines.append("Great job!" if lang == "en" else "Bravissimo!")
        scenes.append({"kind": "title"})
        title = ("Letters " if lang == "en" else "Lettere ") + f"{letters[0]} - {letters[-1]}"
    else:  # animali (AI)
        sysk = ("You write gentle educational lines for toddlers (age 2-5). Only simple, true, well-known facts. "
                "No scary content, no calls to action, no links, no brands or characters.")
        user = (f"Language: {LANG_NAME[lang]}. Pick one common animal not in: {', '.join(past_titles[-15:])}. "
                "Return JSON: {\"animal\": str, \"title\": str (max 50 chars), \"lines\": [6 lines, max 9 words each], "
                "\"facts_confidence\": number 0-1}")
        data = llm.ask_json(sysk, user, temperature=0.7)
        if not data:
            return None
        data["scenes"] = [{"kind": "animal", "label": data.get("animal", "")} for _ in data["lines"]]
        data["description"] = ""
        data["tags"] = []
        return data
    return {"title": title, "lines": lines, "scenes": scenes, "description": "", "tags": [],
            "facts_confidence": 1.0}


def kids_description(lang):
    return ("A gentle learning short for little ones: colors, numbers, shapes and letters."
            if lang == "en" else "Un breve video educativo per i più piccoli: colori, numeri, forme e lettere.")


def new_content_id(method_key, lang, variant_code):
    return f"{today():%Y%m%d}-{method_key[0]}-{lang}-{short_hash(method_key, lang, variant_code, random.random())}"


def landing_slug(lang, title):
    return f"{lang}/{slugify(title, 50)}"
