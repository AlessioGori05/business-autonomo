"""Accesso gratuito a modelli di linguaggio.

Ordine di tentativo:
 1. Google Gemini, piano gratuito (segreto GEMINI_API_KEY, chiave gratis da aistudio.google.com)
    Il modello "Flash" più recente disponibile viene scelto da solo.
 2. Groq, piano gratuito (segreto GROQ_API_KEY, facoltativo) come riserva.
Se nessuno risponde, restituisce None e il chiamante salta quel contenuto
(meglio non pubblicare che pubblicare contenuti scadenti).

Nota: GitHub Models è stato chiuso da GitHub il 30/07/2026, per questo non è più usato.
"""
from __future__ import annotations

import json
import os
import re
import time

import requests

from .util import log, settings

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_gemini_models: list[str] | None = None


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


def _version_key(name: str):
    nums = re.findall(r"\d+(?:\.\d+)?", name)
    v = float(nums[0]) if nums else 0
    return (v, "lite" not in name, "preview" not in name and "exp" not in name)


def gemini_models(key: str) -> list[str]:
    """Elenca i modelli Gemini 'flash' testuali disponibili, dal più recente."""
    global _gemini_models
    if _gemini_models is not None:
        return _gemini_models
    preferred = settings()["llm"].get("gemini_models") or []
    found = []
    try:
        r = requests.get(f"{GEMINI_BASE}/models", params={"key": key, "pageSize": 200}, timeout=30)
        r.raise_for_status()
        for m in r.json().get("models", []):
            name = m["name"].split("/", 1)[1]
            if ("generateContent" in m.get("supportedGenerationMethods", []) and "flash" in name
                    and not re.search(r"image|tts|audio|live|vision|embedding|thinking-exp|native", name)):
                found.append(name)
    except Exception as e:  # noqa: BLE001
        log(f"Elenco modelli Gemini non disponibile: {e}")
    found.sort(key=_version_key, reverse=True)
    _gemini_models = [m for m in preferred if m in found or not found] + [m for m in found if m not in preferred]
    if not _gemini_models:
        _gemini_models = ["gemini-2.5-flash", "gemini-2.0-flash"]
    log(f"Modelli Gemini in uso: {_gemini_models[:4]}")
    return _gemini_models


def _gemini(system: str, user: str, temperature: float) -> str | None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    for model in gemini_models(key)[:4]:
        for attempt in range(3):
            try:
                r = requests.post(
                    f"{GEMINI_BASE}/models/{model}:generateContent", params={"key": key}, timeout=120,
                    json={"systemInstruction": {"parts": [{"text": system}]},
                          "contents": [{"role": "user", "parts": [{"text": user}]}],
                          "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"}},
                )
                if r.status_code in (429, 503):
                    time.sleep(15 * (attempt + 1))
                    continue
                if not r.ok:
                    log(f"Gemini {model}: HTTP {r.status_code} {r.text[:200]!r}")
                    break
                parts = r.json()["candidates"][0]["content"]["parts"]
                time.sleep(4)  # rispetta il limite gratuito di richieste al minuto
                return "".join(p.get("text", "") for p in parts if not p.get("thought"))
            except Exception as e:  # noqa: BLE001
                log(f"Gemini {model} errore: {e}")
                break
    return None


def _groq(system: str, user: str, temperature: float) -> str | None:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    for model in settings()["llm"].get("groq_models", ["llama-3.3-70b-versatile"]):
        try:
            r = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {key}"}, timeout=120,
                              json={"model": model, "temperature": temperature,
                                    "response_format": {"type": "json_object"},
                                    "messages": [{"role": "system", "content": system},
                                                 {"role": "user", "content": user}]})
            if not r.ok:
                log(f"Groq {model}: HTTP {r.status_code} {r.text[:200]!r}")
                continue
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            log(f"Groq {model} errore: {e}")
    return None


def available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY"))


def ask_json(system: str, user: str, temperature: float | None = None):
    """Chiede una risposta JSON. Restituisce l'oggetto o None."""
    temperature = settings()["llm"]["temperature"] if temperature is None else temperature
    system = system + "\nRispondi SOLO con JSON valido, senza testo prima o dopo."
    for fn in (_gemini, _groq):
        text = fn(system, user, temperature)
        if not text:
            continue
        try:
            return _extract_json(text)
        except Exception as e:  # noqa: BLE001
            log(f"JSON non valido da {fn.__name__}: {e}")
    return None
