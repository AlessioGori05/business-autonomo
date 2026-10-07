"""Punto di ingresso. Uso:
    python -m src.run daily      # produce e pubblica i contenuti del giorno
    python -m src.run evening    # raccoglie KPI, valuta varianti, report serale
    python -m src.run weekly     # riallocazione settimanale + report dettagliato
    python -m src.run approve --issue 12 --text "/approva 1,3"
    python -m src.run demo       # prova completa offline senza account
"""
from __future__ import annotations

import argparse
import os
import random
import re
import shutil
import traceback

from PIL import Image

from . import decide, generate as G, github_issues, llm, metrics, pod, qc, render, report, site, tts
from .leadmagnet import ensure_guide
from .util import (summary, DATA, OUT, ROOT, channel_credentials, iso_week, ledger, log, methods, read_json,
                   save_ledger, settings, site_base_url, today, write_json)
from .youtube import YouTube

POD_STATE = DATA / "pod.json"
DAYLOG = report.DAYLOG


class QuotaExceeded(Exception):
    pass


def _daylog_add(key, n=1, warning=None):
    d = read_json(DAYLOG, {})
    day = d.setdefault(today().isoformat(), {})
    if key:
        day[key] = day.get(key, 0) + n
    if warning and warning not in day.setdefault("warnings", []):
        day["warnings"].append(warning)
    for old in sorted(d)[:-90]:
        del d[old]
    write_json(DAYLOG, d)


def _run_url():
    repo, rid = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_RUN_ID")
    return f"https://github.com/{repo}/actions/runs/{rid}" if repo and rid else "(locale)"


# --------------------------------------------------------------- POD settimanale
def pod_designs(lang: str) -> list[dict]:
    state = read_json(POD_STATE, {})
    wk = iso_week(today())
    if wk in state and lang in state[wk]:
        return state[wk][lang]
    m = methods().get("D_pod")
    if not m:
        return []
    past = [d["slogan"] for w in state.values() for l in w.values() for d in l]
    data = G.gen_pod_designs(lang, m["topics"][lang], m.get("designs_per_week", 6), past)
    if not data:
        return []
    clean = [d for d in data if d.get("slogan") and not qc.check(
        {"title": d["slogan"], "lines": [f"x{i}" for i in range(5)], "facts_confidence": 1}, past)]
    rows = pod.build_week(clean, lang)
    state.setdefault(wk, {})[lang] = rows
    write_json(POD_STATE, state)
    if rows:
        lst = "\n".join(f"- **{r['slogan']}** — {r.get('listing_title', '')}  \n  tag: {', '.join(r.get('tags', []))}" for r in rows)
        github_issues.create(
            f"🎨 Nuovi design POD {wk} ({lang.upper()})",
            f"Pronti {len(rows)} design (PNG 4500x5400 trasparenti) + `listing.csv` con titoli, tag e descrizioni.\n\n"
            f"**Scaricali qui** (sezione *Artifacts* in fondo alla pagina, restano 14 giorni): {_run_url()}\n\n"
            f"Caricali sul tuo negozio POD gratuito (Redbubble/Spreadshirt/Teepublic), ~2 minuti a design, poi chiudi questa issue.\n\n{lst}",
            ["pod"])
    return rows


# --------------------------------------------------------------- produzione singolo contenuto
def produce(alloc, ck, mk, yt, pending):
    cfg = settings()
    ch = cfg["channels"][ck]
    lang, kids = ch["lang"], ch.get("made_for_kids", False)
    m = methods()[mk]
    st = alloc["methods"][mk][lang]
    variant = G.pick_variant(st["variants"], decide.variant_usage(ck, mk))
    if not variant:
        return
    items = ledger()
    past_titles = [i["title"] for i in items if i["lang"] == lang]
    recent_topics = [i["topic"] for i in items if i["method"] == mk and i["lang"] == lang]
    brand = cfg["site"][f"brand_name_{lang}"]
    base = site_base_url(cfg)
    extra, pod_imgs = {}, None

    data, problems = None, []
    for _attempt in range(3):
        topic = G.pick_topic(m, lang, recent_topics)
        if mk == "A_viral":
            data = G.gen_viral(lang, topic, variant, past_titles)
        elif mk == "B_affiliate":
            data = G.gen_affiliate(lang, topic, variant, past_titles)
            if data:
                extra = {"products": data.get("products", [])[:3], "page_intro": data.get("page_intro", "")}
        elif mk == "C_leadmagnet":
            guide = ensure_guide(lang, topic, brand, G.gen_guide)
            if guide:
                data = G.gen_leadmagnet_short(lang, topic, variant, past_titles, guide["title"])
                extra = {"guide": guide["slug"]}
        elif mk == "D_pod":
            designs = pod_designs(lang)
            if len(designs) >= 2:
                chosen = random.sample(designs, min(3, len(designs)))
                data = G.gen_pod_short(lang, variant, chosen, past_titles)
                pod_imgs = [Image.open(ROOT / d["preview"]).convert("RGBA") for d in chosen]
                topic = ", ".join(d["slogan"] for d in chosen)
        elif mk == "E_kids":
            idx = m["topics"][lang].index(topic)
            data = G.gen_kids(lang, idx, variant, past_titles)
        if not data:
            continue
        problems = qc.check(data, past_titles, kids=kids)
        # seconda verifica con l'AI per i contenuti con affermazioni (non per conteggi/colori/forme/lettere)
        if not problems and (mk in ("A_viral", "B_affiliate", "C_leadmagnet") or data.get("animal")):
            problems = qc.fact_check({**data, "products": data.get("products")}, llm.ask_json)
        if mk == "D_pod" and pod_imgs and len(data.get("lines", [])) < len(pod_imgs) + 1:
            problems.append("script POD troppo corto per i design")
        if not problems:
            break
        log(f"QC respinto ({mk}/{lang}): {problems}")
        data = None
    if not data:
        _daylog_add("skipped_qc" if problems else "skipped_error",
                    warning=None if problems else ("Nessun modello AI disponibile: contenuti saltati" if not llm.available() else None))
        return

    cid = G.new_content_id(mk, lang, variant["code"])
    item = {"id": cid, "date": today().isoformat(), "channel": ck, "lang": lang, "method": mk,
            "variant": {k: variant[k] for k in ("code", "hook", "theme", "length")}, "topic": topic,
            "title": data["title"].strip(), "lines": data["lines"], "tags": data.get("tags", []), **extra}
    if mk == "B_affiliate":
        item["landing"] = G.landing_slug(lang, item["title"] + "-" + cid[-4:])
    if data.get("scenes"):
        item["scenes"] = data["scenes"]

    # descrizione
    if kids:
        desc = G.kids_description(lang)
    else:
        if mk == "B_affiliate":
            link = f"{base}{item['landing']}.html"
        elif mk == "C_leadmagnet":
            link = f"{base}{lang}/guide-{extra['guide']}.html"
        else:
            link = f"{base}{lang}/index.html"
        disclosure = {"B_affiliate": {"en": "Contains affiliate links.", "it": "Contiene link di affiliazione."}}.get(mk, {}).get(lang, "")
        desc = f"{data.get('description', '')}\n\n{link}\n{disclosure}\n\n#shorts " + " ".join(
            "#" + re.sub(r"\W", "", t) for t in item["tags"][:3])
    item["description"] = desc.strip()

    # voce + video
    work = OUT / "work" / cid
    voice = tts.pick_voice(lang, variant["code"], kids)
    audio = tts.synth_lines(item["lines"], voice, work, kids=kids)
    if not audio:
        _daylog_add("skipped_error", warning="Voce narrante non disponibile (edge-tts): alcuni contenuti saltati")
        return
    vid_path = OUT / "videos" / ck / f"{cid}.mp4"
    vid_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if kids:
            label = cfg["site"].get(f"brand_name_kids_{lang}", brand)
        elif mk == "D_pod":
            label = "NEW DESIGNS" if lang == "en" else "NUOVI DESIGN"
        else:
            label = item["topic"][:38].upper()
        render.render({**item, "variant": variant}, audio, work, vid_path, label=label,
                      kids=kids, pod_images=pod_imgs, bg_query=item["topic"])
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        _daylog_add("skipped_error")
        return
    finally:
        shutil.rmtree(work, ignore_errors=True)
    _daylog_add("produced")

    # pubblicazione
    if yt is None:
        item["status"] = "preview"
        _daylog_add("preview_only", warning=f"Canale {ck} non collegato: i video sono solo in anteprima (scaricabili da Actions)")
    else:
        need_ok = ch.get("require_approval", False)
        try:
            title = item["title"] if len(item["title"]) <= 90 else item["title"][:87] + "..."
            item["video_id"] = yt.upload(vid_path, title, item["description"], item["tags"], lang, kids,
                                         privacy="private" if need_ok else "public")
            item["status"] = "pending_approval" if need_ok else "published"
            _daylog_add("pending_approval" if need_ok else "published")
            if need_ok:
                pending.append(item)
        except Exception as e:  # noqa: BLE001
            msg = str(getattr(e, "response", None) and e.response.text or e)
            item["status"] = "upload_failed"
            if "quota" in msg.lower() or "uploadLimitExceeded" in msg:
                _daylog_add("skipped_error", warning=f"Quota YouTube esaurita su {ck}: riprendo domani")
                raise QuotaExceeded() from e
            _daylog_add("skipped_error", warning=f"Errore caricamento su {ck}: {msg[:160]}")
    items = ledger()
    items.append(item)
    save_ledger(items)


def cmd_daily():
    cfg = settings()
    alloc = decide.load_alloc()
    if not llm.available():
        _daylog_add(None, warning="Nessun modello AI configurato: manca il segreto GEMINI_API_KEY (chiave gratuita da aistudio.google.com)")
    for ck, ch in cfg["channels"].items():
        plan = decide.daily_plan(alloc, ck)
        if not plan:
            continue
        creds = None if cfg.get("dry_run") else channel_credentials(ch)
        yt = YouTube(creds) if creds else None
        log(f"Canale {ck}: piano {plan} ({'pubblica' if yt else 'anteprima'})")
        pending = []
        for mk in plan:
            try:
                produce(alloc, ck, mk, yt, pending)
            except QuotaExceeded:
                break
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                _daylog_add("skipped_error")
        if pending:
            ask_approval(ck, pending)
    decide.save_alloc(alloc)
    site.build()


def ask_approval(ck, pending):
    lines = []
    for n, it in enumerate(pending, 1):
        script = " / ".join(it["lines"])
        lines.append(f"**{n}. {it['title']}** — https://youtu.be/{it['video_id']} (privato, visibile solo a te)\n> {script}")
    body = ("Ho preparato questi video per bambini. Sono caricati come **privati**.\n\n" + "\n\n".join(lines) +
            "\n\n---\nRispondi con un commento:\n- `/approva` per pubblicarli tutti\n- `/approva 1,3` per pubblicarne solo alcuni\n"
            "- `/rifiuta` per scartarli tutti\n\nControlla che siano adatti ai bambini prima di approvare.")
    num = github_issues.create(f"👶 Approva video bambini {today():%d/%m} ({ck})", body, ["approvazione-kids"])
    items = ledger()
    ids = {p["id"] for p in pending}
    for i in items:
        if i["id"] in ids:
            i["approval_issue"] = num
            i["approval_index"] = [p["id"] for p in pending].index(i["id"]) + 1
    save_ledger(items)


def cmd_approve(issue: int, text: str):
    cfg = settings()
    text = text.strip().lower()
    items = ledger()
    mine = [i for i in items if i.get("approval_issue") == issue and i.get("status") == "pending_approval"]
    if not mine:
        github_issues.comment(issue, "Nessun video in attesa per questa richiesta.")
        return
    sel = None
    mnum = re.search(r"/approva\s+([\d,\s]+)", text)
    if mnum:
        sel = {int(x) for x in re.findall(r"\d+", mnum.group(1))}
    approve = text.startswith("/approva")
    done = []
    for i in mine:
        ch = cfg["channels"][i["channel"]]
        creds = channel_credentials(ch)
        ok = approve and (sel is None or i.get("approval_index") in sel)
        try:
            if ok and creds:
                YouTube(creds).set_privacy(i["video_id"], "public", True)
                i["status"] = "published"
                done.append(f"✅ pubblicato: {i['title']}")
            elif ok:
                done.append(f"⚠️ canale {i['channel']} non collegato, impossibile pubblicare: {i['title']}")
            else:
                i["status"] = "rejected"
                done.append(f"🗑️ scartato (resta privato): {i['title']}")
        except Exception as e:  # noqa: BLE001
            done.append(f"⚠️ errore su {i['title']}: {e}")
    save_ledger(items)
    github_issues.comment(issue, "\n".join(done))
    github_issues.close(issue)


def cmd_evening():
    metrics.collect()
    alloc = decide.load_alloc()
    actions = decide.evaluate_variants(alloc)
    decide.save_alloc(alloc)
    locked = [i for i in ledger() if i.get("status") == "private_locked"]
    if locked:
        _daylog_add(None, warning=f"{len(locked)} video bloccati come privati da YouTube: il progetto Google API va verificato (vedi SETUP.md, passo 'Audit')")
    report.daily(alloc, actions)
    site.build()


def cmd_weekly():
    metrics.collect()
    alloc = decide.load_alloc()
    actions = decide.evaluate_variants(alloc) + decide.reallocate(alloc)
    decide.save_alloc(alloc)
    report.weekly(alloc, actions)


def cmd_verify():
    """Controlla i collegamenti YouTube senza pubblicare nulla."""
    import requests
    cfg = settings()
    for ck, ch in cfg["channels"].items():
        creds = channel_credentials(ch)
        if not creds:
            summary(f"{ck}: non collegato")
            continue
        try:
            yt = YouTube(creds)
            r = requests.get("https://www.googleapis.com/youtube/v3/channels", params={"part": "snippet,statistics", "mine": "true"},
                             headers={"Authorization": f"Bearer {yt.token()}"}, timeout=30)
            r.raise_for_status()
            items = r.json().get("items", [])
            names = [f"{i['snippet']['title']} ({i['statistics'].get('subscriberCount', '?')} iscritti)" for i in items]
            summary(f"{ck}: OK -> {names}")
        except Exception as e:  # noqa: BLE001
            summary(f"{ck}: ERRORE {str(getattr(getattr(e, 'response', None), 'text', e))[:300]}")


def cmd_demo():
    """Prova completa senza account: testi d'esempio, voce muta, nessun caricamento."""
    from . import demo_data
    os.environ["BA_ALLOW_SILENT"] = "1"
    llm.ask_json = demo_data.fake_ask_json
    llm.available = lambda: True
    G.llm.ask_json = demo_data.fake_ask_json
    cmd_daily()
    cmd_evening()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["daily", "evening", "weekly", "approve", "demo", "site", "verify"])
    ap.add_argument("--issue", type=int)
    ap.add_argument("--text", default="")
    a = ap.parse_args()
    {"daily": cmd_daily, "verify": cmd_verify, "evening": cmd_evening, "weekly": cmd_weekly, "demo": cmd_demo, "site": site.build,
     "approve": lambda: cmd_approve(a.issue, a.text)}[a.cmd]()


if __name__ == "__main__":
    main()
