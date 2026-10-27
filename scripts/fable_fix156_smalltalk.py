#!/usr/bin/env python3
"""Experiment 156 -- THE ONE CHANGE: a no-write small-talk stage on loop150.

Base: loop150 (scripts/fable_loop150_agent.py; loop150 = loop129b + 139b
value guard + 150 subject guard; loop150 imported read-only, no file
edited). Red team (exp 152, class N1): every greeting/thanks/lol/ok/bye
gets the generic fallthrough clarify (scripts/fable_loop90_agent.py:291).

THE RULE (cooperative Smalltalk156Mixin, ears hear() only -- the OUTERMOST
layer, so every notebook-path stage below has already run): call
super().hear(turn) first. If the notebook path UNDERSTOOD the message
(anything other than the exact generic fallthrough clarify), return its
actions untouched. Only when the base returns exactly
[{"act": "clarify", "text": FALLTHROUGH_MSG}] is the message tested: after
lower-casing and normalising punctuation, repeated letters and emoji, if
EVERY word is in the closed SMALLTALK_VOCAB below, return one fixed
short clarify reply for its class (greeting / thanks / laugh-ack / bye).
Otherwise return the base actions untouched.

Consequences by construction: 0 writes (clarify acts never reach the
notebook -- AgentLoop._act handles "clarify" with no write,
scripts/fable_agent_loop.py:337-339); messages mixing small talk with
content ("hi, Tom's boss is Bob") keep content words outside the closed
list and are unchanged; "who are you" / "what can you do" contain
who/are/what/can/do (not in the list) and are unchanged for the exp-127
self router; empty/emoji-only input has zero tokens and is unchanged.
"""

from __future__ import annotations

import re

# The generic fallthrough this stage keys on (exact text of the notebook
# path's "did not understand" reply; see scripts/fable_loop90_agent.py:291
# and the FakeEars template at scripts/fable_agent_loop.py:148).
FALLTHROUGH_MSG = ("I didn't understand that. "
                   "Could you say it another way?")

# One fixed short reply per class (sealed; greeting carries one teach
# example and one ask example).
GREETING_REPLY = ("Hi! Teach me like \"Tom's boss is Ann.\" "
                  "Ask me like \"Who is Tom's boss?\"")
THANKS_REPLY = "You're welcome!"
ACK_REPLY = "Got it!"
BYE_REPLY = "Bye!"

CLASS_REPLIES = {"greeting": GREETING_REPLY, "thanks": THANKS_REPLY,
                 "ack": ACK_REPLY, "bye": BYE_REPLY}

# Sealed closed lists (natural spelling; matched AFTER normalize_156, and
# the sets below are stored post-normalisation so "cool"/"coool" both hit).
# One-line reason each: these are discourse glue / politeness particles
# that can never be a taught name, relation, or question word.
GREETING_WORDS = (
    "hi",      # greeting core (covers hii/hiii/hi!! after normalisation)
    "hey",     # greeting core (covers heyyy)
    "hello",   # longer greeting
    "yo",      # short greeting
    "hiya",    # friendly greeting
    "howdy",   # friendly greeting
)
THANKS_WORDS = (
    "thanks",  # thanks core
    "thank",   # "thank you" head
    "thx",     # textspeak thanks (covers thx!!)
    "ty",      # textspeak "thank you" ("ty, very helpful!")
)
BYE_WORDS = (
    "bye",      # bye core (covers byeee/bye!!)
    "byebye",   # doubled bye
    "goodbye",  # formal bye
    "cya",      # textspeak bye
    "night",    # "night" as send-off
)
ACK_WORDS = (
    "lol",      # laugh (covers lolll)
    "lmao",     # stronger laugh
    "haha",     # laugh
    "hahaha",   # long laugh (no letter-run; listed outright)
    "ha",       # short laugh
    "hehe",     # giggle
    "ok",       # acknowledgement (covers okkk)
    "okay",     # acknowledgement
    "k",        # textspeak ack ("k bye"; covers kk)
    "cool",     # approval (covers coool; "cool thanks")
    "nice",     # approval
    "great",    # approval
    "awesome",  # approval
    "yup",      # assent
    "yep",      # assent (covers yeppp)
    "yes",      # assent
    "fine",     # assent
    "sure",     # assent
    "alright",  # assent
)
# Glue words that only ever ride along inside a thanks-flavoured message
# ("thanks so much!", "ty, very helpful!", "cool thanks").
MODIFIER_WORDS = (
    "you",      # "thank you"
    "very",     # "very helpful"
    "much",     # "so much"
    "so",       # "so much"
    "helpful",  # "very helpful"
)

# Deliberately NOT in the list (each would hijack another experiment's
# path): no/wait (bare corrections, N6); who/are/what/can/do/you-are...
# ("who are you"/"what can you do" stay fallthrough for the exp-127 self
# router); btw/also/oh/actually/my (filler teaches, N4 + exp 150);
# who/what/where/is/are (questions); any name or relation word.


def normalize_156(text: str) -> list[str]:
    """Lower-case, collapse letter runs, strip punctuation/emoji -> tokens.

    "hiii" -> "hi"; "heyyy" -> "hey"; "thx!!" -> "thx"; "hi <wave>" ->
    "hi"; "Hi-Fi" -> ["hi", "fi"]; emoji-only -> [] (never small talk).
    """
    low = str(text).lower()
    low = re.sub(r"([a-z])\1+", r"\1", low)  # repeated letters: hiii->hi
    low = re.sub(r"[^a-z0-9]+", " ", low)    # punctuation/emoji -> split
    return [t for t in low.split() if t]


def _norm_set(words: tuple[str, ...]) -> frozenset[str]:
    out: set[str] = set()
    for w in words:
        out.update(normalize_156(w))
    return frozenset(out)


GREETING_TOKENS = _norm_set(GREETING_WORDS)
THANKS_TOKENS = _norm_set(THANKS_WORDS)
BYE_TOKENS = _norm_set(BYE_WORDS)
ACK_TOKENS = _norm_set(ACK_WORDS)
MODIFIER_TOKENS = _norm_set(MODIFIER_WORDS)

SMALLTALK_VOCAB: frozenset[str] = (GREETING_TOKENS | THANKS_TOKENS
                                   | BYE_TOKENS | ACK_TOKENS
                                   | MODIFIER_TOKENS)


def classify_156(text: str) -> str | None:
    """Small-talk class for text, or None (NOT small talk, leave alone).

    Fires only on all-words-in-list input with at least one token.
    Priority: thanks > bye > greeting > ack (so "cool thanks" is thanks,
    "k bye" is bye, "ok cool" is ack).
    """
    toks = normalize_156(text)
    if not toks:
        return None
    if any(t not in SMALLTALK_VOCAB for t in toks):
        return None
    if any(t in THANKS_TOKENS for t in toks):
        return "thanks"
    if any(t in BYE_TOKENS for t in toks):
        return "bye"
    if any(t in GREETING_TOKENS for t in toks):
        return "greeting"
    return "ack"


def is_fallthrough(actions) -> bool:
    """True iff the notebook path did not understand the message."""
    return (isinstance(actions, list) and len(actions) == 1
            and isinstance(actions[0], dict)
            and actions[0].get("act") == "clarify"
            and actions[0].get("text") == FALLTHROUGH_MSG)


def smalltalk_actions(text: str, base_actions: list[dict]) -> list[dict]:
    """Apply the stage: class reply on fallthrough+small-talk, else base."""
    if not is_fallthrough(base_actions):
        return base_actions
    cls = classify_156(text)
    if cls is None:
        return base_actions
    return [{"act": "clarify", "text": CLASS_REPLIES[cls]}]


class Smalltalk156Mixin:
    """Stackable mixin: no-write small-talk stage, outermost ears layer.

    Cooperative (super() first): on ears it runs after the whole loop150
    chain (129 strip + 139b value screen + 150 subject guard), and only
    rewrites the exact generic fallthrough. Loop-level _act needs no
    override: the stage emits clarify acts, which never write.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        return smalltalk_actions(str(turn), actions)
