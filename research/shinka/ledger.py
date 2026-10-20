"""Whole-trial API spend ledger (research/shinka/CARD.md section 5).

Every paid call in the trial is appended to results/TRIAL_LEDGER.jsonl:
the smoke tests, the evolve run and the novelty judge. `total()` is the
trial-wide spend that the $4.50 stop checks. The file is read once per process,
and after that the total is kept in memory. Run the trial's tools one at a time,
not concurrently, so that each process's starting total is current.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

PATH = Path(__file__).resolve().parent / "results" / "TRIAL_LEDGER.jsonl"
HARD_STOP_USD = 4.50

_lock = threading.Lock()
_total: float | None = None


def total() -> float:
    global _total
    with _lock:
        if _total is None:
            _total = 0.0
            if PATH.exists():
                for line in PATH.read_text().splitlines():
                    if line.strip():
                        _total += json.loads(line)["usd"]
        return _total


def record(model: str, tag: str, input_tokens: int, output_tokens: int, usd: float, **extra) -> float:
    """Append one call and return the new trial total."""
    global _total
    total()
    with _lock:
        PATH.parent.mkdir(parents=True, exist_ok=True)
        with PATH.open("a") as f:
            f.write(json.dumps({"t": time.time(), "model": model, "tag": tag,
                                "input_tokens": input_tokens, "output_tokens": output_tokens,
                                "usd": usd, **extra}) + "\n")
        _total += usd
        return _total


def spent_with_tag(tag: str) -> float:
    """Dollars recorded under one tag (re-read from the file; used once per run start)."""
    if not PATH.exists():
        return 0.0
    return sum(json.loads(line)["usd"] for line in PATH.read_text().splitlines()
               if line.strip() and json.loads(line).get("tag") == tag)


def remaining() -> float:
    return HARD_STOP_USD - total()
