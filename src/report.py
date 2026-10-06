"""Report giornaliero (3 righe + tabella KPI) e settimanale (metriche, test, vincitori, azioni)."""
from __future__ import annotations

import datetime as dt

from . import github_issues
from .decide import agg
from .metrics import views_delta
from .util import DATA, REPORTS, iso_week, ledger, methods, read_json, settings, today

DAYLOG = DATA / "daylog.json"
STATUS_IT = {"active": "attivo", "cut": "ridotto", "stopped": "fermato"}


def _fmt_s(x):
    return f"{x:.1f}s" if x is not None else "n/d"


def kpi_table(alloc: dict, items: list, since: dt.date | None = None) -> str:
    rows = ["| Metodo | Lingua | Quota | Contenuti oggi / tot | Views 24h | Views tot | Views/video | Engagement | Durata media | RPM | Stato |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    names = methods(enabled_only=False)
    for mk, langs in alloc["methods"].items():
        for lang, st in langs.items():
            mine = [i for i in items if i["method"] == mk and i["lang"] == lang]
            pub = [i for i in mine if i.get("video_id")]
            if since:
                pub = [i for i in pub if dt.date.fromisoformat(i["date"]) >= since]
            a = agg(pub)
            today_n = sum(1 for i in mine if i["date"] == today().isoformat())
            d24 = sum(views_delta(i["video_id"]) for i in pub)
            rows.append(f"| {names.get(mk, {}).get('name', mk)} | {lang.upper()} | {st['share']:.0%} | {today_n} / {len(mine)} | "
                        f"{d24} | {a['views']} | {a['vpv']:.0f} | {a['eng']:.2%} | {_fmt_s(a['avg_view_s'])} | "
                        f"{a['rpm']:.2f} € | {STATUS_IT.get(st['status'], st['status'])} |")
    return "\n".join(rows)


def daily(alloc: dict, eval_actions: list[str]) -> str:
    items = ledger()
    log = read_json(DAYLOG, {}).get(today().isoformat(), {})
    made = log.get("produced", 0)
    pub = log.get("published", 0)
    pend = log.get("pending_approval", 0)
    prev = log.get("preview_only", 0)
    skipped = log.get("skipped_qc", 0) + log.get("skipped_error", 0)
    total_24 = sum(views_delta(i["video_id"]) for i in items if i.get("video_id"))
    best = None
    for mk, langs in alloc["methods"].items():
        for lang in langs:
            a = agg([i for i in items if i["method"] == mk and i["lang"] == lang and i.get("video_id")])
            if a["n"] and (best is None or a["vpv"] > best[2]):
                best = (mk, lang, a["vpv"])
    l1 = (f"Oggi prodotti {made} contenuti: {pub} pubblicati, {pend} in attesa della tua approvazione, "
          f"{prev} in anteprima (canale non collegato), {skipped} scartati dal controllo qualità o per errori.")
    l2 = (f"Ultime 24h: {total_24} visualizzazioni totali" +
          (f"; metodo migliore finora {methods(False)[best[0]]['name']} {best[1].upper()} con {best[2]:.0f} views/video." if best else "; ancora nessun dato di visualizzazione."))
    l3 = ("Decisioni: " + "; ".join(eval_actions[:3])) if eval_actions else (
        "Decisioni: nessuna variante ha ancora chiuso la finestra di test (7 giorni o 1.000 views)." if items else
        "Decisioni: in attesa dei primi contenuti.")
    warn = log.get("warnings", [])
    body = (f"## Report {today():%d/%m/%Y}\n\n{l1}\n{l2}\n{l3}\n\n{kpi_table(alloc, items)}\n")
    if warn:
        body += "\n**Da sistemare:**\n" + "\n".join(f"- {w}" for w in sorted(set(warn))) + "\n"
    if eval_actions:
        body += "\n**Tutte le azioni e motivazioni:**\n" + "\n".join(f"- {a}" for a in eval_actions) + "\n"
    (REPORTS / "daily" / f"{today().isoformat()}.md").write_text(body, encoding="utf-8")
    github_issues.post_daily(body)
    return body


def weekly(alloc: dict, actions: list[str]) -> str:
    items = ledger()
    hist = alloc["history"][-1] if alloc["history"] else {"start": today().isoformat()}
    since = dt.date.fromisoformat(hist["start"])
    week_items = [i for i in items if dt.date.fromisoformat(i["date"]) >= since]
    winners, suspended, redesign, testing = [], [], [], 0
    for mk, langs in alloc["methods"].items():
        for lang, st in langs.items():
            for v in st["variants"]:
                tag = f"{mk} {lang.upper()} {v['code']} ({v['hook']} / {v['theme']} / {v['length']})"
                {"winner": winners, "suspended": suspended, "redesign": redesign}.get(v["status"], []).append(tag)
                testing += v["status"] == "testing"
    body = [f"# Report settimanale {iso_week(today())} (ciclo {alloc['cycle'] - 1})\n",
            f"Periodo: {since:%d/%m} - {today():%d/%m}. Contenuti prodotti: {len(week_items)}, "
            f"pubblicati: {sum(1 for i in week_items if i.get('video_id'))}.\n",
            "## Metriche del ciclo\n", kpi_table(alloc, items, since), "\n",
            f"## Test eseguiti\nVarianti in test: {testing}. Vincitrici: {len(winners)}. Sospese: {len(suspended)}. Da riprogettare: {len(redesign)}.\n",
            "## Vincitori\n" + ("\n".join(f"- {w}" for w in winners) or "- nessuno ancora") + "\n",
            "## Azioni eseguite e motivazioni\n" + ("\n".join(f"- {a}" for a in actions) or "- nessuna riallocazione") + "\n",
            "## Quote per il prossimo ciclo\n" + "\n".join(
                f"- {mk} {lang.upper()}: {st['share']:.0%} ({STATUS_IT.get(st['status'], st['status'])})"
                for mk, langs in alloc["methods"].items() for lang, st in langs.items()) + "\n",
            "## Prossimi passi\n- Il sistema continua in automatico con le nuove quote.\n"
            "- Le varianti vincitrici ricevono il doppio dei caricamenti; quelle da riprogettare vengono sostituite.\n"]
    text = "\n".join(body)
    (REPORTS / "weekly" / f"{iso_week(today())}.md").write_text(text, encoding="utf-8")
    github_issues.create(f"📈 Report settimanale {iso_week(today())}", text, ["report-settimanale"])
    return text
