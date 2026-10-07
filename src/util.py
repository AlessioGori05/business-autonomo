"""Funzioni comuni: percorsi, configurazione, registro (ledger), log."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"
OUT = ROOT / "out"            # file temporanei (video renderizzati), non salvati nel repo
ASSETS = ROOT / "assets"

for _p in (DATA, REPORTS / "daily", REPORTS / "weekly", DOCS, OUT):
    _p.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    print(f"[{dt.datetime.utcnow():%H:%M:%S}] {msg}", flush=True)


def summary(msg: str) -> None:
    """Scrive una riga nel riepilogo visibile nella pagina dell'esecuzione su GitHub Actions."""
    log(msg)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"- {msg}\n")


def today() -> dt.date:
    forced = os.environ.get("BA_TODAY")
    return dt.date.fromisoformat(forced) if forced else dt.date.today()


def load_yaml(name: str) -> dict:
    with open(CONFIG / name, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def settings() -> dict:
    return load_yaml("settings.yaml")


def methods(enabled_only: bool = True) -> dict:
    m = load_yaml("methods.yaml")
    return {k: v for k, v in m.items() if v.get("enabled") or not enabled_only}


def read_json(path: Path, default):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
    tmp.replace(path)


# ------------------------------------------------------------------ ledger
LEDGER = DATA / "ledger.json"          # ogni contenuto prodotto
ALLOC = DATA / "allocation.json"       # quote per metodo/canale + stato varianti
METRICS = DATA / "metrics.json"        # storico metriche per video


def ledger() -> list:
    return read_json(LEDGER, [])


def save_ledger(items: list) -> None:
    write_json(LEDGER, items)


def slugify(text: str, maxlen: int = 60) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:maxlen].strip("-") or "item"


def short_hash(*parts) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8]


def channel_credentials(channel: dict) -> dict | None:
    p = channel["secret_prefix"]
    cid, sec, tok = (os.environ.get(f"{p}_{k}") for k in ("CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN"))
    if cid and sec and tok:
        return {"client_id": cid, "client_secret": sec, "refresh_token": tok}
    return None


def site_base_url(cfg: dict) -> str:
    url = (cfg.get("site") or {}).get("base_url") or ""
    if url:
        return url.rstrip("/") + "/"
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner.lower()}.github.io/{name}/"
    return "https://example.github.io/business-autonomo/"


def iso_week(d: dt.date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"
