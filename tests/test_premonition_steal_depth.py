"""Steal 5, `row_halt` and `random_depth`: per-register dynamic depth
(design/steals-2026-10-17/SPEC.md section 5)."""
from __future__ import annotations

import math
import unittest

import torch

from premonition.flops import FlopFit
from premonition.model import _norm
from premonition.train import Curriculum, MiniTrainer, mini_train_config, planned_loops
from tests.test_premonition_model import eager, synthetic_batch, tiny_config, tiny_model


def start(model, batch):
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    return model._start(batch, hidden, store, model._mentions(batch)), store


def capture_episode(model) -> dict:
    """Make `model._start` remember its episode in the returned dict (undo with `release`)."""
    seen, original = {}, model._start

    def spy(*args):
        seen["episode"] = original(*args)
        return seen["episode"]

    model._start = spy
    return seen


def release(model) -> None:
    del model._start


class RowHaltTest(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = synthetic_batch(visits=2, lines=24, seed=5)
        self.count = self.batch.q_visit.shape[0]

    def test_router_exists_only_under_the_flag_with_the_open_bias(self) -> None:
        model = tiny_model(row_halt=True)
        self.assertEqual(tuple(model.heads.row_halt.weight.shape), (1, model.config.d_model))
        self.assertTrue(torch.all(model.heads.row_halt.bias == model.config.row_halt_bias))
        self.assertIsNone(tiny_model().heads.row_halt)
        episode, _ = start(model, self.batch)
        self.assertTrue(torch.equal(episode.keep, torch.ones(self.count, model.config.registers)))
        self.assertEqual(episode.ponder, [])
        off = start(tiny_model(), self.batch)[0]
        self.assertIsNone(off.keep)
        self.assertIsNone(off.ponder)

    def test_loop_zero_never_halts(self) -> None:
        model = tiny_model(row_halt=True)
        with torch.no_grad():
            model.heads.row_halt.bias.fill_(20.0)
        episode, store = start(model, self.batch)
        model._step(episode, torch.arange(self.count), 0, store)
        self.assertTrue(torch.equal(episode.keep, torch.ones_like(episode.keep)))
        self.assertEqual(episode.ponder, [])

    def test_keep_is_hard_forward_and_soft_backward(self) -> None:
        """Review round 4, item 2: training and answering share one forward rule (keep is the sticky 0/1 keep); the
        gradient is the soft keep's, so the router still learns."""
        model = tiny_model(row_halt=True)
        with torch.no_grad():
            model.heads.row_halt.bias.fill_(-0.5)                                   # p ~ 0.38: below one half
        episode, _ = start(model, self.batch)
        base = model._register_base
        episode.x = episode.x + torch.randn_like(episode.x) * 0.1
        index = torch.arange(self.count)
        proposed = torch.randn_like(episode.x)
        before = episode.x[:, base:]
        p = torch.sigmoid(model.heads.row_halt(_norm(before)).squeeze(-1))
        self.assertTrue((p < 0.5).all())
        out = model._loop_output(episode, index, 1, proposed)
        self.assertTrue(torch.equal(episode.keep.detach(), torch.ones_like(episode.keep)))   # full update, no damping
        torch.testing.assert_close(out[:, base:], proposed[:, base:])
        self.assertTrue(torch.equal(out[:, :base], proposed[:, :base]))             # other rows are the block's
        episode.keep.sum().backward()                                                # d keep / d p = -1 per register
        expected = -(p * (1 - p)).sum()
        torch.testing.assert_close(model.heads.row_halt.bias.grad[0], expected.detach())
        self.assertEqual(len(episode.ponder), 1)
        self.assertEqual(tuple(episode.ponder[0].shape), (self.count * model.config.registers,))

    def test_a_halted_register_zero_does_not_freeze_the_halt_read(self) -> None:
        """Review round 5, item 1: once register 0 halts, its stored row is frozen, but the question-level HALT
        must keep reading a live state, or a question that halted register 0 early could never finish."""
        model = tiny_model(row_halt=True)
        with torch.no_grad():
            model.heads.row_halt.bias.fill_(20.0)                                  # every register halts at loop 1
        episode, store = start(model, self.batch)
        index = torch.arange(self.count)
        halts = []
        with torch.no_grad():
            for step in range(4):
                rows, halt, ask, scores = model._step(episode, index, step, store)
                halts.append(halt.clone())
        self.assertTrue(torch.equal(episode.halted[:, 0], torch.ones_like(episode.halted[:, 0])))
        self.assertFalse(torch.equal(halts[2], halts[3]))         # the HALT read still moves (frozen before the fix)

    def test_training_and_no_grad_paths_give_the_same_keep_and_rows(self) -> None:
        model = tiny_model(row_halt=True)
        with torch.no_grad():
            model.heads.row_halt.bias.fill_(0.0)
            model.heads.row_halt.weight.normal_(std=2.0)                            # a mix of halting rows
        proposed = torch.randn(self.count, model.config.rows, model.config.d_model)
        results = []
        for grad in (True, False):
            episode, _ = start(model, self.batch)
            with torch.set_grad_enabled(grad):
                rows = model._loop_output(episode, torch.arange(self.count), 1, proposed)
            results.append((episode.keep.detach(), rows.detach()))
        self.assertTrue(torch.equal(results[0][0], results[1][0]))
        self.assertTrue(torch.equal(results[0][1], results[1][1]))
        self.assertTrue((results[0][0] == 0).any() and (results[0][0] == 1).any())

    def test_hard_keep_is_sticky_and_discrete(self) -> None:
        model = tiny_model(row_halt=True)
        episode, _ = start(model, self.batch)
        index = torch.arange(self.count)
        proposed = torch.randn_like(episode.x)
        with torch.no_grad():
            model.heads.row_halt.bias.fill_(-1.0)
        model._loop_output(episode, index, 1, proposed)
        self.assertTrue(torch.equal(episode.keep, torch.ones_like(episode.keep)))   # p ~ 0.27 <= 0.5: keeps going
        with torch.no_grad():
            model.heads.row_halt.bias.fill_(1.0)
        model._loop_output(episode, index, 2, proposed)
        self.assertTrue(torch.equal(episode.keep, torch.zeros_like(episode.keep)))
        with torch.no_grad():
            model.heads.row_halt.bias.fill_(-5.0)
        model._loop_output(episode, index, 3, proposed)
        self.assertTrue(torch.equal(episode.keep, torch.zeros_like(episode.keep)))

    def test_a_forced_halted_register_is_frozen_while_the_other_rows_change(self) -> None:
        model = tiny_model(row_halt=True)
        episode, store = start(model, self.batch)
        index = torch.arange(self.count)
        base = model._register_base
        model._step(episode, index, 0, store)
        before = episode.x.clone()
        with torch.no_grad():                                                      # halt every register
            model.heads.row_halt.bias.fill_(20.0)
        model._step(episode, index, 1, store)
        self.assertTrue(torch.equal(episode.keep, torch.zeros_like(episode.keep)))
        self.assertTrue(torch.equal(episode.x[:, base:], before[:, base:]))
        self.assertFalse(torch.equal(episode.x[:, :base], before[:, :base]))       # question and slot rows still move
        with torch.no_grad():                                                      # sticky: no waking up
            model.heads.row_halt.bias.fill_(-20.0)
        model._step(episode, index, 2, store)
        self.assertTrue(torch.equal(episode.keep, torch.zeros_like(episode.keep)))
        self.assertTrue(torch.equal(episode.x[:, base:], before[:, base:]))

    def test_only_the_halted_registers_freeze(self) -> None:
        model = tiny_model(row_halt=True)
        episode, store = start(model, self.batch)
        index = torch.arange(self.count)
        base = model._register_base
        model._step(episode, index, 0, store)
        before = episode.x.clone()
        # A rank-one router that halts the registers lying on one side of the median along register 0's direction.
        direction = _norm(before[0, base:base + 1])[0]
        score = _norm(before[:, base:]) @ direction
        with torch.no_grad():
            model.heads.row_halt.weight.copy_(direction * 50.0)
            model.heads.row_halt.bias.fill_(-50.0 * float(score.median()))
        model._step(episode, index, 1, store)
        halted = episode.keep == 0
        self.assertTrue(halted.any() and (~halted).any(), "need a mix of halted and live registers")
        after = episode.x[:, base:]
        self.assertTrue(torch.equal(after[halted], before[:, base:][halted]))
        self.assertFalse(torch.equal(after[~halted], before[:, base:][~halted]))

    def test_register_zero_halted_means_no_fetches(self) -> None:
        model = eager(tiny_model(row_halt=True))
        episode, store = start(model, self.batch)
        index = torch.arange(self.count)
        rows, halt, ask, scores = model._step(episode, index, 0, store)
        stop = torch.zeros(self.count, dtype=torch.bool)
        self.assertTrue((model._choose(episode, index, store, scores, ask, stop) >= 0).any())
        episode.halted[:, 0] = True
        self.assertTrue((model._choose(episode, index, store, scores, ask, stop) == -1).all())
        episode.halted[:, 0] = False
        episode.halted[:, 1:] = True                                               # other registers do not matter
        episode.keep[:, 0] = 0.01                                                  # nor does the soft keep itself
        self.assertTrue((model._choose(episode, index, store, scores, ask, stop) >= 0).any())
        episode.halted[:, 0] = True
        episode.halted[0, 0] = False                                               # only question 0 may still ask
        picks = model._choose(episode, index, store, scores, ask, stop)
        self.assertTrue((picks[1:] == -1).all())

    def test_training_and_answering_stop_asking_under_the_same_rule(self) -> None:
        """Review item 3: a router at p = 0.4 never halts register 0 in either path (the soft keep 0.6^t falls below
        one half, but fetching follows the sticky p > 0.5 rule); at p = 0.6 both paths stop after loop 0."""
        for p, halts in ((0.4, False), (0.6, True)):
            model = eager(tiny_model(row_halt=True))               # always ASK, never the question-level HALT
            with torch.no_grad():
                model.heads.row_halt.weight.zero_()
                model.heads.row_halt.bias.fill_(math.log(p / (1 - p)))
            calls = []
            original = model._insert

            def record(episode, store, index, cards):
                calls.append(cards.clone())
                return original(episode, store, index, cards)

            model._insert = record
            model(self.batch, mode="own", p_own=1.0, generator=torch.Generator().manual_seed(0))
            own_later = [bool((c >= 0).any()) for c in calls[1:]]
            del model._insert
            answered = model.answer(self.batch).fetched.sum(1)
            with self.subTest(p=p):
                self.assertTrue(own_later)
                if halts:
                    self.assertFalse(any(own_later))
                    self.assertTrue((answered <= model.config.top_k).all())
                else:
                    self.assertTrue(all(own_later))
                    self.assertGreater(int(answered.max()), model.config.top_k)

    def test_answer_stops_fetching_once_register_zero_halts(self) -> None:
        def fetched(**flags) -> torch.Tensor:
            model = eager(tiny_model(**flags))
            if flags.get("row_halt"):
                with torch.no_grad():
                    model.heads.row_halt.bias.fill_(20.0)
            return model.answer(self.batch).fetched.sum(1)

        top_k = tiny_config().top_k
        halted, free = fetched(row_halt=True), fetched()
        self.assertTrue((halted <= top_k).all(), halted)       # only the first loop's fetch happens
        self.assertGreater(int(free.max()), top_k)

    def test_own_mode_training_fetches_nothing_after_register_zero_halts(self) -> None:
        model = tiny_model(row_halt=True)
        with torch.no_grad():
            model.heads.ask.bias.fill_(20.0)
            model.heads.row_halt.bias.fill_(20.0)
        calls = []
        original = model._insert

        def record(episode, store, index, cards):
            calls.append(cards.clone())
            return original(episode, store, index, cards)

        model._insert = record
        model(self.batch, mode="own", p_own=1.0, generator=torch.Generator().manual_seed(0))
        del model._insert
        self.assertGreater(len(calls), 1)
        self.assertTrue((calls[0] >= 0).any())                  # loop 0 has not halted anything yet
        for cards in calls[1:]:                                 # keep ~ 2e-9 from loop 1 on
            self.assertTrue((cards == -1).all())

    def test_ponder_term_is_added_to_the_halt_loss(self) -> None:
        def run(cost: float):
            model = tiny_model(row_halt=True, row_halt_cost=cost)
            seen = capture_episode(model)
            out = model(self.batch, mode="teacher", generator=torch.Generator().manual_seed(0))
            release(model)
            return out, seen["episode"]

        plain, _ = run(0.0)
        priced, episode = run(0.5)
        terms = torch.cat(episode.ponder)
        registers = tiny_config().registers
        later = int(priced["metrics"]["question_loops"]) - self.count          # (question, loop) pairs with loop >= 1
        self.assertEqual(terms.numel(), registers * later)
        self.assertTrue(0.0 < float(terms.detach().mean()) <= 1.0)          # the share of registers still updating
        torch.testing.assert_close(priced["halt"] - plain["halt"], 0.5 * terms.mean(), rtol=1e-4, atol=1e-6)
        torch.testing.assert_close(priced["ans"], plain["ans"])                  # only L_halt carries the cost
        self.assertGreater(float(priced["loss"].detach()), float(plain["loss"].detach()))

    def test_no_ponder_term_with_a_single_loop(self) -> None:
        priced = tiny_model(row_halt=True, row_halt_cost=0.5)
        free = tiny_model(row_halt=True, row_halt_cost=0.0)
        one = priced(self.batch, mode="teacher", loops=1, generator=torch.Generator().manual_seed(0))
        ref = free(self.batch, mode="teacher", loops=1, generator=torch.Generator().manual_seed(0))
        self.assertTrue(torch.equal(one["halt"], ref["halt"]))

    def test_the_router_gets_gradient(self) -> None:
        model = tiny_model(row_halt=True, row_halt_cost=1.0)
        out = model(self.batch, mode="teacher", generator=torch.Generator().manual_seed(0))
        out["loss"].backward()
        self.assertGreater(float(model.heads.row_halt.weight.grad.abs().sum()), 0.0)
        self.assertGreater(float(model.heads.row_halt.bias.grad.abs().sum()), 0.0)

    def test_controls_run(self) -> None:
        for variant in ("D-noask", "D-noptr"):
            model = tiny_model(variant, row_halt=True)
            out = model(self.batch, mode="own", p_own=0.5, generator=torch.Generator().manual_seed(0))
            out["loss"].backward()
            self.assertTrue(torch.isfinite(out["loss"]))
            model.answer(self.batch)


class RandomDepthTest(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = synthetic_batch(visits=2, lines=24, seed=5)
        self.count = self.batch.q_visit.shape[0]

    def loops_run(self, model, mode="own", **kwargs) -> int:
        out = model(self.batch, mode=mode, generator=torch.Generator().manual_seed(0), **kwargs)
        return int(out["metrics"]["question_loops"])

    def test_a_fixed_cap_clamps_the_question_loops(self) -> None:
        model = tiny_model()
        top = model.config.max_loops
        self.assertEqual(self.loops_run(model, "own"), self.count * top)
        for cap in (1, 2, 4, top, top + 3):
            self.assertEqual(self.loops_run(model, "own", depth_cap=cap), self.count * min(cap, top))
        self.assertEqual(self.loops_run(model, "gold", depth_cap=1), self.count)
        self.assertEqual(self.loops_run(model, "gold", depth_cap=5), 2 * self.count)           # a cap never extends
        self.assertEqual(self.loops_run(model, "own", loops=5, depth_cap=3), 3 * self.count)   # explicit loops too
        self.assertEqual(self.loops_run(model, "own", loops=2, depth_cap=3), 2 * self.count)
        for mode in ("gold", "teacher", "own"):
            for cap in (1, 2, 3):
                self.assertEqual(self.loops_run(model, mode, depth_cap=cap),
                                 int(planned_loops(self.batch, mode, model.config, cap).sum()), (mode, cap))
        with self.assertRaises(ValueError):
            self.loops_run(model, "own", depth_cap=0)

    def test_planned_loops_clamps_like_the_model(self) -> None:
        config = tiny_config()
        for mode in ("gold", "teacher", "own"):
            free = planned_loops(self.batch, mode, config)
            self.assertTrue(torch.equal(planned_loops(self.batch, mode, config, None), free))
            self.assertTrue(torch.equal(planned_loops(self.batch, mode, config, 3), free.clamp_max(3)))
            self.assertTrue((planned_loops(self.batch, mode, config, 1) == 1).all())

    def test_forward_samples_its_own_cap_from_the_generator(self) -> None:
        model = tiny_model(random_depth=True, random_depth_min=2)
        top = model.config.max_loops
        seen = set()
        for seed in range(40):
            expected = int(torch.randint(2, top + 1, (1,), generator=torch.Generator().manual_seed(seed)))
            out = model(self.batch, mode="own", generator=torch.Generator().manual_seed(seed))
            self.assertEqual(int(out["metrics"]["question_loops"]), self.count * expected)
            seen.add(expected)
        self.assertEqual(seen, set(range(2, top + 1)))

    def test_forward_without_a_generator_uses_the_global_rng(self) -> None:
        model = tiny_model(random_depth=True)
        torch.manual_seed(7)
        expected = int(torch.randint(1, model.config.max_loops + 1, (1,)))
        torch.manual_seed(7)
        out = model(self.batch, mode="gold")
        self.assertEqual(int(out["metrics"]["question_loops"]), self.count * min(expected, 2))

    def test_an_explicit_cap_skips_sampling(self) -> None:
        model = tiny_model(random_depth=True)
        generator = torch.Generator().manual_seed(0)
        state = generator.get_state()
        model(self.batch, mode="gold", depth_cap=2, generator=generator)
        self.assertTrue(torch.equal(generator.get_state(), state))

    def test_flag_off_and_no_grad_draw_nothing(self) -> None:
        for model, grad in ((tiny_model(), True), (tiny_model(random_depth=True), False)):
            generator = torch.Generator().manual_seed(0)
            state = generator.get_state()
            with torch.set_grad_enabled(grad):
                out = model(self.batch, mode="gold", generator=generator)    # gold draws nothing else
            self.assertTrue(torch.equal(generator.get_state(), state))
            self.assertEqual(int(out["metrics"]["question_loops"]), 2 * self.count)
        model = tiny_model(random_depth=True)                                # control: the flag does draw
        generator = torch.Generator().manual_seed(0)
        state = generator.get_state()
        model(self.batch, mode="gold", generator=generator)
        self.assertFalse(torch.equal(generator.get_state(), state))

    def test_eval_mode_forward_draws_no_cap(self) -> None:
        model = tiny_model(random_depth=True)
        model.eval()
        out = model(self.batch, mode="own", generator=torch.Generator().manual_seed(0))
        self.assertEqual(int(out["metrics"]["question_loops"]), model.config.max_loops * self.batch.q_visit.shape[0])

    def test_budget_for_steps_prices_the_mean_cap(self) -> None:
        """train_toy(steps=N) with random_depth runs about N steps (the budget averages over the caps)."""
        from premonition.train import train_toy
        steps = [train_toy("D", steps=40, log_every=20, warmup_steps=2, seed=seed,
                           config_overrides={"random_depth": True})["train"]["steps"] for seed in (0, 1)]
        for count in steps:
            self.assertTrue(28 <= count <= 52, steps)

    def test_answer_is_unaffected(self) -> None:
        a, b = tiny_model(), tiny_model(random_depth=True)
        self.assertTrue(torch.equal(a.answer(self.batch).tokens, b.answer(self.batch).tokens))
        self.assertTrue(torch.equal(a.answer(self.batch).loops, b.answer(self.batch).loops))

    def test_trainer_plans_the_loops_it_runs(self) -> None:
        batches = [synthetic_batch(visits=2, lines=20, seed=s) for s in range(30, 38)]
        for label, curriculum in (("gold", Curriculum()), ("teacher", Curriculum(0.0, 1.0, 1.0)),
                                  ("own", Curriculum(0.0, 0.0, 0.0))):
            with self.subTest(phase=label):
                model = tiny_model(random_depth=True)
                trainer = MiniTrainer(model, mini_train_config(lr=1e-3, warmup_steps=2, log_every=2), "cpu",
                                      flop_budget=1e12, curriculum=curriculum, seed=3, fit=FlopFit(0.0, 1.0, 0.0))
                self.assertIsNone(trainer.depth_cap)
                charged = []
                original = trainer.batch_cost

                def spy(batch, plan, original=original):
                    cost, loops = original(batch, plan)
                    charged.append((trainer.depth_cap, int(loops.sum()), plan.mode, batch))
                    return cost, loops

                trainer.batch_cost = spy
                report = trainer.train(batches, max_steps=len(batches))
                self.assertEqual(report["steps"], len(batches))
                self.assertEqual(report["loop_mismatches"], 0)
                self.assertEqual(trainer.question_loops, sum(c[1] for c in charged))
                caps = [c[0] for c in charged]
                self.assertTrue(all(1 <= c <= model.config.max_loops for c in caps), caps)
                self.assertGreater(len(set(caps)), 1, "the cap should vary across steps")
                free = [int(planned_loops(b, m, model.config).sum()) for _, _, m, b in charged]
                self.assertTrue(any(c[1] < f for c, f in zip(charged, free)), "a cap should bite somewhere")

    def test_trainer_draws_nothing_without_the_flag(self) -> None:
        trainer = MiniTrainer(tiny_model(), mini_train_config(lr=1e-3, warmup_steps=2, log_every=2), "cpu",
                              flop_budget=1e12, seed=3, fit=FlopFit(0.0, 1.0, 0.0))
        report = trainer.train([synthetic_batch(visits=2, lines=20, seed=30)], max_steps=1)
        self.assertEqual(report["loop_mismatches"], 0)
        self.assertIsNone(trainer.depth_cap)


class BothTogetherTest(unittest.TestCase):
    def test_row_halt_with_random_depth_and_attnres_trains(self) -> None:
        batch = synthetic_batch(visits=2, lines=24, seed=5)
        model = tiny_model(row_halt=True, random_depth=True, loop_attnres=True)
        out = model(batch, mode="own", p_own=0.5, generator=torch.Generator().manual_seed(2), depth_cap=4)
        out["loss"].backward()
        self.assertTrue(torch.isfinite(out["loss"]))
        self.assertGreater(float(model.heads.row_halt.weight.grad.abs().sum()), 0.0)
        model.answer(batch)


if __name__ == "__main__":
    unittest.main()
