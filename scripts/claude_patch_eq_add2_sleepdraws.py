#!/usr/bin/env python3
"""Extra sleep draws for ADDENDUM-2 fix X1 (and report-only P4): old-kind scores after the k=64 and
k=16,384 sleeps, draws 1 and 2, for the patch and the loop with episodes.

Draw 0 is the ladder's own sleep (seed + k, already in adapt.json). Draw d uses sleep seed
seed + k + {101, 202}, the same offsets as scripts/claude_fewex_distill_sleep.py. The harness sleep code
(the plug-in's Learner.sleep, unchanged) starts from the ladder's saved k{k}.pt. For the patch arm the
old kinds are also scored with the patch KEPT at the end of the sleep (before it is zeroed): report only.

  python3 -B scripts/claude_patch_eq_add2_sleepdraws.py --arm patch|loop_ep --seed S --k 64|16384 --draw 1|2
Writes artifacts/claude-patch-eq-20260928/eq-runs/sleepdraws/{arm}-s{S}-k{k}-d{draw}.json (refuses to overwrite).
"""
from __future__ import annotations

import argparse
import copy
import importlib
import json
import subprocess
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_eq_bench as EQ  # noqa: E402

ART = Path(__file__).resolve().parents[1] / "artifacts" / "claude-patch-eq-20260928"
PLUGIN = {"patch": "claude_patch_eq_plugin", "loop_ep": "claude_fewex_net"}
RUN = {"patch": "patch", "loop_ep": "loopep"}       # eq-runs folder prefix
SRC = {"patch": "patch", "loop_ep": "loop_ep"}      # runs/ folder prefix
OFFSET = {1: 101, 2: 202}


def utc():
    return subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True).strip()


def draw(arm, seed, k, d, ckpt_dir=None, source_dir=None, steps=None, out=None):
    B.N = EQ.B.N = importlib.import_module(PLUGIN[arm])
    ckpt_dir = ckpt_dir or ART / "eq-runs" / f"{RUN[arm]}-s{seed}"
    source_dir = source_dir or ART / "runs" / f"{SRC[arm]}-s{seed}"
    out = out or ART / "eq-runs" / "sleepdraws" / f"{arm}-s{seed}-k{k}-d{d}.json"
    if out.exists():
        raise FileExistsError(out)
    start, started = time.monotonic(), utc()
    depth = EQ.identity_source(source_dir, "loop", seed)["fixed_depth"]
    _, banned = D.panels()
    pool, _, digest = EQ.make_pool(seed, banned)
    old, replay = D.old_panels(), D.replay_old()
    net = B.load_model(ckpt_dir / f"k{k}.pt", "loop")
    learner = getattr(B.N, "Learner", B.Learner)(copy.deepcopy(net), 1e-3)
    kept = {}
    if arm == "patch":  # score with the patch still in, at the moment the sleep would zero it
        real = learner.net.remove_patch

        def score_then_remove():
            kept.update(EQ.old_scores(learner.net, old, depth))
            real()
        learner.net.remove_patch = score_then_remove
    if steps is not None:
        B.SLEEP_STEPS = B.N.SLEEP_STEPS = steps
    sleep_seed = seed + k + OFFSET[d]
    seconds = learner.sleep(pool[:k], sleep_seed, replay)
    res = {"arm": arm, "seed": seed, "k": k, "draw": d, "sleep_seed": sleep_seed, "updates": learner.steps,
           "fixed_depth": depth, "support_sha256": digest, "started_utc": started,
           "student_ckpt": str(ckpt_dir / f"k{k}.pt"),
           "old": {n: v["right"] for n, v in EQ.old_scores(learner.net, old, depth).items()},
           "old_patch_kept_report_only": {n: v["right"] for n, v in kept.items()} or None,
           "sleep_seconds": seconds, "seconds_total": time.monotonic() - start, "finished_utc": utc()}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2, sort_keys=True))
    print(json.dumps({"phase": "draw_done", "arm": arm, "seed": seed, "k": k, "draw": d, "old": res["old"],
                      "kept": res["old_patch_kept_report_only"], "seconds": round(res["seconds_total"])}), flush=True)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=tuple(PLUGIN), required=True)
    ap.add_argument("--seed", type=int, choices=(0, 1), required=True)
    ap.add_argument("--k", type=int, choices=(64, 16384), required=True)
    ap.add_argument("--draw", type=int, choices=(1, 2), required=True)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--ckpt-dir", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--steps", type=int, help="SMOKE TEST ONLY; never for a record")
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    draw(a.arm, a.seed, a.k, a.draw, a.ckpt_dir, None, a.steps, a.out)
