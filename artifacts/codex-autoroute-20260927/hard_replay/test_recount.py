#!/usr/bin/env python3
"""Synthetic, raw-only AR2 recount checks; no AutoNet construction or MPS use."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import platform
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import recount


HERE = Path(__file__).resolve().parent
REGISTRATION = "542f61b8c63e505ed02b881eb2216d57001ed1c7"
KINDS = (("grids", 5), ("sums", 4), ("mazes", 7))


def rows(n_each: int, start: int) -> list[dict]:
    """Unique small synthetic inputs; these are never scientific panels."""
    result = []
    for kind, size in KINDS:
        for offset in range(n_each):
            number = start + len(result)
            tokens = [[number % 125, number // 125, 7]]
            slot = [[1, 0, 0]]
            result.append({"id": recount.canonical_id(tokens, slot), "env": kind,
                           "size": size, "tokens": tokens, "slot": slot,
                           "target": [[1, 2, 3]], "meta": {}})
    return result


def raw(row: dict) -> dict:
    context = [0.0] * 4
    context[{kind: i for i, (kind, _) in enumerate(KINDS)}[row["env"]]] = 1.0
    return {"id": row["id"], "predictions": [[1, 2, 3] for _ in range(48)],
            "stop_probabilities": [0.0, 0.0] + [0.75] * 46,
            "context_probabilities": context}


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def write_stream(path: Path, values: list[dict]) -> None:
    path.write_text("".join(json.dumps(value, separators=(",", ":")) + "\n" for value in values),
                    encoding="utf-8")


def phase_sizes(phase: str, candidate: bool) -> dict[str, int]:
    sizes = {key: 0 for key in recount.SIZE_KEYS}
    if phase == "A":
        sizes.update(grids4=1250, grids5=1250)
    elif phase == "B":
        sizes.update(grids4=0 if candidate else 120,
                     grids5=250 if candidate else 130,
                     sums1=500, sums2=500, sums3=500, sums4=750)
    else:
        sizes.update(grids4=0 if candidate else 37,
                     grids5=75 if candidate else 38,
                     sums1=18, sums2=19, sums3=19, sums4=19,
                     mazes5=675, mazes7=675)
    return sizes


def result_metadata(candidate: bool) -> dict:
    return {
        "phases": {phase: {"steps": steps, "kind_batches": dict(kinds),
                           "size_batches": phase_sizes(phase, candidate)}
                   for phase, (steps, kinds) in recount.PHASE_BUDGETS.items()},
        "practice_panel_rejections": {kind: 0 for kind, _ in KINDS},
    }


class FakeItem:
    def __init__(self, env, size, tokens, slot, target, meta):
        self.target = target


FAKE_API = (None,
            SimpleNamespace(Item=FakeItem, check=lambda item, prediction: prediction == item.target),
            SimpleNamespace(grid_of=lambda prediction, item: [prediction]))


class RecountSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="recount-synthetic-", dir=HERE)
        self.addCleanup(self.temporary.cleanup)
        self.fixture_dir = Path(self.temporary.name)

    def test_registered_stop_rule(self):
        predictions = [[i] for i in range(48)]
        probabilities = [0.9] * 48
        self.assertEqual(recount.own_stop(predictions, probabilities), 48)
        predictions[:3] = [[1], [1], [1]]
        probabilities[2] = 0.5
        for i in range(3, 48):
            predictions[i] = [i]
        self.assertEqual(recount.own_stop(predictions, probabilities), 48)
        probabilities[2] = 0.50001
        self.assertEqual(recount.own_stop(predictions, probabilities), 3)
        predictions[:3] = [[0], [1], [2]]
        predictions[3:6] = [[8], [8], [8]]
        self.assertEqual(recount.own_stop(predictions, probabilities), 6)

    def test_exact_kind_and_size_budgets(self):
        for arm, candidate in (("baseline", False), ("hard_grid_replay", True)):
            metadata = result_metadata(candidate)
            recount.validate_budget(metadata, arm, arm)
            wrong = copy.deepcopy(metadata)
            wrong["phases"]["B"]["size_batches"]["sums4"] += 1
            with self.assertRaisesRegex(ValueError, "size counts"):
                recount.validate_budget(wrong, arm, arm)
            wrong = copy.deepcopy(metadata)
            wrong["phases"]["C"]["kind_batches"]["mazes"] -= 1
            with self.assertRaisesRegex(ValueError, "kind-batch budget"):
                recount.validate_budget(wrong, arm, arm)
            wrong = copy.deepcopy(metadata)
            del wrong["phases"]["A"]["size_batches"]["sums1"]
            with self.assertRaisesRegex(ValueError, "eight nonnegative"):
                recount.validate_budget(wrong, arm, arm)
        wrong = result_metadata(True)
        wrong["phases"]["B"]["size_batches"].update(grids4=1, grids5=249)
        with self.assertRaisesRegex(ValueError, "not all grid5"):
            recount.validate_budget(wrong, "hard_grid_replay", "candidate")
        wrong = result_metadata(True)
        wrong["phases"]["C"]["size_batches"]["grids4"] = True
        with self.assertRaisesRegex(ValueError, "eight nonnegative"):
            recount.validate_budget(wrong, "hard_grid_replay", "candidate")

    def test_new_panel_seed_contract_and_duplicates(self):
        panel = {"seed": 61, "panel_seed": 927206481061,
                 "diagnostic_seed": 927206482061,
                 "duplicate_rejections": {"final": 0, "diagnostic": 0},
                 "final": rows(200, 0), "diagnostic": rows(100, 600)}
        path = self.fixture_dir / "synthetic-panel.json"
        write_json(path, panel)
        self.assertEqual(len(recount.load_panel(path, 61)["final"]), 600)
        wrong = copy.deepcopy(panel)
        wrong["panel_seed"] += 1
        write_json(path, wrong)
        with self.assertRaisesRegex(ValueError, "panel seed"):
            recount.load_panel(path, 61)
        wrong = copy.deepcopy(panel)
        wrong["diagnostic"][0] = copy.deepcopy(wrong["final"][0])
        write_json(path, wrong)
        with self.assertRaisesRegex(ValueError, "overlap"):
            recount.load_panel(path, 61)

    def test_raw_scores_and_corrupt_stream(self):
        panel = rows(200, 0)
        predictions = [raw(row) for row in panel]
        path = self.fixture_dir / "synthetic-C.jsonl"
        write_stream(path, predictions)
        with mock.patch.object(recount, "model_api", return_value=FAKE_API):
            scores, stopping = recount.recount_stream(path, panel)
        for score in scores.values():
            self.assertEqual(score, {"right": 200, "n": 200, "fixed16": 200,
                                     "any48": 200, "stopping_rounds_sum": 600})
        self.assertEqual(stopping["mean_rounds"], 3)
        wrong = copy.deepcopy(predictions)
        wrong[0]["id"] = "0" * 64
        write_stream(path, wrong)
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            list(recount.read_stream(path, panel))
        wrong = copy.deepcopy(predictions)
        wrong[0]["context_probabilities"] = [0.5, 0.5]
        write_stream(path, wrong)
        with self.assertRaisesRegex(ValueError, "four-way"):
            list(recount.read_stream(path, panel))

    def test_diagnostic_context_recount_and_corruption(self):
        diagnostic, final = rows(100, 600), rows(200, 0)
        diag_path, final_path = self.fixture_dir / "diagnostic.jsonl", self.fixture_dir / "C.jsonl"
        write_stream(diag_path, [raw(row) for row in diagnostic])
        write_stream(final_path, [raw(row) for row in final])
        counts = {str(i): {kind: 100 if i == j else 0 for j, (kind, _) in enumerate(KINDS)}
                  for i in range(3)}
        counts["3"] = {kind: 0 for kind, _ in KINDS}
        recorded = {"mapping": {"0": "grids", "1": "sums", "2": "mazes", "3": "grids"},
                    "calibration_counts": counts, "agreement": 600, "n": 600}
        self.assertEqual(recount.recount_context(diag_path, diagnostic, final_path, final, recorded), recorded)
        wrong = copy.deepcopy(recorded)
        wrong["agreement"] = 599
        with self.assertRaisesRegex(ValueError, "context agreement differs"):
            recount.recount_context(diag_path, diagnostic, final_path, final, wrong)
        corrupt = [raw(row) for row in diagnostic]
        corrupt[0]["context_probabilities"] = [float("nan"), 0.0, 0.0, 0.0]
        # JSON NaN is invalid under the recount's strict parser.
        write_stream(diag_path, corrupt)
        with self.assertRaises(ValueError):
            recount.recount_context(diag_path, diagnostic, final_path, final, recorded)

    def test_parent_model_path_manifest_and_registration(self):
        self.assertEqual(recount.REPO, HERE.parents[2])
        self.assertEqual(recount.REGISTRATION, REGISTRATION)
        required = ("artifacts/codex-autoroute-20260927/auto_model.py",
                    "artifacts/codex-autoroute-20260927/hard_replay/run_experiment.py")
        hashes = {name: hashlib.sha256((recount.REPO / name).read_bytes()).hexdigest()
                  for name in required}
        manifest = {"software_commit": "a" * 40, "source_hashes": hashes}

        def committed_bytes(command, **_kwargs):
            name = command[2].split(":", 1)[1]
            return (recount.REPO / name).read_bytes()

        with mock.patch.object(recount.subprocess, "check_output", side_effect=committed_bytes):
            self.assertEqual(recount.source_manifest(manifest, "synthetic"), hashes)
        wrong = copy.deepcopy(manifest)
        del wrong["source_hashes"][required[1]]
        with self.assertRaisesRegex(ValueError, "must cover parent"):
            recount.source_manifest(wrong, "synthetic")
        marks = "artifacts/codex-autoroute-20260927/hard_replay/PASSMARKS.md"
        registered = subprocess.check_output(["git", "show", f"{REGISTRATION}:{marks}"],
                                             cwd=recount.REPO)
        self.assertEqual(registered, (HERE / "PASSMARKS.md").read_bytes())


if __name__ == "__main__":
    print(f"UTC: {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S UTC}; "
          f"machine: {platform.node()}; PID: {os.getpid()}", flush=True)
    unittest.main(verbosity=2)
