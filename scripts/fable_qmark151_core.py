#!/usr/bin/env python3
"""Experiment 151 -- no-question-mark core (the ONE change, sealed word list).

A message that contains NO "?" at all is treated exactly as if it ended
with "?" when BOTH hold:

  (a) its first word, after stripping optional openers, is a question word
      or question auxiliary (sealed list below), and
  (b) the existing teach parser does not accept it as a teach, i.e. both
      fable_bench73_english_arm.hear_teach_template and
      fable_loop121_agent.hear_teach_extra return None on the collapsed
      text AND on its qualifier-stripped form (conservative: either parser
      accepting on either form keeps the teach path).

SEALED WORD LIST (exact; matched case-insensitively after straightening
U+2019 to ASCII apostrophe and stripping surrounding punctuation):
  openers (skipped, repeatedly): hey, hi, ok, so, and, um
  single first words: what, whats, what's, who, whos, who's, whose,
    where, wheres, where's, which, when, how,
    is, are, was, does, do, did, can, could
  multi-word first phrases: tell me, do you know
("where's" is the apostrophe-normalised twin of listed "wheres";
"what's"/"who's" match straight and curly apostrophes as one word.)

Transform (byte-exact twin): collapse whitespace; strip trailing "."
and "!" (phone-typing periods); append "?"; feed the result through the
exact base path. Messages already containing "?" pass through untouched.

Nothing here edits an existing file: should_rewrite()/with_question_mark()
are pure functions called only from scripts/fable_loop151_agent.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

OPENERS_151 = ("hey", "hi", "ok", "so", "and", "um")

SINGLES_151 = (
    "what", "whats", "what's",
    "who", "whos", "who's", "whose",
    "where", "wheres", "where's",
    "which", "when", "how",
    "is", "are", "was",
    "does", "do", "did",
    "can", "could",
)

PHRASES_151 = (
    ("tell", "me"),
    ("do", "you", "know"),
)


def collapse_151(text: str) -> str:
    """Whitespace-collapsed message (twin construction uses this form)."""
    return " ".join(str(text).split())


def words_151(text: str) -> list[str]:
    """Lowercase word tokens for first-word detection (sealed matching)."""
    t = collapse_151(text).replace("\u2019", "'").lower()
    return re.findall(r"[a-z']+", t)


def first_hits_151(text: str) -> bool:
    """Condition (a): first word/phrase after openers is a question word."""
    w = words_151(text)
    i = 0
    while i < len(w) and w[i].strip("',.") in OPENERS_151:
        i += 1
    w = w[i:]
    if len(w) >= 3 and tuple(w[:3]) == ("do", "you", "know"):
        return True
    if len(w) >= 2 and tuple(w[:2]) == ("tell", "me"):
        return True
    return bool(w) and w[0].strip("',.") in SINGLES_151


def teach_rejects_151(text: str) -> bool:
    """Condition (b): the existing teach parser accepts nothing here."""
    import fable_bench73_english_arm as B73  # noqa: E402 (read-only)
    import fable_loop102_agent as L102  # noqa: E402 (read-only)
    import fable_loop121_agent as L121  # noqa: E402 (read-only)
    cands = [collapse_151(text)]
    try:
        stripped = L102.strip_trailing_qualifier(cands[0])
    except Exception:  # noqa: BLE001 -- parser guard stays conservative
        stripped = ""
    if stripped and stripped != cands[0]:
        cands.append(stripped)
    for cand in cands:
        if not cand:
            continue
        try:
            if B73.hear_teach_template(cand) is not None:
                return False
        except Exception:  # noqa: BLE001
            return False
        try:
            if L121.hear_teach_extra(cand) is not None:
                return False
        except Exception:  # noqa: BLE001
            return False
    return True


def should_rewrite_151(turn: str) -> bool:
    """True iff the turn takes the as-if-"?" path (conditions + no "?")."""
    text = collapse_151(turn)
    if not text or "?" in text:
        return False
    return first_hits_151(text) and teach_rejects_151(text)


def with_question_mark_151(turn: str) -> str:
    """Byte-exact "?" twin: collapsed text, trailing .!/ stripped, + "?"."""
    text = collapse_151(turn).rstrip().rstrip(".!")
    return text + "?"
