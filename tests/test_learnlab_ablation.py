"""Step 0 ablation harness: planted flaws must be refused or failed; a good component must pass."""
from __future__ import annotations

from contextlib import contextmanager
import random
import unittest
from typing import Iterator, Optional

import torch

from learnlab.ablation import (
    REQUIREMENTS,
    Account,
    Arm,
    Component,
    Requirement,
    judge_component,
)
from learnlab.policy import MIN_EFFECT

N = 300
ITEMS = tuple(f"item{i:03d}" for i in range(N))
INFO = frozenset({"context"})


def account(run_id: str, **overrides) -> Account:
    budget = dict(retrieved_items=N, retrieved_tokens=12 * N, information=INFO)
    budget.update(overrides)
    return Account(run_id, **budget)


def binary(rate: float, rng: random.Random) -> dict[str, float]:
    return {item: 1.0 if rng.random() < rate else 0.0 for item in ITEMS}


class Toggle:
    """A system whose component can be switched off; scores come from fixed tables."""

    def __init__(self, full: dict[str, float], lesioned: dict[str, float]) -> None:
        self.full, self.lesioned_scores = full, lesioned
        self.on = True

    def evaluate(self, items: tuple[str, ...]) -> dict[str, float]:
        table = self.full if self.on else self.lesioned_scores
        return {item: table[item] for item in items}

    @contextmanager
    def lesion(self) -> Iterator[None]:
        self.on = False
        try:
            yield
        finally:
            self.on = True

    def state(self) -> str:
        return f"on={self.on}"

    def component(self, kind: str = "toy_store") -> Component:
        return Component("toggle", kind, self.lesion, self.state)


def good_case(seed: int = 0) -> tuple[Toggle, dict[str, Arm]]:
    """Full 0.6 + 0.75 * rest (about 0.9) vs lookup about 0.6; the lesion falls back to lookup."""
    rng = random.Random(seed)
    base = binary(0.6, rng)
    full = {item: 1.0 if base[item] or rng.random() < 0.75 else 0.0 for item in ITEMS}
    system = Toggle(full, dict(base))
    baselines = {"plain_lookup": Arm("plain_lookup", base, account("lookup-run"))}
    return system, baselines


def judge(system: Toggle, baselines, *, full_account: Optional[Account] = None, **kwargs):
    kwargs.setdefault("min_effect", MIN_EFFECT)
    return judge_component(
        system.component(kwargs.pop("kind", "toy_store")),
        kwargs.pop("evaluate", system.evaluate),
        kwargs.pop("items", ITEMS),
        full_account or account("full-run"),
        baselines,
        **kwargs,
    )


class RequirementTableTests(unittest.TestCase):
    def test_design_table_and_toy_are_covered(self):
        for kind in ["episode_cards", "knowledge_slots", "gating", "thinking_stop",
                     "continual_learner", "transfer", "toy_store"]:
            self.assertIn(kind, REQUIREMENTS)
            self.assertTrue(REQUIREMENTS[kind].baselines)
        self.assertIn("fixed_k_thinking", REQUIREMENTS["thinking_stop"].baselines)
        self.assertIn("flops", REQUIREMENTS["thinking_stop"].match)
        self.assertIn("age_matched", REQUIREMENTS["transfer"].baselines)
        self.assertFalse(REQUIREMENTS["transfer"].same_information)
        self.assertIn("retrieved_tokens", REQUIREMENTS["episode_cards"].match)
        self.assertEqual(
            set(REQUIREMENTS["gating"].baselines),
            {"fifo", "lru", "reservoir", "surprise_only", "teacher_flag_only"},
        )

    def test_requirement_and_account_validation(self):
        with self.assertRaises(ValueError):
            Requirement(baselines=("x",), match=("wall_clock",))
        with self.assertRaises(ValueError):
            Requirement(baselines=())
        with self.assertRaises(ValueError):
            Account("")
        with self.assertRaises(ValueError):
            Account("run", flops=-1.0)
        with self.assertRaises(TypeError):
            Account("run", information="context")


class GoodComponentTests(unittest.TestCase):
    def test_good_component_with_matched_budgets_passes(self):
        system, baselines = good_case()
        verdict = judge(system, baselines)
        self.assertTrue(verdict.passed, verdict.reasons)
        self.assertTrue(verdict.beats_baselines and verdict.lesion_removes_gain)
        self.assertTrue(verdict.repeatable and verdict.lesion_active and verdict.lesion_restored)
        report = verdict.as_dict()
        self.assertTrue(report["passed"])
        self.assertIn("full", report["accounts"])
        self.assertIn("baseline:plain_lookup", report["accounts"])
        self.assertLess(report["baseline_pvalues"]["plain_lookup"], 0.01)
        self.assertIsNotNone(report["lesion_gain_pvalue"])

    def test_caller_rng_is_restored(self):
        system, baselines = good_case()

        def consuming(items):
            random.random()
            torch.rand(3)
            return system.evaluate(items)

        random.seed(123)
        torch.manual_seed(123)
        expected_py, expected_torch = random.random(), torch.rand(1)
        random.seed(123)
        torch.manual_seed(123)
        verdict = judge(system, baselines, evaluate=consuming)
        self.assertTrue(verdict.passed, verdict.reasons)
        self.assertEqual(random.random(), expected_py)
        self.assertTrue(torch.equal(torch.rand(1), expected_torch))

    def test_rng_dependent_evaluation_is_repeatable(self):
        system, baselines = good_case()

        def noisy(items):
            scores = system.evaluate(items)
            # Global-RNG noise that would break pairing if arms saw different RNG states.
            return {item: scores[item] if random.random() > 0.01 else 1.0 - scores[item] for item in items}

        verdict = judge(system, baselines, evaluate=noisy)
        self.assertTrue(verdict.repeatable, verdict.reasons)

    def test_settings_are_validated(self):
        system, baselines = good_case()
        for bad in [0.0, -0.1, float("nan")]:
            with self.assertRaises(ValueError):
                judge(system, baselines, min_effect=bad)
        with self.assertRaises(ValueError):
            judge(system, baselines, kind="unknown_kind")
        with self.assertRaises(TypeError):
            judge(system, baselines, items="item000")


class EvaluationProtocolTests(unittest.TestCase):
    def test_drifting_evaluation_fails(self):
        # Review 1: a no-op component "passed" because the first call scored 1.0 and later ones 0.0.
        system, baselines = good_case()
        calls = {"n": 0}

        def drifting(items):
            calls["n"] += 1
            value = 1.0 if calls["n"] == 1 else 0.0
            return {item: value for item in items}

        verdict = judge(system, baselines, evaluate=drifting)
        self.assertFalse(verdict.passed)
        self.assertFalse(verdict.repeatable)
        self.assertTrue(any("not repeatable" in reason for reason in verdict.reasons), verdict.reasons)

    def test_reshuffled_or_incomplete_evaluation_is_rejected(self):
        system, baselines = good_case()
        as_list = lambda items: [system.evaluate(items)[item] for item in items]  # noqa: E731
        verdict = judge(system, baselines, evaluate=as_list)
        self.assertFalse(verdict.passed)
        self.assertTrue(any("not a mapping" in reason for reason in verdict.reasons), verdict.reasons)
        missing = lambda items: {item: 1.0 for item in items[:-1]}  # noqa: E731
        verdict = judge(system, baselines, evaluate=missing)
        self.assertTrue(any("missing 1 item" in reason for reason in verdict.reasons), verdict.reasons)
        extra = lambda items: {**system.evaluate(items), "other": 1.0}  # noqa: E731
        verdict = judge(system, baselines, evaluate=extra)
        self.assertTrue(any("unrequested" in reason for reason in verdict.reasons), verdict.reasons)

    def test_non_restoring_lesion_fails(self):
        system, baselines = good_case()

        @contextmanager
        def leaky():
            system.on = False
            yield  # never restores

        component = Component("leaky", "toy_store", leaky, system.state)
        verdict = judge_component(
            component, system.evaluate, ITEMS, account("full-run"), baselines, min_effect=MIN_EFFECT
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(verdict.lesion_restored)
        self.assertFalse(verdict.repeatable)
        self.assertTrue(any("did not restore" in reason for reason in verdict.reasons), verdict.reasons)

    def test_lesion_that_changes_no_state_fails(self):
        system, baselines = good_case()

        @contextmanager
        def no_op():
            yield

        component = Component("inert", "toy_store", no_op, system.state)
        verdict = judge_component(
            component, system.evaluate, ITEMS, account("full-run"), baselines, min_effect=MIN_EFFECT
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(verdict.lesion_active)
        self.assertFalse(verdict.lesion_removes_gain)
        self.assertTrue(any("changed no component state" in reason for reason in verdict.reasons))

    def test_one_item_and_duplicate_items_fail(self):
        # Review 2: a one-item test passed. Here full is right and the baseline wrong on that item.
        item = ITEMS[0]
        system = Toggle({item: 1.0}, {item: 0.0})
        one = {"plain_lookup": Arm("plain_lookup", {item: 0.0}, account("lookup-run"))}
        verdict = judge(system, one, items=(item,))
        self.assertFalse(verdict.passed)
        self.assertTrue(any("at least 100" in reason for reason in verdict.reasons), verdict.reasons)
        # Even with the minimum waived, one item cannot be significant.
        waived = judge(system, one, items=(item,), min_items=1)
        self.assertFalse(waived.passed)
        self.assertEqual(waived.baseline_pvalues["plain_lookup"], 0.5)
        system, baselines = good_case()
        verdict = judge(system, baselines, items=ITEMS + ITEMS[:1])
        self.assertTrue(any("not unique" in reason for reason in verdict.reasons), verdict.reasons)


class BaselineSlotTests(unittest.TestCase):
    def test_mismatched_baseline_items_are_refused(self):
        system, baselines = good_case()
        other = {f"other{i:03d}": 0.0 for i in range(N)}
        verdict = judge(system, {"plain_lookup": Arm("plain_lookup", other, account("lookup-run"))})
        self.assertFalse(verdict.passed)
        self.assertIn("plain_lookup", verdict.refused)
        self.assertNotIn("plain_lookup", verdict.baseline_pvalues)

    def test_budget_mismatch_is_refused(self):
        system, baselines = good_case()
        scores = dict(baselines["plain_lookup"].scores)
        cheap = Arm("plain_lookup", scores, account("lookup-run", retrieved_tokens=N))
        verdict = judge(system, {"plain_lookup": cheap})
        self.assertFalse(verdict.passed)
        problems = verdict.refused["plain_lookup"]
        self.assertTrue(any("budget mismatch: retrieved_tokens" in p for p in problems), problems)
        # Within the 5% tolerance is accepted.
        close = Arm("plain_lookup", scores, account("lookup-run", retrieved_tokens=int(12 * N * 1.03)))
        self.assertTrue(judge(system, {"plain_lookup": close}).passed)

    def test_information_mismatch_and_shared_run_id_are_refused(self):
        system, baselines = good_case()
        scores = dict(baselines["plain_lookup"].scores)
        oracle = frozenset({"context", "oracle"})
        informed = Arm("plain_lookup", scores, account("lookup-run", information=oracle))
        self.assertIn("plain_lookup", judge(system, {"plain_lookup": informed}).refused)
        same_run = Arm("plain_lookup", scores, account("full-run"))
        self.assertIn("plain_lookup", judge(system, {"plain_lookup": same_run}).refused)
        misnamed = Arm("majority", scores, account("lookup-run"))
        self.assertIn("plain_lookup", judge(system, {"plain_lookup": misnamed}).refused)

    def test_missing_required_baseline_is_refused(self):
        system, baselines = good_case()
        majority = {item: 0.0 for item in ITEMS}
        verdict = judge(system, {"majority": Arm("majority", majority, account("majority-run"))})
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.missing_baselines, ["plain_lookup"])
        self.assertFalse(verdict.beats_baselines)

    def test_extra_baselines_must_also_be_beaten(self):
        system, baselines = good_case()
        strong = Arm("oracle_lookup", dict(system.full), account("oracle-run"))
        verdict = judge(system, {**baselines, "oracle_lookup": strong})
        self.assertFalse(verdict.passed)
        self.assertFalse(verdict.beats_baselines)


class StatisticalRuleTests(unittest.TestCase):
    def test_four_of_three_hundred_discordant_wins_fail(self):
        # Review 2: 4/300 discordant items, all favouring full, passed the old bootstrap rule.
        rng = random.Random(0)
        base = binary(0.6, rng)
        full = dict(base)
        for item in [item for item in ITEMS if base[item] == 0.0][:4]:
            full[item] = 1.0
        system = Toggle(full, dict(base))
        verdict = judge(system, {"plain_lookup": Arm("plain_lookup", base, account("lookup-run"))})
        self.assertFalse(verdict.passed)
        self.assertFalse(verdict.beats_baselines)
        self.assertGreater(verdict.baseline_pvalues["plain_lookup"], 0.01)

    def test_constant_small_improvement_fails(self):
        # Review 1: a constant 0.001 improvement passed with min_margin=0.
        full = {item: 0.501 for item in ITEMS}
        base = {item: 0.5 for item in ITEMS}
        system = Toggle(full, dict(base))
        verdict = judge(system, {"plain_lookup": Arm("plain_lookup", base, account("lookup-run"))})
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.baseline_pvalues["plain_lookup"], 1.0)

    def test_forty_percent_gain_removing_component_fails(self):
        # Review 2: a lesion that removes only 40% of a 20-point gain passed 12/200 trials.
        passes = 0
        for trial in range(25):
            rng = random.Random(100 + trial)
            base = binary(0.5, rng)
            full = {item: 1.0 if base[item] or rng.random() < 0.4 else 0.0 for item in ITEMS}
            lesioned = {
                item: full[item] if full[item] == base[item] or rng.random() < 0.6 else base[item]
                for item in ITEMS
            }
            system = Toggle(full, lesioned)
            verdict = judge(system, {"plain_lookup": Arm("plain_lookup", base, account("lookup-run"))})
            self.assertTrue(verdict.beats_baselines)
            passes += verdict.passed
        self.assertEqual(passes, 0)

    def test_destructive_lesion_needs_trained_without_control(self):
        # Review 2: full 0.90 vs lookup 0.85; the lesion wrecks the system to 0.
        rng = random.Random(1)
        base = binary(0.7, rng)
        full = {item: 1.0 if base[item] or rng.random() < 0.8 else 0.0 for item in ITEMS}
        system = Toggle(full, {item: 0.0 for item in ITEMS})
        baselines = {"plain_lookup": Arm("plain_lookup", base, account("lookup-run"))}
        verdict = judge(system, baselines)
        self.assertFalse(verdict.passed)
        self.assertTrue(verdict.destructive)
        self.assertGreater(verdict.destructive_overshoot, 0.5)
        self.assertTrue(any("destructive lesion" in reason for reason in verdict.reasons), verdict.reasons)

        # With a weaker control trained without the component, the verdict is judged and passes.
        control = Arm("trained_without", dict(base), account("without-run"))
        judged = judge(system, baselines, trained_without=control)
        self.assertTrue(judged.passed, judged.reasons)
        self.assertLess(judged.trained_without_pvalue, 0.01)

        # A control trained without the component that does as well as the full system fails it.
        as_good = Arm("trained_without", dict(full), account("without-run"))
        failed = judge(system, baselines, trained_without=as_good)
        self.assertFalse(failed.passed)
        self.assertTrue(any("control trained without" in reason for reason in failed.reasons))

        # A control with a mismatched budget is refused.
        unmatched = Arm("trained_without", dict(base), account("without-run", retrieved_items=1))
        refused = judge(system, baselines, trained_without=unmatched)
        self.assertIn("trained_without", refused.refused)
        self.assertFalse(refused.passed)


if __name__ == "__main__":
    unittest.main()
