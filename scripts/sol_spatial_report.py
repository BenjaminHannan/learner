#!/usr/bin/env python3
"""Recount already recorded predictions; never reload/evaluate a model."""
import argparse
import json
from pathlib import Path
from sol_spatial_experiment import ROOT, BUNDLE, ARMS, verify, sha, digest


def report(record_file):
    spec, seal = verify()
    r = json.loads(Path(record_file).read_text())
    assert r["complete"] and r["seal_sha256"] == seal
    assert r["development_only"] and r["official_holdout_opened"] is False
    assert len(r["models"]) == len(r["scores"]) == 6
    rows = []
    for seed in spec["seeds"]:
        orders, data = set(), set()
        for arm in ARMS:
            key = f"s{seed}-{arm}"
            m = r["models"][key]
            assert m["updates"] == len(m["losses"]) == spec["updates"]
            assert m["presentation_slots"] == 8 * spec["updates"]
            assert sha(ROOT / m["checkpoint"]) == m["checkpoint_sha256"]
            orders.add(m["batch_order_sha256"]); data.add(digest(m["data"]))
            for kind in ("mazes9", "mazes11"):
                for depth in ("24", "48"):
                    raw = r["scores"][key][kind][depth]
                    supports, cells = 64, 81 if kind == "mazes9" else 121
                    assert raw["n"] == supports
                    assert len(raw["predictions"]) == len(raw["per_puzzle_correctness"]) == supports
                    assert all(len(p) == cells for p in raw["predictions"])
                    assert all(type(v) is bool for v in raw["per_puzzle_correctness"])
                    assert sum(raw["per_puzzle_correctness"]) == raw["exact"]
                    rows.append({"seed": seed, "arm": arm, "kind": kind, "depth": int(depth),
                                 "exact": raw["exact"], "n": 64})
        assert len(orders) == len(data) == 1
    comparisons = []
    for seed in spec["seeds"]:
        for kind, bar in spec["absolute_screen_counts"].items():
            scores = {arm: r["scores"][f"s{seed}-{arm}"][kind]["48"]["exact"] for arm in ARMS}
            comparisons.append({"seed": seed, "kind": kind, "counts": scores,
                "candidate_absolute_screen": scores[ARMS[1]] >= bar,
                "stronger_control_count": max(scores[ARMS[0]], scores[ARMS[2]]),
                "delta_vs_top1": scores[ARMS[1]] - scores[ARMS[0]],
                "delta_vs_dense": scores[ARMS[1]] - scores[ARMS[2]],
                "delta_vs_stronger_control": scores[ARMS[1]] - max(scores[ARMS[0]], scores[ARMS[2]])})
    return {"record_sha256": sha(record_file), "seal_sha256": seal, "rows": rows,
            "comparisons": comparisons,
            "absolute_development_screen_pass": all(x["candidate_absolute_screen"] for x in comparisons),
            "claim": "NOT SHOWN: development screen only; noise is insufficient for improvement inference",
            "noise": spec["noise"], "new_training_presentation_slots": 48 * spec["updates"],
            "not_tested": ["independent confirmation", "F_eq/F_few", "same-size plain control",
                           "learned stopping calibration", "sleep", "old-skill retention", "full target transformer"],
            "recount_scope": "Recorded exact flags summed; separate independent recount must check predictions against labels. No holdout rescored."}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("record"); args = p.parse_args()
    print(json.dumps(report(args.record), indent=2))
