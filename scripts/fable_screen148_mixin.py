#!/usr/bin/env python3
"""Experiment 148 -- question screen for meaning-changing words (mixin).

THE ONE CHANGE (question side only): before any question composer/lookup
runs, if a "?" turn contains a negation or a time qualifier the notebook
cannot represent, the ears return a short honest clarify and never answer.
Teach (statement) turns are untouched -- only trailing-"?" turns consult
this module.

Sealed word list (see PASSMARKS.md; reasons sealed there, one line each):

  NEGATION (case-insensitive):
    not, never, n't (apostrophe contraction), "no one", nobody, none.
    Bare "no" is NOT a trigger; neither/nor/nothing are NOT triggers.
  TIME:
    4-digit year ([12]\\d{3}), "as of", before, after, formerly,
    originally, "used to", currently.
    "now" and "still" are NOT triggers.

Entity exemption: a trigger token is ignored when it lies inside a taught
entity/value mention from the live notebook triples (titles like "1984",
"Windows 2000", "Can't Buy Me Love" name things, not times). Matching is
on word-boundary tokens, so "Knot", "Notre-Dame", "Norway", "Annotated"
never fire.

No existing file is edited; agents subclass/wrap this module.
"""

from __future__ import annotations

import re

# --------------------------------------------------------------------------
# sealed patterns
# --------------------------------------------------------------------------

_NEG_WORDS = ("not", "never", "nobody", "none")
_NEG_RES = [re.compile(r"\b" + w + r"\b", re.IGNORECASE)
            for w in _NEG_WORDS]
_NO_ONE_RE = re.compile(r"\bno\s+one\b", re.IGNORECASE)
# n't with straight or curly apostrophe (contracted negation only).
_NT_RE = re.compile(r"n['\u2019]t\b", re.IGNORECASE)

_YEAR_RE = re.compile(r"\b[12]\d{3}\b")
_TIME_WORDS = ("formerly", "originally", "currently", "before", "after")
_TIME_RES = [re.compile(r"\b" + w + r"\b", re.IGNORECASE)
             for w in _TIME_WORDS]
_AS_OF_RE = re.compile(r"\bas\s+of\b", re.IGNORECASE)
_USED_TO_RE = re.compile(r"\bused\s+to\b", re.IGNORECASE)

NEG_MSG = ("I didn't understand that. I only know current facts and I "
           "can't do 'not' -- could you say it without that part?")
TIME_MSG = ("I didn't understand that. I only know current facts, not "
            "years or 'as of' -- could you say it without that part?")


def _spans(text: str, rx: "re.Pattern[str]") -> list[tuple[int, int]]:
    return [m.span() for m in rx.finditer(text)]


def _inside(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    return any(s <= start and end <= e for s, e in spans)


def trigger_spans(question: str,
                  known: list[str] | tuple[str, ...] = ()) -> list[
                      tuple[str, str]]:
    """Return [(kind, matched-text)] for sealed triggers in `question`.

    `known` is taught entity/value display strings; any trigger wholly
    inside one of their case-insensitive occurrences is exempted (it names
    a thing, e.g. a title, rather than negating or dating the question).
    kind is "neg" or "time".
    """
    q = str(question)
    low = q.lower()
    exempt: list[tuple[int, int]] = []
    for name in known:
        nm = str(name or "").strip().lower()
        if not nm:
            continue
        start = 0
        while True:
            i = low.find(nm, start)
            if i < 0:
                break
            exempt.append((i, i + len(nm)))
            start = i + 1
    out: list[tuple[str, str]] = []
    for rx in _NEG_RES:
        for m in rx.finditer(q):
            if not _inside(exempt, m.start(), m.end()):
                out.append(("neg", m.group(0)))
    for rx in (_NO_ONE_RE, _NT_RE):
        for m in rx.finditer(q):
            if not _inside(exempt, m.start(), m.end()):
                out.append(("neg", m.group(0)))
    if _YEAR_RE.search(q):
        for m in _YEAR_RE.finditer(q):
            if not _inside(exempt, m.start(), m.end()):
                out.append(("time", m.group(0)))
    for rx in _TIME_RES + [_AS_OF_RE, _USED_TO_RE]:
        for m in rx.finditer(q):
            if not _inside(exempt, m.start(), m.end()):
                out.append(("time", m.group(0)))
    return out


def screen_question(question: str,
                    known: list[str] | tuple[str, ...] = ()) -> str | None:
    """Return the clarify text if the question must be screened, else None.

    Only the FIRST trigger class matters: negation wins over time when both
    are present (one honest message either way; never an answer).
    """
    hits = trigger_spans(question, known)
    if not hits:
        return None
    kinds = {k for k, _ in hits}
    if "neg" in kinds:
        return NEG_MSG
    return TIME_MSG
