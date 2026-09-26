#!/usr/bin/env python3
"""CPU tests for scripts/claude_k1c_cre.py (needs torch, no model). Run: python -B scripts/claude_k1c_test.py"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_chat338_agent as C38  # noqa: E402
import claude_cre333_agent as C  # noqa: E402
import claude_cre333d_agent as CD  # noqa: E402
import claude_k1c_cre as K  # noqa: E402
import claude_k1c_pilot as PL  # noqa: E402

REQ = "any ideas for 3 names for it?"


class Gen:
    """sample_chat returns fixed drafts; records the prompt."""
    def __init__(self, outs):
        self.outs, self.msgs = outs, None
        self.g = type("G", (), {})()

    def sample_chat(self, msgs, n):
        self.msgs = msgs
        return list(self.outs)[:n]


def main():
    ok = 0
    real_lp = PL.reply_logp
    three = "1. Crumb.\n2. Rise.\n3. Loaf."
    two = "1. Crumb.\n2. Rise."
    # fake 1B information: longer text = more tied to the prompt; the null prompt gives 0
    PL.reply_logp = lambda g, gen, msgs, t: (0.0 if msgs[-1]["content"] == "" else len(t) / 100)
    try:
        # 1. form first: the draft with the asked-for count wins over an earlier, shorter list
        st = {}
        out = K.write_k1c(Gen([two, three, "1. A.\n2. B.\n3. C."]), REQ, "", [], st, whole=False)
        assert out == three and st["picked_not_first"] == 1 and st["picked_by_form"] == 1, (out, st)
        ok += 1
        # 2. same form: the 1B's information decides; ties keep draw order
        st = {}
        a, b = "1. Crumb Club.\n2. Rise.\n3. Loaf.", "1. Crumb Club and Co.\n2. Rise.\n3. Loaf."
        assert K.write_k1c(Gen([a, b]), REQ, "", [], st, whole=False) == b
        assert K.write_k1c(Gen([a, a + ""]), REQ, "", [], {}, whole=False) == a
        ok += 1
        # 3. a draft that fails a guard is never picked; none passing -> None (fallback upstream)
        real_g = CD.guard333d
        CD.guard333d = lambda c, t, k: ("G4" if c == three else None)
        try:
            st = {}
            assert K.write_k1c(Gen([two, three]), REQ, "", [], st, whole=False) == two and st["G4"] == 1
            CD.guard333d = lambda c, t, k: "G5"
            assert K.write_k1c(Gen([two, three]), REQ, "", [], {}, whole=False) is None
        finally:
            CD.guard333d = real_g
        ok += 1
        # 4. history goes between the system line and the request; trim is applied as in cre333d
        hist = [{"role": "user", "content": "I'm opening a bakery called Crumb"}, {"role": "assistant", "content": "Nice!"}]
        g = Gen(["Here you go: 1. Crumb\n2. Rise\n3. Loaf and more"])
        out = K.write_k1c(g, REQ, "", hist, {}, whole=False)
        assert [m["role"] for m in g.msgs] == ["system", "user", "assistant", "user"] and g.msgs[1:3] == hist
        assert out == C38.trim("Here you go: 1. Crumb\n2. Rise\n3. Loaf and more"), out
        ok += 1
        # 5. whole=True goes through k1b's finished-sample path (strip_only when finished, trim when cut)
        real_fin = K.KB.sample_chat_fin
        K.KB.sample_chat_fin = lambda gen, msgs, n: [("1. Crumb.\n2. Rise.\n3. Loaf", True), (two + " and", False)]
        try:
            st = {}
            out = K.write_k1c(Gen([]), REQ, "", [], st, whole=True)
            assert out == "1. Crumb.\n2. Rise.\n3. Loaf" and st["kept_whole"] == 1 and st["trimmed"] == 1, (out, st)
        finally:
            K.KB.sample_chat_fin = real_fin
        ok += 1
    finally:
        PL.reply_logp = real_lp
    # 6. reply_logp: mean token log-prob after the prompt, no random draws
    class Tok:
        def __call__(self, text, return_tensors=None):
            return {"input_ids": torch.tensor([[1] * len(text)])}

    class M:
        def __call__(self, input_ids):
            return type("O", (), {"logits": torch.zeros(1, input_ids.shape[1], 4)})()
    g = type("G", (), {"tok": Tok(), "model": M(), "dev": "cpu", "torch": torch})()
    gen = type("Gn", (), {"_render": lambda self, msgs: "ab"})()
    s0 = torch.get_rng_state()
    v = PL.reply_logp(g, gen, [], "xyz")
    assert abs(v - float(torch.log(torch.tensor(0.25)))) < 1e-6 and torch.equal(s0, torch.get_rng_state())
    ok += 1
    # 7. the four builders swap the writer in and restore it; the turn reads chat338's history
    import claude_mu402 as MU
    seen, real = {}, MU.build_null02c

    def fake(state_dir, args):
        seen["fn"] = CD.install_creative333d
        o = type("L", (), {})()
        o.layers330c = ["330a_334", "cre333d", "seed402"]
        return o
    MU.build_null02c = fake
    try:
        before = CD.install_creative333d
        for fn, tag in ((K.build_null_k1c_x, "cre_k1c_x"), (K.build_null_k1c_k, "cre_k1c_k"),
                        (K.build_null_k1c_b, "cre_k1c_b"), (K.build_null_k1c_kb, "cre_k1c_kb")):
            out = fn("x", None)
            assert seen["fn"] is not before and CD.install_creative333d is before
            assert out.layers330c == ["330a_334", tag, "seed402"]
    finally:
        MU.build_null02c = real

    class NB:
        events = []

    class L:
        def __init__(self, d):
            self.dir, self.nb, self.counters, self.experience, self.tick = d, NB(), {}, [], 0
            self.turn = lambda t: ["(inner)"]

        def _save(self):
            pass
    C._facts = lambda loop: []
    PL.reply_logp = lambda g, gen, msgs, t: 0.0
    try:
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / C38.STATE_NAME338).write_text(json.dumps({"history": hist}), encoding="utf-8")
            loop = L(d)
            K.install_creative_k1c(loop, Gen([two, three]), use_hist=True, whole=False)
            assert loop.turn(REQ) == [three] and loop.cre333_stats["hist_msgs"] == 2
            assert loop.experience[-1]["phase"] == "creative_k1c" and loop.turn("what time is it") == ["(inner)"]
            loop2 = L(d)
            K.install_creative_k1c(loop2, Gen([two]), use_hist=False, whole=False)
            assert loop2.turn(REQ) == [two] and loop2.cre333_stats["hist_msgs"] == 0
    finally:
        PL.reply_logp = real_lp
    ok += 1
    print(f"k1c tests: {ok}/7 OK")


if __name__ == "__main__":
    main()
