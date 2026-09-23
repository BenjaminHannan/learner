#!/usr/bin/env python3
"""Experiment 171 -- THE ONE CHANGE: a teach whose value must be a NAME but
is not name-shaped writes nothing and gets one sealed clarify.

Wrong-write class (director probe 07:55 on loop138b AND loop138d, same
replies): "Kim's mom is sick." -> "Saved: Kim's mom is sick." (and boss is
mean / sister is tall / dog is brown / mother is a nurse / friend is here /
boss is away today -> offers to change the boss; "Who is Kim's dog?" ->
"Kim's dog is brown."). On loop166 "My mom is sick." -> "Saved: your mother
is sick." 8/8 such turns saved junk. These are the most natural phone-chat
sentences, so this is a wrong-write class.

Rule: for relations whose value must be a NAME (NAME_KEYS below), a teach
(or correct) whose value is not name-shaped writes nothing and replies with
the one sealed clarify CLARIFY_PREFIX + "What is {Name}'s {relation}'s
name?" ("your ..." when the subject is the USER key, which the 138d base
never produces -- branch kept for the sealed form).

Not name-shaped = the value's first word (lowercased, surrounding punct
stripped) is in WORDS (the sealed wordlist171.txt = lowercase entries of
/usr/share/dict/words minus the sealed givennames171.txt; sha256 of both
files is written into the artifact SEAL.sha256.txt), OR in DETERMINERS
(a, an, the, my, his, her, ...), OR in PLACE_TIME_ADVERBS (here, there,
away, home, today, ...). A lowercase word NOT in WORDS (ana, priya, ...)
keeps today's behaviour exactly. Relations NOT on the name list (job,
occupation, pet, city, colour, food, ...) keep today's behaviour exactly.

No existing file is edited. Base modules are imported read-only. The mixin
is cooperative (super-first): hear() rewrites refused teach/correct actions
to clarify AFTER the inner chain runs; _act() re-checks just before the
write (same shape as the exp-139b value guard).
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ART171 = SCRIPTS.parent / "artifacts" / "fable-nameval171-20260922"

# Canonical relation keys (FakeEars._relation: lowercase, spaces -> "_")
# whose value must be a NAME. One-line reason each (see design doc 171):
NAME_KEYS = frozenset({
    "mother",    # a mother is a person, identified by name
    "father",    # a father is a person, identified by name
    "mom",       # parser key for mom/Mom (distinct from mother)
    "dad",       # parser key for dad/Dad (distinct from father)
    "mum",       # parser key for mum/Mum, common mother surface
    "daddy",     # parser key for daddy/Daddy, common father surface
    "sister",    # a sister is a person, identified by name
    "brother",   # a brother is a person, identified by name
    "sibling",   # a sibling is a person, identified by name
    "boss",      # a boss is a person, identified by name
    "friend",    # a friend is a person, identified by name
    "spouse",    # a spouse is a person, identified by name
    "wife",      # a wife is a person, identified by name
    "husband",   # a husband is a person, identified by name
    "child",     # a child is a person, identified by name
    "son",       # a son is a person, identified by name
    "daughter",  # a daughter is a person, identified by name
    "teacher",   # a teacher is a person, identified by name
    "colleague", # a colleague is a person, identified by name
    "dog",       # a dog is a named animal, identified by name
    "cat",       # a cat is a named animal, identified by name
})

# Sealed article/determiner/modifier stoplist (first word, lowercased).
DETERMINERS = frozenset({
    "a", "an", "the", "my", "his", "her", "its", "our", "their", "your",
    "this", "that", "these", "those",
    "very", "so", "really", "quite", "too", "rather", "somewhat", "fairly",
    "pretty", "much", "more", "most",
    "not", "still", "always", "never", "just", "no", "some", "any", "such",
    "own", "same", "other", "another", "each", "every", "few", "several",
    "both",
})

# Sealed place/time adverb list (the value, or its first word, lowercased).
PLACE_TIME_ADVERBS = frozenset({
    "here", "there", "away", "home", "today", "yesterday", "tomorrow",
    "inside", "outside", "upstairs", "downstairs", "abroad", "nearby",
    "elsewhere", "everywhere", "nowhere", "somewhere", "anywhere",
    "indoors", "outdoors",
})

# Sealed clarify prefix (exact form; the question part names subject+relation).
CLARIFY_PREFIX = ("That sounds like a description, not a name, "
                  "so I didn't save it. ")

_WORDS: frozenset | None = None


def WORDS() -> frozenset:
    """Sealed common-word set: wordlist171.txt (dict minus given names)."""
    global _WORDS
    if _WORDS is None:
        text = (ART171 / "wordlist171.txt").read_text(encoding="utf-8")
        _WORDS = frozenset(w.strip() for w in text.splitlines()
                           if w.strip())
    return _WORDS


def first_word(value: object) -> str:
    """Lowercased first word of the value, surrounding punct stripped."""
    text = " ".join(str(value).split())
    if not text:
        return ""
    tok = text.split()[0]
    return tok.strip(".,;:!?\"'`()[]{}").lower()


def is_description_value(value: object) -> bool:
    """True when the value is not name-shaped (writes nothing)."""
    first = first_word(value)
    if not first:
        return False
    if first in DETERMINERS:
        return True
    if first in PLACE_TIME_ADVERBS:
        return True
    return first in WORDS()


def clarify_for(name: object, relation: object) -> str:
    """The one sealed clarify text for a refused name-valued teach."""
    rel_disp = str(relation).replace("_", " ")
    if str(name) == "USER":
        return (CLARIFY_PREFIX
                + f"What is your {rel_disp}'s name?")
    return (CLARIFY_PREFIX
            + f"What is {name}'s {rel_disp}'s name?")


def screen_name_value(name: object, relation: object,
                      value: object) -> str | None:
    """Clarify message when a name-relation teach value must not write.

    Returns None when the value may be stored as-is (name-shaped, or the
    relation is not a name relation).
    """
    if str(relation) not in NAME_KEYS:
        return None
    if is_description_value(value):
        return clarify_for(name, relation)
    return None


def guard_action(action: dict) -> dict:
    """teach/correct with a refused name value -> sealed clarify; else copy."""
    if not isinstance(action, dict):
        return action
    if action.get("act") not in ("teach", "correct"):
        return action
    msg = screen_name_value(action.get("name"), action.get("relation"),
                            action.get("value", ""))
    if msg is not None:
        return {"act": "clarify", "text": msg}
    return action


def guard_actions(actions: list[dict]) -> list[dict]:
    return [guard_action(a) for a in list(actions)]


class NameVal171Mixin:
    """Stackable mixin: refuse description values on name relations.

    Cooperative (super() first): on ears it runs after the base hear (so
    every inner guard has already run); on the loop it re-checks just
    before the write (covers structured/delegate paths). Same shape as
    ValueGuard139BMixin; only the screen differs.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        return guard_actions(actions)

    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if isinstance(action, dict) and action.get("act") in (
                "teach", "correct"):
            msg = screen_name_value(action.get("name"),
                                    action.get("relation"),
                                    action.get("value", ""))
            if msg is not None:
                self.counters["clarifications"] += 1  # type: ignore[attr-defined]
                return {"kind": "clarify", "text": msg}
        return super()._act(action)  # type: ignore[misc]
