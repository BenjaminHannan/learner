#!/usr/bin/env python3
"""Report-only: what the H3 settle gate does in saved checkpoints. Scores nothing.

NOT EXECUTED where written (no torch). Reads a checkpoint written by the harness or by
claude_dir_h3_practice.py (a state dict) and, on a fixed handful of puzzles, prints per-round gate
statistics (mean, share below 0.5, share above 0.98) and the three learned gate numbers.
Puzzles: 32 source-guard sums, 32 source-guard grids, and 32 maze layouts from the DEV panel only.
The holdout panel is never opened here.

  python -B scripts/claude_dir_h3_gate_report.py --ckpt <dir>/source.pt --out gate-source-s0.json
  python -B scripts/claude_dir_h3_gate_report.py --ckpt <eq-runs>/h3-pre-s0/k64.pt --out gate-k64-s0.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

import claude_dir_h3_net as H
import claude_fewex_bench as B
import claude_fewex_data as D
import claude_fewex_net as base

GUARD_SEED = D.SOURCE_SEED + 300


def main(ckpt, out, n):
    net = H.Net("loop")
    net.load_state_dict(torch.load(ckpt, map_location="cpu", weights_only=True))
    net.eval()
    guard = D.old_panels(GUARD_SEED)
    dev9 = D.panels()[0]["dev"][9]
    sets = {"sums4": guard["sums4"][:n], "grids5": guard["grids5"][:n], "dev_mazes9": dev9[:n]}
    res = {"ckpt": str(ckpt), "gate_state_bias": float(net.gate_state.bias),
           "gate_state_weight_norm": float(net.gate_state.weight.norm()),
           "gate_surprise_weight": float(net.gate_surprise), "sets": {}}
    for name, items in sets.items():
        t, s, _ = base.tensors(items)
        res["sets"][name] = net.gate_stats(t, s, 48)
    B.dump(Path(out), res)
    for name, st in res["sets"].items():
        m = st["mean_by_round"]
        print(json.dumps({"set": name, "mean_g_rounds_1_8_16_32_48": [m[0], m[7], m[15], m[31], m[47]],
                          "min": st["min"], "max": st["max"]}))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--n", type=int, default=32)
    p.add_argument("--threads", type=int, default=2)
    a = p.parse_args()
    torch.set_num_threads(a.threads)
    main(a.ckpt, a.out, a.n)
