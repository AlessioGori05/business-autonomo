"""Voce narrante gratuita con edge-tts (voci neurali Microsoft, nessuna chiave richiesta)."""
from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

from .util import log

VOICES = {
    "en": ["en-US-AriaNeural", "en-US-GuyNeural", "en-US-JennyNeural", "en-GB-RyanNeural"],
    "it": ["it-IT-ElsaNeural", "it-IT-DiegoNeural", "it-IT-IsabellaNeural", "it-IT-GiuseppeMultilingualNeural"],
}
KIDS_VOICES = {"en": ["en-US-AnaNeural", "en-US-JennyNeural"], "it": ["it-IT-IsabellaNeural", "it-IT-ElsaNeural"]}


def pick_voice(lang: str, variant_code: str, kids: bool) -> str:
    pool = (KIDS_VOICES if kids else VOICES)[lang]
    return pool[sum(map(ord, variant_code)) % len(pool)]


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True)
    return float(out.stdout.strip() or 0)


def _silent(path: Path, seconds: float) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                    "-t", f"{seconds:.2f}", "-q:a", "9", str(path)], check=True)


async def _speak(text: str, voice: str, path: Path, rate: str) -> None:
    import edge_tts  # installato su GitHub Actions da requirements.txt
    await edge_tts.Communicate(text, voice, rate=rate).save(str(path))


def synth_lines(lines: list[str], voice: str, workdir: Path, kids: bool = False) -> list[tuple[Path, float]] | None:
    """Crea un mp3 per riga. None se la voce non è disponibile (in produzione il video viene saltato)."""
    workdir.mkdir(parents=True, exist_ok=True)
    allow_silent = os.environ.get("BA_ALLOW_SILENT") == "1"
    rate = "-10%" if kids else "+8%"
    out = []
    for i, line in enumerate(lines):
        p = workdir / f"line_{i:02d}.mp3"
        try:
            asyncio.run(_speak(line, voice, p, rate))
            if duration(p) < 0.3:
                raise RuntimeError("audio vuoto")
        except Exception as e:  # noqa: BLE001
            if not allow_silent:
                log(f"Voce non disponibile ({e}); contenuto saltato")
                return None
            _silent(p, 0.5 + len(line.split()) / 2.6)
        out.append((p, duration(p)))
    return out
