#!/usr/bin/env python3
"""Exp 261b -- mixed-case span guard (the ONE change on top of 261's sealed arm A).

Rule (from design/v3/30-modes/261b-decision.md, Ruling 2): after the checker, a
TEACH frame whose subject or value span mixes a Capitalised word with a
lowercase non-particle word is held back as UNSURE. The guard only holds back;
it never adds, edits or reorders a frame. ASK frames are never guarded
(questions never write).

Fixed before the seal, from the relation table v2 and general knowledge only:

- PARTICLES: de, da, van, von, der, la, le, del, di, bin, al (decision note).
  A lowercase particle inside an otherwise-Capitalised name span (e.g. a
  "van"-style family name) is not a typo leak, so it never trips the guard.
- VALUE_EXEMPT_KINDS: value_kind values from table v2 whose values are common
  nouns, not proper names: literal (occupation, pet, hobby, sport, nickname,
  ...), thing (instrument, favourite foods, ...), work (notable_work titles,
  which carry articles), date, number. A mixed-case job title or food phrase
  is ordinary wording, not a typo leak. Proper-name kinds -- person, pet,
  place, organization, language -- are always checked.
- Subjects are always checked (subjects are names or "me"; "me" is a single
  lowercase word and always passes).

Span rule: strip edge punctuation per word; ignore words with no cased
letters (digits etc.). A word counts Capitalised when its first cased letter
is uppercase, lowercase when all its cased letters are lowercase. A span trips
iff it holds at least one Capitalised word AND at least one lowercase word
that is not a particle. All-lowercase spans (lowercase chat) and
all-Capitalised spans pass.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_model as E  # noqa: E402

PARTICLES = frozenset({
    "de", "da", "van", "von", "der", "la", "le", "del", "di", "bin", "al",
})

# value_kind values (table v2) whose values are common nouns, not proper names.
VALUE_EXEMPT_KINDS = frozenset({"literal", "thing", "work", "date", "number"})

_EDGE = " \t\"'.,;:!?()[]{}"


def _words(span):
    out = []
    for w in str(span).split():
        w = w.strip(_EDGE)
        if w:
            out.append(w)
    return out


def _case(w):
    """Return 'cap', 'low' or None (no cased letters)."""
    cased = [c for c in w if c.isalpha()]
    if not cased:
        return None
    if cased[0].isupper():
        return "cap"
    if all(not c.isupper() for c in cased):
        return "low"
    return None


def span_mixed(span):
    """True iff the span mixes a Capitalised word with a lowercase non-particle."""
    seen_cap, seen_low = False, False
    for w in _words(span):
        c = _case(w)
        if c == "cap":
            seen_cap = True
        elif c == "low" and w.lower() not in PARTICLES:
            seen_low = True
        if seen_cap and seen_low:
            return True
    return False


def _value_kind(relation):
    canon = E.canon_rel(relation) or str(relation).strip()
    for r in E._TABLE["relations"]:
        if r["name"] == canon:
            return r.get("value_kind")
    return None


def guard_hold(frame):
    """Return a reason string if this TEACH frame is held, else None.

    Reasons: 'subject_mix', 'value_mix', 'both_mix'. Non-TEACH frames and
    value-exempt kinds never held.
    """
    if not isinstance(frame, dict) or frame.get("act") != "TEACH":
        return None
    s_hold = span_mixed(frame.get("subject", ""))
    kind = _value_kind(frame.get("relation", ""))
    v_hold = span_mixed(frame.get("value", "")) if kind not in VALUE_EXEMPT_KINDS else False
    if s_hold and v_hold:
        return "both_mix"
    if s_hold:
        return "subject_mix"
    if v_hold:
        return "value_mix"
    return None


def guard_split(saved_frames):
    """Split checker-saved frames into (kept, held). Order preserved; held
    frames carry why='GUARD_UNSURE' and guard=<reason>. Never mutates input."""
    kept, held = [], []
    for f in saved_frames:
        reason = guard_hold(f)
        if reason is None:
            kept.append(f)
        else:
            held.append(dict(f, why="GUARD_UNSURE", guard=reason))
    return kept, held
