"""Steal 7 (design/steals-2026-10-17/SPEC.md): ask_reuse, the ASK ranking cached between refresh loops."""
from __future__ import annotations

import unittest

import torch

from premonition.model import _norm
from tests.test_premonition_model import eager, synthetic_batch, tiny_model

NEG_INF = float("-inf")


def start(model, batch):
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    episode = model._start(batch, hidden, store, model._mentions(batch))
    return episode, store, torch.arange(batch.q_visit.shape[0])


class AskReuseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = synthetic_batch(visits=2, lines=24, seed=7)

    def test_a_reuse_loop_with_an_unmoved_query_returns_the_cache_minus_fetched_cards(self) -> None:
        model = tiny_model(seed=0, ask_reuse=True, ask_refresh_every=100, ask_refresh_cos=2.0)
        episode, store, index = start(model, self.batch)
        with torch.no_grad():
            _, _, _, first = model._step(episode, index, 0, store)
            self.assertTrue((episode.ask_age == 0).all())
            self.assertTrue(torch.equal(episode.ask_cache, first))
            cards = store.top(first, model.config.top_k)
            model._insert(episode, store, index, cards)
            _, _, _, second = model._step(episode, index, 1, store)
        self.assertTrue((episode.ask_age == 1).all())                       # reused, not refreshed
        expected = first.clone()
        for q in range(index.numel()):
            for card in cards[q][cards[q] >= 0]:
                if card != store.null:
                    expected[q, card] = NEG_INF
        self.assertTrue(torch.equal(second, expected))
        self.assertTrue(torch.isfinite(second[:, store.null]).all())        # NULL stays eligible
        self.assertTrue(torch.equal(episode.ask_cache, first))              # the cache itself is kept
        top = store.top(second, model.config.top_k)
        for q in range(index.numel()):                                       # a fetched card is never re-fetched
            real = cards[q][(cards[q] >= 0) & (cards[q] != store.null)]
            self.assertFalse(torch.isin(top[q], real).any())

    def test_threshold_zero_always_refreshes_and_matches_flags_off(self) -> None:
        for mode, p_own in (("gold", 0.0), ("teacher", 0.0), ("own", 0.5)):
            off, on = tiny_model(seed=2), tiny_model(seed=2, ask_reuse=True, ask_refresh_cos=0.0,
                                                     ask_refresh_every=100)
            outs = [m(self.batch, mode=mode, p_own=p_own, generator=torch.Generator().manual_seed(0))
                    for m in (off, on)]
            for name in ("lm", "ask", "ans", "halt", "loss"):
                self.assertTrue(torch.equal(outs[0][name], outs[1][name]), (mode, name))
            outs[0]["loss"].backward()
            outs[1]["loss"].backward()
            for (name, a), (_, b) in zip(off.named_parameters(), on.named_parameters()):
                self.assertTrue(a.grad is None and b.grad is None or torch.equal(a.grad, b.grad), (mode, name))
        off, on = (eager(tiny_model(seed=3, **kw)) for kw in ({}, dict(ask_reuse=True, ask_refresh_cos=0.0,
                                                                        ask_refresh_every=100)))
        a, b = off.answer(self.batch), on.answer(self.batch)
        for field in ("tokens", "lengths", "loops", "first_top", "fetched", "halt_prob"):
            self.assertTrue(torch.equal(getattr(a, field), getattr(b, field)), field)

    def test_threshold_zero_refreshes_even_a_frozen_query(self) -> None:
        """In fp32, 1 - u.u of an unchanged unit query can come out slightly negative: 0 must still mean always."""
        model = tiny_model(seed=0, ask_reuse=True, ask_refresh_every=100, ask_refresh_cos=0.0)
        episode, store, index = start(model, self.batch)
        register = torch.randn(index.numel(), model.config.d_model, generator=torch.Generator().manual_seed(5))
        with torch.no_grad():
            model._ask_scores(episode, index, 0, store, register)
            model._ask_scores(episode, index, 1, store, register)               # the same query again
        self.assertTrue((episode.ask_age == 0).all())

    def test_every_n_loops_refresh_regardless_of_the_query(self) -> None:
        model = tiny_model(seed=0, ask_reuse=True, ask_refresh_every=2, ask_refresh_cos=2.0)
        episode, store, index = start(model, self.batch)
        with torch.no_grad():
            ages = []
            for step in range(4):
                model._step(episode, index, step, store)
                ages.append(episode.ask_age.clone())
        self.assertEqual([int(a.unique()) for a in ages], [0, 1, 0, 1])

    def test_moving_the_query_past_the_threshold_triggers_a_refresh(self) -> None:
        model = tiny_model(seed=0, ask_reuse=True, ask_refresh_every=100, ask_refresh_cos=0.1)
        episode, store, index = start(model, self.batch)
        with torch.no_grad():
            rows, _, _, first = model._step(episode, index, 0, store)
            register = _norm(rows[:, model._register_base])
            same = model._ask_scores(episode, index, 1, store, register)
            self.assertTrue((episode.ask_age == 1).all())
            self.assertTrue(torch.equal(same, first))
            wild = _norm(torch.randn_like(register))                         # a query far from the cached one
            moved = model._ask_scores(episode, index, 2, store, wild)
            self.assertTrue((episode.ask_age == 0).all())
            fresh = store.ask(model.heads.query(wild), episode.q_visit, episode.q_line,
                              model.heads.log_kappa.exp(), model.think.age_bias, episode.fetched, questions=index)
            self.assertTrue(torch.equal(moved, fresh))
            self.assertTrue(torch.equal(episode.ask_cache, fresh))
            # a barely moved query stays under the threshold
            nudge = wild + 1e-3 * torch.randn_like(wild)
            model._ask_scores(episode, index, 3, store, nudge)
            self.assertTrue((episode.ask_age == 1).all())

    def test_subsets_refresh_per_question_and_leave_other_rows_alone(self) -> None:
        model = tiny_model(seed=0, ask_reuse=True, ask_refresh_every=100, ask_refresh_cos=0.1)
        episode, store, index = start(model, self.batch)
        count = index.numel()
        self.assertGreaterEqual(count, 4)
        with torch.no_grad():
            rows, _, _, _ = model._step(episode, index, 0, store)
            register = _norm(rows[:, model._register_base])
            cache, queries = episode.ask_cache.clone(), episode.ask_query.clone()
            # loop 1 runs only on the even questions, and only the first of them has moved
            subset = index[::2]
            mixed = register[subset].clone()
            mixed[0] = _norm(torch.randn_like(mixed[0]))
            scores = model._ask_scores(episode, subset, 1, store, mixed)
        self.assertEqual(episode.ask_age[subset].tolist(), [0] + [1] * (subset.numel() - 1))
        untouched = torch.ones(count, dtype=torch.bool)
        untouched[subset] = False
        self.assertTrue(torch.equal(episode.ask_age[untouched], torch.zeros(int(untouched.sum()), dtype=torch.long)))
        self.assertTrue(torch.equal(episode.ask_cache[untouched], cache[untouched]))
        self.assertTrue(torch.equal(episode.ask_cache[subset[1:]], cache[subset[1:]]))
        self.assertTrue(torch.equal(episode.ask_query[subset[1:]], queries[subset[1:]]))
        self.assertTrue(torch.equal(episode.ask_cache[subset[0]], scores[0]))
        self.assertFalse(torch.equal(episode.ask_query[subset[0]], queries[subset[0]]))
        self.assertTrue(torch.equal(scores[1:], cache[subset[1:]]))

    def test_questions_without_a_cache_always_score_in_full(self) -> None:
        model = tiny_model(seed=0, ask_reuse=True, ask_refresh_every=100, ask_refresh_cos=2.0)
        episode, store, index = start(model, self.batch)
        with torch.no_grad():
            model._step(episode, index[:2], 0, store)                        # only two questions have run
            self.assertEqual(episode.ask_age.tolist(), [0, 0] + [-1] * (index.numel() - 2))
            rows, _, _, scores = model._step(episode, index, 1, store)
        self.assertTrue((episode.ask_age[:2] == 1).all() and (episode.ask_age[2:] == 0).all())
        self.assertFalse(torch.isnan(scores).any())

    def test_reused_scores_keep_their_graph(self) -> None:
        model = tiny_model(seed=0, ask_reuse=True, ask_refresh_every=100, ask_refresh_cos=2.0)
        episode, store, index = start(model, self.batch)
        _, _, _, first = model._step(episode, index, 0, store)
        model._insert(episode, store, index, store.top(first.detach(), model.config.top_k))
        _, _, _, second = model._step(episode, index, 1, store)
        self.assertTrue(second.requires_grad)
        self.assertEqual(int((episode.ask_age == 1).sum()), index.numel())
        finite = second.masked_fill(~torch.isfinite(second), 0.0)
        finite.sum().backward()
        self.assertGreater(model.heads.query.weight.grad.abs().sum(), 0)

    def test_trains_with_the_defaults_and_answers(self) -> None:
        model = tiny_model(seed=0, ask_reuse=True)
        for mode in ("gold", "teacher", "own"):
            out = model(self.batch, mode=mode, p_own=0.5, generator=torch.Generator().manual_seed(0))
            out["loss"].backward()
            self.assertTrue(torch.isfinite(out["loss"]), mode)
        answers = eager(model).answer(self.batch)
        self.assertEqual(answers.tokens.shape[0], self.batch.q_visit.shape[0])


if __name__ == "__main__":
    unittest.main()
