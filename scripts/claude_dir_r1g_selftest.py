#!/usr/bin/env python3
"""CPU self-test for the general reach-channel design (scripts/claude_dir_r1g_net.py). No maze is scored.

Every check asserts; the run ends with "selftest": "ok" only if all pass. CPU, fp32.
  budget            8,472 extra weights, 1,654,198 stored, +0.515% over the loop, inside the 1% band, plain 1,619,965
  same_loop         loop parameters get the baseline's random init; with the zero-initialised mix one round and 6 rounds of inference
                    equal the baseline loop exactly on sums, grids and mazes (the design starts as the loop)
  reach_exact       S from repeated squaring equals the brute-force sum of M^0..M^63 (float64); every S row sum is at most cap
  features_range    the ten features are finite and inside [0, 1] on real inputs and on inputs scaled x50 (no blow-up)
  equivariance      a random permutation of the items (offsets permuted with them) permutes the features and the round output
  set_input         the channel runs on 37 unordered items with no grid at all (offsets all equal) and on 81 items
  no_kind_words     the design file, read as code with its docstrings removed, has no identifier or string with maze / wall / route / start /
                    goal / grid / puzzle / kind / sudoku / sum, and step() reads only (h, e, dr, dc)
  gradients         fresh init: only mix gets gradient (documented: mix is zero); after mix is set nonzero every 2-D weight gets one
  groups            Practice and Learner build two AdamW groups (decay 0.1; 0 for gamma, link bias, probe bias); plain arm one group
  decay_effect      a zero-gradient AdamW step leaves the exempt tensors exactly unchanged and moves a decayed weight
  learner           the harness Learner subclass runs 4 updates on a maze batch and a short sleep; mix moved
  credit_off        REACH_OFF with a nonzero mix changes the output; with the zero mix it equals the loop
  practice_smoke    a short practice on sums and grids: loss falls, gradient_check nonzero_all, reload identical, reach_stats printed
  timing_cpu        seconds per practice step, maze batch and 48-round inference, this design and the loop
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import math
import random
import sys
import tempfile
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_r1g_net as R  # noqa: E402
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_net as base  # noqa: E402
import claude_rsn358a_envs as E  # noqa: E402

LOOP_WEIGHTS, PLAIN_WEIGHTS, EXTRA = 1_645_726, 1_619_965, 8_472
EXEMPT = {"reach_g", "link_b", "probe.bias"}


def batch(kind, n=4, seed=5):
    rng = random.Random(seed)
    if kind == "sums":
        return [E.make_sum(rng, 4) for _ in range(n)]
    if kind == "grids":
        return [D.latin_legend(rng, 5) for _ in range(n)]
    return [D.make_maze(rng, 9) for _ in range(n)]     # training-shaped input only, never scored


def randomise_mix(net, seed=3, scale=0.2):
    g = torch.Generator().manual_seed(seed)
    with torch.no_grad():
        net.mix.weight.copy_(torch.randn(net.mix.weight.shape, generator=g) * scale)
        net.mix.bias.copy_(torch.randn(net.mix.bias.shape, generator=g) * scale)
        for p in (net.wq.weight, net.wk.weight, net.probe.weight):
            p.copy_(torch.randn(p.shape, generator=g) * 0.3)


def check_budget():
    d = R.describe()
    assert d["loop_stored"] == LOOP_WEIGHTS and d["plain_stored"] == PLAIN_WEIGHTS, d
    assert d["reach_weights"] == EXTRA and d["stored"] == LOOP_WEIGHTS + EXTRA == 1_654_198, d
    assert 0 < d["gap_vs_loop_pct"] < 1.0 and abs(d["gap_vs_loop_pct"] - 0.5148) < 1e-3, d
    names = {n for n, _ in R.Net("loop").named_parameters()} - {n for n, _ in base.Net("loop").named_parameters()}
    assert names == {"reach_ln.weight", "reach_ln.bias", "wq.weight", "wk.weight", "link_r", "link_c", "link_b", "probe.weight",
                     "probe.bias", "reach_g", "mix.weight", "mix.bias"}, names
    assert R.Net("plain").weight_count() == PLAIN_WEIGHTS       # the plain arm is untouched
    d["new_parameter_names"] = sorted(names)
    return d


def check_same_loop():
    torch.manual_seed(7)
    a = R.Net("loop")
    torch.manual_seed(7)
    b = base.Net("loop")
    pa, pb = dict(a.named_parameters()), dict(b.named_parameters())
    assert all(torch.equal(pa[n], pb[n]) for n in pb)
    a.eval(), b.eval()
    out = {}
    for kind in ("sums", "grids", "mazes"):
        t, s, _ = base.tensors(batch(kind, 3))
        with torch.no_grad():
            e, (dr, dc) = a.embed(t, s)
            h = torch.randn_like(e)
            one = float((a.step(h, e, dr, dc) - b.step(h, e, dr, dc)).abs().max())
            pa_, qa = a.loop_rounds(t, s, 6)
            pb_, qb = b.loop_rounds(t, s, 6)
        assert one == 0.0 and torch.equal(pa_, pb_) and torch.equal(qa, qb), (kind, one)
        out[kind] = {"one_round_max_abs_diff": one, "six_rounds_identical": True}
    return out


def check_reach_exact():
    torch.manual_seed(1)
    T = 12
    P = torch.softmax(torch.randn(3, T, T, dtype=torch.float64), -1)
    gamma = 0.95
    M = gamma * P
    S = R.reach_matrix(M)
    brute, Mn = torch.zeros_like(M), torch.eye(T, dtype=torch.float64).expand_as(M).clone()
    for _ in range(64):
        brute += Mn
        Mn = Mn @ M
    err = float((S - brute).abs().max())
    cap = (1 - gamma ** 64) / (1 - gamma)
    assert err < 1e-9, err
    assert float(S.sum(-1).max()) <= cap + 1e-9 and float(S.sum(-1).min()) >= 1.0 - 1e-9
    return {"max_abs_error_vs_brute_force": err, "cap": cap, "max_row_sum": float(S.sum(-1).max())}


def check_features_range():
    torch.manual_seed(2)
    net = R.Net("loop").eval()
    randomise_mix(net)
    res = {}
    for kind in ("sums", "grids", "mazes"):
        t, s, _ = base.tensors(batch(kind, 3))
        with torch.no_grad():
            e, (dr, dc) = net.embed(t, s)
            for scale in (1.0, 50.0):
                f = net.reach_features(torch.randn_like(e) * scale, dr, dc)
                assert torch.isfinite(f).all() and float(f.min()) >= -1e-6 and float(f.max()) <= 1 + 1e-5, (kind, scale, float(f.min()), float(f.max()))
        res[kind] = {"min": float(f.min()), "max": float(f.max()), "shape": list(f.shape)}
    assert res["mazes"]["shape"] == [3, 81, R.FEATURES]
    return res


def check_equivariance():
    torch.manual_seed(4)
    net = R.Net("loop").eval()
    randomise_mix(net)
    t, s, _ = base.tensors(batch("mazes", 2))
    with torch.no_grad():
        e, (dr, dc) = net.embed(t, s)
        h = torch.randn_like(e)
        z = torch.randn_like(e)
        perm = torch.randperm(81, generator=torch.Generator().manual_seed(9))
        dr2, dc2 = dr[perm][:, perm], dc[perm][:, perm]      # the offsets follow the items
        f = net.reach_features(z, dr, dc)
        f2 = net.reach_features(z[:, perm], dr2, dc2)
        d1 = float((f[:, perm] - f2).abs().max())
        o = net.step(h, e, dr, dc)
        o2 = net.step(h[:, perm], e[:, perm], dr2, dc2)
        d2 = float((o[:, perm] - o2).abs().max())
    assert d1 < 1e-5 and d2 < 1e-4, (d1, d2)
    return {"features_max_abs_diff": d1, "round_output_max_abs_diff": d2}


def check_set_input():
    torch.manual_seed(5)
    net = R.Net("loop").eval()
    randomise_mix(net)
    out = {}
    for T in (37, 81):
        z = torch.randn(2, T, 256)
        zero = torch.full((T, T), base.CLIP, dtype=torch.long)       # no positions at all: every pair has the same offset
        with torch.no_grad():
            f = net.reach_features(z, zero, zero)
        assert f.shape == (2, T, R.FEATURES) and torch.isfinite(f).all()
        out[str(T)] = {"shape": list(f.shape)}
    return out


def check_no_kind_words():
    src = Path(R.__file__).read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):                                   # drop every docstring
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and node.body and isinstance(node.body[0], ast.Expr) \
                and isinstance(getattr(node.body[0], "value", None), ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:] or [ast.Pass()]
    words = ("maze", "wall", "route", "start", "goal", "grid", "puzzle", "kind", "sudoku", "sum", "latin", "digit")
    bad = []
    for node in ast.walk(tree):
        toks = []
        if isinstance(node, ast.Name):
            toks = [node.id]
        elif isinstance(node, ast.Attribute):
            toks = [node.attr]
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            toks = [node.name]
        elif isinstance(node, ast.arg):
            toks = [node.arg]
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            toks = [node.value]
        for tk in toks:
            if any(w in tk.lower() for w in words):
                bad.append(tk)
    # `sum` is allowed only as the torch method name a.sum / S.sum
    bad = [x for x in bad if x != "sum"]
    assert not bad, bad
    co = R.Net.step.__code__
    step_args = list(co.co_varnames[:co.co_argcount])
    assert step_args == ["self", "h", "e", "dr", "dc"], step_args
    return {"forbidden_words_found": 0, "step_inputs": step_args}


def check_gradients():
    torch.manual_seed(6)
    net = R.Net("loop")
    t, s, y = base.tensors(batch("sums", 4))
    rng = random.Random(1)
    R.train_loss(net, batch("sums", 4), rng).backward()
    dead = sorted(n for n, p in net.named_parameters() if p.dim() == 2 and (p.grad is None or float(p.grad.abs().max()) == 0))
    fresh_alive = sorted(n for n, p in net.named_parameters() if p.dim() == 2 and p.grad is not None and float(p.grad.abs().max()) > 0)
    assert "mix.weight" in fresh_alive and "wq.weight" in dead, (dead, fresh_alive)       # zero mix: upstream gets no gradient yet
    torch.manual_seed(6)
    net = R.Net("loop")
    randomise_mix(net)
    R.train_loss(net, batch("sums", 4), random.Random(1)).backward()
    dead2 = sorted(n for n, p in net.named_parameters() if p.dim() == 2 and (p.grad is None or float(p.grad.abs().max()) == 0))
    assert not dead2, dead2
    return {"fresh_init_2d_without_gradient": dead, "after_mix_nonzero_2d_without_gradient": dead2}


def named_ids(net):
    return {id(p): n for n, p in net.named_parameters()}


def check_groups():
    torch.manual_seed(0)
    p = R.Practice("loop", 0, 12000)
    g = p.opt.param_groups
    assert len(g) == 2 and g[0]["weight_decay"] == R.WD == 0.1 and g[1]["weight_decay"] == 0.0
    ids = named_ids(p.net)
    free, rest = {ids[id(q)] for q in g[1]["params"]}, {ids[id(q)] for q in g[0]["params"]}
    assert free == EXEMPT and not (free & rest) and free | rest == set(ids.values()), (free, len(rest))
    lrn = R.Learner(R.Net("loop"), 1e-3)
    assert [x["weight_decay"] for x in lrn.opt.param_groups] == [0.1, 0.0] and lrn.sched.optimizer is lrn.opt
    plain = R.Practice("plain", 0, 12000)
    assert len(plain.opt.param_groups) == 1 and plain.opt.param_groups[0]["weight_decay"] == 0.1
    return {"practice_groups": 2, "learner_groups": 2, "plain_groups": 1, "exempt": sorted(free)}


def check_decay_effect():
    torch.manual_seed(0)
    p = R.Practice("loop", 0, 12000)
    named = dict(p.net.named_parameters())
    other = "mix.weight"
    with torch.no_grad():
        named[other].fill_(0.5)
    before = {n: q.detach().clone() for n, q in named.items()}
    for q in p.net.parameters():
        q.grad = torch.zeros_like(q)
    p.opt.step()
    for n in EXEMPT:
        assert torch.equal(named[n].detach(), before[n]), n
    assert not torch.equal(named[other].detach(), before[other])
    return {"exempt_unchanged": True, "decayed_weight_changed": other}


def check_learner():
    B.N = R
    torch.manual_seed(1)
    net = R.Net("loop")
    before = copy.deepcopy(net.state_dict())
    rng = random.Random(77)
    mazes = [D.make_maze(rng, 9) for _ in range(B.MAZE_BATCH)]
    old = D.replay_old()
    saved = B.SLEEP_STEPS
    B.SLEEP_STEPS = 3
    try:
        learner = R.Learner(net, 1e-3)
        assert type(learner) is R.Learner and isinstance(learner, B.Learner)
        learner.maze_batch(mazes)
        assert learner.steps == B.UPDATES == 4
        sd = learner.net.state_dict()
        moved = {n: not torch.equal(before[n], sd[n]) for n in ("mix.weight", "mix.bias", "reach_g")}
        assert moved["mix.weight"] and moved["mix.bias"], moved
        learner.sleep(mazes, 5, old)
        assert learner.steps == 4 + 3
    finally:
        B.SLEEP_STEPS = saved
        B.N = base
    return {"updates_after_batch": 4, "moved": moved, "sleep_updates": 3}


def check_credit_off():
    torch.manual_seed(8)
    net = R.Net("loop").eval()
    t, s, _ = base.tensors(batch("mazes", 2))
    try:
        R.Net.REACH_OFF = True
        with torch.no_grad():
            off_zero = net.loop_rounds(t, s, 5)[0]
        R.Net.REACH_OFF = False
        with torch.no_grad():
            on_zero = net.loop_rounds(t, s, 5)[0]
        assert torch.equal(off_zero, on_zero)                      # zero mix: switching the features off changes nothing
        randomise_mix(net)
        e, (dr, dc) = net.embed(t, s)
        with torch.no_grad():
            h = torch.randn_like(e)
            on_h = net.step(h, e, dr, dc)
            on = net.loop_rounds(t, s, 5)[0]
            R.Net.REACH_OFF = True
            off_h = net.step(h, e, dr, dc)
            off = net.loop_rounds(t, s, 5)[0]
    finally:
        R.Net.REACH_OFF = False
    diff = float((on_h - off_h).abs().max())
    assert diff > 1e-3, diff
    return {"zero_mix_off_equals_on": True, "nonzero_mix_state_max_abs_change": diff,
            "answers_changed_of_total": [int((on != off).sum()), int(on.numel())]}


def check_practice(steps):
    B.N = R
    torch.manual_seed(0)
    rng = random.Random(7000000)
    p = R.Practice("loop", 0, 12000)
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
        again = R.load_net(path)
    t, s, _ = base.tensors(batch("sums", 3))
    p.net.eval(), again.eval()
    with torch.no_grad():
        same = torch.equal(p.net.loop_rounds(t, s, 6)[0], again.loop_rounds(t, s, 6)[0])
    assert same
    st = p.net.reach_stats(t, s, 6)
    B.N = base
    return {"steps": steps, "loss_first": first, "loss_last": last, "reload_identical": same,
            "reach_stats_after_smoke": st, "gradient_check_after": gc}


def timing():
    out, rng = {}, random.Random(11)
    items = {"sums4": [E.make_sum(rng, 4) for _ in range(64)], "grids5": [D.latin_legend(rng, 5) for _ in range(64)],
             "maze9": [D.make_maze(rng, 9) for _ in range(32)]}
    for name, mod in (("r1g", R), ("loop", base)):
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
    res = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "device": "cpu", "torch": torch.__version__,
           "plugin": "claude_dir_r1g_net"}
    for name, fn in (("budget", check_budget), ("same_loop", check_same_loop), ("reach_exact", check_reach_exact),
                     ("features_range", check_features_range), ("equivariance", check_equivariance),
                     ("set_input", check_set_input), ("no_kind_words", check_no_kind_words),
                     ("gradients", check_gradients), ("groups", check_groups), ("decay_effect", check_decay_effect),
                     ("learner", check_learner), ("credit_off", check_credit_off),
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
