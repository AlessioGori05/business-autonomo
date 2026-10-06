"""Accesso gratuito a modelli di linguaggio.

Ordine di tentativo:
 1. GitHub Models (gratis dentro GitHub Actions con il token automatico GITHUB_TOKEN)
 2. Google Gemini free tier (se esiste il segreto GEMINI_API_KEY)
Se nessuno risponde, restituisce None e il chiamante salta quel contenuto
(meglio non pubblicare che pubblicare contenuti scadenti).
"""
from __future__ import annotations

import json
import os
import re
import time

import requests

from .util import log, settings

GH_ENDPOINTS = [
    # (url, prefisso del nome modello da togliere o no)
    ("https://models.github.ai/inference/chat/completions", False),
    ("https://models.inference.ai.azure.com/chat/completions", True),   # endpoint storico, nomi senza "openai/"
]
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _extract_json(text: str):
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1)
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
    if start < 0:
        raise ValueError("nessun JSON nella risposta")
    end = max(text.rfind("}"), text.rfind("]"))
    return json.loads(text[start:end + 1])


def _github(system: str, user: str, temperature: float) -> str | None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_MODELS_TOKEN")
    if not token:
        return None
    for url, strip in GH_ENDPOINTS:
        for model in settings()["llm"]["github_models"]:
            name = model.split("/", 1)[1] if strip and "/" in model else model
            for attempt in range(2):
                try:
                    r = requests.post(
                        url,
                        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                                 "Accept": "application/json", "X-GitHub-Api-Version": "2022-11-28"},
                        json={"model": name, "temperature": temperature,
                              "messages": [{"role": "system", "content": system},
                                           {"role": "user", "content": user}]},
                        timeout=120,
                    )
                    if r.status_code == 429:
                        time.sleep(20)
                        continue
                    if not r.ok or not r.text.strip().startswith("{"):
                        log(f"GitHub Models {name} @ {url.split('/')[2]}: HTTP {r.status_code} {r.text[:200]!r}")
                        break
                    return r.json()["choices"][0]["message"]["content"]
                except Exception as e:  # noqa: BLE001
                    log(f"GitHub Models {name} errore: {e}")
                    break
    return None


def _gemini(system: str, user: str, temperature: float) -> str | None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    model = settings()["llm"]["gemini_model"]
    try:
        r = requests.post(
            GEMINI_URL.format(model=model), params={"key": key}, timeout=90,
            json={"systemInstruction": {"parts": [{"text": system}]},
                  "contents": [{"role": "user", "parts": [{"text": user}]}],
                  "generationConfig": {"temperature": temperature}},
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:  # noqa: BLE001
        log(f"Gemini errore: {e}")
        return None


def available() -> bool:
    return bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_MODELS_TOKEN") or os.environ.get("GEMINI_API_KEY"))


def ask_json(system: str, user: str, temperature: float | None = None):
    """Chiede una risposta JSON. Restituisce l'oggetto o None."""
    temperature = settings()["llm"]["temperature"] if temperature is None else temperature
    system = system + "\nRispondi SOLO con JSON valido, senza testo prima o dopo."
    for fn in (_github, _gemini):
        text = fn(system, user, temperature)
        if not text:
            continue
        try:
            return _extract_json(text)
        except Exception as e:  # noqa: BLE001
            log(f"JSON non valido da {fn.__name__}: {e}")
    return None
