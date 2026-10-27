#!/usr/bin/env python3
"""H3 race table and verdict from raw harness JSON and PASSMARKS.md (artifacts/claude-dir-h3-design-20260928).

Pure standard library (no torch). Uses the summary and gate arithmetic of scripts/claude_sparse_race.py
(imported, not edited), which reads the harness's adapt.json / holdout.json and applies RACE-PASSMARKS.md
with RACE-ADDENDUM-1.md's F_all -> F_eq substitution, thresholds unchanged. Only the folder names differ:
  <dir>/h3-pre-s{seed}   <dir>/h3-fresh-s{seed}
and the baseline's eq-runs/loop-s{seed}-pre, eq-runs/plain-s{seed}-pre.

  python3 scripts/claude_dir_h3_report.py --split dev     --h3 <eq-runs dir> --loop '<...>/loop-s{seed}-pre' --plain '<...>/plain-s{seed}-pre' --out dev-table.json
  python3 scripts/claude_dir_h3_report.py --split holdout ...     (only after every dev run is committed)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_sparse_race as R  # noqa: E402


def main(split, h3_dir, loop_fmt, plain_fmt, out):
    res = {"split": split, "seeds": {}}
    for seed in (0, 1):
        h3 = R.summary(*R.load(Path(h3_dir) / f"h3-pre-s{seed}"), split)
        fr = R.summary(*R.load(Path(h3_dir) / f"h3-fresh-s{seed}"), split)
        lp = R.summary(*R.load(loop_fmt.format(seed=seed)), split)
        pl = R.summary(*R.load(plain_fmt.format(seed=seed)), split)
        row = {"h3": h3, "h3_fresh": fr, "loop": lp, "plain": pl, "F_eq_minus_loop": h3["F_eq"] - lp["F_eq"]}
        if split == "holdout":
            row["gates"] = R.gates(h3, fr, lp, pl)
            row["all_gates"] = all(row["gates"].values())
            row["maze_gain_breaking_old_gate"] = h3["F_eq"] > lp["F_eq"] and not all(
                row["gates"][k] for k in ("old_before_95", "old_before_within3_of_loop",
                                          "sleep64_old_within3_of_loop", "sleep16384_old_within3_of_loop"))
        res["seeds"][str(seed)] = row
    if split == "holdout":
        s = res["seeds"]
        rejected = all(s[x]["F_eq_minus_loop"] <= 0 for x in s) or any(
            s[x]["maze_gain_breaking_old_gate"] for x in s)
        res["verdict"] = ("PASS" if all(s[x]["all_gates"] for x in s) else
                          "REJECTED" if rejected else "NOT PROMOTED")
        res["failing_gates"] = {x: [k for k, v in s[x]["gates"].items() if not v] for x in s}
    Path(out).write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    for seed, row in res["seeds"].items():
        print(f"seed {seed}: F_eq h3 {row['h3']['F_eq']:.2f}, fresh {row['h3_fresh']['F_eq']:.2f}, "
              f"loop {row['loop']['F_eq']:.2f}, plain {row['plain']['F_eq']:.2f}; "
              f"h3-loop {row['F_eq_minus_loop']:+.2f}")
    if split == "holdout":
        print("verdict:", res["verdict"], res["failing_gates"])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=("dev", "holdout"), required=True)
    p.add_argument("--h3", required=True, help="folder holding h3-{pre,fresh}-s{seed}")
    p.add_argument("--loop", required=True, help="baseline loop/pre run folder, with {seed}")
    p.add_argument("--plain", required=True, help="baseline plain/pre run folder, with {seed}")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    main(a.split, a.h3, a.loop, a.plain, a.out)
