#!/usr/bin/env python3
"""339 unit tests (stub reader and stub generator; cloud-safe).
Run: python -B scripts/claude_style339_test.py

  T1 feedback is saved, acknowledged, and survives an end-of-day sleep and a restart
  T2 the generator's system line carries the preference; the post-filter removes a banned nickname,
     emoji and a closing question, and "shorter" keeps 2 sentences
  T3 a confirm question is never changed by the post-filter
  T4 look-alike turns that are not about the assistant save nothing
  T5 opposite preferences replace each other; name needs the name in the text (fail closed)
  T6 a fact in the same message as feedback is still saved, and the reply says both
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_lis314_test as H  # noqa: E402
import claude_chat338_agent as C  # noqa: E402
import claude_style339_agent as S  # noqa: E402
import claude_e2e336_run as R  # noqa: E402

LAYERS = ("313", "315", "314")
FB_SHORT = "ugh your replies are way too long"
MIX = "keep it short pls. My dog is Pip."
Q_DOG = "What is my dog's name?"
TABLE = {"My dog is Pip.": H.st([H.fact("me", "dog", "Pip")], [H.LO]),
         MIX: H.st([H.fact("me", "dog", "Pip")], [H.HI]),
         Q_DOG: H.ask(owner="me", rel="dog")}


class StubGen:
    def __init__(self, outs):
        self.outs, self.calls = list(outs), []

    def sample_chat(self, msgs, n):
        self.calls.append(msgs)
        return self.outs[:n]


def build(outs, d=None):
    loop, _r, d = H.fresh(TABLE, LAYERS, d)
    gen = StubGen(outs)
    C.install_chat338(loop, S.StyledGen339(gen, loop))
    S.install_style339(loop)
    return loop, gen, None, d


LONG = "Sure thing, buddy! Bread rises because yeast makes gas 🙂. It traps bubbles. Then it bakes. Want a recipe?"


def t1_saved_and_survives_restart():
    loop, gen, clf, d = build([LONG])
    rep = H.say(loop, FB_SHORT)
    assert rep == "Sure, I'll keep it short.", rep
    R.end_day(loop)
    loop, gen, clf, _ = build([LONG], d)
    assert loop.style339_prefs.get("length") == "shorter", loop.style339_prefs
    rep = H.say(loop, "why does bread rise?")
    assert len(S._sentences(rep)) == 2, rep


def t2_prompt_and_filters():
    loop, gen, clf, _ = build([LONG])
    for t in ("stop calling me buddy lol", "no emojis please", "you don't need to end with a question every time"):
        H.say(loop, t)
    rep = H.say(loop, "why does bread rise?")
    sysline = gen.calls[-1][0]["content"]
    assert 'Never call the user "buddy"' in sysline and "Never use emoji" in sysline, sysline
    assert "buddy" not in rep.lower() and "🙂" not in rep and not rep.endswith("?"), rep
    assert rep.startswith("Sure thing!"), rep


def t3_confirm_untouched():
    loop, gen, clf, _ = build([LONG])
    H.say(loop, "you don't need to end with a question every time")
    H.say(loop, "My dog is Pip.")                           # unsure -> pending
    rep = H.say(loop, Q_DOG)
    assert rep.endswith("is that right?"), rep


def t4_no_false_saves():
    loop, gen, clf, _ = build([LONG])
    for t in ("how are you today", "my essay must be shorter", "my coach keeps calling me champ",
              "i have so many questions about the trip", "my friends call me Bo"):
        H.say(loop, t)
    assert loop.style339_prefs == {}, loop.style339_prefs


def t5_opposites_and_fail_closed():
    loop, gen, clf, _ = build([LONG])
    H.say(loop, FB_SHORT)
    H.say(loop, "from now on give me longer answers")
    assert loop.style339_prefs["length"] == "longer"
    H.say(loop, "call me whatever")                         # classifier says name, no capitalised name
    assert "name" not in loop.style339_prefs
    rep = H.say(loop, "you can call me Dita")
    assert loop.style339_prefs["name"] == "Dita" and rep == "Okay, Dita it is.", (rep, loop.style339_prefs)
    H.say(loop, "why does bread rise?")
    assert "called Dita" in gen.calls[-1][0]["content"]


def t6_fact_in_feedback_turn():
    loop, gen, clf, _ = build([LONG])
    rep = H.say(loop, MIX)
    assert rep.startswith("Sure, I'll keep it short.") and len(rep) > len("Sure, I'll keep it short."), rep
    assert H.has(loop, "USER", "dog", "Pip"), H.triples(loop)


if __name__ == "__main__":
    tests = (t1_saved_and_survives_restart, t2_prompt_and_filters, t3_confirm_untouched, t4_no_false_saves,
             t5_opposites_and_fail_closed, t6_fact_in_feedback_turn)
    for fn in tests:
        fn()
        print("ok", fn.__name__)
    print(f"339 tests {len(tests)}/{len(tests)}")
