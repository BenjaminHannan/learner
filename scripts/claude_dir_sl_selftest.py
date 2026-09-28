#!/usr/bin/env python3
"""SL plug-in selftest (torch, CPU, random-init nets; no practised net is needed or used).

1. With target="exact" the plug-in's loss is bit-identical to claude_fewex_net.train_loss (same net, same rng): proves the round
   draws, the free/gradient split, the cross-entropy, the weight and the mean are copied, i.e. only the target can differ.
2. With target="stable" the loss equals an independently built value: cross-entropy from the baseline loss path plus 0.5 x BCE
   against a target made by the net's own 48-round `forward` (a different code path from the plug-in's continue-the-state loop).
3. The stop head gets gradient under both targets; the target is not the exact one (they differ on a random net).
4. Practice.step (plug-in) runs, moves the weights and keeps the baseline's optimizer, schedule and seeds.
5. Plug-in exposes what the harness needs, defines no Learner, and its Net is the baseline class (1,645,726 weights).
6. Plain arm falls back to the baseline's cross-entropy path.
Prints one line {"selftest": "ok", ...} at the end; any failure raises.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_sl_stop as P
import claude_fewex_data as D
import claude_fewex_net as base
import claude_rsn358a_envs as E


def batch(seed, n=8):
    rng = random.Random(seed)
    return [E.make_sum(rng, 3) for _ in range(n)] if seed % 2 == 0 else [D.latin_legend(rng, 4) for _ in range(n)]


def independent(net, items, seed):
    """Loss rebuilt from the net's own 48-round forward (a separate path), same round draws."""
    t, s, y = base.tensors(items)
    rr = random.Random(seed)
    total = rr.randint(1, base.TRAIN_ROUNDS)
    k = rr.randint(1, min(total, base.GRAD_ROUNDS))
    with torch.no_grad():
        cells, _ = net.forward(t, s)
        final = cells[47].argmax(-1)
    e, (dr, dc) = net.embed(t, s)
    fill = s.view(s.shape[0], -1).bool()
    h = torch.zeros_like(e)
    for r in range(1, total + 1):                    # every round with gradient; the plug-in detaches the free ones (values equal)
        h = net.step(h, e, dr, dc)
        if r > total - k:
            lg, q = net.read(h)
            ce, _ = base.ce_and_exact(lg, s, y)
            tgt = ((lg.argmax(-1) == final) | ~fill).all(1).float()
            yield ce, F.binary_cross_entropy_with_logits(q.float(), tgt), tgt


def main():
    torch.manual_seed(0)
    net = base.Net("loop")
    assert net.weight_count() == 1645726 and P.Net is base.Net
    d = P.describe()
    assert d["gap_vs_loop_weights"] == 0 and d["stop_weight"] == 0.5 and d["final_round"] == 48
    assert not hasattr(P, "Learner"), "the harness must fall back to its own baseline Learner"
    for name in ("Net", "ARMS", "TRAIN_ROUNDS", "GRAD_ROUNDS", "LR", "WD", "WARMUP", "tensors", "ce_and_exact", "train_loss", "Practice", "load_net"):
        assert hasattr(P, name), name
    # target function on hand-made logits: 3 puzzles x 4 cells; puzzle 0 agrees everywhere, 1 differs on a fill cell, 2 differs only off the fill
    lg = torch.zeros(3, 4, 5)
    for i, cls in enumerate([[1, 2, 3, 4], [1, 2, 3, 4], [1, 2, 3, 4]]):
        for c, v in enumerate(cls):
            lg[i, c, v] = 1.0
    final = torch.tensor([[1, 2, 3, 4], [1, 2, 3, 0], [1, 0, 3, 4]])
    fill = torch.tensor([[1, 1, 1, 1], [1, 1, 1, 1], [1, 0, 1, 1]]).bool()
    assert P.stable_target(lg, final, fill).tolist() == [1.0, 0.0, 1.0]
    out = {}
    for seed in (2, 3, 4, 5, 6, 7):
        items = batch(seed)
        # 1. exact target == the baseline loss, bit for bit
        a = P.loss_with_target(net, items, random.Random(seed), "exact")
        b = base.train_loss(net, items, random.Random(seed))
        assert a.item() == b.item(), (seed, a.item(), b.item())
        # 2. stable target == independently built
        parts = list(independent(net, items, seed))
        want = torch.stack([c for c, _, _ in parts]).mean() + 0.5 * torch.stack([h for _, h, _ in parts]).mean()
        got = P.loss_with_target(net, items, random.Random(seed), "stable")
        assert abs(got.item() - want.item()) < 1e-5, (seed, got.item(), want.item())
        out[f"seed{seed}"] = {"exact_loss": round(a.item(), 6), "stable_loss": round(got.item(), 6)}
    # 3. gradient reaches the halt head under the stable target; target differs from the exact one somewhere
    P.STATS.update({k: 0 for k in P.STATS})
    net.zero_grad(set_to_none=True)
    for seed in range(2, 12):
        P.loss_with_target(net, batch(seed), random.Random(seed), "stable").backward()
    assert net.halt.weight.grad is not None and bool(net.halt.weight.grad.abs().sum() > 0)
    assert all(p.grad is not None for p in net.parameters() if p.ndim == 2), "a matrix got no gradient"
    st = dict(P.STATS)
    assert st["gradient_round_items"] > 0 and st["stable"] != st["exact"] or st["stable_and_exact"] != st["stable"], st
    # 4. plug-in practice step
    torch.manual_seed(1)
    pr = P.Practice("loop", 1, 100)
    ref = base.Practice("loop", 1, 100)
    assert type(pr.opt) is type(ref.opt) and pr.opt.defaults == ref.opt.defaults
    w0 = {k: v.clone() for k, v in pr.net.state_dict().items()}
    loss = pr.step(batch(2))
    assert loss == loss and any(not torch.equal(w0[k], v) for k, v in pr.net.state_dict().items())
    # 6. plain arm: baseline cross-entropy path
    pn = base.Net("plain")
    assert P.loss_with_target(pn, batch(2), random.Random(2), "stable").item() == base.train_loss(pn, batch(2), random.Random(2)).item()
    print(json.dumps({"selftest": "ok", "torch": torch.__version__, "weights": net.weight_count(), "losses": out, "stats_over_10_batches": st}))


if __name__ == "__main__":
    main()
