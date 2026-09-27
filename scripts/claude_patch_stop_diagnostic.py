#!/usr/bin/env python3
"""Compare already saved source predictions; never run or change a model.

This is a report-only diagnosis. It cannot replace learned-stop eligibility
scores or select a new stopping rule from the verification panel.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess

import claude_patch_data as D
import claude_rsn358a_envs as E


def diagnose(path):
    raw = path.read_bytes()
    groups = defaultdict(list)
    for line in raw.splitlines():
        row = json.loads(line)
        item = E.Item(**row["input"])
        selected = bool(D.check(item, row["pred"]))
        assert selected == row["right"], "saved correctness disagrees with checker"
        groups[row["kind"]].append((row, item, selected))
    assert set(groups) == set(D.KINDS)
    result = {}
    for kind, items in groups.items():
        assert len(items) == 300
        assert len({row["fingerprint"] for row, _, _ in items}) == 300
        selected_right = sum(selected for _, _, selected in items)
        depths = {}
        for depth in (4, 8, 16, 32, 48):
            both = recovered = regressed = neither = 0
            recovered_rounds = []
            for row, item, selected in items:
                fixed = bool(D.check(item, row["fixed_pred"][str(depth)]))
                both += selected and fixed
                recovered += not selected and fixed
                regressed += selected and not fixed
                neither += not selected and not fixed
                if not selected and fixed:
                    recovered_rounds.append(row["round"])
            assert both + recovered + regressed + neither == 300
            assert both + regressed == selected_right
            depths[str(depth)] = {
                "both_correct": both, "fixed_correct_selected_wrong": recovered,
                "selected_correct_fixed_wrong": regressed, "both_wrong": neither,
                "fixed_right": both + recovered, "net_more_right": recovered - regressed,
                "selected_rounds_for_recovered_examples": sorted(recovered_rounds),
            }
        result[kind] = {"n": 300, "selected_right": selected_right, "fixed_depths": depths}
    return {
        "utc": subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True).strip(),
        "input": str(path.resolve()), "input_sha256": hashlib.sha256(raw).hexdigest(),
        "diagnostic_only": True, "new_model_runs": 0,
        "eligibility_rule_changed": False, "kinds": result,
        "limitation": "These paired outcomes describe the saved trajectory. They do not establish that a newly calibrated stop rule would pass a fresh panel.",
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", type=Path, help="completed own practice-arm directory")
    args = ap.parse_args()
    result = diagnose(args.run / "verify-raw.jsonl")
    (args.run / "stop-diagnostic.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: {"selected_right": v["selected_right"], **v["fixed_depths"]["48"]}
                      for k, v in result["kinds"].items()}, indent=2))
