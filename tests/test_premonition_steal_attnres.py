"""Steal 3, `loop_attnres`: each loop's registers are a softmax mix of every earlier loop's
(design/steals-2026-10-17/SPEC.md section 3)."""
from __future__ import annotations

import unittest

import torch

from tests.test_premonition_model import eager, synthetic_batch, tiny_config, tiny_model


def start(model, batch):
    """(episode, store) of every question of `batch`, before any loop."""
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    return model._start(batch, hidden, store, model._mentions(batch)), store


def run_loops(model, episode, store, steps: int, index=None) -> None:
    index = torch.arange(episode.x.shape[0]) if index is None else index
    for step in range(steps):
        model._step(episode, index, step, store)


class LoopAttnResTest(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = synthetic_batch(visits=2, lines=24, seed=5)
        self.model = tiny_model(loop_attnres=True)
        self.count = self.batch.q_visit.shape[0]
        self.assertGreater(self.count, 2)

    def test_parameter_exists_only_under_the_flag_and_starts_at_zero(self) -> None:
        config = self.model.config
        self.assertEqual(tuple(self.model.think.loop_query.shape), (config.max_loops, config.d_model))
        self.assertEqual(float(self.model.think.loop_query.abs().sum()), 0.0)
        self.assertIsNone(tiny_model().think.loop_query)

    def test_history_starts_as_the_initial_registers(self) -> None:
        episode, _ = start(self.model, self.batch)
        self.assertEqual(len(episode.history), 1)
        self.assertEqual(tuple(episode.history[0].shape),
                         (self.count, self.model.config.registers, self.model.config.d_model))
        self.assertTrue(torch.equal(episode.history[0], episode.x[:, self.model._register_base:]))
        self.assertIsNone(start(tiny_model(), self.batch)[0].history)

    def test_loop_zero_is_unchanged(self) -> None:
        episode, store = start(self.model, self.batch)
        index = torch.arange(self.count)
        self.assertTrue(torch.equal(self.model._loop_input(episode, index, 0), episode.x[index]))
        model = self.model
        with torch.no_grad():
            model.think.loop_query.normal_()
        self.assertTrue(torch.equal(model._loop_input(episode, index, 0), episode.x[index]))

    def test_zero_query_mixes_the_mean_of_the_registers_so_far(self) -> None:
        episode, store = start(self.model, self.batch)
        run_loops(self.model, episode, store, 3)
        self.assertEqual(len(episode.history), 4)                      # v_0 .. v_3
        base = self.model._register_base
        index = torch.arange(self.count)
        for step in (1, 2, 3):
            mixed = self.model._loop_input(episode, index, step)
            expected = torch.stack([v[index] for v in episode.history[:step + 1]]).mean(0)
            torch.testing.assert_close(mixed[:, base:], expected, rtol=1e-5, atol=1e-6)
            # Only the registers are mixed: question, slot and card rows pass through.
            self.assertTrue(torch.equal(mixed[:, :base], episode.x[index][:, :base]))

    def test_the_last_history_entry_is_the_current_registers(self) -> None:
        episode, store = start(self.model, self.batch)
        run_loops(self.model, episode, store, 2)
        self.assertTrue(torch.equal(episode.history[-1], episode.x[:, self.model._register_base:]))

    def test_a_nonzero_query_weights_by_softmax_of_the_normed_states(self) -> None:
        model = self.model
        with torch.no_grad():
            model.think.loop_query.normal_(std=2.0)
        episode, store = start(model, self.batch)
        run_loops(model, episode, store, 2)
        index = torch.arange(self.count)
        mixed = model._loop_input(episode, index, 2)[:, model._register_base:]
        past = torch.stack(episode.history[:3])                                   # [3, Q, R, d]
        normed = torch.nn.functional.layer_norm(past, (past.shape[-1],))
        alpha = torch.softmax((normed * model.think.loop_query[2]).sum(-1), dim=0)  # per question and register
        self.assertGreater(float((alpha - 1 / 3).abs().max().detach()), 0.01)
        torch.testing.assert_close(mixed, (alpha.unsqueeze(-1) * past).sum(0), rtol=1e-5, atol=1e-6)

    def test_questions_that_stopped_early_keep_their_history(self) -> None:
        episode, store = start(self.model, self.batch)
        everyone = torch.arange(self.count)
        self.model._step(episode, everyone, 0, store)
        survivors = everyone[:2]                                                  # the rest stop after loop 1
        self.model._step(episode, survivors, 1, store)
        self.model._step(episode, survivors, 2, store)
        self.assertEqual(len(episode.history), 4)
        stopped = everyone[2:]
        for t in (2, 3):                                                          # carried, not re-mixed
            self.assertTrue(torch.equal(episode.history[t][stopped], episode.history[1][stopped]))
        for t in (2, 3):                                                          # survivors moved on
            self.assertFalse(torch.equal(episode.history[t][survivors], episode.history[t - 1][survivors]))
        # The entry for loop t holds each running question's own state after its loop t - 1.
        self.assertTrue(torch.equal(episode.history[3][survivors],
                                    episode.x[survivors][:, self.model._register_base:]))
        self.assertTrue(torch.equal(episode.x[stopped][:, self.model._register_base:],
                                    episode.history[1][stopped]))

    def test_answer_path_with_different_stopping_loops_carries_history(self) -> None:
        model = eager(self.model)
        stops = torch.arange(self.count) % 3 + 1                                  # question q halts after this loop
        step_original, start_original = model._step, model._start
        seen = {}

        def step(episode, index, step_no, store):
            rows, halt, ask, scores = step_original(episode, index, step_no, store)
            return rows, torch.where(step_no + 1 >= stops[index], 10.0, -10.0), ask, scores

        def spy(*args):
            seen["episode"] = start_original(*args)
            return seen["episode"]

        model._step, model._start = step, spy
        try:
            answers = model.answer(self.batch)
        finally:
            del model._step, model._start
        self.assertEqual(answers.loops.tolist(), stops.tolist())
        history = seen["episode"].history
        self.assertEqual(len(history), 4)
        for q, used in enumerate(stops.tolist()):
            for t in range(used, len(history)):
                self.assertTrue(torch.equal(history[t][q], history[used][q]), (q, used, t))

    def test_gradient_reaches_loop_query(self) -> None:
        out = self.model(self.batch, mode="teacher", generator=torch.Generator().manual_seed(0))
        out["loss"].backward()
        grad = self.model.think.loop_query.grad
        self.assertIsNotNone(grad)
        self.assertTrue(torch.isfinite(grad).all())
        self.assertGreater(float(grad[1:].abs().sum()), 0.0)
        self.assertEqual(float(grad[0].abs().sum()), 0.0)                         # loop 0 never mixes

    def test_changing_the_query_changes_the_loss(self) -> None:
        def loss() -> float:
            return float(self.model(self.batch, mode="teacher", generator=torch.Generator().manual_seed(0))["loss"].detach())

        base = loss()
        with torch.no_grad():
            self.model.think.loop_query.normal_(std=3.0)
        self.assertNotEqual(loss(), base)

    def test_controls_and_forward_modes_run(self) -> None:
        for variant in ("D", "D-noask", "D-noptr"):
            model = tiny_model(variant, loop_attnres=True)
            for mode in ("gold", "teacher", "own"):
                out = model(self.batch, mode=mode, p_own=0.5, generator=torch.Generator().manual_seed(1))
                self.assertTrue(torch.isfinite(out["loss"]), (variant, mode))
            model.answer(self.batch)


if __name__ == "__main__":
    unittest.main()
