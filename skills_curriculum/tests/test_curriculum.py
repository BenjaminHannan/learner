import collections
import hashlib
import json
import os
import re
import tempfile
import unittest

from skills_curriculum import build, core, skills, verify  # noqa: F401


def _read(p):
    with open(p, "rb") as f:
        return f.read()


class CurriculumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.train, cls.dev, cls.man = build.build(cls.tmp, 4800, 10, 7)

    def test_all_rows_verify(self):
        bad = [(r["id"], verify.check_item(r)) for r in self.train + sum(self.dev.values(), []) if verify.check_item(r)]
        self.assertEqual(bad, [])

    def test_checker_catches_a_wrong_answer(self):
        r = dict(next(r for r in self.train if r["family"] == "arith_bare" and r["variant"] == "verbal"))
        r["answer"] = str(int(r["answer"]) + 1)
        r["accepted"] = [r["answer"]]
        self.assertTrue(verify.check_item(r))

    def test_train_has_no_heldout_flag(self):
        for r in self.train:
            self.assertFalse(any(r["flags"].values()), r["id"])

    def test_heldout_families_absent_from_train(self):
        ho = {f for f, v in core.FAMILIES.items() if v["heldout_family"]}
        self.assertTrue(ho)
        self.assertFalse({r["family"] for r in self.train} & ho)
        self.assertEqual({r["family"] for r in self.dev["family"]}, ho)

    def test_prompts_never_repeat_and_dev_is_disjoint(self):
        tp = [r["prompt"] for r in self.train]
        self.assertEqual(len(tp), len(set(tp)))
        for k, rows in self.dev.items():
            self.assertFalse(set(tp) & {r["prompt"] for r in rows}, k)

    def test_dev_cells_isolate_one_shift(self):
        for kind in ("answer", "frame", "vocab", "variant"):
            for r in self.dev[kind]:
                on = [k for k, v in r["flags"].items() if v]
                self.assertEqual(on, [kind], (kind, r["id"], on))

    def test_heldout_answers_never_in_train_per_family(self):
        for r in self.train:
            if core.FAMILIES[r["family"]]["answer_open"]:
                self.assertFalse(core.answer_held(r["family"], r["answer"]), r["id"])

    def test_heldout_vocab_words_absent_from_train_text(self):
        pools = {"names": core.NAMES, "nouns": core.NOUNS, "words": core.WORDS, "catwords": core.CAT_WORDS,
                 "places": core.PLACES, "colors": core.COLORS}
        held = set()
        for key, pool in pools.items():
            held |= {w.lower() for w in pool if core.held_by_rank("vocab", key, w, pool, core.VOCAB_FRAC, 5)}
        self.assertTrue(len(held) > 20)
        for r in self.train:
            for t in re.findall(r"[A-Za-z]+", r["prompt"].lower()):
                self.assertNotIn(t, held, r["id"])
                self.assertNotIn(t.rstrip("s"), held, r["id"])

    def test_heldout_syllables_absent_from_train_made_up_words(self):
        held = [s for s in core.SYLLABLES if core.held_by_rank("vocab", "syllables", s, core.SYLLABLES, core.VOCAB_FRAC, 5)]
        self.assertTrue(held)
        for r in self.train:
            if r["family"] == "copy_word":
                self.assertFalse(r["flags"]["vocab"])

    def test_wrappers_in_train_are_trainable(self):
        for r in self.train:
            for k, pool in (("pre", core.OPENERS), ("post", core.CLOSERS)):
                if r["wrap"][k]:
                    key = "wrap_open" if k == "pre" else "wrap_close"
                    self.assertFalse(core.held_by_rank("frame", key, r["wrap"][k], pool, core.FRAME_FRAC, 5))

    def test_token_estimate_cap(self):
        self.assertLessEqual(max(r["est_tokens"] for r in self.train), core.MAX_TOKENS_EST)

    def test_stage_order_easy_to_hard(self):
        stages = [r["stage"] for r in self.train]
        self.assertEqual(stages, sorted(stages))
        for r in self.train:
            if r["stage"] <= 8:
                self.assertLessEqual(r["level"], r["stage"])

    def test_every_op_in_every_position_present(self):
        seen = set()
        for r in self.train:
            if r["family"] == "chain_ops":
                ops = r["meta"]["ops"]
                seen |= {(i, o) for i, o in enumerate(ops)}
        for pos in (0, 1):
            for op in ("add", "sub", "mul", "div"):
                self.assertIn((pos, op), seen)

    def test_layouts_cover_question_first(self):
        self.assertIn("question_first", {r["layout"] for r in self.train})
        used = {r["layout"] for r in self.train}
        held = [l for l in core.LAYOUTS if core.held_by_rank("variant", "layouts", l, core.LAYOUTS, 0.34, 3)]
        self.assertEqual(len(held), 1)
        self.assertFalse(used & set(held))

    def test_deterministic(self):
        d2 = tempfile.mkdtemp()
        build.build(d2, 4800, 10, 7)
        for fn in ("train.jsonl", "dev/answer.jsonl", "dev/family.jsonl"):
            a = hashlib.sha256(_read(os.path.join(self.tmp, fn))).hexdigest()
            b = hashlib.sha256(_read(os.path.join(d2, fn))).hexdigest()
            self.assertEqual(a, b, fn)

    def test_stream_never_repeats_and_is_clean(self):
        it = build.iter_train(3, levels={2, 3})
        seen = set()
        for _ in range(300):
            r = next(it)
            self.assertNotIn(r["prompt"], seen)
            seen.add(r["prompt"])
            self.assertFalse(any(r["flags"].values()))


if __name__ == "__main__":
    unittest.main()
