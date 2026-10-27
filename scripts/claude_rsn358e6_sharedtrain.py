#!/usr/bin/env python3
"""rsn-358e6 DRAFT (sleep research thread, 2026-09-27): shared layers keep learning in the freeze-and-grow arm.

rsn-358e4's eq-replayall freezes everything trained so far at each grow step: old experts, old router rows, attention,
norms, embeddings, output head and stop head, so only the new router group and its 4 narrow experts train in phases
B and C (352,944 of 1,654,446 weights). In 7 of 8 freeze-and-grow runs the new group received the new kind and still
learned little (artifacts/claude-rsn358e4-20260927/DIAG-new-group-share.md). The one change tested here, asked by the
Thread manager at 02:52 UTC:

  shared layers train   after each grow step, every block's attention (qkv, out, and the row/column position biases
                        br, bc) and every LayerNorm (ln1, ln2, ln_out, ln_state) train again in phases B and C.
                        Old experts, old router rows, token/slot/env embeddings, the output head and the stop head stay
                        frozen, as before. This is the usual mixture-of-experts layout: separate experts, shared layers.

Everything else is rsn-358e4's eq-replayall, imported unchanged: seeds 3-8, data, steps, replay of every earlier kind,
dev sets and scoring. Phase A is untouched, so its after-A scores must equal rsn-358e4's eq-replayall runs exactly.
The controls are rsn-358e4's own runs (eq-replayall and dense-replayall, same seeds); they are not rerun.

  python -B scripts/claude_rsn358e6_sharedtrain.py run --arm eq-replayall-shared --seed S --out DIR
  python -B scripts/claude_rsn358e6_sharedtrain.py selftest
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358e4_replayall as E4  # noqa: E402  (eq-replayall arm, replay-all schedule, scoring)

E3, X = E4.E3, E4.X
SHARED = (".qkv.", ".out.", ".br", ".bc", ".ln1.", ".ln2.")
TOP = ("ln_out.", "ln_state.")


def is_shared(name):
    return (name.startswith("blocks.") and any(k in name for k in SHARED)) or name.startswith(TOP)


def unfreeze_shared(net):
    for n, p in net.named_parameters():
        if is_shared(n):
            p.requires_grad_(True)


def make_net(arm, size):
    assert arm == "eq-replayall-shared"
    return E4.make_net("eq-replayall", size)


def score(net, dev, device):
    out = E4.score(net, dev, device)                             # grows (and freezes) after calls 2 and 3
    if E3.ST["calls"] in (2, 3):
        unfreeze_shared(net)                                     # before the next phase's optimiser is built
        out["trainable_next_phase"] = sum(p.numel() for p in net.parameters() if p.requires_grad)
    return out


def selftest():
    import random
    net = make_net("eq-replayall-shared", "small")
    E3.eq_grow(net)
    base = sum(p.numel() for p in net.parameters() if p.requires_grad)
    unfreeze_shared(net)
    names = [n for n, p in net.named_parameters() if p.requires_grad]
    now = sum(p.numel() for p in net.parameters() if p.requires_grad)
    assert base == 352944, base
    assert now == 882640, now
    frozen = [n for n, p in net.named_parameters() if not p.requires_grad]
    later = tuple(f".mlp.experts.{i}." for i in (0, 1, 2, 3, 8, 9, 10, 11)) + (".mlp.groups.0.", ".mlp.groups.2.")
    assert all(n.startswith(("tok", "slot", "env", "head", "halt")) or any(k in n for k in later) for n in frozen), frozen
    assert not any(k in n for n in names for k in later[:4] + later[8:9])      # old experts and old router rows
    # one step: old experts and embeddings unchanged, attention moves
    rng = random.Random(0)
    t, s, y, env = E3.R.tensors([E3.E.make_sum(rng, 3) for _ in range(8)], "cpu")
    before = {k: v.detach().clone() for k, v in net.named_parameters()}
    opt = torch.optim.AdamW(net.parameters(), lr=1e-2, weight_decay=0.1)
    for lg, q in net.loop_train(t, s, env, 1, 2):
        pass
    loss = E3.R.ce_and_exact(lg, s, y)[0] + X.aux_loss(net)
    opt.zero_grad(); loss.backward(); opt.step()
    after = dict(net.named_parameters())
    for k in frozen:
        assert torch.equal(after[k], before[k]), k
    qkv = next(k for k in after if ".qkv." in k)
    assert not torch.equal(after[qkv], before[qkv]), qkv
    print(f"selftest ok: trainable in B/C {now:,} (was {base:,}); attention and norms move after a step; old experts, "
          f"old router rows, embeddings, head and stop head unchanged")


if __name__ == "__main__":
    X.make_net, X.score, X.phase_batch = make_net, score, E4.phase_batch
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--arm", choices=["eq-replayall-shared"], required=True)
        ap.add_argument("--seed", type=int, required=True)
        ap.add_argument("--out", required=True)
        ap.add_argument("--threads", type=int, default=1)
        a = ap.parse_args()
        a.small, a.steps = True, None
        X.run(a)
