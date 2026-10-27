#!/usr/bin/env python3
"""relnet practice gate verdict (2026-09-27): reads practice-*.json from scripts/claude_relnet_practice.py and applies
artifacts/claude-relnet-20260927/GATE-PASSMARKS.md (G1: relation net >= 190 of 200 on gate sums4 and grids5 per
seed; G2: at most 6 of 200 below the same-seed loop on each kind). Stop failure, rounds and minutes are report-only.

  python -B scripts/claude_relnet_gate.py --dir artifacts/claude-relnet-20260927/practice [--lr 0.001]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

KINDS = ["sums4", "grids5"]


def stop_failure(r, kind):
    """learned stop vs the best fixed depth picked on dev, both scored on gate"""
    fd = r["dev"][kind]["fixed_depth_right"]
    best = max(fd, key=lambda k: (fd[k], -int(k)))
    fixed_gate = r["gate"][kind]["fixed_depth_right"][best]
    return int(best), fixed_gate, fixed_gate - r["gate"][kind]["right"] > 4


def main(a):
    runs = {}
    for p in sorted(Path(a.dir).glob("practice-*.json")):
        r = json.loads(p.read_text())
        runs[(r["arm"], r["seed"], r["lr"])] = r
    lines, verdicts = [], []
    lines.append("| arm | seed | lr | weights | train min | dev sums4 | dev grids5 | gate sums4 | gate grids5 | mean rounds (s/g) | cap hits (s/g) | best fixed depth -> gate (s/g) | stop failure |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---|")
    for (arm, seed, lr), r in sorted(runs.items()):
        sf = [stop_failure(r, k) for k in KINDS]
        lines.append(
            f"| {arm} | {seed} | {lr:g} | {r['weights']:,} | {r['train_minutes']} | "
            + " | ".join(f"{r['dev'][k]['right']} of 200" for k in KINDS) + " | "
            + " | ".join(f"{r['gate'][k]['right']} of 200" for k in KINDS) + " | "
            + "/".join(str(r['gate'][k]['mean_rounds']) for k in KINDS) + " | "
            + "/".join(str(r['gate'][k]['cap_hits']) for k in KINDS) + " | "
            + "/".join(f"{d}->{g}" for d, g, _ in sf) + " | "
            + ("yes" if any(f for _, _, f in sf) else "no") + " |")
    for seed in sorted({s for (arm, s, lr) in runs if arm == "relnet" and lr == a.lr}):
        rel, loop = runs.get(("relnet", seed, a.lr)), runs.get(("loop", seed, 0.001))
        g1 = all(rel["gate"][k]["right"] >= 190 for k in KINDS)
        g2 = None if loop is None else all(rel["gate"][k]["right"] >= loop["gate"][k]["right"] - 6 for k in KINDS)
        verdicts.append(dict(seed=seed, G1=g1, G2=g2))
    ok = verdicts and all(v["G1"] and v["G2"] for v in verdicts) and len(verdicts) >= 2
    pending = any(v["G2"] is None for v in verdicts)
    lines.append("")
    for v in verdicts:
        lines.append(f"- seed {v['seed']}: G1 {'pass' if v['G1'] else 'FAIL'}; "
                     f"G2 {'pending (no loop run)' if v['G2'] is None else ('pass' if v['G2'] else 'FAIL')}")
    lines.append(f"- **gate verdict (lr {a.lr:g}): {'PENDING' if pending else ('PASS' if ok else 'FAIL')}**")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="artifacts/claude-relnet-20260927/practice")
    ap.add_argument("--lr", type=float, default=0.001)
    main(ap.parse_args())
