#!/usr/bin/env python3
"""rsn-358e8 (sleep research thread, 2026-09-27): Ben 18:54 UTC, "I meant what if we have a dense model, and then each
sleep, each layer gets one new neuron" (18:42: "We freeze the neurons, and add a new neuron each sleep"). Not experts: a
dense loop net that grows wider at each new phase.

Base: rsn-358e3's dense-replay (artifacts/claude-rsn358e3-20260926/RESULTS.md): the dense loop, phases A grids / B sums /
C mazes, every 10th phase-B step a grids batch from the phase-A pool, the same seeds, data, steps, dev sets and scoring.
The one change: instead of every weight training in phases B and C, everything already trained is frozen and each
block's MLP gets k new hidden units that are the only trainable weights. A new unit reads the whole residual stream (so it
sees every old unit's features, d + 1 weights in) and writes back into it (d weights out, zero at the start, so the net
starts each phase exactly as it ended the last one; the selftest checks this). The attention layers, embeddings, norms,
head and stop head do not grow and stay frozen. Old skills can still shift through the new units' outputs, which also
reach grids cells; the replay batches are what guard against that.

  grow1-replay     Ben's literal version: k = 1 new unit per layer (MLP) per phase
  grow1024-replay  k = 1,024 per layer per phase: the MLP hidden doubles in B; trainable in B = 1,050,624, about
                   moe-grow's 1,054,728
  dense2048-replay size control for grow1024 (report only): the dense loop with MLP hidden 2,048 from the start, every
                   weight training, the same replay. Its total weights equal grow1024's in B.
(The size control for grow1 is 358e3's dense-replay itself: grow1 adds 1,026 weights to 1,646,750.)

  python -B scripts/claude_rsn358e8_growunits.py run --arm grow1-replay|grow1024-replay|dense2048-replay --seed S --out DIR
  python -B scripts/claude_rsn358e8_growunits.py selftest
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358e3_replay as E3  # noqa: E402  (replay batches; imports claude_rsn358e_moe unchanged)
import claude_rsn358e_moe as X  # noqa: E402  (phases, data, dev sets, scoring, run)

R, E = X.R, X.E
_score, _make = X.score, X.make_net
K = {"grow1-replay": 1, "grow1024-replay": 1024}
ST = {"arm": None, "calls": 0}


class Grown(nn.Module):
    """the frozen old MLP plus k new hidden units: out = old(x) + W_out GELU(W_in x), W_out zero at the start"""

    def __init__(self, old, d, k):
        super().__init__()
        self.old = old
        self.fc_in = nn.Linear(d, k)
        self.fc_out = nn.Linear(k, d, bias=False)
        with torch.no_grad():
            self.fc_out.weight.zero_()

    def forward(self, x):
        return self.old(x) + self.fc_out(F.gelu(self.fc_in(x)))


def grow(net, k):
    for p in net.parameters():
        p.requires_grad_(False)
    d = X.SIZES["small"]["d"]
    for b in net.blocks:
        dev = next(b.parameters()).device
        b.mlp = Grown(b.mlp, d, k).to(dev)


def make_net(arm, size):
    ST.update(arm=arm, calls=0)
    E3.ST.update(arm=arm, calls=0, sums_steps=0, replayed=0)   # E3.phase_batch replays for any arm ending in "replay"
    net = _make("dense", size)
    if arm == "dense2048-replay":
        d = X.SIZES[size]["d"]
        for b in net.blocks:
            b.mlp = nn.Sequential(nn.Linear(d, 2048), nn.GELU(), nn.Linear(2048, d))
    net.arm = arm
    return net


def counts(net):
    return {"total": sum(p.numel() for p in net.parameters()),
            "trainable": sum(p.numel() for p in net.parameters() if p.requires_grad)}


def score(net, dev, device):
    """X.run scores at start and after each phase; grow arms grow (and freeze) right after phases A and B"""
    out = _score(net, dev, device)
    ST["calls"] += 1
    if ST["arm"] in K and ST["calls"] in (2, 3):
        grow(net, K[ST["arm"]])
    out["weights_next_phase"] = counts(net)
    if ST["calls"] == 3:
        out["replayed_batches"] = E3.ST["replayed"]
    return out


def selftest():
    import random
    rng = random.Random(0)
    t, s, y, env = R.tensors([E.make_sum(rng, 3) for _ in range(8)], "cpu")
    sizes = {}
    for arm, k in K.items():
        torch.manual_seed(0)
        net = make_net(arm, "small")
        ref = copy.deepcopy(net)
        grow(net, k)
        with torch.no_grad():
            a, _ = ref.loop_rounds(t, s, env, 4)
            b, _ = net.loop_rounds(t, s, env, 4)
        assert torch.equal(a, b), "a grown net must start identical"
        old = {n: p.detach().clone() for n, p in net.named_parameters() if not p.requires_grad}
        opt = torch.optim.AdamW(net.parameters(), lr=1e-2, weight_decay=0.1)
        for _ in range(2):
            for lg, q in net.loop_train(t, s, env, 1, 2):
                pass
            loss = R.ce_and_exact(lg, s, y)[0]
            opt.zero_grad(); loss.backward(); opt.step()
        now = dict(net.named_parameters())
        assert all(torch.equal(now[n], p) for n, p in old.items()), "a frozen weight moved"
        assert float(now["blocks.0.mlp.fc_out.weight"].detach().abs().sum()) > 0
        assert float(now["blocks.0.mlp.fc_in.weight"].detach().abs().sum()) > 0
        c = counts(net)
        assert c["trainable"] == 2 * k * (2 * 256 + 1), c
        sizes[arm] = c
    big = make_net("dense2048-replay", "small")
    nb = sum(p.numel() for p in big.parameters())
    assert nb == sizes["grow1024-replay"]["total"], (nb, sizes)
    E3.ST.update(arm="grow1-replay", sums_steps=0, replayed=0)
    pool = {sz: [E.make_latin_base(rng, sz) for _ in range(5)] for sz in (4, 5)}
    for _ in range(2500):
        E3.phase_batch(rng, "sums", 2, pool)
    assert E3.ST["replayed"] == 250
    print(f"selftest ok: grown nets start identical; frozen weights unchanged after 2 steps; new units learn; "
          f"in B: {sizes}; dense2048 {nb} total (= grow1024 in B); replay 250 of 2,500 sums steps")


if __name__ == "__main__":
    X.make_net, X.score, X.phase_batch = make_net, score, E3.phase_batch
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--arm", choices=["grow1-replay", "grow1024-replay", "dense2048-replay"], required=True)
        ap.add_argument("--seed", type=int, required=True)
        ap.add_argument("--out", required=True)
        ap.add_argument("--threads", type=int, default=1)
        a = ap.parse_args()
        a.small, a.steps = True, None
        X.run(a)
