#!/usr/bin/env python3
"""Exp 265 -- the "our/we" ask-whose rule (the ONE change on 261b's arm A).

Ben's ruling (design/v3/30-modes/our-policy-decision-20260923.md): a teach
whose owner is we/us/our/ours/ourselves is NOT the speaker's fact. 261's
sealed canonicaliser (claude_earcheck261_canon, read-only, never edited) maps
those words to "me"; this module replaces it for arm A only:

- FIRST_WORDS (i/me/my/mine/myself, any case) still map to "me".
- A TEACH frame whose subject is a GROUP word (we/us/our/ours/ourselves, any
  case) is NEVER saved. It is diverted: the turn gets the fixed reply
      "Whose <relation words> is <V>? Tell me whose, and I'll remember it."
  with 0 writes for that frame. <relation words> is the table-v2 canonical
  relation name with underscores turned into spaces; <V> is the frame value.
- Every other frame in the turn is handled as before (checker + guard).
- ASK frames: first-person subjects map to "me" as before; group-word ASK
  subjects pass through unchanged (never diverted, never checked -- questions
  never write). The registered panel has no question families.

Order in the pipeline (unchanged apart from the canon swap): ear greedy raw
-> brake -> 265 canon/divert -> checker (prompt B, theta 0.25, TEACH only,
no query spent on diverted frames) -> 261b span guard.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_model as E  # noqa: E402

FIRST_WORDS = frozenset({"i", "me", "my", "mine", "myself"})

GROUP_WORDS = frozenset({"we", "us", "our", "ours", "ourselves"})

_ME = "me"

ASK_TAIL = "Tell me whose, and I'll remember it."


def is_group_subject(subject) -> bool:
    return str(subject).strip().lower() in GROUP_WORDS


def is_first_subject(subject) -> bool:
    return str(subject).strip().lower() in FIRST_WORDS


def canon_subject_265(subject: str) -> str:
    s = str(subject).strip()
    if s.lower() in FIRST_WORDS:
        return _ME
    return subject


def canonicalise_265(frames):
    """New list with first-person TEACH/ASK subjects mapped to "me".

    Group-word TEACH subjects are left as-is here (the divert step removes
    them); group-word ASK subjects pass through unchanged. Never mutates.
    """
    out = []
    for f in frames:
        if isinstance(f, dict) and f.get("act") in ("TEACH", "ASK") and "subject" in f:
            if f.get("act") == "ASK" and is_group_subject(f["subject"]):
                out.append(dict(f))
            else:
                g = dict(f)
                g["subject"] = canon_subject_265(f["subject"])
                out.append(g)
        else:
            out.append(f)
    return out


def relation_words(relation: str) -> str:
    try:
        canon = E.canon_rel(relation)
    except Exception:
        canon = None
    return (canon or str(relation)).strip().replace("_", " ")


def ask_whose_reply(frame) -> str:
    return (f"Whose {relation_words(frame.get('relation', ''))} "
            f"is {str(frame.get('value', '')).strip()}? {ASK_TAIL}")


def divert(frames):
    """Split 265-canonicalised frames into (kept, diverted).

    Diverted = TEACH frames with group-word subjects. Order preserved in both
    lists; diverted frames carry why="ASK_WHOSE" and the fixed reply text.
    Never mutates input.
    """
    kept, diverted = [], []
    for f in frames:
        if isinstance(f, dict) and f.get("act") == "TEACH" and is_group_subject(f.get("subject", "")):
            diverted.append(dict(f, why="ASK_WHOSE", reply=ask_whose_reply(f)))
        else:
            kept.append(f)
    return kept, diverted


def turn_reply(diverted) -> str:
    """The turn's reply text: "" when nothing diverted, else the fixed ask
    reply per diverted frame joined with a single space."""
    return " ".join(d["reply"] for d in diverted) if diverted else ""


def asks_whose(reply: str) -> bool:
    """Sealed check the scorer uses: the turn asks whose iff its reply is the
    fixed template (starts "Whose ", ends with the fixed tail)."""
    r = str(reply).strip()
    return r.startswith("Whose ") and ASK_TAIL in r
