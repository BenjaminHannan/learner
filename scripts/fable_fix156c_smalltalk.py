#!/usr/bin/env python3
"""Experiment 156c -- THE ONE CHANGE: wider small-talk classes on loop138h.

Base: loop138h (scripts/fable_loop138h_agent.py, imported read-only, no
file edited). Loop138h already carries the 156b small-talk classes inside
its 138f stack (Smalltalk156bMixin in Loop138fEars), so "Hi!",
"Good morning.", "Thanks!", "Bye!", "Hey you", "See you later.",
"Good night." already answer. Everyday turns still fall through to the
generic clarify: greetings with a trailing word ("Hello there."),
the how-are-you family ("How are you?", "How's it going?", "What's up?"),
weather/idle chat ("Nice weather today.", "It's cold out."), and
first-person feeling statements ("I'm tired.", "I'm happy today.").

THE RULE (cooperative Smalltalk156cMixin, ears hear() only -- the
OUTERMOST layer, so every notebook-path stage below, including 156b's,
has already run): call super().hear(turn) first. If the notebook path
UNDERSTOOD the message (anything other than the exact generic
fallthrough clarify), return its actions untouched. Only when the base
returns exactly [{"act": "clarify", "text": FALLTHROUGH_MSG}] is the
message tested against the closed anchored phrase sets below; on a full-
message match, return one fixed short clarify reply for its class.
Otherwise return the base actions untouched.

Closed and rule-based: every class is an exact normalized full-message
match (no learned weights, nothing tuned to any panel). Normalisation:
lower-case, unify "i am"->"im" and "it is"->"its", punctuation (incl.
apostrophes left over after the contraction guard) turned into word
splits, whitespace collapsed. Fact teaches and questions about stored
facts can never match: (a) anything the base understood is returned
untouched (keyed on the exact fallthrough); (b) the possessive guard
blocks every "'s" form except the contractions inside our own phrases
(how's/what's/it's) and "i'm"; (c) the question-word guard blocks
who/whose/whom/where/which/when/why; (d) every class is an anchored
whole-message match, so "How are you, Tom?", "Nice weather, Tom.",
"It is cold in Oslo.", "How is Kim's city?" and "Happy is my dog."
(all probed) stay exactly as the base handles them.

Consequences by construction: 0 writes (clarify acts never reach the
notebook -- AgentLoop._act handles "clarify" with no write,
scripts/fable_agent_loop.py:337-339); the feelings and how-are-you
replies never claim the agent has feelings (it is plain software);
overlaps with 156b ("Hey you", "See you later.", "Good night.",
"Goodnight") keep byte-identical replies ("Bye!" / greeting) by design.
Empty and pure-punctuation input never fires.
"""

from __future__ import annotations

import re

# The generic fallthrough this stage keys on (exact text of the notebook
# path's "did not understand" reply at ears.hear level; see
# scripts/fable_agent_loop.py:148 and scripts/fable_loop90_agent.py:291).
FALLTHROUGH_MSG = ("I didn't understand that. "
                   "Could you say it another way?")

# One fixed short reply per class (sealed). The greeting reply reuses
# 156b's text verbatim; the bye reply is "Bye!" verbatim, so every input
# the base already answers keeps a byte-identical reply. The how-are-you,
# weather and feelings replies are kind but never claim feelings.
GREETING_REPLY = ("Hi! Teach me like \"Tom's boss is Ann.\" "
                  "Ask me like \"Who is Tom's boss?\"")
HOWAREYOU_REPLY = ("I'm just plain software, so I don't feel much, "
                   "but I'm ready to help!")
WEATHER_REPLY = ("Sounds nice! I don't feel the weather - "
                 "I'm just plain software.")
FEELINGS_REPLY = ("Thanks for telling me. I'm just plain software with "
                  "no feelings, but I'm here to help.")
BYE_REPLY = "Bye!"

CLASS_REPLIES = {"greeting": GREETING_REPLY, "howareyou": HOWAREYOU_REPLY,
                 "weather": WEATHER_REPLY, "feelings": FEELINGS_REPLY,
                 "bye": BYE_REPLY}

# Sealed closed phrase sets (natural spelling; matched AFTER
# normalize_156c, stored post-normalisation). One-line reason each:
# fixed everyday chat shapes with no name, relation, or question word
# inside; every teach/ask shape differs by at least one token.
GREET_TAIL_PHRASES = (
    "hello there",  # trailing-word greeting (the director probe)
    "hey there",    # trailing-word greeting
    "hi there",     # trailing-word greeting
    "hello you",    # greeting + trailing word
    "hey you",      # greeting + trailing word (base already answers)
    "hi you",       # greeting + trailing word
    "hello friend",  # friendly greeting
    "hey friend",   # friendly greeting
    "hi friend",    # friendly greeting
    "hello again",  # re-greeting
    "hey again",    # re-greeting
    "hi again",     # re-greeting
)
HOWAREYOU_PHRASES = (
    "how are you",            # the director probe
    "how are you today",      # how-are-you + tail
    "how are you doing",      # how-are-you family
    "how are you doing today",  # how-are-you family (director shape)
    "how is it going",        # how-are-you family
    "hows it going",          # contraction spelling
    "how is life",            # idle how-are-you
    "hows life",              # contraction spelling
    "what is up",             # idle greeting-question
    "whats up",               # contraction spelling
    "how do you do",          # formal greeting-question
    "how have you been",      # idle how-are-you
    "how have you been today",  # idle how-are-you + tail
    "how is your day",        # idle how-are-you
    "hows your day",          # contraction spelling
    "how is your day going",  # idle how-are-you
    "hows your day going",    # contraction spelling
)
WEATHER_PHRASES = (
    "nice weather today",  # the director probe
    "nice weather",        # weather chat
    "nice weather isnt it",  # weather chat (isn't normalised)
    "its cold out",        # the director shape ("It's cold out.")
    "its cold",            # weather chat
    "cold today",          # weather chat
    "its raining",         # weather chat
    "its sunny",           # weather chat
    "lovely day",          # idle chat
    "what a lovely day",   # idle chat
    "nice day today",      # idle chat
    "beautiful day",       # idle chat
    "what a beautiful day",  # idle chat
    "its a nice day",      # idle chat ("It is a nice day.")
)
# Feelings statements about the USER ("I'm tired.", "I'm happy today."):
# anchored ^im + one closed feeling word + one optional tail. Bare
# "Happy is my dog." never matches (no leading "im"); "I am hungry"
# and "I am from Lima" are deliberately NOT listed (name-guard
# territory; they stay as the base handles them).
FEELINGS_WORDS = (
    "tired",    # feeling state
    "happy",    # feeling state
    "sad",      # feeling state
    "bored",    # feeling state
    "excited",  # feeling state
    "sleepy",   # feeling state
    "sick",     # feeling state
    "good",     # feeling state ("I'm good.")
    "great",    # feeling state
    "fine",     # feeling state
    "ok",       # feeling state
    "okay",     # feeling state
    "well",     # feeling state
)
FEELINGS_TAILS = (
    "today",     # time tail ("I'm happy today.")
    "now",       # time tail
    "a bit",     # degree tail
    "a little",  # degree tail
    "very",      # degree tail
    "really",    # degree tail
    "so",        # degree tail
)
BYE_PHRASES = (
    "see you later",     # farewell (base already answers "Bye!")
    "see you soon",      # farewell
    "see you tomorrow",  # farewell
    "have a good day",   # send-off
    "have a good night",  # send-off
    "take care",         # send-off
    "talk soon",         # send-off
    "talk later",        # send-off
    "good night",        # farewell (base already answers "Bye!")
    "goodnight",         # farewell (base already answers "Bye!")
)

_FEELINGS_RE = re.compile(
    r"^im (?:%s)(?: (?:%s))?$" % ("|".join(FEELINGS_WORDS),
                                  "|".join(t.replace(" ", r"\s+") for t in FEELINGS_TAILS)))

# Deliberately NOT matched (each would hijack another path): every
# possessive "'s" outside our contractions (fact teaches/asks);
# who/whose/whom/where/which/when/why (questions about stored facts);
# "are you ..." agent-questions ("Are you happy?" stays base);
# "Happy is my dog." (no leading "im"; base serves its feelings reply);
# "I am hungry / from Lima" (not listed; 173 territory, stays base);
# "bye for now", bare good/see/got/it (156b near-miss guards, kept).

# Apostrophe forms allowed inside our own phrases (contractions only).
_CONTRACTION_HEADS = {"how", "what", "it", "that", "there", "here"}


def _is_ascii_alpha(c: str) -> bool:
    return "a" <= c <= "z" or "A" <= c <= "Z"


# Linear-time apostrophe scan: the head pattern ([A-Za-z]+)' would
# backtrack quadratically on long apostrophe-free alpha runs (pilot:
# 100 KB of "x" took 40 s), which broke the 1 MB rt110-D2 junk case.
# Instead match one alpha char beside the apostrophe and expand the
# head leftwards by hand -- same heads/tails as ([A-Za-z]+)'([A-Za-z]*)
# on every input, O(n) on all inputs.
_APOS_CORE_RE = re.compile(r"[A-Za-z]'[A-Za-z]*")


def _possessive_guard(raw: str) -> bool:
    """True iff raw contains a non-contraction apostrophe form.

    "How's"/"What's"/"It's"/"I'm" pass; "Kim's"/"Tom's"/"don't"/"it's
    cold in Oslo" possessive... ("It's" passes the guard but can still
    only fire via an anchored weather phrase, so "It is cold in Oslo."
    stays base.) Any other apostrophe form blocks the stage.
    """
    text = str(raw).replace("\u2019", "'").replace("\u2018", "'")
    if "'" not in text:
        return False
    for m in _APOS_CORE_RE.finditer(text):
        s = m.group(0)
        apos = s.index("'")
        i = m.start()
        while i > 0 and _is_ascii_alpha(text[i - 1]):
            i -= 1
        head = text[i:m.start() + apos].lower()
        tail = s[apos + 1:].lower()
        if head == "i" and tail == "m":
            continue
        if head in _CONTRACTION_HEADS and tail == "s":
            continue
        return True
    return False


_QUESTION_GUARD_RE = re.compile(r"\b(who|whose|whom|where|which|when|why)\b")


def normalize_156c(text: str) -> str:
    """Lower-case, unify i-am/it-is, strip punctuation -> one string.

    "How's it going?" -> "hows it going"; "It is cold out." ->
    "its cold out"; "I'm happy today." -> "im happy today";
    "Nice weather today." -> "nice weather today".
    """
    low = str(text).lower().replace("\u2019", "'").replace("\u2018", "'")
    low = re.sub(r"\bi am\b", "im", low)
    for src, dst in (("i\x27m", "im"), ("it\x27s", "its"), ("how\x27s", "hows"),
                     ("what\x27s", "whats"), ("isn\x27t", "isnt"),
                     ("that\x27s", "thats")):
        low = low.replace(src, dst)
    low = re.sub(r"\bit is\b", "its", low)
    low = re.sub(r"[^a-z0-9]+", " ", low)
    return " ".join(low.split())


def _norm_set(phrases: tuple[str, ...]) -> frozenset[str]:
    return frozenset(normalize_156c(p) for p in phrases)


GREET_TAIL = _norm_set(GREET_TAIL_PHRASES)
HOWAREYOU = _norm_set(HOWAREYOU_PHRASES)
WEATHER = _norm_set(WEATHER_PHRASES)
BYE2 = _norm_set(BYE_PHRASES)


def classify_156c(text: str) -> str | None:
    """Small-talk class for text, or None (NOT small talk, leave alone).

    Fires only on an anchored whole-message match of the closed sets,
    and never on possessive/question-word input. Priority:
    bye > greeting > howareyou > weather > feelings (sets are disjoint;
    the order only documents intent).
    """
    raw = str(text)
    if not raw.strip():
        return None
    if _possessive_guard(raw):
        return None
    norm = normalize_156c(raw)
    if not norm:
        return None
    if _QUESTION_GUARD_RE.search(norm):
        return None
    if norm in BYE2:
        return "bye"
    if norm in GREET_TAIL:
        return "greeting"
    if norm in HOWAREYOU:
        return "howareyou"
    if norm in WEATHER:
        return "weather"
    if _FEELINGS_RE.match(norm):
        return "feelings"
    return None


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
    cls = classify_156c(text)
    if cls is None:
        return base_actions
    return [{"act": "clarify", "text": CLASS_REPLIES[cls]}]


class Smalltalk156cMixin:
    """Stackable mixin: wider no-write small-talk classes, outermost ears.

    Cooperative (super() first): on ears it runs after the whole loop138h
    chain (including 156b's stage inside 138f), and only rewrites the
    exact generic fallthrough. Loop-level _act needs no override: the
    stage emits clarify acts, which never write.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        return smalltalk_actions(str(turn), actions)
