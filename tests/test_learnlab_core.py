"""Plain core learner: model, streaming trainer and checkpoints (CPU, tiny sizes)."""
from __future__ import annotations

import math
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import torch

from learnlab.ckpt import CheckpointError, load_checkpoint, read_config, save_checkpoint
from learnlab.core import Core, CoreConfig, lm_loss
from learnlab.readonly import ReadOnlyViolation
from learnlab.train import MemoryGuardError, TrainConfig, Trainer, pattern_stream
from memorylab.storage import Budget, BudgetError

VOCAB, CONTEXT = 16, 32


class Payload:
    """An arbitrary object that a weights-only load must refuse to unpickle."""


def tiny_core(seed: int = 0) -> Core:
    torch.manual_seed(seed)
    return Core(CoreConfig(vocab_size=VOCAB, context=CONTEXT, d_model=32, n_layers=2, n_heads=2))


def tiny_trainer(seed: int = 0, **overrides) -> Trainer:
    settings = dict(batch=4, seq_len=CONTEXT, lr=3e-3, log_every=10)
    settings.update(overrides)
    return Trainer(tiny_core(seed), TrainConfig(**settings), "cpu")


def pattern_tokens(count: int, seed: int = 0) -> torch.Tensor:
    stream = pattern_stream(VOCAB, seed, chunk=16)
    tokens = torch.cat([next(stream) for _ in range(count // (16 * 17) + 1)])
    return tokens[:count]


class CoreModelTest(unittest.TestCase):
    def test_presets_match_the_scale_plan(self) -> None:
        expected = {"4M": (3.5e6, 4.5e6), "28M": (25e6, 30e6), "90M": (85e6, 95e6)}
        for size, (low, high) in expected.items():
            with torch.device("meta"):
                model = Core(CoreConfig.preset(size, vocab_size=2048, context=512))
            self.assertTrue(low < model.num_parameters() < high, (size, model.num_parameters()))
        with self.assertRaises(ValueError):
            CoreConfig.preset("7B", vocab_size=2048, context=512)

    def test_shapes_and_tied_embeddings(self) -> None:
        model = tiny_core()
        tokens = torch.randint(0, VOCAB, (3, CONTEXT))
        self.assertEqual(tuple(model(tokens).shape), (3, CONTEXT, VOCAB))
        vocab_sized = [n for n, p in model.named_parameters() if VOCAB in p.shape]
        self.assertEqual(vocab_sized, ["embed.weight"])
        with self.assertRaises(ValueError):
            model(torch.zeros(1, CONTEXT + 1, dtype=torch.long))

    def test_future_tokens_do_not_affect_earlier_logits(self) -> None:
        model = tiny_core().eval()
        tokens = torch.randint(0, VOCAB, (2, CONTEXT))
        changed = tokens.clone()
        changed[:, 20:] = (changed[:, 20:] + 1) % VOCAB
        with torch.no_grad():
            before, after = model(tokens), model(changed)
        torch.testing.assert_close(before[:, :20], after[:, :20], rtol=0, atol=1e-6)
        self.assertFalse(torch.allclose(before[:, 20:], after[:, 20:]))

    def test_loss_mask_and_ignore_index(self) -> None:
        logits = torch.randn(2, 5, VOCAB)
        targets = torch.randint(0, VOCAB, (2, 5))
        mask = torch.tensor([[1, 0, 1, 1, 0], [0, 0, 1, 0, 1]], dtype=torch.bool)
        expected = torch.nn.functional.cross_entropy(logits[mask], targets[mask])
        torch.testing.assert_close(lm_loss(logits, targets, mask), expected)
        torch.testing.assert_close(lm_loss(logits, targets.masked_fill(~mask, -100)), expected)
        self.assertEqual(lm_loss(logits, targets, torch.zeros_like(mask)).item(), 0.0)


class TrainerTest(unittest.TestCase):
    def test_loss_decreases_on_pattern_stream(self) -> None:
        trainer = tiny_trainer(batch=8, log_every=20)
        summary = trainer.train(pattern_stream(VOCAB, 0, chunk=32), max_tokens=8 * CONTEXT * 300)
        losses = [record["loss"] for record in trainer.history]
        self.assertEqual(summary["stop"], "max_tokens")
        self.assertLess(losses[-1], losses[0] - 1.0)
        self.assertLess(summary["final_loss"], math.log(VOCAB - 1) - 0.5)  # below unigram level
        for key in ("tokens_per_s", "grad_norm", "weight_norm", "dead_mlp_fraction", "lr"):
            self.assertIn(key, trainer.history[0])
        self.assertTrue(0.0 <= trainer.history[0]["dead_mlp_fraction"] <= 1.0)

    def test_one_optimizer_step_per_microbatch_and_every_token_a_target_once(self) -> None:
        trainer = tiny_trainer()
        per_step = 4 * CONTEXT
        stream = pattern_tokens(3 * per_step + 1 + 50)
        sizes = [1, 7, 100, 3, 200, 13]
        items, start = [], 0
        while start < len(stream):
            size = sizes[len(items) % len(sizes)]
            items.append(stream[start:start + size].tolist())
            start += size
        steps = []
        trainer.optimizer.register_step_post_hook(lambda *_: steps.append(1))
        seen_inputs, seen_targets = [], []
        next_batch = trainer._next_batch

        def recording(source):
            batch = next_batch(source)
            if batch is not None:
                seen_inputs.append(batch[0].reshape(-1))
                seen_targets.append(batch[1].reshape(-1))
            return batch

        with mock.patch.object(trainer, "_next_batch", recording):
            summary = trainer.train(iter(items))
        self.assertEqual(summary["stop"], "stream ended")
        self.assertEqual((len(steps), trainer.step, summary["steps"]), (3, 3, 3))
        self.assertEqual(trainer.tokens, 3 * per_step)
        self.assertTrue(torch.equal(torch.cat(seen_inputs), stream[:3 * per_step]))
        self.assertTrue(torch.equal(torch.cat(seen_targets), stream[1:3 * per_step + 1]))
        self.assertEqual(trainer.state_dict()["carry_tokens"].tolist(),
                         stream[3 * per_step:].tolist())

    def test_max_tokens_is_never_exceeded(self) -> None:
        trainer = tiny_trainer()
        summary = trainer.train(pattern_stream(VOCAB), max_tokens=4 * CONTEXT * 2 + 5)
        self.assertEqual((summary["steps"], summary["tokens"]), (2, 4 * CONTEXT * 2))

    def test_masked_positions_are_not_trained(self) -> None:
        per_step = 4 * CONTEXT
        tokens = pattern_tokens(per_step + 1)
        # The last target of a microbatch feeds no other prediction in it, so
        # changing it can only matter through its own loss term.
        other = tokens.clone()
        other[-1] = (other[-1] + 5) % VOCAB
        mask = torch.ones(per_step + 1, dtype=torch.bool)
        mask[-1] = False

        def trained(stream_tokens, stream_mask):
            trainer = tiny_trainer()
            item = stream_tokens if stream_mask is None else (stream_tokens, stream_mask)
            trainer.train([item])
            self.assertEqual(trainer.step, 1)
            return [p.detach().clone() for p in trainer.model.parameters()]

        masked = zip(trained(tokens, mask), trained(other, mask))
        self.assertTrue(all(torch.equal(a, b) for a, b in masked))
        unmasked = zip(trained(tokens, None), trained(other, None))
        self.assertFalse(all(torch.equal(a, b) for a, b in unmasked))

    def test_memory_guard_aborts_after_first_step(self) -> None:
        trainer = tiny_trainer(memory_limit_bytes=1024)
        with mock.patch("learnlab.train.reserved_bytes", return_value=4096):
            with self.assertRaises(MemoryGuardError) as caught:
                trainer.train(pattern_stream(VOCAB), max_tokens=4 * CONTEXT * 10)
        self.assertEqual(trainer.step, 1)
        self.assertIn("exceeds", str(caught.exception))
        self.assertEqual((caught.exception.peak, caught.exception.limit), (4096, 1024))
        with mock.patch("learnlab.train.reserved_bytes", return_value=512):
            trainer.train(pattern_stream(VOCAB), max_tokens=4 * CONTEXT * 3)
        self.assertEqual(trainer.step, 4)

    def test_eval_hook_is_read_only(self) -> None:
        trainer = tiny_trainer(eval_every=2)
        probe = torch.randint(0, VOCAB, (1, CONTEXT))
        trainer.train(pattern_stream(VOCAB), max_tokens=4 * CONTEXT * 4,
                      evaluate=lambda model: model(probe).mean().item())
        evals = [record for record in trainer.history if "eval" in record]
        self.assertEqual([record["step"] for record in evals], [2, 4])
        self.assertTrue(trainer.model.training)

        def mutating(model):
            with torch.no_grad():
                model.pos.add_(1.0)

        with self.assertRaises(ReadOnlyViolation):
            trainer.evaluate(mutating)
        with self.assertRaises(ReadOnlyViolation):
            tiny_trainer(eval_every=1).train(pattern_stream(VOCAB), max_tokens=4 * CONTEXT,
                                             evaluate=mutating)


class CheckpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.budget = Budget(self.directory.name, hard=200_000_000, steady=150_000_000,
                             free_floor=0)

    def test_round_trip_is_bit_exact_and_resumes_training(self) -> None:
        stream = pattern_stream(VOCAB, 1, chunk=5)
        first = tiny_trainer(seed=0)
        first.train(stream, max_tokens=4 * CONTEXT * 3)
        config = {"core": {"vocab_size": VOCAB}, "note": "test"}
        path = save_checkpoint(self.budget, "ckpt/a", model=first.model, config=config,
                               optimizer=first.optimizer, trainer_state=first.state_dict())
        self.assertEqual(sorted(p.name for p in path.iterdir()),
                         ["config.json", "manifest.json", "state.pt"])
        self.assertEqual(read_config(path), config)

        second = tiny_trainer(seed=1)
        loaded = load_checkpoint(path, second.model, optimizer=second.optimizer)
        second.load_state_dict(loaded["trainer"])
        self.assertEqual(loaded["config"], config)
        probe = torch.randint(0, VOCAB, (2, CONTEXT))
        first.model.eval()
        second.model.eval()
        with torch.no_grad():
            self.assertTrue(torch.equal(first.model(probe), second.model(probe)))
        self.assertEqual((second.step, second.tokens), (first.step, first.tokens))

        rest = [next(stream) for _ in range(12)]
        first.train(iter(rest))
        second.train(iter(rest))
        self.assertEqual(second.step, first.step)
        for a, b in zip(first.model.parameters(), second.model.parameters()):
            self.assertTrue(torch.equal(a, b))

    def test_no_clobber_and_tamper_detection(self) -> None:
        trainer = tiny_trainer()
        save_checkpoint(self.budget, "ckpt/b", model=trainer.model, config={})
        with self.assertRaises(CheckpointError):
            save_checkpoint(self.budget, "ckpt/b", model=trainer.model, config={})
        with self.assertRaises(BudgetError):  # the per-file guard also refuses
            self.budget.atomic_write("ckpt/b/state.pt", 10, lambda handle: handle.write(b"x"))
        state = Path(self.directory.name, "ckpt/b/state.pt")
        data = bytearray(state.read_bytes())
        data[len(data) // 2] ^= 0xFF
        state.write_bytes(bytes(data))
        with self.assertRaises(CheckpointError):
            load_checkpoint(state.parent, tiny_core())
        with self.assertRaises(CheckpointError):
            load_checkpoint(Path(self.directory.name, "ckpt/missing"), tiny_core())
        path = save_checkpoint(self.budget, "ckpt/c", model=trainer.model, config={})
        with self.assertRaises(CheckpointError):  # saved without optimizer state
            load_checkpoint(path, tiny_core(), optimizer=trainer.optimizer)

    def test_load_refuses_pickled_objects(self) -> None:
        trainer = tiny_trainer()
        path = save_checkpoint(self.budget, "ckpt/d", model=trainer.model, config={},
                               trainer_state={"object": Payload()})
        with self.assertRaises(CheckpointError):
            load_checkpoint(path, tiny_core())


if __name__ == "__main__":
    unittest.main()
