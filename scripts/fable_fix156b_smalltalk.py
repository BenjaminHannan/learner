#!/usr/bin/env python3
"""Experiment 156b -- THE ONE CHANGE: small-talk classes on loop156/loop150.

Base: loop156 (scripts/fable_loop156_agent.py; loop156 = loop150 + 156
exact-word small-talk stage; imported read-only, no file edited). Exp 156
passed its own panel, but everyday phone small talk fell through: common
greetings with a time of day, thanks with extra words or spelling
variants, goodnight/see-you abbreviations, reactions and interjections,
emoji-only messages, and multi-word acknowledgements all got the generic
fallthrough; and "LOL" -> "Got it!" is an odd reply to laughter.

THE RULE (cooperative Smalltalk156bMixin, ears hear() only -- the
OUTERMOST layer, so every notebook-path stage below has already run):
call super().hear(turn) first. If the notebook path UNDERSTOOD the
message (anything other than the exact generic fallthrough clarify),
return its actions untouched. Only when the base returns exactly
[{"act": "clarify", "text": FALLTHROUGH_MSG}] is the message tested: the
whole message must be small talk (every token after normalisation in the
closed SMALLTALK_VOCAB below, or an emoji-only message); then return one
fixed short clarify reply for its class. Otherwise return base untouched.

Closed and rule-based: per-class lexicons written from general knowledge
of English chat (no learned weights, nothing tuned to any panel).
Normalisation: lower-case, collapse repeated letters ("hiii"->"hi",
"thx!!"->"thx", "soorry"->"sory"), glue multi-word phrases
("good morning", "see you", "got it", "a lot", "so much", "thank you")
before splitting, punctuation/emoji turned into word splits. Emoji-only
messages (zero tokens but emoji present) are the laugh/reaction class.

Consequences by construction: 0 writes (clarify acts never reach the
notebook -- AgentLoop._act handles "clarify" with no write,
scripts/fable_agent_loop.py:337-339); messages mixing small talk with
content ("Hi Tom", "thanks, Bob is Tom's boss", "Wow Records' founder is
Ann", "Sorry's singer is Justin Bieber") keep a content word outside the
closed list and are unchanged; "who are you" / "what can you do" contain
who/are/what/can/do (not in the list) and are unchanged; empty and pure
punctuation input never fires.
"""

from __future__ import annotations

import re

# The generic fallthrough this stage keys on (exact text of the notebook
# path's "did not understand" reply; see scripts/fable_loop90_agent.py:291
# and the FakeEars template at scripts/fable_agent_loop.py:148).
FALLTHROUGH_MSG = ("I didn't understand that. "
                   "Could you say it another way?")

# One fixed short reply per class (sealed; greeting carries one teach
# example and one ask example). Laugh and apology replies are new in 156b:
# laughter no longer gets "Got it!".
GREETING_REPLY = ("Hi! Teach me like \"Tom's boss is Ann.\" "
                  "Ask me like \"Who is Tom's boss?\"")
THANKS_REPLY = "You're welcome!"
LAUGH_REPLY = "Haha, nice!"
ACK_REPLY = "Got it!"
BYE_REPLY = "Bye!"
APOLOGY_REPLY = "No worries!"

CLASS_REPLIES = {"greeting": GREETING_REPLY, "thanks": THANKS_REPLY,
                 "laugh": LAUGH_REPLY, "ack": ACK_REPLY, "bye": BYE_REPLY,
                 "apology": APOLOGY_REPLY}

# Sealed closed lexicons (natural spelling; matched AFTER normalize_156b,
# sets stored post-normalisation so "cool"/"coool" both hit, "hmm"->"hm",
# "sorry"->"sory", "good morning"->"god_morning"). One-line reason each:
# discourse glue / politeness particles / reactions that can never be a
# taught name, relation, or question word. Multi-word items ("good
# morning", "see you", "got it", "a lot", "so much", "thank you") are
# glued to single phrase tokens so bare "good"/"see"/"got"/"it"/"a" stay
# OUTSIDE the vocabulary (content words, e.g. "good thanks" stays a
# near-miss exactly as in 156).
GREETING_WORDS = (
    "hi",             # greeting core (covers hii/hiii/hi!!)
    "hey",            # greeting core (covers heyyy)
    "hello",          # longer greeting (covers hellooo)
    "yo",             # short greeting
    "hiya",           # friendly greeting
    "howdy",          # friendly greeting
    "morning",        # time-of-day greeting ("morning!")
    "mornin",         # time-of-day variant ("mornin!")
    "afternoon",      # time-of-day greeting
    "evening",        # time-of-day greeting ("evening!")
    "good morning",   # time-of-day phrase
    "good afternoon",  # time-of-day phrase
    "good evening",   # time-of-day phrase
)
THANKS_WORDS = (
    "thanks",     # thanks core
    "thank",      # "thank you" head
    "thx",        # textspeak thanks (covers thx!!/thaaanks)
    "ty",         # textspeak "thank you"
    "thanx",      # spelling variant
    "thnx",       # spelling variant
    "thank you",  # canonical phrase
)
LAUGH_WORDS = (
    "lol",      # laugh (covers lolll)
    "lmao",     # stronger laugh
    "haha",     # laugh
    "hahaha",   # long laugh (covers hahahaha: no letter-run)
    "ha",       # short laugh
    "hehe",     # giggle
    "wow",      # reaction/interjection (covers woow/wooww)
    "nice",     # approval reaction
    "cool",     # approval reaction (covers coool)
)
ACK_WORDS = (
    "ok",       # acknowledgement (covers okkk)
    "okay",     # acknowledgement (covers oookay)
    "k",        # textspeak ack ("k bye"; covers kk)
    "sure",     # assent
    "alright",  # assent
    "okie",     # assent variant ("okie!")
    "got it",   # multi-word acknowledgement phrase
    "yup",      # assent (legacy from 156, unchanged reply)
    "yep",      # assent (legacy from 156)
    "yes",      # assent (legacy from 156)
    "fine",     # assent (legacy from 156)
    "great",    # approval (legacy from 156)
    "awesome",  # approval (legacy from 156)
)
BYE_WORDS = (
    "bye",         # bye core (covers byeee/bye!!)
    "byebye",      # doubled bye
    "goodbye",     # formal bye
    "cya",         # textspeak bye
    "night",       # "night" as send-off (from 156)
    "goodnight",   # one-word goodnight
    "good night",  # two-word goodnight phrase
    "gn",          # goodnight abbreviation ("gn!")
    "nite",        # night variant ("nite!")
    "later",       # send-off ("later!", "see you later")
    "ttyl",        # textspeak bye ("talk to you later")
    "see you",     # farewell phrase
    "see ya",      # farewell variant
)
APOLOGY_WORDS = (
    "sorry",  # apology core (covers soorry/sorry!/sorry)
    "hmm",    # hesitation (normalises to hm; covers hmmm)
    "hm",     # hesitation core
    "um",     # hesitation (covers umm/um...)
    "uh",     # hesitation (covers uhh)
    "oops",   # apology-ish interjection (covers oopss)
)
# Glue words that only ever ride along inside a thanks-flavoured message
# ("thank you", "thanks so much!", "ty, very helpful!", "thanks a lot").
# Bare "a"/"lot"/"good"/"see"/"got"/"it" are NOT vocabulary (content).
GLUE_WORDS = (
    "you",      # "thank you"
    "very",     # "very helpful"
    "much",     # "so much"
    "so",       # "so much"
    "helpful",  # "very helpful"
    "a lot",    # "thanks a lot" tail (phrase only)
    "so much",  # "thanks so much" tail (phrase only)
)

# Deliberately NOT in the list (each would hijack another experiment's
# path): bare good/see/got/it/a/lot (content words; only their phrases
# are vocabulary); no/wait (bare corrections, N6); who/are/what/can/do/
# you-are... ("who are you"/"what can you do" stay fallthrough for the
# exp-127 self router); btw/also/oh/actually/my (filler teaches, N4 +
# exp 150); who/what/where/is/are (questions); there/for/now (near-miss
# guards: "hi there", "bye for now" stay unchanged); every name and
# relation word.


def _collapse_runs(low: str) -> str:
    """Collapse repeated letters: hiii->hi, heyyy->hey, soorry->sory."""
    return re.sub(r"([a-z])\1+", r"\1", low)


# Phrase gluing on the collapsed lowercase text (keys are post-collapse
# forms: "good"->"god", "see"->"se"; the collapse already absorbed
# repeated letters, e.g. "goood morning" -> "god morning"). Longer
# phrases first so "good night" wins over parts.
_PHRASE_ORDER = (
    ("god afternon", "god_afternon"),
    ("god morning", "god_morning"),
    ("god evening", "god_evening"),
    ("god night", "god_night"),
    ("thank you", "thank_you"),
    ("se you", "se_you"),
    ("so much", "so_much"),
    ("got it", "got_it"),
    ("se ya", "se_ya"),
    ("a lot", "a_lot"),
)


def normalize_156b(text: str) -> list[str]:
    """Lower-case, collapse letter runs, glue phrases, split -> tokens.

    "hiii" -> ["hi"]; "Good morning!!" -> ["god_morning"]; "see-you" ->
    ["se_you"]; "hi <wave>" -> ["hi"]; emoji-only -> [] (laugh class via
    has_emoji_156b, never bare small talk).
    """
    low = _collapse_runs(str(text).lower())
    for phrase, glued in _PHRASE_ORDER:
        low = low.replace(phrase, glued)
    low = re.sub(r"[^a-z0-9_]+", " ", low)  # punctuation/emoji -> split
    return [t for t in low.split() if t]


def has_emoji_156b(text: str) -> bool:
    """True iff the text contains a non-ASCII character (emoji).

    Rule-based only: any codepoint above 127 counts as emoji for the
    emoji-only rule. Pure ASCII punctuation (":)", "...", "!!!") is not
    emoji and never fires.
    """
    return any(ord(c) > 127 for c in str(text))


def _norm_set(words: tuple[str, ...]) -> frozenset[str]:
    out: set[str] = set()
    for w in words:
        out.update(normalize_156b(w))
    return frozenset(out)


GREETING_TOKENS = _norm_set(GREETING_WORDS)
THANKS_TOKENS = _norm_set(THANKS_WORDS)
LAUGH_TOKENS = _norm_set(LAUGH_WORDS)
ACK_TOKENS = _norm_set(ACK_WORDS)
BYE_TOKENS = _norm_set(BYE_WORDS)
APOLOGY_TOKENS = _norm_set(APOLOGY_WORDS)
GLUE_TOKENS = _norm_set(GLUE_WORDS)

SMALLTALK_VOCAB: frozenset[str] = (GREETING_TOKENS | THANKS_TOKENS
                                   | LAUGH_TOKENS | ACK_TOKENS
                                   | BYE_TOKENS | APOLOGY_TOKENS
                                   | GLUE_TOKENS)

# Longer laughter runs ("hahahaha", "hehehehe"): still the closed
# rule-based laugh class. Tokens fully matching (ha){2,} or (he){2,}
# count as laugh vocabulary (no weights, no panel data; "ha"/"hehe" are
# already listed outright above, and bare "he" is NOT matched).
_LAUGH_RUN_RE = re.compile(r"^(?:ha){2,}$|^(?:he){2,}$")


def _in_vocab(tok: str) -> bool:
    return tok in SMALLTALK_VOCAB or _LAUGH_RUN_RE.match(tok) is not None


def _in_laugh(tok: str) -> bool:
    return tok in LAUGH_TOKENS or _LAUGH_RUN_RE.match(tok) is not None


def classify_156b(text: str) -> str | None:
    """Small-talk class for text, or None (NOT small talk, leave alone).

    Fires only when the whole message is small talk: every token in the
    closed list with at least one token, or an emoji-only message (zero
    tokens but emoji present -> laugh). Any content word -> None.
    Priority: thanks > bye > greeting > apology > laugh > ack (so
    "cool thanks" is thanks, "k bye" is bye, "ok cool" is laugh).
    """
    toks = normalize_156b(text)
    if not toks:
        if str(text).strip() and has_emoji_156b(text):
            return "laugh"
        return None
    if any(not _in_vocab(t) for t in toks):
        return None
    if any(t in THANKS_TOKENS for t in toks):
        return "thanks"
    if any(t in BYE_TOKENS for t in toks):
        return "bye"
    if any(t in GREETING_TOKENS for t in toks):
        return "greeting"
    if any(t in APOLOGY_TOKENS for t in toks):
        return "apology"
    if any(_in_laugh(t) for t in toks):
        return "laugh"
    if any(t in ACK_TOKENS for t in toks):
        return "ack"
    return None  # all-glue tails ("so much", "very helpful") never fire


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
    cls = classify_156b(text)
    if cls is None:
        return base_actions
    return [{"act": "clarify", "text": CLASS_REPLIES[cls]}]


class Smalltalk156bMixin:
    """Stackable mixin: no-write small-talk classes, outermost ears layer.

    Cooperative (super() first): on ears it runs after the whole loop156
    chain, and only rewrites the exact generic fallthrough. Loop-level
    _act needs no override: the stage emits clarify acts, which never
    write.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        return smalltalk_actions(str(turn), actions)
