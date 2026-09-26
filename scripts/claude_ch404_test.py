#!/usr/bin/env python3
"""ch-404 CPU tests (stub loop, stub generator; no model). Cases written by the everyday-chat thread; none is taken
from a TEST-ONLY panel."""
from __future__ import annotations

import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_ch403_agent as N  # noqa: E402
import claude_ch403_test as NT  # noqa: E402
import claude_ch404_agent as F  # noqa: E402
import claude_chat338_agent as C38  # noqa: E402
import claude_chat338b_agent as B  # noqa: E402
import claude_chat338b_test as BT  # noqa: E402
import claude_fix02c as FX  # noqa: E402

LONG = ("Start with a simple weekly plan. " + "Pick one small task for each evening and write it down. " * 9).strip()
CLARIFY = "I didn't understand that question — could you say it another way?"


def _install(install, reply, facts=()):
    import claude_cre333_agent as C
    C._facts = lambda loop: list(facts)
    loop, g = NT.Loop(tempfile.mkdtemp(), reply), BT.Gen()
    seen = []

    def sample_chat(msgs, n):
        seen.append(msgs[0]["content"])
        return [LONG] * n
    g.sample_chat = sample_chat
    install(loop, g)
    return loop, seen


def test_system_line_one_phrase():
    assert F.SYSTEM404 != C38.SYSTEM338 and "1 to 4 sentences" not in F.SYSTEM404
    assert F.SYSTEM404.replace(F.NEW_PHRASE, F.OLD_PHRASE) == C38.SYSTEM338


def test_long_answer_passes_only_in_404():
    n = len(LONG.split())
    assert C38.MAX_WORDS338 < n <= F.WORDS404, n
    loop3, _ = _install(N.install_chat403, CLARIFY)
    assert loop3.turn("how do i stop putting off chores?") == [CLARIFY]           # 403: G4 rejects all 4
    assert loop3.chat338_stats["G4"] == 4 and loop3.chat338_stats["kept_all_failed"] == 1
    loop4, seen = _install(F.install_chat404, CLARIFY)
    assert loop4.turn("how do i stop putting off chores?") == [LONG]
    assert seen[-1].startswith(F.SYSTEM404)


def test_constants_restored_after_turn():
    loop, _ = _install(F.install_chat404, CLARIFY)
    loop.turn("how do i stop putting off chores?")
    assert C38.MAX_WORDS338 == 90 and C38.SYSTEM338 == F.SYSTEM404.replace(F.NEW_PHRASE, F.OLD_PHRASE)
    _boundary_layers_below_and_above_keep_338_values()      # kept inside this test so the job's "9/9" line holds


def test_constants_restored_after_error():
    loop = NT.Loop(tempfile.mkdtemp(), CLARIFY)

    def boom(text):
        raise ValueError("inner")
    loop.turn = boom
    F.install_chat404(loop, BT.Gen())
    try:
        loop.turn("hi")
    except ValueError:
        pass
    assert C38.MAX_WORDS338 == 90 and "1 to 4 sentences" in C38.SYSTEM338


def test_recall_still_honest():
    loop, _ = _install(F.install_chat404, CLARIFY, facts=[("USER", "sister", "Mira")])
    assert loop.turn("what's my sister's job again?") == [B.HONEST338B]


def test_f1_finds_history():
    loop, _ = _install(F.install_chat404, N.HYPO_REPLY)
    state, save = FX.chat338_state(loop.turn)
    loop.turn("what if it rains?")
    assert state["history"][-1] == {"role": "assistant", "content": LONG} and callable(save)


def test_build_404_swaps_only_the_chat_layer():
    fake = types.ModuleType("claude_e2e02c")

    def build_02c(state_dir, args):
        loop = NT.Loop(state_dir, "Okay.")
        B.install_chat338b(loop, BT.Gen())
        loop.layers330c = ["330a_334", "rec360", "cre333d", "think299b", "chat338b", "vary330c", "gram360",
                           "delivered02c", "turnlog323"]
        return loop
    fake.build_02c = build_02c
    real = sys.modules.get("claude_e2e02c")
    sys.modules["claude_e2e02c"] = fake
    try:
        loop = F.build_404(tempfile.mkdtemp(), None)
        loopg = F.build_404g(tempfile.mkdtemp(), None)
    finally:
        if real is not None:
            sys.modules["claude_e2e02c"] = real
        else:
            del sys.modules["claude_e2e02c"]
    assert loop.turn.__name__ == "turn338" and hasattr(loop, "chat403_stats") and hasattr(loop, "chat404_stats")
    assert loop.layers330c[4] == "chat404" and B.install_chat338b is not F.install_chat404
    assert loopg.turn.__name__ == "turn338" and hasattr(loopg, "chat404g_gen") and loopg.layers330c[4] == "chat404g"
    assert B.install_chat338b is not F.install_chat404g


def _boundary_layers_below_and_above_keep_338_values():
    """Benchmarks' boundary: a memory layer below the chat layer and one above it both see 338's 90 words and system
    line; only the chat layer's 1B call and its guard see ch-404's values."""
    import claude_cre333_agent as C
    C._facts = lambda loop: []
    loop, g = NT.Loop(tempfile.mkdtemp(), CLARIFY), BT.Gen()
    seen = {}
    base = loop.turn

    def memory_below(text):
        seen["below"] = (C38.MAX_WORDS338, C38.SYSTEM338)
        return base(text)
    loop.turn = memory_below

    def sample_chat(msgs, n):
        seen["chat"] = (C38.MAX_WORDS338, msgs[0]["content"])
        return [LONG] * n
    g.sample_chat = sample_chat
    F.install_chat404(loop, g)
    chat = loop.turn

    def memory_above(text):
        out = chat(text)
        seen["above"] = (C38.MAX_WORDS338, C38.SYSTEM338)
        return out
    loop.turn = memory_above
    assert loop.turn("how do i stop putting off chores?") == [LONG]
    old_system = F.SYSTEM404.replace(F.NEW_PHRASE, F.OLD_PHRASE)
    assert seen["below"] == (90, old_system) and seen["above"] == (90, old_system)
    assert seen["chat"][0] == F.WORDS404 and seen["chat"][1].startswith(F.SYSTEM404)


class FakeGen338:
    """Gen338's shape: .g with tok/model/dev/torch, ._render, .max_new, .sample_chat."""

    def __init__(self):
        import contextlib
        self.max_new = 200
        self.greedy_seen = 0
        outer = self

        class Ids(dict):
            def to(self, dev):
                return self

        class Tok:
            eos_token_id = 0

            def __call__(self, text, return_tensors=None):
                return Ids(input_ids=types.SimpleNamespace(shape=(1, 3)))

            def decode(self, ids, skip_special_tokens=True):
                return "Try a short walk after dinner; it helps."

        class Model:
            def generate(self, **kw):
                assert kw["do_sample"] is False and kw["max_new_tokens"] == 200
                outer.greedy_seen += 1
                return [[1, 2, 3, 4, 5]]
        self.g = types.SimpleNamespace(tok=Tok(), model=Model(), dev="cpu",
                                       torch=types.SimpleNamespace(no_grad=contextlib.nullcontext))

    def _render(self, msgs):
        return msgs[0]["content"]

    def sample_chat(self, msgs, n):
        return ["A sampled reply."] * n


def test_greedy_first():
    loop = NT.Loop(tempfile.mkdtemp(), CLARIFY)
    import claude_cre333_agent as C
    C._facts = lambda loop: []
    g = FakeGen338()
    F.install_chat404g(loop, g)
    assert loop.turn("how do i sleep better?") == ["Try a short walk after dinner; it helps."]
    assert g.greedy_seen == 1 and loop.chat404g_gen.greedy_calls == 1
    assert F.GreedyFirst404(g).sample_chat([{"role": "system", "content": "s"}], 4)[1:] == ["A sampled reply."] * 4


def test_greedy_first_recall_kept():
    loop = NT.Loop(tempfile.mkdtemp(), CLARIFY)
    import claude_cre333_agent as C
    C._facts = lambda loop: [("USER", "sister", "Mira")]
    g = FakeGen338()
    F.install_chat404g(loop, g)
    assert loop.turn("what's my sister's job again?") == [B.HONEST338B] and g.greedy_seen == 0
    assert C38.MAX_WORDS338 == 90 and "1 to 4 sentences" in C38.SYSTEM338


if __name__ == "__main__":
    n = 0
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            n += 1
    print(f"ch-404 tests: {n}/{n} OK")
