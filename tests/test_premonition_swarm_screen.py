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
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import premonition_swarm_screen as screen                        # noqa: E402  (bootstraps before torch)
import premonition_swarm_marks as marks                          # noqa: E402

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
            "history": [{"step": 50, "loss": 2.4}, {"step": 100, "loss": 2.3}], "parameters": 1,
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

        write("c0.json", {"T": T, "tag": "tag-1", "tokenizer_sha256": "sha-1"})
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
    def test_promote_and_every_mark_is_computed(self) -> None:
        result = self.run_card(Scenario())
        self.assertVerdict(result, "PROMOTE")
        self.assertEqual({m["mark"] for m in result["marks"]}, {"M1", "M2", "M3", "M4", "M5", "M6", "KILL"})
        self.assertTrue(all(result["marks_computed"].values()))
        m1 = next(m for m in result["marks"] if m["mark"] == "M1")
        self.assertEqual(m1["status"], "pass")
        self.assertAlmostEqual(m1["detail"]["delta_points"], 100 * 15 / FAR_N)       # 12.5 points
        self.assertEqual(m1["detail"]["n_pooled"], 3 * FAR_N)
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
        self.assertFalse(screen.stop_flags(2.5, 1.0, 300, 60, 0.4)["stop_and_ask"])          # exactly 2.5: no
        self.assertTrue(screen.stop_flags(2.5001, 1.0, 300, 60, 0.4)["stop_and_ask"])
        self.assertFalse(screen.stop_flags(1.2, 1.0, 300, 60, 0.4)["stop_and_ask"])

    def test_money_stop_flag(self) -> None:
        hours = screen.projected_box_hours(3600, 60)
        self.assertAlmostEqual(hours, (6 * 3600 + 6 * 60) / 3600 * 1.15)                      # 7.015
        low, high = screen.stop_flags(1.0, 1.0, 3600, 60, 0.49), screen.stop_flags(1.0, 1.0, 3600, 60, 0.50)
        self.assertFalse(low["money_stop"])
        self.assertTrue(high["money_stop"])
        self.assertAlmostEqual(high["projected_s0_cost_usd"], hours * 0.50)
        self.assertFalse(screen.stop_flags(1.0, 1.0, 3600, 60, 0.0)["money_stop"])             # no rate given: cannot fire
        small = screen.stop_flags(1.0, 1.0, 300, 30, 0.46)
        self.assertFalse(small["money_stop"])

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


if __name__ == "__main__":
    unittest.main()
