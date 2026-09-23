#!/usr/bin/env python3
"""Exp 280b -- THE ONE CHANGE: catch every general ability question.

Base: 280 (scripts/claude_loop280_agent.py, read-only) + its sealed
CAN280 text (scripts/claude_fix280_capab.py, read-only, imported).

DIAGNOSIS (280's registered FAIL, artifacts/claude-capab280-20260923/):
280's honest text only fires for a closed 16-form set; wordings outside
that set keep 260's clarify line (M1b 9/12).

THE RULE (outermost instance turn wrapper turn280b over turn280):
A turn is a general ability question when ALL of these hold:
  1. question-shaped (ends with "?" or starts with a question/ask word,
     or starts with "tell me"/"list"), and
  2. addresses the assistant (a you/u/your/yourself token), and
  3. contains an ability cue (can, able, good at, capable, help,
     abilities, skills, "what do you do", purpose, or what...for), and
  4. names no stored or new entity and no relation word, and
  5. is not negated (not/n't/never/cannot/unable: "What can't you do?"
     stays on 280's CANNOT sheet), and
  6. is not a "Can you <specific thing>?" turn: a can/could + you/u led
     turn is general only when the remainder after that prefix is
     itself general (e.g. "can you tell me what you can do").
Such turns get 280's sealed CAN280 text with 0 writes. Everything else
passes through byte-identical, so "Can you <specific>?", near-misses
("What can Mira do?", "What is Tomas good at?", "Ana can swim."),
teaches, asks and the notebook are untouched.
Slang/typo tolerance: a small slang map plus edit-distance-1 matching
for cue words of length >= 4 (short words match exactly).
"""

from __future__ import annotations

import re

import claude_fix280_capab as F280  # noqa: E402 (read-only: CAN280 text)

CAN280B = F280.CAN280

# Leading words dropped (at most 2) before the rule match, as on 280,
# plus assistant vocatives (a real person may lead with the name).
OPENER280B = frozenset(set(F280.OPENER280) | {
    "premonition", "assistant", "chatbot", "bot",
})

# First-word question/ask shapes (after slang normalisation).
SHAPED280B = frozenset({
    "what", "how", "which", "who", "when", "where", "why", "whose",
    "whom", "can", "could", "do", "does", "did", "are", "is", "will",
    "would", "shall", "have", "has", "tell", "list", "describe", "say",
    "explain",
})

# Multi-word statement openers that still ask about abilities
# ("wordings as varied as real people type").
WANT280B = (
    ("i", "want", "to", "know"),
    ("i", "wonder"),
    ("i", "d", "like", "to", "know"),
)
# Second-person tokens (after normalisation).
YOU280B = frozenset({
    "you", "u", "your", "yours", "yourself", "youre", "youve",
    "youll", "youd",
})

# Single-token ability cues (exact match; slang map + fuzz below).
CUE280B = frozenset({
    "can", "able", "capable", "help", "ability", "abilities",
    "skill", "skills", "purpose",
})

# Slang / typo normalisation (whole tokens only).
SLANG280B = {
    "u": "you", "ur": "your", "ure": "your", "r": "are",
    "wat": "what", "wot": "what", "whut": "what", "wut": "what",
    "wht": "what", "teh": "the", "pls": "please", "plz": "please",
    "yuo": "you", "oyu": "you", "yoru": "your", "cna": "can",
    "gud": "good", "hlep": "help", "skils": "skills",
    "skil": "skill", "abilitiy": "ability", "abilitie": "ability",
    "ablities": "abilities", "capble": "capable",
}

# Negation tokens: such turns stay on 280's sheets.
NEG280B = frozenset({"not", "never", "cannot", "unable", "incapable",
                     "without"})

# Relation words: the store's possessive-relation vocabulary and close
# kin. A turn naming one is about a fact, not about abilities.
REL280B = frozenset({
    "mother", "father", "sister", "brother", "friend", "boss",
    "teacher", "wife", "husband", "neighbour", "neighbor", "partner",
    "mentor", "employer", "employee", "colleague", "coworker",
    "sibling", "parent", "child", "son", "daughter", "cousin",
    "uncle", "aunt", "nephew", "niece",
    "cat", "cats", "dog", "dogs", "pet", "pets", "bird", "fish",
    "boat", "band", "street", "city", "cities", "town", "village",
    "country", "job", "jobs", "work", "works", "employer",
    "company", "school", "team", "car", "house", "home",
    "name", "names", "named", "called", "age", "color", "colour",
    "food", "movie", "book", "song", "toy", "game", "sport",
    "doctor", "lawyer", "nurse", "pilot", "driver", "mason",
    "clerk", "steward", "cooper", "wright", "cook", "baker",
    "tinker", "smith", "dyer",
    "live", "lives", "born", "birth", "birthday", "address",
    "favorite", "favourite",
})

# Assistant-address words: never count as entities.
SELF280B = frozenset({"premonition", "assistant", "chatbot", "bot",
                      "ai"})

# First-token skips for the capitalised-name scan.
IWORDS280B = frozenset({"i", "im", "ive", "ill", "id", "ok", "okay"})

_CONTRACTIONS = (("can't", "can n't"), ("couldn't", "could n't"),
                 ("won't", "will n't"), ("n't", " n't"),
                 ("'re", " re"), ("'ve", " ve"), ("'ll", " ll"),
                 ("'d", " d"), ("'m", " m"))


def _lev1(a: str, b: str) -> bool:
    """True if edit distance between a and b is <= 1."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        return sum(1 for x, y in zip(a, b) if x != y) <= 1
    if la < lb:
        a, b = b, a
        la, lb = lb, la
    for i in range(la):
        if a[:i] + a[i + 1:] == b:
            return True
    return False


def _toks(text: str) -> list[str]:
    t = str(text).lower().replace("\u2019", "'").replace("\u2018", "'")
    for k, v in _CONTRACTIONS:
        t = t.replace(k, v)
    t = re.sub(r"[^a-z0-9' ]", " ", t)
    return [w for w in t.split(" ") if w]


def _norm_toks(text: str) -> list[str]:
    return [SLANG280B.get(w, w) for w in _toks(text)]


def _strip_openers(words: list[str]) -> list[str]:
    n = 0
    while n < 2 and words and words[0].rstrip(",") in OPENER280B:
        words = words[1:]
        n += 1
    return words


def _has_cue(words: list[str]) -> bool:
    s = set(words)
    for w in words:
        if w in CUE280B:
            return True
        if len(w) >= 4:
            for c in ("able", "capable", "help", "ability",
                      "abilities", "skill", "skills", "purpose"):
                if _lev1(w, c):
                    return True
    if "good" in s or any(len(w) >= 3 and _lev1(w, "good")
                           for w in words):
        if "at" in s:
            return True
    if "what" in s and "for" in s:
        return True
    for i, w in enumerate(words):
        if w != "what":
            continue
        for j in range(i + 1, len(words)):
            if words[j] not in YOU280B:
                continue
            if "do" in words[j + 1:]:
                return True
    return False


def _stored_names(loop) -> set[str]:
    try:
        nb = getattr(loop, "nb", None)
        trips = []
        for o in (nb, getattr(nb, "nb", None)):
            if o is not None and hasattr(o, "events"):
                for ev in o.events:
                    trips.append(getattr(ev, "triple", None))
        names: set[str] = set()
        for t in trips:
            if not t:
                continue
            try:
                parts = list(t)
            except TypeError:
                continue
            for p in parts:
                for w in str(p).lower().split():
                    if len(w) >= 3:
                        names.add(w)
        return names
    except Exception:  # noqa: BLE001
        return set()


def _has_entity(orig_text: str, words: list[str], loop) -> bool:
    if "'" in " ".join(words):
        return True
    if loop is not None:
        stored = _stored_names(loop)
        if stored:
            you_free = [w for w in words if w not in YOU280B]
            if any(w in stored for w in you_free):
                return True
    caps = re.findall(r"[A-Za-z][A-Za-z'\u2019\-]*", str(orig_text))
    for i, c in enumerate(caps):
        if i == 0:
            continue
        cl = c.lower().replace("\u2019", "'")
        if cl in IWORDS280B or cl in OPENER280B or cl in SELF280B:
            continue
        if c[:1].isupper():
            return True
    return False


def _rule_general(words: list[str], orig_text: str, loop) -> bool:
    if not words:
        return False
    if any(w in NEG280B or w.endswith("n't") for w in words):
        return False
    shaped = (str(orig_text).strip().endswith("?") or words[0] in SHAPED280B
              or any(tuple(words[:len(p)]) == p for p in WANT280B))
    if not shaped:
        return False
    if not any(w in YOU280B for w in words):
        return False
    if not _has_cue(words):
        return False
    if any(w in REL280B for w in words):
        return False
    if _has_entity(orig_text, words, loop):
        return False
    return True


def is_general280b(text: str, loop=None) -> bool:
    """True when a turn is a general ability question per the 280b rule."""
    if F280.is_general280(text):
        return True
    words = _strip_openers(_norm_toks(text))
    if not words:
        return False
    if (words[0] in ("can", "cannot", "could") and len(words) > 1
            and words[1] in ("you", "u")):
        rest = words[2:]
        return _rule_general(rest, text, loop)
    return _rule_general(words, text, loop)


def install_general280b(loop):
    """Install the 280b layer on a built 280 loop (outermost, instance)."""
    inner_turn = loop.turn            # turn280(turn260(...))
    loop.turn280b_inner = inner_turn
    loop.general280b_log = []

    def turn280b(text: str) -> list[str]:
        t = str(text)
        if is_general280b(t, loop):
            loop.general280b_log.append({"pre": t})
            return [CAN280B]
        return list(inner_turn(t))

    turn280b.__name__ = "turn280b"
    loop.turn = turn280b
    return loop
