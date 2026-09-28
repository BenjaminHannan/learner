#!/usr/bin/env python3
"""Test D race table and verdict from raw harness JSON and PASSMARKS-D.md's reading.

Inputs: this design's runs (sparse-pre-s{seed}, sparse-fresh-s{seed}, each with
adapt.json and, after the one holdout pass, holdout.json) and the few-example
baseline's loop/pre and plain/pre runs for the same seeds. `--split dev` builds
the dev table from adapt.json only; `--split holdout` applies the marks.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

RUNGS = ("1", "4", "16", "64", "256", "1024", "4096", "16384", "65536")
FEW = RUNGS[:4]
KINDS = ("sums4", "grids5")


def load(d):
    d = Path(d)
    adapt = json.loads((d / "adapt.json").read_text())
    ho = d / "holdout.json"
    return adapt, (json.loads(ho.read_text()) if ho.exists() else None)


def rung_scores(adapt, hold, split):
    """{rung: {size: record}} for rungs 0..65536 plus sleep64/sleep64k."""
    if split == "holdout":
        return hold["scores"]
    out = dict(adapt["rungs"])
    out["sleep64"] = adapt["sleep"]["64"]["maze_dev"]
    out["sleep64k"] = adapt["sleep"]["64k"]["maze_dev"]
    return out


def pct(rec):
    return 100.0 * rec["right"] / rec["n"]


def summary(adapt, hold, split):
    sc = rung_scores(adapt, hold, split)
    f_all = sum(pct(sc[r]["9"]) for r in RUNGS) / len(RUNGS)
    f_few = sum(pct(sc[r]["9"]) for r in FEW) / len(FEW)
    stop_fail = {r: pct(sc[r]["9"]) < 100.0 * sc[r]["9"]["fixed_right"] / sc[r]["9"]["n"] - 2
                 for r in ("0",) + RUNGS + ("sleep64", "sleep64k")} if adapt["arm"] == "loop" else {}
    old = adapt["old"]
    return {"F_all": f_all, "F_few": f_few, "cold": pct(sc["0"]["9"]), "F_few_minus_cold": f_few - pct(sc["0"]["9"]),
            "curve9": {r: f'{sc[r]["9"]["right"]} of {sc[r]["9"]["n"]}' for r in ("0",) + RUNGS + ("sleep64", "sleep64k")},
            "curve7": {r: f'{sc[r]["7"]["right"]} of {sc[r]["7"]["n"]}' for r in ("0",) + RUNGS + ("sleep64", "sleep64k")},
            "curve11": {r: f'{sc[r]["11"]["right"]} of {sc[r]["11"]["n"]}' for r in ("0",) + RUNGS + ("sleep64", "sleep64k")},
            "fixed9": {r: f'{sc[r]["9"]["fixed_right"]} of {sc[r]["9"]["n"]}' for r in ("0",) + RUNGS},
            "mean_rounds9": {r: round(sc[r]["9"]["mean_rounds"], 2) for r in ("0",) + RUNGS},
            "cap_hits9": {r: sc[r]["9"]["cap_hits"] for r in ("0",) + RUNGS},
            "stop_failures": [r for r, v in stop_fail.items() if v],
            "k64_at_least_50pct": pct(sc["64"]["9"]) >= 50,
            "old_before": {k: old["before"][k]["right"] for k in KINDS},
            "old_after_64": {k: old["after_64"][k]["right"] for k in KINDS},
            "old_after_64k": {k: old["after_64k"][k]["right"] for k in KINDS},
            "old_sleep64": {k: adapt["sleep"]["64"]["old"][k]["right"] for k in KINDS},
            "old_sleep64k": {k: adapt["sleep"]["64k"]["old"][k]["right"] for k in KINDS},
            "D_sleep64": {k: (old["before"][k]["right"] - adapt["sleep"]["64"]["old"][k]["right"]) / 2 for k in KINDS},
            "D_sleep64k": {k: (old["before"][k]["right"] - adapt["sleep"]["64k"]["old"][k]["right"]) / 2 for k in KINDS},
            "weights": adapt["weights"], "fixed_depth": adapt["fixed_depth"],
            "updates": adapt.get("optimizer_updates"), "training_seconds": adapt.get("training_seconds")}


def gates(sp, fr, lp, pl):
    g = {}
    g["old_before_95"] = all(sp["old_before"][k] >= 190 for k in KINDS)
    g["old_before_within3_of_loop"] = all(sp["old_before"][k] >= lp["old_before"][k] - 6 for k in KINDS)
    g["F_all_plain_plus5"] = sp["F_all"] >= pl["F_all"] + 5
    g["F_all_fresh_plus5"] = sp["F_all"] >= fr["F_all"] + 5
    g["sleep64_old_within3_of_loop"] = all(sp["old_sleep64"][k] >= lp["old_sleep64"][k] - 6 for k in KINDS)
    g["sleep64k_old_within3_of_loop"] = all(sp["old_sleep64k"][k] >= lp["old_sleep64k"][k] - 6 for k in KINDS)
    g["budget_within2pct"] = abs(sp["weights"] - lp["weights"]) <= .02 * lp["weights"]
    g["F_all_loop_plus10"] = sp["F_all"] >= lp["F_all"] + 10
    return g


def main(split, sparse_dir, loop_fmt, plain_fmt, out):
    res = {"split": split, "seeds": {}}
    for seed in (0, 1):
        sp = summary(*load(Path(sparse_dir) / f"sparse-pre-s{seed}"), split)
        fr = summary(*load(Path(sparse_dir) / f"sparse-fresh-s{seed}"), split)
        lp = summary(*load(loop_fmt.format(seed=seed)), split)
        pl = summary(*load(plain_fmt.format(seed=seed)), split)
        row = {"sparse": sp, "sparse_fresh": fr, "loop": lp, "plain": pl,
               "F_all_minus_loop": sp["F_all"] - lp["F_all"]}
        if split == "holdout":
            row["gates"] = gates(sp, fr, lp, pl)
            row["all_gates"] = all(row["gates"].values())
            row["maze_gain_breaking_old_gate"] = sp["F_all"] > lp["F_all"] and not all(
                row["gates"][k] for k in ("old_before_95", "old_before_within3_of_loop",
                                          "sleep64_old_within3_of_loop", "sleep64k_old_within3_of_loop"))
        res["seeds"][str(seed)] = row
    if split == "holdout":
        s = res["seeds"]
        rejected = all(s[x]["F_all_minus_loop"] <= 0 for x in s) or any(
            s[x]["maze_gain_breaking_old_gate"] for x in s)
        res["verdict"] = ("PASS" if all(s[x]["all_gates"] for x in s) else
                          "REJECTED" if rejected else "NOT PROMOTED")
        res["failing_gates"] = {x: [k for k, v in s[x]["gates"].items() if not v] for x in s}
    Path(out).write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    for seed, row in res["seeds"].items():
        print(f"seed {seed}: F_all sparse {row['sparse']['F_all']:.2f}, fresh {row['sparse_fresh']['F_all']:.2f}, "
              f"loop {row['loop']['F_all']:.2f}, plain {row['plain']['F_all']:.2f}; "
              f"sparse-loop {row['F_all_minus_loop']:+.2f}")
    if split == "holdout":
        print("verdict:", res["verdict"], res["failing_gates"])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=("dev", "holdout"), required=True)
    p.add_argument("--sparse", required=True, help="folder holding sparse-{pre,fresh}-s{seed}")
    p.add_argument("--loop", required=True, help="baseline loop/pre run folder, with {seed}")
    p.add_argument("--plain", required=True, help="baseline plain/pre run folder, with {seed}")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    main(a.split, a.sparse, a.loop, a.plain, a.out)
