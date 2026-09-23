#!/usr/bin/env python3
"""Experiment 129 -- THE ONE CHANGE: strip trailing sentence punctuation.

Red team 124 (bug 4) showed bench73-style teaches keep the sentence-final
period inside the stored value ("AJ Lee is a citizen of Italy." stores
'Italy.'), which then breaks every chain through that value. Step-0 probe
(scripts/fable_fix129_probe.py) confirmed the leak on EVERY teach path
except FakeEars-with-plain-period (its regex strips one '.') and the
explicit-dot bench73 patterns (apprentice_of etc.):

  LEAK: bench73 citizen/capital/official-language (+ all patterns without
        a trailing-dot guard) with '.', '!', '?', trailing spaces;
        exp-92 extra patterns (employer/occupation/child) with '.';
        FakeEars possessive path with '!' and '?'.
  clean: FakeEars possessive + '.'; explicit-dot bench73 patterns + '.'.

THE RULE (strip-then-restore, stated here and tested in F1):
  1. Trim outer whitespace; drop outer quotes/brackets first.
  2. Greedily drop ALL trailing sentence-punctuation runs ``. ! ? ; :``
     (with whitespace/quotes between them).
  3. If at least one '.' was dropped AND the stem's last
     whitespace-separated token is abbreviation-shaped, put ONE '.' back.
     Abbreviation-shaped = the token (a) contains another '.' besides the
     dropped one (``D.C``, ``U.S.S.R``, ``U.K``), or (b) is a single
     uppercase letter (initials like ``J``), or (c) is a known honorific /
     street token (St Mr Mrs Ms Dr Jr Sr Ave Blvd Rd Ln Mt Ft, any case).
     Rationale: a sentence period can only ever be the LAST character, so
     any '.' strictly inside the span is content; a trailing '.' after an
     abbreviation token is ambiguous and the conservative choice (keep) is
     picked because dropping a real abbreviation period corrupts a name
     while keeping a sentence period only risks the old junk behaviour on
     exactly the tokens people abbreviate.

  Examples: "Italy." -> "Italy"; "Italy!" -> "Italy"; "Paris?" -> "Paris";
  "Washington, D.C." -> "Washington, D.C."; "U.S.S.R." -> "U.S.S.R.";
  "D.C.." -> "D.C."; "St." -> "St."; "Hello..." -> "Hello".

Applied (subclass/wrap only, no existing file edited) at TWO levels so
every teach path is covered before the write:
  * ears hear(): sanitize the name/value of outgoing teach/correct actions;
  * loop _act(): sanitize again just before the notebook write
    (covers the inner-chain Bench73Stage/FakeStage delegate path whose
    correct/teach flag was computed on the raw span).

Relation keys are never touched. Forget/ask/clarify actions are never
touched. Empty-after-strip spans are left as-is (downstream guards, e.g.
"I didn't get the value.", still fire).
"""

from __future__ import annotations

import copy

_SENTENCE_PUNCT = frozenset(".!?;:")
_ABBREV_WORDS = frozenset({
    # honorifics / street tokens (were already here)
    "st", "mr", "mrs", "ms", "dr", "jr", "sr",
    "ave", "blvd", "rd", "ln", "mt", "ft",
    # corporate designators ("Apple Inc." must keep its period)
    "inc", "corp", "ltd", "co", "plc", "llc", "ltda", "gmbh", "ag", "sa",
    "nv", "pty", "bros", "dept", "univ", "govt", "assn", "est",
    # personal titles
    "prof", "rev", "gen", "col", "maj", "lt", "sgt", "sen", "rep", "gov",
    "pres", "hon", "esq", "phd", "md",
    # common short forms
    "etc", "vs",
})


def _last_token(text: str) -> str:
    toks = text.split()
    return toks[-1] if toks else ""


def _is_abbrev_token(token: str) -> bool:
    """True when a period after this stem token is probably content."""
    t = token.strip("([{<\u00ab\"'\"' ")
    if not t:
        return False
    if "." in t:
        return True  # D.C / U.S.S.R / U.K -- internal periods are content
    if len(t) == 1 and t.isalpha() and t.isupper():
        return True  # single initial "J"
    return t.lower() in _ABBREV_WORDS


_PAIRS = {")": "(", "]": "[", "}": "{", ">": "<", "»": "«"}
_CLOSERS = frozenset(_PAIRS)


def _strip_unmatched_closer(s: str) -> str:
    """Drop ONE trailing closer if it has no matching opener in the span."""
    if s and s[-1] in _CLOSERS:
        opener = _PAIRS[s[-1]]
        if s.count(s[-1]) > s.count(opener):
            return s[:-1].rstrip()
    return s


_QUOTE_PAIRS = [("\"", "\""), ("'", "'"), ("\u201c", "\u201d"),
                ("\u2018", "\u2019"), ("\u00ab", "\u00bb")]


def _strip_wrapping_quotes(s: str) -> str:
    """Drop surrounding quote pairs ('"France"' -> 'France')."""
    changed = True
    while changed and len(s) >= 2:
        changed = False
        for q0, q1 in _QUOTE_PAIRS:
            if s[0] == q0 and s[-1] == q1:
                inner = s[1:-1]
                if q0 != q1 or q0 not in inner:
                    s = inner.strip()
                    changed = True
                    break
    return s


def strip_sentence_punct(span: str) -> str:
    """Strip trailing sentence punctuation, keeping abbreviation periods.

    Balance-aware: matched brackets/quotes are content (only unmatched
    closers and surrounding wrapping quotes are dropped), so balanced
    spans like "Ford Falcon (North America)" pass through byte-identical.
    """
    s = " ".join(str(span).split())
    if not s:
        return s
    s = _strip_wrapping_quotes(s)
    s = _strip_unmatched_closer(s)
    dropped_dot = False
    while s and (s[-1] in _SENTENCE_PUNCT or s[-1].isspace()):
        if s[-1] == ".":
            dropped_dot = True
        s = s[:-1].rstrip()
        s = _strip_unmatched_closer(s)
    if not s:
        return " ".join(str(span).split())
    s = _strip_wrapping_quotes(s)
    if dropped_dot and _is_abbrev_token(_last_token(s)):
        s = s + "."
    return s


def sanitize_triple(triple: tuple[str, str, str]
                    ) -> tuple[str, str, str]:
    """Strip subject and value spans; relation key byte-identical."""
    subj, rel, obj = triple
    return (strip_sentence_punct(subj), rel, strip_sentence_punct(obj))


def sanitize_action(action: dict) -> dict:
    """Copy of a teach/correct action with name/value stripped; else as-is."""
    if not isinstance(action, dict):
        return action
    if action.get("act") not in ("teach", "correct"):
        return action
    out = copy.copy(action)
    if "name" in out:
        cleaned = strip_sentence_punct(out.get("name", ""))
        if cleaned:
            out["name"] = cleaned
    if "value" in out:
        cleaned = strip_sentence_punct(out.get("value", ""))
        if cleaned:
            out["value"] = cleaned
    return out


def sanitize_actions(actions: list[dict]) -> list[dict]:
    return [sanitize_action(a) for a in list(actions)]
