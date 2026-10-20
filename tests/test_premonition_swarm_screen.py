"""The swarm screen kit (scripts/premonition_swarm_screen.py, scripts/premonition_swarm_marks.py; CPU, seconds).

No data files: eval, train and c0 JSON are synthetic. What is checked is the readout's logic -- every S0 verdict
branch, the S1 board branches, the per-seed (never averaged) DEV slip, cell membership against the real
`exp1.slice_report`, the T formula and the two C0 stop flags -- and that the constants copied into the
(torch-free) readout still equal the library's.
"""
from __future__ import annotations

import copy
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

# The runner sets its cache and temp variables (TMPDIR and others) at import time, for its own process. Restore
# the environment afterwards so the rest of the test process is unaffected (round 3, sixth pass, item 19).
_ENV_BEFORE = dict(os.environ)
_TEMPDIR_BEFORE = tempfile.tempdir
import premonition_swarm_screen as screen                        # noqa: E402  (bootstraps before torch)
import premonition_swarm_marks as marks                          # noqa: E402
os.environ.clear()
os.environ.update(_ENV_BEFORE)
tempfile.tempdir = _TEMPDIR_BEFORE

from learnlab import policy                                      # noqa: E402
from premonition import exp1, slices, swarm                      # noqa: E402
from premonition import config as pconfig                        # noqa: E402

T = 300
SEEDS = (0, 1, 2)
FAR_N = 120
NEAR_N = 120
OTHER_N = 20
EXCLUDED_N = 5
HEALTHY = dict(ask_rate=[0.5, 0.5, 0.5, 0.5], fetch_count=[2.0, 2.2, 1.9, 2.1], fetch_overlap=0.4,
               register_cos=0.5, collapsed=False, silent_desks=0)


def cell_of(items: list[dict], name: str) -> dict:
    members = [i for i in items if name in i["slices"]]
    hits = sum(i["correct"] for i in members)
    return {"n": len(members), "hits": hits, "accuracy": hits / len(members) if members else None}


def make_items(far_hits: int, near_hits: int, *, far_n: int = FAR_N, near_n: int = NEAR_N, oth_hits: int = 10
               ) -> list[dict]:
    """Items with fixed ids; the first `hits` of a group are correct, so groups nest across arms."""
    items = []
    for k in range(far_n):
        items.append({"id": f"far{k}", "correct": int(k < far_hits), "decision": True,
                      "slices": ["overall", "far", "far_deep", "multi_hop", "depth_2", "changed"]})
    for k in range(near_n):
        items.append({"id": f"near{k}", "correct": int(k < near_hits), "decision": True,
                      "slices": ["overall", "near", "depth_1", "unchanged"]})
    for k in range(OTHER_N):
        items.append({"id": f"oth{k}", "correct": int(k < oth_hits), "decision": True,
                      "slices": ["overall", "far", "depth_3", "multi_hop"]})
    for k in range(EXCLUDED_N):
        items.append({"id": f"exc{k}", "correct": 1, "decision": False,
                      "slices": ["excluded", "excluded:repeat"]})
    return items


def eval_report(arm: str, seed: int, items: list[dict], *, lesion=None, swarm_diag=None, tag="tag-1",
                sha="sha-1") -> dict:
    summary = {
        "items": len(items),
        "decision_cells": {name: {**cell_of(items, name), "enough": True} for name in marks.DECISION_CELLS},
        "per_depth": {str(d): cell_of(items, f"depth_{d}") for d in marks.DEPTHS},
        "cells": {name: cell_of(items, name) for name in ("changed", "unchanged", "depth_1", "depth_2", "depth_3")},
    }
    mini = {"thinkers": 1, "swarm_board": False} if arm == "D1" else {"thinkers": 4, "swarm_board": arm == "S1"}
    retrieval = {} if swarm_diag is None else {"swarm": swarm_diag}
    return {"split": "validation", "lesion": lesion, "checkpoint": f"checkpoints/swarm-screen/{arm}-s{seed}",
            "identity": {"primary": True, "regime": "label-free"},
            "config": {"mini": mini}, "data": {"tag": tag}, "tokenizer": {"sha256": sha},
            "items": {"validation": items},
            "directories": {"validation": {"summary": summary, "retrieval": retrieval}}}


def refresh(report: dict) -> None:
    """Recompute a synthetic eval report's summary cells from its (edited) items."""
    items = report["items"]["validation"]
    summary = report["directories"]["validation"]["summary"]
    for name in marks.DECISION_CELLS:
        summary["decision_cells"][name].update(cell_of(items, name))
    for d in marks.DEPTHS:
        summary["per_depth"][str(d)] = cell_of(items, f"depth_{d}")
    for name in list(summary["cells"]):
        summary["cells"][name] = cell_of(items, name)


def train_report(arm: str, seed: int, *, seconds: float = T * 1.004, tag="tag-1", sha="sha-1", steps=1000) -> dict:
    return {"status": "completed", "arm": arm, "seed": seed, "train_seconds": seconds, "seconds_budget": T,
            "steps": steps, "stop": "seconds budget", "loop_mismatches": 0, "final": {"loss": 2.3},
            "history": [{"step": 50, "loss": 2.4}, {"step": 100, "loss": 2.3}], "nonfinite_logged_steps": [],
            "parameters": 1, "size": "full",
            "swarm": marks.EXPECTED_SWARM[arm], "data": {"tag": tag}, "tokenizer": {"sha256": sha}}


class Scenario:
    """Per-arm, per-seed hits; build() writes the folder. Defaults give PROMOTE for S0."""

    def __init__(self) -> None:
        self.far = {"D1": [60, 60, 60], "S0": [75, 75, 75], "S1": [90, 90, 90]}
        self.near = {"D1": [100, 100, 100], "S0": [100, 100, 100], "S1": [100, 100, 100]}
        self.oth = {arm: [10, 10, 10] for arm in ("D1", "S0", "S1")}
        self.swarm = {"S0": [dict(HEALTHY) for _ in SEEDS], "S1": [dict(HEALTHY) for _ in SEEDS]}
        self.lesion_far = {"board": [60, 60, 60], "notes": [80, 80, 80], "cards": [70, 70, 70]}
        self.seconds = {}
        self.far_n = FAR_N
        self.edits = []                      # (filename, function(dict))

    def build(self, folder: Path, *, with_s1: bool = False) -> Path:
        def write(name: str, payload: dict) -> None:
            (folder / name).write_text(json.dumps(payload), encoding="utf-8")

        write("c0.json", {"T": T, "T_formula": T, "t_override": None, "tag": "tag-1", "tokenizer_sha256": "sha-1"})
        arms = ("D1", "S0", "S1") if with_s1 else ("D1", "S0")
        for arm in arms:
            for seed in SEEDS:
                write(f"train-{arm}-s{seed}.json", train_report(arm, seed, seconds=self.seconds.get((arm, seed), T * 1.004)))
                diag = None if arm == "D1" else self.swarm[arm][seed]
                items = make_items(self.far[arm][seed], self.near[arm][seed], far_n=self.far_n,
                                   oth_hits=self.oth[arm][seed])
                write(f"eval-{arm}-s{seed}.json", eval_report(arm, seed, items, swarm_diag=diag))
                if arm == "S1":
                    for lesion in marks.LESIONS:
                        write(f"eval-S1-s{seed}-{lesion}.json",
                              eval_report(arm, seed, make_items(self.lesion_far[lesion][seed], self.near[arm][seed],
                                                                far_n=self.far_n),
                                          lesion=lesion, swarm_diag=self.swarm[arm][seed]))
        for name, edit in self.edits:
            payload = json.loads((folder / name).read_text(encoding="utf-8"))
            edit(payload)
            write(name, payload)
        return folder


class MarksTestCase(unittest.TestCase):
    def run_card(self, scenario: Scenario, card: str = "S0", **options) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            scenario.build(Path(tmp), with_s1=card == "S1")
            return marks.run(card, tmp, **options)

    def assertVerdict(self, result: dict, verdict: str) -> None:
        self.assertEqual(result["verdict"], verdict, result["verdict_line"] + " " + str(result["void_reasons"]))
        self.assertTrue(result["verdict_line"].startswith("VERDICT: " + verdict), result["verdict_line"])


class S0VerdictTest(MarksTestCase):
    def test_seed_repeated_items_are_not_counted_as_independent(self) -> None:
        """Round 3, item 3 (coordinator ruling): every seed scores the same items, so the pooled test pairs the
        per-item SEED MEANS. Here the same 6 far_deep items flip in every seed (+5 pts on each seed): as 18
        "independent" pairs McNemar gives p ~ 4e-6 (the old PROMOTE). As 6 items the sign-flip test gives
        p ~ 1/64 > 0.01, so M1 fails and the verdict is HOLD."""
        scenario = Scenario()
        scenario.far = {"D1": [60, 60, 60], "S0": [66, 66, 66], "S1": [66, 66, 66]}
        out = self.run_card(scenario)
        m1 = next(m for m in out["marks"] if m["mark"] == "M1")
        self.assertEqual(m1["detail"]["n_pooled"], FAR_N)
        self.assertGreaterEqual(m1["detail"]["p"], 0.01)
        self.assertEqual(m1["status"], "fail")
        self.assertVerdict(out, "HOLD")
        from learnlab.metrics import paired_greater_pvalue
        old_p = paired_greater_pvalue([1] * 18, [0] * 18)                      # what 3x pooling had computed
        self.assertLess(old_p, 0.01)

    def test_promote_and_every_mark_is_computed(self) -> None:
        result = self.run_card(Scenario())
        self.assertVerdict(result, "PROMOTE")
        self.assertEqual({m["mark"] for m in result["marks"]}, {"M1", "M2", "M3", "M4", "M5", "M6", "KILL"})
        self.assertTrue(all(result["marks_computed"].values()))
        m1 = next(m for m in result["marks"] if m["mark"] == "M1")
        self.assertEqual(m1["status"], "pass")
        self.assertAlmostEqual(m1["detail"]["delta_points"], 100 * 15 / FAR_N)       # 12.5 points
        self.assertEqual(m1["detail"]["n_pooled"], FAR_N)                # pooled unit = the item (round 3, item 3)
        self.assertLess(m1["detail"]["p"], 0.01)

    def test_void_on_a_schema_mismatch(self) -> None:
        scenario = Scenario()
        scenario.edits.append(("eval-S0-s1.json", lambda r: r["directories"]["validation"]["summary"]["decision_cells"]
                               ["far_deep"].update(hits=r["directories"]["validation"]["summary"]["decision_cells"]
                                                   ["far_deep"]["hits"] + 1)))
        result = self.run_card(scenario)
        self.assertVerdict(result, "VOID")
        self.assertIn("schema", result["verdict_line"])
        self.assertIn("far_deep", result["verdict_line"])
        self.assertTrue(all(result["marks_computed"].values()), "the other marks are still computed")

    def test_void_when_the_two_arms_have_different_items(self) -> None:
        scenario = Scenario()
        scenario.edits.append(("eval-D1-s2.json", lambda r: r["items"]["validation"][0].update(id="stranger")))
        result = self.run_card(scenario)
        self.assertVerdict(result, "VOID")
        self.assertTrue(any("item id sets differ" in reason for reason in result["void_reasons"]))

    def test_void_on_train_seconds(self) -> None:
        scenario = Scenario()
        scenario.seconds[("S0", 1)] = T * 1.05
        result = self.run_card(scenario)
        self.assertVerdict(result, "VOID")
        self.assertIn("seconds", result["verdict_line"])
        self.assertIn("train-S0-s1", result["verdict_line"])
        within = Scenario()
        within.seconds[("S0", 1)] = T * 1.019
        self.assertVerdict(self.run_card(within), "PROMOTE")

    def test_void_on_a_missing_or_unfinished_train(self) -> None:
        scenario = Scenario()
        scenario.edits.append(("train-D1-s0.json", lambda r: r.update(status="aborted")))
        self.assertVerdict(self.run_card(scenario), "VOID")
        scenario = Scenario()
        scenario.edits.append(("train-D1-s0.json", lambda r: r["final"].update(loss="nan")))
        self.assertVerdict(self.run_card(scenario), "VOID")
        scenario = Scenario()
        scenario.edits.append(("train-S0-s0.json", lambda r: r.update(loop_mismatches=3)))
        self.assertVerdict(self.run_card(scenario), "VOID")

    def test_void_on_two_tokenizers(self) -> None:
        scenario = Scenario()
        scenario.edits.append(("eval-S0-s0.json", lambda r: r["tokenizer"].update(sha256="other")))
        self.assertVerdict(self.run_card(scenario), "VOID")

    def test_insufficient_below_min_items_and_the_full_path_with_min_items_1(self) -> None:
        scenario = Scenario()
        scenario.far_n = 60
        scenario.far = {"D1": [30] * 3, "S0": [40] * 3, "S1": [50] * 3}
        result = self.run_card(scenario)
        self.assertVerdict(result, "INSUFFICIENT")
        self.assertTrue(all(result["marks_computed"].values()), "every other mark is still computed")
        self.assertVerdict(self.run_card(scenario, min_items=1), "PROMOTE")

    def test_void_outranks_insufficient(self) -> None:
        scenario = Scenario()
        scenario.far_n = 60
        scenario.far = {"D1": [30] * 3, "S0": [40] * 3, "S1": [50] * 3}
        scenario.seconds[("D1", 0)] = T * 2
        self.assertVerdict(self.run_card(scenario), "VOID")

    def test_kill_when_s0_is_not_better(self) -> None:
        scenario = Scenario()
        scenario.far["S0"] = [60, 60, 60]                                  # pooled difference exactly 0
        self.assertVerdict(self.run_card(scenario), "KILL")
        scenario = Scenario()
        scenario.far["S0"] = [50, 55, 90]                                  # pooled > 0 but S0 < D1 on 2 of 3 seeds
        result = self.run_card(scenario)
        self.assertVerdict(result, "KILL")
        self.assertGreater(next(m for m in result["marks"] if m["mark"] == "M1")["detail"]["delta_points"], 0)

    def test_kill_outranks_a_guard_fail(self) -> None:
        scenario = Scenario()
        scenario.far["S0"] = [50, 50, 50]
        scenario.swarm["S0"] = [dict(HEALTHY, ask_rate=[0.5, 0.5, 0.5, 0.01]) for _ in SEEDS]
        self.assertVerdict(self.run_card(scenario), "KILL")

    def test_dev_slip_fails_on_two_seeds(self) -> None:
        scenario = Scenario()
        scenario.near["S0"] = [85, 85, 100]                                # near drops 12.5 points on seeds 0 and 1
        result = self.run_card(scenario)
        self.assertVerdict(result, "FAIL")
        self.assertIn("M2", result["verdict_line"])

    def test_dev_slip_is_per_seed_never_averaged(self) -> None:
        scenario = Scenario()
        scenario.near["S0"] = [60, 100, 100]                               # one seed -33 points, the 3-seed mean -11
        result = self.run_card(scenario)
        m2 = next(m for m in result["marks"] if m["mark"] == "M2")
        mean_drop = sum(r["delta_points"] for r in m2["detail"]["near"]) / 3
        self.assertLess(mean_drop, -3.0, "the 3-seed mean does slip")
        self.assertEqual([r["slip"] for r in m2["detail"]["near"]], [True, False, False])
        self.assertEqual(m2["status"], "pass")
        self.assertVerdict(result, "PROMOTE")

    def test_overall_slip_is_judged_separately_from_near(self) -> None:
        scenario = Scenario()
        scenario.far["S0"] = [61, 61, 61]                                  # a tiny gain, so not KILL and not PROMOTE
        scenario.oth["D1"] = [20, 20, 20]
        scenario.oth["S0"] = [0, 0, 20]                                    # overall falls 7 points on seeds 0 and 1 only
        result = self.run_card(scenario)
        m2 = next(m for m in result["marks"] if m["mark"] == "M2")
        self.assertEqual([r["slip"] for r in m2["detail"]["near"]], [False, False, False])
        self.assertEqual([r["slip"] for r in m2["detail"]["overall"]], [True, True, False])
        self.assertEqual(m2["status"], "fail")
        self.assertVerdict(result, "FAIL")
        self.assertIn("M2 DEV slip", result["verdict_line"])

    def test_usage_collapse_fails_m3(self) -> None:
        scenario = Scenario()
        scenario.swarm["S0"][0] = dict(HEALTHY, ask_rate=[0.5, 0.5, 0.5, 0.01])
        scenario.swarm["S0"][1] = dict(HEALTHY, fetch_count=[2.0, 0.1, 2.0, 2.0])      # 0.1 < 0.10 x 2.0 is false: 0.1 < 0.2
        result = self.run_card(scenario)
        self.assertVerdict(result, "FAIL")
        self.assertIn("M3", result["verdict_line"])
        self.assertIn("USAGE-COLLAPSE", result["verdict_line"])

    def test_usage_is_ok_on_two_of_three_seeds(self) -> None:
        scenario = Scenario()
        scenario.swarm["S0"][2] = dict(HEALTHY, ask_rate=[0.5, 0.04, 0.5, 0.5])        # one bad seed only
        self.assertVerdict(self.run_card(scenario), "PROMOTE")

    def test_hold_for_a_small_gain(self) -> None:
        scenario = Scenario()
        scenario.far["S0"] = [61, 61, 61]                                  # +0.8 points
        self.assertVerdict(self.run_card(scenario), "HOLD")
        scenario = Scenario()
        scenario.far["S0"] = [64, 64, 64]                                  # +3.3 points but p ~ 0.06 (4 discordant per seed)
        result = self.run_card(scenario)
        m1 = next(m for m in result["marks"] if m["mark"] == "M1")
        self.assertGreater(m1["detail"]["delta_points"], 3.0)
        self.assertGreater(m1["detail"]["p"], 0.0001)

    def test_hold_when_the_gain_is_large_but_not_significant(self) -> None:
        def two_way(report):
            for item in report["items"]["validation"]:
                if item["id"] in {f"far{k}" for k in range(8)}:
                    item["correct"] = 0                                    # 8 items S0 gets wrong that D1 gets right
                if item["id"] in {f"far{k}" for k in range(60, 72)}:
                    item["correct"] = 1                                    # 12 items S0 gets right that D1 gets wrong
            refresh(report)

        scenario = Scenario()
        scenario.far = {"D1": [60, 60, 60], "S0": [60, 60, 60], "S1": [90, 90, 90]}
        scenario.edits += [(f"eval-S0-s{seed}.json", two_way) for seed in SEEDS]
        result = self.run_card(scenario)
        m1 = next(m for m in result["marks"] if m["mark"] == "M1")
        self.assertAlmostEqual(m1["detail"]["delta_points"], 100 * 12 / (3 * FAR_N))                # +3.33 points
        self.assertEqual(m1["detail"]["seeds_positive"], 3)
        self.assertGreater(m1["detail"]["p"], 0.01)
        self.assertEqual(m1["status"], "fail")
        self.assertVerdict(result, "HOLD")

    def test_collapsed_desks_block_promote(self) -> None:
        scenario = Scenario()
        scenario.swarm["S0"] = [dict(HEALTHY, register_cos=0.99, fetch_overlap=0.9, collapsed=True),
                                dict(HEALTHY, register_cos=0.99, fetch_overlap=0.9, collapsed=True),
                                dict(HEALTHY)]
        result = self.run_card(scenario)
        self.assertVerdict(result, "HOLD")
        self.assertIn("COLLAPSED: the desks are copies", result["verdict_line"])
        one_seed = Scenario()
        one_seed.swarm["S0"][0] = dict(HEALTHY, register_cos=0.99, fetch_overlap=0.9, collapsed=True)
        self.assertVerdict(self.run_card(one_seed), "PROMOTE")

    def test_collapsed_text_rides_on_a_fail_too(self) -> None:
        scenario = Scenario()
        scenario.swarm["S0"] = [dict(HEALTHY, ask_rate=[0.5, 0.5, 0.5, 0.0], register_cos=0.99, fetch_overlap=0.9,
                                     collapsed=True) for _ in SEEDS]
        result = self.run_card(scenario)
        self.assertVerdict(result, "FAIL")
        self.assertIn("COLLAPSED: the desks are copies", result["verdict_line"])

    def test_collapsed_flag_that_disagrees_with_its_numbers_is_void(self) -> None:
        scenario = Scenario()
        scenario.swarm["S0"][0] = dict(HEALTHY, register_cos=0.99, fetch_overlap=0.9, collapsed=False)
        self.assertVerdict(self.run_card(scenario), "VOID")

    def test_nan_swarm_numbers_do_not_crash(self) -> None:
        scenario = Scenario()
        scenario.swarm["S0"][0] = dict(HEALTHY, fetch_overlap="nan")
        result = self.run_card(scenario)
        self.assertIn(result["verdict"], ("PROMOTE", "HOLD", "FAIL", "VOID"))

    def test_readout_files_and_one_verdict_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Scenario().build(Path(tmp))
            out = Path(tmp) / "MARKS-S0.json"
            marks.main(["--card", "S0", "--dir", tmp, "--out", str(out), "--note", "DRY RUN: meaningless"])
            text = out.with_suffix(".md").read_text(encoding="utf-8")
            self.assertEqual(sum(1 for line in text.splitlines() if line.startswith("VERDICT")), 1)
            self.assertIn("DRY RUN: meaningless", text)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["verdict"], "PROMOTE")


class S1VerdictTest(MarksTestCase):
    def test_pass_when_the_board_adds_and_is_used(self) -> None:
        result = self.run_card(Scenario(), "S1")
        self.assertVerdict(result, "PASS")
        self.assertTrue(all(result["marks_computed"].values()))
        info = result["information"]["information"]
        self.assertAlmostEqual(info["lesion_board_drop"]["delta_points"], 100 * 30 / FAR_N)
        self.assertGreater(info["lesion_notes_drop"]["delta_points"], 0)
        self.assertEqual(set(result["information"]["cells"]), {"D1", "S0", "S1"})

    def test_board_unused_fails(self) -> None:
        scenario = Scenario()
        scenario.lesion_far["board"] = [90, 90, 90]                        # lesioning the board costs nothing
        result = self.run_card(scenario, "S1")
        self.assertVerdict(result, "FAIL")
        self.assertIn("BOARD-UNUSED", result["verdict_line"])

    def test_kill_comm(self) -> None:
        scenario = Scenario()
        scenario.far["S1"] = [75, 75, 75]
        scenario.lesion_far["board"] = [60, 60, 60]
        self.assertVerdict(self.run_card(scenario, "S1"), "KILL-COMM")

    def test_hold_for_a_small_communication_gain(self) -> None:
        scenario = Scenario()
        scenario.far["S1"] = [76, 76, 76]
        self.assertVerdict(self.run_card(scenario, "S1"), "HOLD")

    def test_dev_slip_against_d1(self) -> None:
        scenario = Scenario()
        scenario.near["S1"] = [80, 80, 100]
        result = self.run_card(scenario, "S1")
        self.assertVerdict(result, "FAIL")
        self.assertIn("M3 DEV slip", result["verdict_line"])

    def test_the_board_collapsed_the_desks(self) -> None:
        scenario = Scenario()
        scenario.swarm["S1"] = [dict(HEALTHY, register_cos=0.99, fetch_overlap=0.9, collapsed=True) for _ in SEEDS]
        result = self.run_card(scenario, "S1")
        self.assertVerdict(result, "HOLD")
        self.assertIn("the board collapsed the desks", result["verdict_line"])
        both = Scenario()
        both.swarm["S0"] = [dict(HEALTHY, register_cos=0.99, fetch_overlap=0.9, collapsed=True) for _ in SEEDS]
        both.swarm["S1"] = [dict(HEALTHY, register_cos=0.99, fetch_overlap=0.9, collapsed=True) for _ in SEEDS]
        self.assertNotIn("the board collapsed the desks", self.run_card(both, "S1")["verdict_line"])

    def test_a_missing_lesion_file_is_void(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Scenario().build(Path(tmp), with_s1=True)
            (Path(tmp) / "eval-S1-s1-board.json").unlink()
            self.assertVerdict(marks.run("S1", tmp), "VOID")

    def test_a_lesion_file_labelled_wrongly_is_void(self) -> None:
        scenario = Scenario()
        scenario.edits.append(("eval-S1-s0-notes.json", lambda r: r.update(lesion="cards")))
        self.assertVerdict(self.run_card(scenario, "S1"), "VOID")


class CellMembershipTest(unittest.TestCase):
    """The readout's cell rebuild against the real `exp1.slice_report` on real `SliceTags`."""

    def rows(self):
        def tag(i, **fields):
            base = dict(id=f"q{i}", source="validation", split="validation", qtype="Q1", bank="q.where_object",
                        depth=1, knowable=True, evidence_kept=True, repeat=False, repeat_in_visit=False,
                        reworded=False, names=(), changed=False)
            base.update(fields)
            return slices.SliceTags(**base)

        specs = [dict(), dict(evidence_kept=False, depth=2), dict(evidence_kept=False, depth=3),
                 dict(evidence_kept=False, depth=5, changed=True), dict(evidence_kept=False, depth=2, repeat=True),
                 dict(evidence_kept=True, repeat_in_visit=True), dict(evidence_kept=False, depth=4, bank="leak"),
                 dict(knowable=False, evidence_kept=None, depth=None), dict(evidence_kept=None),
                 dict(evidence_kept=False, depth=2, changed=None), dict(evidence_kept=True, depth=2)]
        tags, results = {}, []
        for i in range(36):
            spec = specs[i % len(specs)]
            t = tag(i, **spec)
            tags[t.id] = t
            results.append({"id": t.id, "split": "validation", "qtype": "Q1", "depth": t.depth, "visible": True,
                            "knowable": t.knowable, "rule_families": [], "heldout_family": False,
                            "template": "seen", "style": None, "style_status": "seen", "name_answer": False,
                            "truncated": False, "evidence_kept": t.evidence_kept, "repeat_in_context": t.repeat,
                            "changed_since_asked": None, "twin": None, "answer": "a", "prediction": "a" if i % 3 else "b",
                            "exact": bool(i % 3), "plan_checked": False, "correct": bool(i % 3)})
        return exp1.attach(results, tags)

    def test_the_readout_rebuilds_exp1_cells_exactly(self) -> None:
        rows = self.rows()
        info = exp1.slice_report(rows, min_items=1)
        report = {"split": "validation", "lesion": None, "checkpoint": "x/S0-s0", "config": {"mini": {
            "thinkers": 4, "swarm_board": False}}, "data": {"tag": "t"}, "tokenizer": {"sha256": "s"},
                  "items": {"validation": [{key: row[key] for key in exp1._ITEM_KEYS} for row in rows]},
                  "directories": {"validation": {"summary": info, "retrieval": {"swarm": dict(HEALTHY)}}}}
        report = json.loads(json.dumps(exp1.jsonable(report)))
        with tempfile.TemporaryDirectory() as tmp:
            ctx = marks.Context(directory=Path(tmp), seeds=SEEDS, min_items=1, seconds_tol=0.02)
            (Path(tmp) / "eval-S0-s0.json").write_text(json.dumps(report), encoding="utf-8")
            found = marks.load_eval(ctx, "S0", 0, None)
            self.assertEqual(ctx.void, [])
            for name in slices.DECISION_SLICES:
                self.assertEqual(found.cell(name), (info["decision_cells"][name]["hits"], info["decision_cells"][name]["n"]))
            self.assertGreater(found.cell("far_deep")[1], 0)
            self.assertGreater(found.cell("overall")[1], 0)
            self.assertLess(found.cell("overall")[1], len(rows), "excluded items are in no decision cell")
            # a deliberately wrong count is caught
            report["directories"]["validation"]["summary"]["decision_cells"]["far"]["n"] += 1
            (Path(tmp) / "eval-S0-s0.json").write_text(json.dumps(report), encoding="utf-8")
            marks.load_eval(ctx, "S0", 0, None)
            self.assertTrue(any("cell far" in reason for reason in ctx.void))


class RunnerMathTest(unittest.TestCase):
    def test_t_formula_rounds_up_to_300_and_caps_at_3600(self) -> None:
        flops = 1e14
        for raw, want in [(1.0, 300), (299.9, 300), (300.0, 300), (300.5, 600), (601.0, 900), (3599.0, 3600),
                          (3600.0, 3600), (3600.5, 3600), (1e6, 3600)]:
            got_raw, got = screen.compute_T(screen.F_TARGET / raw)
            self.assertAlmostEqual(got_raw, raw, delta=raw * 1e-9)
            self.assertEqual(got, want, raw)
        with self.assertRaises(ValueError):
            screen.compute_T(0.0)
        with self.assertRaises(ValueError):
            screen.compute_T(float("nan"))
        self.assertEqual(flops, 1e14)

    def test_weighted_and_median(self) -> None:
        self.assertAlmostEqual(screen.weighted({"gold": 1.0, "teacher": 2.0, "own": 3.0}), 0.05 + 0.5 + 2.1)
        self.assertEqual(screen.median_of([3.0, 1.0, 2.0]), 2.0)
        self.assertEqual(screen.median_of([1.0, 2.0, 3.0, 4.0]), 2.5)

    def test_stop_and_ask_flag(self) -> None:
        self.assertFalse(screen.stop_flags(2.5, 1.0, 300, 60, 0.4, train_overhead=0.0)["stop_and_ask"])          # exactly 2.5: no
        self.assertTrue(screen.stop_flags(2.5001, 1.0, 300, 60, 0.4, train_overhead=0.0)["stop_and_ask"])
        self.assertFalse(screen.stop_flags(1.2, 1.0, 300, 60, 0.4, train_overhead=0.0)["stop_and_ask"])

    def test_money_stop_flag(self) -> None:
        hours = screen.projected_box_hours(3600, 60, train_overhead=0.0)
        self.assertAlmostEqual(hours, (6 * 3600 + 6 * 60) / 3600 * 1.15)                      # 7.015
        low = screen.stop_flags(1.0, 1.0, 3600, 60, 0.49, train_overhead=0.0)
        high = screen.stop_flags(1.0, 1.0, 3600, 60, 0.50, train_overhead=0.0)
        self.assertFalse(low["money_stop"])
        self.assertTrue(high["money_stop"])
        self.assertAlmostEqual(high["projected_s0_cost_usd"], hours * 0.50)
        self.assertFalse(screen.stop_flags(1.0, 1.0, 3600, 60, 0.0, train_overhead=0.0)["money_stop"])             # no rate given: cannot fire
        small = screen.stop_flags(1.0, 1.0, 300, 30, 0.46, train_overhead=0.0)
        self.assertFalse(small["money_stop"])

    def test_money_stop_counts_train_overhead(self) -> None:
        """Review round 3, item 4: each train also spends time outside T (caches, calibration, final validation,
        save). The projection adds it, and leaving it out is impossible (the keyword is required)."""
        hours = screen.projected_box_hours(3000, 60, train_overhead=300)
        self.assertAlmostEqual(hours, (6 * (3000 + 300) + 6 * 60) / 3600 * 1.15)
        without = screen.stop_flags(1.0, 1.0, 3000, 60, 0.56, train_overhead=0.0)
        with_overhead = screen.stop_flags(1.0, 1.0, 3000, 60, 0.56, train_overhead=300.0)
        self.assertFalse(without["money_stop"])                                # ~$3.28: under the $3.50 S0 cap
        self.assertTrue(with_overhead["money_stop"])                           # ~$3.61: over it
        self.assertEqual(with_overhead["train_overhead_seconds"], 300.0)
        with self.assertRaises(TypeError):
            screen.stop_flags(1.0, 1.0, 3000, 60, 0.56)                        # the overhead cannot be omitted

    def test_trim_history_keeps_the_last_five(self) -> None:
        trimmed = screen.trim_history({"history": list(range(20)), "x": 1})
        self.assertEqual(trimmed["history"], [15, 16, 17, 18, 19])
        self.assertEqual((trimmed["history_total"], trimmed["x"]), (20, 1))

    def test_manifest_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in screen.MANIFEST_FILES:
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text(name, encoding="utf-8")
            manifest = root / "m.txt"
            manifest.write_text("\n".join(screen.manifest_lines(root)) + "\n", encoding="utf-8")
            self.assertEqual(screen.check_manifest(root, manifest), [])
            (root / "premonition/swarm.py").write_text("changed", encoding="utf-8")
            self.assertEqual(len(screen.check_manifest(root, manifest)), 1)
            manifest.write_text("\n".join(screen.manifest_lines(root)[:-1]) + "\n", encoding="utf-8")
            self.assertTrue(any("not in" in p for p in screen.check_manifest(root, manifest)))


class ConstantsMatchTheLibraryTest(unittest.TestCase):
    def test_readout_constants_equal_the_library(self) -> None:
        self.assertEqual(marks.DECISION_CELLS, tuple(slices.DECISION_SLICES))
        self.assertEqual(marks.DEPTHS, tuple(slices.DEPTHS))
        self.assertEqual(marks.ALPHA, policy.ALPHA)
        self.assertEqual(marks.MARGIN, __import__("fractions").Fraction(str(policy.MIN_EFFECT)))
        self.assertEqual(marks.MIN_ITEMS, policy.MIN_ITEMS)
        self.assertEqual((marks.COLLAPSE_COS, marks.COLLAPSE_OVERLAP), (swarm.COLLAPSE_COS, swarm.COLLAPSE_OVERLAP))
        self.assertEqual(tuple(marks.LESIONS), tuple(x for x in swarm.LESIONS if x))
        self.assertEqual(marks.EXPECTED_SWARM["S0"], screen.ARMS["S0"])
        self.assertEqual(marks.EXPECTED_SWARM["S1"], screen.ARMS["S1"])
        self.assertIsNone(marks.EXPECTED_SWARM["D1"])
        self.assertEqual(screen.VOCAB_V2, pconfig.VOCAB_V2)

    def test_arms_are_the_registered_ones(self) -> None:
        self.assertEqual(screen.ARMS["D1"], {})
        self.assertEqual(screen.C0_ARMS["S0m4"], screen.ARMS["S0"])
        self.assertEqual(screen.C0_ARMS["S1m4"], screen.ARMS["S1"])
        self.assertEqual(screen.C0_ARMS["S0m2"], {"thinkers": 2})
        self.assertEqual(screen.C0_ARMS["S0m8"], {"thinkers": 8})
        self.assertEqual(list(screen.C0_ARMS), ["D1", "S0m2", "S0m4", "S0m8", "S1m4"])
        self.assertEqual(screen.CURRICULUM_WEIGHTS, {"gold": 0.05, "teacher": 0.25, "own": 0.70})
        self.assertAlmostEqual(sum(screen.CURRICULUM_WEIGHTS.values()), 1.0)

    def test_the_tokenizer_the_runner_pins_is_the_identity_one(self) -> None:
        from premonition import identity
        path, manifest = screen.tokenizer_paths()
        self.assertEqual(path, identity.V2_TOKENIZER["path"])
        self.assertEqual(manifest, "data/tokenizer/premonition-tok-v2-fallback.manifest.json")
        self.assertEqual(identity.V2_TOKENIZER["vocab_size"], 7068)


class CheckpointRefusalTest(unittest.TestCase):
    """Review round 3, item b: a rerun whose checkpoint already exists is refused BEFORE any training."""

    def test_train_refuses_before_training_when_the_checkpoint_exists(self) -> None:
        import argparse
        import premonition.train as ptrain
        called = []
        original = ptrain.train_d
        ptrain.train_d = lambda *a, **k: called.append(1) or {"status": "completed"}
        try:
            with tempfile.TemporaryDirectory() as folder:
                (Path(folder) / "ck" / "D1-s0").mkdir(parents=True)
                args = argparse.Namespace(root=folder, device="cpu", ckpt_dir="ck", arm="D1", seed=0, data_rel="d",
                                          tokenizer="t", seconds=30.0, size="tiny", max_tokens=3000, workers=1,
                                          out=str(Path(folder) / "train.json"))
                with self.assertRaises(SystemExit) as caught:
                    screen.cmd_train(args)
                self.assertIn("REFUSED before training", str(caught.exception))
                self.assertEqual(called, [])                                  # train_d never ran
                self.assertFalse((Path(folder) / "train.json").exists())
        finally:
            ptrain.train_d = original


class BoxGuardTest(unittest.TestCase):
    """Review round 3, item 2: the box refuses a dirty working tree (every mode), and the committed manifest pins
    every repo module the run imports."""

    ROOT = Path(__file__).resolve().parents[1]

    def test_manifest_covers_every_imported_repo_module(self) -> None:
        closure = screen.import_closure(self.ROOT)
        self.assertIn("learnlab/train.py", closure)
        missing = [name for name in closure if name not in screen.MANIFEST_FILES]
        self.assertEqual(missing, [], "imported by the run but not pinned")
        for name in ("learnlab/train.py", "learnlab/ckpt.py", "learnlab/tokenizer.py", "learnlab/village/world.py",
                     "premonition/pointer.py", "scripts/premonition_swarm_box.sh"):
            self.assertIn(name, screen.MANIFEST_FILES)
        self.assertEqual(screen.check_manifest(self.ROOT, self.ROOT / screen.MANIFEST_PATH), [],
                         "regenerate scripts/premonition_swarm_manifest.txt")

    def test_documented_dry_run_gets_past_every_check(self) -> None:
        """Third pass, item 1: the dry run exactly as documented (DRYRUN=1 PIN=HEAD, default OUT) passes the
        clean-tree check. The default OUT is a fresh dryrun-<sha> folder, and CHECK_ONLY stops before any step."""
        import os
        import subprocess
        status = subprocess.run(["git", "status", "--porcelain"], cwd=self.ROOT, capture_output=True, text=True).stdout
        if status.strip():
            self.skipTest("the working tree is dirty (development); this test needs a committed tree")
        pin = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.ROOT, capture_output=True, text=True).stdout.strip()
        env = {key: value for key, value in os.environ.items() if key != "OUT"}
        run = subprocess.run(["bash", str(self.ROOT / "scripts/premonition_swarm_box.sh")], cwd=self.ROOT,
                             env={**env, "DRYRUN": "1", "PIN": pin, "CHECK_ONLY": "1"},
                             capture_output=True, text=True, timeout=300)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn(f"dryrun-{pin[:9]}", run.stdout)
        self.assertIn("CHECK_ONLY: every refusal check passed", run.stdout)
        after = subprocess.run(["git", "status", "--porcelain"], cwd=self.ROOT, capture_output=True, text=True).stdout
        self.assertEqual(after.strip(), "")                                   # the check itself left the tree clean

    def test_out_holding_tracked_files_is_refused_before_writing(self) -> None:
        import os
        import subprocess
        tracked = self.ROOT / "artifacts/claude-swarm-screen-20261018/dryrun"
        listed = subprocess.run(["git", "ls-files", "--", str(tracked)], cwd=self.ROOT, capture_output=True,
                                text=True).stdout
        self.assertTrue(listed.strip())                                       # the old, committed dry-run folder
        before = (tracked / "box.log").read_bytes()
        pin = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.ROOT, capture_output=True, text=True).stdout.strip()
        run = subprocess.run(["bash", str(self.ROOT / "scripts/premonition_swarm_box.sh")], cwd=self.ROOT,
                             env={**os.environ, "DRYRUN": "1", "PIN": pin, "OUT": str(tracked), "CHECK_ONLY": "1"},
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertIn("holds git-tracked files", run.stdout)
        self.assertEqual((tracked / "box.log").read_bytes(), before)          # nothing was written into it

    def test_box_refuses_a_dirty_tree_before_anything_runs(self) -> None:
        import os
        import subprocess
        probe = self.ROOT / f"dirty-probe-{os.getpid()}.tmp"                 # untracked, so `git status` is dirty
        pin = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.ROOT, capture_output=True, text=True).stdout.strip()
        with tempfile.TemporaryDirectory(dir=self.ROOT / "artifacts") as out:   # inside the repo, git-ignored
            probe.write_text("dirty", encoding="utf-8")
            try:
                run = subprocess.run(["bash", str(self.ROOT / "scripts/premonition_swarm_box.sh")], cwd=self.ROOT,
                                     env={**os.environ, "DRYRUN": "1", "PIN": pin, "OUT": out},
                                     capture_output=True, text=True, timeout=120)
            finally:
                probe.unlink()
            self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
            self.assertIn("working tree is not clean", run.stdout)
            self.assertIn(probe.name, run.stdout)
            self.assertFalse((Path(out) / "data.json").exists())             # refused before any step ran


class FourthPassTest(unittest.TestCase):
    """Review round 3, fourth pass (ruled Oct 20): C0 benches exactly the run's trainer (1); the box refuses before
    any paid work (2) and refuses an OUT outside the repo cleanly (3)."""

    ROOT = Path(__file__).resolve().parents[1]

    def test_bench_trainer_equals_the_run_trainer_field_by_field(self) -> None:
        from dataclasses import asdict
        import argparse
        import premonition.train as ptrain
        captured = {}
        original = ptrain.train_d
        ptrain.train_d = lambda *a, **k: captured.update(k) or {"status": "completed"}
        try:
            with tempfile.TemporaryDirectory() as folder:
                args = argparse.Namespace(root=folder, device="cpu", ckpt_dir="ck", arm="S0", seed=0, data_rel="d",
                                          tokenizer="t", seconds=600.0, size="tiny", max_tokens=3000, workers=1,
                                          out=str(Path(folder) / "train.json"))
                screen.cmd_train(args)
        finally:
            ptrain.train_d = original
        settings = {k: captured[k] for k in ("flop_budget", "lr", "warmup_steps", "log_every", "eval_every")}
        self.assertEqual(settings, screen.RUN_SETTINGS)                      # what the run passes to train_d
        vocab = 64
        bench = screen.fresh_trainer(screen.ARMS["S0"], "tiny", vocab, "cpu")
        from premonition.config import MiniConfig
        from premonition.model import PremonitionMini
        model = PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=vocab, **screen.ARMS["S0"]))
        run = ptrain.d_trainer(model, "cpu", seed=captured["seed"], seconds_budget=captured["seconds_budget"],
                               **settings)                                    # what train_d builds from them
        self.assertEqual(asdict(bench.config), asdict(run.config))
        self.assertEqual(asdict(bench.curriculum), asdict(run.curriculum))
        for field in ("flop_budget", "tolerance", "seed", "device"):
            self.assertEqual(getattr(bench, field), getattr(run, field), field)
        self.assertIsNotNone(bench.seconds_budget)                            # a budget is set in both ...
        self.assertIsNotNone(run.seconds_budget)
        self.assertFalse(bench.model.train_diagnostics)                       # ... so diagnostics are off in both
        self.assertFalse(run.model.train_diagnostics)
        self.assertEqual(bench.model.config, run.model.config)

    def _box(self, **env) -> "subprocess.CompletedProcess":
        import os
        import subprocess
        pin = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.ROOT, capture_output=True, text=True).stdout.strip()
        base = {k: v for k, v in os.environ.items() if k not in ("OUT", "CKPT")}
        return subprocess.run(["bash", str(self.ROOT / "scripts/premonition_swarm_box.sh")], cwd=self.ROOT,
                              env={**base, "DRYRUN": "1", "PIN": pin, **env}, capture_output=True, text=True,
                              timeout=180)

    def test_out_outside_the_repo_is_refused_cleanly(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as outside:              # TMPDIR may sit inside the repo
            self.assertFalse(Path(outside).resolve().is_relative_to(self.ROOT))
            run = self._box(OUT=outside, CHECK_ONLY="1")
            self.assertEqual(run.returncode, 2, run.stdout + run.stderr)      # not git's exit 128
            self.assertIn("is outside the repository", run.stdout)
            self.assertEqual(list(Path(outside).iterdir()), [])               # nothing was written

    def test_out_and_ckpt_must_be_git_ignored_and_relative(self) -> None:
        run = self._box(OUT=str(self.ROOT / "premonition" / "not-ignored-out"), CHECK_ONLY="1")
        self.assertEqual(run.returncode, 2, run.stdout)
        self.assertIn("is not git-ignored", run.stdout)
        self.assertFalse((self.ROOT / "premonition" / "not-ignored-out").exists())
        with tempfile.TemporaryDirectory() as outside:
            run = self._box(CKPT=outside, CHECK_ONLY="1")
            self.assertEqual(run.returncode, 2, run.stdout)
            self.assertIn("must be a path relative to the repository", run.stdout)

    def test_existing_checkpoints_refuse_before_any_step(self) -> None:
        import subprocess
        status = subprocess.run(["git", "status", "--porcelain"], cwd=self.ROOT, capture_output=True, text=True).stdout
        if status.strip():
            self.skipTest("the working tree is dirty (development); the clean-tree refusal would fire first")
        out = self.ROOT / "artifacts" / f"swarm-rerun-test-{os.getpid() if (os := __import__('os')) else 0}"
        try:
            (out / "ckpt" / "D1-s0").mkdir(parents=True)
            (out / "ckpt" / "D1-s0" / "model.pt").write_text("x", encoding="utf-8")
            run = self._box(OUT=str(out))                                     # a real (dry) run, no CHECK_ONLY
            self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
            self.assertIn("already holds checkpoints", run.stdout)
            self.assertFalse((out / "data.json").exists())                    # refused before the data build
            self.assertFalse((out / "c0.json").exists())
        finally:
            import shutil
            shutil.rmtree(out, ignore_errors=True)


class FifthPassTest(MarksTestCase):
    """Review round 3, fifth pass (ruled Oct 20): 1 a collapsed S1 never PASSes; 5 M3 fails when no desk fetched
    anything; 4 a non-finite loss anywhere in the full history voids; 2 symlinked repo paths; 3 the archive is
    packed only at a successful end; 6 C0's probes live apart from CKPT."""

    ROOT = Path(__file__).resolve().parents[1]
    COLLAPSED = dict(HEALTHY, register_cos=0.99, fetch_overlap=0.9, collapsed=True)

    def test_collapsed_s1_never_passes_even_when_s0_is_collapsed(self) -> None:
        scenario = Scenario()
        scenario.swarm = {"S0": [dict(self.COLLAPSED) for _ in SEEDS], "S1": [dict(self.COLLAPSED) for _ in SEEDS]}
        out = self.run_card(scenario, "S1")
        self.assertEqual(next(m for m in out["marks"] if m["mark"] == "M1")["status"], "pass")
        self.assertVerdict(out, "HOLD")
        self.assertIn("COLLAPSED", out["verdict_line"])
        self.assertEqual(next(m for m in out["marks"] if m["mark"] == "M5")["status"], "fail")

    def test_m3_fails_when_every_desk_fetched_nothing(self) -> None:
        scenario = Scenario()
        scenario.swarm["S0"] = [dict(HEALTHY, fetch_count=[0.0, 0.0, 0.0, 0.0]) for _ in SEEDS]
        out = self.run_card(scenario)
        self.assertEqual(next(m for m in out["marks"] if m["mark"] == "M3")["status"], "fail")
        self.assertVerdict(out, "FAIL")

    def test_a_nonfinite_loss_anywhere_in_the_full_history_voids(self) -> None:
        scenario = Scenario()
        scenario.edits.append(("train-S0-s1.json", lambda r: r.update(nonfinite_logged_steps=[50])))
        out = self.run_card(scenario)
        self.assertVerdict(out, "VOID")
        self.assertTrue(any("non-finite" in v or "final loss" in v for v in out["void_reasons"]), out["void_reasons"])
        scenario = Scenario()
        scenario.edits.append(("train-D1-s0.json", lambda r: r.pop("nonfinite_logged_steps")))
        self.assertVerdict(self.run_card(scenario), "VOID")                   # the full-history count must exist
        history = [{"step": 50, "loss": float("nan")}] + [{"step": 100 + i, "loss": 2.0} for i in range(10)]
        self.assertEqual(screen.nonfinite_logged_steps(history), [50])        # trimming would have hidden step 50
        self.assertEqual(screen.trim_history({"history": history})["history"][0]["step"], 105)

    def _box(self, script: Path, cwd: Path, **env) -> "subprocess.CompletedProcess":
        import os
        import subprocess
        pin = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.ROOT, capture_output=True, text=True).stdout.strip()
        base = {k: v for k, v in os.environ.items() if k not in ("OUT", "CKPT")}
        return subprocess.run(["bash", str(script)], cwd=cwd, env={**base, "DRYRUN": "1", "PIN": pin, **env},
                              capture_output=True, text=True, timeout=180)

    def test_a_symlinked_repo_path_is_not_outside_the_repository(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as folder:
            link = Path(folder) / "repo"
            link.symlink_to(self.ROOT)
            run = self._box(link / "scripts/premonition_swarm_box.sh", link, CHECK_ONLY="1")
            self.assertNotIn("is outside the repository", run.stdout, run.stdout)
            self.assertIn(run.returncode, (0, 2), run.stdout + run.stderr)     # 2 only for a dirty dev tree
            if run.returncode == 2:
                self.assertIn("working tree is not clean", run.stdout)

    def test_the_archive_is_packed_only_at_a_successful_end(self) -> None:
        import shutil
        out = self.ROOT / "artifacts" / f"swarm-pack-test-{__import__('os').getpid()}"
        try:
            (out / "ckpt" / "D1-s0").mkdir(parents=True)
            (out / "ckpt" / "D1-s0" / "model.pt").write_text("x", encoding="utf-8")
            (out / "swarm-screen-out.tgz").write_bytes(b"an archive whose sha256 was logged")
            run = self._box(self.ROOT / "scripts/premonition_swarm_box.sh", self.ROOT, OUT=str(out))
            self.assertEqual(run.returncode, 2, run.stdout + run.stderr)       # a refusal (CKPT busy, or dirty tree)
            self.assertEqual((out / "swarm-screen-out.tgz").read_bytes(), b"an archive whose sha256 was logged")
            self.assertNotIn("packed ", run.stdout)
            fresh = self.ROOT / "artifacts" / f"swarm-pack-test-{__import__('os').getpid()}-fresh"
            run = self._box(self.ROOT / "scripts/premonition_swarm_box.sh", self.ROOT, OUT=str(fresh), CHECK_ONLY="1")
            self.assertFalse((fresh / "swarm-screen-out.tgz").exists())        # CHECK_ONLY / refusals never pack
        finally:
            shutil.rmtree(out, ignore_errors=True)
            shutil.rmtree(self.ROOT / "artifacts" / f"swarm-pack-test-{__import__('os').getpid()}-fresh",
                          ignore_errors=True)

    def test_c0_probes_live_apart_from_ckpt(self) -> None:
        text = (self.ROOT / "scripts/premonition_swarm_box.sh").read_text(encoding="utf-8")
        c0_line = next(line for line in text.splitlines() if line.strip().startswith("step c0 "))
        self.assertIn('--ckpt-dir "${OUT#"$ROOT"/}/c0-probe"', c0_line)
        self.assertNotIn('--ckpt-dir "$CKPT"', c0_line)
        self.assertLess(text.index('rm -rf "$OUT/c0-probe"'), text.index(c0_line))   # cleared before C0 starts
        self.assertIn("--exclude=./c0-probe", text)                            # and never packed



class SixthPassReadoutTest(MarksTestCase):
    """Review round 3, sixth pass (the complete sweep, ruled Oct 20), readout items 4, 13, 14 and 21."""

    def test_an_unregistered_T_voids_the_readout(self) -> None:
        # Item 4: a T that is not the registered formula's (an override, or a T that differs from T_formula) is VOID.
        for patch in ({"t_override": 300.0}, {"T_formula": 600}):
            scenario = Scenario()
            scenario.edits.append(("c0.json", lambda c, patch=patch: c.update(patch)))
            result = self.run_card(scenario)
            self.assertVerdict(result, "VOID")
            self.assertTrue(any("registered formula" in r for r in result["void_reasons"]), result["void_reasons"])
        self.assertVerdict(self.run_card(Scenario()), "PROMOTE")                     # the registered T reads clean

    def test_tiny_runs_and_non_primary_evals_void_the_real_card(self) -> None:
        # Item 4: the real card reads only full-size trains and primary label-free evals; the dry run says so.
        scenario = Scenario()
        scenario.edits.append(("train-S0-s1.json", lambda r: r.update(size="tiny")))
        scenario.edits.append(("eval-D1-s2.json", lambda r: r.update(identity={"primary": False, "regime": "label-free"})))
        result = self.run_card(scenario)
        self.assertVerdict(result, "VOID")
        reasons = " ".join(result["void_reasons"])
        self.assertIn("train-S0-s1 size 'tiny'", reasons)
        self.assertIn("eval-D1-s2.json is not a primary label-free report", reasons)
        self.assertVerdict(self.run_card(scenario, dry_run=True), "PROMOTE")         # the dry run accepts them

    def test_item_sets_that_differ_across_seeds_are_void(self) -> None:
        # Item 13: each seed is internally consistent, but seed 1 scored one far item fewer. Pooling must not
        # silently intersect: VOID.
        scenario = Scenario()

        def drop(report: dict) -> None:
            report["items"]["validation"] = [i for i in report["items"]["validation"] if i["id"] != "far0"]
            refresh(report)
        for arm in ("D1", "S0"):
            scenario.edits.append((f"eval-{arm}-s1.json", drop))
        result = self.run_card(scenario)
        self.assertVerdict(result, "VOID")
        self.assertTrue(any("item sets differ across seeds" in r for r in result["void_reasons"]),
                        result["void_reasons"])

    def test_per_desk_lists_must_have_one_finite_number_per_desk(self) -> None:
        # Item 14: an empty list, a short list (3 entries for 4 desks), a NaN and a string are schema problems.
        for key, bad in (("fetch_count", []), ("ask_rate", [0.5, 0.5, 0.5]), ("fetch_count", [1.0, 2.0, float("nan"), 1.0]),
                         ("ask_rate", "0.5")):
            scenario = Scenario()
            scenario.swarm["S0"][0] = {**HEALTHY, key: bad}
            result = self.run_card(scenario)
            self.assertVerdict(result, "VOID")
            self.assertTrue(any(f"swarm.{key} must list 4 finite numbers" in r for r in result["void_reasons"]),
                            (key, bad, result["void_reasons"]))

    def test_s1_computes_each_arms_diversity_rows_once(self) -> None:
        # Item 21: s1_card reuses the rows M5 / M5b already computed, instead of a second pass that re-appended the
        # same VOID reasons (hidden only by the final de-duplication).
        calls = []
        original = marks.diversity_rows
        marks.diversity_rows = lambda ctx, arm: calls.append(arm) or original(ctx, arm)
        try:
            scenario = Scenario()
            scenario.edits.append(("eval-S0-s1.json", lambda r: r["directories"]["validation"].update(retrieval={})))
            result = self.run_card(scenario, card="S1")
        finally:
            marks.diversity_rows = original
        self.assertEqual(sorted(calls), ["S0", "S1"])
        self.assertVerdict(result, "VOID")
        self.assertEqual(len(result["void_reasons"]), len(set(result["void_reasons"])))


class SixthPassRunnerTest(unittest.TestCase):
    """Review round 3, sixth pass, runner items 1, 4, 12, 17 and 19."""

    def test_t_raw_is_the_time_share_formula(self) -> None:
        # Item 17, as corrected by the eighth pass (item 4, coordinator ruling Oct 20): a seconds-budget run splits
        # its phases by TIME, so T_raw = F / sum_m w_m (f_m / s_m), and D1 trained for T_raw spends exactly F.
        seconds = {"gold": 1.0, "teacher": 2.0, "own": 4.0}
        flops = {"gold": 1e12, "teacher": 1e12, "own": 4e12}
        want = screen.F_TARGET / (0.05 * 1e12 / 1.0 + 0.25 * 1e12 / 2.0 + 0.70 * 4e12 / 4.0)
        got = screen.t_raw_from_modes(seconds, flops)
        self.assertAlmostEqual(got, want, delta=want * 1e-12)
        spent = sum(screen.CURRICULUM_WEIGHTS[m] * got * flops[m] / seconds[m] for m in screen.MODES)
        self.assertAlmostEqual(spent, screen.F_TARGET, delta=screen.F_TARGET * 1e-12)   # T means "F FLOPs"
        flop_share = screen.F_TARGET * sum(screen.CURRICULUM_WEIGHTS[m] * seconds[m] / flops[m] for m in screen.MODES)
        self.assertGreater(abs(flop_share - want) / want, 0.05)                       # the sixth pass's rule differs
        old = screen.F_TARGET / (screen.weighted(flops) / screen.weighted(seconds))     # the old update-share rule
        self.assertGreater(abs(old - want) / want, 0.05)                              # they really differ here
        with self.assertRaises(ValueError):
            screen.t_raw_from_modes({**seconds, "own": 0.0}, flops)

    def test_c0_refuses_a_t_override_off_the_tiny_preset(self) -> None:
        # Item 4: an unregistered T is refused before any work, not only detected later.
        import contextlib
        import io
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = screen.main(["c0", "--data-rel", "nowhere", "--tokenizer", "nowhere", "--out", "unused.json",
                              "--size", "full", "--device", "cpu", "--t-override", "300"])
        self.assertEqual(rc, 2)                                                    # eighth pass, item 9: "refused"
        self.assertIn("REFUSED: c0: --t-override is for the tiny CPU dry run only", err.getvalue())

    def test_the_c0_bench_trips_the_run_trainers_memory_guard(self) -> None:
        # Item 1: time_run checks the run trainer's memory guard after each timed chunk, so an arm that S0 would
        # abort on cannot set a T.
        import premonition.train as ptrain
        from learnlab.train import MemoryGuardError
        from tests.test_premonition_model import VOCAB, synthetic_batch
        batches = [synthetic_batch(seed=k) for k in range(3)]
        checks = []

        def guard(trainer) -> None:
            checks.append(1)
            raise MemoryGuardError("over the limit", 15, 14)
        original = ptrain.MiniTrainer._check_memory
        ptrain.MiniTrainer._check_memory = guard
        try:
            with self.assertRaises(MemoryGuardError):
                screen.time_run({}, "teacher", batches, size="tiny", vocab=VOCAB, device="cpu", warmup=1, timed=2,
                                chunk=1)
        finally:
            ptrain.MiniTrainer._check_memory = original
        self.assertEqual(checks, [1])

    def test_an_aborted_overhead_probe_stops_c0(self) -> None:
        # Item 1: a probe that did not complete (e.g. the memory guard) stops C0 instead of reporting an overhead.
        import premonition.train as ptrain
        original = ptrain.train_d
        ptrain.train_d = lambda *a, **k: {"status": "memory_guard", "error": "over the limit", "train_seconds": 1.0}
        try:
            with tempfile.TemporaryDirectory() as root:
                budget = type("B", (), {"root": root})()
                with self.assertRaises(SystemExit) as caught:
                    screen.measure_train_overhead(budget, "d", "t", size="tiny", device="cpu", workers=1,
                                                  ckpt_dir="ck", seconds=1.0, max_tokens=10)
        finally:
            ptrain.train_d = original
        self.assertIn("did not complete", str(caught.exception))
        self.assertEqual(caught.exception.code, screen.C0_STOP)                    # a C0 stop, exit 3 (item 9)

    def test_the_runners_default_checkpoint_folder_is_git_ignored(self) -> None:
        # Item 12: a manual `train` run with the default --ckpt-dir must not dirty the tree.
        import subprocess
        args = screen.build_parser().parse_args(["train", "--arm", "D1", "--seed", "0", "--seconds", "1",
                                                 "--data-rel", "d", "--tokenizer", "t", "--out", "o.json"])
        self.assertEqual(args.ckpt_dir, screen.CKPT_DIR)
        ignored = subprocess.run(["git", "check-ignore", "-q", "--no-index", f"{screen.CKPT_DIR}/D1-s0/model.pt"],
                                 cwd=ROOT)
        self.assertEqual(ignored.returncode, 0, screen.CKPT_DIR)

    def test_importing_the_runner_leaves_the_test_environment_alone(self) -> None:
        # Item 19: the runner's import-time cache and temp variables are restored for the rest of the test process.
        # (Not a whole-environment comparison: torch's inductor sets TORCHINDUCTOR_CACHE_DIR itself when used.)
        for name in ("TMPDIR", "TMP", "TEMP", "TORCH_HOME", "XDG_CACHE_HOME", "HF_HOME", "TORCHDYNAMO_DISABLE",
                     "TORCH_COMPILE_DISABLE", "CUDA_CACHE_DISABLE"):
            self.assertEqual(os.environ.get(name), _ENV_BEFORE.get(name), name)
        self.assertNotEqual(os.environ.get("TMPDIR"), str(ROOT / ".runtime" / "tmp"))


# A stand-in runner and readout for the box script: the REAL premonition_swarm_box.sh runs in a throwaway git repo
# (clean tree, its own manifest), so every refusal and exit path is reachable on a CPU host in seconds.
FAKE_SCREEN = r"""
import json, os, sys
from pathlib import Path
argv = sys.argv[1:]
cmd = argv[0]
opts = {argv[i][2:]: argv[i + 1] for i in range(1, len(argv) - 1) if argv[i].startswith("--")}
if cmd == os.environ.get("FAKE_FAIL"):
    print(f"fake {cmd} failed"); sys.exit(int(os.environ.get("FAKE_RC") or 1))
if cmd == "manifest":
    print("manifest OK"); sys.exit(0)
out = Path(opts["out"])
if cmd == "data":
    out.write_text(json.dumps({"data_rel": "data/fake", "tokenizer_path": "tok/fake.json"}))
elif cmd == "c0":
    Path(opts["ckpt-dir"]).mkdir(parents=True, exist_ok=True)
    (Path(opts["ckpt-dir"]) / "probe.pt").write_text("probe")
    T = int(float(opts.get("t-override") or 600))
    c0 = {"T": T, "T_formula": 600, "t_override": opts.get("t-override"), "stop_and_ask": False, "money_stop": False,
          "ratio_s0m4_over_d1": 1.2,
          "flags": {"ratio": 1.2, "stop_ratio": 2.5, "T": T, "eval_seconds_estimate": 60,
                    "train_overhead_seconds": 30, "projected_s0_box_hours": 1.5, "dph": 0.46,
                    "projected_s0_cost_usd": 0.69, "money_cap_usd": 3.5}}
    patch = json.loads(os.environ.get("FAKE_C0") or "{}")
    c0.update({k: v for k, v in patch.items() if k != "flags"}); c0["flags"].update(patch.get("flags", {}))
    out.write_text(json.dumps(c0))
elif cmd == "train":
    folder = Path(opts["ckpt-dir"]) / f"{opts['arm']}-s{opts['seed']}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "model.pt").write_text("weights")
    out.write_text(json.dumps({"status": "completed"}))
elif cmd == "eval":
    out.write_text(json.dumps({"lesion": opts.get("lesion")}))
"""
FAKE_MARKS = r"""
import sys
from pathlib import Path
argv = sys.argv[1:]
out = Path(argv[argv.index("--out") + 1])
out.write_text("{}")
out.with_suffix(".md").write_text("VERDICT: HOLD (fake readout)\n")
"""
FAKE_PY = """#!/usr/bin/env bash
# the box's CUDA probe answers FAKE_CUDA (default yes); everything else is the real python
case "$*" in *torch.cuda.is_available*) exit "${FAKE_CUDA:-0}";; esac
exec "%s" "$@"
"""


class BoxRepoCase(unittest.TestCase):
    """The harness: the real box script in a throwaway clean git repo with the stand-in runner and readout."""

    ROOT = Path(__file__).resolve().parents[1]

    def setUp(self) -> None:
        import shutil
        import subprocess
        self._tmp = tempfile.TemporaryDirectory(dir="/tmp")
        self.repo = Path(self._tmp.name).resolve() / "repo"
        (self.repo / "scripts").mkdir(parents=True)
        shutil.copy(self.ROOT / "scripts/premonition_swarm_box.sh", self.repo / "scripts/premonition_swarm_box.sh")
        (self.repo / "scripts/premonition_swarm_screen.py").write_text(FAKE_SCREEN, encoding="utf-8")
        (self.repo / "scripts/premonition_swarm_marks.py").write_text(FAKE_MARKS, encoding="utf-8")
        (self.repo / ".gitignore").write_text("artifacts/\n", encoding="utf-8")
        self.py = Path(self._tmp.name) / "fakepy"
        self.py.write_text(FAKE_PY % sys.executable, encoding="utf-8")
        self.py.chmod(0o755)
        git = lambda *a: subprocess.run(["git", *a], cwd=self.repo, check=True, capture_output=True, text=True)
        self.git = git
        git("init", "-q")
        git("config", "user.email", "t@t"), git("config", "user.name", "t")
        names = ["scripts/premonition_swarm_box.sh", "scripts/premonition_swarm_screen.py",
                 "scripts/premonition_swarm_marks.py"]
        lines = subprocess.run(["sha256sum", *names], cwd=self.repo, capture_output=True, text=True, check=True).stdout
        (self.repo / "scripts/premonition_swarm_manifest.txt").write_text(lines, encoding="utf-8")
        git("add", "-A")
        git("commit", "-qm", "fake")
        self.pin = git("rev-parse", "HEAD").stdout.strip()
        self.run_dir = self.repo / "artifacts" / "claude-swarm-screen-20261018"
        self.ledger = self.run_dir / "money-ledger.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def box(self, **env) -> "subprocess.CompletedProcess":
        import subprocess
        base = {k: v for k, v in os.environ.items()
                if k not in ("OUT", "CKPT", "DRYRUN", "DPH", "CAP", "MAXH", "PART", "FROM", "CHECK_ONLY",
                             "STOP_OVERRIDE", "BOX_START", "C0_EXTRA")}
        if env.get("DRYRUN") != "1" and "BOX_START" not in env:
            import time
            env["BOX_START"] = int(time.time()) - 60                 # the billing start is required (eighth pass, 3)
        env = {**base, "PIN": self.pin, "PY": str(self.py), **{k: str(v) for k, v in env.items()}}
        return subprocess.run(["bash", str(self.repo / "scripts/premonition_swarm_box.sh")], cwd=self.repo, env=env,
                              capture_output=True, text=True, timeout=300)

    def out(self, name: str) -> Path:
        return self.run_dir / name

    def write_ledger(self, box_start: int, dph: str = "0.46", cap: str = "4.20") -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.ledger.write_text(json.dumps({"box_start": box_start, "dph": dph, "cap": cap, "first_out": "x"}))

    def c0_folder(self, name: str, *, gpu: str = "none", **c0) -> Path:
        folder = self.out(name)
        folder.mkdir(parents=True)
        (folder / "data.json").write_text(json.dumps({"data_rel": "data/fake", "tokenizer_path": "tok/fake.json"}))
        base = {"T": 600, "T_formula": 600, "t_override": None, "stop_and_ask": False, "money_stop": False,
                "ratio_s0m4_over_d1": 1.2,
                "flags": {"ratio": 1.2, "stop_ratio": 2.5, "T": 600, "eval_seconds_estimate": 60,
                          "train_overhead_seconds": 30, "projected_s0_box_hours": 1.5, "dph": 0.46,
                          "projected_s0_cost_usd": 0.69, "money_cap_usd": 3.5}}
        base.update(c0)
        (folder / "c0.json").write_text(json.dumps(base))
        (folder / "host-c0.txt").write_text(f"gpu: {gpu}\n")
        return folder



class SixthPassBoxTest(BoxRepoCase):
    """Review round 3, sixth pass, box items 2-11, on the real box script in a throwaway clean repo."""

    # ------------------------------------------------------------------ the whole flow, and the archive (10, 11)
    def test_a_full_run_packs_without_the_actual_ckpt_and_keeps_both_host_records(self) -> None:
        import tarfile
        out = self.out("full")
        run = self.box(DPH="0.46", OUT=out, CKPT="artifacts/claude-swarm-screen-20261018/full/my-ckpt")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertTrue((out / "my-ckpt" / "D1-s0" / "model.pt").exists())
        with tarfile.open(out / "swarm-screen-out.tgz") as archive:
            names = archive.getnames()
        self.assertIn("./MARKS-S0.md", names)
        self.assertFalse([n for n in names if "my-ckpt" in n or "c0-probe" in n or n.endswith(".tgz")], names)
        self.assertIn("./host-c0.txt", names)
        self.assertIn("./host-s0.txt", names)
        self.assertTrue(self.ledger.exists())

    # ------------------------------------------------------------------ money (2, 3, 5)
    def test_the_bid_hours_at_this_dph_must_fit_the_total_cap(self) -> None:
        run = self.box(DPH="0.50", OUT=self.out("o"))                       # 8.5 h x 0.50 = 4.25 > 4.20
        self.assertEqual(run.returncode, 2, run.stdout)
        self.assertIn("A revised bid with the new total is needed", run.stdout)
        self.assertFalse(self.ledger.exists())

    def test_money_inputs_must_be_positive_decimals(self) -> None:
        for env, word in (({"DPH": "abc"}, "DPH"), ({"DPH": "0.46", "MAXH": "2h"}, "MAXH"),
                          ({"DPH": "0.46", "CAP": "-1"}, "CAP"), ({"DPH": "0"}, "DPH")):
            run = self.box(OUT=self.out("o"), **env)
            self.assertEqual(run.returncode, 2, (env, run.stdout))
            self.assertIn(word, run.stdout.split("REFUSED")[-1], env)

    def test_the_total_persists_across_invocations_and_fresh_outs(self) -> None:
        import time
        self.write_ledger(int(time.time()) - int(9.2 * 3600))                 # 9.2 h x 0.46 = 4.23: nothing left
        run = self.box(DPH="0.46", OUT=self.out("fresh-out"))
        self.assertEqual(run.returncode, 2, run.stdout)
        self.assertIn("no money is left", run.stdout)
        self.assertFalse(self.out("fresh-out").joinpath("data.json").exists())
        self.write_ledger(int(time.time()) - 3600, dph="0.40")               # a different rate than the ledger's
        run = self.box(DPH="0.46", OUT=self.out("fresh-out-2"))
        self.assertEqual(run.returncode, 2, run.stdout)
        self.assertIn("differ from the box ledger", run.stdout)

    def test_the_first_invocation_starts_the_ledger_and_later_ones_reuse_it(self) -> None:
        import time
        start = int(time.time()) - 600
        run = self.box(DPH="0.46", OUT=self.out("a"), PART="c0", BOX_START=start)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(self.ledger.read_text())["box_start"], start)
        run = self.box(DPH="0.46", OUT=self.out("b"), PART="c0", BOX_START=start + 500)   # ignored: the ledger rules
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn(f"box billing since {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(start))}", run.stdout)

    def test_a_projected_s0_beyond_the_money_left_stops_and_cannot_be_overridden(self) -> None:
        import time
        self.write_ledger(int(time.time()) - 8 * 3600)                        # 9.13 h of money, 1.13 h left
        run = self.box(DPH="0.46", OUT=self.out("o"), STOP_OVERRIDE="coordinator says go",
                       FAKE_C0=json.dumps({"flags": {"projected_s0_box_hours": 7.5}}))
        self.assertEqual(run.returncode, 3, run.stdout)
        self.assertIn("a revised bid is needed", run.stdout)
        self.assertFalse(list(self.out("o").glob("train-*.json")))

    # ------------------------------------------------------------------ an unregistered T is refused (4)
    def test_an_unregistered_t_is_refused(self) -> None:
        run = self.box(DPH="0.46", OUT=self.out("o"), C0_EXTRA="--t-override 300")
        self.assertEqual(run.returncode, 2, run.stdout)
        self.assertIn("may not set --t-override", run.stdout)
        run = self.box(DPH="0.46", OUT=self.out("p"), FAKE_C0=json.dumps({"T": 900}))   # T != T_formula
        self.assertEqual(run.returncode, 2, run.stdout)
        self.assertIn("is not the registered formula", run.stdout)
        self.assertFalse(list(self.out("p").glob("train-*.json")))

    # ------------------------------------------------------------------ robustness (6-11)
    def test_a_failed_step_exits_5_and_packs_nothing(self) -> None:
        run = self.box(DRYRUN="1", OUT=self.out("o"), FAKE_FAIL="c0")
        self.assertEqual(run.returncode, 5, run.stdout + run.stderr)
        self.assertIn("STEP c0 FAILED", run.stdout)
        self.assertFalse(self.out("o").joinpath("swarm-screen-out.tgz").exists())
        self.assertFalse(list(self.out("o").glob("train-*.json")))

    def test_an_out_with_many_tracked_files_is_refused_not_141(self) -> None:
        big = self.out("big")
        big.mkdir(parents=True)
        for k in range(3000):
            (big / f"tracked-file-with-a-long-name-so-the-list-overflows-a-pipe-{k:05d}.txt").write_text("x")
        self.git("add", "-f", str(big))
        self.git("commit", "-qm", "tracked under artifacts")
        self.pin = self.git("rev-parse", "HEAD").stdout.strip()
        run = self.box(DRYRUN="1", OUT=big, CHECK_ONLY="1")
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertIn("holds git-tracked files", run.stdout)

    def test_one_run_per_out(self) -> None:
        used = self.out("used")
        used.mkdir(parents=True)
        (used / "box.log").write_text("an earlier refusal's log only")
        run = self.box(DRYRUN="1", OUT=used, CHECK_ONLY="1")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)           # a log alone is not a result
        for name in ("train-D1-s0.json", "eval-S0-s2.json", "MARKS-S0.md", "swarm-screen-out.tgz"):
            folder = self.out(f"with-{name}")
            folder.mkdir(parents=True)
            (folder / name).write_text("{}")
            run = self.box(DRYRUN="1", OUT=folder, CHECK_ONLY="1")
            self.assertEqual(run.returncode, 2, (name, run.stdout))
            self.assertIn("already holds results", run.stdout)

    def test_check_only_covers_part_s0s_inputs_host_and_gate(self) -> None:
        run = self.box(DRYRUN="1", OUT=self.out("empty"), PART="s0", CHECK_ONLY="1")
        self.assertEqual(run.returncode, 2, run.stdout)
        self.assertIn("PART=s0 needs data.json", run.stdout)
        other = self.c0_folder("other-gpu", gpu="Tesla T4, GPU-1234")
        run = self.box(DRYRUN="1", OUT=self.out("o1"), PART="s0", FROM=other, CHECK_ONLY="1")
        self.assertEqual(run.returncode, 2, run.stdout)
        self.assertIn("is not the one C0 measured T on", run.stdout)
        stop = self.c0_folder("stop", stop_and_ask=True)
        run = self.box(DRYRUN="1", OUT=self.out("o2"), PART="s0", FROM=stop, CHECK_ONLY="1")
        self.assertEqual(run.returncode, 3, run.stdout)
        unregistered = self.c0_folder("unregistered", T=900)
        run = self.box(DPH="0.46", OUT=self.out("o3"), PART="s0", FROM=unregistered, CHECK_ONLY="1")
        self.assertEqual(run.returncode, 2, run.stdout)
        self.assertIn("is not the registered formula", run.stdout)
        good = self.c0_folder("good")
        run = self.box(DRYRUN="1", OUT=self.out("o4"), PART="s0", FROM=good, CHECK_ONLY="1")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertFalse(self.out("o4").joinpath("c0.json").exists())          # CHECK_ONLY copies nothing

    def test_part_s0_from_an_earlier_out_copies_its_c0_and_trains(self) -> None:
        good = self.c0_folder("first")
        run = self.box(DPH="0.46", OUT=self.out("rerun"), PART="s0", FROM=good)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(self.out("rerun").joinpath("c0.json").read_text(), good.joinpath("c0.json").read_text())
        self.assertIn("FROM: copied c0.json", run.stdout)
        self.assertTrue(self.out("rerun").joinpath("train-S0-s2.json").exists())
        missing = self.out("no-c0")
        missing.mkdir(parents=True)
        run = self.box(DPH="0.46", OUT=self.out("rerun-2"), PART="s0", FROM=missing)
        self.assertEqual(run.returncode, 2, run.stdout)
        self.assertIn("has no data.json", run.stdout)



class EighthPassBoxTest(BoxRepoCase):
    """Review round 3, eighth pass, box items 1, 3, 8 and 9 (same throwaway-repo harness)."""

    def ledger_stops(self) -> list:
        return json.loads(self.ledger.read_text()).get("c0_stops") or []

    def test_a_c0_stop_cannot_be_rerun_away(self) -> None:
        # Item 1: run 1 stops at C0. Rerunning the same OUT is refused (it holds the stopping c0.json); a fresh OUT
        # is refused too (the ledger holds the stop) unless the coordinator's STOP_OVERRIDE is given.
        stop = json.dumps({"stop_and_ask": True})
        first = self.box(DPH="0.46", OUT=self.out("o"), FAKE_C0=stop)
        self.assertEqual(first.returncode, 3, first.stdout)
        self.assertEqual(len(self.ledger_stops()), 1)
        stopping = self.out("o").joinpath("c0.json").read_text()
        again = self.box(DPH="0.46", OUT=self.out("o"))
        self.assertEqual(again.returncode, 2, again.stdout)
        self.assertIn("already holds results (for example data.json)", again.stdout)
        self.assertEqual(self.out("o").joinpath("c0.json").read_text(), stopping)       # never overwritten
        fresh = self.box(DPH="0.46", OUT=self.out("fresh"))
        self.assertEqual(fresh.returncode, 2, fresh.stdout)
        self.assertIn("an earlier C0 on this box stopped", fresh.stdout)
        self.assertFalse(self.out("fresh").joinpath("c0.json").exists())
        ruled = self.box(DPH="0.46", OUT=self.out("ruled"), STOP_OVERRIDE="coordinator: re-measure once")
        self.assertEqual(ruled.returncode, 0, ruled.stdout + ruled.stderr)
        self.assertIn("STOP_OVERRIDE given", ruled.stdout)

    def test_the_runners_c0_stop_is_a_stop_not_a_crash(self) -> None:
        # Item 9: C0 exits 3 (D1 or S0m4 cannot run); the box exits 3 with STOP-AND-ASK.txt and a ledger record.
        run = self.box(DPH="0.46", OUT=self.out("o"), FAKE_FAIL="c0", FAKE_RC="3")
        self.assertEqual(run.returncode, 3, run.stdout)
        self.assertTrue(self.out("o").joinpath("STOP-AND-ASK.txt").exists())
        self.assertEqual([s["reason"] for s in self.ledger_stops()], ["c0 could not set T"])
        self.assertFalse(list(self.out("o").glob("train-*.json")))

    def test_the_billing_start_is_required_and_fixed_from_the_first_check(self) -> None:
        # Item 3: no default BOX_START (setup time would be left out); a future one is refused; CHECK_ONLY already
        # fixes it in the ledger, so a later run counts the setup and the checks.
        import time
        run = self.box(DPH="0.46", OUT=self.out("o"), BOX_START="")
        self.assertEqual(run.returncode, 2, run.stdout)
        self.assertIn("BOX_START", run.stdout.split("REFUSED")[-1])
        self.assertFalse(self.ledger.exists())
        run = self.box(DPH="0.46", OUT=self.out("o"), BOX_START=int(time.time()) + 3600)
        self.assertEqual(run.returncode, 2, run.stdout)
        self.assertIn("in the future", run.stdout)
        start = int(time.time()) - 2700                                     # 45 minutes of setup
        run = self.box(DPH="0.46", OUT=self.out("o"), BOX_START=start, CHECK_ONLY="1")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(self.ledger.read_text())["box_start"], start)
        later = self.box(DPH="0.46", OUT=self.out("p"), PART="c0", BOX_START=int(time.time()))
        self.assertEqual(later.returncode, 0, later.stdout + later.stderr)
        self.assertIn(f"box billing since {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(start))}", later.stdout)

    def test_from_is_only_for_part_s0(self) -> None:
        # Item 8: with PART=all or c0, data and C0 would overwrite FROM's files while the log claimed a reuse.
        good = self.c0_folder("first")
        for part in ("all", "c0"):
            run = self.box(DPH="0.46", OUT=self.out(f"o-{part}"), PART=part, FROM=good)
            self.assertEqual(run.returncode, 2, run.stdout)
            self.assertIn("FROM is only for PART=s0", run.stdout)


class EighthPassRunnerTest(unittest.TestCase):
    """Review round 3, eighth pass, runner / readout / docs items 6, 7, 9, 12 and 13."""

    @staticmethod
    def _result() -> dict:
        return {"round_value": 1.0, "chunks": [1.0], "peak_allocated_bytes": None}

    def test_a_failed_required_arm_stops_c0_at_once(self) -> None:
        # Item 7: S0m4 trips the memory guard in round 1: C0 stops there (exit 3), no further billed benching.
        from learnlab.train import MemoryGuardError
        calls = []

        def run_one(config, mode):
            arm = next(name for name, c in screen.C0_ARMS.items() if c is config)
            calls.append((arm, mode))
            if arm == "S0m4":
                raise MemoryGuardError("over", 15, 14)
            return self._result()
        with self.assertRaises(screen.Stop) as caught:
            screen.bench(run_one, rounds=3, device="cpu", log=lambda m: None)
        self.assertEqual(caught.exception.code, screen.C0_STOP)
        self.assertIn("S0m4 could not run", str(caught.exception))
        self.assertEqual(calls[-1], ("S0m4", "gold"))
        self.assertNotIn("S0m8", {arm for arm, _ in calls})

    def test_an_optional_arm_fails_alone_and_the_cache_is_freed_after_the_handler(self) -> None:
        # Items 6 and 7: S0m8 fails and is skipped from then on; the others finish all rounds. The arm's tensors
        # (held by the traceback inside the except block) are already gone when the cache is emptied.
        import weakref
        from learnlab.train import MemoryGuardError

        class Activations:
            pass
        refs, alive_at_collect = [], []

        def run_one(config, mode):
            if config is screen.C0_ARMS["S0m8"]:
                held = Activations()
                refs.append(weakref.ref(held))
                raise MemoryGuardError("over", 15, 14)
            return self._result()
        original = screen.gc.collect
        screen.gc.collect = lambda *a: alive_at_collect.append(any(r() is not None for r in refs)) or original(*a)
        try:
            runs, failed = screen.bench(run_one, rounds=2, device="cpu", log=lambda m: None)
        finally:
            screen.gc.collect = original
        self.assertEqual(list(failed), ["S0m8"])
        self.assertEqual(alive_at_collect, [False])
        self.assertEqual(len(runs["D1"]["own"]), 2)
        self.assertEqual(runs["S0m8"]["gold"], [])

    def test_runner_refusals_exit_2(self) -> None:
        # Item 9: a refusal exits 2 ("refused"), not Python's 1 for SystemExit(str).
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "ck" / "D1-s0").mkdir(parents=True)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc = screen.main(["train", "--arm", "D1", "--seed", "0", "--seconds", "30", "--data-rel", "d",
                                  "--tokenizer", "t", "--out", str(Path(folder) / "t.json"), "--root", folder,
                                  "--ckpt-dir", "ck", "--device", "cpu", "--size", "tiny"])
        self.assertEqual(rc, screen.REFUSED)
        self.assertIn("REFUSED before training", err.getvalue())

    def test_s1_m5_status_is_set_in_one_place(self) -> None:
        # Item 12 (no behaviour change): the dead re-assignment is gone; a collapsed S1 still never passes.
        import inspect
        self.assertNotIn('m5["status"] =', inspect.getsource(marks.s1_card))
        scenario = Scenario()
        collapsed = dict(HEALTHY, register_cos=0.99, fetch_overlap=0.9, collapsed=True)
        scenario.swarm["S1"] = [dict(collapsed) for _ in SEEDS]
        result = MarksTestCase.run_card(self, scenario, card="S1")
        m5 = next(m for m in result["marks"] if m["mark"] == "M5")
        self.assertEqual(m5["status"], "fail")
        self.assertNotEqual(result["verdict"], "PASS")

    def test_the_design_docs_match_the_code(self) -> None:
        # Item 13: the docs no longer say the subclasses compose with the swarm, or that matched wall-clock uses
        # max_seconds; the ledger is described where it lives.
        design = (ROOT / "design/swarm/SWARM-DESIGN.md").read_text(encoding="utf-8")
        spec = (ROOT / "design/swarm/IMPLEMENTATION-SPEC.md").read_text(encoding="utf-8")
        box = (ROOT / "design/swarm/BOX-SPEC.md").read_text(encoding="utf-8")
        self.assertNotIn("compose with it (not exercised at size)", design)
        self.assertNotIn("`MiniTrainer.train(max_seconds=…)`, with", design)
        self.assertNotIn("`direct_reader.py`) compose.", spec)
        self.assertIn("one level\n  above OUT", box)
        self.assertNotIn('The ruling said "persisted under OUT"', box)

if __name__ == "__main__":
    unittest.main()
