#!/usr/bin/env python3
"""Exp 248 -- THE ONE CHANGE (diagnosis 243 cause C2): read "whats".

Nothing in the 138i stack reads "whats / whos / wheres" typed without an
apostrophe (fable_fix158_qform.py:42 expands only "what's"). This module is
an OUTERMOST ears mixin (it sits above ChainOf174), so every reader below it
(ChainOf174, Typo165, Verb167*, Name173*, Me166, ..., Qform158, FakeEars)
sees the expanded text.

Rewrite (exactly what is accepted):
  * the turn, after trimming, ends in "?" and has no "?" or "!" before the
    final run of marks (glued multi-sentence turns are never touched);
  * optionally ONE leading filler word from FILLERS248, optionally followed
    by "," or "!" -- the filler is dropped from the rewritten text;
  * then, as the first real word, one of whats / whos / wheres / whens /
    hows in any casing, followed by whitespace and at least one more word;
  * that word must not resolve to a notebook entity (a person really named
    "Hows" is never rewritten). Longer names that merely start with these
    letters ("Whatsley", "Whoson") never match: the word must end exactly
    there.
  -> "<word minus final s> is <rest of the turn, byte-for-byte>".

The rewrite is used ONLY when the unchanged stack below hears it as an ask
(same probe-then-fallback contract as Qform158 / ChainOf174); otherwise the
original turn is heard exactly as before. hear() does not write the
notebook, so the probe cannot store anything.
"""

from __future__ import annotations

import re

WHATS_WORDS248 = ("whats", "whos", "wheres", "whens", "hows")
FILLERS248 = ("so", "hey", "hi", "hello", "yo", "ok", "okay", "well", "oh",
              "um", "uh", "please")

_WHATS_RE248 = re.compile(
    r"^(?:(?P<filler>" + "|".join(FILLERS248) + r")[,!]?\s+)?"
    r"(?P<word>" + "|".join(WHATS_WORDS248) + r")(?=\s)\s+(?P<rest>\S.*)$",
    re.I | re.S)
_TRAILING_MARKS248 = re.compile(r"[?.!]+\s*$")


def rewrite_whats248(turn: str) -> tuple[str, str] | None:
    """Return (candidate, whats_word) or None when the rule does not fire."""
    text = " ".join(str(turn).split())
    if not text.endswith("?"):
        return None
    m_end = _TRAILING_MARKS248.search(text)
    stem = text[:m_end.start()] if m_end else text
    if "?" in stem or "!" in stem:
        return None
    m = _WHATS_RE248.match(text)
    if m is None:
        return None
    word = m.group("word")
    cand = word[:-1] + " is " + m.group("rest")
    return cand, word


def _notebook_of(ears):
    for name in ("nb", "_nb", "notebook"):
        try:
            nb = getattr(ears, name)
        except Exception:
            nb = None
        if nb is not None and hasattr(nb, "resolve"):
            return nb
    return None


def is_entity_name248(ears, word: str) -> bool:
    """True when `word` resolves (OK or ambiguous) in the live notebook."""
    nb = _notebook_of(ears)
    if nb is None:
        return False
    try:
        res = nb.resolve(word)
    except Exception:
        return False
    status = getattr(res, "status", None)
    if status is None and isinstance(res, tuple) and res:
        status = res[0]
    return str(status).upper() in ("OK", "AMBIGUOUS")


class Whats248Mixin:
    """Outermost cooperative ears mixin: whats/whos/wheres -> what is ..."""

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        hit = rewrite_whats248(turn)
        if hit is not None and not is_entity_name248(self, hit[1]):
            cand = hit[0]
            try:
                probe = super().hear(cand)  # type: ignore[misc]
            except Exception:
                probe = None
            if isinstance(probe, list) and any(
                    isinstance(a, dict) and a.get("act") == "ask"
                    for a in probe):
                try:
                    self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                        "loop248-whats", 1.0)
                except AttributeError:
                    pass
                return probe
        return super().hear(turn)  # type: ignore[misc]
