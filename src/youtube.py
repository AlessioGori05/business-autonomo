"""YouTube Data API v3 + YouTube Analytics API, via semplici chiamate HTTP (quota gratuita)."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import requests

from .util import log

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
API = "https://www.googleapis.com/youtube/v3"
ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"


class YouTube:
    def __init__(self, creds: dict):
        self.creds = creds
        self._token = None

    def token(self) -> str:
        if not self._token:
            r = requests.post(TOKEN_URL, data={**{k: self.creds[k] for k in ("client_id", "client_secret", "refresh_token")},
                                               "grant_type": "refresh_token"}, timeout=30)
            r.raise_for_status()
            self._token = r.json()["access_token"]
        return self._token

    def _h(self, extra=None):
        return {"Authorization": f"Bearer {self.token()}", **(extra or {})}

    def upload(self, path: Path, title: str, description: str, tags: list, lang: str,
               made_for_kids: bool, privacy: str = "public") -> str:
        body = {
            "snippet": {"title": title[:100], "description": description[:4900], "tags": tags[:15],
                        "categoryId": "27" if made_for_kids else "22", "defaultLanguage": lang,
                        "defaultAudioLanguage": lang},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": made_for_kids,
                       "containsSyntheticMedia": True, "embeddable": True},
        }
        size = path.stat().st_size
        r = requests.post(UPLOAD_URL, params={"uploadType": "resumable", "part": "snippet,status"},
                          headers=self._h({"Content-Type": "application/json; charset=UTF-8",
                                           "X-Upload-Content-Type": "video/mp4",
                                           "X-Upload-Content-Length": str(size)}),
                          data=json.dumps(body), timeout=60)
        r.raise_for_status()
        loc = r.headers["Location"]
        with open(path, "rb") as f:
            up = requests.put(loc, headers=self._h({"Content-Type": "video/mp4"}), data=f, timeout=600)
        up.raise_for_status()
        vid = up.json()["id"]
        log(f"Caricato su YouTube: {vid} ({privacy})")
        return vid

    def set_privacy(self, video_id: str, privacy: str, made_for_kids: bool) -> None:
        r = requests.put(f"{API}/videos", params={"part": "status"}, headers=self._h({"Content-Type": "application/json"}),
                         data=json.dumps({"id": video_id, "status": {"privacyStatus": privacy,
                                                                     "selfDeclaredMadeForKids": made_for_kids,
                                                                     "containsSyntheticMedia": True}}), timeout=30)
        r.raise_for_status()

    def stats(self, ids: list[str]) -> dict:
        out = {}
        for i in range(0, len(ids), 50):
            r = requests.get(f"{API}/videos", params={"part": "statistics,status", "id": ",".join(ids[i:i + 50])},
                             headers=self._h(), timeout=30)
            r.raise_for_status()
            for it in r.json().get("items", []):
                s = it.get("statistics", {})
                out[it["id"]] = {"views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                                 "comments": int(s.get("commentCount", 0)),
                                 "privacy": it.get("status", {}).get("privacyStatus"),
                                 "upload_status": it.get("status", {}).get("uploadStatus")}
        return out

    def analytics(self, ids: list[str], since: dt.date, until: dt.date) -> dict:
        """Durata media di visione e % visualizzata per video (può non essere disponibile su canali nuovi)."""
        out = {}
        for i in range(0, len(ids), 200):
            try:
                r = requests.get(ANALYTICS, headers=self._h(), timeout=30, params={
                    "ids": "channel==MINE", "startDate": since.isoformat(), "endDate": until.isoformat(),
                    "metrics": "views,averageViewDuration,averageViewPercentage,subscribersGained",
                    "dimensions": "video", "filters": "video==" + ",".join(ids[i:i + 200]), "maxResults": 200})
                r.raise_for_status()
                for row in r.json().get("rows", []) or []:
                    out[row[0]] = {"a_views": row[1], "avg_view_s": row[2], "avg_view_pct": row[3], "subs": row[4]}
            except Exception as e:  # noqa: BLE001
                log(f"Analytics non disponibili: {e}")
        # ricavi (solo se il canale è nel Programma partner e lo scope è stato concesso)
        try:
            r = requests.get(ANALYTICS, headers=self._h(), timeout=30, params={
                "ids": "channel==MINE", "startDate": since.isoformat(), "endDate": until.isoformat(),
                "metrics": "estimatedRevenue", "dimensions": "video",
                "filters": "video==" + ",".join(ids[:200]), "maxResults": 200})
            if r.ok:
                for row in r.json().get("rows", []) or []:
                    out.setdefault(row[0], {})["revenue"] = row[1]
        except Exception:  # noqa: BLE001
            pass
        return out
