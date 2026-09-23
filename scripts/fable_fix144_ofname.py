#!/usr/bin/env python3
"""Experiment 144 -- THE ONE CHANGE: multi-"of" names are one fact, not two.

Bug (director, loop140 + loop129b): the teach
  "Charles M. Schulz is famous for The Protocols of the Elders of Zion"
is refused with "I can take one fact at a time -- could you split that?"
and nothing is saved, while "Tolkien is famous for The Lord of the Rings"
(5 words) and "Dara Fenn is famous for The Protocols of the Elders"
(5 words) save fine. It cost bench132 case bench132-4hop-022 (edit teach
refused, old answer stood, 4-hop question wrong).

Diagnosis (Step 1): the reply text lives in
scripts/fable_earsguard91.py:34 (SPLIT_MSG), returned by screen_value() at
scripts/fable_earsguard91.py:53-60. The parsed value
"The Protocols of the Elders of Zion" is 7 whitespace-separated words, so
the >6-word clause (fable_earsguard91.py:45 MAX_VALUE_WORDS = 6, check at
line 58) fires. There is NO "of"-counter anywhere: one-"of" values pass
only because they are short (5 words). Loop121's narrowing
(fable_loop121_agent.py:78-99 _is_single_name_span, applied at :117-120)
exempts Title-Case spans only when they contain "and", so a pure-"of" name
still refuses at fable_loop121_agent.py:117 and again at
fable_earsguard91.py:58 on the fallback path.

THE RULE (this file): a message is treated as multi-fact ONLY when the
extra part is itself a complete teach frame -- its own subject (a
capitalised span) + a relation cue + a value -- not when "of" / "of the"
merely continues a capitalised name. Concretely, screen_value_144() is
byte-identical to the loop121 screen except the >6-word clause ALSO passes
a value that
  (a) is one capitalised name span (every token starts uppercase or is
      lowercase glue "of"/"the"/"and", and the span contains "of"), AND
  (b) contains no embedded complete teach frame (no relation cue with a
      capitalised subject before it and a non-empty value after it).

Every other screen ("?", ";", possessive-is, and-possessive, second
copula) still refuses exactly as before, so genuine two-fact messages
("Tom is a citizen of Peru and the capital of Peru is Lima",
"The capital of Peru is Lima, the capital of Chile is Santiago",
"Ann is famous for Rain and Tom is famous for Snow") still refuse: each
carries a second copula (or ";" / possessive), and each embeds a complete
teach frame ("the capital of Peru is Lima", ...). The copula-free
two-fact joins ("Cats and Tom died in the city of Oslo") fail the
name-span test AND trip the verbless-cue frame backstop.

Stdlib only (re + sys + pathlib at import; fable_earsguard91 is
stdlib-only). No existing file is edited; the loop144 agent
(scripts/fable_loop144_agent.py) calls screen_value_144() read-only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_earsguard91 as G91  # noqa: E402 (screens, read-only)

# Lowercase glue allowed inside one capitalised name span. Loop121 allowed
# {"of", "and"} for "and"-names; the observed "of"-names also need "the"
# ("The Protocols of the Elders of Zion", "Order of the Knights of Malta").
_NAME_GLUE_144 = frozenset({"of", "the", "and"})

_OF_RE = re.compile(r"\bof\b", re.IGNORECASE)

# Relation cues WITHOUT a copula (every other bench73/extra frame carries
# is/are/was/were or 's, already refused by the copula/possessive screens).
# These are the backstop: "Cats and Tom died in the city of Oslo" must stay
# refused even though it has no second copula.
_VERBLESS_CUES_144 = (
    "died in the city of",
    "plays the position of",
    "speaks the language of",
    "works in the field of",
    "was written in the language of",
)

# Copula cues, listed for explicitness (already refused upstream by
# _SECOND_COPULA; the frame test below would catch them anyway).
_COPULA_CUES_144 = ("is", "are", "was", "were")


def _is_single_name_span_121(value: str) -> bool:
    """Loop121's Title-Case "and"-name exemption, copied verbatim in logic.

    Source: fable_loop121_agent.py:78-99 (imported read-only nowhere here
    to keep this module stdlib-only; logic identical, cited).
    """
    text = str(value)
    if not re.search(r"\band\b", text, re.IGNORECASE):
        return False
    toks = text.split()
    if not toks:
        return False
    for tok in toks:
        stripped = tok.strip(".,;:'\"()")
        if not stripped:
            return False
        if stripped[0].isupper():
            continue
        if stripped.islower() and stripped.lower() in frozenset({"of", "and"}):
            continue
        return False
    return True


def is_single_of_name(value: str) -> bool:
    """True when value is one capitalised name span continued by of-phrases."""
    text = " ".join(str(value).split())
    if not _OF_RE.search(text):
        return False
    toks = text.split()
    if not toks:
        return False
    for tok in toks:
        stripped = tok.strip(".,;:'\"()")
        if not stripped:
            return False
        if stripped[0].isupper():
            continue
        if stripped.islower() and stripped.lower() in _NAME_GLUE_144:
            continue
        return False
    return True


def _cue_has_own_frame(text: str, cue_start: int, cue_end: int) -> bool:
    """True when a cue occurrence has its own subject (before) + value (after)."""
    before = text[:cue_start].rstrip()
    after = text[cue_end:].lstrip(" ,;:")
    if not before or not after:
        return False
    last = before.split()[-1].strip(".,;:'\"()")
    if not last or not last[0].isupper():
        return False
    first = after.split()[0].strip(".,;:'\"()")
    return bool(first)


def has_embedded_teach_frame(value: str) -> bool:
    """True when the value embeds a complete teach frame of its own.

    A complete frame = relation cue + capitalised subject before it +
    non-empty value after it. "of"/"of the" continuing a capitalised name
    never qualifies (no cue, no second subject).
    """
    text = " ".join(str(value).split())
    if not text:
        return False
    # Space-padded lowercase copy: indices shift by exactly 1 vs `text`
    # (padding is one ASCII space), so cue spans map back directly.
    padded = " " + text.lower() + " "
    for cue in _VERBLESS_CUES_144 + _COPULA_CUES_144:
        needle = " " + cue + " "
        pos = padded.find(needle)
        while pos >= 0:
            # Cue occupies text[pos:pos+len(cue)]; the subject must end at
            # or before pos and the value must start at pos+len(cue).
            if _cue_has_own_frame(text, pos, pos + len(cue)):
                return True
            pos = padded.find(needle, pos + 1)
    return False


def screen_value_144(value: str) -> str | None:
    """Exp-91/121 value screen with the multi-"of"-name narrowing.

    Identical refuses for "?", ";", possessive-is, and-possessive and
    second copula; identical passes for short values and loop121
    "and"-names; the >6-word screen ADDITIONALLY passes a single
    capitalised "of"-name span with no embedded teach frame. Returns the
    clarify message or None to let pass.
    """
    text = str(value)
    if "?" in text:
        return G91.QUESTION_MSG
    if (";" in text
            or G91._POSSESSIVE_IS.search(text)
            or G91._AND_POSSESSIVE.search(text)
            or G91._SECOND_COPULA.search(text)):
        return G91.SPLIT_MSG
    if len(text.split()) > G91.MAX_VALUE_WORDS:
        if _is_single_name_span_121(text):
            return None
        if is_single_of_name(text) and not has_embedded_teach_frame(text):
            return None
        return G91.SPLIT_MSG
    return None


# ---------------------------------------------------------------- mixin


class OfNameScreenMixin:
    """The one change as stackable methods (same style as exp 140's mixin)."""

    @staticmethod
    def is_single_of_name(value: str) -> bool:
        return is_single_of_name(value)

    @staticmethod
    def has_embedded_teach_frame(value: str) -> bool:
        return has_embedded_teach_frame(value)

    @staticmethod
    def screen_value(value: str) -> str | None:
        return screen_value_144(value)
