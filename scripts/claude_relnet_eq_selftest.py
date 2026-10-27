#!/usr/bin/env python3
"""Selftest and timing probe for the relation-net plug-in (claude_relnet_eq_plugin.py). No maze is scored.

Checks: weight count (1,644,198) and budget; plug-in contract (Net arms, forward = 48 cell + 48 stop logits, infer_rounds
shapes and agreement with forward, tensors/ce_and_exact/train_loss, Practice, Learner); the harness's one-step gradient
check (every 2-D matrix gets a nonzero fp32 gradient on a sums or a grids batch); the Learner does 4 updates per maze
batch, changes the weights, stays finite and is deterministic; the sleep is the baseline's. Then a CPU timing probe
(training loss only; mazes are used as training input, never scored).
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
import claude_relnet_eq_plugin as P  # noqa: E402

B.N = P


def check_budget():
    rel, loop, plain = P.Net("loop"), base.Net("loop"), P.Net("plain")
    n = rel.weight_count()
    assert n == 1644198, n
    assert abs(n - loop.weight_count()) / loop.weight_count() <= .02
    assert abs(n - plain.weight_count()) / n <= .02
    assert type(plain) is base.Net
    return {"relnet": n, "loop": loop.weight_count(), "plain": plain.weight_count(),
            "gap_vs_loop_pct": 100 * (n - loop.weight_count()) / loop.weight_count()}


def check_contract():
    torch.manual_seed(0)
    net = P.Net("loop")
    assert net.arm == "loop"
    rng = random.Random(3)
    items = [D.latin_legend(rng, 5) for _ in range(3)]
    t, s, y = P.tensors(items)
    net.eval()
    with torch.no_grad():
        cells, stops = net.forward(t, s)
        ps, qs = net.infer_rounds(t, s, 48)
    assert len(cells) == len(stops) == 48
    assert cells[0].shape == (3, 35, E.VOCAB) and stops[0].shape == (3,)
    assert ps.shape == (3, 48, 35) and qs.shape == (3, 48)
    assert torch.equal(torch.stack([c.argmax(-1) for c in cells], 1), ps)
    assert torch.allclose(torch.stack([x.sigmoid() for x in stops], 1), qs, atol=1e-5)
    ce, ex = P.ce_and_exact(cells[0], s, y)
    assert ce.ndim == 0 and ex.shape == (3,)
    net.train()
    loss = P.train_loss(net, items, random.Random(1))
    assert loss.ndim == 0 and torch.isfinite(loss)
    # plain arm through the same plug-in
    plain = P.Net("plain")
    c, st = plain.forward(t, s)
    assert len(c) == 1 and st == []
    # Practice and its save / harness load round trip
    p = P.Practice("loop", 0, 10)
    p.step(items)
    path = Path("/tmp/claude_relnet_eq_selftest.pt")
    p.save(path)
    d = torch.load(path, map_location="cpu")
    assert d["arm"] == "loop"
    loaded = P.Net("loop")
    loaded.load_state_dict(d["state"])
    path.unlink()
    return {"ok": True, "practice_step_loss_finite": True}


def check_gradients(net=None):
    if net is None:
        torch.manual_seed(0)
        net = P.Net("loop")
    gc = B.gradient_check(net, 0)
    assert gc["nonzero_all"], gc
    return {**gc, "note": "matrix_count counts every 2-D parameter, embeddings included"}


def check_learner():
    torch.manual_seed(1)
    net = P.Net("loop")
    rng = random.Random(77)
    mazes = [D.make_maze(rng, 7) for _ in range(6)]   # training input only, never scored
    old = D.replay_old()
    saved = B.SLEEP_STEPS
    B.SLEEP_STEPS = 3
    try:
        runs = []
        for _ in range(2):
            lr_ = P.Learner(copy.deepcopy(net), 1e-3)
            lr_.maze_batch(mazes)
            after_maze = copy.deepcopy(lr_.net.state_dict())
            secs = lr_.sleep(mazes, 5, old)
            runs.append((lr_, after_maze))
    finally:
        B.SLEEP_STEPS = saved
    (a, ma), (b, mb) = runs
    assert a.steps == b.steps == 4 + 3, (a.steps, b.steps)
    assert all(torch.equal(x, y) for x, y in zip(ma.values(), mb.values())), "not deterministic"
    changed = sum(not torch.equal(x, y) for x, y in zip(ma.values(), net.state_dict().values()))
    assert changed > 0 and all(torch.isfinite(v).all() for v in ma.values())
    return {"updates_after_maze_batch": 4, "updates_after_3_step_sleep": a.steps, "tensors_changed_by_maze_batch": changed,
            "deterministic": True}


def timing(threads):
    torch.set_num_threads(threads)
    rng = random.Random(11)
    items = {"sums4": [E.make_sum(rng, 4) for _ in range(64)],
             "grids5": [D.latin_legend(rng, 5) for _ in range(64)],
             "maze9": [D.make_maze(rng, 9) for _ in range(32)]}
    torch.manual_seed(0)
    net = P.Net("loop")
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3)
    r = {"threads": threads}
    for kind in ("sums4", "grids5"):
        ts = []
        for i in range(3):
            t0 = time.monotonic()
            loss = P.train_loss(net, items[kind], random.Random(16))   # fixed draw: 16 rounds of 16... same both times
            opt.zero_grad(); loss.backward(); opt.step()
            ts.append(time.monotonic() - t0)
        r[f"practice_step_{kind}_s"] = min(ts)
    # average over the real random round schedule (expected cost), on a mixed stream
    rr, t0 = random.Random(9000), time.monotonic()
    src = random.Random(7000000)
    n = 10
    for _ in range(n):
        loss = P.train_loss(net, D.source_batch(src, 64), rr)
        opt.zero_grad(); loss.backward(); opt.step()
    r["practice_step_stream_mean_s"] = (time.monotonic() - t0) / n
    learner = P.Learner(net, 1e-3)
    t0 = time.monotonic()
    learner.maze_batch(items["maze9"])
    r["maze_batch_9x9_batch32_4updates_s"] = time.monotonic() - t0
    t, s, _ = P.tensors(items["maze9"])
    t0 = time.monotonic()
    net.infer_rounds(t, s, 48)
    r["infer_48_rounds_9x9_batch32_s"] = time.monotonic() - t0
    return r


def main(out, threads, skip_timing):
    res = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "torch": torch.__version__, "device": "cpu", "threads": threads}
    torch.set_num_threads(threads)
    steps = [("budget", check_budget), ("contract", check_contract),
             ("gradients_fresh_init", check_gradients), ("learner", check_learner)]
    if not skip_timing:
        steps.append(("timing_cpu", lambda: timing(threads)))
    for name, fn in steps:
        res[name] = fn()
        print(json.dumps({name: res[name]}), flush=True)
    res["selftest"] = "ok"
    if out:
        B.dump(out, res)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path)
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--skip-timing", action="store_true")
    a = p.parse_args()
    main(a.out, a.threads, a.skip_timing)
