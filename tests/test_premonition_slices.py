"""Experiment 1 slice tags, read-only evaluation and the §6 decision rules (design/06; CPU, fast).

Fake-village fixtures come from tests/test_learnlab_step1.py; the changed-fact replay and the
far-long generator use the real simulator on a handful of visits.
"""
from __future__ import annotations

from dataclasses import asdict
import functools
import json
from pathlib import Path
import tempfile
import unittest

import torch

from learnlab import step1
from learnlab.ckpt import save_checkpoint
from learnlab.core import Core, CoreConfig
from learnlab.metrics import mcnemar_greater
from learnlab.readonly import ReadOnlyViolation
from memorylab.storage import Budget
from premonition import exp1, preprocess, slices
from tests.test_learnlab_step1 import NAMES, Workspace, repeat_shard, tiny_tokenizer

QUIET = lambda _message: None  # noqa: E731
EMPTY_SEEN = {"templates": set(), "styles": set(), "rule_families": set()}


def tag(**fields):
    base = dict(id="q", source="validation", split="validation", qtype="Q1", bank="q.where_object", depth=1,
                knowable=True, evidence_kept=True, repeat=False, repeat_in_visit=False, reworded=False, names=(),
                changed=False)
    base.update(fields)
    return slices.SliceTags(**base)


class FakeVillageTagsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.work = Workspace()
        cls.data = cls.work.data()
        cls.eval_data = exp1.open_data(cls.work.root, cls.data.rel, cls.data.tokenizer_info["path"],
                                       tokenizer_sha=cls.data.tokenizer.digest)
        cls.questions = exp1.split_questions(cls.eval_data, "validation")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.work.close()

    def tags(self, **options):
        return slices.tag_questions(self.eval_data.tokenizer, self.questions, seen=self.eval_data.seen,
                                    source="validation", names=NAMES["validation"], **options)

    def test_cut_is_a_s_window(self) -> None:
        self.assertEqual(slices.CUT_MAX_LEN, 768 - 32)
        items, tags = self.tags()
        self.assertEqual(len(tags), len(self.questions))
        self.assertEqual([item.question.id for item in items], [q.id for q in self.questions])
        for item in items:
            self.assertEqual(slices.window_start(item), item.question.context[0][0])   # short visits fit whole

    def test_near_far_not_told_names_and_rewording(self) -> None:
        _, tags = self.tags()
        for qid, t in tags.items():
            names = t.slices()
            self.assertTrue(t.decision)
            self.assertIn("overall", names)
            self.assertIn("reworded", names)                 # validation templates and style are unseen
            if qid.endswith("-c"):
                self.assertEqual(t.knowable, False)
                self.assertIn("not_told", names)
                self.assertFalse(t.near or t.far)
            else:
                self.assertIn("near", names)                 # everything fits A's cut
                self.assertIn("depth_1", names)
                self.assertNotIn("multi_hop", names)         # depth 1 is one hop
            self.assertEqual("fresh_names" in names, qid.endswith("-b"), qid)   # "-b" answers a name
            self.assertIsNone(t.changed)                     # fake shards are not replayed
        # A cut too short for the evidence line makes knowable questions far.
        _, short = self.tags(max_len=24)
        far = [t for t in short.values() if t.far]
        self.assertTrue(far)
        for t in far:
            self.assertEqual(t.evidence_kept, False)
            self.assertIn("far", t.slices())
            self.assertNotIn("far_deep", t.slices())         # depth 1
        self.assertIsNone(slices.shard_generator(self.eval_data.split_dir("validation")))

    def test_leak_classes_and_repeats_are_excluded(self) -> None:
        leak = tag(bank="q.who_has")
        self.assertFalse(leak.decision)
        self.assertEqual(leak.slices(), ("excluded", "excluded:leak:who_has"))
        box = tag(bank="q.in_container", repeat=True)
        self.assertEqual(box.slices(), ("excluded", "excluded:repeat", "excluded:leak:box_contents"))
        mixed = {"a": tag(id="a"), "b": leak, "c": tag(id="c", long=True, evidence_kept=False)}
        self.assertEqual(set(slices.decision_slices(mixed)), {"a"})   # no excluded, no far-long item decides
        self.assertIn("far_long", mixed["c"].slices())

    def test_repeats_anywhere_in_the_visit_leave_the_decision(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            text, meta = repeat_shard(Path(folder))
            same = {f"v:{key}": "q.where_person|kelo" for key in "abcd"}
            questions = step1.read_questions(text, meta, "test", same)
        tokenizer = tiny_tokenizer()
        _, tags = slices.tag_questions(tokenizer, questions, seen=EMPTY_SEEN, source="test", max_len=400, names=())
        self.assertEqual([t.repeat for t in tags.values()], [False, True, False, True])
        self.assertEqual([t.decision for t in tags.values()], [True, False, True, False])
        # Cut b's input so A no longer sees a's answer: step 1 stops calling it a repeat,
        # but the whole visit (D's input) still shows it, so it stays out of the decision.
        tail = len(tokenizer.encode(questions[1].prompt_line))
        _, cut = slices.tag_questions(tokenizer, questions[1:2], seen=EMPTY_SEEN, source="test", max_len=tail + 2,
                                      names=())
        b = cut["v:b"]
        self.assertFalse(b.repeat)
        self.assertTrue(b.repeat_in_visit)
        self.assertEqual(b.slices(), ("excluded", "excluded:repeat_in_visit"))

    def test_inputs_never_contain_the_answer(self) -> None:
        """design/06 §7 test 3, for A's canonical inputs: each ends at [answer], nothing follows."""
        items, _ = self.tags()
        audit = exp1.audit_items(self.eval_data.tokenizer, items)
        self.assertEqual(audit["inputs"], len(items))
        bad = items[0]
        answer = self.eval_data.tokenizer.encode(" " + bad.question.answer)
        planted = step1.EvalItem(**{**bad.__dict__, "prompt": bad.prompt[:-1] + answer + bad.prompt[-1:]})
        with self.assertRaises(AssertionError):
            exp1.audit_items(self.eval_data.tokenizer, [planted])


class ChangedFactTest(unittest.TestCase):
    """design/06 §7 test 10 on the real simulator: the changed tag fires on a planted twice-moved object."""

    def setUp(self) -> None:
        from learnlab.village import scheduler

        self.scheduler = scheduler
        self.registry = slices.village_registry()

    def planted(self, split: str = "validation", seed: int = 3):
        from learnlab.village.oracle import surface

        village = self.scheduler.Village(split, seed, self.registry.view(split))   # the replay rebuilds this exact one
        w = village.world
        loose = [o for o in w.objects() if w.items[o].loc[0] == "place" and w.breaks_on_put_down(o) is None]
        moved, still = loose[0], loose[1]
        start = w.items[moved].loc[1]
        first, second = [p for p in sorted(w.places) if p != start][:2]
        person = village.people[0]
        go = lambda place: {"op": "act", "action": "go", "args": {"person": person, "place": place}}  # noqa: E731
        hold = lambda action: {"op": "act", "action": action, "args": {"person": person, "item": moved}}  # noqa: E731
        script = [{"op": "say", "bank": "ev.intro_object", "slots": {"object": moved, "place": start}},
                  {"op": "say", "bank": "ev.intro_object", "slots": {"object": still, "place": w.items[still].loc[1]}}]
        script += [go(start)] if w.people[person] != start else []
        script += [hold("pick_up"), go(first), hold("put_down"), hold("pick_up"), go(second), hold("put_down"),
                   {"op": "ask", "bank": "q.where_object", "slots": {"object": moved}, "wrapper": None, "key": "q0"},
                   {"op": "ask", "bank": "q.where_object", "slots": {"object": still}, "wrapper": None, "key": "q1"}]

        def generate():
            vis, _ = self.scheduler._standalone(split, seed, self.registry, None, self.scheduler.VISIBLE_LINES,
                                                script=list(script))
            self.assertEqual(len(vis.script), len(script))     # every planted step happened
            return vis

        return generate, [surface(w, p) for p in (start, first, second)]

    def test_changed_fires_on_a_twice_moved_object(self) -> None:
        generate, (start, first, second) = self.planted()
        replays = slices.replay_changes(generate)
        moved, still = replays["validation-3:q0"], replays["validation-3:q1"]
        self.assertEqual(moved.answer, second)
        self.assertTrue(moved.changed)
        self.assertEqual(set(moved.older), {start, first})
        self.assertGreater(moved.states, 3)
        self.assertEqual(still.changed, False)
        self.assertEqual((moved.errors, still.errors), (0, 0))
        t = tag(changed=moved.changed, older_answers=moved.older)
        self.assertIn("changed", t.slices())
        self.assertTrue(slices.is_stale(t, start.upper()))     # an older place, however it is cased
        self.assertFalse(slices.is_stale(t, second))
        self.assertFalse(slices.is_stale(t, ""))
        self.assertIn("unchanged", tag(changed=still.changed).slices())

    def test_generated_visits_replay_exactly(self) -> None:
        visit = self.scheduler.generate_visit("validation", 5, registry=self.registry)
        replays = slices.replay_visit("validation", "validation-5")
        asked = self.scheduler.questions_of(visit)
        self.assertEqual({str(q["id"]): str(q["answer"]) for q in asked},
                         {qid: r.answer for qid, r in replays.items()})
        self.assertTrue(any(r.changed for r in replays.values()))
        self.assertEqual(sum(r.errors for r in replays.values()), 0)
        for q in asked:
            self.assertEqual(replays[str(q["id"])].signature, step1.question_signature(q["bank"], q["slots"]))
        with self.assertRaises(step1.ShardFormatError):
            slices.replay_visit("validation", "validation-5-cf")


class LongSplitTest(unittest.TestCase):
    def test_long_visits_have_four_days(self) -> None:
        from learnlab.village import scheduler

        registry = slices.village_registry()
        long = slices.long_visit("validation", 0, seed=0, registry=registry)
        plain = scheduler.generate_visit("validation", 0, registry=registry)
        self.assertEqual(long["id"], f"validation-{slices.LONG_SEED_OFFSET}")
        days = lambda visit: sum(r["bank"] == "ev.new_day" for r in visit["records"])  # noqa: E731
        self.assertEqual(days(long), slices.LONG_DAYS)
        self.assertGreater(len(long["records"]), len(plain["records"]))

    def test_generate_split_takes_the_long_generator(self) -> None:
        from learnlab.village.shards import GENERATOR, write_shards

        self.assertEqual(slices.PLAIN_GENERATOR, GENERATOR)
        with tempfile.TemporaryDirectory() as folder:
            budget = Budget(Path(folder), hard=10_000_000_000, steady=8_000_000_000)
            writer = functools.partial(write_shards, verbose=False)
            summary = slices.generate_long_split(budget, "d", "validation", 2, seed=0, workers=1, log=QUIET,
                                                 writer=writer)
            directory = Path(folder) / "d" / "validation-long"
            self.assertTrue((directory / "COMPLETE.json").is_file())
            self.assertEqual(summary["visits"], 2)
            self.assertEqual(slices.shard_generator(directory), slices.LONG_GENERATOR)
            replays = slices.replay_split(directory, "validation", days=slices.LONG_DAYS, log=QUIET)
            questions = [q for text, meta in step1.shard_files(directory)
                         for q in step1.read_questions(text, meta, "validation")]
            self.assertEqual({q.id for q in questions}, set(replays))
            for q in questions:
                self.assertEqual(replays[q.id].answer, q.answer)
            with self.assertRaises(ValueError):
                slices.generate_long_split(budget, "d", "train", 2, seed=0, workers=1, log=QUIET, writer=writer)


class EvaluationTest(unittest.TestCase):
    """exp1 end to end on the fake village with a tiny `Core` checkpoint (context 768, as A)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.work = Workspace()
        cls.data = cls.work.data()
        torch.manual_seed(0)
        cls.config = CoreConfig(cls.data.tokenizer.vocab_size, 768, 32, 2, 2)
        cls.model = Core(cls.config)
        # A checkpoint now records the preprocessing identity it was trained under, and a toy tokenizer is
        # scored only as an explicit test fixture (design/06 §11.4; premonition.identity).
        save_checkpoint(cls.work.budget, "artifacts/tiny.ckpt", model=cls.model,
                        config={"core": asdict(cls.config), "data": {"dir": cls.data.rel, "tag": cls.data.tag},
                                "tokenizer": cls.data.tokenizer_info,
                                "preprocess": preprocess.identity(preprocess.WITH_LABELS)})
        cls.report = exp1.evaluate_checkpoint(cls.work.root, "artifacts/tiny.ckpt", heldin=20, max_new=8,
                                              names=NAMES["train"] + NAMES["validation"], purpose="fixture",
                                              log=QUIET)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.work.close()

    def test_scores_every_validation_question_with_tags(self) -> None:
        report = self.report
        questions = exp1.split_questions(exp1.open_data(self.work.root, self.data.rel,
                                                        self.data.tokenizer_info["path"]), "validation")
        self.assertEqual(list(report["directories"]), ["validation", exp1.HELDIN_SOURCE])
        items = report["items"]["validation"]
        self.assertEqual([r["id"] for r in items], [q.id for q in questions])      # all of them, in order
        summary = report["directories"]["validation"]["summary"]
        self.assertEqual(summary["items"], len(questions))
        self.assertEqual(set(summary["decision_cells"]), set(slices.DECISION_SLICES))
        self.assertFalse(summary["decision_cells_ok"])                               # 72 items < MIN_ITEMS
        self.assertEqual(summary["decision_cells"]["overall"]["n"], summary["decision_items"])
        self.assertEqual(summary["cells"]["not_told"]["n"], len(questions) // 3)
        self.assertEqual(summary["per_depth"]["1"]["n"], 2 * len(questions) // 3)
        self.assertEqual(report["directories"]["validation"]["replay"]["replayed"], False)
        self.assertEqual(report["name_gap"]["fresh_names"]["n"], len(questions) // 3)
        self.assertGreater(report["name_gap"]["seen_names"]["n"], 0)
        self.assertEqual(report["cut"]["max_len"], 736)
        json.dumps(report)                                                          # JSON-able as is
        self.assertIn("overall: ", exp1.format_report(report))
        saved = exp1.save_report(self.work.budget, report)
        self.assertTrue((self.work.root / saved).is_file())

    def test_evaluation_is_read_only(self) -> None:
        """design/06 §7 test 4: a planted parameter write inside evaluation raises ReadOnlyViolation."""
        data = exp1.open_data(self.work.root, self.data.rel, self.data.tokenizer_info["path"])
        questions = exp1.split_questions(data, "validation")[:6]
        items = slices.canonical_items(data.tokenizer, questions, seen=data.seen)
        before = {k: v.clone() for k, v in self.model.state_dict().items()}
        results = exp1.score_read_only(self.model, data.tokenizer, items, max_new=4)
        self.assertEqual(len(results), len(items))
        for key, value in self.model.state_dict().items():
            self.assertTrue(torch.equal(value, before[key]), key)

        def cheating(model, tokenizer, items, **_options):
            model.embed.weight.add_(1.0)
            return []

        with self.assertRaises(ReadOnlyViolation):
            exp1.score_read_only(self.model, data.tokenizer, items, scorer=cheating)
        with self.assertRaises(ReadOnlyViolation):
            exp1.evaluate_directory(self.model, data, "validation", scorer=cheating, log=QUIET)
        with torch.no_grad():
            self.model.embed.weight.copy_(before["embed.weight"])     # undo the planted writes

    def test_verdict_pairs_reports_on_question_ids(self) -> None:
        other = json.loads(json.dumps(self.report))
        other["contender"] = "D"
        for row in other["items"]["validation"]:
            row["correct"] = not row["correct"]
        decision = exp1.verdict([self.report, other], allow_fixture=True)
        self.assertEqual(decision["contenders"], ["A", "D"])
        self.assertEqual(decision["verdict"], "INSUFFICIENT")                 # too few items, no C, E, B
        self.assertEqual(decision["cells"]["overall"], self.report["directories"]["validation"]["summary"]
                         ["decision_items"])
        with self.assertRaises(ValueError):
            exp1.verdict([self.report, self.report], allow_fixture=True)       # two reports for A
        clash = json.loads(json.dumps(other))
        clash["items"]["validation"][0]["slices"] = ["overall", "far"]
        with self.assertRaises(ValueError):
            exp1.verdict([self.report, clash], allow_fixture=True)


# ----------------------------------------------------------------- decision rules


def pattern(ids, accuracy):
    """Item i is right when (37 i mod 100) < 100 * accuracy: nested sets, so a higher accuracy is a superset."""
    return {i: (37 * int(i[1:])) % 100 < round(100 * accuracy) for i in ids}


class DecisionRuleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ids = [f"q{i}" for i in range(400)]
        self.near, self.far = self.ids[:200], self.ids[200:]
        self.slices = {}
        for i, qid in enumerate(self.ids):
            names = {"overall", "near" if i < 200 else "far"}
            if 200 <= i < 350:
                names.add("far_deep")
            if i >= 250:
                names.add("multi_hop")
            self.slices[qid] = names

    def contender(self, near, far):
        return {**pattern(self.near, near), **pattern(self.far, far)}

    def results(self, **changes):
        results = {"A": self.contender(0.8, 0.3), "C": self.contender(0.8, 0.3), "E": self.contender(0.8, 0.3),
                   "D": self.contender(0.8, 0.7), "B12": self.contender(0.5, 0.5), "B28": self.contender(0.55, 0.55),
                   exp1.WIPE_FULL: self.contender(0.78, 0.3)}
        results.update(changes)
        return {k: v for k, v in results.items() if v is not None}

    def status(self, decision):
        return {p["rule"]: p["status"] for p in decision["passes"]} | {"kill": decision["kill"]["status"]}

    def test_all_pass(self) -> None:
        decision = exp1.decide(self.results(), self.slices)
        self.assertEqual(decision["verdict"], "PASS", decision["reasons"])
        self.assertEqual(decision["passes"][2]["comparisons"][0]["better_b"], "B28")
        self.assertEqual(decision["cells"], {"overall": 400, "near": 200, "far": 200, "far_deep": 150,
                                             "multi_hop": 150})
        json.dumps(decision)

    def test_e_matching_d_fails_pass_2(self) -> None:
        decision = exp1.decide(self.results(E=self.contender(0.8, 0.7)), self.slices)
        self.assertEqual(self.status(decision)["pass2_far_multi_hop"], "FAIL")
        self.assertEqual(self.status(decision)["kill"], "SURVIVES")
        self.assertEqual(decision["verdict"], "FAIL")

    def test_a_small_lead_fails_pass_2_even_when_significant(self) -> None:
        decision = exp1.decide(self.results(C=self.contender(0.8, 0.62)), self.slices)
        failed = [c for c in decision["passes"][1]["comparisons"] if c["status"] == "FAIL"]
        self.assertEqual({(c["slice"], c["versus"]) for c in failed}, {("far", "C"), ("multi_hop", "C")})
        self.assertEqual(decision["verdict"], "FAIL")

    def test_c_matching_d_on_deep_far_kills(self) -> None:
        decision = exp1.decide(self.results(C=self.contender(0.8, 0.7)), self.slices)
        self.assertEqual(decision["kill"]["status"], "KILL")
        self.assertEqual(decision["verdict"], "KILL")

    def test_a_better_on_near_fails_pass_1(self) -> None:
        decision = exp1.decide(self.results(A=self.contender(0.95, 0.3)), self.slices)
        self.assertEqual(self.status(decision)["pass1_near"], "FAIL")
        # A one point ahead is not significantly ahead by the margin, but D >= A fails.
        decision = exp1.decide(self.results(A=self.contender(0.81, 0.3)), self.slices)
        entry = decision["passes"][0]["comparisons"][0]
        self.assertGreaterEqual(entry["p_value"], 0.01)
        self.assertEqual(entry["status"], "FAIL")

    def test_b_significantly_better_fails_pass_3(self) -> None:
        decision = exp1.decide(self.results(B28=self.contender(0.95, 0.95)), self.slices)
        self.assertEqual(self.status(decision)["pass3_overall"], "FAIL")
        self.assertEqual(decision["passes"][2]["comparisons"][0]["better_b"], "B28")

    def test_wipe_full_must_lose_the_far_advantage(self) -> None:
        decision = exp1.decide(self.results(**{exp1.WIPE_FULL: self.contender(0.78, 0.7)}), self.slices)
        self.assertEqual(self.status(decision)["pass4_wipe_full"], "FAIL")
        decision = exp1.decide(self.results(**{exp1.WIPE_FULL: self.contender(0.5, 0.3)}), self.slices)
        self.assertEqual(self.status(decision)["pass4_wipe_full"], "FAIL")    # near fell below 90% of D's

    def test_missing_or_small_cells_are_insufficient(self) -> None:
        decision = exp1.decide(self.results(E=None), self.slices)
        self.assertEqual(self.status(decision)["pass2_far_multi_hop"], "INSUFFICIENT")
        self.assertEqual(decision["verdict"], "INSUFFICIENT")
        small = {qid: names for qid, names in self.slices.items() if int(qid[1:]) % 5 == 0}   # 40 near, 40 far
        decision = exp1.decide(self.results(), small)
        self.assertEqual(set(self.status(decision).values()), {"INSUFFICIENT"})
        self.assertEqual(decision["verdict"], "INSUFFICIENT")
        self.assertEqual(exp1.decide(self.results(), small, min_items=25)["verdict"], "PASS")

    def test_paired_helper(self) -> None:
        a, b = self.contender(0.8, 0.7), self.contender(0.8, 0.3)
        out = exp1.paired(a, b, self.far)
        self.assertEqual(out["n"], 200)
        self.assertAlmostEqual(out["difference"], 0.4)
        self.assertEqual(out["p_value"], mcnemar_greater([float(a[i]) for i in self.far],
                                                          [float(b[i]) for i in self.far]))
        self.assertEqual((out["a_only"], out["b_only"]), (80, 0))
        self.assertTrue(out["significant"])
        margin = exp1.paired(a, b, self.far, margin=0.03)
        self.assertLess(margin["p_value"], 0.01)
        self.assertGreater(exp1.paired(b, a, self.far, margin=0.03)["p_value"], 0.5)
        self.assertEqual(exp1.paired(a, b, ["nope"])["n"], 0)
        self.assertIsNone(exp1.paired(a, {}, None)["p_value"])


if __name__ == "__main__":
    unittest.main()
