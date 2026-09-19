"""Premonition-mini training (design/06 §3-4, §7-9; build steps 4-6): curriculum, FLOP stop, label-free
reader stream, card diagnostics, checkpoints and the far-fact toy.

The toy-accuracy gate (D >= 95%, D-noask <= chance + 5 points) is NOT met yet: see
design/research/2026-09-18-trainer-handoff.md. It runs only with PREMONITION_SLOW=1, and then it fails
loudly rather than being weakened.
"""
from __future__ import annotations

import os
import random
import tempfile
import unittest
from pathlib import Path

import torch

from premonition.batch import N_ENT
from premonition.config import MiniConfig
from premonition.model import PremonitionMini
from premonition.toy import ANSWER, NEWLINE, QUESTION, ToySpec, make_batch, min_distance, toy_stream
from premonition.train import (Curriculum, InsertLog, MiniTrainer, budget_for_steps, card_stats, checkpoint_config,
                               entity_text, label_free, load_mini, mini_train_config, planned_loops,
                               save_mini_checkpoint, train_toy, validate)

SPEC = ToySpec()


def tiny(variant: str = "D", seed: int = 0) -> PremonitionMini:
    torch.manual_seed(seed)
    return PremonitionMini(MiniConfig.preset(variant, "tiny", vocab_size=SPEC.vocab_size, window=64))


class CurriculumTest(unittest.TestCase):
    def test_phases_and_p_own(self) -> None:
        c = Curriculum()
        self.assertEqual([c.plan(s).phase for s in (0.0, 0.049, 0.05, 0.299, 0.30, 0.9)],
                         ["gold", "gold", "teacher", "teacher", "own", "own"])
        self.assertEqual(c.plan(0.30).p_own, 0.0)
        self.assertAlmostEqual(c.plan(0.45).p_own, 0.375)
        self.assertAlmostEqual(c.plan(0.60).p_own, 0.75)
        self.assertAlmostEqual(c.plan(0.99).p_own, 0.75)

    def test_planned_loops_match_the_model(self) -> None:
        model, batch = tiny(), label_free(make_batch(SPEC, 3, random.Random(0)))
        for mode in ("gold", "teacher", "own"):
            out = model(batch, mode=mode, p_own=0.5, generator=torch.Generator().manual_seed(0))
            self.assertEqual(int(out["metrics"]["question_loops"]), int(planned_loops(batch, mode, model.config).sum()))


class ToyAndLabelFreeTest(unittest.TestCase):
    def test_toy_questions_are_beyond_attention_reach(self) -> None:
        batch = make_batch(SPEC, 8, random.Random(1))
        self.assertGreaterEqual(min_distance(batch), 2 * 64)
        self.assertTrue(bool((batch.line_ents[batch.q_visit, batch.gold_lines[:, 0], 0] >= 0).all()))

    def test_label_free_drops_every_answer_span(self) -> None:
        batch = make_batch(SPEC, 4, random.Random(2))
        free = label_free(batch)
        for q in range(free.size[2]):
            row, (start, end) = int(free.q_visit[q]), free.q_span[q].tolist()
            self.assertEqual(int(free.tokens[row, start]), QUESTION)
            self.assertEqual(int(free.tokens[row, end - 1]), ANSWER)
            self.assertEqual(int(free.tokens[row, end]), NEWLINE)               # nothing of the answer follows
            self.assertFalse(bool(free.lm_mask[row, end - 1]))
            self.assertEqual(free.tokens[row, start:end].tolist(), batch.tokens[row, batch.q_span[q, 0]:batch.q_span[q, 1]].tolist())
        for row in range(free.size[0]):
            size = int(free.lengths[row])
            kept = free.line_of[row, :size]
            self.assertEqual(torch.unique_consecutive(kept).tolist(), list(range(int((free.line_start[row] >= 0).sum()))))
            ends = torch.nonzero(free.card_end[row]).flatten()
            self.assertTrue(bool((free.tokens[row, ends] == NEWLINE).all()))
            self.assertFalse(bool(free.line_is_question[row, free.line_of[row, ends]].any()))
        self.assertLess(int(free.lengths.sum()), int(batch.lengths.sum()))
        out = tiny()(free, mode="teacher", generator=torch.Generator().manual_seed(0))
        self.assertEqual(int(out["metrics"]["gold_missing"]), 0)

    def test_unknown_entities_are_wrong_not_errors(self) -> None:
        from learnlab.tokenizer import Tokenizer
        from premonition.batch import NameTable
        tokenizer = Tokenizer.train(["[world] the kite is red.\n"], vocab_size=300)
        text = entity_text([tokenizer.vocab_size + 5], NameTable({0: "Kelo"}), tokenizer)
        self.assertEqual(text, "<ent5>")


class CardStatsTest(unittest.TestCase):
    def test_fifo_eviction_and_early_weight_are_counted(self) -> None:
        batch = make_batch(SPEC, 1, random.Random(3))
        batch.gold_lines[0, :12] = torch.arange(12)          # |G| = 12 for question 0
        # Three teacher fetches of 4 gold + 2 distractors = 18 inserts > 16 rows: gold lines 0-1 are evicted.
        calls = [(torch.tensor([0]), torch.tensor([[0, 1, 2, 3, 20, 21]])),
                 (torch.tensor([0]), torch.tensor([[4, 5, 6, 7, 22, 23]])),
                 (torch.tensor([0]), torch.tensor([[8, 9, 10, 11, 24, -1]]))]
        loops = torch.tensor([6] + [4] * (batch.size[2] - 1))
        stats = card_stats(calls, batch, loops, 16, offset=1)
        self.assertEqual(stats["overflow"], 1)
        self.assertEqual(stats["gold_evicted"], 1)
        self.assertEqual(stats["full_gold"], 1)
        self.assertEqual(stats["big_gold"], 1)
        # question 0 has every gold card from loop 3 on: loops 0-2 at the early weight; the others never do.
        self.assertEqual(stats["early_terms"], 3 + 4 * (batch.size[2] - 1))

    def test_insert_log_leaves_the_model_unchanged(self) -> None:
        model, batch = tiny(), label_free(make_batch(SPEC, 2, random.Random(4)))
        with InsertLog(model) as log:
            model(batch, mode="teacher", generator=torch.Generator().manual_seed(0))
        self.assertTrue(log.calls)
        self.assertNotIn("_insert", model.__dict__)


class TrainerTest(unittest.TestCase):
    def test_flop_budget_stop_curriculum_and_checkpoint(self) -> None:
        from learnlab.readonly import read_only
        from memorylab.storage import Budget
        model = tiny()
        trainer = MiniTrainer(model, mini_train_config(lr=1e-3, warmup_steps=5, log_every=5), "cpu",
                              flop_budget=1.0, seed=0)
        stream = (label_free(b) for b in toy_stream(SPEC, 4, 0))
        head = [next(stream) for _ in range(2)]
        fit = trainer.calibrate(head)
        self.assertLess(fit.worst, 0.15)
        trainer.flop_budget = budget_for_steps(trainer, head, 30)
        report = trainer.train(head + [next(stream) for _ in range(200)])
        self.assertEqual(report["stop"], "flop budget")
        self.assertTrue(report["budget_ok"], report["flops_share"])
        self.assertEqual(report["loop_mismatches"], 0)
        self.assertEqual(list(report["phases"]), ["gold", "teacher", "own"])
        logged = [r for r in trainer.history if "eval" not in r]
        for key in ("lm", "ask", "ans", "halt", "gold_recall_at_4", "loops_per_question", "tokens_per_s", "flops"):
            self.assertIn(key, logged[-1])
        self.assertTrue(any("cards" in r for r in logged))
        held_out = [label_free(make_batch(SPEC, 4, random.Random(9)))]
        result = trainer.evaluate(lambda m: validate(m, held_out))
        for key in ("accuracy", "accuracy_gold_cards", "gold_recall_at_4", "random_recall_at_4", "cards"):
            self.assertIn(key, result)
        with tempfile.TemporaryDirectory() as folder:
            budget = Budget(Path(folder), hard=10_000_000_000, steady=8_000_000_000)
            config = checkpoint_config(trainer, contender="D", tokenizer={"path": "toy", "sha256": "t" * 64},
                                       detector="d" * 64, data={"dir": "toy", "tag": "toy"})
            save_mini_checkpoint(budget, "ck/D", trainer, config)
            loaded, saved, state = load_mini(Path(folder) / "ck" / "D")
            self.assertEqual(saved["tokenizer"]["sha256"], "t" * 64)
            self.assertEqual(saved["detector"]["sha256"], "d" * 64)
            self.assertEqual(saved["data"]["tag"], "toy")
            self.assertAlmostEqual(state["flops"], trainer.flops)
            with read_only(loaded):
                again = loaded.answer(held_out[0])
            self.assertTrue(torch.equal(again.tokens, model.answer(held_out[0]).tokens))


class SmokeTest(unittest.TestCase):
    def test_cpu_smoke_on_a_tiny_village(self) -> None:
        try:
            import learnlab.village.shards  # noqa: F401
        except ImportError as error:
            raise unittest.SkipTest(f"village simulator not available: {error}")
        from premonition.train import smoke
        report = smoke(steps=40, log=lambda _line: None)
        self.assertTrue(report["passed"], report["checks"])
        self.assertLess(report["seconds"], 300)


@unittest.skipUnless(os.environ.get("PREMONITION_SLOW") == "1", "slow toy gate; currently failing (see the handoff)")
class ToyGateTest(unittest.TestCase):
    """Build step 4's pass condition, unweakened."""

    def test_d_learns_far_facts_and_noask_does_not(self) -> None:
        d = train_toy("D", steps=int(os.environ.get("PREMONITION_TOY_STEPS", "1500")), lr=1e-3, warmup_steps=100)
        noask = train_toy("D-noask", steps=300, lr=1e-3, warmup_steps=100)
        self.assertGreaterEqual(d["validation"]["accuracy"], 0.95)
        self.assertLessEqual(noask["validation"]["accuracy"], SPEC.chance + 0.05)


if __name__ == "__main__":
    unittest.main()
