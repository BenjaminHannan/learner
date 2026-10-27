#!/usr/bin/env python3
"""Experiment 137b -- discourse-glued names: the closed list + strip rule.

THE ONE CHANGE (against loop138b's inherited 137 upgrade): a multi-word
subject or value name accepted by 137's rule
(`scripts/fable_fix137_names.py:123-127`, the 2-4 Title-case token check
called from `scripts/fable_loop138b_agent.py:142-169`) is REJECTED when

  (a) it contains a sentence break (". ", "! ", "? ") that is NOT an
      abbreviation period (a single-capital initial like "A. " or a common
      title abbreviation "St./Mr./Mrs./Ms./Dr. " never counts -- exp-129
      allows one trailing period on abbreviation-shaped tokens, so
      "A. A. Milne" stays one name), or
  (b) its first token (lowercased, edge punctuation stripped) is in the
      closed DISCOURSE137B list below -- fixed before any panel read.

In that case the message is handled as if that first token (and a
following comma/period, which rides on the same whitespace token: "So,",
"Hi.") were absent: the rest is re-parsed through the unchanged loop138b
pipeline, and if the rest still does not parse (no non-clarify action)
the base refusal stands.

Scope notes (judgment calls, all sealed in PASSMARKS.md):
- Subject triggers strip the message-leading token (possessive subjects
  are message-initial; a correction-prefixed turn whose name does not
  start the message is left to the base path).
- Value triggers strip only discourse-first-token values ("Oh Bob" ->
  "Bob"). A value containing a sentence break is left to the base refusal
  (loop138b already refuses "Mary Ann's boss is Bob. Call me." with 0
  writes; truncating to the head would newly teach).
- Phone-fronted questions ("So what is Tom's boss?") carry the same glued
  token and never reach 137's rule (it returns None on "?"). The same
  strip applies on "?" turns whose first token is discourse, used only
  when the rest parses to a non-clarify action (else the base refusal).
  Statements starting with a discourse word but outside 137's rule
  ("Imagine the capital of Peru is Lima.", "Actually, ...") are untouched.
- Known edge: a real title starting with a listed word in 137 position
  ("Hey Jude's director ...", "Mary Ann's favorite movie is Hey Jude.")
  strips like discourse. No sealed suite contains such a case (verified by
  scan); the T1 title probes use base-path positions and stay identical.

Stdlib only. Mac CPU. Deterministic: no seeds, no sampling, no model.
"""

from __future__ import annotations

import re

# Closed list, fixed before any panel read (brief order).
DISCOURSE137B = frozenset([
    "suppose", "imagine", "say", "hi", "hey", "hello", "okay", "ok",
    "so", "well", "oh", "btw", "also", "and", "but", "actually",
    "basically", "anyway", "please", "remember", "note", "fyi",
    "listen", "look",
])

_EDGE = ".,;:'\"()!?"

# Abbreviation periods that never count as sentence breaks: a single
# capital initial ("A. ") or a common title abbreviation.
_ABBR_RE = re.compile(r"\b(?:[A-Z]|St|Mr|Mrs|Ms|Dr)\. ")


def first_token_lower(name: str) -> str:
    toks = str(name).split()
    if not toks:
        return ""
    return toks[0].strip(_EDGE).strip().lower()


def has_sentence_break(name: str) -> bool:
    """True for a real sentence break; abbreviation periods excluded."""
    scrubbed = _ABBR_RE.sub("", str(name))
    return (". " in scrubbed) or ("! " in scrubbed) or ("? " in scrubbed)


def is_discourse_name(name: str) -> bool:
    """True when a multi-word name triggers the 137b rejection."""
    toks = str(name).split()
    if len(toks) < 2:
        return False
    if has_sentence_break(name):
        return True
    return first_token_lower(name) in DISCOURSE137B


def strip_first_token(text: str) -> str:
    """Drop the message-leading token ("So,"/"Hi." ride on one token)."""
    parts = str(text).split(None, 1)
    if len(parts) < 2:
        return ""
    rest = parts[1].lstrip(" ,.")
    return " ".join(rest.split())


def message_starts_with_name_token(turn: str, name: str) -> bool:
    """True when the name's first token is the message's first token."""
    t = " ".join(str(turn).split())
    ntok = str(name).split()
    if not ntok:
        return False
    first = t.split(None, 1)
    if not first:
        return False
    a = first[0].strip(_EDGE).strip().lower()
    b = ntok[0].strip(_EDGE).strip().lower()
    return bool(a) and a == b
