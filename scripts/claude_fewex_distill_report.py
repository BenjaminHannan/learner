#!/usr/bin/env python3
"""Apply PASSMARKS.md (artifacts/claude-distill-20260928) to the 60 sleep records.

Writes summary.json and tables.md next to the records. Reads only JSON.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "artifacts" / "claude-distill-20260928"
RULER = Path(__file__).resolve().parents[1] / "artifacts" / "claude-fewex-20260927" / "eq-runs"
ARMS = ("R128", "D128", "W128", "R16", "D16")
CELLS = [(s, k) for s in (0, 1) for k in (64, 16384)]
KINDS = ("sums4", "grids5")


def load():
    recs = {}
    for s, k in CELLS:
        for arm in ARMS:
            for d in range(3):
                r = json.loads((OUT / "sleeps" / f"s{s}-k{k}-{arm}-d{d}.json").read_text())
                assert (r["seed"], r["branch"], r["arm"], r["draw"]) == (s, k, arm, d)
                assert r["updates"] == 512
                recs[s, k, arm, d] = r
    return recs


def mean(xs):
    return sum(xs) / len(xs)


def cell(recs, s, k, arm, get):
    vals = [get(recs[s, k, arm, d]) for d in range(3)]
    return {"mean": mean(vals), "draws": vals, "min": min(vals), "max": max(vals)}


def compare(recs, a, b, kind, need_mean):
    diffs = [cell(recs, s, k, a, lambda r: r["old"][kind]["right"])["mean"] -
             cell(recs, s, k, b, lambda r: r["old"][kind]["right"])["mean"] for s, k in CELLS]
    higher = sum(x > 0 for x in diffs)
    return {"cell_diffs": diffs, "mean_diff": mean(diffs), "cells_higher": higher,
            "holds_mean": mean(diffs) >= need_mean}


def main():
    recs = load()
    get_old = {kind: (lambda kind: lambda r: r["old"][kind]["right"])(kind) for kind in KINDS}
    table = {f"s{s}-k{k}": {arm: {
        **{kind: cell(recs, s, k, arm, get_old[kind]) for kind in KINDS},
        **{f"fresh_{kind}": cell(recs, s, k, arm, (lambda kd: lambda r: r["fresh_old"][kd]["right"])(kind))
           for kind in KINDS},
        **{f"maze{p}": cell(recs, s, k, arm, (lambda p: lambda r: r["maze_dev"][p]["right"])(p))
           for p in ("7", "9", "11")},
        **{f"rounds_{kind}": cell(recs, s, k, arm, (lambda kd: lambda r: r["old"][kd]["mean_rounds"])(kind))
           for kind in KINDS},
        "rounds_maze9": cell(recs, s, k, arm, lambda r: r["maze_dev"]["9"]["mean_rounds"]),
        **{f"kl_before_{kind}": cell(recs, s, k, arm,
                                     (lambda kd: lambda r: r["kl_store128_before"][kd]["mean_rounds_1_16"])(kind))
           for kind in KINDS},
        **{f"kl_after_{kind}": cell(recs, s, k, arm,
                                    (lambda kd: lambda r: r["kl_store128_after"][kd]["mean_rounds_1_16"])(kind))
           for kind in KINDS},
        "sleep_seconds": cell(recs, s, k, arm, lambda r: r["sleep_seconds"]),
    } for arm in ARMS} for s, k in CELLS}

    m1 = {kind: compare(recs, "D128", "R128", kind, 20) for kind in KINDS}
    for v in m1.values():
        v["holds"] = v["holds_mean"] and v["cells_higher"] >= 3
    m1b = {kind: compare(recs, "D128", "W128", kind, 10) for kind in KINDS}
    for v in m1b.values():
        v["holds"] = v["holds_mean"]
    m2_cells = {f"s{s}-k{k}": table[f"s{s}-k{k}"]["D128"]["maze9"]["mean"] -
                table[f"s{s}-k{k}"]["R128"]["maze9"]["mean"] for s, k in CELLS}
    m2 = {"cell_diffs_D_minus_R": m2_cells, "holds": all(x >= -6 for x in m2_cells.values())}
    small = {kind: compare(recs, "D16", "R16", kind, 20) for kind in KINDS}
    for v in small.values():
        v["holds"] = v["holds_mean"] and v["cells_higher"] >= 3
    near = {}
    for kind in KINDS:
        diffs = [table[f"s{s}-k{k}"]["D16"][kind]["mean"] - table[f"s{s}-k{k}"]["R128"][kind]["mean"]
                 for s, k in CELLS]
        near[kind] = {"cell_diffs_D16_minus_R128": diffs, "cells_within_6": sum(x >= -6 for x in diffs)}
        near[kind]["holds"] = near[kind]["cells_within_6"] >= 3

    m1_all = all(v["holds"] for v in m1.values())
    m1b_all = all(v["holds"] for v in m1b.values())
    wrong = all(v["mean_diff"] < 5 for v in m1.values())
    if m1_all and m1b_all and m2["holds"]:
        verdict = "PASS"
    elif m1_all and not m1b_all:
        verdict = "helps only as extra weight"
    elif wrong:
        verdict = "PROVED WRONG"
    else:
        verdict = "not passed, not proved wrong"

    validity = {}
    for s, k in CELLS:
        orig = json.loads((RULER / f"loop-s{s}-pre" / "adapt.json").read_text())["sleep"][str(k)]
        reb = json.loads((OUT / "rebuild" / f"loop-s{s}-pre" / f"rebuild-k{k}.json").read_text())["sleep"][str(k)]
        r0 = recs[s, k, "R128", 0]
        validity[f"s{s}-k{k}"] = {
            "original_old": {kd: orig["old"][kd]["right"] for kd in KINDS},
            "R128_d0_old": {kd: r0["old"][kd]["right"] for kd in KINDS},
            "equals_original": all(orig["old"][kd]["right"] == r0["old"][kd]["right"] for kd in KINDS),
            "equals_rebuild_harness_sleep_exactly": reb["old"] == r0["old"] and reb["maze_dev"] == r0["maze_dev"],
        }
    summary = {"verdict": verdict, "M1": m1, "M1b": m1b, "M2": m2,
               "proved_wrong": wrong, "smaller_store": {"D16_vs_R16": small,
                                                        "D16_passes": all(v["holds"] for v in small.values()),
                                                        "D16_near_R128": near},
               "validity": validity, "cells": table}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    lines = ["| Cell | Arm | sums4 mean (draws) | grids5 mean (draws) | fresh sums4 | fresh grids5 | "
             "7x7 of 24 | 9x9 of 300 | 11x11 of 300 |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for c, arms in table.items():
        for arm, v in arms.items():
            f = lambda x: f"{x['mean']:.1f} ({', '.join(str(int(d)) for d in x['draws'])})"
            lines.append(f"| {c} | {arm} | {f(v['sums4'])} | {f(v['grids5'])} | {v['fresh_sums4']['mean']:.1f} | "
                         f"{v['fresh_grids5']['mean']:.1f} | {v['maze7']['mean']:.1f} | {f(v['maze9'])} | "
                         f"{v['maze11']['mean']:.1f} |")
    lines += ["", "| Cell | Arm | KL before s/g | KL after s/g | stop rounds s/g/maze9 | sleep s |",
              "|---|---|---|---|---|---:|"]
    for c, arms in table.items():
        for arm, v in arms.items():
            lines.append(f"| {c} | {arm} | {v['kl_before_sums4']['mean']:.3f} / {v['kl_before_grids5']['mean']:.3f} | "
                         f"{v['kl_after_sums4']['mean']:.3f} / {v['kl_after_grids5']['mean']:.3f} | "
                         f"{v['rounds_sums4']['mean']:.1f} / {v['rounds_grids5']['mean']:.1f} / "
                         f"{v['rounds_maze9']['mean']:.1f} | {v['sleep_seconds']['mean']:.0f} |")
    (OUT / "tables.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"verdict": verdict,
                      "M1": {k: (round(v["mean_diff"], 2), v["cells_higher"], v["holds"]) for k, v in m1.items()},
                      "M1b": {k: (round(v["mean_diff"], 2), v["holds"]) for k, v in m1b.items()},
                      "M2": m2, "small": {k: (round(v["mean_diff"], 2), v["cells_higher"], v["holds"])
                                          for k, v in small.items()},
                      "near": {k: v["cells_within_6"] for k, v in near.items()},
                      "validity": validity}, indent=1))


if __name__ == "__main__":
    main()
