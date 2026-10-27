#!/usr/bin/env python3
"""Exp 282 -- THE ONE CHANGE: casual greetings and closings get small talk.

Base: 260 (scripts/claude_loop260_agent.py, read-only). New file only.

DIAGNOSIS (reproduced live on 260; the probe's own rows are
artifacts/claude-chatweak-20260923/dialogs.json t07-t0 and t01-t7):
  - "hey whats up" gets "I didn't understand that question ..." while bare
    "hey" already gets the head's greeting reply.
  - "Thanks, that's all!" gets "I didn't understand that well enough to
    save it ..." while bare "Thanks!" already gets "You're welcome!".
  - Same boundary on 260: "whats up" / "wassup" / "sup", "whats new" /
    "whats good", "cheers", "many thanks", "talk later" / "gotta go",
    "good day", "greetings", bare "that's all" / "that's it", pure
    "bye for now", and caps/run-on/punctuated variants ("HEY WHATS UP",
    "heyyy whats uppp", "hey... whats up?") all get a clarify, a
    save-failure line, or a mode-status line instead of small talk.
  - Already fine on 260 and must not move: "hey", "hey there", "thanks",
    "thank you", "thx", "ty", "ok thanks", "thanks so much",
    "cool thanks bye", "see ya" / "see you" / "goodbye" / "good night",
    "Bye.", "Hello.", "how are you" (234 fixed reply).

THE RULE (outermost instance turn wrapper turn282 over turn260):
  1. A closed whole-turn grammar (below) recognises pure small talk in
     three classes: greet (greetings + casual greeting cores, lowercase /
     no apostrophe / no end mark tolerant), thanks (thanks forms plus
     short closing tails), close (pure closings). Only turns whose every
     token parses match; any turn with fact or question content keeps
     260's route exactly (mixed items can never match).
  2. The original turn runs first through the whole head. If it wrote, or
     its reply is already not an error reply (clarify / save-failure /
     abstain / mode-status), its reply stands.
  3. Else the head's own canonical small-talk reply for the class is used:
     greet -> the head's reply to "Hello.", thanks -> to "Thanks!",
     close -> to "Bye." The canonical probe runs through the whole head
     with the pre-turn state restored; if it writes or is itself an error
     reply, the state after the original run is restored and the original
     reply stands. Net effect: the only moves are pure-small-talk turns
     that 260 mishandled -> the head's own small-talk reply; everything
     else is byte-identical to 260, with identical stores.
  4. Questions never write through this layer (a written canonical run is
     undone); teaches are untouched (a teach-shaped turn can never match
     the grammar, and a written original run is always kept).
"""

from __future__ import annotations

import re

import claude_fix260_openers as F260  # noqa: E402 (read-only helpers)


def normalize_282(text: str) -> list[str]:
    """Lower-case, fold curly quotes, drop apostrophes, collapse letter
    runs of 3+ ("heyyy" -> "hey"), split on non-letters."""
    low = str(text).lower().replace("\u2019", "'").replace("\u2018", "'")
    low = low.replace("'", "")
    low = re.sub(r"([a-z])\1{2,}", r"\1", low)
    low = re.sub(r"[^a-z]+", " ", low)
    return low.split()


# Greeting openers (bare "hey" / "good morning" style turns).
GREET_SEQS282 = [
    ("good", "morning"), ("good", "afternoon"), ("good", "evening"),
    ("good", "day"),
    ("hi",), ("hey",), ("hello",), ("hiya",), ("heya",), ("howdy",),
    ("yo",), ("greetings",), ("morning",), ("afternoon",), ("evening",),
]
GREET_TAIL282 = ("there", "again")

# Casual greeting cores (slang / lowercase / no-punctuation tolerant).
CASUAL_CORES282 = [
    ("whats", "going", "on"), ("whats", "happening"),
    ("whats", "up"), ("whats", "new"), ("whats", "good"), ("whats", "on"),
    ("how", "is", "it", "going"), ("hows", "it", "going"),
    ("hows", "things"), ("hows", "life"),
    ("just", "saying", "hi"), ("just", "saying", "hello"),
    ("just", "saying", "hey"), ("saying", "hi"), ("saying", "hello"),
    ("good", "to", "see", "you"),
    ("wassup",), ("wazzup",), ("wazup",), ("wasup",), ("whatsup",),
    ("sup",),
]

# Thanks forms.
THANKS282 = [
    ("thank", "you", "so", "much"), ("thank", "you", "very", "much"),
    ("thank", "you", "again"), ("thank", "you"),
    ("thanks", "a", "lot"), ("thanks", "so", "much"),
    ("thanks", "a", "bunch"), ("thanks", "again"),
    ("many", "thanks"),
    ("cool", "thanks"), ("ok", "thanks"), ("okay", "thanks"),
    ("great", "thanks"), ("awesome", "thanks"),
    ("thanks",), ("thankyou",), ("thx",), ("ty",), ("cheers",),
]

# Short closing tails (with a thanks form, or alone as a pure closing).
CLOSE_TAILS282 = [
    ("that", "is", "all"), ("that", "is", "it"),
    ("thats", "all"), ("thats", "it"),
    ("bye", "for", "now"), ("see", "you", "later"),
    ("talk", "to", "you", "later"), ("catch", "you", "later"),
    ("see", "ya"), ("see", "you"), ("see", "u"),
    ("good", "night"), ("talk", "later"), ("take", "care"),
    ("gotta", "go"), ("ok", "bye"), ("okay", "bye"),
    ("goodbye",), ("goodnight",), ("bye", "bye"), ("bye",),
]

# Optional casual prefix before a thanks/closing core ("ok that's all").
OPENER_PREFIX282 = ("ok", "okay", "well", "so", "um", "umm", "uh", "uhh",
                    "oh", "right", "anyway", "anyways", "alright", "please")

_GREET_SEQS282 = sorted(GREET_SEQS282, key=len, reverse=True)
_CORES282 = sorted(CASUAL_CORES282, key=len, reverse=True)
_THANKS282 = sorted(THANKS282, key=len, reverse=True)
_TAILS282 = sorted(CLOSE_TAILS282, key=len, reverse=True)


def _match_at(toks: list[str], i: int, seqs) -> int:
    for s in seqs:
        n = len(s)
        if tuple(toks[i:i + n]) == s:
            return n
    return 0


def classify_small282(text: str):
    """'greet' | 'thanks' | 'close' if the whole turn is pure small talk
    of that class, else None. Any fact or question content fails to parse
    (no match), so mixed turns always keep 260's route."""
    toks = normalize_282(text)
    if not toks:
        return None
    i, n = 0, len(toks)
    pi = 0
    while pi < 2 and i < n and toks[i] in OPENER_PREFIX282:
        i += 1
        pi += 1
    greeted = False
    while True:
        k = _match_at(toks, i, _GREET_SEQS282)
        if not k:
            break
        greeted = True
        i += k
        while i < n and toks[i] in GREET_TAIL282:
            i += 1
    thanks = False
    k = _match_at(toks, i, _THANKS282)
    if k:
        thanks = True
        i += k
    core = False
    if not thanks:
        k = _match_at(toks, i, _CORES282)
        if k:
            core = True
            i += k
    closed = False
    while True:
        k = _match_at(toks, i, _TAILS282)
        if not k:
            break
        closed = True
        i += k
    if i != n:
        return None
    if thanks:
        return "thanks"
    if greeted or core:
        return "greet"
    if closed:
        return "close"
    return None


# Canonical probes: the head's own small-talk reply for each class.
PROBE282 = {"greet": "Hello.", "thanks": "Thanks!", "close": "Bye."}

# An original reply that mishandles small talk: clarify glue, honest
# abstains, save-failure lines, and the mode-status line. Anything else
# (a small-talk reply, a stored answer, a save confirmation) stands.
_ERROR282 = (F260.CLARIFY_MARKS260
             + ("was that a question",)
             + ("don't know", "do not know", "never told me",
                "never taught me", "no record",
                "not someone i can look up")
             + ("listening mode", "waiting for your next turn"))


def is_error_reply282(reply_lines) -> bool:
    text = " ".join(str(x) for x in (reply_lines or [])).lower()
    if not text.strip():
        return True
    return any(m in text for m in _ERROR282)


def install_small282(loop):
    """Install the 282 layer on a built 260 loop (outermost, instance)."""
    inner_turn = loop.turn            # turn260(turn224c(...))
    loop.turn282_inner = inner_turn
    loop.small282_log = []

    def turn282(text: str) -> list[str]:
        t = str(text)
        cls = classify_small282(t)
        if cls is None:
            return inner_turn(t)
        s0 = F260.snapshot260(loop)
        e0 = F260._nb_events(loop)
        r0 = list(inner_turn(t))
        if F260._nb_events(loop) != e0:
            return r0                 # a write: keep the original
        if not is_error_reply282(r0):
            return r0                 # already small talk: keep it
        s1 = F260.snapshot260(loop)
        F260.restore260(s0)
        r1 = list(inner_turn(PROBE282[cls]))
        wrote = F260._nb_events(loop) != e0
        if wrote or is_error_reply282(r1):
            F260.restore260(s1)
            return r0                 # canonical failed: 260's route stands
        loop.small282_log.append({"turn": t, "class": cls})
        return r1

    turn282.__name__ = "turn282"
    loop.turn = turn282
    return loop
