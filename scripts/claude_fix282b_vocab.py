#!/usr/bin/env python3
"""Exp 282b -- THE ONE CHANGE: small talk by vocabulary, not word order.

Base: 282 (scripts/claude_loop282_agent.py + its config, read-only).
New file only. Outermost instance turn wrapper turn282b over turn282.

DIAGNOSIS (282's registered FAIL: 31/35 writer greeting+closing fitting,
bar 32/35; the 4 remaining turns abstain on both arms as shapes outside
282's closed word-order grammar; 282's known limits: opener-prefixed
small talk keeps 260's route, "how are you" shapes untouched):
a whole turn is small talk when EVERY word, after lowercasing and
stripping punctuation and emoji, belongs to a sealed small-talk
vocabulary. The closed grammar cannot see fillers mid-turn ("hey man
whats up"), opener words ("oh hey there"), "how are you" words next to
a greeting ("hiya how are you"), or emoji tails; the vocabulary test
does, while any fact or question content (entity or relation words)
fails the vocabulary test, so mixed turns keep 282's route exactly.

THE RULE (turn282b, outermost, instance):
  1. normalize_282b: lower-case, fold curly quotes, drop apostrophes,
     collapse letter runs of 3+ ("heyyy" -> "hey"), split on
     non-letters (punctuation, emoji and digits all split).
  2. Every token must belong to the sealed VOCAB282B (greetings,
     thanks, closings, "how are you" words, fillers, the assistant's
     own name "premonition"); the turn must hold at least one
     greeting, thanks or closing word; it must name no stored entity
     (notebook subject or value, incl. apostrophe-less possessive
     stems) and no relation word (single or adjacent-pair surface
     from fable_listening_english.RELATION_MAP). Class = the first
     greeting/thanks/closing word.
  3. The original turn runs first through the whole head (282's turn).
     If it wrote, or its reply is already not an error reply, its
     reply stands.
  4. Else the head's own canonical reply for the class is used:
     greet -> "Hello.", thanks -> "Thanks!", close -> "Bye." The
     canonical probe runs through the whole head with the pre-turn
     state restored; if it writes or is itself an error reply, the
     state after the original run is restored and the original reply
     stands.
Net effect: the only moves vs 282 are whole-turn pure-small-talk
turns that 282 mishandles -> the head's own small-talk reply;
everything else is byte-identical to 282, with identical stores.
"""

from __future__ import annotations

import re

import claude_fix260_openers as F260  # noqa: E402 (read-only helpers)
import claude_fix282_small as F282  # noqa: E402 (error test, read-only)
import fable_listening_english as LE  # noqa: E402 (relation surfaces)
import fable_loop90_agent as L90  # noqa: E402 (read-only triple reader)


def normalize_282b(text: str) -> list[str]:
    """Lower-case, fold curly quotes, drop apostrophes, collapse letter
    runs of 3+ ("heyyy" -> "hey"), split on non-letters (this strips
    punctuation, emoji and digits)."""
    low = str(text).lower().replace("\u2019", "'").replace("\u2018", "'")
    low = low.replace("'", "")
    low = re.sub(r"([a-z])\1{2,}", r"\1", low)
    low = re.sub(r"[^a-z]+", " ", low)
    return low.split()


# Sealed small-talk vocabulary (all lowercase; matched on normalized
# tokens). Class words carry greet/thanks/close; the rest are neutral
# ("how are you" words, fillers, joiners, the assistant's own name).
_GREET282B = (
    "hi", "hey", "hello", "hiya", "heya", "howdy", "yo", "yoo",
    "greetings", "morning", "afternoon", "evening", "day",
    "sup", "whatsup", "wassup", "wazzup", "wazup", "wasup",
    "whats", "happening",
    "heyy", "hii", "helloo",
)
_THANKS282B = (
    "thanks", "thank", "thankyou", "thanx", "thankss",
    "thx", "ty", "cheers",
)
_CLOSE282B = (
    "bye", "byee", "goodbye", "goodnight", "goodnite", "nite",
    "night", "nighty", "gnite", "later", "soon", "farewell", "adios",
    "cya", "seeya",
)
_NEUTRAL282B = (
    # "how are you" words
    "how", "are", "you", "u", "doing", "today", "feeling",
    # casual cores' companion words
    "going", "on", "new", "up", "good",
    # fillers and joiners
    "so", "ok", "okay", "okey", "soo", "lol", "man", "dude",
    "bro", "mate", "buddy", "pal", "again", "all", "for",
    "now", "much", "very", "lot", "bunch", "many", "cool",
    "great", "awesome", "a", "and", "too", "ever", "of",
    "your", "help", "everything", "kind", "hope", "well",
    "glad", "nice", "one", "have",
    # opener / discourse words
    "oh", "ah", "ooh", "um", "umm", "uh", "uhh", "right",
    "anyway", "anyways", "alright", "please", "just",
    "say", "saying",
    # closing companion words
    "see", "ya", "talk", "take", "gotta", "go", "care",
    "to", "lets", "catch", "till", "until",
    "thats", "that", "is", "it", "there",
    # the assistant's own name (identity sheet: 'My name is
    # Premonition.')
    "premonition",
)

VOCAB282B = frozenset(_GREET282B + _THANKS282B + _CLOSE282B
                      + _NEUTRAL282B)

_CLASS282B: dict = {}
for _w in _GREET282B:
    _CLASS282B.setdefault(_w, "greet")
for _w in _THANKS282B:
    _CLASS282B.setdefault(_w, "thanks")
for _w in _CLOSE282B:
    _CLASS282B.setdefault(_w, "close")

# Relation surfaces (single tokens and adjacent pairs, normalized the
# same way: lowercase, apostrophes dropped). By construction none of
# these is in VOCAB282B (asserted in pilot); the check stays as a
# backstop so a turn naming a relation can never match.
_REL1_282B = frozenset(
    k for k in (kk.replace("'", "").lower() for kk in LE.RELATION_MAP)
    if " " not in k) | frozenset(
    r.lower() for r in LE.KNOWN_RELATIONS)
_REL2_282B = frozenset(
    k for k in (kk.replace("'", "").lower() for kk in LE.RELATION_MAP)
    if " " in k)


def known_store282b(loop):
    """(subjects, values): lowercase notebook subjects and stored value
    words right now."""
    try:
        triples = L90.notebook_triples(loop.nb)
    except Exception:  # noqa: BLE001
        return {}, set()
    subjects, values = {}, set()
    for t in triples or []:
        try:
            s, _r, v = str(t[0]), str(t[1]), str(t[2])
        except Exception:  # noqa: BLE001
            continue
        subjects.setdefault(" ".join(s.lower().split()), s)
        for w in str(v).lower().replace("'", " ").split():
            if w:
                values.add(w)
    return subjects, values


def _names_entity282b(tok: str, subjects: dict, values: set) -> bool:
    if tok in subjects or tok in values:
        return True
    m = re.match(r"^([a-z]+)s$", tok)
    if m is not None and len(m.group(1)) >= 2 \
            and m.group(1) in subjects:
        return True  # apostrophe-less possessive of a known subject
    return False


def classify_small282b(text: str, subjects=None, values=None):
    """'greet' | 'thanks' | 'close' if the whole turn is pure small
    talk by the vocabulary test, else None. Class = the first
    greeting/thanks/closing word. Any entity or relation content
    fails, so mixed turns always keep 282's route."""
    toks = normalize_282b(text)
    if not toks:
        return None
    if any(t not in VOCAB282B for t in toks):
        return None
    subjects = {} if subjects is None else subjects
    values = set() if values is None else values
    if any(_names_entity282b(t, subjects, values) for t in toks):
        return None
    if any(t in _REL1_282B for t in toks):
        return None
    if any(" ".join(toks[i:i + 2]) in _REL2_282B
           for i in range(len(toks) - 1)):
        return None
    for t in toks:
        if t in _CLASS282B:
            return _CLASS282B[t]
    return None


# Canonical probes: the head's own small-talk reply for each class.
PROBE282B = {"greet": "Hello.", "thanks": "Thanks!", "close": "Bye."}


def install_small282b(loop):
    """Install the 282b layer on a built 282 loop (outermost, instance)."""
    inner_turn = loop.turn            # turn282(turn260(...))
    loop.turn282b_inner = inner_turn
    loop.small282b_log = []

    def turn282b(text: str) -> list[str]:
        t = str(text)
        subjects, values = known_store282b(loop)
        cls = classify_small282b(t, subjects, values)
        if cls is None:
            return inner_turn(t)
        s0 = F260.snapshot260(loop)
        e0 = F260._nb_events(loop)
        r0 = list(inner_turn(t))
        if F260._nb_events(loop) != e0:
            return r0                 # a write: keep the original
        if not F282.is_error_reply282(r0):
            return r0                 # already small talk: keep it
        s1 = F260.snapshot260(loop)
        F260.restore260(s0)
        r1 = list(inner_turn(PROBE282B[cls]))
        wrote = F260._nb_events(loop) != e0
        if wrote or F282.is_error_reply282(r1):
            F260.restore260(s1)
            return r0                 # canonical failed: 282's route stands
        loop.small282b_log.append({"turn": t, "class": cls})
        return r1

    turn282b.__name__ = "turn282b"
    loop.turn = turn282b
    return loop
