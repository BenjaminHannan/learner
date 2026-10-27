#!/usr/bin/env python3
"""Experiment 137d -- non-assertive framings never write (WRONG-WRITE class).

Base agent: loop137c (`scripts/fable_loop137c_agent.py`,
`artifacts/fable-hypo137c-20260922/loop137c-config.json`).

Step-1 facts (asked):
- 137c's closed sentence-initial marker list lives at
  `scripts/fable_fix137c_hypo.py:48-60` (`_MARKERS`, longest-first,
  matched by `hypo_marker`, lines 98-109).
- The path that produced the Supposedly junk: on loop137c
  "Supposedly Kim's boss is Lee." is NOT hypothetical (`is_hypothetical`
  is False: "supposedly" is not in `_MARKERS` and the trailing-boundary
  rule needs end/whitespace/punctuation after the marker), so
  `Loop137cEars.hear` falls through at
  `scripts/fable_loop137c_agent.py:84` (`return super().hear(turn)`)
  into the unchanged loop137b/138b pipeline, which parses
  "Supposedly Kim" as a 2-token possessive subject and SAVES the junk
  triple `[Supposedly Kim,boss,Lee]` (verified live pre-seal; reply
  "Saved: Supposedly Kim's boss is Lee."). "Say Kim's boss is Lee."
  saves `[Kim,boss,Lee]` on loop137c (only "say that" is a 137c marker,
  so bare "say" teaches).

THE ONE CHANGE (against loop137c): two new closed groups, fixed here
before any panel read, matched in the SAME sentence-initial position
with the SAME rules as 137c (after optional case-insensitive fillers
ok/so/and plus punctuation, repeatable; case-insensitive everywhere;
marker needs a trailing boundary of end/whitespace/punctuation, never
an apostrophe so "Say's ..."/"They Say's ..." possessives stay names).
Checked FIRST, before the unchanged loop137c pipeline (hypo guard +
base) runs:

  (a) Say-group: `say`, `say that` (longest-first, so "say that" wins
      over "say"). "Say X ..." is pretend (Ben's ruling 2026-09-22),
      never a fact. Reply: the sentence echoed WITHOUT the marker,
      then " (I'm treating that as pretend, so I won't save it.)",
      e.g. "Say Kim's boss is Lee." ->
      "Kim's boss is Lee. (I'm treating that as pretend, so I won't
      save it.)". NOTE: "say that" was a 137c hypo marker with the
      pretend-sentence reply; on 137d it moves to the say echo reply
      by design (never writes either way).
  (b) Hearsay-group: `supposedly`, `apparently`, `allegedly`,
      `reportedly`, `rumor has it`, `rumour has it`, `i heard`,
      `i heard that`, `they say`, `they say that`, `people say`
      (longest-first). Hearsay is never a fact (Ben's ruling).
      Reply exactly: "That sounds like hearsay, so I won't save it as
      a fact. If it's true, just tell me plainly."

Neither group ever writes (a single clarify is returned before any
teach path, rendered verbatim by the normal mouth path with zero
writes and zero self-routing: neither reply holds "didn't
understand"). Later questions in the same session therefore answer
only from real saved facts. Marker words LATER in a sentence or inside
names/titles ("Kim's song is Say My Name", "Kim's book is Apparently")
never match: only turn-initial position counts -- identical to loop137c.
Everything else falls through byte-identical (including all 137c hypo
markers except "say that", whose reply moves as stated above).

Stdlib only. Mac CPU. Deterministic: no seeds, no sampling, no model.
"""

from __future__ import annotations

import re

# Exact fixed reply for every hearsay-group turn.
HEARSAY_REPLY = ("That sounds like hearsay, so I won't save it as a fact. "
                 "If it's true, just tell me plainly.")

# Suffix appended to the echoed sentence for every say-group turn.
SAY_SUFFIX = " (I'm treating that as pretend, so I won't save it.)"

# Bare parenthetical when "say"/"say that" carries no remainder.
SAY_BARE_REPLY = "(I'm treating that as pretend, so I won't save it.)"

# Fillers skipped before the marker (whole words, case-insensitive).
_FILLERS = frozenset(["ok", "so", "and"])

# Say-group, longest-first for alternation (matched case-insensitively).
_SAY = [
    "say that",
    "say",
]

# Hearsay-group, longest-first (matched case-insensitively).
_HEARSAY = [
    "rumour has it",
    "rumor has it",
    "i heard that",
    "they say that",
    "people say",
    "supposedly",
    "apparently",
    "allegedly",
    "reportedly",
    "i heard",
    "they say",
]

_EDGE_PUNCT = " \t\n\r.,;:!?\"'()[]{}-_\u2013\u2014/"

# Trailing boundary after a marker: end, whitespace, or punctuation --
# but NOT an apostrophe: "Say's boss ..." / "They Say's mother ..." are
# possessive names (titles), not framings. Same rule as 137c.
_BOUND = " \t\n\r.,;:!?\"()[]{}-_\u2013\u2014/"

# Leading characters stripped from the echoed remainder after a
# say-group marker (whitespace + sentence punctuation, never letters).
_ECHO_STRIP = " \t\n\r.,;:!?\"'()[]{}-_\u2013\u2014/"


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


def _marker_here(s: str, markers: list[str]) -> str | None:
    for marker in markers:
        if s[:len(marker)].lower() != marker:
            continue
        rest = s[len(marker):]
        if rest == "" or rest[0] in _BOUND:
            return marker
    return None


def say_marker(turn: str) -> str | None:
    """The matched say-group marker, or None."""
    s = _norm_apos(_strip_fillers(turn))
    if not s:
        return None
    return _marker_here(s, _SAY)


def hearsay_marker(turn: str) -> str | None:
    """The matched hearsay-group marker, or None."""
    s = _norm_apos(_strip_fillers(turn))
    if not s:
        return None
    return _marker_here(s, _HEARSAY)


def say_echo(turn: str) -> str:
    """The framed sentence with the say-group marker removed.

    Whitespace-collapsed (same normalization as matching), leading
    punctuation/space stripped, original word case preserved, trailing
    punctuation kept. "" when nothing follows the marker.
    """
    s = _norm_apos(_strip_fillers(turn))
    marker = _marker_here(s, _SAY)
    if marker is None:
        return ""
    return s[len(marker):].lstrip(_ECHO_STRIP).rstrip(" \t\n\r")


def say_reply(turn: str) -> str:
    """Exact sealed reply for a say-group turn."""
    echo = say_echo(turn)
    if not echo:
        return SAY_BARE_REPLY
    return echo + SAY_SUFFIX


def frame_kind(turn: str) -> str | None:
    """'say' | 'hearsay' | None. Say-group wins (checked first)."""
    if say_marker(turn) is not None:
        return "say"
    if hearsay_marker(turn) is not None:
        return "hearsay"
    return None


def is_framed(turn: str) -> bool:
    """True when the turn opens with a closed-list 137d frame marker."""
    return frame_kind(turn) is not None
