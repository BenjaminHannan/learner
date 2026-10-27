#!/usr/bin/env python3
"""rd-371b sentence checker: shared prompt ("does the conversation state this sentence? yes/no").

The source is the same window the rd-378 note writer saw: up to 6 earlier turns and the latest turn.
"""
from __future__ import annotations

from claude_rd378_common import HIST, speaker_name

SSYS = ("Does the conversation state everything in this sentence (no guess, no wrong person, time or detail)? "
        "Answer yes or no.")


def build_sprompt(kind: str, date: str, earlier: list, latest: dict, sentence: str) -> str:
    lines = [f"{speaker_name(kind, t['speaker'])}: {t['text'].strip()}" for t in earlier[-HIST:]]
    return (f"{SSYS}\nDate: {date or '(unknown)'}\nEarlier:\n" + ("\n".join(lines) if lines else "(none)") +
            f"\nLatest ({speaker_name(kind, latest['speaker'])}): {latest['text'].strip()}\n"
            f"Sentence: {sentence.strip()}\nAnswer: ")


def windows(dialog: dict):
    """(t, earlier, latest) for every turn the note writer reads (chat: non-assistant turns only)."""
    turns = dialog["turns"]
    for k, t in enumerate(turns):
        if dialog["kind"] == "chat" and t["speaker"] == "assistant":
            continue
        yield int(t["t"]), turns[:k], t
