"""Step 0: every planted flaw is caught and every clean control passes."""
import unittest

from learnlab.step0 import AREAS, run_step0
from learnlab.toy import counterfactual_pair, episodes, make_registry


class ToyWorldTests(unittest.TestCase):
    def test_generation_is_deterministic_and_splits_stay_disjoint(self):
        first = episodes(make_registry(), "test", 20)
        second = episodes(make_registry(), "test", 20)
        self.assertEqual([e.text for e in first], [e.text for e in second])
        registry = make_registry()
        for split in ("train", "validation", "test"):
            episodes(registry, split, 30)
        registry.assert_disjoint()
        for axis in ("template", "teacher_style", "rule_family"):
            self.assertTrue(all(count > 0 for count in registry.summary()[axis].values()), axis)

    def test_counterfactual_twins_differ_in_answer_only(self):
        first, twin = counterfactual_pair(make_registry(), "test", 3)
        self.assertEqual(first.question, twin.question)
        self.assertNotEqual(first.target.place, twin.target.place)
        self.assertNotIn(first.target.place, first.question.lower())


class Step0Tests(unittest.TestCase):
    def test_every_planted_flaw_is_caught_and_every_clean_control_passes(self):
        report = run_step0()
        failed = [(c["check"], c.get("error")) for c in report["checks"] if not c["passed"]]
        self.assertEqual(failed, [])
        self.assertEqual(report["status"], "passed")
        self.assertEqual(set(report["area_seconds"]), set(AREAS))


if __name__ == "__main__":
    unittest.main()
