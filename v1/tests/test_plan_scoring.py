"""Q12 plan-aware scoring (finding q12-plan-scoring): a working plan that differs from the canonical string counts when plans
are passed, and nothing changes when they are not. Questions are regenerated from the village simulator's `validation`
split (never the sealed `test` split)."""
import ast, inspect, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import torch

from learnlab import step1
from memorylab.storage import Budget
from premonition import scoring, train
from v1 import run as vrun


class PlanScoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from learnlab.village.shards import write_shards
        except ImportError as error:
            raise unittest.SkipTest(f"village simulator not available: {error}")
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        write_shards("validation", 4, root / "d" / "validation", 1, seed=0, verbose=False)
        step1.build_oracle(Budget(root, hard=10_000_000_000, steady=8_000_000_000), "d", "validation", "validation",
                           workers=1, log=lambda _m: None)
        cls.root = root / "d"
        split = cls.root / "validation"
        cls.signatures, cls.plans, _ = step1.load_oracle(split)
        cls.q12 = [q for t, m in step1.shard_files(split) for q in step1.read_questions(t, m, "validation", cls.signatures)
                   if q.qtype == "Q12"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def padded(self, q):
        """A different working plan: the canonical one behind a redundant 'go to <where the person already is>'."""
        from learnlab.village.oracle import surface
        world, person, _ = self.plans[q.id]
        return f"go to {surface(world, world.people[person])}, {q.answer.lower()}"

    def test_canonical_and_padded_plan(self):
        self.assertTrue(self.q12)
        differs = 0
        for q in self.q12:
            plan = self.plans[q.id]
            self.assertEqual(scoring.score_answer(q.answer, q.answer.lower(), plan), (True, True))   # model output is lowercase
            exact, correct = scoring.score_answer(q.answer, self.padded(q), plan)
            self.assertTrue(correct)
            differs += not exact
            self.assertEqual(scoring.score_answer(q.answer, self.padded(q), None), (exact, exact))   # no plan: exact only
            self.assertEqual(scoring.score_answer(q.answer, "not told", plan), (False, False))
            self.assertEqual(scoring.score_answer(q.answer, "", plan), (False, False))
        self.assertGreater(differs, 0)          # some canonical plans (no 'go to') differ from the padded working plan

    def test_plan_checked_never_below_exact(self):
        for q in self.q12:
            for said in (q.answer.lower(), "not told", q.answer.lower() + ", open the moon", self.padded(q)):
                exact, correct = scoring.score_answer(q.answer, said, self.plans[q.id])
                self.assertGreaterEqual(correct, exact)

    def test_module_imports_no_torch(self):
        tree = ast.parse(inspect.getsource(scoring))
        names = [a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names]
        self.assertFalse(any("torch" in n for n in names))

    def _judge(self, plans):
        """judge() over the regenerated questions, the model 'saying' the padded plan for each."""
        ids = [q.id for q in self.q12]
        said = {q.id: self.padded(q) for q in self.q12}
        gold = {q.id: q.answer for q in self.q12}
        batch = SimpleNamespace(question_ids=ids, answer=torch.zeros(len(ids), 1, dtype=torch.long),
                                q_visit=torch.zeros(len(ids), dtype=torch.long), names=[None])
        answers = SimpleNamespace(ids=lambda: [[i] for i in range(len(ids))])
        exact_out: list = []
        with mock.patch.object(train, "entity_text", lambda i, table, tok: said[ids[i[0]]]), \
             mock.patch.object(train.preprocess, "target_text", mock.Mock(side_effect=[gold[i] for i in ids])):
            correct, _ = train.judge(answers, batch, tokenizer=object(), plans=plans, exact_out=exact_out)
        return correct, exact_out

    def test_judge_default_is_exact_only_and_plans_add_credit(self):
        correct0, exact0 = self._judge(None)
        self.assertEqual(exact0, [])                        # exact_out untouched without plans
        correct1, exact1 = self._judge(self.plans)
        self.assertEqual(exact1, correct0)                  # exact flags are the old scores
        self.assertTrue(all(correct1))                      # every padded plan works
        self.assertGreater(sum(correct1), sum(correct0))

    def test_plan_counts(self):
        ids = [q.id for q in self.q12] + ["other"]
        yes = [True] * len(ids)
        n = len(self.q12)
        self.assertEqual(scoring.plan_counts(ids, yes, yes, self.plans),
                         {"q12_questions": n, "q12_exact": n, "q12_plan_checked": n})
        self.assertEqual(scoring.plan_counts(ids, yes, yes, None)["q12_questions"], 0)

    def test_load_plans_refuses_the_sealed_split(self):
        self.assertEqual(set(vrun.load_plans(self.root, "validation")), set(self.plans))
        with self.assertRaises(ValueError):
            vrun.load_plans(self.root, "test")

    def test_plan_scoring_flag_defaults_off(self):
        self.assertIn('"--plan-scoring", action="store_true"', inspect.getsource(vrun.main))


if __name__ == "__main__":
    unittest.main()
