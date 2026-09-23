"""Direct contextual-state reader (premonition/direct_reader.py; milestone-3 continuation). CPU; no training."""
from __future__ import annotations

from pathlib import Path
import random
import sys
import unittest

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402
import premonition_pool_controls as H  # noqa: E402

from learnlab.readonly import read_only  # noqa: E402
from premonition import direct_reader, toy_ladder  # noqa: E402
from premonition.model import PremonitionMini  # noqa: E402

H.L, H.R = L, R
SPEC = toy_ladder.LadderSpec()


def item(seed=3, training=True):
    return L.label_free_item(toy_ladder.make(SPEC, 4, random.Random(seed), training=training))


def build_direct(seed):
    torch.manual_seed(seed)
    base = PremonitionMini(H.answer_config())
    model = direct_reader.DirectReaderQReadMini(H.answer_config())
    model.load_state_dict(base.state_dict())
    model._nothink = True
    return model


def episodes(model, pooled, it, cards="all", seed=7):
    out = []
    for m in (model, pooled):
        ep, _, _, store = L.episode(m, it, cards=cards, generator=torch.Generator().manual_seed(seed), passes=0)
        out.append((ep, store))
    return out


class BuildTest(unittest.TestCase):
    def test_same_initial_weights_and_random_stream_as_the_pooled_arm(self):
        pooled = H.build("answer", "original", 1)
        after_pooled = torch.rand(4)
        direct = build_direct(1)                  # same construction order as H.build (base, then variant)
        after_direct = torch.rand(4)
        self.assertTrue(torch.equal(after_pooled, after_direct))
        sa, sb = pooled.state_dict(), direct.state_dict()
        self.assertEqual(set(sa), set(sb))                        # no new parameters
        self.assertTrue(all(torch.equal(sa[k], sb[k]) for k in sa))

    def test_line_positions_are_exactly_the_pooled_positions(self):
        batch = item()[0]
        table = direct_reader.line_positions(batch)
        for v in range(batch.tokens.shape[0]):
            for line in range(batch.line_start.shape[1]):
                want = (batch.line_of[v] == line).nonzero().squeeze(1).tolist()
                got = [p for p in table[v, line].tolist() if p >= 0]
                self.assertEqual(got, want)


class MemoryTest(unittest.TestCase):
    def setUp(self):
        self.direct, self.pooled = build_direct(0), H.build("answer", "original", 0)
        weight = torch.randn(self.pooled.writer.pool.weight.shape, generator=torch.Generator().manual_seed(11))
        with torch.no_grad():                                   # a non-uniform pool, identical in both arms
            for model in (self.direct, self.pooled):
                model.writer.pool.weight.copy_(weight)
        self.item = item()

    def test_pooled_row_is_the_pool_weighted_mean_of_the_direct_rows(self):
        (ep, store), (pep, _) = episodes(self.direct, self.pooled, self.item)
        batch, supplied, hops = self.item
        start, width = ep.direct_rows
        hidden = self.pooled.read(batch)
        score = self.pooled.writer.pool(hidden).squeeze(-1).float()
        order = torch.rand(supplied.shape, generator=torch.Generator().manual_seed(7)).argsort(1)
        chosen = supplied.gather(1, order)
        longest = width // chosen.shape[1]
        base = self.pooled._card_base
        checked = 0
        for q in range(chosen.shape[0]):
            v = int(batch.q_visit[q])
            for k in range(chosen.shape[1]):
                line = int(chosen[q, k])
                if line < 0:
                    continue
                pos = (batch.line_of[v] == line).nonzero().squeeze(1)
                w = torch.softmax(score[v, pos], 0)
                rows = ep.x[q, start + k * longest:start + k * longest + len(pos)]
                pooled_row = pep.x[q, base + int((chosen[q, :k] >= 0).sum())]
                self.assertTrue(torch.allclose((w.unsqueeze(1) * rows).sum(0), pooled_row, atol=1e-5))
                checked += 1
        self.assertGreater(checked, 10)

    def test_only_the_card_region_differs_and_pooled_rows_are_masked(self):
        (ep, _), (pep, _) = episodes(self.direct, self.pooled, self.item)
        base, cards = self.pooled._card_base, self.pooled.config.cards
        rows = pep.x.shape[1]
        self.assertTrue(torch.equal(ep.x[:, :rows], pep.x))           # slots bound with the same pooled values
        keep = torch.ones(rows, dtype=torch.bool)
        keep[base:base + cards] = False
        self.assertTrue(torch.equal(ep.valid[:, :rows][:, keep], pep.valid[:, keep]))
        self.assertFalse(bool(ep.valid[:, base:base + cards].any()))
        self.assertTrue(bool(pep.valid[:, base:base + cards].any()))
        batch, supplied, _ = self.item
        start, width = ep.direct_rows
        self.assertEqual(start, rows)
        lengths = torch.stack([(batch.line_of[int(batch.q_visit[q])].unsqueeze(0)
                                == supplied[q].clamp_min(0).unsqueeze(1)).sum(1) * (supplied[q] >= 0)
                               for q in range(supplied.shape[0])])
        self.assertTrue(torch.equal(ep.valid[:, start:].sum(1), lengths.sum(1)))
        self.assertTrue(torch.equal(ep.fetched, pep.fetched) and torch.equal(ep.count, pep.count))

    def test_no_cards_gives_the_baseline_episode_and_decode(self):
        (ep, _), (pep, _) = episodes(self.direct, self.pooled, self.item, cards="none")
        self.assertTrue(torch.equal(ep.x, pep.x) and torch.equal(ep.valid, pep.valid))
        batch = self.item[0]
        with torch.no_grad():
            a = self.direct._greedy(batch, ep, self.direct._mentions(batch), None)
            b = self.pooled._greedy(batch, pep, self.pooled._mentions(batch), None)
        self.assertTrue(torch.equal(a[0], b[0]) and torch.equal(a[1], b[1]))

    def test_token_rows_come_from_earlier_fact_lines_and_later_text_cannot_leak(self):
        batch, supplied, _ = self.item
        self.assertFalse(bool(batch.line_is_question[batch.q_visit.unsqueeze(1), supplied.clamp_min(0)]
                              [supplied >= 0].any()))
        self.assertTrue(bool((supplied[supplied >= 0].view(-1)
                              < batch.q_line.unsqueeze(1).expand_as(supplied)[supplied >= 0]).all()))
        # label-free: every question line reads "... [answer] <newline>"; the answer and feedback are gone
        for q in range(batch.q_visit.shape[0]):
            v, end = int(batch.q_visit[q]), int(batch.q_span[q, 1])
            self.assertEqual(int(batch.tokens[v, end - 1]), toy_ladder.ANSWER)
            self.assertEqual(int(batch.tokens[v, end]), toy_ladder.NEWLINE)
            self.assertNotIn(toy_ladder.FEEDBACK, batch.tokens[v, :int(batch.lengths[v])].tolist())
        # perturb everything after the first question of visit 0: its memory and answer logits must not move
        q = int((batch.q_visit == 0).nonzero()[0])
        cut = int(batch.q_span[q, 1])
        changed = batch.tokens.clone()
        later = torch.arange(changed.shape[1]) >= cut
        changed[0, later & (batch.line_of[0] >= 0)] = toy_ladder.FIRST_FREE
        from dataclasses import replace
        other = (replace(batch, tokens=changed), supplied, self.item[2])
        ep, _ = episodes(self.direct, self.pooled, self.item)[0]
        ep2, _ = episodes(self.direct, self.pooled, other)[0]
        self.assertTrue(torch.allclose(ep.x[q], ep2.x[q], atol=1e-6))
        self.assertTrue(torch.equal(ep.valid[q], ep2.valid[q]))

    def test_gradients_reach_reader_and_value_through_the_token_rows(self):
        loss = L.loss_of(self.direct, self.item, direct_reader.VARIANT, torch.Generator().manual_seed(3))
        loss.backward()
        for name in ("reader.layers.0.mixer.inp.weight", "writer.value.weight", "decoder.cross_kv.weight"):
            grad = dict(self.direct.named_parameters())[name].grad
            self.assertTrue(grad is not None and bool(torch.isfinite(grad).all()) and float(grad.abs().max()) > 0,
                            name)
        self.assertTrue(torch.isfinite(loss))

    def test_training_and_greedy_decoding_see_the_same_memory(self):
        batch = self.item[0]
        ep, _ = episodes(self.direct, self.pooled, self.item)[0]
        targets, _ = L.targets_inputs(self.direct, batch)
        inputs, first = self.direct.qread_inputs(batch, targets)
        with torch.no_grad():
            train_first = self.direct._decode_logits(ep.x, ep.valid, inputs)[:, first]
            tokens, _ = self.direct._greedy(batch, ep, self.direct._mentions(batch), None)
        logits = F.linear(train_first, self.direct.embed.weight).float()
        banned = torch.zeros_like(logits, dtype=torch.bool)
        banned[:, self.direct.config.vocab_size:] = ~self.direct._mentions(batch)
        self.assertTrue(torch.equal(logits.masked_fill(banned, -float("inf")).argmax(-1), tokens[:, 0]))
        start, _ = ep.direct_rows                                  # the token rows are actually attended
        hidden = self.direct._decode_logits(ep.x, torch.cat([ep.valid[:, :start],
                                                            torch.zeros_like(ep.valid[:, start:])], 1), inputs)
        self.assertFalse(torch.allclose(hidden[:, first], train_first))

    def test_read_only_evaluation_and_refusals(self):
        self.direct.eval()
        with read_only(self.direct):
            first, ok = L.predictions(self.direct, self.item, cards="all", seed=5)
        self.assertEqual(first.shape[0], ok.shape[0])
        ep, store = episodes(self.direct, self.pooled, self.item)[0]
        with self.assertRaises(NotImplementedError):
            self.direct._step(ep, torch.arange(2), 0, store)
        with self.assertRaises(NotImplementedError):
            self.direct._insert(ep, store, torch.arange(1), torch.tensor([[0]]))


if __name__ == "__main__":
    unittest.main()
