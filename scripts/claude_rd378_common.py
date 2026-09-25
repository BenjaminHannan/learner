#!/usr/bin/env python3
"""rd-378 note writer: shared prompt. One call per non-assistant turn, with up to 6 earlier turns."""
from __future__ import annotations

import json

NSYS = ("Write memory notes: plain sentences worth remembering from the latest message. Use names, not pronouns; "
        "plans stay plans; nothing guessed. Output one JSON object.")
END = "\n<END>"
HIST = 6


def speaker_name(kind: str, speaker: str) -> str:
    if kind == "chat":
        return "User" if speaker == "user" else "Assistant"
    return speaker


def build_nprompt(kind: str, date: str, earlier: list, latest: dict) -> str:
    """earlier = [{"speaker","text"}, ...] oldest first (the last HIST are used); latest = {"speaker","text"}."""
    lines = [f"{speaker_name(kind, t['speaker'])}: {t['text'].strip()}" for t in earlier[-HIST:]]
    return (f"{NSYS}\nDate: {date or '(unknown)'}\nEarlier:\n" + ("\n".join(lines) if lines else "(none)") +
            f"\nLatest ({speaker_name(kind, latest['speaker'])}): {latest['text'].strip()}\nNotes: ")


def notes_text(notes: list) -> str:
    out = [{"text": n["text"], "cites": list(n.get("cites") or [0]), "when": n.get("when")} for n in notes]
    return json.dumps({"notes": out}, ensure_ascii=False, separators=(", ", ": ")) + END


def parse_notes(text: str):
    t = text.split("<END>")[0].strip()
    try:
        obj = json.loads(t)
    except Exception:
        return None
    if not isinstance(obj, dict) or not isinstance(obj.get("notes"), list):
        return None
    return [n for n in obj["notes"] if isinstance(n, dict) and isinstance(n.get("text"), str)]
