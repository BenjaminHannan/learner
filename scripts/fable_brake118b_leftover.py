#!/usr/bin/env python3
"""Exp 118b — LEFTOVER BRAKE with the TRAINING-derived allow-list (doc 118b).

THE ONE CHANGE vs exp 118 (design doc 118, scripts/fable_brake118_leftover.py):
the CAL-tuned V2 framing list (11 words) is replaced by TRAIN_FRAMING_V2
(2618 words, sha256 60a4450e…f3743ad8cb), derived from the exp-47 TRAINING
pool — the sentences the ears were trained on, regenerated with the exp-47
data builder (never the sealed test panels). Rule: a word is allowed if it
appears OUTSIDE the gold subject/value spans in >= K=50 training sentences
and inside a gold VALUE span in < J=1% of the sentences containing it.
K,J fixed on CAL only (fable_brake118b_tune.py); "aside" is NOT in the list.

Everything else is EXACTLY as in 118 by code reuse: V1
(fable_brake118_leftover.FUNCTION_WORDS_V1), the relation cue-word rule
(_cue_words_for_rel), and the blocking/downgrade semantics below.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_brake118_leftover as B118  # noqa: E402 (V1 + cues + logic, read-only)

REPO = Path(__file__).resolve().parent.parent
WORDLIST = REPO / "artifacts" / "fable-brake118b-20260922" / "fable_brake118b_wordlist.txt"
WORDLIST_SHA256 = "60a4450ef450f364d99f07c180a5dec71f2165388da1a8413e829f3743ad8cb8"
K_FIXED, J_FIXED = 50, 0.01


def _load_train_list() -> frozenset:
    words = frozenset(
        w.strip() for w in WORDLIST.read_text(encoding="utf-8").splitlines()
        if w.strip()
    )
    return words


TRAIN_FRAMING_V2 = _load_train_list()
assert len(TRAIN_FRAMING_V2) == 2618, len(TRAIN_FRAMING_V2)
assert "aside" not in TRAIN_FRAMING_V2, "aside entered the allow-list"

ALLOW_WORDS = B118.FUNCTION_WORDS_V1 | TRAIN_FRAMING_V2

WRITE_ACTS = B118.WRITE_ACTS


def leftover_blocks(text, frame, chspans, allow=None):
    """Same semantics as exp 118; `allow` overrides the allow-list (tuning)."""
    if allow is None:
        allow = ALLOW_WORDS
    real = B118.ALLOW_WORDS
    B118.ALLOW_WORDS = allow
    try:
        return B118.leftover_blocks(text, frame, chspans)
    finally:
        B118.ALLOW_WORDS = real
