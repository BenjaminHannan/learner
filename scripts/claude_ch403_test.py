#!/usr/bin/env python3
"""ch-403 CPU tests (stub loop, stub generator; no model). Cases: 338b's own DEV cases (claude_chat338b_test.py)
and everyday questions written by the everyday-chat thread; none is taken from a TEST-ONLY panel."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_ch403_agent as N  # noqa: E402
import claude_chat338_agent as C38  # noqa: E402
import claude_chat338b_agent as B  # noqa: E402
import claude_chat338b_test as BT  # noqa: E402
import claude_fix02c as FX  # noqa: E402
import fable_fix137c_hypo as H  # noqa: E402

RECALL = BT.DIVERT + [
    "ok whats my cat's name, lets see if you remember",
    "which of my coworkers went to the icu? my charge nurse was asking",
    "do you remember what instrument i played as a kid?",
    "wait what city did i tell you i live in?",
    "quick q, what did i say my best friends name was?",
    "what's ulla's last name? i'm writing the thank-you card",
    "vada's the older one right?",
]
EVERYDAY = [q for q in BT.KEEP if "photosynthesis" not in q] + [
    "can you explain photosynthesis again? i missed it",
    "why does my phone battery die so much faster when its cold outside",
    "how do taxes on a paycheck work? my first check was smaller than i expected",
    "why do cats knead blankets with their paws? she does it every single night",
    "what if our schedules are totally different? she works nights now",
    "how do i tell when the soil is dry enough to water again",
    "why does my rice come out mushy sometimes and crunchy other times",
    "is it better to keep the bike money in a separate account from my spending money",
    "what's the best way to clean my oven without harsh stuff?",
    "i told my boss i'd take the weekend shift, was that dumb?",
    "did i mess up by not texting back yet?",
]


def test_recall403():
    miss = [t for t in RECALL if not N.recall403(t, {"pip", "orla"})]
    assert not miss, miss
    wrong = [t for t in EVERYDAY if N.recall403(t, {"pip", "orla"})]
    assert not wrong, wrong
    assert N.recall403("what does kasia do?", {"kasia"})
    assert not N.recall403("what does a notary do?", {"kasia"})


def test_hypo_line_identical():
    assert N.HYPO_REPLY == H.HYPO_REPLY


class Loop(BT.Loop):
    def __init__(self, d, reply):
        super().__init__(d)
        self.turn = lambda text: [reply(text) if callable(reply) else reply]


def _install(reply, facts=()):
    import claude_cre333_agent as C
    C._facts = lambda loop: list(facts)
    loop, g = Loop(tempfile.mkdtemp(), reply), BT.Gen()
    g.sample_chat = lambda msgs, n: ["Then you could try meeting on weekends instead."] * n
    N.install_chat403(loop, g)
    return loop


def test_pretend_goes_to_1b():
    loop = _install(N.HYPO_REPLY)
    assert loop.turn("what if that doesn't work?") == ["Then you could try meeting on weekends instead."]
    assert loop.chat403_stats == {"recall_kept": 0, "released": 0, "pretend_handed": 1, "pretend_replaced": 1}


def test_pretend_after_a_save_stays():
    loop = _install(N.HYPO_REPLY)
    inner = loop.turn.__closure__  # noqa: F841  (installed; the stub inner below writes an event)
    loop2 = Loop(tempfile.mkdtemp(), N.HYPO_REPLY)

    def saving_inner(text):
        loop2.nb.events.append("save")
        return [N.HYPO_REPLY]
    loop2.turn = saving_inner
    g = BT.Gen()
    N.install_chat403(loop2, g)
    assert loop2.turn("suppose my cat is called Pip") == [N.HYPO_REPLY] and g.calls == 0


def test_pretend_that_is_a_recall_question_gets_honest_line():
    loop = _install(N.HYPO_REPLY)
    assert loop.turn("what if i told you my dog's name, do you remember it?") == [B.HONEST338B]


def test_everyday_my_question_released():
    clarify = "I didn't understand that question — could you say it another way?"
    loop = _install(clarify)
    assert loop.turn("why does my phone battery die faster in the cold?") == \
        ["Then you could try meeting on weekends instead."]
    assert loop.chat403_stats["released"] == 1 and loop.chat338b_stats["diverted"] == 0


def test_recall_question_kept_honest():
    clarify = "I didn't understand that question — could you say it another way?"
    loop = _install(clarify, facts=[("USER", "sister", "Mira")])
    assert loop.turn("what's my sister's job again?") == [B.HONEST338B]
    assert loop.chat403_stats["recall_kept"] == 1 and loop.chat338b_stats["diverted"] == 1


def test_other_rule_lines_untouched():
    loop = _install("Saved: your sister is Mira.")
    assert loop.turn("my sister is Mira") == ["Saved: your sister is Mira."]
    assert loop.chat338_stats["gave_up"] == 0


def test_f1_finds_history():
    loop = _install(N.HYPO_REPLY)
    state, save = FX.chat338_state(loop.turn)
    loop.turn("what if it rains?")
    assert state["history"][-1] == {"role": "assistant", "content": "Then you could try meeting on weekends instead."}
    assert callable(save)


def test_build_403_swaps_only_the_chat_layer():
    import types
    fake = types.ModuleType("claude_e2e02c")

    def build_02c(state_dir, args):
        loop = Loop(state_dir, "Okay.")
        B.install_chat338b(loop, BT.Gen())            # looked up at call time, as build_02c does
        loop.layers330c = ["330a_334", "rec360", "cre333d", "think299b", "chat338b", "vary330c", "gram360",
                           "delivered02c", "turnlog323"]
        return loop
    fake.build_02c = build_02c
    real = sys.modules.get("claude_e2e02c")
    sys.modules["claude_e2e02c"] = fake
    try:
        loop = N.build_403(tempfile.mkdtemp(), None)
    finally:
        if real is not None:
            sys.modules["claude_e2e02c"] = real
        else:
            del sys.modules["claude_e2e02c"]
    assert loop.turn.__name__ == "turn338" and hasattr(loop, "chat403_stats")
    assert loop.layers330c[4] == "chat403" and "chat338b" not in loop.layers330c
    assert B.install_chat338b is not N.install_chat403          # restored after the build


def test_guards_unchanged():
    assert C38.MAX_WORDS338 == 90 and C38.N338 == 4 and C38.HISTORY338 == 12


if __name__ == "__main__":
    n = 0
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            n += 1
    print(f"ch-403 tests: {n}/{n} OK")
