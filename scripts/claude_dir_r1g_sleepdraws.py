#!/usr/bin/env python3
"""Three-draw sleeps for the old-kind gates (ADDENDUM-1 (b) of the H3 folder, applied to the general reach-channel design).

For one arm ("r1g" with --plugin claude_dir_r1g_net, or "loop" with --plugin claude_fewex_net), one seed and one branch k (64 or 16,384):
load the run's pre-sleep k{K}.pt, rebuild the harness's own support pool pool[:k] and replay store, and run the harness sleep three times
with sleep seed = seed + k + offset for offset in (0, 101, 202) (the distill script's DRAW_OFFSETS). Draw 0 is the harness's own sleep, so
its old-kind counts must equal adapt.json["sleep"][k]["old"] exactly (same code, checkpoint and thread count); if they do not, the file
is written with "draw0_matches": false and the report must treat that seed's draws as void (mark 4 then "skipped").

  python3 scripts/claude_dir_r1g_sleepdraws.py draws --plugin claude_dir_r1g_net --run <eq-runs>/r1g-pre-s0 --k 64 --out <dir>/r1g-s0-k64.json --threads 1
  python3 scripts/claude_dir_r1g_sleepdraws.py merge --seed 0 --dir <dir> --out <dir>/sleep-draws-s0.json     (reads r1g-s0-k{64,16384}.json and loop-s0-k{64,16384}.json)
"""
from __future__ import annotations

import argparse
import copy
import importlib
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_eq_bench as Q  # noqa: E402

OFFSETS = (0, 101, 202)


def draws(plugin, run, k, out):
    B.N = importlib.import_module(plugin)
    adapt = json.loads((run / "adapt.json").read_text())
    seed, depth = adapt["seed"], adapt["fixed_depth"]
    _, banned = D.panels()
    pool, _, digest = Q.make_pool(seed, banned)
    if digest != adapt["support_sha256"]:
        raise ValueError("support pool does not match the recorded run")
    old, replay = D.old_panels(), D.replay_old()
    net0 = B.load_model(run / f"k{k}.pt", "loop")
    recorded = {n: adapt["sleep"][str(k)]["old"][n]["right"] for n in ("sums4", "grids5")}
    res = {"plugin": plugin, "run": str(run), "seed": seed, "k": k, "recorded_draw0": recorded, "draws": []}
    for off in OFFSETS:
        sleeper = getattr(B.N, "Learner", B.Learner)(copy.deepcopy(net0), adapt["lr"])
        sleeper.sleep(pool[:k], seed + k + off, replay)
        if sleeper.steps != B.SLEEP_STEPS:
            raise ValueError("sleep update count")
        sc = Q.old_scores(sleeper.net, old, depth)
        res["draws"].append({"offset": off, "sleep_seed": seed + k + off, **{n: sc[n]["right"] for n in ("sums4", "grids5")}})
        print(json.dumps(res["draws"][-1]), flush=True)
    res["draw0_matches"] = all(res["draws"][0][n] == recorded[n] for n in recorded)
    B.dump(out, res)
    print(json.dumps({"draw0_matches": res["draw0_matches"], "recorded": recorded}))


def merge(seed, folder, out):
    res = {"seed": seed}
    for arm, key in (("r1g", "r1g"), ("loop", "loop")):
        res[key] = {}
        for k in (64, 16384):
            d = json.loads((folder / f"{arm}-s{seed}-k{k}.json").read_text())
            if d["seed"] != seed or d["k"] != k or len(d["draws"]) != 3:
                raise ValueError(f"bad draw file {arm} {k}")
            if not d["draw0_matches"]:
                raise ValueError(f"draw 0 does not equal the recorded sleep for {arm} seed {seed} k {k}: the draws for this seed are void")
            res[key][str(k)] = {n: [x[n] for x in d["draws"]] for n in ("sums4", "grids5")}
    B.dump(out, res)
    print("merged", out)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("draws", "merge"))
    p.add_argument("--plugin", default="claude_dir_r1g_net")
    p.add_argument("--run", type=Path)
    p.add_argument("--k", type=int, choices=(64, 16384))
    p.add_argument("--seed", type=int, choices=(0, 1))
    p.add_argument("--dir", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--threads", type=int, default=1)
    a = p.parse_args()
    torch.set_num_threads(a.threads)
    if a.cmd == "draws":
        draws(a.plugin, a.run, a.k, a.out)
    else:
        merge(a.seed, a.dir, a.out)
