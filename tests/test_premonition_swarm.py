"""The swarm of desks (premonition/swarm.py, design/swarm/IMPLEMENTATION-SPEC.md §11), CPU, tiny models.

Test 1 is the contract: with `thinkers == 1` the live model is bit-identical to the frozen pre-swarm copy.
"""
from __future__ import annotations

from dataclasses import asdict
import math
import unittest

import torch
import torch.nn.functional as F

from premonition import swarm as sw
from premonition.batch import MAX_LINE_ENTS, VisitBatch
from premonition.config import PARAM_BAND, MiniConfig
from premonition.model import PremonitionMini
from premonition.store import CardStore
from premonition.train import _mean_diversity, planned_loops, validate
from tests import _premonition_model_pre_swarm as frozen
from tests.test_premonition_model import (N_ENT, VOCAB, eager, synthetic_batch, tiny_config, tiny_model)

VARIANTS = ("D", "D-noask", "D-noptr")
M = 3


def build(variant: str = "D", seed: int = 0, **overrides) -> PremonitionMini:
    return tiny_model(variant, seed, **overrides)


def s0(variant: str = "D", seed: int = 0, **overrides) -> PremonitionMini:
    return build(variant, seed, thinkers=M, **overrides)


def s1(variant: str = "D", seed: int = 0, **overrides) -> PremonitionMini:
    return build(variant, seed, thinkers=M, swarm_board=True, **overrides)


class FlagOffIdentityTest(unittest.TestCase):
    """1. thinkers == 1 reproduces the frozen copy exactly: parameters, losses, gradients, answers."""

    def test_state_losses_gradients_and_answers_are_bit_identical(self) -> None:
        batch = synthetic_batch(seed=1)
        for variant in VARIANTS:
            config = tiny_config(variant)
            torch.manual_seed(7)
            live = PremonitionMini(config)
            torch.manual_seed(7)
            old = frozen.PremonitionMini(config)
            a, b = live.state_dict(), old.state_dict()
            self.assertEqual(list(a), list(b), variant)
            for name in a:
                self.assertTrue(torch.equal(a[name], b[name]), (variant, name))
            self.assertIsNone(live.think.desk)
            self.assertIsNone(live.think.board_type)
            for mode, p_own in (("gold", 0.0), ("teacher", 0.0), ("own", 0.5)):
                outs = []
                for model in (live, old):
                    model.zero_grad(set_to_none=True)
                    out = model(batch, mode=mode, p_own=p_own, generator=torch.Generator().manual_seed(3))
                    out["loss"].backward()
                    outs.append(out)
                for name in ("lm", "ask", "ans", "halt", "loss"):
                    self.assertTrue(torch.equal(outs[0][name], outs[1][name]), (variant, mode, name))
                for key, value in outs[0]["metrics"].items():
                    self.assertTrue(torch.equal(value, outs[1]["metrics"][key]), (variant, mode, key))
                for (name, p), (_, q) in zip(live.named_parameters(), old.named_parameters()):
                    self.assertTrue(p.grad is None and q.grad is None or torch.equal(p.grad, q.grad),
                                    (variant, mode, name))
            for use_eager in (False, True):
                if use_eager:
                    if variant == "D-noask":
                        continue
                    eager(live), eager(old)
                new, ref = live.answer(batch), old.answer(batch)
                self.assertIsNone(new.swarm)
                for name in ("tokens", "lengths", "loops", "first_top", "halt_prob"):
                    self.assertTrue(torch.equal(getattr(new, name), getattr(ref, name)), (variant, use_eager, name))
                if ref.fetched is None:
                    self.assertIsNone(new.fetched)
                else:
                    self.assertTrue(torch.equal(new.fetched, ref.fetched), (variant, use_eager))
                    if use_eager:
                        self.assertTrue(new.fetched[:, :-1].any())

    def test_short_loop_configs_still_build_and_match_with_the_flag_off(self) -> None:
        """Review item 1: swarm-only checks never fire with thinkers == 1, so max_loops < swarm_rounds (4) builds,
        and the model is still bit-identical to the frozen copy there; old saved configs (no swarm keys) load."""
        from premonition.train import mini_config_from
        batch = synthetic_batch(seed=5)
        for variant in VARIANTS:
            for loops in (1, 2, 3):
                config = tiny_config(variant, max_loops=loops)
                self.assertEqual((config.thinkers, config.swarm_rounds), (1, 4))
                torch.manual_seed(11)
                live = PremonitionMini(config)
                torch.manual_seed(11)
                old = frozen.PremonitionMini(config)
                for mode in ("gold", "teacher", "own"):
                    a = live(batch, mode=mode, p_own=0.5, generator=torch.Generator().manual_seed(1))
                    b = old(batch, mode=mode, p_own=0.5, generator=torch.Generator().manual_seed(1))
                    for name in ("lm", "ask", "ans", "halt", "loss"):
                        self.assertTrue(torch.equal(a[name], b[name]), (variant, loops, mode, name))
                new, ref = live.answer(batch), old.answer(batch)
                for name in ("tokens", "lengths", "loops", "first_top", "halt_prob"):
                    self.assertTrue(torch.equal(getattr(new, name), getattr(ref, name)), (variant, loops, name))
        saved = {key: value for key, value in asdict(tiny_config(max_loops=3)).items()
                 if key not in ("thinkers", "swarm_board", "swarm_rounds", "board_cards")}
        self.assertEqual(mini_config_from(saved).max_loops, 3)                   # a pre-swarm checkpoint config
        with self.assertRaises(ValueError):                                      # the swarm itself still checks
            tiny_config(max_loops=2, thinkers=2)

    def test_full_size_count_unchanged_and_lesion_needs_a_swarm(self) -> None:
        config = MiniConfig.preset("D")
        self.assertEqual(config.num_parameters(), 2_013_140)
        with torch.device("meta"):
            self.assertEqual(PremonitionMini(config).num_parameters(), 2_013_140)
        with self.assertRaises(ValueError):
            build().answer(synthetic_batch(), lesion="board")


class ConfigTest(unittest.TestCase):
    def test_validation(self) -> None:
        for bad in (dict(thinkers=0), dict(thinkers=2, swarm_rounds=0), dict(thinkers=2, swarm_rounds=7),
                    dict(thinkers=2, board_cards=0), dict(swarm_board=True),
                    dict(thinkers=2, swarm_board=True, registers=1)):
            with self.assertRaises(ValueError, msg=str(bad)):
                tiny_config(**bad)
        tiny_config(thinkers=2, swarm_board=True, swarm_rounds=6)

    def test_parameter_accounting(self) -> None:
        for variant in VARIANTS:
            for thinkers, board in ((1, False), (2, False), (4, False), (2, True), (4, True)):
                config = tiny_config(variant, thinkers=thinkers, swarm_board=board)
                model = PremonitionMini(config)
                self.assertEqual(model.parameter_breakdown(), config.parameter_breakdown(), (variant, thinkers, board))
        base = tiny_config().num_parameters()
        d = tiny_config().d_model
        self.assertEqual(tiny_config(thinkers=4).num_parameters() - base, 4 * d)
        self.assertEqual(tiny_config(thinkers=4, swarm_board=True).num_parameters() - base, 6 * d)

    def test_band_holds_at_d128_for_two_to_eight_desks(self) -> None:
        for thinkers in range(2, 9):
            config = MiniConfig.preset("D", thinkers=thinkers, swarm_board=True)
            self.assertTrue(PARAM_BAND[0] <= config.num_parameters() <= PARAM_BAND[1])
            self.assertLess(config.num_parameters() - 2_013_140, 1_300)
        with torch.device("meta"):
            config = MiniConfig.preset("D", thinkers=8, swarm_board=True)
            self.assertEqual(PremonitionMini(config).parameter_breakdown(), config.parameter_breakdown())


class ForwardTest(unittest.TestCase):
    def test_forward_backward_every_mode_s0_and_s1(self) -> None:
        batch = synthetic_batch()
        Q = batch.size[2]
        for make in (s0, s1):
            model = make()
            generator = torch.Generator().manual_seed(0)
            for mode, p_own in (("gold", 0.0), ("teacher", 0.0), ("own", 0.5)):
                model.zero_grad(set_to_none=True)
                out = model(batch, mode=mode, p_own=p_own, generator=generator)
                for name in ("lm", "ask", "ans", "halt", "loss"):
                    self.assertTrue(torch.isfinite(out[name]), (make.__name__, mode, name))
                out["loss"].backward()
                grads = [p.grad for p in model.parameters() if p.grad is not None]
                self.assertTrue(grads and all(torch.isfinite(g).all() for g in grads), mode)
                self.assertEqual(int(out["metrics"]["gold_missing"]), 0)
                rounds = 2 if mode == "gold" else model.config.swarm_rounds
                self.assertEqual(int(out["metrics"]["question_loops"]), Q * rounds * M)
                self.assertEqual(len(out["metrics"]["swarm_ask_rate"]), M)
                if mode == "teacher":
                    self.assertGreater(out["ask"].item(), 0.0)
                    self.assertGreater(model.think.desk.weight.grad.abs().sum().item(), 0.0)
                    if make is s1:
                        self.assertGreater(model.think.board_type.weight.grad.abs().sum().item(), 0.0)
            self.assertEqual(int(model(batch, mode="gold", loops=1)["metrics"]["question_loops"]), Q * M)
            planned = planned_loops(batch, "teacher", model.config)
            self.assertEqual(int(planned.sum()), Q * model.config.swarm_rounds * M)
            self.assertEqual(int(planned_loops(batch, "gold", model.config).sum()), Q * 2 * M)

    def test_controls_run(self) -> None:
        batch = synthetic_batch(seed=1)
        for variant in ("D-noask", "D-noptr"):
            for make in (s0, s1):
                model = make(variant)
                out = model(batch, mode="teacher")
                out["loss"].backward()
                self.assertTrue(torch.isfinite(out["loss"]), variant)
                answers = model.answer(batch)
                self.assertEqual(answers.swarm["desk_fetched"].shape[1], M)
                self.assertEqual(answers.fetched is None, variant == "D-noask")

    def test_validate_and_wipes_run_on_a_swarm(self) -> None:
        batch = synthetic_batch(visits=2, lines=24, seed=7)
        model = eager(s1())
        result = validate(model, [batch])
        self.assertEqual(result["questions"], batch.size[2])
        self.assertNotIn("accuracy_gold_cards", result)
        window = (batch.q_line - 6).clamp_min(1)
        lines = torch.arange(batch.line_start.shape[1] + 1)
        outside = (lines[:-1] < window.unsqueeze(1)) | (lines[:-1] >= batch.q_line.unsqueeze(1))
        for wipe in ("store", "full"):
            answers = model.answer(batch, wipe=wipe, window_line=window)
            self.assertFalse((answers.fetched[:, :-1] & outside).any(), wipe)
            self.assertTrue(answers.fetched[:, :-1].any(), wipe)

    def test_empty_batch(self) -> None:
        model = s1()
        batch = synthetic_batch()
        empty = VisitBatch(**{**batch.__dict__, **{k: getattr(batch, k)[:0] for k in (
            "q_visit", "q_line", "q_span", "answer", "gold_lines", "depth")}, "question_ids": []})
        out = model(empty)
        self.assertEqual(int(out["metrics"]["question_loops"]), 0)
        self.assertEqual(model.answer(empty).tokens.shape[0], 0)


class ConcurrencyTest(unittest.TestCase):
    """4. One think call per round over all Q*M desks."""

    def test_one_think_call_per_round_with_batch_q_times_m(self) -> None:
        batch = synthetic_batch()
        Q = batch.size[2]
        for make in (s0, s1):
            model = make()
            calls = []
            hook = model.think.register_forward_hook(lambda _m, args, _o: calls.append(tuple(args[0].shape)))
            model(batch, mode="teacher")
            self.assertEqual(len(calls), model.config.swarm_rounds)
            self.assertTrue(all(shape[0] == Q * M for shape in calls))
            calls.clear()
            model(batch, mode="gold")
            self.assertEqual(len(calls), 2)
            calls.clear()
            model.answer(batch, max_loops=3)
            self.assertEqual(len(calls), 3)
            self.assertTrue(all(shape[0] == Q * M for shape in calls))
            hook.remove()


def _capture_rounds(model: PremonitionMini, batch: VisitBatch, perturb: bool) -> list[torch.Tensor]:
    """Think outputs per round; with `perturb`, desk 1's rows are kicked right after `_start`."""
    outputs: list[torch.Tensor] = []
    hook = model.think.register_forward_hook(lambda _m, _a, out: outputs.append(out.detach().clone()))
    start = model._start

    def kicked(batch_, hidden, store, mentions):
        episode = start(batch_, hidden, store, mentions)
        if perturb:
            gen = torch.Generator().manual_seed(5)
            noise = torch.randn(episode.x.shape, generator=gen)
            mask = (torch.arange(episode.x.shape[0]) % M == 1).view(-1, 1, 1)
            episode.x = episode.x + 0.5 * noise * mask
        return episode

    model._start = kicked
    try:
        model.answer(batch, max_loops=3)
    finally:
        del model._start
        hook.remove()
    return outputs


class IndependenceTest(unittest.TestCase):
    """5. The board is the only channel: S0 desks are independent, S1 desks are coupled."""

    def test_comm_ablation_is_real(self) -> None:
        batch = synthetic_batch(seed=2)
        for board in (False, True):
            model = eager(s1() if board else s0())
            model.eval()
            base = _capture_rounds(model, batch, False)
            moved = _capture_rounds(model, batch, True)
            self.assertEqual(len(base), 3)
            own = torch.arange(base[0].shape[0]) % M == 0
            other = torch.arange(base[0].shape[0]) % M == 1
            self.assertFalse(torch.allclose(moved[0][other], base[0][other]))          # the kick landed
            if board:
                self.assertTrue(torch.equal(moved[0][own], base[0][own]))              # round 0: board still empty
                for r in (1, 2):
                    self.assertFalse(torch.allclose(moved[r][own], base[r][own], atol=1e-6), r)
            else:
                for r in range(3):
                    self.assertTrue(torch.allclose(moved[r][own], base[r][own], rtol=0, atol=1e-6), r)


class LesionTest(unittest.TestCase):
    def test_board_lesion_equals_an_s0_run_of_the_same_weights(self) -> None:
        batch = synthetic_batch(seed=4)
        full = eager(s1(seed=3))
        plain = eager(s0(seed=3))
        missing = plain.load_state_dict(full.state_dict(), strict=False)
        self.assertEqual(list(missing.unexpected_keys), ["think.board_type.weight"])
        self.assertEqual(missing.missing_keys, [])
        lesioned, reference = full.answer(batch, lesion="board"), plain.answer(batch)
        self.assertTrue(torch.equal(lesioned.tokens, reference.tokens))
        self.assertTrue(torch.equal(lesioned.fetched, reference.fetched))
        self.assertIsNone(lesioned.swarm["notes"])
        for lesion in ("notes", "cards"):
            out = full.answer(batch, lesion=lesion)
            self.assertEqual(out.tokens.shape, reference.tokens.shape)
        self.assertIsNotNone(full.answer(batch, lesion="cards").swarm["notes"])
        self.assertIsNone(full.answer(batch, lesion="notes").swarm["notes"])
        with self.assertRaises(ValueError):
            full.answer(batch, lesion="nope")
        with self.assertRaises(ValueError):
            plain.answer(batch, lesion="board")

    def test_lesions_change_what_the_combiner_reads(self) -> None:
        batch = synthetic_batch(seed=4)
        model = eager(s1(seed=3))
        with torch.no_grad():                       # make the board matter
            model.think.board_type.weight.normal_(std=1.0)
        seen = {}
        for lesion in (None, "board", "notes", "cards"):
            memory = []
            hook = model.decoder.register_forward_hook(lambda _m, args, _o: memory.append(args[1].shape[1]))
            model.answer(batch, lesion=lesion, max_loops=2)
            hook.remove()
            seen[lesion] = memory[0]
        R = model.config.rows
        self.assertEqual(seen["board"], M * R)
        self.assertEqual(seen[None], M * R + M + model.config.board_cards)


def _tiny_store(lines: int = 4, visits: int = 1, ents: dict[int, list[int]] | None = None) -> CardStore:
    config = tiny_config()
    d, dk = config.d_model, config.key_dim
    table = torch.full((visits, lines, MAX_LINE_ENTS), -1)
    for line, names in (ents or {}).items():
        table[0, line, :len(names)] = torch.tensor(names)
    return CardStore(keys=F.normalize(torch.randn(visits, lines, dk), dim=-1), values=torch.randn(visits, lines, d),
                     valid=torch.ones(visits, lines, dtype=torch.bool), tags=torch.zeros(visits, lines, dtype=torch.long),
                     ents=table, line_start=torch.zeros(visits, lines, dtype=torch.long),
                     line_len=torch.ones(visits, lines, dtype=torch.long),
                     null_key=F.normalize(torch.randn(dk), dim=0), null_value=torch.zeros(d))


class MergeTest(unittest.TestCase):
    """7. The combiner shows a bound slot from the desk that bound it, and desk 0's copy of the unbound."""

    def test_bound_slot_visibility(self) -> None:
        model = s0()
        config = model.config
        store = _tiny_store(ents={1: [5]})
        R = config.rows
        valid = torch.ones(M, R, dtype=torch.bool)
        first = config.question_rows
        valid[:, first:first + config.slots] = False
        valid[:, first + 5] = valid[:, first + 7] = valid[:, first + 9] = True       # mentioned by all desks
        valid[:, first + 9] = False
        fetched = torch.zeros(M, store.lines + 1, dtype=torch.bool)
        fetched[2, 1] = True                                                           # only desk 2 fetched the card
        fetched[0, store.null] = True                                                  # NULL binds nothing
        out = sw.merge_mask(model, valid, fetched, store, torch.zeros(M, dtype=torch.long), M).view(M, R)
        slot = lambda e: out[:, first + e].tolist()                                    # noqa: E731
        self.assertEqual(slot(5), [False, False, True])                                # only the binder shows it
        self.assertEqual(slot(7), [True, False, False])                                # unbound: desk 0's copy
        self.assertEqual(slot(9), [False, False, False])                               # never mentioned
        self.assertTrue(torch.equal(out[:, :first], valid[:, :first]))                 # other rows untouched
        self.assertTrue(torch.equal(out[:, first + config.slots:], valid[:, first + config.slots:]))

    def test_without_a_binder_every_valid_row_is_shown(self) -> None:
        model = s0("D-noptr")
        valid = torch.rand(M, model.config.rows) > 0.3
        out = sw.merge_mask(model, valid, None, None, torch.zeros(M, dtype=torch.long), M)
        self.assertTrue(torch.equal(out.view(M, -1), valid))


    def test_entity_table_matches_the_one_hot_and_the_cache(self) -> None:
        """Review item 7: the bool scatter table equals the old int64 one-hot, and the per-forward cache
        gives the same mask as building it inside merge_mask."""
        model = s0()
        config = model.config
        store = _tiny_store(lines=6, ents={1: [5, 2], 3: [7], 4: [5]})
        ents = store.ents
        onehot = (F.one_hot(ents.clamp_min(0), config.n_ent).bool() & (ents >= 0).unsqueeze(-1)).any(2)
        self.assertTrue(torch.equal(sw.entity_table(store, config.n_ent), onehot))
        valid = torch.rand(M, config.rows, generator=torch.Generator().manual_seed(0)) > 0.2
        fetched = torch.zeros(M, store.lines + 1, dtype=torch.bool)
        fetched[0, 3] = fetched[1, 1] = fetched[2, 4] = True
        visit = torch.zeros(M, dtype=torch.long)
        cached = sw.entity_table(store, config.n_ent)[visit]
        self.assertTrue(torch.equal(sw.merge_mask(model, valid, fetched, store, visit, M),
                                    sw.merge_mask(model, valid, fetched, store, visit, M, cached)))


class GoldPreloadTest(unittest.TestCase):
    """Review item 2: the gold phase keeps the LATEST gold lines (as the single thinker's topk) and may fill
    M * card_rows rows, so no gold card is dropped while the desks have room."""

    def test_latest_cards_dealt_round_robin(self) -> None:
        gold = torch.zeros(1, 14, dtype=torch.bool)
        gold[0, [1, 4, 7, 9, 12]] = True
        dealt = sw._gold_cards(gold, 2, 4)                                   # keep the 4 latest: 4, 7, 9, 12
        self.assertEqual(dealt.tolist(), [[4, 9], [7, 12]])
        dealt = sw._gold_cards(gold, 3, 6)                                   # room for all five, -1 pads
        self.assertEqual(sorted(c for c in dealt.flatten().tolist() if c >= 0), [1, 4, 7, 9, 12])
        self.assertEqual(dealt.tolist(), [[1, 9], [4, 12], [7, -1]])
        never = torch.zeros(1, 14, dtype=torch.bool)
        never[0, 13] = True                                                  # NULL only: desk 0
        self.assertEqual(sw._gold_cards(never, 3, 3).tolist(), [[13], [-1], [-1]])

    def test_gold_mode_loads_every_gold_card_beyond_card_rows(self) -> None:
        batch = synthetic_batch(seed=0, lines=20)                           # has questions with 2-3 gold cards
        model = s0(card_rows=1)                                              # 3 desks x 1 row = 3 >= |G| (<= 3 here)
        seen = []
        original = model._insert
        model._insert = lambda episode, store, index, cards: (seen.append(cards.clone()), original(episode, store, index, cards))[1]
        model(batch, mode="gold")
        del model._insert
        loaded = seen[0].view(-1, M * seen[0].shape[1])
        store_lines = batch.line_start.shape[1]
        sizes = [int(((batch.gold_lines[q] >= 0) & (batch.gold_lines[q] < batch.q_line[q])).sum())
                 for q in range(batch.size[2])]
        self.assertGreater(max(sizes), model.config.card_rows)              # the case the old cap dropped
        for q in range(batch.size[2]):
            gold = {int(l) for l in batch.gold_lines[q] if l >= 0 and l < batch.q_line[q]} or {store_lines}
            self.assertEqual({int(c) for c in loaded[q] if c >= 0}, gold, q)


class AssignmentTest(unittest.TestCase):
    """8. Training-time balanced split of the cards no desk has fetched."""

    def test_balanced_disjoint_cover(self) -> None:
        torch.manual_seed(0)
        need = torch.zeros(3, 9, dtype=torch.bool)
        need[0, [0, 2, 3, 6, 8]] = True
        need[1, [1, 4]] = True
        need[2, 8] = True                                                   # NULL-only style: one card
        for prefs in (torch.randn(3, 2, 9), torch.zeros(3, 2, 9),
                      torch.randn(3, 2, 9).masked_fill(torch.rand(3, 2, 9) < 0.3, -math.inf)):
            target = sw.balanced_assignment(prefs, need)
            self.assertTrue(torch.equal(target.any(1), need))                # union = need
            self.assertTrue((target.sum(1) <= 1).all())                      # disjoint
            self.assertTrue(((target.sum(2)[0] >= 2) & (target.sum(2)[0] <= 3)).all())
            self.assertEqual(sorted(target.sum(2)[1].tolist()), [1, 1])
            self.assertEqual(sorted(target.sum(2)[2].tolist()), [0, 1])      # exactly one desk
            self.assertFalse(target[:, :, ~need.any(0)].any())

    def test_follows_preferences(self) -> None:
        prefs = torch.full((1, 2, 4), -5.0)
        prefs[0, 1, 0] = prefs[0, 1, 1] = 3.0
        prefs[0, 0, 2] = prefs[0, 0, 3] = 3.0
        need = torch.ones(1, 4, dtype=torch.bool)
        target = sw.balanced_assignment(prefs, need)[0]
        self.assertEqual(target[1].tolist(), [True, True, False, False])
        self.assertEqual(target[0].tolist(), [False, False, True, True])

    def test_nothing_missing_assigns_nothing(self) -> None:
        target = sw.balanced_assignment(torch.randn(2, 3, 5), torch.zeros(2, 5, dtype=torch.bool))
        self.assertFalse(target.any())


class BoardTest(unittest.TestCase):
    """9. Cards are posted once; the card region is a FIFO."""

    def make(self, size: int = 3) -> tuple[PremonitionMini, CardStore, sw.Board]:
        model = s1(board_cards=size)
        store = _tiny_store(lines=8)
        board = sw.Board(model, 1, store, torch.zeros(1, dtype=torch.long), torch.tensor([7]), torch.device("cpu"))
        return model, store, board

    def test_same_card_from_two_desks_is_posted_once(self) -> None:
        _, store, board = self.make()
        cards = torch.tensor([[2, -1], [2, 4], [-1, store.null]])               # desks 0..2 of question 0
        board.post(cards)
        self.assertEqual(int(board.cards_ok.sum()), 2)                          # cards 2 and 4; NULL never posted
        self.assertEqual(board.posted[0].nonzero().flatten().tolist(), [2, 4])
        self.assertEqual(int(board.count[0]), 2)
        board.post(torch.tensor([[2, -1], [-1, -1], [4, -1]]))
        self.assertEqual(int(board.count[0]), 2)                                # nothing new

    def test_fifo_wraps_at_board_cards(self) -> None:
        model, store, board = self.make(size=3)
        for card in range(5):
            board.post(torch.tensor([[card], [-1], [-1]]))
        self.assertEqual(int(board.count[0]), 5)
        self.assertTrue(board.cards_ok.all())
        _, _, fresh = self.make(size=3)
        fresh.post(torch.tensor([[3], [-1], [-1]]))                             
        self.assertTrue(torch.allclose(board.cards[0, 0], fresh.cards[0, 0]))   # card 3 (post number 3) wrapped onto row 0
        board.post(torch.tensor([[4], [-1], [-1]]))                             # still on the board: not again
        self.assertEqual(int(board.count[0]), 5)
        board.post(torch.tensor([[0], [-1], [-1]]))                             # review item 3: card 0 was evicted
        self.assertEqual(int(board.count[0]), 6)                                # by card 3, so it is posted again
        self.assertEqual(sorted(board.slot_card[0].tolist()), [0, 3, 4])

    def test_vectorised_post_matches_a_one_by_one_fifo(self) -> None:
        """Review items 3 and 8: the scatter `post` equals a plain FIFO. Desks post simultaneously each round: a
        card is new if it is real, not NULL, not on the board at the round's start, and its first occurrence in
        desk order. New cards are written one by one (a later one may overwrite an earlier one when more than C
        are new), and a card whose row is overwritten leaves the board, so a later round may post it again."""
        generator = torch.Generator().manual_seed(0)
        for size in (2, 3, 5):
            model, store, board = self.make(size=size)
            card_at, pointer = [-1] * size, 0
            for _ in range(12):
                cards = torch.randint(-1, store.lines + 1, (M, 3), generator=generator)
                board.post(cards)
                at_start, seen = set(card_at), set()
                for card in cards.flatten().tolist():                         # desk-major, as the board walks
                    if card < 0 or card == store.null or card in at_start or card in seen:
                        continue
                    seen.add(card)
                    card_at[pointer % size] = card
                    pointer += 1
                self.assertEqual(int(board.count[0]), pointer, size)
                self.assertEqual(board.slot_card[0].tolist(), card_at, size)
                on_board = {c for c in card_at if c >= 0}
                self.assertEqual(set(board.posted[0].nonzero().flatten().tolist()), on_board, size)
                self.assertEqual(board.cards_ok[0].tolist(), [c >= 0 for c in card_at], size)

    def test_notes_carry_type_and_desk(self) -> None:
        model, _, board = self.make()
        register = torch.randn(M, model.config.d_model)
        board.write_notes(register)
        expected = register + model.think.board_type.weight[0] + model.think.desk.weight
        self.assertTrue(torch.allclose(board.notes[0], expected))
        self.assertTrue(board.notes_ok.all())
        rows, ok = board.rows()
        self.assertEqual(tuple(rows.shape), (1, M + 3, model.config.d_model))
        self.assertEqual(ok[0].tolist(), [True] * M + [False] * 3)


class CausalityTest(unittest.TestCase):
    """10. A swarm's answers ignore everything after the question."""

    def test_answers_ignore_everything_after_the_question(self) -> None:
        batch = synthetic_batch(visits=2, lines=24, seed=6)
        model = eager(s1())
        model.eval()
        pick = int(batch.size[2] // 2)
        visit, cut = int(batch.q_visit[pick]), int(batch.q_span[pick, 1])
        changed = batch.tokens.clone()
        tail = changed[visit, cut:batch.lengths[visit]]
        changed[visit, cut:batch.lengths[visit]] = torch.randint(10, VOCAB + N_ENT, tail.shape)
        base = model.answer(batch)
        moved = model.answer(VisitBatch(**{**batch.__dict__, "tokens": changed}))
        same = (batch.q_visit != visit) | (batch.q_span[:, 1] <= cut)
        self.assertTrue(same.sum() >= 2)
        torch.testing.assert_close(moved.halt_prob[same], base.halt_prob[same], rtol=0, atol=1e-5)
        self.assertTrue(torch.equal(moved.tokens[same], base.tokens[same]))
        self.assertTrue(torch.equal(moved.fetched[same], base.fetched[same]))
        late = base.swarm["desk_fetched"][..., :-1] & (
            torch.arange(base.fetched.shape[1] - 1) >= batch.q_line.view(-1, 1, 1))
        self.assertFalse(late.any())
        self.assertTrue(base.fetched[:, :-1].any())


class DiversityTest(unittest.TestCase):
    """11. The collapse report."""

    def swarm(self, fetched: torch.Tensor, registers: torch.Tensor, asks: torch.Tensor) -> dict:
        return {"desk_fetched": fetched, "desk_asks": asks, "registers": registers, "notes": None, "rounds": 4}

    def test_identical_desks_collapse(self) -> None:
        fetched = torch.zeros(5, 3, 7, dtype=torch.bool)
        fetched[:, :, [1, 3]] = True
        registers = torch.randn(5, 1, 4, 8).expand(5, 3, 4, 8).contiguous()
        report = sw.diversity(self.swarm(fetched, registers, torch.full((5, 3), 4)))
        self.assertAlmostEqual(report["fetch_overlap"], 1.0)
        self.assertAlmostEqual(report["register_cos"], 1.0, places=5)
        self.assertTrue(report["collapsed"])
        self.assertEqual(report["ask_rate"], [1.0, 1.0, 1.0])
        self.assertEqual(report["fetch_count"], [2.0, 2.0, 2.0])
        self.assertEqual(report["silent_desks"], 0)

    def test_disjoint_fetches_do_not(self) -> None:
        fetched = torch.zeros(4, 3, 7, dtype=torch.bool)
        for m in range(3):
            fetched[:, m, m] = True
        fetched[:, :, -1] = True                                                    # NULL is excluded
        asks = torch.tensor([[4, 2, 0]]).expand(4, 3)
        report = sw.diversity(self.swarm(fetched, torch.randn(4, 3, 4, 8), asks))
        self.assertEqual(report["fetch_overlap"], 0.0)
        self.assertFalse(report["collapsed"])
        self.assertEqual(report["ask_rate"], [1.0, 0.5, 0.0])
        self.assertEqual(report["silent_desks"], 1)

    def test_empty_unions_are_skipped_and_report_matches_answer(self) -> None:
        none = sw.diversity(self.swarm(torch.zeros(2, 2, 5, dtype=torch.bool), torch.randn(2, 2, 4, 8),
                                       torch.zeros(2, 2, dtype=torch.long)))
        self.assertTrue(math.isnan(none["fetch_overlap"]))
        self.assertFalse(none["collapsed"])
        answers = eager(s1()).answer(synthetic_batch(seed=5))
        report = sw.diversity(answers.swarm)
        self.assertEqual(len(report["ask_rate"]), M)
        parts = [(4, report), (6, report)]
        merged = _mean_diversity(parts)
        self.assertAlmostEqual(merged["register_cos"], report["register_cos"], places=6)
        self.assertEqual(merged["collapsed"], report["collapsed"])


class TrainerPlumbingTest(unittest.TestCase):
    """train.py: a swarm trains through MiniTrainer (tracked steps skip InsertLog), loops are counted in
    desk-rounds, and the swarm config survives a checkpoint round trip."""

    def test_trainer_step_loop_accounting_and_checkpoint(self) -> None:
        import tempfile
        from pathlib import Path
        from memorylab.storage import Budget
        from premonition.toy import ToySpec, toy_stream
        from premonition.train import (MiniTrainer, checkpoint_config, label_free, load_mini, mini_config_from,
                                       mini_train_config, save_mini_checkpoint)
        spec = ToySpec()
        torch.manual_seed(0)
        model = PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64,
                                                  thinkers=2, swarm_board=True, swarm_rounds=3))
        trainer = MiniTrainer(model, mini_train_config(lr=1e-3, warmup_steps=2, log_every=1), "cpu",
                              flop_budget=1.0, seed=0)
        stream = (label_free(b) for b in toy_stream(spec, 4, 0))
        batch = next(stream)
        plan = trainer.plan()
        loops = planned_loops(batch, plan.mode, model.config)
        self.assertEqual(int(loops.sum()), batch.size[2] * 2 * 2)               # gold: 2 rounds x 2 desks
        last = trainer._train_step(batch, plan, loops, True)                    # track=True: no InsertLog
        self.assertEqual(int(last["metrics"]["question_loops"]), int(loops.sum()))
        self.assertEqual(mini_config_from(asdict(model.config)), model.config)
        with tempfile.TemporaryDirectory() as folder:
            budget = Budget(Path(folder), hard=10_000_000_000, steady=8_000_000_000)
            config = checkpoint_config(trainer, contender="D", tokenizer={"path": "toy", "sha256": "t" * 64},
                                       detector="d" * 64, data={"dir": "toy", "tag": "toy"})
            save_mini_checkpoint(budget, "ck/S1", trainer, config)
            loaded, saved, _ = load_mini(Path(folder) / "ck" / "S1")
            self.assertEqual(loaded.config, model.config)
            self.assertEqual(saved["mini"]["thinkers"], 2)

    def test_seconds_budget_drives_the_curriculum_and_the_stop(self) -> None:
        """Matched wall-clock arms (RUNCARD-S0 §1): the phase follows training seconds, not FLOPs."""
        from premonition.toy import ToySpec, toy_stream
        from premonition.flops import FlopFit
        from premonition.train import MiniTrainer, label_free, mini_train_config
        spec = ToySpec()
        model = PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64))
        trainer = MiniTrainer(model, mini_train_config(warmup_steps=2), "cpu", flop_budget=1e30, seed=0,
                              seconds_budget=100.0)
        self.assertEqual(trainer.plan().phase, "gold")
        trainer.train_seconds = 20.0
        self.assertEqual(trainer.plan().phase, "teacher")
        trainer.train_seconds = 80.0
        self.assertEqual(trainer.plan().phase, "own")
        self.assertEqual(trainer.state_dict()["train_seconds"], 80.0)
        trainer.train_seconds = 100.0                                         # spent: stops before a step
        trainer.fit = FlopFit(0.0, 0.0, 0.0)
        out = trainer.train(label_free(b) for b in toy_stream(spec, 4, 0))
        self.assertEqual((out["stop"], out["steps"]), ("seconds budget", 0))
        plain = MiniTrainer(model, mini_train_config(), "cpu", flop_budget=1.0, seed=0)
        self.assertNotIn("train_seconds", plain.state_dict())                 # flag-off checkpoints unchanged
        with self.assertRaises(ValueError):
            MiniTrainer(model, mini_train_config(), "cpu", flop_budget=1.0, seconds_budget=0.0)


class TrainingTest(unittest.TestCase):
    """12. A short S1 run learns."""

    def test_training_steps_reduce_the_loss(self) -> None:
        model, batch = s1(), synthetic_batch(seed=3)
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3)
        losses = []
        for _ in range(25):
            out = model(batch, mode="teacher", generator=torch.Generator().manual_seed(0))
            optimizer.zero_grad()
            out["loss"].backward()
            optimizer.step()
            losses.append(out["loss"].item())
        self.assertLess(losses[-1], 0.8 * losses[0])


if __name__ == "__main__":
    unittest.main()
