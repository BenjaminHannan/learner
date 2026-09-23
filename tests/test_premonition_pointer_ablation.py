"""The A-vs-E pointer ablation's aligned row builders (scripts/premonition_pointer_ablation.py).

CPU only, seconds: 32 real village visits encoded twice (plain and pointerized) from one temporary shard
build. What is checked is exactly what the comparison rests on -- that the two arms differ ONLY in how
names are spelled:

  * every row is exactly `length` tokens, starts with <eos>, and ends with <eos> unless it was truncated;
  * the loss mask is True over the visit and False over the padding, and nowhere else;
  * every pointerized id is either an ordinary token or one of the N_ENT entity ids, renumbered per visit;
  * the A and E streams walk the SAME visits in the SAME order for the same seed;
  * the plain cache the A arm reads encodes each visit exactly as `learnlab.step1.encode_visit` does.
"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

# The script under test carries run.py's no-install bootstrap (dependency roots and cache redirection), so
# it is imported before torch: that is also how it is imported on the machine that runs the experiment.
import premonition_pointer_ablation as ablation                  # noqa: E402

import torch                                                     # noqa: E402

from learnlab import step1                                       # noqa: E402
from learnlab.tokenizer import Tokenizer                         # noqa: E402
from premonition import data as pdata                            # noqa: E402
from premonition.batch import N_ENT                              # noqa: E402

LENGTH = 2048


def village_or_skip() -> None:
    try:
        from learnlab.village.render import PatternSource  # noqa: F401
    except ImportError as error:
        raise unittest.SkipTest(f"village simulator not available: {error}")


class AlignedRowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from learnlab.village.names import SYLLABLES
        from learnlab.village.shards import write_shards
        village_or_skip()
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        write_shards("train", 32, root / "d", 1, seed=0, visits_per_shard=16, verbose=False)
        texts = [text.read_text(encoding="utf-8") for text, _ in step1.shard_files(root / "d" / "train")]
        cls.tokenizer = Tokenizer.train(texts, vocab_size=1200, syllables=SYLLABLES)
        cls.detector = pdata.fit_detector(root / "d" / "train")
        cls.plain = pdata.build_cache(root / "d" / "train", cls.tokenizer, None)
        cls.pointer = pdata.build_cache(root / "d" / "train", cls.tokenizer, cls.detector)
        cls.eos = cls.tokenizer.token_to_id("<eos>")
        cls.root = root

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def stream(self, kind: str, *, seed: int = 0, length: int = LENGTH) -> ablation.AlignedVisitStream:
        cache = self.pointer if kind == "E" else self.plain
        return ablation.AlignedVisitStream(cache, eos=self.eos, length=length, seed=seed,
                                           pointer=kind == "E")

    # ------------------------------------------------------------------ row shape

    def test_rows_are_exactly_length_and_bounded_by_eos(self) -> None:
        stream = self.stream("E")
        rows = [next(stream) for _ in range(len(self.pointer))]
        self.assertEqual(len(rows), len(self.pointer))
        for tokens, mask in rows:
            self.assertEqual(tokens.shape, (LENGTH,))
            self.assertEqual(mask.shape, (LENGTH,))
            self.assertEqual(tokens.dtype, torch.long)
            self.assertEqual(mask.dtype, torch.bool)
            self.assertEqual(int(tokens[0]), self.eos, "a row must start at a visit start")
        self.assertEqual(stream.truncated_visits, 0, "2048 should hold these visits whole")
        for tokens, _ in rows:
            self.assertEqual(int(tokens[-1]), self.eos, "an untruncated row ends in <eos> padding")

    def test_the_visit_is_wrapped_in_two_eos_and_the_rest_is_padding(self) -> None:
        stream = self.stream("E")
        for _ in range(len(self.pointer)):
            tokens, mask = next(stream)
            kept = int(mask.sum())
            self.assertGreater(kept, 2)
            self.assertEqual(int(tokens[0]), self.eos)
            self.assertEqual(int(tokens[kept - 1]), self.eos, "the visit's own closing <eos>")
            # The mask is a prefix: True over the visit, False over every padding position.
            self.assertTrue(bool(mask[:kept].all()))
            self.assertFalse(bool(mask[kept:].any()))
            self.assertTrue(bool((tokens[kept:] == self.eos).all()), "padding is <eos>")
            # The visit between the two <eos> markers is as long as the cache says it is.
            self.assertEqual(kept - 2, self.pointer.visit_tokens(stream.order_log[-1]).numel())
        self.assertEqual(len(stream.order_log), len(self.pointer))

    def test_truncation_is_counted_and_fills_the_row(self) -> None:
        short = 64
        stream = self.stream("E", length=short)
        rows = [next(stream) for _ in range(len(self.pointer))]
        self.assertGreater(stream.truncated_visits, 0, "64 tokens must cut a real village visit")
        for tokens, mask in rows:
            self.assertEqual(tokens.shape, (short,))
            self.assertEqual(int(tokens[0]), self.eos)
        truncated = [(t, m) for t, m in rows if bool(m.all())]
        self.assertEqual(len(truncated), stream.truncated_visits)
        for tokens, mask in truncated:
            self.assertTrue(bool(mask.all()), "a cut visit fills the whole row; nothing is padding")

    # ------------------------------------------------------------------ entity ids

    def test_entity_ids_are_in_range_and_only_in_the_pointer_arm(self) -> None:
        base = self.tokenizer.vocab_size
        pointer = self.stream("E")
        seen = set()
        for _ in range(len(self.pointer)):
            tokens, mask = next(pointer)
            ids = tokens[mask]
            self.assertTrue(bool((ids >= 0).all()))
            self.assertTrue(bool((ids < base + N_ENT).all()), "an id past the entity block")
            seen.update(int(i) - base for i in ids[ids >= base].tolist())
        self.assertTrue(seen, "the pointerized arm must actually emit entity ids")
        self.assertTrue(seen <= set(range(N_ENT)))
        plain = self.stream("A")
        for _ in range(len(self.plain)):
            tokens, mask = next(plain)
            self.assertTrue(bool((tokens[mask] < base).all()), "the A arm never emits an entity id")

    def test_each_visit_gets_a_fresh_entity_numbering(self) -> None:
        """Two seeds must number the same visit differently (that is what E is trained to be robust to)."""
        first = {index: row for index, row in self.by_visit(self.stream("E", seed=0)).items()}
        second = {index: row for index, row in self.by_visit(self.stream("E", seed=1)).items()}
        base = self.tokenizer.vocab_size
        differing = 0
        for index in first:
            a, b = first[index], second[index]
            ents_a = [int(i) for i in a.tolist() if i >= base]
            ents_b = [int(i) for i in b.tolist() if i >= base]
            self.assertEqual(len(ents_a), len(ents_b), "the same visit has the same number of mentions")
            differing += ents_a != ents_b
        self.assertGreater(differing, 0, "the entity order must be re-permuted per visit")

    def by_visit(self, stream) -> dict:
        out = {}
        for _ in range(len(stream.cache)):
            tokens, mask = next(stream)
            out[stream.order_log[-1]] = tokens[mask]
        return out

    # ------------------------------------------------------------------ the pairing

    def test_a_and_e_walk_the_same_visits_in_the_same_order(self) -> None:
        for seed in (0, 1):
            plain, pointer = self.stream("A", seed=seed), self.stream("E", seed=seed)
            for _ in range(2 * len(self.plain) + 3):        # past the first epoch boundary
                next(plain)
                next(pointer)
            self.assertEqual(plain.order_log, pointer.order_log, f"seed {seed}")
            self.assertEqual(len(set(plain.order_log[:len(self.plain)])), len(self.plain),
                             "one epoch visits every visit exactly once")

    def test_the_two_caches_describe_the_same_visits(self) -> None:
        self.assertEqual(self.plain.visit_ids, self.pointer.visit_ids)
        self.assertEqual(len(self.plain), len(self.pointer))

    def test_pointerizing_never_makes_a_visit_longer(self) -> None:
        longer = 0
        for index in range(len(self.plain)):
            plain = self.plain.visit_tokens(index).numel()
            pointer = self.pointer.visit_tokens(index).numel()
            longer += pointer > plain
        self.assertEqual(longer, 0, "one entity id can only be shorter than a spelled-out name")

    # ------------------------------------------------------------------ the A arm is ordinary step-1 text

    def test_the_plain_cache_matches_step1s_own_encoding(self) -> None:
        text, _ = step1.shard_files(self.root / "d" / "train")[0]
        visits = step1.read_visits(text)
        for index, visit in enumerate(visits[:8]):
            expected = step1.encode_visit(self.tokenizer, [line for _, line in visit], self.eos)
            got = self.plain.visit_tokens(index).tolist() + [self.eos]
            self.assertEqual(got, expected, f"visit {index}")

    def test_a_row_equals_step1s_aligned_row_for_the_same_visit(self) -> None:
        """The A arm's row is exactly the row `step1.stream_for(..., align=(length, eos))` would build."""
        text, _ = step1.shard_files(self.root / "d" / "train")[0]
        visit = step1.read_visits(text)[0]
        ids = step1.encode_visit(self.tokenizer, [line for _, line in visit], self.eos)
        expected = torch.full((LENGTH,), self.eos, dtype=torch.long)
        expected[0] = self.eos
        expected[1:1 + len(ids)] = torch.tensor(ids, dtype=torch.long)
        stream = self.stream("A")
        rows = {}
        for _ in range(len(self.plain)):
            tokens, mask = next(stream)
            rows[stream.order_log[-1]] = (tokens, mask)
        tokens, mask = rows[0]
        self.assertTrue(torch.equal(tokens, expected))
        self.assertEqual(int(mask.sum()), 1 + len(ids))


class ArgumentTest(unittest.TestCase):

    def test_parse_arms(self) -> None:
        self.assertEqual(ablation.parse_arms("A:0,E:0,A:1,E:1"),
                         [("A", 0), ("E", 0), ("A", 1), ("E", 1)])
        self.assertEqual(ablation.parse_arms("A"), [("A", 0)])
        with self.assertRaises(SystemExit):
            ablation.parse_arms("D:0")

    def test_the_arms_share_the_contender_spec(self) -> None:
        from premonition import contenders
        a, e = contenders.contender("A"), contenders.contender("E")
        self.assertEqual(a.shape, e.shape)
        self.assertEqual(a.lr, e.lr)
        self.assertEqual((a.inputs, e.inputs), ("plain", "pointer"))

    def test_e_gets_the_entity_ids_and_a_does_not(self) -> None:
        from premonition import contenders
        plain = contenders.core_config("A", 1000, context=LENGTH)
        pointer = contenders.core_config("E", 1000, context=LENGTH)
        self.assertEqual(plain.vocab_size, 1000)
        self.assertEqual(pointer.vocab_size, 1000 + N_ENT)
        self.assertEqual((plain.context, pointer.context), (LENGTH, LENGTH))
        self.assertEqual((plain.d_model, plain.n_layers, plain.n_heads),
                         (pointer.d_model, pointer.n_layers, pointer.n_heads))


if __name__ == "__main__":
    unittest.main()
