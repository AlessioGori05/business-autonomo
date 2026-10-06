"""Raccolta KPI da YouTube per tutti i video pubblicati."""
from __future__ import annotations

import datetime as dt

from .util import METRICS, channel_credentials, ledger, log, read_json, save_ledger, settings, today, write_json
from .youtube import YouTube


def collect() -> None:
    cfg = settings()
    items = ledger()
    hist = read_json(METRICS, {})
    for ck, ch in cfg["channels"].items():
        creds = channel_credentials(ch)
        mine = [i for i in items if i.get("channel") == ck and i.get("video_id")]
        if not creds or not mine:
            continue
        yt = YouTube(creds)
        ids = [i["video_id"] for i in mine]
        try:
            st = yt.stats(ids)
            first = min(dt.date.fromisoformat(i["date"]) for i in mine)
            an = yt.analytics(ids, first, today())
        except Exception as e:  # noqa: BLE001
            log(f"Metriche {ck} non disponibili: {e}")
            continue
        for i in mine:
            vid = i["video_id"]
            m = {**st.get(vid, {}), **an.get(vid, {})}
            if not m:
                continue
            i["m"] = m
            h = hist.setdefault(vid, {})
            h[today().isoformat()] = {"views": m.get("views", 0), "likes": m.get("likes", 0)}
            if len(h) > 60:
                for d in sorted(h)[:-60]:
                    del h[d]
            if m.get("privacy") == "private" and i.get("status") == "published":
                i["status"] = "private_locked"
        log(f"Metriche aggiornate per {len(mine)} video su {ck}")
    save_ledger(items)
    write_json(METRICS, hist)


def views_delta(video_id: str, days: int = 1) -> int:
    h = read_json(METRICS, {}).get(video_id, {})
    if not h:
        return 0
    dates = sorted(h)
    last = h[dates[-1]]["views"]
    ref_day = (today() - dt.timedelta(days=days)).isoformat()
    prev = [d for d in dates if d <= ref_day]
    return last - (h[prev[-1]]["views"] if prev else 0)
