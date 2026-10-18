"""Span cards (design/span-cards/01-design.md): the flag-off path is today's model, a span model branched from a
per-line parent is the same function, the soft surrogate matches a naive reference and leaves the forward value
alone, layouts are causal and never cross question lines or padding, gold and wipes are mapped by token overlap and
first line, and the card-economy report reads both layouts. CPU, tiny preset; no training beyond a few steps."""
from __future__ import annotations

from types import SimpleNamespace
import unittest

import torch
import torch.nn.functional as F

from premonition import span_cards
from premonition.batch import MAX_GOLD, MAX_LINE_ENTS
from premonition.model import PremonitionMini
from premonition.span_cards import (SpanCardMini, SpanCardStore, SpanConfig, SpanTrainer, build_model,
                                    card_economy, layout_card_stats, log_stay, rate_loss, soft_pool,
                                    surrogate_stay, tokens_per_line)
from learnlab.readonly import read_only
from premonition.train import (InsertLog, answer_with_gold, budget_for_steps, card_stats, mini_train_config,
                               summarize_cards, validate, validation_hook)
from tests.test_premonition_model import NEWLINE, VOCAB, eager, synthetic_batch, tiny_config

GATE = {"gate.weight", "gate.bias", "newline_weight"}


def span_config(**overrides) -> SpanConfig:
    return SpanConfig(enabled=True, newline_id=NEWLINE, **overrides)


def plain_model(seed: int = 0) -> PremonitionMini:
    torch.manual_seed(seed)
    return PremonitionMini(tiny_config())


def span_model(seed: int = 0, **overrides) -> SpanCardMini:
    torch.manual_seed(seed)
    return build_model(tiny_config(), span_config(**overrides))


def variable_model(seed: int = 0) -> SpanCardMini:
    """A gate that fires mid-line (bias -1, random weights) and no longer fires after a newline."""
    model = span_model(seed, max_span=10)
    generator = torch.Generator().manual_seed(seed + 1)
    with torch.no_grad():
        model.writer.gate.weight.copy_(torch.randn(1, 2 * model.config.d_model, generator=generator) * 0.5)
        model.writer.gate.bias.fill_(-1.0)
        model.writer.newline_weight.fill_(-20.0)
    return model.eval()


def store_of(model: PremonitionMini, batch):
    with torch.no_grad():
        return model.build_store(model.read(batch), batch)


def manual_store(token_line: list[int], cards: list[tuple[int, int]]) -> SpanCardStore:
    """One visit; `cards` are (first token, last token) spans; key and value widths 4."""
    width = len(token_line)
    valid = torch.zeros(1, width, dtype=torch.bool)
    card_line, first_line, line_start = (torch.full((1, width), -1) for _ in range(3))
    line_len, card_of = torch.zeros(1, width, dtype=torch.long), torch.full((1, width), -1)
    for first, last in cards:
        valid[0, last] = True
        card_line[0, last], first_line[0, last] = token_line[last], token_line[first]
        line_start[0, last], line_len[0, last] = first, last - first + 1
        card_of[0, first:last + 1] = last
    return SpanCardStore(
        keys=torch.zeros(1, width, 4), values=torch.zeros(1, width, 4), valid=valid,
        tags=torch.full((1, width), -1), ents=torch.full((1, width, MAX_LINE_ENTS), -1),
        line_start=line_start, line_len=line_len, null_key=torch.zeros(4), null_value=torch.zeros(4),
        card_line=card_line, first_line=first_line, token_line=torch.tensor([token_line]), card_of=card_of)


def gold_rows(rows: list[list[int]]) -> torch.Tensor:
    out = torch.full((len(rows), MAX_GOLD), -1)
    for i, row in enumerate(rows):
        out[i, :len(row)] = torch.tensor(row, dtype=torch.long)
    return out


# lines 0, 1, 2 of four tokens and the question line 3; line 0-1 is one merged card, line 2 is split in two
TOKEN_LINE = [0] * 4 + [1] * 4 + [2] * 4 + [3] * 4
CARDS = [(0, 7), (8, 9), (10, 11)]


class FlagOffTest(unittest.TestCase):
    def test_disabled_build_is_exactly_the_plain_model(self) -> None:
        batch = synthetic_batch(seed=1)
        plain = plain_model()
        after_plain = torch.get_rng_state()
        torch.manual_seed(0)
        off = build_model(tiny_config(), SpanConfig())
        self.assertIs(type(off), PremonitionMini)
        self.assertTrue(torch.equal(torch.get_rng_state(), after_plain))
        self.assertEqual(plain.state_dict().keys(), off.state_dict().keys())
        for name, tensor in plain.state_dict().items():
            self.assertTrue(torch.equal(tensor, off.state_dict()[name]), name)
        losses = [model(batch, mode="teacher", generator=torch.Generator().manual_seed(0))["loss"]
                  for model in (plain, off)]
        self.assertTrue(torch.equal(losses[0], losses[1]))

    def test_enabled_build_needs_a_store_and_a_valid_config(self) -> None:
        with self.assertRaises(ValueError):
            build_model(tiny_config("D-noask"), span_config())
        for bad in (dict(tokens_per_card=1.0), dict(max_span=0), dict(w_rate=-1.0), dict(newline_id=-1),
                    dict(base_logit=float("nan"))):
            with self.assertRaises(ValueError, msg=str(bad)):
                SpanConfig(**bad)


class ConstructionTest(unittest.TestCase):
    def test_construction_keeps_the_random_stream_and_every_shared_weight(self) -> None:
        plain = plain_model()
        after_plain = torch.get_rng_state()
        span = span_model()
        self.assertTrue(torch.equal(torch.get_rng_state(), after_plain))
        shared, mine = plain.state_dict(), span.state_dict()
        self.assertEqual({name.removeprefix("writer.") for name in mine.keys() - shared.keys()}, GATE)
        self.assertEqual(shared.keys() - mine.keys(), set())
        for name, tensor in shared.items():
            self.assertTrue(torch.equal(tensor, mine[name]), name)
        d = span.config.d_model
        self.assertEqual(span.num_parameters() - plain.num_parameters(), 2 * d + 2)
        writer = span.writer
        self.assertEqual(float(writer.gate.weight.detach().abs().max()), 0.0)
        self.assertEqual(float(writer.gate.bias.detach()), -4.0)
        self.assertEqual(float(writer.newline_weight.detach()), 8.0)


class BranchPointTest(unittest.TestCase):
    def test_a_loaded_parent_is_the_same_function(self) -> None:
        batch = synthetic_batch(visits=2, lines=24, seed=2)
        parent = eager(plain_model(3)).eval()
        child = span_model(7)
        missing, unexpected = child.load_state_dict(parent.state_dict(), strict=False)
        self.assertEqual({name.removeprefix("writer.") for name in missing}, GATE)
        self.assertEqual(unexpected, [])
        child.writer.init_gate()
        child.eval()
        a, b = store_of(parent, batch), store_of(child, batch)
        self.assertTrue(torch.equal(b.valid, batch.card_end))
        bi, ei = torch.nonzero(b.valid, as_tuple=True)
        line = batch.line_of[bi, ei]
        for name in ("keys", "values"):
            torch.testing.assert_close(getattr(b, name)[bi, ei], getattr(a, name)[bi, line], rtol=0, atol=1e-6)
        for name in ("tags", "ents", "line_start", "line_len"):
            self.assertTrue(torch.equal(getattr(b, name)[bi, ei], getattr(a, name)[bi, line]), name)
        self.assertTrue(torch.equal(b.card_line[bi, ei], line))
        self.assertTrue(torch.equal(b.first_line[bi, ei], line))
        gold_a = a.gold(batch.gold_lines, batch.q_visit, batch.q_line)
        gold_b = b.gold(batch.gold_lines, batch.q_visit, batch.q_line)
        self.assertEqual(int(gold_b[2].sum()), 0)
        self.assertTrue(torch.equal(gold_a[1], gold_b[1]))
        for q in range(batch.size[2]):          # span G = the plain G, columns mapped line -> card end
            row = int(batch.q_visit[q])
            want = {int(torch.nonzero(batch.card_end[row] & (batch.line_of[row] == l)).item())
                    for l in torch.nonzero(gold_a[0][q, :-1]).flatten().tolist()}
            got = set(torch.nonzero(gold_b[0][q, :-1]).flatten().tolist())
            self.assertEqual(got, want)
            self.assertEqual(bool(gold_b[0][q, -1]), bool(gold_a[0][q, -1]))
        with torch.no_grad():
            x, y = parent.answer(batch), child.answer(batch)
        self.assertTrue(torch.equal(x.tokens, y.tokens))
        self.assertTrue(torch.equal(x.lengths, y.lengths))
        self.assertTrue(torch.equal(x.loops, y.loops))
        self.assertTrue(torch.equal(x.first_top, y.first_top))
        self.assertTrue(torch.equal(x.fetched, y.fetched))
        self.assertTrue((x.first_top >= 0).any() and x.loops.max() > 1)


class SoftSurrogateTest(unittest.TestCase):
    def test_matches_a_naive_reference(self) -> None:
        g = torch.Generator().manual_seed(0)
        batch, length, d, window = 2, 30, 8, 6
        hidden = torch.randn(batch, length, d, generator=g)
        score = torch.randn(batch, length, generator=g)
        logit = (torch.randn(batch, length, generator=g) * 3).requires_grad_()
        cardable = torch.rand(batch, length, generator=g) > 0.15
        region = (cardable & F.pad(~cardable[:, :-1], (1, 0), value=True)).long().cumsum(1)
        rows, ends = torch.nonzero(cardable, as_tuple=True)
        soft = soft_pool(hidden, score, log_stay(logit), cardable, region, rows, ends, window)
        lam = torch.log1p(-torch.sigmoid(logit.detach().double())).clamp_min(-30.0)
        clipped = 0
        for i, (b, e) in enumerate(zip(rows.tolist(), ends.tolist())):
            keep = [t for t in range(max(0, e - window + 1), e + 1)
                    if cardable[b, t] and region[b, t] == region[b, e]]
            clipped += len(keep) < min(window, e + 1)
            logw = torch.stack([score[b, t].double() + lam[b, t + 1:e + 1].sum() for t in keep])
            expected = (torch.softmax(logw, 0).unsqueeze(1) * hidden[b, keep].double()).sum(0)
            torch.testing.assert_close(soft[i].double(), expected, rtol=0, atol=1e-5)
        self.assertGreater(clipped, 3)                      # walls and row starts clip some windows
        soft.sum().backward()
        self.assertTrue(torch.isfinite(logit.grad).all() and float(logit.grad.abs().max()) > 0.0)

    def test_saturated_gates_give_the_hard_pool(self) -> None:
        batch = synthetic_batch(visits=2, lines=16, seed=3)
        model = span_model(1).eval()
        with torch.no_grad():
            model.writer.gate.weight.zero_()
            model.writer.gate.bias.fill_(-50.0)
            model.writer.newline_weight.fill_(100.0)
            hidden = model.read(batch)
            store = model.writer(hidden, batch)
            writer = model.writer
            after = F.pad(batch.tokens[:, :-1] == NEWLINE, (1, 0), value=False)
            logit = writer.gate.bias + writer.newline_weight * after.float()
            self.assertTrue(((logit.abs() == 50.0)).all())
            cardable = (batch.line_of >= 0) & ~batch.line_is_question.gather(1, batch.line_of.clamp_min(0))
            region = (cardable & F.pad(~cardable[:, :-1], (1, 0), value=True)).long().cumsum(1)
            score = writer.pool(hidden).squeeze(-1)
            rows, ends = torch.nonzero(store.valid, as_tuple=True)
            soft = soft_pool(hidden, score, log_stay(logit), cardable, region, rows, ends, 64)
            for i, (b, e) in enumerate(zip(rows.tolist(), ends.tolist())):
                first = int(store.line_start[b, e])
                weight = torch.softmax(score[b, first:e + 1], 0)
                hard = (weight.unsqueeze(1) * hidden[b, first:e + 1]).sum(0)
                torch.testing.assert_close(soft[i], hard, rtol=0, atol=1e-5)
            torch.testing.assert_close(F.normalize(writer.key(soft), dim=-1), store.keys[rows, ends],
                                       rtol=0, atol=1e-5)

    def test_forward_value_is_unchanged_and_the_gate_gets_a_gradient(self) -> None:
        batch = synthetic_batch(seed=4)
        model = variable_model(2)
        model.train()
        hidden = model.read(batch)
        trained = model.writer(hidden, batch)
        with torch.no_grad():
            model.eval()
            evaluated = model.writer(hidden.detach(), batch)
        self.assertTrue(torch.equal(trained.keys, evaluated.keys))
        self.assertTrue(torch.equal(trained.values, evaluated.values))
        self.assertTrue(torch.equal(trained.valid, evaluated.valid))
        self.assertTrue(trained.keys.requires_grad and not evaluated.keys.requires_grad)
        for gate in (span_model(5), variable_model(5)):
            gate.train()
            out = gate(batch, mode="teacher", generator=torch.Generator().manual_seed(0))
            out["loss"].backward()
            weight, newline = gate.writer.gate.weight.grad, gate.writer.newline_weight.grad
            self.assertTrue(torch.isfinite(weight).all() and float(weight.abs().max()) > 0.0)
            self.assertTrue(torch.isfinite(newline))
            self.assertTrue(all(torch.isfinite(p.grad).all() for p in gate.parameters() if p.grad is not None))


class LayoutTest(unittest.TestCase):
    def test_variable_layout_merges_splits_and_respects_walls(self) -> None:
        batch = synthetic_batch(visits=3, lines=20, seed=5)
        model = variable_model(0)
        store = store_of(model, batch)
        question = batch.line_is_question.gather(1, batch.line_of.clamp_min(0)) | (batch.line_of < 0)
        rows, ends = torch.nonzero(store.valid, as_tuple=True)
        starts, lengths = store.line_start[rows, ends], store.line_len[rows, ends]
        self.assertTrue((lengths <= model.span.max_span).all())
        self.assertTrue((lengths == ends - starts + 1).all())
        self.assertGreater(int((store.first_line[rows, ends] != store.card_line[rows, ends]).sum()), 0)   # merged
        split = 0
        for b, e, s in zip(rows.tolist(), ends.tolist(), starts.tolist()):
            self.assertTrue((store.card_of[b, s:e + 1] == e).all())
            self.assertFalse(bool(question[b, s:e + 1].any()))                      # no question or padding token
            lines = batch.line_of[b, s:e + 1]
            self.assertTrue(bool((~batch.line_is_question[b, lines]).all()))
            # a card that does not cover its first/last line whole cuts a line in two
            line_end = int(batch.line_start[b, lines[-1]]) + int((batch.line_of[b] == lines[-1]).sum()) - 1
            split += int(s > int(batch.line_start[b, lines[0]]) or e < line_end)
        self.assertGreater(split, 0)
        self.assertTrue(bool((store.card_of[question] == -1).all()))
        self.assertTrue(bool((store.card_of[~question] >= 0).all()))               # every other token is in a card
        report = card_economy(model, [batch])
        self.assertGreater(report["merged"], 0.0)
        self.assertGreater(report["split_lines"], 0.0)
        self.assertLess(report["line_aligned"], 1.0)

    def test_the_cap_cuts_long_runs(self) -> None:
        batch = synthetic_batch(visits=2, lines=12, seed=6)
        model = span_model(0, max_span=3).eval()
        store = store_of(model, batch)
        self.assertLessEqual(int(store.line_len.max()), 3)
        self.assertTrue(torch.equal(store.card_of >= 0,
                                    (batch.line_of >= 0) & ~batch.line_is_question.gather(
                                        1, batch.line_of.clamp_min(0))))

    def test_cards_before_a_question_ignore_everything_after_its_line(self) -> None:
        batch = synthetic_batch(visits=2, lines=24, seed=8)
        model = variable_model(1)
        before = store_of(model, batch)
        generator = torch.Generator().manual_seed(0)
        checked = 0
        for q in range(0, batch.size[2], 2):
            visit, line = int(batch.q_visit[q]), int(batch.q_line[q])
            cut, end = int(batch.line_start[visit, line]), int(batch.lengths[visit])
            tokens = batch.tokens.clone()
            tokens[visit, cut:end] = torch.randint(10, VOCAB, (end - cut,), generator=generator)
            moved = store_of(model, type(batch)(**{**batch.__dict__, "tokens": tokens}))
            self.assertTrue(torch.equal(moved.valid[visit, :cut], before.valid[visit, :cut]))
            self.assertTrue(torch.equal(moved.card_line[visit, :cut], before.card_line[visit, :cut]))
            self.assertTrue(torch.equal(moved.line_start[visit, :cut], before.line_start[visit, :cut]))
            keep = before.valid[visit] & (before.card_line[visit] < line)
            self.assertTrue(bool(keep.any()))
            for name in ("keys", "values"):
                torch.testing.assert_close(getattr(moved, name)[visit][keep], getattr(before, name)[visit][keep],
                                           rtol=0, atol=1e-6)
            checked += 1
        self.assertGreater(checked, 2)


class GoldAndWipeTest(unittest.TestCase):
    def test_gold_is_token_overlap_with_eligible_cards(self) -> None:
        store = manual_store(TOKEN_LINE, CARDS)
        null = store.null
        self.assertEqual((store.lines, null), (16, 16))
        q_visit = torch.zeros(6, dtype=torch.long)
        q_line = torch.tensor([3, 3, 3, 3, 2, 2])
        gold_lines = gold_rows([[1], [2], [], [0, 3], [1], [2]])
        gold, told, missing = store.gold(gold_lines, q_visit, q_line)
        self.assertIs(store.last_gold, gold)
        columns = [set(torch.nonzero(row).flatten().tolist()) for row in gold]
        self.assertEqual(columns[0], {7})                    # merge: the card holding lines 0-1 is gold for line 1
        self.assertEqual(columns[1], {11})                   # split 2 + 2: one gold card per line, tie -> later
        self.assertEqual(columns[2], {null})                 # never told: only NULL
        self.assertEqual(columns[3], {7})
        self.assertEqual(columns[4], {7})
        self.assertEqual(columns[5], set())
        self.assertEqual(told.tolist(), [True, True, False, True, True, True])
        self.assertEqual(missing.tolist(), [0, 0, 0, 1, 0, 1])    # the question's own line and the line it cannot see
        eligible = store.eligible(q_visit, q_line)
        self.assertEqual([set(torch.nonzero(row).flatten().tolist()) for row in eligible],
                         [{7, 9, 11, null}] * 4 + [{7, null}] * 2)
        fetched = torch.zeros(6, 17, dtype=torch.bool)
        fetched[0, 7] = fetched[0, null] = True
        again = store.eligible(q_visit, q_line, fetched)
        self.assertFalse(bool(again[0, 7]))
        self.assertTrue(bool(again[0, null]))                # NULL can always be fetched again

    def test_ages_keep_the_base_signature_for_one_visit(self) -> None:
        store = manual_store(TOKEN_LINE, CARDS)
        q_line = torch.tensor([3, 2])
        torch.testing.assert_close(store.ages(q_line, 16), store.ages(q_line, 16, torch.zeros(2, dtype=torch.long)))
        two = store_of(span_model(0), synthetic_batch(visits=2, seed=1))
        with self.assertRaises(ValueError):
            two.ages(q_line, 16)

    def test_one_gold_card_per_gold_line(self) -> None:
        """Re-review blocker: span gold must never outnumber the gold lines the teacher schedule counts."""
        q_visit, q_line = torch.zeros(2, dtype=torch.long), torch.tensor([3, 3])
        for cards, expected in (([(0, 7), (8, 8), (9, 11)], 11), ([(0, 7), (8, 10), (11, 11)], 10)):
            store = manual_store(TOKEN_LINE, cards)
            gold, _, missing = store.gold(gold_rows([[2], [0, 1, 2]]), q_visit, q_line)
            columns = [set(torch.nonzero(row).flatten().tolist()) for row in gold]
            self.assertEqual(columns[0], {expected})          # the piece holding most of line 2
            self.assertEqual(columns[1], {7, expected})       # lines 0 and 1 share the merged card: gold once
            self.assertEqual(missing.tolist(), [0, 0])

    def test_teacher_schedule_reaches_every_gold_card_on_split_layouts(self) -> None:
        """With the gate splitting lines, the line-counted teacher loops and gold preload still cover every gold
        card, so the span arm never trains against an unreachable ASK target."""
        model = span_model(4, max_span=3)                     # the cap splits most lines into 2-3 cards
        model.train()
        for seed in range(3):
            batch = synthetic_batch(visits=3, lines=24, seed=20 + seed)
            store = store_of(model, batch)
            self.assertGreater(int(store.valid.sum()), int((~batch.line_is_question & (batch.line_start >= 0)).sum()))
            gold, told, missing = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
            cards = gold[:, :store.null].sum(1)
            lines = (batch.gold_lines >= 0).sum(1)
            self.assertTrue(bool((cards <= lines).all()))
            self.assertTrue(bool((cards[told] >= 1).all()))
            self.assertEqual(int(missing.sum()), 0)
            for mode in ("gold", "teacher"):
                with model.scope() as capture:
                    capture["trace"] = []
                    model(batch, mode=mode, generator=torch.Generator().manual_seed(seed))
                fetched = torch.zeros_like(gold)
                for index, picked in capture["trace"]:
                    real = picked >= 0
                    fetched[index.unsqueeze(1).expand_as(picked)[real], picked[real]] = True
                self.assertTrue(bool((capture["gold_matrix"] == gold).all()), mode)
                unreached = (gold & ~fetched)[told]
                self.assertFalse(bool(unreached.any()), (mode, seed))

    def test_synthetic_batches_have_no_missing_gold(self) -> None:
        for model in (span_model(0), variable_model(0)):
            for seed in (1, 2, 3):
                batch = synthetic_batch(visits=2, lines=20, seed=seed)
                store = store_of(model, batch)
                gold, told, missing = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
                self.assertEqual(int(missing.sum()), 0)
                self.assertTrue(torch.equal(gold[:, store.null], ~told))
                self.assertTrue(bool(gold[told][:, :store.null].any(1).all()))
                eligible = store.eligible(batch.q_visit, batch.q_line)
                self.assertFalse(bool((gold & ~eligible).any()))
                self.assertFalse(bool((eligible[:, :-1] & (store.card_line[batch.q_visit]
                                                          >= batch.q_line.unsqueeze(1))).any()))

    def test_wipe_removes_cards_that_start_before_the_window(self) -> None:
        store = manual_store(TOKEN_LINE, CARDS)
        q_visit, q_line = torch.zeros(2, dtype=torch.long), torch.tensor([3, 3])
        wiped = store.wipe(torch.tensor([1, 0]))
        self.assertGreaterEqual(int(store.card_line[0, 7]), 1)       # the merged card ENDS inside the window ...
        eligible = wiped.eligible(q_visit, q_line)
        self.assertFalse(bool(eligible[0, 7]))                       # ... but starts before it: gone
        self.assertTrue(bool(eligible[0, 9]) and bool(eligible[0, 11]) and bool(eligible[0, store.null]))
        self.assertTrue(bool(eligible[1, 7]))                        # floor 0 keeps it
        gold, _, missing = wiped.gold(gold_rows([[1], [1]]), q_visit, q_line)
        self.assertFalse(bool(gold[0, :-1].any()))
        self.assertEqual(missing.tolist(), [1, 0])
        self.assertEqual(wiped.fingerprint(), wiped.fingerprint())
        self.assertNotEqual(wiped.fingerprint(), store.fingerprint())


class RateLossTest(unittest.TestCase):
    def test_minimum_is_one_at_the_target_rate(self) -> None:
        for n in (2.0, 12.0, 30.0):
            self.assertAlmostEqual(rate_loss(1 / n, 1 / n, n), 1.0, places=6)
            for x in (0.0, 0.5 / n, 2 / n, 0.5, 1.0):
                if abs(x - 1 / n) > 1e-9:
                    self.assertGreater(rate_loss(x, x, n), 1.0 + 1e-6, (n, x))     # along F = G the minimum is 1
            # The function is bilinear, so 1 is a minimum only along F = G (a saddle in the plane): flat in G at
            # F = 1 / N, below 1 for F > G. G alone receives the gradient (F is a count): d/dG = N F - 1.
            self.assertAlmostEqual(rate_loss(1 / n, 0.9, n), 1.0, places=6)
            self.assertAlmostEqual(rate_loss(1 / n, 0.0, n), 1.0, places=6)
            self.assertLess(rate_loss(2 / n, 0.0, n), 1.0)
            g = torch.tensor(0.3, requires_grad=True)
            rate_loss(2 / n, g, n).backward()
            self.assertGreater(float(g.grad), 0.0)                        # F > 1 / N pushes G down
            g = torch.tensor(0.3, requires_grad=True)
            rate_loss(0.5 / n, g, n).backward()
            self.assertLess(float(g.grad), 0.0)                           # F < 1 / N pushes G up
        batch = synthetic_batch(seed=1)
        model = span_model(0)
        model.train()
        hidden = model.read(batch)
        store = model.writer(hidden, batch)
        lay = model.writer.layout(hidden, batch)
        soft_starts = torch.where(lay.forced, torch.ones_like(lay.p), lay.p)[lay.cardable].mean()  # forced = 1
        self.assertAlmostEqual(float(store.rate.detach()),
                               rate_loss(float(store.stats["start_rate"]), float(soft_starts),
                                         model.span.tokens_per_card), places=5)


class ModelTest(unittest.TestCase):
    def test_every_mode_trains_and_reports_the_gate(self) -> None:
        model, batch = variable_model(1), synthetic_batch(seed=2)
        model.train()
        generator = torch.Generator().manual_seed(0)
        for mode, p_own in (("gold", 0.0), ("teacher", 0.0), ("own", 0.5)):
            model.zero_grad(set_to_none=True)
            with model.scope() as capture:
                out = model(batch, mode=mode, p_own=p_own, generator=generator)
            self.assertNotIn(SpanCardMini.CAPTURE, vars(model))
            for name in ("lm", "ask", "ans", "halt", "loss", "rate"):
                self.assertTrue(torch.isfinite(out[name]), (mode, name))
            for name in ("start_rate", "gate_mean", "tokens_per_card", "cards_per_visit", "newline_precision",
                         "newline_recall", "gate_mid", "ents_overflow", "rate"):
                self.assertIn(f"span_{name}", out["metrics"])
            self.assertEqual(int(out["metrics"]["gold_missing"]), 0)
            out["loss"].backward()
            self.assertTrue(all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None))
            self.assertEqual(capture["gold_matrix"].shape, (batch.size[2], batch.tokens.shape[1] + 1))
            self.assertNotIn("store", capture)
        loss = model(batch, mode="teacher", generator=torch.Generator().manual_seed(0))
        base = PremonitionMini.forward(model, batch, mode="teacher", generator=torch.Generator().manual_seed(0))
        self.assertAlmostEqual(float(loss["loss"] - base["loss"]), model.span.w_rate * float(loss["rate"]), places=4)

    def test_answer_reports_lines_not_cards(self) -> None:
        batch = synthetic_batch(visits=2, lines=24, seed=6)
        lines = batch.line_start.shape[1]
        for model in (eager(span_model(0)), eager(variable_model(0))):
            model.eval()
            window = (batch.q_line - 6).clamp_min(1)
            for wipe in (None, "store", "full"):
                with model.scope() as capture:
                    answers = model.answer(batch, wipe=wipe, window_line=None if wipe is None else window)
                self.assertEqual(answers.fetched.shape, (batch.size[2], lines + 1))
                self.assertTrue(((answers.first_top >= -1) & (answers.first_top < lines)).all(), wipe)
                self.assertTrue(bool((answers.first_top >= 0).any()), wipe)
                raw_top, raw_fetched = capture["raw_answer"]
                self.assertEqual(raw_fetched.shape[0], batch.size[2])
                self.assertEqual(int((raw_top >= 0).sum()), int((answers.first_top >= 0).sum()))
                fetched = answers.fetched[:, :-1]
                self.assertTrue(bool(fetched.any()))
                self.assertFalse(bool((fetched & (torch.arange(lines) >= batch.q_line.unsqueeze(1))).any()))
                if wipe:
                    self.assertFalse(bool((fetched & (torch.arange(lines) < window.unsqueeze(1))).any()), wipe)
            self.assertNotIn(SpanCardMini.CAPTURE, vars(model))


class EconomyTest(unittest.TestCase):
    def test_line_layouts_are_fully_aligned(self) -> None:
        batches = [synthetic_batch(visits=2, lines=20, seed=s) for s in (1, 2)]
        reports = {}
        for name, model in (("plain", eager(plain_model(0))), ("span", eager(span_model(0)))):
            model.train()
            reports[name] = report = card_economy(model, batches)
            self.assertTrue(model.training)
            self.assertNotIn("_insert", model.__dict__)
            self.assertEqual(report["layout"], "line" if name == "plain" else "span")
            self.assertEqual((report["line_aligned"], report["merged"], report["split_lines"]), (1.0, 0.0, 0.0))
            self.assertEqual((report["newline_precision"], report["newline_recall"]), (1.0, 1.0))
            self.assertEqual(report["ents_overflow"], 0.0)
            self.assertEqual(report["gold_missing"], 0)
            self.assertEqual(sum(report["tokens_per_card"]["hist"].values()), report["cards"])
            self.assertEqual(report["visits"], 4)
            self.assertEqual(report["questions"], sum(b.size[2] for b in batches))
            self.assertGreater(report["asked_rate"], 0.0)
            self.assertGreater(report["fetches_per_q"], 0.0)
            self.assertGreater(report["gold_cards_per_told_q"], 0.0)
            self.assertTrue(0.0 <= report["null_share"] <= 1.0)
            self.assertTrue(0.0 <= report["first_ask_recall"] <= 1.0)
        a, b = reports["plain"], reports["span"]
        for key in ("visits", "cards", "cards_per_visit", "tokens_per_card", "gold_cards_per_told_q",
                    "gold_card_tokens", "asked_rate", "fetches_per_q", "null_share", "first_ask_recall",
                    "full_gold_fetched", "questions", "told"):
            self.assertEqual(a[key], b[key], key)

    def test_a_variable_layout_is_visible(self) -> None:
        batch = synthetic_batch(visits=2, lines=20, seed=3)
        report = card_economy(variable_model(0), [batch])
        self.assertEqual(report["layout"], "span")
        self.assertGreater(report["merged"], 0.0)
        self.assertGreater(report["cards"], 0)
        self.assertLessEqual(report["tokens_per_card"]["mean"], 10.0)
        self.assertLess(report["newline_recall"], 1.0)
        self.assertEqual(report["gold_missing"], 0)

    def test_tokens_per_line_and_identity(self) -> None:
        cache = SimpleNamespace(line_offsets=torch.tensor([0, 4, 10, 12, 20], dtype=torch.int32),
                                line_is_question=torch.tensor([False, False, True, False]))
        self.assertAlmostEqual(tokens_per_line(cache), (4 + 6 + 8) / 3)
        ident = span_cards.identity(span_config(), tiny_config())
        self.assertEqual((ident["variant"], ident["purpose"]), ("D-span-cards", "diagnostic"))
        self.assertEqual(len(ident["source_sha256"]), 64)


class TrainerTest(unittest.TestCase):
    def test_layout_stats_mirror_card_stats_on_line_cards(self) -> None:
        batch = synthetic_batch(visits=2, lines=20, seed=4)
        model = plain_model(0)
        with InsertLog(model) as log:
            out = model(batch, mode="teacher", generator=torch.Generator().manual_seed(0))
        gold, _, _ = store_of(model, batch).gold(batch.gold_lines, batch.q_visit, batch.q_line)
        loops = torch.full((batch.size[2],), 4)
        expected = card_stats(log.calls, batch, loops, 16, offset=1)
        self.assertEqual(layout_card_stats(log.calls, gold, batch, loops, 16, offset=1), expected)
        self.assertEqual(set(summarize_cards(expected)), set(summarize_cards(
            layout_card_stats(log.calls, gold, batch, loops, 16, offset=1))))
        del out

    def test_trainer_logs_layout_cards_and_gate_statistics(self) -> None:
        batches = [synthetic_batch(visits=2, lines=14, seed=s) for s in range(4)]
        model = span_model(0)
        trainer = SpanTrainer(model, mini_train_config(lr=1e-3, warmup_steps=2, log_every=2), "cpu",
                              flop_budget=1.0, seed=0)
        trainer.calibrate(batches[:2])
        trainer.flop_budget = budget_for_steps(trainer, batches[:2], 6)
        report = trainer.train(batches * 3, max_steps=4)
        self.assertEqual(report["steps"], 4)
        self.assertEqual(report["loop_mismatches"], 0)
        self.assertNotIn(SpanCardMini.CAPTURE, vars(model))
        self.assertTrue(trainer.span_log)
        self.assertEqual([r["step"] for r in trainer.span_log], [2, 4])
        for entry in trainer.span_log:
            for key in ("span_start_rate", "span_gate_mean", "span_tokens_per_card", "rate"):
                self.assertIn(key, entry)
        logged = [r for r in trainer.history if "cards" in r]
        self.assertTrue(logged)
        expected = set(summarize_cards(card_stats([], batches[0], torch.zeros(batches[0].size[2], dtype=torch.long),
                                                  16, offset=1)))
        for record in logged:
            self.assertEqual(set(record["cards"]), expected)
        self.assertTrue(all(torch.isfinite(p).all() for p in model.parameters()))


class ReviewRegressionTest(unittest.TestCase):
    """The code review's blocking and correctness findings 1-3 (design/span-cards; review of 2026-10-18)."""

    def test_no_state_survives_a_call_so_read_only_evaluation_works(self) -> None:
        """Finding 1: tensors left on the model made every read_only evaluation raise."""
        batches = [synthetic_batch(visits=2, lines=14, seed=s) for s in range(4)]
        model = variable_model(0)
        model.train()
        model(batches[0], mode="teacher", generator=torch.Generator().manual_seed(0))["loss"].backward()
        before = dict(vars(model))
        with read_only(model):                                           # raised ReadOnlyViolation before
            model.answer(batches[1])
            answer_with_gold(model, batches[1])
            validate(model, batches[2:3])
            card_economy(model, batches[2:3])
        self.assertEqual(set(vars(model)), set(before))
        self.assertNotIn(SpanCardMini.CAPTURE, vars(model))
        for module in model.modules():
            self.assertFalse([name for name, value in vars(module).items() if torch.is_tensor(value)],
                             type(module).__name__)
        trainer = SpanTrainer(span_model(1), mini_train_config(lr=1e-3, warmup_steps=2, log_every=2, eval_every=2),
                              "cpu", flop_budget=1.0, seed=0)
        trainer.calibrate(batches[:2])
        trainer.flop_budget = budget_for_steps(trainer, batches[:2], 6)
        report = trainer.train(batches * 2, max_steps=4, evaluate=validation_hook(batches[:1]))
        self.assertEqual(report["steps"], 4)
        self.assertEqual(len([r for r in trainer.history if "eval" in r]), 2)

    def test_the_reader_gets_exactly_the_hard_pools_gradient(self) -> None:
        """Finding 2: the gate read undetached reader states, so the surrogate and the rate loss trained the reader."""
        batch = synthetic_batch(visits=2, lines=16, seed=8)
        model = variable_model(3)
        writer = model.writer
        hidden = model.read(batch).detach().requires_grad_()
        writer.train()
        trained = writer(hidden, batch)
        loss = trained.keys.sum() + 0.5 * trained.values.sum() + 10.0 * trained.rate
        reader_grad, gate_grad = torch.autograd.grad(loss, (hidden, writer.gate.weight))
        writer.eval()
        with torch.enable_grad():
            hard = writer(hidden, batch)                                # no surrogate in eval; rate left out
            hard_grad, = torch.autograd.grad(hard.keys.sum() + 0.5 * hard.values.sum(), hidden)
        self.assertTrue(torch.equal(trained.valid, hard.valid))
        torch.testing.assert_close(reader_grad, hard_grad, rtol=0, atol=1e-6)
        self.assertGreater(float(gate_grad.abs().max()), 0.0)          # the gate still learns
        rate_grad, = torch.autograd.grad(writer(hidden, batch).rate, hidden, allow_unused=True)
        self.assertTrue(rate_grad is None or float(rate_grad.abs().max()) == 0.0)

    def test_cap_starts_are_hard_boundaries_in_the_surrogate(self) -> None:
        """Finding 3: a start forced by the max_span cap had no gate probability, so the surrogate leaked the
        previous card into the next one even with saturated gates."""
        batch = synthetic_batch(visits=2, lines=16, seed=3)
        model = span_model(1, max_span=3).eval()
        writer = model.writer
        with torch.no_grad():
            writer.gate.weight.zero_()
            writer.gate.bias.fill_(-50.0)
            writer.newline_weight.fill_(100.0)
            hidden = model.read(batch)
            lay = writer.layout(hidden, batch)
            store = writer(hidden, batch)
            capped = lay.forced & ~lay.after_wall
            self.assertGreater(int(capped.sum()), 5)                     # the cap really cuts lines here
            region = (lay.cardable & lay.after_wall).long().cumsum(1)
            score = writer.pool(hidden).squeeze(-1)
            rows, ends = torch.nonzero(store.valid, as_tuple=True)
            hard = []
            for b, e in zip(rows.tolist(), ends.tolist()):
                first = int(store.line_start[b, e])
                self.assertLessEqual(e - first + 1, 3)
                weight = torch.softmax(score[b, first:e + 1], 0)
                hard.append((weight.unsqueeze(1) * hidden[b, first:e + 1]).sum(0))
            hard = torch.stack(hard)
            soft = soft_pool(hidden, score, surrogate_stay(lay.logit, lay.forced), lay.cardable, region, rows,
                             ends, 3)
            torch.testing.assert_close(soft, hard, rtol=0, atol=1e-5)
            leaky = soft_pool(hidden, score, log_stay(lay.logit), lay.cardable, region, rows, ends, 3)
            self.assertGreater(float((leaky - hard).abs().max()), 1e-2)  # the old stay leaked across the cap


class RoundThreeRegressionTest(unittest.TestCase):
    """Round-3 review: finding 1 (the rate loss counted forced starts) and minor findings 3-4."""

    @staticmethod
    def capped_layout(seed: int = 0):
        """A layout with wall starts and cap starts (max_span 3), and its gate logits kept for their gradient."""
        batch = synthetic_batch(visits=2, lines=16, seed=4)
        model = span_model(seed, max_span=3)
        model.train()
        lay = model.writer.layout(model.read(batch), batch)
        lay.logit.retain_grad()
        return model, batch, lay

    def test_the_rate_gradient_skips_forced_starts(self) -> None:
        """Finding 1: G held the gate's p at forced starts, so the gate got rate gradient where its output cannot
        change the layout."""
        model, batch, lay = self.capped_layout()
        forced, decided = lay.forced, lay.cardable & ~lay.forced
        self.assertGreater(int((forced & lay.after_wall).sum()), 0)                 # wall starts
        self.assertGreater(int((forced & ~lay.after_wall).sum()), 5)                # cap starts
        span_cards.layout_rate(lay, 12.0).backward(retain_graph=True)
        grad = lay.logit.grad.clone()
        self.assertEqual(float(grad[forced].abs().max()), 0.0)
        self.assertGreater(float(grad[decided].abs().min()), 0.0)
        lay.logit.grad = None
        start_rate = lay.start[lay.cardable].float().mean()
        rate_loss(start_rate, lay.p[lay.cardable].mean(), 12.0).backward()          # the old G
        self.assertGreater(float(lay.logit.grad[forced].abs().max()), 0.0)

    def test_the_target_is_unchanged_and_has_no_pole(self) -> None:
        """Forced starts still use up the budget: dL/dG is zero exactly at cardable / N - forced chosen starts (the
        proposal's rescaled N' = decided / (cardable / N - forced) has the same zero and sign), G = F at saturated
        gates, and the loss stays finite when the forced starts alone exceed the budget (N' has a pole there)."""
        batch = synthetic_batch(visits=2, lines=24, seed=2)
        model = span_model(0)
        with torch.no_grad():
            model.writer.gate.bias.fill_(-50.0)
            model.writer.newline_weight.fill_(100.0)
        model.train()
        lay = model.writer.layout(model.read(batch), batch)
        cardable = float(lay.cardable.sum())
        starts, forced = float(lay.start.sum()), float(lay.forced.sum())
        decided, chosen = cardable - forced, starts - forced
        self.assertGreater(chosen, 0.0)
        gate = torch.where(lay.forced, torch.ones_like(lay.p), lay.p)[lay.cardable].mean().detach()
        self.assertAlmostEqual(float(gate), starts / cardable, places=6)            # G = F when saturated
        for n in (cardable / starts, 0.5 * cardable / starts, 2.0 * cardable / starts, 1e6):
            g = torch.tensor(float(gate), requires_grad=True)
            loss = rate_loss(starts / cardable, g, n)
            self.assertTrue(torch.isfinite(loss))
            loss.backward()
            budget = cardable / n - forced                                          # chosen starts on target
            if abs(n - cardable / starts) < 1e-9:
                self.assertAlmostEqual(float(g.grad), 0.0, places=5)
                self.assertAlmostEqual(budget, chosen, places=6)
            elif budget > 0:
                rescaled = decided / budget
                self.assertEqual(float(g.grad) > 0, rescaled * chosen / decided - 1 > 0)
            else:
                self.assertGreater(float(g.grad), 0.0)                              # fewer starts, finitely
        model.zero_grad(set_to_none=True)
        span_cards.layout_rate(lay, cardable / starts).backward()
        for name in ("bias", "weight"):
            self.assertLess(float(getattr(model.writer.gate, name).grad.abs().max()), 1e-5, name)

    def test_caller_weights_set_the_rate_weight(self) -> None:
        """Minor 3: forward added w_rate x rate whatever `weights` the caller passed."""
        model, batch = variable_model(1), synthetic_batch(seed=2)
        model.train()
        weights = {"lm": 1.0, "ans": 1.0, "ask": 0.0, "halt": 0.0}

        def loss(**extra: float) -> tuple[float, float]:
            out = model(batch, mode="gold", weights={**weights, **extra},
                        generator=torch.Generator().manual_seed(0))
            base = PremonitionMini.forward(model, batch, mode="gold", weights=dict(weights),
                                           generator=torch.Generator().manual_seed(0))
            return float((out["loss"] - base["loss"]).detach()), float(out["rate"].detach())

        off, _ = loss(rate=0.0)
        self.assertEqual(off, 0.0)
        double, rate = loss(rate=2.0)
        self.assertAlmostEqual(double, 2.0 * rate, places=4)
        default, rate = loss()
        self.assertAlmostEqual(default, model.span.w_rate * rate, places=4)

    def test_a_line_cut_by_the_batch_gets_no_card(self) -> None:
        """Minor 4: the span writer wrote a card for a line whose last token (`card_end`) is not in the batch."""
        full = synthetic_batch(visits=3, lines=12, seed=0)
        visit = next(v for v in range(3) if not bool(full.line_is_question[v, -1]))  # ends on a card line
        size = int(full.lengths[visit])
        cut, line = size - 2, full.line_is_question.shape[1] - 1                    # drop "... x \n" of the last line
        fields = dict(full.__dict__)
        for name, fill in (("tokens", 0), ("line_of", -1), ("card_end", False), ("lm_mask", False)):
            fields[name] = full.__dict__[name].clone()
            fields[name][visit, cut:size] = fill
        fields["lengths"] = full.lengths.clone()
        fields["lengths"][visit] = cut
        batch = type(full)(**fields)
        cut_tokens = (batch.line_of[visit] == line).nonzero().flatten()
        self.assertGreater(cut_tokens.numel(), 0)
        plain = store_of(eager(plain_model(3)), batch)
        self.assertFalse(bool(plain.valid[visit, line]))                            # the parent's rule
        for model in (eager(span_model(0)).eval(), variable_model(0)):
            before, after = store_of(model, full), store_of(model, batch)
            self.assertFalse(bool(after.card_of[visit, cut_tokens].ge(0).any()))
            self.assertFalse(bool((after.valid[visit] & (after.card_line[visit] == line)).any()))
            rows, ends = torch.nonzero(after.valid, as_tuple=True)
            self.assertTrue(bool(batch.card_end[rows].logical_and(
                batch.line_of[rows] == after.card_line[rows, ends].unsqueeze(1)).any(1).all()))
            keep = before.valid.clone()
            keep[visit] &= before.card_line[visit] < line
            self.assertTrue(torch.equal(after.valid, keep))                         # every other card unchanged
            torch.testing.assert_close(after.keys[keep], before.keys[keep], rtol=0, atol=1e-6)
        self.assertTrue(torch.equal(store_of(eager(span_model(0)).eval(), batch).valid, batch.card_end))


class RoundTripTest(unittest.TestCase):
    def test_state_dict_round_trip(self) -> None:
        batch = synthetic_batch(seed=7)
        source = eager(variable_model(0))
        fresh = eager(span_model(9))
        fresh.eval()
        self.assertFalse(torch.equal(fresh.writer.gate.weight, source.writer.gate.weight))
        fresh.load_state_dict(source.state_dict())
        eager(fresh)
        a, b = store_of(source, batch), store_of(fresh, batch)
        for name in ("keys", "values", "valid", "card_line", "first_line", "card_of", "ents"):
            self.assertTrue(torch.equal(getattr(a, name), getattr(b, name)), name)
        x, y = source.answer(batch), fresh.answer(batch)
        self.assertTrue(torch.equal(x.tokens, y.tokens))
        self.assertTrue(torch.equal(x.first_top, y.first_top))
        self.assertTrue(torch.equal(x.fetched, y.fetched))
        self.assertTrue(torch.equal(x.halt_prob, y.halt_prob))
        with self.assertRaises(RuntimeError):
            plain_model().load_state_dict(source.state_dict())


if __name__ == "__main__":
    unittest.main()
