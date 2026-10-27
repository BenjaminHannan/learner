#!/usr/bin/env python3
"""Selftest for the pond plug-in (needs torch; one thread, fp32 CPU). Prints one JSON line ending "selftest": "ok".

Proves, on random-init nets and real Wilson mazes (the practised source nets are not in git):
 1. interface: what the equal-practice harness reads; Net is the baseline loop, unchanged; arms a/b/c/z carry lambda 0.001/0.004/0.016/0;
 2. the penalty formula equals a hand loop on numbers (masses sum to 1, expected rounds, gradient signs);
 3. the penalty term alone gives gradient ONLY to the stop head's weight and bias;
 4. with clipping switched off, the body (every parameter except the stop head) after 8 updates is bit-identical to the
    harness's own Learner, and the stop head differs; with the real clip the body difference is printed, not hidden;
 5. per-maze cross-entropy, fill-count weighted, equals ce_and_exact's pooled CE;
 6. 4 optimizer updates per batch, 2,048 per rung; sleep and update inherited untouched; the scorer runs the net.
It does NOT test how a practised net's stop learns on mazes; that is the experiment.
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
import claude_dir_pond_stop as P  # noqa: E402
import claude_dir_pond_a, claude_dir_pond_b, claude_dir_pond_c, claude_dir_pond_z  # noqa: E401,E402


def mazes(n, seed=1):
    rng, seen = random.Random(seed), set()
    return [D.unique_maze(rng, 9, set(), seen) for _ in range(n)]


def hand_ponder(q, c, lam):
    """Plain python loops, no torch ops beyond sigmoid: the same quantity written the slow way."""
    import math
    T, Bn = len(q), len(q[0])
    total = 0.0
    masses = []
    for b in range(Bn):
        alive, ec, er, m = 1.0, 0.0, 0.0, []
        for t in range(T):
            h = 1 / (1 + math.exp(-q[t][b]))
            p = h * alive if t < T - 1 else alive
            m.append(p)
            ec += p * c[t][b]
            er += (t + 1) * p
            alive *= 1 - h
        masses.append(m)
        total += ec + lam * er
    return total / Bn, masses


def body_equal(a, b):
    sa, sb = a.state_dict(), b.state_dict()
    return all(torch.equal(sa[k], sb[k]) for k in sa if not k.startswith("halt."))


def body_maxdiff(a, b):
    sa, sb = a.state_dict(), b.state_dict()
    return max(float((sa[k] - sb[k]).abs().max()) for k in sa if not k.startswith("halt."))


def main():
    torch.set_num_threads(1)
    B.N = P
    # 1. interface
    for name in ("Net", "ARMS", "TRAIN_ROUNDS", "GRAD_ROUNDS", "tensors", "ce_and_exact", "train_loss", "Practice", "Learner"):
        assert hasattr(P, name), name
    assert P.Net is base.Net
    torch.manual_seed(0)
    net0 = P.Net("loop")
    assert net0.weight_count() == 1645726 == base.Net("loop").weight_count()
    assert P.describe()["gap_vs_loop_weights"] == 0
    arms = {"a": (claude_dir_pond_a, 0.001), "b": (claude_dir_pond_b, 0.004), "c": (claude_dir_pond_c, 0.016), "z": (claude_dir_pond_z, 0.0)}
    for name, (mod, lam) in arms.items():
        assert mod.LAMBDA == lam and mod.Learner.LAMBDA == lam and mod.Net is base.Net, name
        assert issubclass(mod.Learner, B.Learner) and "maze_batch" in vars(mod.Learner)
        assert mod.Learner.sleep is B.Learner.sleep and mod.Learner.update is B.Learner.update
        assert mod.Learner.__init__ is B.Learner.__init__

    # 2. the formula on numbers
    g = torch.Generator().manual_seed(3)
    q = torch.randn(5, 7, generator=g)
    c = torch.rand(5, 7, generator=g)
    for lam in (0.0, 0.004, 0.5):
        want, masses = hand_ponder(q.tolist(), c.tolist(), lam)
        got = float(P.ponder_term(q, c, lam))
        assert abs(got - want) < 1e-5, (lam, got, want)
        assert all(abs(sum(m) - 1) < 1e-9 for m in masses)
    # gradient signs. constant cost, lambda > 0: every earlier hazard should rise (negative gradient on the logit)
    qq = torch.zeros(5, 4, requires_grad=True)
    P.ponder_term(qq, torch.full((5, 4), 0.3), 0.05).backward()
    assert bool((qq.grad[:4] < 0).all()), qq.grad
    # lambda = 0 and constant cost: nothing to gain from stopping earlier or later, so no gradient
    qq = torch.zeros(5, 4, requires_grad=True)
    P.ponder_term(qq, torch.full((5, 4), 0.3), 0.0).backward()
    assert float(qq.grad.abs().max()) < 1e-7
    # round 1 costly, round 2 cheap, later costly: hazard at round 1 goes down, at round 2 goes up
    cost = torch.tensor([[2.0], [0.1], [2.0], [2.0], [2.0]]).repeat(1, 4)
    qq = torch.zeros(5, 4, requires_grad=True)
    P.ponder_term(qq, cost, 0.0).backward()
    assert bool((qq.grad[0] > 0).all()) and bool((qq.grad[1] < 0).all()), qq.grad
    # the last round's hazard is never used
    assert float(qq.grad[4].abs().max()) == 0.0

    items = mazes(64)
    assert len({D.layout_key(x) for x in items}) == 64
    batch_a, batch_b = items[:32], items[32:]

    # 5. per-maze CE
    t, s, y = base.tensors(batch_a)
    e, (dr, dc) = net0.embed(t, s)
    with torch.no_grad():
        h = net0.step(torch.zeros_like(e), e, dr, dc)
        logits = net0.read(h)[0]
    pm = P.ce_per_maze(logits, s, y)
    pooled = base.ce_and_exact(logits, s, y)[0]
    fills = s.view(32, -1).float().sum(1)
    assert abs(float((pm * fills).sum() / fills.sum()) - float(pooled)) < 1e-5

    # 3. penalty alone touches only the stop head
    n3 = copy.deepcopy(net0)
    n3.train()
    e, (dr, dc) = n3.embed(t, s)
    hh = torch.zeros_like(e)
    zs, cs = [], []
    with torch.no_grad():
        for _ in range(3):
            hh = n3.step(hh, e.detach(), dr, dc)
            z = n3.ln_out(hh)
            zs.append(z.mean(1))
            cs.append(P.ce_per_maze(n3.head(z), s, y))
    hh = hh.detach()
    for _ in range(2):
        hh = n3.step(hh, e, dr, dc)
        z = n3.ln_out(hh)
        zs.append(z.detach().mean(1))
        cs.append(P.ce_per_maze(n3.head(z).detach(), s, y))
    term = P.ponder_term(torch.stack([n3.halt(x).squeeze(-1) for x in zs]), torch.stack(cs), 0.004)
    term.backward()
    got = {n for n, p in n3.named_parameters() if p.grad is not None and bool(torch.any(p.grad != 0))}
    assert got == {"halt.weight", "halt.bias"}, got

    # 4. body bit-identical to the harness Learner when clipping is off; halt differs; real-clip difference reported
    clip = torch.nn.utils.clip_grad_norm_
    Lb = claude_dir_pond_b.Learner
    try:
        torch.nn.utils.clip_grad_norm_ = lambda params, max_norm, **kw: torch.tensor(0.0)
        n1, n2 = copy.deepcopy(net0), copy.deepcopy(net0)
        l_base, l_mine = B.Learner(n1, 1e-3), Lb(n2, 1e-3)
        for b in (batch_a, batch_b):
            l_base.maze_batch(b)
            l_mine.maze_batch(b)
        assert l_base.steps == l_mine.steps == 2 * B.UPDATES
        assert body_equal(n1, n2), "with clipping off the body must equal the harness learner exactly"
        assert not torch.equal(n1.halt.weight, n2.halt.weight)
        assert n1.halt.weight.grad is None and n2.halt.weight.grad is not None
    finally:
        torch.nn.utils.clip_grad_norm_ = clip
    n5, n6 = copy.deepcopy(net0), copy.deepcopy(net0)
    l5, l6 = B.Learner(n5, 1e-3), Lb(n6, 1e-3)
    for b in (batch_a, batch_b):
        l5.maze_batch(b)
        l6.maze_batch(b)
    clip_diff = body_maxdiff(n5, n6)
    assert all(torch.isfinite(p).all() for p in n6.parameters())

    # 6. counts and scorer
    assert EQ.N_BATCHES * B.UPDATES == EQ.N_UPDATES == 2048
    l3 = Lb(copy.deepcopy(net0), 1e-3)
    for _ in range(3):
        l3.maze_batch(batch_b)
    assert l3.steps == 12
    r = B.score(l3.net, items[:8], fixed_depth=16)
    assert set(r) == {"right", "n", "fixed_right", "mean_rounds", "cap_hits"} and r["n"] == 8
    print(json.dumps({"selftest": "ok", "weights": net0.weight_count(), "lambdas": {k: v[1] for k, v in arms.items()},
                      "body_maxdiff_with_real_clip_after_8_updates": clip_diff, "updates_per_batch": l3.steps // 3}))


if __name__ == "__main__":
    main()
