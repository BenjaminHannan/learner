#!/usr/bin/env python3
"""Three sleep draws for one finished ruler run (the driver ADDENDUM-1 (b) of the H3 folder planned but did not write).

For one run folder from `claude_fewex_eq_bench.py adapt` (it holds adapt.json and k64.pt, k16384.pt) this repeats the harness's own
sleep on the stage checkpoint with three sleep seeds: draw 0 = seed + k (the harness's recorded sleep), draws 1 and 2 = seed + k + 101
and seed + k + 202 (the distill test's DRAW_OFFSETS). It uses the harness's own pool, replay store, old panels, Learner (the plug-in's
if it has one), lr and fixed depth; nothing else changes. Output: one JSON of integer counts of 200 for sums4 and grids5,
{"seed", "plugin", "run", "64": {"sums4": [a, b, c], "grids5": [...]}, "16384": {...}, "draw0_matches_recorded": true/false}.
If draw 0 differs from the recorded sleep in adapt.json the JSON says so and the draws are void (do not use them).

  python3 -B scripts/claude_dir_r2g_sleepdraws.py --plugin claude_dir_r2g_net --arm loop --seed 0 --run-dir <run folder> --out <json>
  python3 -B scripts/claude_dir_r2g_sleepdraws.py merge --h3 <json> --loop <json> --out sleep-draws-s{seed}.json     (pure python)
"""
from __future__ import annotations

import argparse
import copy
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

OFFSETS = (0, 101, 202)
KINDS = ("sums4", "grids5")


def draws(plugin, arm, seed, run_dir, out, threads):
    import torch
    import claude_fewex_bench as B
    import claude_fewex_data as D
    import claude_fewex_eq_bench as Q
    torch.set_num_threads(threads)
    B.N = importlib.import_module(plugin)
    run = json.loads((run_dir / "adapt.json").read_text())
    assert (run["arm"], run["seed"]) == (arm, seed), "run identity mismatch"
    depth, lr = run["fixed_depth"], run["lr"]
    _, banned = D.panels()
    pool, _, _ = Q.make_pool(seed, banned)
    old, replay = D.old_panels(), D.replay_old()
    res = {"seed": seed, "plugin": plugin, "run": str(run_dir)}
    ok = True
    for k in (64, 16384):
        net = B.load_model(run_dir / f"k{k}.pt", arm)
        counts = {n: [] for n in KINDS}
        for off in OFFSETS:
            sleeper = getattr(B.N, "Learner", B.Learner)(copy.deepcopy(net), lr)
            sleeper.sleep(pool[:k], seed + k + off, replay)
            assert sleeper.steps == B.SLEEP_STEPS
            sc = Q.old_scores(sleeper.net, old, depth)
            for n in KINDS:
                counts[n].append(int(sc[n]["right"]))
        rec = {n: int(run["sleep"][str(k)]["old"][n]["right"]) for n in KINDS}
        same = all(counts[n][0] == rec[n] for n in KINDS)
        ok &= same
        res[str(k)] = counts
        res[f"recorded_{k}"] = rec
        print(json.dumps({"k": k, "draws": counts, "recorded": rec, "draw0_matches": same}), flush=True)
    res["draw0_matches_recorded"] = ok
    Path(out).write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")


def merge(h3, loop, out):
    a, b = json.loads(Path(h3).read_text()), json.loads(Path(loop).read_text())
    if not (a["draw0_matches_recorded"] and b["draw0_matches_recorded"]):
        raise SystemExit("draw 0 differs from the recorded sleep on at least one side: the draws are void")
    if a["seed"] != b["seed"]:
        raise SystemExit("seed mismatch")
    doc = {"seed": a["seed"], "h3": {k: a[k] for k in ("64", "16384")}, "loop": {k: b[k] for k in ("64", "16384")}}
    Path(out).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    print("merged", out)


if __name__ == "__main__":
    if sys.argv[1:2] == ["merge"]:
        p = argparse.ArgumentParser()
        p.add_argument("merge")
        p.add_argument("--h3", required=True)
        p.add_argument("--loop", required=True)
        p.add_argument("--out", required=True)
        a = p.parse_args()
        merge(a.h3, a.loop, a.out)
    else:
        p = argparse.ArgumentParser()
        p.add_argument("--plugin", required=True)
        p.add_argument("--arm", default="loop")
        p.add_argument("--seed", type=int, choices=(0, 1), required=True)
        p.add_argument("--run-dir", type=Path, required=True)
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--threads", type=int, default=1)
        a = p.parse_args()
        draws(a.plugin, a.arm, a.seed, a.run_dir, a.out, a.threads)
