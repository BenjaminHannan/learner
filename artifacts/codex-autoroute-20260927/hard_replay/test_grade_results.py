#!/usr/bin/env python3
"""Synthetic AR2 grading checks; no model imports, panels, or training."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import grade_results as G


def sizes(phase: str, arm: str) -> dict[str, int]:
    counts = dict.fromkeys(G.SIZES, 0)
    if phase == "A":
        counts.update(grids4=1250, grids5=1250)
    elif phase == "B":
        counts.update(grids4=125, grids5=125, sums1=563, sums2=563, sums3=562, sums4=562)
        if arm == "hard_grid_replay":
            counts.update(grids4=0, grids5=250)
    else:
        counts.update(grids4=37, grids5=38, sums1=19, sums2=19, sums3=19, sums4=18,
                      mazes5=675, mazes7=675)
        if arm == "hard_grid_replay":
            counts.update(grids4=0, grids5=75)
    return counts


def record(arm: str, seed: int) -> dict:
    phases = {}
    for phase, (steps, kind_batches) in G.PHASES.items():
        right = {"grids5": 190 if phase == "A" else (185 if arm == "hard_grid_replay" else 130),
                 "sums4": 198 if phase == "B" else 190,
                 "maze7": 150}
        phases[phase] = {"steps": steps, "kind_batches": dict(kind_batches),
                         "size_batches": sizes(phase, arm),
                         "score": {name: {"right": value, "n": 200, "fixed16": value,
                                          "any48": value, "stopping_rounds_sum": 3200}
                                   for name, value in right.items()}}
    return {"seed": seed, "arm": arm, "complete": True, "parameters": G.PARAMETERS,
            "device": "mps", "precision": "float32", "batch_size": 64,
            "software_commit": "a" * 40, "minutes": 2.0,
            "m4": {"pass": True, "failures": [], "public_request_fields": ["tokens", "slot"]},
            "m4_final": {"pass": True, "failures": [], "public_request_fields": ["tokens", "slot"]},
            "phases": phases}


class GradeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="grade-fixture-", dir=G.HERE)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "run"
        self.paths = G.result_paths(self.root)
        self.data = {(arm, seed): record(arm, seed) for arm in G.ARMS for seed in G.SEEDS}
        self.write_all()

    def write_all(self):
        for (arm, seed), path in self.paths.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.data[(arm, seed)]), encoding="utf-8")
        self.write_recount()

    def recount(self):
        runs = {}
        for arm in G.ARMS:
            for seed in G.SEEDS:
                label = f"{arm}-s{seed}"
                data = self.data[(arm, seed)]
                runs[label] = {
                    "scores": {phase: data["phases"][phase]["score"] for phase in G.PHASES},
                    "raw_files": {phase: f"{label}/{phase}.jsonl" for phase in G.PHASES},
                    "checkpoint_replay": {
                        "parameters": G.PARAMETERS, "device": "mps", "requests": 600,
                        "mismatches": {"predictions": 0, "stop_probabilities": 0,
                                       "context_probabilities": 0},
                    },
                }
        return {"status": "OK", "mode": "full", "errors": [], "missing": [], "runs": runs}

    def write_recount(self, audit=None):
        path = self.root.parent / "RECOUNT-FINAL.json"
        path.write_text(json.dumps(self.recount() if audit is None else audit), encoding="utf-8")
        return path

    def verdict(self):
        return G.grade(self.paths)["status"]

    def test_pass_and_report(self):
        report = G.grade(self.paths)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["criteria"]["positive_T_gaps"], 6)
        text = G.render_report(report)
        self.assertIn("full recount", text)
        self.assertIn("grid4/grid5 targeted", text)
        self.assertIn("Grid4 retention", text)

    def test_fail_not_proved_wrong(self):
        self.data[("hard_grid_replay", 61)]["phases"]["C"]["score"]["grids5"]["right"] = 150
        self.write_all()
        self.assertEqual(self.verdict(), "FAIL (not proved wrong)")

    def test_proved_wrong_precedes_other_failed_marks(self):
        for seed in G.SEEDS:
            self.data[("hard_grid_replay", seed)]["phases"]["C"]["score"]["grids5"]["right"] = 130
        self.write_all()
        self.assertEqual(self.verdict(), "PROVED WRONG")

    def test_missing_run_and_recount_are_incomplete(self):
        self.paths[("baseline", 61)].unlink()
        (self.root.parent / "RECOUNT-FINAL.json").unlink()
        self.assertEqual(self.verdict(), "INCOMPLETE")
        self.assertEqual(len(G.grade(self.paths)["missing"]), 2)

    def test_missing_recount_only_is_incomplete(self):
        (self.root.parent / "RECOUNT-FINAL.json").unlink()
        self.assertEqual(self.verdict(), "INCOMPLETE")

    def test_wrong_candidate_size_is_invalid(self):
        counts = self.data[("hard_grid_replay", 61)]["phases"]["B"]["size_batches"]
        counts["grids4"], counts["grids5"] = 1, 249
        self.write_all()
        report = G.grade(self.paths)
        self.assertEqual(report["status"], "INVALID")
        self.assertTrue(any("candidate grids" in problem for problem in report["invalid"]))

    def test_missing_or_inconsistent_size_counters_are_invalid(self):
        counts = self.data[("baseline", 61)]["phases"]["C"]["size_batches"]
        del counts["mazes7"]
        self.write_all()
        self.assertEqual(self.verdict(), "INVALID")
        counts["mazes7"] = 674
        self.write_all()
        self.assertEqual(self.verdict(), "INVALID")

    def test_recount_errors_or_checkpoint_mismatch_are_invalid(self):
        audit = self.recount()
        audit["errors"].append("synthetic raw checksum mismatch")
        self.write_recount(audit)
        self.assertEqual(self.verdict(), "INVALID")
        audit = self.recount()
        audit["runs"]["baseline-s61"]["checkpoint_replay"]["mismatches"]["stop_probabilities"] = 1
        self.write_recount(audit)
        self.assertEqual(self.verdict(), "INVALID")

    def test_recount_score_mismatch_and_raw_only_are_invalid(self):
        audit = self.recount()
        audit["runs"]["baseline-s61"]["scores"]["C"]["grids5"]["right"] += 1
        self.write_recount(audit)
        self.assertEqual(self.verdict(), "INVALID")
        audit = self.recount()
        audit["mode"] = "raw-only"
        self.write_recount(audit)
        self.assertEqual(self.verdict(), "INVALID")

    def test_recount_incomplete_and_missing_phase(self):
        audit = self.recount()
        audit["status"] = "INCOMPLETE"
        audit["missing"] = ["synthetic C.jsonl"]
        self.write_recount(audit)
        self.assertEqual(self.verdict(), "INCOMPLETE")
        audit = self.recount()
        del audit["runs"]["baseline-s61"]["scores"]["B"]
        self.write_recount(audit)
        self.assertEqual(self.verdict(), "INVALID")

    def test_cli_creates_both_reports_once(self):
        out = self.root.parent / "grade.md"
        command = [sys.executable, "-B", str(G.HERE / "grade_results.py"),
                   "--root", str(self.root), "--out", str(out)]
        first = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertTrue(out.is_file())
        self.assertTrue(out.with_suffix(".json").is_file())
        second = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("refusing to overwrite", second.stderr)


if __name__ == "__main__":
    timestamp = subprocess.check_output(["date", "-u", "+%Y-%m-%d %H:%M:%S UTC"], text=True).strip()
    print(f"UTC (date -u): {timestamp}; machine: {platform.node()}; PID: {os.getpid()}", flush=True)
    unittest.main(verbosity=2)
