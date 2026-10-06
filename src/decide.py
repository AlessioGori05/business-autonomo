"""Motore decisionale: varianti, quote giornaliere, valutazione KPI, riallocazione settimanale."""
from __future__ import annotations

import datetime as dt
import itertools
import random
import statistics

from .util import ALLOC, read_json, settings, methods, today, write_json, ledger


# ------------------------------------------------------------ stato
def load_alloc() -> dict:
    a = read_json(ALLOC, {"cycle": 1, "cycle_start": today().isoformat(), "methods": {}, "history": []})
    for key, m in methods().items():
        langs = {settings()["channels"][c]["lang"] for c in m.get("channels", [])}
        for lang in langs:
            st = a["methods"].setdefault(key, {}).setdefault(lang, {
                "share": m.get("initial_share", 0.25), "status": "active", "neg_cycles": 0, "tactic": 1,
                "variants": [], "next_variant": 1})
            ensure_variants(key, m, st)
    return a


def save_alloc(a: dict) -> None:
    write_json(ALLOC, a)


def ensure_variants(key: str, m: dict, st: dict) -> None:
    target = settings()["kpi"]["variants_per_method"]
    dims = m.get("variants", {})
    names = list(dims)
    combos = [dict(zip(names, c)) for c in itertools.product(*(dims[n] for n in names))]
    used = {tuple(v[n] for n in names) for v in st["variants"]}
    free = [c for c in combos if tuple(c[n] for n in names) not in used]
    random.shuffle(free)
    active = [v for v in st["variants"] if v["status"] in ("testing", "winner")]
    while len(active) < min(target, len(combos)) and free:
        c = free.pop()
        v = {"code": f"{key[0]}{st['next_variant']}", **c, "status": "testing", "tactic": st["tactic"],
             "created": today().isoformat(), "low_cycles": 0, "evaluated": None}
        st["next_variant"] += 1
        st["variants"].append(v)
        active.append(v)
    if not active and st["variants"]:   # tutte le combinazioni esaurite: ricicla le "da riprogettare"
        for v in st["variants"]:
            if v["status"] == "redesign":
                v["status"], v["low_cycles"] = "testing", 0
                active.append(v)
                if len(active) >= target:
                    break


# ------------------------------------------------------------ quote giornaliere
def daily_plan(alloc: dict, channel_key: str) -> list[str]:
    """Lista ordinata dei metodi da produrre oggi su un canale (uno per slot)."""
    cfg = settings()
    ch = cfg["channels"][channel_key]
    lang, slots = ch["lang"], ch["daily_uploads"]
    cands = {k: alloc["methods"][k][lang] for k, m in methods().items()
             if channel_key in m.get("channels", []) and alloc["methods"].get(k, {}).get(lang, {}).get("status") != "stopped"}
    shares = {k: max(st["share"], 0) for k, st in cands.items()}
    tot = sum(shares.values()) or 1
    shares = {k: s / tot for k, s in shares.items()}
    start = dt.date.fromisoformat(alloc["cycle_start"])
    done = {k: 0 for k in shares}
    for it in ledger():
        if it.get("channel") == channel_key and it["method"] in done and dt.date.fromisoformat(it["date"]) >= start:
            done[it["method"]] += 1
    plan = []
    total = sum(done.values())
    for _ in range(slots):
        total += 1
        k = max(shares, key=lambda k: shares[k] * total - done[k] + random.random() * 1e-3)
        done[k] += 1
        plan.append(k)
    return plan


def variant_usage(channel_key: str, method_key: str) -> dict:
    use = {}
    for it in ledger():
        if it.get("channel") == channel_key and it["method"] == method_key:
            use[it["variant"]["code"]] = use.get(it["variant"]["code"], 0) + 1
    return use


# ------------------------------------------------------------ metriche aggregate
def agg(items: list) -> dict:
    n = len(items)
    views = sum((i.get("m") or {}).get("views", 0) for i in items)
    likes = sum((i.get("m") or {}).get("likes", 0) + (i.get("m") or {}).get("comments", 0) for i in items)
    with_a = [i for i in items if (i.get("m") or {}).get("avg_view_s") is not None]
    wv = sum(i["m"].get("views", 0) for i in with_a) or 0
    avg_s = (sum(i["m"]["avg_view_s"] * i["m"].get("views", 0) for i in with_a) / wv) if wv else None
    avg_pct = (sum(i["m"]["avg_view_pct"] * i["m"].get("views", 0) for i in with_a) / wv) if wv else None
    revenue = sum((i.get("m") or {}).get("revenue", 0) or 0 for i in items)
    return {"n": n, "views": views, "vpv": views / n if n else 0, "eng": likes / views if views else 0,
            "avg_view_s": avg_s, "avg_view_pct": avg_pct, "revenue": revenue,
            "rpm": revenue / views * 1000 if views else 0}


def score(a: dict) -> float:
    pct = (a["avg_view_pct"] or 50) / 100
    return a["vpv"] * pct * (1 + 10 * a["eng"])


# ------------------------------------------------------------ valutazione varianti (ogni giorno)
def evaluate_variants(alloc: dict) -> list[str]:
    k = settings()["kpi"]
    actions = []
    items = [i for i in ledger() if i.get("video_id")]
    for mkey, langs in alloc["methods"].items():
        for lang, st in langs.items():
            mine = [i for i in items if i["method"] == mkey and i["lang"] == lang]
            per_v = {}
            for i in mine:
                per_v.setdefault(i["variant"]["code"], []).append(i)
            scores = {c: score(agg(v)) for c, v in per_v.items()}
            med = statistics.median(scores.values()) if scores else 0
            for v in st["variants"]:
                vids = per_v.get(v["code"], [])
                if not vids or v["status"] not in ("testing", "winner"):
                    continue
                first = min(dt.date.fromisoformat(i["date"]) for i in vids)
                since = dt.date.fromisoformat(v["evaluated"]) if v.get("evaluated") else first
                a = agg(vids)
                window = (today() - since).days >= k["test_window_days"] or a["views"] >= k["test_window_views"] * (1 + (1 if v.get("evaluated") else 0))
                if not window:
                    continue
                v["evaluated"] = today().isoformat()
                s = scores.get(v["code"], 0)
                low = a["eng"] < k["suspend_ctr"] and (a["avg_view_s"] is not None and a["avg_view_s"] < k["suspend_avg_view_seconds"])
                old = v["status"]
                if low:
                    v["low_cycles"] += 1
                    if v["low_cycles"] >= k["suspend_cycles"]:
                        v["status"] = "suspended"
                else:
                    v["low_cycles"] = 0
                    if s >= med * k["winner_factor"] and len(vids) >= 2 and med > 0:
                        v["status"] = "winner"
                    elif s < med * 0.6:
                        v["status"] = "redesign"
                    elif v["status"] == "winner" and s < med:
                        v["status"] = "testing"
                if v["status"] != old or low:
                    actions.append(f"{mkey}/{lang} variante {v['code']} ({v['hook']}, {v['theme']}, {v['length']}): "
                                   f"{old} -> {v['status']} | views/video {a['vpv']:.0f}, engagement {a['eng']:.2%}, "
                                   f"durata media {round(a['avg_view_s'], 1) if a['avg_view_s'] is not None else 'n/d'}s")
            ensure_variants(mkey, methods().get(mkey, {}), st) if mkey in methods() else None
    return actions


# ------------------------------------------------------------ riallocazione settimanale
def reallocate(alloc: dict) -> list[str]:
    k = settings()["kpi"]
    actions = []
    start = dt.date.fromisoformat(alloc["cycle_start"])
    cycle_items = [i for i in ledger() if i.get("video_id") and dt.date.fromisoformat(i["date"]) >= start]
    for lang in ("en", "it"):
        for kids in (False, True):
            group = {mk: st[lang] for mk, st in alloc["methods"].items() if lang in st
                     and (mk == "E_kids") == kids and st[lang]["status"] != "stopped"}
            if not group:
                continue
            per = {mk: agg([i for i in cycle_items if i["method"] == mk and i["lang"] == lang]) for mk in group}
            tot_n = sum(a["n"] for a in per.values())
            avg_vpv = (sum(a["views"] for a in per.values()) / tot_n) if tot_n else 0
            if avg_vpv < 20:
                actions.append(f"{lang}{' kids' if kids else ''}: dati insufficienti (media {avg_vpv:.0f} views/video), quote invariate")
                continue
            for mk, st in group.items():
                a = per[mk]
                if a["n"] == 0:
                    continue
                ratio = a["vpv"] / avg_vpv
                conv = a["eng"]
                if ratio < k["negative_ratio"]:
                    st["neg_cycles"] += 1
                    if st["status"] == "cut":
                        st["status"], st["share"] = "stopped", 0
                        actions.append(f"STOP {mk}/{lang}: ancora negativo dopo il taglio (resa {ratio:.0%} della media)")
                    elif st["neg_cycles"] >= k["negative_cycles_before_cut"]:
                        st["share"] *= k["cut_factor"]
                        st["status"], st["tactic"] = "cut", st["tactic"] + 1
                        for v in st["variants"]:
                            if v["status"] == "testing":
                                v["status"] = "redesign"
                        actions.append(f"TAGLIO -50% {mk}/{lang}: negativo per {st['neg_cycles']} cicli (resa {ratio:.0%}); nuova tattica #{st['tactic']}, varianti rigenerate")
                    else:
                        actions.append(f"ATTENZIONE {mk}/{lang}: resa {ratio:.0%} della media (ciclo negativo {st['neg_cycles']})")
                else:
                    if st["status"] == "cut":
                        st["status"] = "active"
                    st["neg_cycles"] = 0
                    conv_rate = a.get("conversion")  # disponibile solo se colleghi il tracciamento click
                    if len(group) > 1 and ratio >= 1 and (a["vpv"] >= k["promote_target_views_per_video"] or
                                                          (conv_rate is not None and conv_rate >= k["promote_target_conversion"])):
                        st["share"] *= k["promote_factor"]
                        actions.append(f"PROMOSSO +50% {mk}/{lang}: {a['vpv']:.0f} views/video (target {k['promote_target_views_per_video']}), resa {ratio:.0%} della media")
            act = {mk: st for mk, st in group.items() if st["status"] != "stopped"}
            tot = sum(st["share"] for st in act.values()) or 1
            for st in act.values():
                st["share"] = max(st["share"] / tot, 0.1 if len(act) > 1 else 1.0)
            tot = sum(st["share"] for st in act.values())
            for st in act.values():
                st["share"] = round(st["share"] / tot, 3)
            for mk, st in group.items():
                ensure_variants(mk, methods().get(mk, {}), st) if mk in methods() else None
    alloc["history"].append({"cycle": alloc["cycle"], "start": alloc["cycle_start"], "end": today().isoformat(),
                             "shares": {mk: {l: s["share"] for l, s in st.items()} for mk, st in alloc["methods"].items()},
                             "actions": actions})
    alloc["cycle"] += 1
    alloc["cycle_start"] = today().isoformat()
    return actions
