#!/usr/bin/env python3
"""Selftest for the H12 plug-in (needs torch; one thread, fp32 CPU). Prints one JSON line ending "selftest": "ok".

What it proves, on random-init nets and real Wilson mazes (the practised source nets are not in git):
 1. the plug-in exposes what the equal-practice harness reads, and its Net is the baseline loop, unchanged;
 2. with the stop term switched off, the plug-in's maze_batch gives bit-identical weights to the harness's own
    Learner (so the loop structure was copied exactly and the stop term is the ONLY difference);
 3. with the stop term on, the first update's loss equals the practice loss (claude_fewex_net.train_loss)
    computed for 3 free + 2 gradient rounds, and the stop head receives gradient (it receives none in the baseline);
 4. four optimizer updates per batch, 2,048 per rung of 512 batches; sleep and update are inherited untouched;
 5. the harness scorer runs the plug-in net and reports the fields the marks read.
It does NOT test how well a practised net's stop learns on mazes; that is the experiment.
"""
from __future__ import annotations

import copy
import json
import random
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_eq_bench as EQ  # noqa: E402
import claude_fewex_net as base  # noqa: E402
import claude_dir_h12_stop as H  # noqa: E402


class FakeRng:
    """Feeds train_loss the round counts it would draw: total = 5, gradient rounds = 2."""

    def __init__(self, *vals):
        self.vals = list(vals)

    def randint(self, a, b):
        v = self.vals.pop(0)
        assert a <= v <= b
        return v


def mazes(n, seed=1):
    rng, seen = random.Random(seed), set()
    return [D.unique_maze(rng, 9, set(), seen) for _ in range(n)]


def same_state(a, b):
    sa, sb = a.state_dict(), b.state_dict()
    assert sa.keys() == sb.keys()
    return all(torch.equal(sa[k], sb[k]) for k in sa)


def main():
    torch.set_num_threads(1)
    B.N = H                       # what the harness does with --plugin
    # 1. interface
    for name in ("Net", "ARMS", "TRAIN_ROUNDS", "GRAD_ROUNDS", "tensors", "ce_and_exact", "train_loss",
                 "Practice", "Learner"):
        assert hasattr(H, name), name
    assert H.Net is base.Net
    torch.manual_seed(0)
    net0 = H.Net("loop")
    assert net0.weight_count() == 1645726 == base.Net("loop").weight_count()
    assert H.describe()["gap_vs_loop_weights"] == 0
    assert H.STOP_WEIGHT == 0.5
    assert H.Learner.sleep is B.Learner.sleep and H.Learner.update is B.Learner.update
    assert H.Learner.__init__ is B.Learner.__init__ and "maze_batch" in vars(H.Learner)
    assert getattr(B.N, "Learner", B.Learner) is H.Learner            # the harness picks it up

    items = mazes(64)
    assert len({D.layout_key(x) for x in items}) == 64
    batch_a, batch_b = items[:32], items[32:]

    # 2. stop term off == baseline learner, bit for bit (two batches = 8 updates)
    saved = H.STOP_WEIGHT
    try:
        H.STOP_WEIGHT = 0
        n1, n2 = copy.deepcopy(net0), copy.deepcopy(net0)
        l_base, l_mine = B.Learner(n1, 1e-3), H.Learner(n2, 1e-3)
        for b in (batch_a, batch_b):
            l_base.maze_batch(b)
            l_mine.maze_batch(b)
        assert l_base.steps == l_mine.steps == 2 * B.UPDATES
        assert same_state(n1, n2), "stop term off must reproduce the harness learner exactly"
        assert n1.halt.weight.grad is None and n2.halt.weight.grad is None
    finally:
        H.STOP_WEIGHT = saved

    # 3. stop term on: first-update loss equals the practice loss, stop head gets gradient
    ref = copy.deepcopy(net0)
    ref.train()
    expected = base.train_loss(ref, batch_a, FakeRng(5, 2)).item()      # 3 free + 2 gradient rounds, weight 0.5
    seen = []
    orig = H.Learner.update

    class Spy(H.Learner):
        def update(self, loss):
            seen.append(float(loss.detach()))
            return orig(self, loss)

    n3, n4 = copy.deepcopy(net0), copy.deepcopy(net0)
    l_stop, l_off = Spy(n3, 1e-3), B.Learner(n4, 1e-3)
    l_stop.maze_batch(batch_a)
    l_off.maze_batch(batch_a)
    assert len(seen) == B.UPDATES == l_stop.steps == 4
    assert abs(seen[0] - expected) < 1e-5, (seen[0], expected)
    assert n3.halt.weight.grad is not None and bool(torch.any(n3.halt.weight.grad != 0))
    assert n4.halt.weight.grad is None                                   # baseline: the stop head is never trained on mazes
    assert not torch.equal(n3.halt.weight, n4.halt.weight)
    assert all(torch.isfinite(p).all() for p in n3.parameters())

    # 4. 512 batches x 4 updates = 2,048 per rung (arithmetic the harness enforces, plus a real 3-batch count)
    assert EQ.N_BATCHES * B.UPDATES == EQ.N_UPDATES == 2048
    l3 = H.Learner(copy.deepcopy(net0), 1e-3)
    for _ in range(3):
        l3.maze_batch(batch_b)
    assert l3.steps == 12

    # 5. the harness scorer runs this net and gives the fields the marks read
    r = B.score(l3.net, items[:8], fixed_depth=16)
    assert set(r) == {"right", "n", "fixed_right", "mean_rounds", "cap_hits"} and r["n"] == 8
    assert 3.0 <= r["mean_rounds"] <= 48.0 and 0 <= r["cap_hits"] <= 8
    print(json.dumps({"selftest": "ok", "weights": net0.weight_count(), "stop_weight": H.STOP_WEIGHT,
                      "first_update_loss": seen[0], "practice_loss_same_rounds": expected,
                      "updates_per_batch": l_stop.steps}))


if __name__ == "__main__":
    main()
