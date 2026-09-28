#!/usr/bin/env python3
"""Selftest for the H3 settle-gate loop (claude_dir_h3_net.py). No maze is scored.

NOT EXECUTED where it was written (no torch there). Run it first on a machine with torch;
every check asserts, and the run ends with "selftest": "ok" only if all pass.

Checks
  budget        exact weight count (loop + 258), inside the 2% band of loop and plain
  same_loop     every non-gate parameter has the loop's name and shape, and (same torch
                seed) the same random init values
  shapes        forward gives 48 cell tensors [B,T,V] and 48 stop tensors [B]; infer_rounds
                gives [B,n,T] and [B,n]; the plain arm is untouched (weights, outputs)
  gate_init     at init the gate is sigmoid(4) everywhere (state weight 0, surprise weight 0)
  gate_open     with the gate forced fully open, the net equals the baseline loop (same weights)
  gate_range    gate values stay strictly inside (0,1); stats API works
  surprise_detached  the surprise term carries no gradient into the blocks by itself
  gradients     the harness's one-step check (every 2-D matrix nonzero on sums or grids) at fresh
                init, plus the three gate tensors nonzero, plus the halt head
  learner       the baseline learner runs one maze batch: exactly 4 updates, weights change,
                gate tensors change; sleep runs 3 updates
  practice      Practice steps, saves and load_net reloads to identical outputs; a short
                smoke run lowers the loss and the gradient check still passes
  timing        CPU seconds for a practice step and a 9x9 maze batch, against the loop
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
import tempfile
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_h3_net as H  # noqa: E402
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_net as base  # noqa: E402
import claude_rsn358a_envs as E  # noqa: E402

LOOP_WEIGHTS, PLAIN_WEIGHTS, GATE_WEIGHTS = 1_645_726, 1_619_965, 258


def batch(kind, n=4, seed=5):
    rng = random.Random(seed)
    if kind == "sums":
        return [E.make_sum(rng, 4) for _ in range(n)]
    if kind == "grids":
        return [D.latin_legend(rng, 5) for _ in range(n)]
    return [D.make_maze(rng, 9) for _ in range(n)]     # training-shaped input only, never scored


def check_budget():
    d = H.describe()
    assert d["loop_stored"] == LOOP_WEIGHTS and d["plain_stored"] == PLAIN_WEIGHTS, d
    assert d["gate_weights"] == GATE_WEIGHTS, d
    assert d["stored"] == LOOP_WEIGHTS + GATE_WEIGHTS == 1_645_984, d
    assert abs(d["gap_vs_loop_pct"]) <= 2 and abs(d["stored"] - d["plain_stored"]) / d["stored"] <= .02, d
    return d


def check_same_loop():
    torch.manual_seed(7)
    a = H.Net("loop")
    torch.manual_seed(7)
    b = base.Net("loop")
    sa, sb = dict(a.named_parameters()), dict(b.named_parameters())
    extra = sorted(set(sa) - set(sb))
    assert extra == ["gate_state.bias", "gate_state.weight", "gate_surprise"], extra
    assert not set(sb) - set(sa)
    for n, p in sb.items():
        assert sa[n].shape == p.shape and torch.equal(sa[n], p), n
    return {"shared_parameters": len(sb), "same_init_values": True, "gate_tensors": extra}


def check_shapes():
    torch.manual_seed(0)
    net = H.Net("loop").eval()
    t, s, _ = base.tensors(batch("grids", 3))
    with torch.no_grad():
        cells, stops = net.forward(t, s)
        preds, qs = net.infer_rounds(t, s, 12)
    B_, T_ = t.shape[0], t.shape[1] * t.shape[2]
    assert len(cells) == 48 and len(stops) == 48
    assert all(tuple(c.shape) == (B_, T_, E.VOCAB) for c in cells)
    assert all(tuple(x.shape) == (B_,) for x in stops)
    assert tuple(preds.shape) == (B_, 12, T_) and tuple(qs.shape) == (B_, 12)
    assert torch.isfinite(torch.stack(cells)).all() and torch.isfinite(torch.stack(stops)).all()
    torch.manual_seed(0)
    p_h, p_b = H.Net("plain").eval(), base.Net("plain").eval()
    p_b.load_state_dict(p_h.state_dict())
    with torch.no_grad():
        same = torch.equal(p_h.forward(t, s)[0][0], p_b.forward(t, s)[0][0])
    assert same and p_h.weight_count() == PLAIN_WEIGHTS
    return {"cells": len(cells), "stops": len(stops), "plain_unchanged": True}


def check_gate_init():
    torch.manual_seed(0)
    net = H.Net("loop").eval()
    assert float(net.gate_state.weight.abs().max()) == 0.0 and float(net.gate_surprise.abs().max()) == 0.0
    t, s, _ = base.tensors(batch("mazes", 2))
    st = net.gate_stats(t, s, 6)
    import math
    want = 1 / (1 + math.exp(-H.GATE_BIAS_INIT))
    assert abs(st["min"] - want) < 1e-5 and abs(st["max"] - want) < 1e-5, st
    return {"gate_at_init": want, "min": st["min"], "max": st["max"]}


def check_gate_open_equals_loop():
    torch.manual_seed(1)
    b = base.Net("loop").eval()
    h = H.Net("loop").eval()
    h.load_state_dict({**h.state_dict(), **b.state_dict()})
    h.gate_state.bias.data.fill_(60.0)                 # sigmoid(60) == 1.0 in fp32
    h.gate_state.weight.data.zero_()
    h.gate_surprise.data.zero_()
    t, s, _ = base.tensors(batch("grids", 3))
    with torch.no_grad():
        ca, qa = h.forward(t, s)
        cb, qb = b.forward(t, s)
    err = max(float((x - y).abs().max()) for x, y in zip(ca[:12], cb[:12]))
    qerr = max(float((x - y).abs().max()) for x, y in zip(qa[:12], qb[:12]))
    assert err < 1e-3 and qerr < 1e-3, (err, qerr)     # h + 1*(prop - h) differs from prop only by rounding
    pa, _ = h.loop_rounds(t, s, 12)
    pb, _ = b.loop_rounds(t, s, 12)
    agree = float((pa == pb).float().mean())
    assert agree >= 0.99, agree                        # a rounding-level tie may flip a rare cell
    return {"max_logit_abs_error_12_rounds": err, "max_stop_abs_error_12_rounds": qerr, "prediction_agreement_12_rounds": agree}


def check_gate_range():
    torch.manual_seed(2)
    net = H.Net("loop").eval()
    for p in (net.gate_state.weight, net.gate_surprise):     # move the gate off its init
        p.data.normal_(0, .3)
    t, s, _ = base.tensors(batch("mazes", 2))
    st = net.gate_stats(t, s, 10)
    assert 0.0 < st["min"] <= st["max"] < 1.0 and len(st["mean_by_round"]) == 10, st
    assert net.record is None
    return {"min": st["min"], "max": st["max"], "rounds": 10}


def check_surprise_detached():
    """Freeze the blocks' output path: with the gate weights only trainable through the surprise
    term (state weight fixed at 0), the surprise scalar gets a gradient but nothing upstream
    of it does through that path."""
    torch.manual_seed(3)
    net = H.Net("loop").train()
    t, s, y = base.tensors(batch("grids", 2))
    e, (dr, dc) = net.embed(t, s)
    h0 = torch.zeros_like(e)
    e = e.detach().requires_grad_(True)
    h0.requires_grad_(True)
    net.gate_state.weight.requires_grad_(False)
    net.gate_state.bias.data.fill_(0.0)
    net.gate_surprise.data.fill_(1.0)
    out = net.step(h0, e, dr, dc)
    out.sum().backward()
    # gradient exists on e through the proposal path (the loop's own), and on the surprise weight
    assert net.gate_surprise.grad is not None and float(net.gate_surprise.grad.abs()) > 0
    # the same forward with surprise computed as a live tensor would give a different gradient on e:
    g_detached = e.grad.clone()
    net.zero_grad(set_to_none=True)
    e.grad = None
    h0.grad = None
    prop = base.Net.step(net, h0, e, dr, dc)
    live = torch.log((prop - h0).pow(2).mean(-1, keepdim=True) + H.SURPRISE_EPS)
    g = torch.sigmoid(net.gate_state(prop) + net.gate_surprise * live)
    (h0 + g * (prop - h0)).sum().backward()
    assert not torch.allclose(g_detached, e.grad), "surprise looks live, not detached"
    net.gate_state.weight.requires_grad_(True)
    return {"surprise_weight_grad_nonzero": True, "detached_differs_from_live": True}


def check_gradients():
    B.N = H
    torch.manual_seed(0)
    net = H.Net("loop")
    gc = B.gradient_check(net, 0)
    assert gc["nonzero_all"], gc
    net.zero_grad(set_to_none=True)
    rng = random.Random(9242700)
    H.train_loss(net, [E.make_sum(rng, 4) for _ in range(16)] , rng).backward()
    named = dict(net.named_parameters())
    gate = {n: float(named[n].grad.abs().sum()) for n in ("gate_state.weight", "gate_state.bias", "gate_surprise")}
    halt = float(named["halt.weight"].grad.abs().sum())
    assert all(v > 0 for v in gate.values()) and halt > 0, (gate, halt)
    net.zero_grad(set_to_none=True)
    B.N = base
    return {**gc, "gate_grad_abs_sum": gate, "halt_grad_abs_sum": halt}


def check_learner():
    B.N = H
    torch.manual_seed(1)
    net = H.Net("loop")
    before = copy.deepcopy(net.state_dict())
    rng = random.Random(77)
    mazes = [D.make_maze(rng, 9) for _ in range(B.MAZE_BATCH)]
    old = D.replay_old()
    saved = B.SLEEP_STEPS
    B.SLEEP_STEPS = 3
    try:
        learner = getattr(H, "Learner", B.Learner)(net, 1e-3)
        assert not hasattr(H, "Learner")               # the harness must fall back to the baseline learner
        learner.maze_batch(mazes)
        assert learner.steps == B.UPDATES == 4, learner.steps
        changed_gate = {n: not torch.equal(before[n], learner.net.state_dict()[n])
                        for n in ("gate_state.weight", "gate_state.bias", "gate_surprise")}
        changed = sum(not torch.equal(before[n], v) for n, v in learner.net.state_dict().items())
        assert changed > 0 and all(changed_gate.values()), changed_gate
        learner.sleep(mazes, 5, old)
        assert learner.steps == 4 + 3, learner.steps
    finally:
        B.SLEEP_STEPS = saved
        B.N = base
    return {"updates_after_batch": 4, "tensors_changed": changed, "gate_changed": changed_gate, "sleep_updates": 3}


def check_practice(steps):
    B.N = H
    torch.manual_seed(0)
    rng = random.Random(7000000)
    p = H.Practice("loop", 0, 12000)
    losses = [p.step(D.source_batch(rng, 64)) for _ in range(steps)]
    assert all(x == x and abs(x) < 1e6 for x in losses)
    n = min(20, steps // 2)
    first, last = sum(losses[:n]) / n, sum(losses[-n:]) / n
    assert last < first, (first, last)
    gc = B.gradient_check(p.net, 0)
    assert gc["nonzero_all"], gc
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "ck.pt"
        p.save(path)
        again = H.load_net(path)
    t, s, _ = base.tensors(batch("sums", 3))
    p.net.eval()
    again.eval()
    with torch.no_grad():
        same = torch.equal(p.net.loop_rounds(t, s, 6)[0], again.loop_rounds(t, s, 6)[0])
    assert same
    gs = p.net.gate_stats(t, s, 6)
    B.N = base
    return {"steps": steps, "loss_first": first, "loss_last": last, "reload_identical": same,
            "gate_after_smoke": {"mean_all": gs["mean_all"], "min": gs["min"], "max": gs["max"]},
            "gradient_check_after": gc}


def timing():
    out, rng = {}, random.Random(11)
    items = {"sums4": [E.make_sum(rng, 4) for _ in range(64)],
             "grids5": [D.latin_legend(rng, 5) for _ in range(64)],
             "maze9": [D.make_maze(rng, 9) for _ in range(32)]}
    for name, mod in (("h3", H), ("loop", base)):
        B.N = mod
        torch.manual_seed(0)
        net = mod.Net("loop")
        opt = torch.optim.AdamW(net.parameters(), lr=1e-3)
        r = {}
        for kind in ("sums4", "grids5"):
            t0 = time.monotonic()
            loss = mod.train_loss(net, items[kind], random.Random(16))
            opt.zero_grad()
            loss.backward()
            opt.step()
            r[f"practice_step_{kind}_s"] = time.monotonic() - t0
        t0 = time.monotonic()
        B.Learner(net, 1e-3).maze_batch(items["maze9"])
        r["maze_batch_9x9_s"] = time.monotonic() - t0
        t, s, _ = base.tensors(items["maze9"])
        t0 = time.monotonic()
        net.infer_rounds(t, s, 48)
        r["infer_48_rounds_9x9_batch32_s"] = time.monotonic() - t0
        out[name] = r
    B.N = base
    return out


def main(out, smoke_steps):
    torch.set_num_threads(2)
    res = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "device": "cpu", "torch": torch.__version__}
    for name, fn in (("budget", check_budget), ("same_loop", check_same_loop), ("shapes", check_shapes),
                     ("gate_init", check_gate_init), ("gate_open_equals_loop", check_gate_open_equals_loop),
                     ("gate_range", check_gate_range), ("surprise_detached", check_surprise_detached),
                     ("gradients_fresh_init", check_gradients), ("learner", check_learner),
                     ("practice_smoke", lambda: check_practice(smoke_steps)), ("timing_cpu", timing)):
        res[name] = fn()
        print(json.dumps({name: res[name]}), flush=True)
    res["selftest"] = "ok"
    print(json.dumps({"selftest": "ok"}))
    if out:
        B.dump(out, res)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path)
    p.add_argument("--smoke-steps", type=int, default=200)
    a = p.parse_args()
    main(a.out, a.smoke_steps)
