#!/usr/bin/env python3
"""Selftest for the H3 settle-gate loop, version 2, and its constant-g control (ADDENDUM-1 of the H3 folder). No maze is scored.

NOT EXECUTED where it was written (helper H10, 2026-09-28: no torch on that box); it is checked with python3 -m py_compile only.
Run it first on a machine with torch. Every check asserts; the run ends with "selftest": "ok" only if all pass.

Reuse: the v1 selftest (scripts/claude_dir_h3_selftest.py, which passed on the Mac at its first run) is imported and its module
variable `H` is pointed at the v2 plug-in, so every v1 check runs unchanged on v2: budget, same_loop, shapes, gate_init,
gate_open_equals_loop, gate_range, surprise_detached, gradients_fresh_init, practice_smoke, timing_cpu. The v1 `learner` check asserts
that the plug-in has NO Learner (v2 has one on purpose), so it is replaced by `learner_v2`. New checks:
  groups        Practice and Learner build two AdamW groups (decay 0.1 for everything else, 0 for the three gate tensors);
                the plain arm and the constant-g control build one group
  decay_effect  one zero-gradient AdamW step leaves the gate bias exactly unchanged and changes a decayed weight
  const_g       the control has the loop's parameter names, values and 1,645,726 weights, no gate tensors; one round equals
                h + 0.9 (prop - h); its gate is 0.9 with std 0; its practice step and gradient check pass
  gate_std      gate_stats reports std_all, and it is 0 for the control and positive for a moved gate
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
import claude_dir_h3_net_v2 as V  # noqa: E402
import claude_dir_h3_net_v2_const as VC  # noqa: E402
import claude_dir_h3_selftest as T  # noqa: E402
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_net as base  # noqa: E402

T.H = V     # every v1 check now runs on the v2 plug-in (they read the module variable at call time)


def named_ids(net):
    return {id(p): n for n, p in net.named_parameters()}


def check_groups():
    torch.manual_seed(0)
    p = V.Practice("loop", 0, 12000)
    g = p.opt.param_groups
    assert len(g) == 2 and g[0]["weight_decay"] == V.WD == 0.1 and g[1]["weight_decay"] == 0.0, [x["weight_decay"] for x in g]
    ids = named_ids(p.net)
    gate, rest = {ids[id(q)] for q in g[1]["params"]}, {ids[id(q)] for q in g[0]["params"]}
    assert gate == set(V.GATE_PARAMS) and not (gate & rest) and gate | rest == set(ids.values()), (gate, len(rest))
    lrn = V.Learner(V.Net("loop"), 1e-3)
    assert [x["weight_decay"] for x in lrn.opt.param_groups] == [0.1, 0.0]
    assert lrn.sched.optimizer is lrn.opt
    plain = V.Practice("plain", 0, 12000)
    assert len(plain.opt.param_groups) == 1 and plain.opt.param_groups[0]["weight_decay"] == 0.1
    ctl = VC.Practice("loop", 0, 12000)
    assert len(ctl.opt.param_groups) == 1 and ctl.opt.param_groups[0]["weight_decay"] == 0.1
    return {"practice_groups": 2, "learner_groups": 2, "plain_groups": 1, "const_groups": 1, "gate_tensors_exempt": sorted(gate)}


def check_decay_effect():
    torch.manual_seed(0)
    p = V.Practice("loop", 0, 12000)
    named = dict(p.net.named_parameters())
    other = next(n for n, q in named.items() if q.dim() == 2 and n not in V.GATE_PARAMS)
    before = {n: q.detach().clone() for n, q in named.items()}
    for q in p.net.parameters():
        q.grad = torch.zeros_like(q)
    p.opt.step()
    for n in V.GATE_PARAMS:
        assert torch.equal(named[n].detach(), before[n]), n            # zero gradient, no decay: exactly unchanged
    assert not torch.equal(named[other].detach(), before[other]), other  # a decayed weight moved by the decay alone
    return {"gate_unchanged": True, "decayed_weight_changed": other}


def check_learner_v2():
    B.N = V
    torch.manual_seed(1)
    net = V.Net("loop")
    before = copy.deepcopy(net.state_dict())
    rng = random.Random(77)
    mazes = [D.make_maze(rng, 9) for _ in range(B.MAZE_BATCH)]
    old = D.replay_old()
    saved = B.SLEEP_STEPS
    B.SLEEP_STEPS = 3
    try:
        learner = getattr(V, "Learner", B.Learner)(net, 1e-3)
        assert type(learner) is V.Learner and isinstance(learner, B.Learner)
        learner.maze_batch(mazes)
        assert learner.steps == B.UPDATES == 4, learner.steps
        sd = learner.net.state_dict()
        changed_gate = {n: not torch.equal(before[n], sd[n]) for n in V.GATE_PARAMS}
        assert all(changed_gate.values()), changed_gate
        learner.sleep(mazes, 5, old)
        assert learner.steps == 4 + 3, learner.steps
    finally:
        B.SLEEP_STEPS = saved
        B.N = base
    return {"updates_after_batch": 4, "gate_changed": changed_gate, "sleep_updates": 3}


def check_const_g():
    torch.manual_seed(7)
    a = VC.Net("loop")
    torch.manual_seed(7)
    b = base.Net("loop")
    pa, pb = dict(a.named_parameters()), dict(b.named_parameters())
    assert sorted(pa) == sorted(pb), sorted(set(pa) ^ set(pb))          # no gate tensors
    assert all(torch.equal(pa[n], pb[n]) for n in pb)                   # the loop's own random start
    assert a.weight_count() == T.LOOP_WEIGHTS == 1_645_726, a.weight_count()
    d = VC.describe()
    assert d["gate_weights"] == 0 and d["stored"] == T.LOOP_WEIGHTS, d
    a.load_state_dict(b.state_dict())
    a.eval()
    t, s, _ = base.tensors(T.batch("grids", 2))
    e, (dr, dc) = a.embed(t, s)
    h = torch.randn_like(e)
    with torch.no_grad():
        prop = base.Net.step(a, h, e, dr, dc)
        out = a.step(h, e, dr, dc)
    err = float((out - (h + 0.9 * (prop - h))).abs().max())
    assert err < 1e-5, err
    st = a.gate_stats(t, s, 6)
    assert abs(st["mean_all"] - 0.9) < 1e-6 and st["std_all"] < 1e-6 and a.record is None, st
    B.N = VC
    try:
        torch.manual_seed(0)
        p = VC.Practice("loop", 0, 12000)
        rng = random.Random(7000000)
        losses = [p.step(D.source_batch(rng, 64)) for _ in range(5)]
        assert all(x == x and abs(x) < 1e6 for x in losses)
        gc = B.gradient_check(p.net, 0)
        assert gc["nonzero_all"], gc
    finally:
        B.N = base
    return {"same_parameters_as_loop": True, "stored": a.weight_count(), "round_max_abs_error": err,
            "gate_mean": st["mean_all"], "gate_std": st["std_all"], "gradient_check_nonzero_all": True}


def check_gate_std():
    torch.manual_seed(2)
    net = V.Net("loop").eval()
    for q in (net.gate_state.weight, net.gate_surprise):
        q.data.normal_(0, .3)
    t, s, _ = base.tensors(T.batch("mazes", 2))
    st = net.gate_stats(t, s, 10)
    assert st["std_all"] > 0 and "std_all" in st, st
    return {"std_all_moved_gate": st["std_all"], "dead_std_threshold": V.DEAD_STD}


def main(out, smoke_steps):
    torch.set_num_threads(2)
    res = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "device": "cpu", "torch": torch.__version__,
           "plugin": "claude_dir_h3_net_v2 (+ claude_dir_h3_net_v2_const)"}
    for name, fn in (("budget", T.check_budget), ("same_loop", T.check_same_loop), ("shapes", T.check_shapes),
                     ("gate_init", T.check_gate_init), ("gate_open_equals_loop", T.check_gate_open_equals_loop),
                     ("gate_range", T.check_gate_range), ("surprise_detached", T.check_surprise_detached),
                     ("gradients_fresh_init", T.check_gradients), ("groups", check_groups),
                     ("decay_effect", check_decay_effect), ("learner_v2", check_learner_v2),
                     ("gate_std", check_gate_std), ("const_g", check_const_g),
                     ("practice_smoke", lambda: T.check_practice(smoke_steps)), ("timing_cpu", T.timing)):
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
