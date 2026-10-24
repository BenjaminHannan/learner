"""CPU tests for the W1 per-bank baseline (v1/baselines.py) and the opt-in Q13 first-named swap (village scheduler).
Run: python -m unittest v1.tests.test_baselines_q13  (the swap test regenerates ~1200 visits, about a minute)."""
import json, unittest

from v1 import baselines


class Cache:
    def __init__(self, ids, answers):
        self.question_ids, self._a = ids, answers

    def answer(self, q):
        return self._a[q]


class PerBank(unittest.TestCase):
    def setUp(self):
        tr = [("a0", "A", [1]), ("a1", "A", [1]), ("a2", "A", [1]), ("a3", "A", [2]),
              ("b0", "B", [3]), ("b1", "B", [3]), ("b2", "B", [3]), ("b3", "B", [4])]
        dv = [("d0", "A", [1]), ("d1", "A", [1]), ("d2", "B", [3]), ("d3", "B", [3])]
        self.train = Cache([t[0] for t in tr], [t[2] for t in tr])
        self.dev = Cache([t[0] for t in dv], [t[2] for t in dv])
        self.banks = {t[0]: t[1] for t in tr + dv}

    def test_per_bank_beats_global(self):
        out = baselines.baselines(self.train, self.dev, banks=self.banks)
        self.assertEqual(out["majority_per_bank"], 1.0)
        self.assertEqual(out["best"], 0.5)          # frozen v1 rule: one constant answer
        self.assertEqual(out["best_v2"], 1.0)

    def test_v1_output_unchanged_without_banks(self):
        out = baselines.baselines(self.train, self.dev)
        self.assertEqual(set(out), {"majority_train", "majority_train_answer_ids", "majority_dev",
                                    "majority_dev_answer_ids", "n_questions", "best"})

    def test_unseen_bank_falls_back_to_global(self):
        banks = dict(self.banks, d2="C", d3="C")    # bank C never in train: global train majority is [1] (tie, first seen)
        out = baselines.baselines(self.train, self.dev, banks=banks)
        self.assertEqual(out["majority_per_bank"], 0.5)

    def test_first_named_q13(self):
        # per-bank majority is [9]: right only on the untold one; the rule is right on both first-named questions
        tr = Cache(["t0", "t1"], [[9], [9]])
        dv = Cache(["q0", "q1", "q2", "q3"], [[1], [2], [3], [9]])
        banks = {k: "q.compare_count" for k in ("t0", "t1", "q0", "q1", "q2", "q3")}
        out = baselines.baselines(tr, dv, banks=banks, first_named={"q0": True, "q1": True, "q2": False, "q3": None})
        self.assertEqual(out["majority_per_bank"], 0.25)
        self.assertEqual(out["first_named_q13"], 0.75)      # q0, q1 by rule; q3 by majority
        self.assertEqual(out["best_v2"], 0.75)


class CompareSwap(unittest.TestCase):
    @staticmethod
    def render(split, a, b, swap):
        from learnlab.village import scheduler, shards
        shards._setup({"seed": 0, "generator": shards.GENERATOR, "families": shards.FAMILIES, "names": shards.NAMES,
                       "patterns": None, "window_chars": shards.WINDOW_CHARS, "audit_every": 0})
        old, scheduler.COMPARE_SWAP = scheduler.COMPARE_SWAP, swap
        try:
            return [q for r in shards.render_range(split, a, b)[2] for q in r.questions]
        finally:
            scheduler.COMPARE_SWAP = old

    def test_swap(self):
        for split, a, b in (("train", 95000, 95300), ("validation", 0, 300)):   # dev visits are train 95000+; never test
            off, on = self.render(split, a, b, False), self.render(split, a, b, True)
            key = lambda q: json.dumps(q, sort_keys=True, default=str)
            rest = lambda L: [key(q) for q in L if q["base_qtype"] != "Q13"]
            self.assertEqual(rest(off), rest(on))               # the swap touches no other question
            self.assertEqual(len(off), len(on))
            shares = []
            for L in (off, on):
                c = {"first": 0, "second": 0}
                for q in L:
                    if q["qtype"] != "Q13":
                        continue
                    t, al = q["question"].lower(), str(q["answer"]).lower()
                    j = t.rfind(" or ")
                    if al in t[:j] and al not in t[j:]:
                        c["first"] += 1
                    elif al in t[j:] and al not in t[:j]:
                        c["second"] += 1
                shares.append(c["first"] / (c["first"] + c["second"]))
            self.assertGreater(shares[0], 0.9, split)           # the old shortcut
            self.assertTrue(0.40 <= shares[1] <= 0.60, (split, shares[1]))


if __name__ == "__main__":
    unittest.main()
