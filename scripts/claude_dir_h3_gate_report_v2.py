#!/usr/bin/env python3
"""Report-only (version 2, ADDENDUM-1 of the H3 folder): what the H3 settle gate does in saved checkpoints. Scores nothing.

Copy of scripts/claude_dir_h3_gate_report.py (v1 not edited). Differences: it loads scripts/claude_dir_h3_net_v2.py (or the constant-g
control with --const), adds the standard deviation of g over puzzles, rounds and cells (`std_all`) per set, and reports the dead-gate
flag of ADDENDUM-1: a gate is DEAD at a checkpoint when std_all < 0.02 on every one of the three sets. The v1 "mean above 0.98 or
below 0.05" is still printed as `mean_extreme` (report only). The constant-g control is dead by construction.

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

import claude_dir_h3_net_v2 as H
import claude_dir_h3_net_v2_const as HC
import claude_fewex_bench as B
import claude_fewex_data as D
import claude_fewex_net as base

GUARD_SEED = D.SOURCE_SEED + 300


def main(ckpt, out, n, const=False):
    net = (HC if const else H).Net("loop")
    net.load_state_dict(torch.load(ckpt, map_location="cpu", weights_only=True))
    net.eval()
    guard = D.old_panels(GUARD_SEED)
    dev9 = D.panels()[0]["dev"][9]
    sets = {"sums4": guard["sums4"][:n], "grids5": guard["grids5"][:n], "dev_mazes9": dev9[:n]}
    res = {"ckpt": str(ckpt), "const_control": const, "sets": {}}
    if not const:
        res.update({"gate_state_bias": float(net.gate_state.bias),
                    "gate_state_weight_norm": float(net.gate_state.weight.norm()),
                    "gate_surprise_weight": float(net.gate_surprise)})
    for name, items in sets.items():
        t, s, _ = base.tensors(items)
        res["sets"][name] = net.gate_stats(t, s, 48)
    for st in res["sets"].values():
        m = st["mean_by_round"]
        st["mean_extreme"] = all(x > 0.98 for x in m) or all(x < 0.05 for x in m)      # v1 rule, report only
    res["dead_gate_rule"] = f"std of g over puzzles, rounds and cells below {H.DEAD_STD} on all three sets"
    res["dead_gate"] = all(st["std_all"] < H.DEAD_STD for st in res["sets"].values())
    B.dump(Path(out), res)
    for name, st in res["sets"].items():
        m = st["mean_by_round"]
        print(json.dumps({"set": name, "mean_g_rounds_1_8_16_32_48": [m[0], m[7], m[15], m[31], m[47]],
                          "std_all": round(st["std_all"], 4), "min": st["min"], "max": st["max"],
                          "mean_extreme": st["mean_extreme"]}))
    print(json.dumps({"dead_gate": res["dead_gate"], "rule": res["dead_gate_rule"]}))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--n", type=int, default=32)
    p.add_argument("--const", action="store_true", help="checkpoint of the constant-g = 0.9 control (no gate tensors)")
    p.add_argument("--threads", type=int, default=2)
    a = p.parse_args()
    torch.set_num_threads(a.threads)
    main(a.ckpt, a.out, a.n, a.const)
