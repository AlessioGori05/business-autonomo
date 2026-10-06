"""Notifiche tramite GitHub Issues (ricevi un'email da GitHub ad ogni report/richiesta)."""
from __future__ import annotations

import os

import requests

from .util import log

API = "https://api.github.com"


def _ctx():
    repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        return None
    return repo, {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def ensure_label(name: str, color: str = "1d4ed8") -> None:
    c = _ctx()
    if c:
        requests.post(f"{API}/repos/{c[0]}/labels", headers=c[1], json={"name": name, "color": color}, timeout=30)


def find_open(label: str) -> dict | None:
    c = _ctx()
    if not c:
        return None
    r = requests.get(f"{API}/repos/{c[0]}/issues", headers=c[1], params={"labels": label, "state": "open"}, timeout=30)
    items = r.json() if r.ok else []
    return items[0] if items else None


def create(title: str, body: str, labels: list[str]) -> int | None:
    c = _ctx()
    if not c:
        log(f"(issue non creata, siamo fuori da GitHub) {title}")
        return None
    for l in labels:
        ensure_label(l)
    r = requests.post(f"{API}/repos/{c[0]}/issues", headers=c[1], json={"title": title, "body": body[:65000], "labels": labels}, timeout=30)
    if r.ok:
        return r.json()["number"]
    log(f"Errore creazione issue: {r.status_code} {r.text[:200]}")
    return None


def comment(number: int, body: str) -> None:
    c = _ctx()
    if c:
        requests.post(f"{API}/repos/{c[0]}/issues/{number}/comments", headers=c[1], json={"body": body[:65000]}, timeout=30)


def close(number: int) -> None:
    c = _ctx()
    if c:
        requests.patch(f"{API}/repos/{c[0]}/issues/{number}", headers=c[1], json={"state": "closed"}, timeout=30)


def post_daily(body: str) -> None:
    """Un'unica issue 'Report giornalieri' con un commento al giorno."""
    issue = find_open("report-giornaliero")
    if issue:
        comment(issue["number"], body)
    else:
        create("📊 Report giornalieri", body, ["report-giornaliero"])
