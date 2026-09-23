#!/usr/bin/env python3
"""Exp 270b -- THE ONE CHANGE: 270's text normaliser in front of the EAR
(261b's arm A), with the keep-s rule fixed.

Base: 261b's registered arm A (v4.1 ear + speaker canonicaliser + brake +
YES/NO checker at sealed theta 0.25, prompt B + 261b span guard), all imported
read-only and unchanged. The normaliser runs outermost on the raw turn text,
before the ear sees it.

RULE (fixed before the seal; general knowledge + 270's registered FAIL only;
never any panel):
The normaliser fires only when (a) the turn has no capital letters at all
(reason "lowercase") or (b) the turn has no apostrophes and an "Xs <relation>"
possessive pattern is present (reason "possessive"). Anything else passes
through byte-identical (the exact same string), so clean turns behave exactly
like 261b's arm A (M4 by construction).

When it fires, the pass does two things, in order:
  1. Possessive fix: "Xs <relation>" -> "X's <relation>", with the FIXED
     keep-s rule (this experiment's fix for 270's three Beno/Dilo/Haki-stem
     near-miss wrong saves):
       - words that are common English (COMMON270b) or check-tail words are
         never fixed ("his mother" stays);
       - a word whose full lowercase form is a known s-ending name keeps its
         s (whole word + "'s"): the sealed S_NAMES270b list (general-knowledge
         real-world s-names: james, thomas, charles, louis, tess, morris,
         dennis, miles, ...) or a full word already in the seen-names memory
         ("James" seen -> "jamess ..." keeps);
       - a word whose stem (without the s) is a seen name or a common word
         strips ("benos" with Beno seen -> "Beno's"; "dogs" -> "dog's";
         "wills" -> "will's");
       - otherwise the s STRIPS by default (no ending heuristic): "belmaras"
         -> "Belmara's", "benos" (unseen) -> "Beno's", "hakis" -> "Haki's",
         "dilos" -> "Dilo's". 270's ss/us/is/os/mes/les ending heuristic is
         GONE: it caused the Benos/Dilos/Hakis misses (kept) and the
         Thomas->Thoma's residual (stripped). Residual risk flips to real
         s-names absent from S_NAMES270b and unseen (they strip; disclosed).
     "Only-if" reading (task brief): a name keeps its s only if its stem is
     not a known (seen) name and the word is not in the common-word list.
     Both keep branches satisfy this (stems "jame"/"tes"/... are not seen
     names; "james"/"tess"/... are not common words). Stripping an unknown
     stem is allowed by the rule and is the default.
     Leading wh-contractions without apostrophes ("whos", "whats", ...)
     get theirs ("who's", "what's", ...) so casual questions parse.
  2. Capitals: every word that is not common English (COMMON270b) is
     capitalised, except a word matching a seen name, which takes the seen
     capitalisation (seen names win over COMMON270b).
     COMMON270b = 270's COMMON270 (imported read-only) PLUS pet-species
     singulars (dog, cat, horse, rabbit, parrot, turtle, goat, hamster,
     puppy, kitten): relation-noun species stay lowercase so "benos dog"
     becomes "Beno's dog" exactly, and A diverges from A261b only where the
     possessive fix fires. (270 removed animal nouns for the LOOP line's
     description-check; the ear line has no such check, and dev decides.)

Suppression (carried from 270 D1, pre-seal): trailing confirmation-check
tails (", right", bare "right" with punctuation, ", isn't it",
", don't you think", ", yeah/yep/yes/no", ", ok/okay", ", correct",
", you know") pass through unchanged. Bare "so ..."-heads are NOT
suppressed (same rationale as 270 D1).

Seen-names memory (the "known name" source on the stateless ear line): the
caller passes known_names={lowercase: StoredForm}, accumulated from the
current item's earlier turns (setup/context capitalised content words;
reset per item). Single-turn s-stems with no seen name strip by default.

Known limits (pre-seal, reported): names that are common English words
("will", "mark", "hope", ...) can never be restored when lowercase;
multi-word names, "X is a Y" shapes and our/we owners behave as 261b does.
Real s-names outside S_NAMES270b and unseen strip (documented residual).
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_type270_normalise as N270  # noqa: E402 (read-only: constants)

COMMON270b = N270.COMMON270 | frozenset("""
dog cat horse rabbit parrot turtle goat hamster puppy kitten
""".split())

# General-knowledge real-world s-ending given/family names (fixed pre-seal).
# A full word matching this list keeps its s ("james" -> "James's").
S_NAMES270b = frozenset("""
james thomas charles louis tess morris dennis miles chris jess bess
wells brooks hayes watts rhodes forbes collins evans davis lewis
hughes burns jones williams adams collins barnes holmes
""".split())

_REL270 = N270.REL270
_NEVER_FIX270 = N270._NEVER_FIX270
_WH270 = N270._WH270
_CHECK_RES270 = N270._CHECK_RES270
_POSS_RE270 = N270._POSS_RE270
_WORD_RE270 = N270._WORD_RE270


def _possessive_form270b(word: str, names: dict):
    """Possessive of an s-ending word, or None when it must not be fixed."""
    wl = word.lower()
    if wl in COMMON270b or wl in _NEVER_FIX270:
        return None
    if len(word) <= 2:
        return None
    if wl in S_NAMES270b:
        return word + "'s"
    if wl in names:
        return word + "'s"
    stem = word[:-1]
    sl = stem.lower()
    if sl in names or sl in COMMON270b:
        return stem + "'s"
    if wl in COMMON270b:
        return stem + "'s"
    return stem + "'s"


def _word_runs270b(text: str):
    return [(m.group(1), m.start(1), m.end(1))
            for m in _POSS_RE270.finditer(text)]


def has_possessive270b(text: str, names=None) -> bool:
    """An "Xs <relation>" pattern with no apostrophe in the turn."""
    if "'" in text or "\u2019" in text:
        return False
    names = names or {}
    runs = _word_runs270b(text)
    for (w, _s, _e), (rel, _s2, _e2) in zip(runs, runs[1:]):
        if not w.lower().endswith("s"):
            continue
        if rel.lower() not in _REL270:
            continue
        if _possessive_form270b(w, names) is None:
            continue
        return True
    return False


def _suppressed270b(text: str) -> bool:
    return any(r.search(text) for r in _CHECK_RES270)


def fire270b(text: str, names=None):
    """Why the normaliser fires, or None for passthrough."""
    t = str(text)
    names = names or {}
    if any(c.isupper() for c in t):
        if has_possessive270b(t, names):
            if _suppressed270b(t):
                return None
            return "possessive"
        return None
    if _suppressed270b(t):
        return None
    return "lowercase"


def _possessive_fix270b(text: str, names: dict) -> str:
    runs = _word_runs270b(text)
    fixes = []
    for (w, s, e), (rel, _s2, _e2) in zip(runs, runs[1:]):
        if not w.lower().endswith("s"):
            continue
        if rel.lower() not in _REL270:
            continue
        poss = _possessive_form270b(w, names)
        if poss is None:
            continue
        fixes.append((s, e, poss))
    out = []
    pos = 0
    for s, e, poss in fixes:
        out.append(text[pos:s])
        out.append(poss)
        pos = e
    out.append(text[pos:])
    out = "".join(out)
    for plain, apos in _WH270:
        out = re.sub(r"\b" + plain + r"\b", apos, out,
                     flags=re.IGNORECASE)
    return out


def _cap_word270b(w: str, names: dict) -> str:
    key = w.lower()
    if key in names:
        return names[key]
    if key in COMMON270b:
        return w
    if "'" in w:
        head, sep, tail = w.partition("'")
        if not head:
            return w
        return head[:1].upper() + head[1:] + sep + tail
    return w[:1].upper() + w[1:]


def seen_names_from_text270b(text: str) -> dict:
    """Capitalised content words in a turn -> {lower: StoredForm}.

    Used to seed per-item memory from setup/context turns. Words that are
    common English (or check-tail words) are skipped; first-seen form wins.
    """
    seen: dict = {}
    for m in re.finditer(r"[A-Za-z]+(?:'[A-Za-z]+)?", str(text)):
        w = m.group(0)
        if not any(c.isupper() for c in w):
            continue
        key = w.lower()
        if key in COMMON270b or key in _NEVER_FIX270:
            continue
        seen.setdefault(key, w)
    return seen


def normalise270b(text: str, known_names=None):
    """Rule-based pass. Returns (fixed_text, reason_or_None, ms).

    Returns the input unchanged (same string) when not firing, so clean
    turns behave exactly like 261b's arm A.
    """
    t = str(text)
    names = known_names or {}
    t0 = time.perf_counter()
    reason = fire270b(t, names)
    if reason is None:
        ms = (time.perf_counter() - t0) * 1000.0
        return t, None, round(ms, 4)
    fixed = _possessive_fix270b(t, names)
    fixed = _WORD_RE270.sub(lambda m: _cap_word270b(m.group(0), names),
                            fixed)
    ms = (time.perf_counter() - t0) * 1000.0
    return fixed, reason, round(ms, 4)
