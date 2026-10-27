#!/usr/bin/env python3
"""Read-only dev recount of stopped loop seed 1 checkpoints after V3 failed."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import torch

import claude_fewex_bench as B
import claude_fewex_data as D

ROOT = Path(__file__).resolve().parents[1] / "artifacts" / "claude-fewex-20260927" / "runs"
RUNGS = ("0", "1", "4", "16", "64", "256", "1024", "4096", "16384")


def main():
    torch.set_num_threads(2)
    panel, _ = D.panels()
    old = D.old_panels()
    stamp = subprocess.check_output(["date", "-u", "+%Y-%m-%d %H:%M:%S UTC"], text=True).strip()
    for init in ("pre", "fresh"):
        root = ROOT / f"loop-s1-{init}"
        fixed = json.loads((ROOT / "qual-loop-s1" / "source.json").read_text())["fixed_depth"]
        scores = {}
        for rung in RUNGS:
            net = B.load_model(root / f"k{rung}.pt", "loop")
            scores[rung] = B.score(net, panel["dev"][9], fixed)
        old_scores = {}
        for label, file in (("before", "k0.pt"), ("after_64", "k64.pt"),
                            ("sleep64", "sleep64.pt")):
            net = B.load_model(root / file, "loop")
            old_scores[label] = {k: B.score(net, v, fixed) for k, v in old.items()}
        sleep = B.load_model(root / "sleep64.pt", "loop")
        result = {"arm": "loop", "seed": 1, "init": init, "recounted_utc": stamp,
                  "stop_reason": "V3 mathematically impossible; no 65536 rung or holdout evaluated",
                  "fixed_depth": fixed, "dev9_rungs": scores, "old": old_scores,
                  "sleep64_dev9": B.score(sleep, panel["dev"][9], fixed)}
        B.dump(root / "partial.json", result)
        print(json.dumps({"init": init, "right9": {k: v["right"] for k, v in scores.items()}}), flush=True)


if __name__ == "__main__":
    main()
