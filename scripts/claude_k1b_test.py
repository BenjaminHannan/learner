#!/usr/bin/env python3
"""CPU tests for scripts/claude_k1b_cre.py (needs torch, no model). Run: python -B scripts/claude_k1b_test.py"""
from __future__ import annotations

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_chat338_agent as C38  # noqa: E402
import claude_cre333_agent as C  # noqa: E402
import claude_cre333d_agent as CD  # noqa: E402
import claude_k1b_cre as K  # noqa: E402

VOCAB = ["<pad>", "</s>", "Here", " are", " names", ":", "\n1.", " \"Crumb", " Club\"", "\n2.", " \"Rise", " Up\"",
         " and", " more", "<im_end>"]
EOS2 = 14


class Tok:
    eos_token_id = 1
    chat_template = None

    def __call__(self, text, return_tensors=None):
        class B(dict):
            def to(self, dev):
                return self
        return B(input_ids=torch.tensor([[5, 5, 5]]))

    def decode(self, ids, skip_special_tokens=True):
        ids = ids.tolist() if hasattr(ids, "tolist") else ids
        return "".join(VOCAB[i] for i in ids if not (skip_special_tokens and i in (0, 1, EOS2)))


class Model:
    def __init__(self, rows):
        self.rows, self.kw = rows, None
        self.generation_config = type("GC", (), {"eos_token_id": [1, EOS2]})()

    def generate(self, **kw):
        self.kw = kw
        return torch.tensor([[5, 5, 5] + r for r in self.rows])


class G:
    def __init__(self, rows):
        self.tok, self.model, self.dev, self.torch = Tok(), Model(rows), "cpu", torch


class Gen:
    def __init__(self, rows):
        self.g, self.max_new, self.t, self.p = G(rows), 200, 0.7, 0.9

    def _render(self, msgs):
        return "x"


def main():
    ok = 0
    list_done = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, EOS2, 1]         # ended on its own: last item has no full stop
    list_cut = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]            # hit the token limit
    # 1. generate is called with Gen338.sample_chat's exact arguments; finish flags read from the ids
    gen = Gen([list_done, list_cut])
    res = K.sample_chat_fin(gen, [{"role": "user", "content": "q"}], 2)
    kw = gen.g.model.kw
    assert kw["max_new_tokens"] == 200 and kw["do_sample"] is True and kw["temperature"] == 0.7 and kw["top_p"] == 0.9
    assert kw["num_return_sequences"] == 2 and kw["pad_token_id"] == 1
    assert [f for _t, f in res] == [True, False], res
    ok += 1
    # 2. the finished list keeps its last item; trim (cre333d) would have cut it back to "2."
    full = res[0][0]
    assert full.endswith('"Rise Up"') and C38.trim(full).endswith("2."), (full, C38.trim(full))
    stats = {}
    out = K.write_k1b(Gen([list_done]), "any ideas for names for it?", "", stats)
    assert out == full and stats["kept_whole"] == 1, (out, stats)
    ok += 1
    # 3. a cut-off sample is trimmed exactly as cre333d does
    stats = {}
    out = K.write_k1b(Gen([list_cut]), "any ideas for names for it?", "", stats)
    assert out == C38.trim(res[1][0]) and stats["trimmed"] == 1, (out, stats)
    ok += 1
    # 4. strip_only removes think text and an assistant prefix, nothing else
    assert K.strip_only("<think>x</think> Assistant: Hi there\n5. \"Bo\"") == "Hi there\n5. \"Bo\""
    ok += 1
    # 5. guards still apply (a refusal is dropped even when finished) and the fallback is cre333d's
    class L:
        def __init__(self):
            class NB:
                events = []
            self.nb, self.counters, self.experience, self.tick, self.dir = NB(), {}, [], 0, "."
            self.turn = lambda t: ["(inner)"]

        def _save(self):
            pass
    C._facts = lambda loop: []
    loop = L()
    K.install_creative_k1b(loop, Gen([[2, 3, 4, EOS2]]))
    import claude_cre333b_agent as CB
    assert CB.is_creative333c("any ideas for names for it?")
    r = loop.turn("any ideas for names for it?")
    assert r == ["Here are names"] and loop.cre333_stats["kept_whole"] == 1
    loop2 = L()
    K.install_creative_k1b(loop2, Gen([[2, 3, 4, EOS2]]))
    K.CD.guard333d, real = (lambda c, t, k: "G5"), K.CD.guard333d
    try:
        assert loop2.turn("any ideas for names for it?") == [C.FALLBACK] and loop2.cre333_stats["G5"] == 1
    finally:
        K.CD.guard333d = real
    ok += 1
    print(f"k1b tests: {ok}/5 OK")


if __name__ == "__main__":
    main()
