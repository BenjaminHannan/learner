#!/usr/bin/env python3
"""Experiment 227c -- WIDER IDENTITY MATCHING + NAME-CHECK / RENAME intents.

Plain software, reply-only, no writes. Used by scripts/claude_loop227c_agent.py
inside the notebook-miss branch AFTER the untouched 227 exact-template gate
(so every turn 227/227b already answers keeps its answer).

Widening (all still whole-sentence matches, never keyword spotting):
  * normalise(): lowercase, curly apostrophes, drop commas, strip ending
    punctuation (so a missing "?" is fine), strip leading fillers
    (so/hey/ok/okay/well/oh/um/and/hi/hello) and trailing fillers
    (anyway/anyways/exactly/then/though/actually/again/please/really/
    by the way), expand contractions (what's -> what is, who's, where's,
    where're, what're, you're, i'll, i'm, whats, whos).
  * a larger, explicit sentence list per sheet intent (casual synonyms such
    as bot / real person / call you / built you / learn stuff).
  * NAMECHECK: "Is your name X?", "Are you called/named X?", "Is X your
    name?" -> "Yes, my name is Premonition." when X is Premonition, else
    "No, my name is Premonition."
  * RENAME: "Your name is X.", "I'll call you X.", "I'm going to call you
    X.", "You are called X.", "Can I call you X?" ... -> "My name is
    Premonition." (0 writes; the assistant's name never changes).
  X must be one word starting with a capital letter in the original turn.
A second-person word (you/your/yours/yourself) is required, as in 227.
"""
from __future__ import annotations

import re

ASSISTANT_NAME = "Premonition"

SHEET_227C: dict[str, str] = {
    "NAME": "My name is Premonition.",
    "MAKER": "Ben built me.",
    "WHAT": ("I'm a small program that keeps what you teach me in a "
             "notebook and answers from it. When I don't know something, "
             "I say so instead of guessing."),
    "LEARN": ('I learn when you tell me facts in plain sentences, like '
              '"Kim lives in Oslo." I save each one and answer from my notes.'),
    "AGE": ("I don't have an age. I'm a program, so I don't measure "
            "my life in years."),
    "HOME": ("I don't live anywhere. I'm a program that runs on a computer "
             "and keeps a notebook file."),
}
NAMECHECK_YES = "Yes, my name is Premonition."
NAMECHECK_NO = "No, my name is Premonition."
RENAME_REPLY = "My name is Premonition."

SECOND_PERSON = {"you", "your", "yours", "yourself"}

LEAD_FILLERS = ("so", "hey", "ok", "okay", "well", "oh", "um", "and", "hi",
                "hello")
TRAIL_FILLERS = ("by the way", "anyways", "anyway", "exactly", "then",
                 "though", "actually", "again", "please", "really")
CONTRACTIONS = {
    "what's": "what is", "whats": "what is", "who's": "who is",
    "whos": "who is", "where's": "where is", "where're": "where are",
    "what're": "what are", "you're": "you are", "i'll": "i will",
    "i'm": "i am", "how's": "how is", "i'd": "i would", "when's": "when is",
}


def _variants(heads: list[str], tails: list[str]) -> list[str]:
    return [f"{h} {t}".strip() for h in heads for t in tails]


def _build_templates() -> dict[str, str]:
    t: dict[str, list[str]] = {}
    t["NAME"] = [
        "what is your name", "what are you called", "what is your name called",
        "what should i call you", "what do i call you", "what can i call you",
        "what shall i call you", "how should i call you",
        "do you have a name", "have you got a name", "do you have a name yet",
        "have you got a name yet", "what do people call you",
        "what do they call you", "what name do you go by",
        "what is your real name", "what are you named", "tell me your name",
        "what name should i use for you", "what should i call you then",
        "may i ask your name", "can i ask your name", "can you tell me your name",
        "could you tell me your name", "what do you call yourself",
        "what is your name called", "do you have your own name",
    ]
    t["MAKER"] = (
        _variants(["who"], ["made you", "created you", "built you",
                            "designed you", "invented you", "programmed you",
                            "wrote you", "coded you", "trained you"])
        + _variants(["who is your"], ["maker", "creator", "builder",
                                      "designer", "inventor", "programmer",
                                      "author"])
        + ["who was your maker", "who was your creator",
           "who are your makers", "who are your creators",
           "who is the person who made you", "who is the one who built you"])
    t["WHAT"] = (
        _variants(["are you"], [
            "a human", "a machine", "a person", "a program", "a robot",
            "alive", "software", "a bot", "a chatbot", "a chat bot",
            "a real person", "a real human", "human", "an ai", "a computer",
            "a computer program", "real", "a living thing", "a real robot",
            "a piece of software", "a human being"])
        + ["what are you", "what kind of thing are you",
           "what sort of thing are you", "what kind of program are you",
           "what type of thing are you", "what exactly are you",
           "tell me what you are", "are you a person or a program",
           "are you a human or a bot", "are you a human or a robot",
           "are you a person or a bot", "are you a person or a robot"])
    t["LEARN"] = (
        _variants(["how do you"], [
            "know things", "learn", "learn new things", "remember things",
            "work", "learn stuff", "learn new stuff", "remember stuff",
            "know stuff", "learn things", "remember what i tell you",
            "store what i tell you", "learn from me", "get new facts",
            "keep facts"])
        + ["how does your memory work", "how does your learning work",
           "how do you actually learn", "how can you learn",
           "how are you able to learn", "how did you learn things"])
    t["AGE"] = [
        "do you have an age", "how old are you", "what is your age",
        "what is your birthday", "when were you born", "when were you made",
        "when is your birthday", "when were you created",
        "when were you built", "what year were you made",
        "are you old", "are you young", "do you have a birthday",
    ]
    t["HOME"] = [
        "do you have a home", "do you live anywhere", "what is your home",
        "where are you from", "where do you live", "where is your home",
        "where do you come from", "where do you stay", "where are you",
        "where are you located", "where do you live now",
        "where are you based", "what is your address",
        "what city do you live in", "where is your house",
    ]
    out: dict[str, str] = {}
    for intent, forms in t.items():
        for f in forms:
            out[f] = intent
    return out


TEMPLATES = _build_templates()

_NAME_WORD = r"([A-Z][A-Za-z'-]*)"
NAMECHECK_RE = [
    re.compile(r"^is your name " + r"(\S+)$"),
    re.compile(r"^is your name really " + r"(\S+)$"),
    re.compile(r"^are you called " + r"(\S+)$"),
    re.compile(r"^are you named " + r"(\S+)$"),
    re.compile(r"^is (\S+) your name$"),
    re.compile(r"^is (\S+) your real name$"),
]
RENAME_RE = [re.compile("^" + h + r" (\S+)$") for h in (
    "your name is", "your new name is", "your name will be",
    "your name should be", "from now on your name is",
    "i will call you", "i am going to call you", "i am gonna call you",
    "i am calling you", "i shall call you", "i want to call you",
    "i would like to call you", "i will name you", "i name you",
    "let me call you", "can i call you", "could i call you",
    "may i call you", "you are called", "you are named",
    "from now on you are called", "i will just call you",
)]


def normalise(turn: str) -> str:
    s = str(turn).replace("’", "'").replace("‘", "'")
    s = s.replace(",", " ")
    s = " ".join(s.split())
    s = re.sub(r"[\s?.!]+$", "", s)
    s = s.lower()
    words = s.split()
    words = [CONTRACTIONS.get(w, w) for w in words]
    s = " ".join(words)
    changed = True
    while changed and s:
        changed = False
        for f in LEAD_FILLERS:
            if s.startswith(f + " "):
                s = s[len(f) + 1:]
                changed = True
        for f in TRAIL_FILLERS:
            if s.endswith(" " + f):
                s = s[: -(len(f) + 1)]
                changed = True
    return s.strip()


def _original_token(turn: str, lowered: str) -> str | None:
    """The original-case spelling of a slot word (for the capital check)."""
    for tok in re.findall(r"[A-Za-z][A-Za-z'-]*", str(turn)):
        if tok.lower() == lowered:
            return tok
    return None


def _slot_is_name(turn: str, slot: str) -> bool:
    slot = slot.strip("'\"")
    if not re.fullmatch(r"[a-z][a-z'-]*", slot):
        return False
    orig = _original_token(turn, slot)
    return bool(orig) and re.fullmatch(_NAME_WORD, orig) is not None


def identity_answer227c(turn: str) -> tuple[str, str] | None:
    """(intent, reply) for a widened identity turn, else None. No writes."""
    s = normalise(turn)
    if not s:
        return None
    toks = set(re.findall(r"[a-z]+", s))
    if not (toks & SECOND_PERSON):
        return None
    intent = TEMPLATES.get(s)
    if intent is not None:
        return intent, SHEET_227C[intent]
    for rx in NAMECHECK_RE:
        m = rx.match(s)
        if m and _slot_is_name(turn, m.group(1)):
            name = m.group(1).strip("'\"")
            if name == ASSISTANT_NAME.lower():
                return "NAMECHECK", NAMECHECK_YES
            return "NAMECHECK", NAMECHECK_NO
    for rx in RENAME_RE:
        m = rx.match(s)
        if m and _slot_is_name(turn, m.group(1)):
            return "RENAME", RENAME_REPLY
    return None
