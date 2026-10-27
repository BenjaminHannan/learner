#!/usr/bin/env python3
"""Experiment 137c -- hypothetical-openers never write: closed list + match.

THE ONE CHANGE (against loop137b, which strips "Suppose" at
`scripts/fable_loop137b_agent.py:125` inside `_upgrade137b` and re-teaches
the rest as fact): a turn whose FIRST words -- after optional
case-insensitive fillers "ok"/"so"/"and" plus punctuation -- are one of the
closed HYPO137C markers below is a hypothetical. It NEVER writes; the
agent replies exactly HYPO_REPLY. Later questions in the same session
therefore answer only from real saved facts (there is nothing else to
read: the pretend turn stored nothing).

Closed list, fixed before any panel read (brief order):
  suppose | supposing | imagine | pretend | pretend that | let's say |
  lets say | hypothetically | in theory | what if | say that

Matching (all sealed in PASSMARKS.md):
- Case-insensitive everywhere ("SUPPOSE Kim's ..." counts).
- Fillers: whole words ok/so/and only (case-insensitive), each optionally
  followed by punctuation; repeatable ("Ok, so suppose ..."). "Okay" is
  NOT a filler (it is a 137b discourse word, not a 137c filler).
- Marker match is longest-first ("pretend that" beats "pretend") and
  needs a trailing boundary (end of string, whitespace, or punctuation
  , ; : . ! ? ' " ( ) -); "Supposedly ..." and "Imagines ..." do NOT
  match. "let's say" also matches the curly-apostrophe form.
- "say" ALONE is not a marker (only "say that" is), so 137b's
  "Say Tom's ..." teach stays byte-identical. Bare "if" is not a marker
  (only "what if" is), so "If Kim's boss is Lee then ..." stays declined
  exactly as on 137b.
- Names/titles with a marker word LATER in the sentence ("Kim's song is
  Imagine", "Kim's film is What If") never match: only turn-initial
  position counts.

Stdlib only. Mac CPU. Deterministic: no seeds, no sampling, no model.
"""

from __future__ import annotations

import re

# Exact reply for every hypothetical turn. Fixed before any panel read.
HYPO_REPLY = "OK, I'll treat that as pretend, so I won't save it."

# Fillers skipped before the marker (whole words, case-insensitive).
_FILLERS = frozenset(["ok", "so", "and"])

# Markers, longest-first for alternation (all matched case-insensitively).
_MARKERS = [
    "pretend that",
    "let's say",
    "lets say",
    "in theory",
    "what if",
    "say that",
    "supposing",
    "suppose",
    "imagine",
    "pretend",
    "hypothetically",
]

_EDGE_PUNCT = " \t\n\r.,;:!?\"'()[]{}-_\u2013\u2014/"

# Trailing boundary after a marker: end, whitespace, or punctuation --
# but NOT an apostrophe: "What If's boss ..." / "Suppose's boss ..." are
# possessive names (titles), not hypothetical openers.
_BOUND = " \t\n\r.,;:!?\"()[]{}-_\u2013\u2014/"


def _norm_apos(text: str) -> str:
    return text.replace("\u2019", "'").replace("\u2018", "'")


def _strip_fillers(text: str) -> str:
    """Drop leading punctuation + ok/so/and filler words (repeatable)."""
    s = _norm_apos(" ".join(str(text).split()))
    while True:
        s = s.lstrip(_EDGE_PUNCT)
        m = re.match(r"([A-Za-z]+)", s)
        if not m:
            return s
        if m.group(1).lower() in _FILLERS:
            s = s[m.end(1):]
            continue
        return s


def _marker_here(s: str) -> str | None:
    for marker in _MARKERS:
        if s[:len(marker)].lower() != marker:
            continue
        rest = s[len(marker):]
        if rest == "" or rest[0] in _BOUND:
            return marker
    return None


def hypo_marker(turn: str) -> str | None:
    """The matched marker, or None when the turn is not hypothetical."""
    s = _norm_apos(_strip_fillers(turn))
    if not s:
        return None
    low = s.lower()
    for marker in _MARKERS:
        if low.startswith(marker):
            rest = s[len(marker):]
            if rest == "" or rest[0] in _BOUND:
                return marker
    return None


def is_hypothetical(turn: str) -> bool:
    """True when the turn opens with a closed-list hypothetical marker."""
    return hypo_marker(turn) is not None
