#!/usr/bin/env python3
"""Apply artifacts/claude-patch-eq-20260928/PASSMARKS.md to the raw harness JSON.

  dev      -> race-dev.json      (dev tables only; no gate, no verdict)
  holdout  -> race-holdout.json  (holdout F_eq, every mark per seed, the verdict)

Reads only adapt.json / holdout.json / source.json files. Seeds are never pooled.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "claude-patch-eq-20260928"
BASE = ROOT / "artifacts" / "claude-fewex-20260927" / "eq-runs"
RUNGS = ("1", "4", "16", "64", "256", "1024", "4096", "16384")
KINDS = ("sums4", "grids5")
SEEDS = (0, 1)


def runs(seed):
    return {"patch": ART / "eq-runs" / f"patch-s{seed}",
            "fresh": ART / "eq-runs" / f"fresh-s{seed}",
            "loop_ep": ART / "eq-runs" / f"loopep-s{seed}",
            "plain": BASE / f"plain-s{seed}-pre",
            "loop_base": BASE / f"loop-s{seed}-pre"}


def load(path):
    return json.loads(path.read_text())


def curve(scores, key="right", size="9"):
    return {k: scores[k][size][key] for k in ("0",) + RUNGS}


def f_eq(counts):
    return sum(100 * counts[k] / 300 for k in RUNGS) / len(RUNGS)


def e50(counts):
    return next((int(k) for k in RUNGS if counts[k] >= 150), "not reached")


def stop_failures(scores):
    out = {}
    for size in ("7", "9", "11"):
        bad = []
        for k in ("0",) + RUNGS:
            r = scores[k][size]
            gap = 100 * (r["fixed_right"] - r["right"]) / r["n"]
            if gap > 2:
                bad.append({"k": k, "learned": r["right"], "fixed": r["fixed_right"], "n": r["n"]})
        out[size] = bad
    return out


def arm_record(adapt, scores):
    c = curve(scores)
    return {"right9": c, "F_eq": f_eq(c), "E50": e50(c),
            "fixed9": curve(scores, "fixed_right"),
            "right7": curve(scores, size="7"), "right11": curve(scores, size="11"),
            "mean_rounds9": curve(scores, "mean_rounds"), "cap_hits9": curve(scores, "cap_hits"),
            "stop_failures": stop_failures(scores),
            "old": {"before": {k: adapt["old"]["before"][k]["right"] for k in KINDS},
                    "after_64": {k: adapt["old"]["after_64"][k]["right"] for k in KINDS},
                    "sleep_64": {k: adapt["sleep"]["64"]["old"][k]["right"] for k in KINDS},
                    "after_16384": {k: adapt["old"]["after_16384"][k]["right"] for k in KINDS},
                    "sleep_16384": {k: adapt["sleep"]["16384"]["old"][k]["right"] for k in KINDS}},
            "weights": adapt["weights"], "fixed_depth": adapt["fixed_depth"],
            "support_sha256": adapt["support_sha256"],
            "training_seconds": adapt.get("training_seconds")}


def dev(out):
    table = {}
    for seed in SEEDS:
        table[str(seed)] = {}
        for arm, path in runs(seed).items():
            a = load(path / "adapt.json")
            table[str(seed)][arm] = arm_record(a, a["rungs"])
    json.dump(table, out.open("w"), indent=2, sort_keys=True)
    return table


def gates(seed):
    r = runs(seed)
    rec = {arm: arm_record(load(p / "adapt.json"), load(p / "holdout.json")["scores"]) for arm, p in r.items()}
    for arm in ("patch", "fresh", "loop_ep"):
        if rec[arm]["support_sha256"] != rec["plain"]["support_sha256"]:
            raise ValueError("support pool differs from the baseline's")
    p, l = rec["patch"], rec["loop_ep"]
    g = {
        "F_eq_patch_minus_loop_ep_ge_10": p["F_eq"] - l["F_eq"] >= 10,
        "F_eq_patch_minus_plain_ge_5": p["F_eq"] - rec["plain"]["F_eq"] >= 5,
        "F_eq_patch_minus_fresh_ge_5": p["F_eq"] - rec["fresh"]["F_eq"] >= 5,
        "old_before_ge_190": all(p["old"]["before"][k] >= 190 for k in KINDS),
        "old_before_within_6_of_loop_ep": all(p["old"]["before"][k] >= l["old"]["before"][k] - 6 for k in KINDS),
        "sleep_64_within_6_of_loop_ep": all(p["old"]["sleep_64"][k] >= l["old"]["sleep_64"][k] - 6 for k in KINDS),
        "sleep_16384_within_6_of_loop_ep": all(p["old"]["sleep_16384"][k] >= l["old"]["sleep_16384"][k] - 6
                                               for k in KINDS),
        "size_within_2pct_of_loop_ep": abs(p["weights"] - l["weights"]) / l["weights"] <= .02,
    }
    old_gates = ("old_before_ge_190", "old_before_within_6_of_loop_ep",
                 "sleep_64_within_6_of_loop_ep", "sleep_16384_within_6_of_loop_ep")
    diffs = {"patch_minus_loop_ep": p["F_eq"] - l["F_eq"], "patch_minus_plain": p["F_eq"] - rec["plain"]["F_eq"],
             "patch_minus_fresh": p["F_eq"] - rec["fresh"]["F_eq"],
             "loop_ep_minus_loop_base": l["F_eq"] - rec["loop_base"]["F_eq"]}
    return rec, g, diffs, {"above_loop_ep": p["F_eq"] > l["F_eq"],
                           "old_gates_all_hold": all(g[x] for x in old_gates)}


def holdout(out):
    res = {"seeds": {}}
    for seed in SEEDS:
        rec, g, diffs, flags = gates(seed)
        res["seeds"][str(seed)] = {"arms": rec, "gates": g, "differences": diffs, "flags": flags,
                                   "failing": [k for k, v in g.items() if not v]}
    seeds = res["seeds"].values()
    no_higher_both = all(not s["flags"]["above_loop_ep"] for s in seeds)
    gained = [s for s in seeds if s["flags"]["above_loop_ep"]]
    gain_only_by_breaking = bool(gained) and all(not s["flags"]["old_gates_all_hold"] for s in gained)
    if all(not s["failing"] for s in seeds):
        verdict = "PASS"
    elif no_higher_both or gain_only_by_breaking:
        verdict = "REJECTED"
    else:
        verdict = "NOT PROMOTED"
    res.update({"verdict": verdict, "rejected_because": {"F_eq_no_higher_than_loop_ep_in_both_seeds": no_higher_both,
                                                        "maze_gain_only_by_breaking_old_kind_gate": gain_only_by_breaking},
                "failing_marks": {k: v["failing"] for k, v in res["seeds"].items()}})
    json.dump(res, out.open("w"), indent=2, sort_keys=True)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("dev", "holdout"))
    a = ap.parse_args()
    if a.cmd == "dev":
        t = dev(ART / "race-dev.json")
        for seed, arms in t.items():
            print(seed, {arm: round(r["F_eq"], 2) for arm, r in arms.items()})
    else:
        r = holdout(ART / "race-holdout.json")
        print(json.dumps({"verdict": r["verdict"], "failing": r["failing_marks"],
                          "diffs": {s: v["differences"] for s, v in r["seeds"].items()}}, indent=1))
