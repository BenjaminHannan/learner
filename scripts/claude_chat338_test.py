#!/usr/bin/env python3
"""338 unit tests (stub reader and stub generator, cloud-safe). Run: python -B scripts/claude_chat338_test.py

  T1 a turn the stack gives up on is answered by the generator; the notebook is untouched
  T2 a taught fact is saved exactly as before and its reply is not replaced
  T3 G1: a sample that claims to remember is skipped; the next passing sample is used
  T4 G2: "your sister <unknown Name>" is skipped; G3: an invented answer to a personal question is
     skipped; if every sample fails, the stack's own reply stays
  T5 the chat history survives a restart and reaches the generator's prompt
  T6 a lis-314 confirm question and its "yes" are never replaced
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_lis314_test as H  # noqa: E402 (stubs route122, builds stacks with a stub reader)
import claude_chat338_agent as C  # noqa: E402

LAYERS = ("313", "315", "314")
T_SURE, T_UNSURE = "My sister is Ilka.", "My dog is Pip."
Q_DOG = "What is my dog's name?"
TABLE = {T_SURE: H.st([H.fact("me", "sister", "Ilka")], [H.HI]),
         T_UNSURE: H.st([H.fact("me", "dog", "Pip")], [H.LO]),
         Q_DOG: H.ask(owner="me", rel="dog")}


class StubGen:
    def __init__(self, outs):
        self.outs = list(outs)
        self.calls = []

    def sample_chat(self, msgs, n):
        self.calls.append(msgs)
        return self.outs[:n]


def build(outs, d=None):
    loop, _r, d = H.fresh(TABLE, LAYERS, d)
    gen = StubGen(outs)
    C.install_chat338(loop, gen)
    return loop, gen, d


def t1_gave_up_is_answered():
    loop, gen, _ = build(["Bread rises because yeast makes gas bubbles. Want a simple recipe?"])
    ev0 = len(loop.nb.events)
    rep = H.say(loop, "why does bread rise?")
    assert rep.startswith("Bread rises because yeast"), rep
    assert len(loop.nb.events) == ev0 and loop.chat338_stats["replaced"] == 1
    rep = H.say(loop, "hi")                               # canned help line is replaced too
    assert "Teach me like" not in rep, rep


def t2_teach_unchanged():
    loop, gen, _ = build(["SHOULD NOT APPEAR."])
    rep = H.say(loop, T_SURE)
    assert "SHOULD NOT APPEAR" not in rep and H.has(loop, "USER", "sister", "Ilka"), (rep, H.triples(loop))
    assert not gen.calls


def t3_memory_claim_skipped():
    loop, gen, _ = build(["Got it, I'll remember that!", "That sounds like a lot. What part worries you most?"])
    rep = H.say(loop, "i'm so stressed about exams")
    assert rep.startswith("That sounds like a lot"), rep
    assert loop.chat338_stats["G1"] == 1


def t4_invented_people_and_answers():
    loop, gen, _ = build(["Maybe ask your sister Wren to help.", "Could you ask a friend to quiz you?"])
    rep = H.say(loop, "how do i stay focused when studying?")
    assert rep.startswith("Could you ask a friend"), rep
    assert loop.chat338_stats["G2"] == 1
    loop, gen, _ = build(["Your cat is called Mochi.", "Your cat is 4 years old."])
    rep = H.say(loop, "what's my cat called again?")
    assert "Mochi" not in rep and " 4 " not in rep, rep     # both fail G3 -> the stack's own reply stays
    assert loop.chat338_stats["G3"] == 2 and loop.chat338_stats["kept_all_failed"] == 1


def t5_history_survives_restart():
    loop, gen, d = build(["Sure, happy to chat about it."])
    H.say(loop, "can we talk about my garden project?")
    loop, gen, _ = build(["Of course, how is it going?"], d)
    H.say(loop, "why do tomatoes split?")
    texts = [m["content"] for m in gen.calls[-1]]
    assert "can we talk about my garden project?" in texts, texts


def t6_confirm_not_replaced():
    loop, gen, _ = build(["SHOULD NOT APPEAR."])
    H.say(loop, T_UNSURE)
    rep = H.say(loop, Q_DOG)
    assert "is that right?" in rep and "SHOULD NOT APPEAR" not in rep, rep
    rep = H.say(loop, "yes")
    assert "SHOULD NOT APPEAR" not in rep and H.has(loop, "USER", "dog", "Pip"), (rep, H.triples(loop))


if __name__ == "__main__":
    tests = (t1_gave_up_is_answered, t2_teach_unchanged, t3_memory_claim_skipped,
             t4_invented_people_and_answers, t5_history_survives_restart, t6_confirm_not_replaced)
    for fn in tests:
        fn()
        print("ok", fn.__name__)
    print(f"338 tests {len(tests)}/{len(tests)}")
