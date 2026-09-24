#!/usr/bin/env python3
"""338b unit tests (stub loop, stub generator; no model). Cases are written by the month-end thread, not
taken from any TEST-ONLY panel."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_chat338b_agent as B  # noqa: E402

DIVERT = [
    "what's my sister's job again?",
    "whose cat is biscuit?",
    "juno's a lab, right?",
    "where does my dad work these days? a form wants it",
    "the dentist called and asked how old pip is and i forgot. what did i tell you",
    "is he still at the bakery?",
    "who's the lady with the three greyhounds? she waved at me",
    "remind me what time the plumber is coming",
    "how old is my neighbour's kid?",
    "what's orla's surname?",
]
KEEP = [
    "how do rainbows form?",
    "what's the tallest mountain in the world?",
    "can you explain photosynthesis again? i missed it",       # "explain ... again" is not recall ... see below
    "should i take the job offer or stay where i am?",
    "any tips for my first half marathon?",
    "how do i stop my sourdough from going flat?",
    "what should i get my brother for his birthday? ideas welcome",
    "i had such a long day at work",
    "tell me a fun fact about octopuses",
    "why is the earth's core so hot?",
    "what do you think about pineapple on pizza?",
    "we might go to the lake saturday if it doesn't rain",
    "can you write a short poem my niece could read at her grandpa's party?",
    "help me plan a surprise for my girlfriend's birthday?",
]


def test_people_question():
    bad = [t for t in DIVERT if not B.people_question(t, {"pip", "orla"})]
    assert not bad, bad
    wrong = [t for t in KEEP if B.people_question(t, {"pip", "orla"})]
    assert wrong == ["can you explain photosynthesis again? i missed it"], wrong   # known cost: "again" recall


def test_known_name():
    assert B.people_question("what does kasia do?", {"kasia"})
    assert not B.people_question("what does a notary do?", {"kasia"})


class Nb:
    def __init__(self):
        self.events = []


class Loop:
    def __init__(self, d):
        self.dir, self.nb, self.lis314_store = d, Nb(), {}
        self.turn = lambda text: ["I didn't understand that question — could you say it another way?"]


class Gen:
    def __init__(self):
        self.calls = 0

    def sample_chat(self, msgs, n):
        self.calls += 1
        return ["Yes, I'm sure about that."] * n


def test_install():
    import claude_cre333_agent as C
    C._facts = lambda loop: [("USER", "sister", "Mira"), ("Mira", "job", "nurse")]
    d = tempfile.mkdtemp()
    loop, g = Loop(d), Gen()
    B.install_chat338b(loop, g)
    assert loop.turn("mira's still a nurse, right?") == [B.HONEST338B]
    assert g.calls == 0 and loop.chat338b_stats["diverted"] == 1
    assert loop.turn("how do volcanoes work?") == ["Yes, I'm sure about that."]
    assert g.calls == 1
    g.sample_chat = lambda msgs, n: ["Your sister Tilda would know!", "Volcanoes vent magma from below."]
    assert loop.turn("how do geysers work?") == ["Volcanoes vent magma from below."]
    assert loop.chat338b_stats["g2_capital"] == 1


if __name__ == "__main__":
    n = 0
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            n += 1
    print(f"338b tests: {n}/{n} OK")
