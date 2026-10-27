#!/usr/bin/env python3
"""Selftest for the Test D sparse loop (claude_sparse_net.py). No maze is scored.

Checks: weight budget and active weights; the non-MLP parts are the loop's,
name for name and shape for shape; the mixture layer matches a per-cell
reference; the router input is the hidden state only; the harness's one-step
gradient check (every 2-D matrix, every expert and the router); the learner is
the baseline learner exactly when the load-balancing coefficient is 0; a CPU
timing smoke on sums, grids and one 9x9 maze training batch (loss only).
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_net as base  # noqa: E402
import claude_rsn358a_envs as E  # noqa: E402
import claude_sparse_net as S  # noqa: E402


def check_budget():
    d = S.describe()
    assert abs(d["gap_vs_loop_pct"]) <= 2, d
    assert abs(d["stored"] - d["plain_stored"]) / d["stored"] <= .02, d
    return d


def check_same_loop():
    sp, lp = S.Net("loop"), base.Net("loop")
    a = {n: tuple(p.shape) for n, p in sp.named_parameters() if ".mlp." not in n}
    b = {n: tuple(p.shape) for n, p in lp.named_parameters() if ".mlp." not in n}
    assert a == b, set(a) ^ set(b)
    # With the MLP outputs removed, the two nets compute the same thing.
    sp.load_state_dict({**sp.state_dict(), **{k: v for k, v in lp.state_dict().items() if ".mlp." not in k}})
    for net in (sp, lp):
        for blk in net.blocks:
            blk.mlp = ZeroMLP()
    rng = random.Random(5)
    t, s, _ = base.tensors([D.latin_legend(rng, 5) for _ in range(4)])
    with torch.no_grad():
        pa, qa = sp.loop_rounds(t, s, 12)
        pb, qb = lp.loop_rounds(t, s, 12)
    assert torch.equal(pa, pb) and torch.allclose(qa, qb, atol=1e-6)
    return {"non_mlp_parameters": len(a), "identical_without_mlp": True}


class ZeroMLP(torch.nn.Module):
    def forward(self, x):
        return torch.zeros_like(x)


def check_moe_reference():
    torch.manual_seed(3)
    moe = S.MoE(256)
    x = torch.randn(2, 25, 256)
    with torch.no_grad():
        got = moe(x)
        flat = x.reshape(-1, 256)
        ref = torch.zeros_like(flat)
        for i, row in enumerate(flat):
            lg = moe.router(row)
            v, idx = lg.topk(2)
            w = torch.softmax(v, -1)
            ref[i] = sum(w[j] * moe.experts[int(idx[j])](row) for j in range(2))
    err = (got.reshape(-1, 256) - ref).abs().max().item()
    assert err < 1e-5, err
    # router is a bias-free linear map of the cell's hidden state only
    assert moe.router.bias is None and moe.router.in_features == 256
    return {"max_abs_error_vs_per_cell_reference": err}


def check_gradients(net=None, require=True):
    B.N = S
    if net is None:
        torch.manual_seed(0)
        net = S.Net("loop")
    gc = B.gradient_check(net, 0)
    assert gc["nonzero_all"] or not require, gc
    names = [n for n, p in net.named_parameters() if p.ndim == 2]
    experts = sorted({n.rsplit(".fc", 1)[0] for n in names if ".experts." in n})
    routers = [n for n in names if n.endswith("router.weight")]
    # per-batch detail: which experts see gradient on sums alone and on grids alone
    rng = random.Random(9242700)
    per = {}
    for name, batch in (("sums4", [E.make_sum(rng, 4) for _ in range(32)]),
                        ("grids5", [D.latin_legend(rng, 5) for _ in range(32)])):
        net.zero_grad(set_to_none=True)
        S.train_loss(net, batch, rng).backward()
        per[name] = sorted(n for n, p in net.named_parameters()
                           if p.ndim == 2 and (p.grad is None or not bool(torch.any(p.grad != 0))))
    B.N = base
    return {**gc, "expert_count": len(experts), "router_matrices": routers,
            "zero_on_sums_only_batch": per["sums4"], "zero_on_grids_only_batch": per["grids5"]}


def check_learner_equivalence():
    """AUX_COEF=0: the plug-in learner must leave the same weights as the baseline learner."""
    saved = S.AUX_COEF, S.SLEEP_STEPS, B.SLEEP_STEPS
    S.AUX_COEF, S.SLEEP_STEPS, B.SLEEP_STEPS = 0.0, 3, 3
    B.N = base   # the baseline learner's own helpers
    try:
        torch.manual_seed(1)
        net = S.Net("loop")
        rng = random.Random(77)
        mazes = [D.make_maze(rng, 7) for _ in range(8)]   # training input only, never scored
        old = D.replay_old()
        a, b = S.Learner(copy.deepcopy(net), 1e-3), B.Learner(copy.deepcopy(net), 1e-3)
        for lr_ in (a, b):
            lr_.maze_batch(mazes)
            lr_.sleep(mazes, 5, old)
        same = all(torch.equal(x, y) for x, y in zip(a.net.state_dict().values(), b.net.state_dict().values()))
        assert same and a.steps == b.steps == 4 + 3
    finally:
        S.AUX_COEF, S.SLEEP_STEPS, B.SLEEP_STEPS = saved
    return {"identical_weights_with_aux_0": same, "updates": a.steps}


def timing():
    out = {}
    rng = random.Random(11)
    items = {"sums4": [E.make_sum(rng, 4) for _ in range(64)],
             "grids5": [D.latin_legend(rng, 5) for _ in range(64)],
             "maze9": [D.make_maze(rng, 9) for _ in range(32)]}
    for name, mod in (("sparse", S), ("loop", base)):
        torch.manual_seed(0)
        net = mod.Net("loop")
        opt = torch.optim.AdamW(net.parameters(), lr=1e-3)
        r = {}
        for kind in ("sums4", "grids5"):
            t0 = time.monotonic()
            loss = mod.train_loss(net, items[kind], random.Random(16))  # fixed draw: same rounds both nets
            opt.zero_grad(); loss.backward(); opt.step()
            r[f"practice_step_{kind}_s"] = time.monotonic() - t0
        learner = (S.Learner if mod is S else B.Learner)(net, 1e-3)
        t0 = time.monotonic()
        learner.maze_batch(items["maze9"])
        r["maze_batch_9x9_s"] = time.monotonic() - t0
        t, s, _ = base.tensors(items["maze9"])
        t0 = time.monotonic()
        net.infer_rounds(t, s, 48)
        r["infer_48_rounds_9x9_batch32_s"] = time.monotonic() - t0
        out[name] = r
    return out


def smoke_practice(steps):
    """CPU smoke: the practice recipe's first steps, then the harness gradient check."""
    torch.manual_seed(0)
    rng = random.Random(7000000)
    p = S.Practice("loop", 0, 12000)
    t0, losses = time.monotonic(), []
    for _ in range(steps):
        losses.append(p.step(D.source_batch(rng, 64)))
    seconds = time.monotonic() - t0
    return {"steps": steps, "seconds": seconds, "seconds_per_step": seconds / steps,
            "loss_first20": sum(losses[:20]) / 20, "loss_last20": sum(losses[-20:]) / 20,
            "gradient_check_after": check_gradients(p.net)}


def main(out, smoke_steps):
    torch.set_num_threads(2)
    res = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "device": str(S.DEVICE)}
    for name, fn in (("budget", check_budget), ("same_loop", check_same_loop),
                     ("moe_reference", check_moe_reference), ("gradients_fresh_init", lambda: check_gradients(require=False)),
                     ("learner_equivalence", check_learner_equivalence), ("timing_cpu", timing),
                     ("smoke_practice_cpu", lambda: smoke_practice(smoke_steps))):
        res[name] = fn()
        print(json.dumps({name: res[name]}), flush=True)
    res["selftest"] = "ok"
    if out:
        B.dump(out, res)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path)
    p.add_argument("--smoke-steps", type=int, default=300)
    a = p.parse_args()
    main(a.out, a.smoke_steps)
