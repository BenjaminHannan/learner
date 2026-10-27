"""Address-keyed evidence selection (premonition/address_reader.py; milestone-3 continuation 3). CPU; no training."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import random
import sys
import unittest

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_address_keys as A  # noqa: E402
import premonition_direct_reader as D  # noqa: E402
import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402
import premonition_pool_controls as H  # noqa: E402

from learnlab.readonly import read_only  # noqa: E402
from premonition import address_reader, toy_ladder  # noqa: E402

H.L, H.R = L, R
D.H, D.L, D.R = H, L, R
A.D, A.H, A.L, A.R = D, H, L, R
SPEC = toy_ladder.LadderSpec()


def item(seed=3, training=True):
    return L.label_free_item(toy_ladder.make(SPEC, 4, random.Random(seed), training=training))


def episode(model, it, cards="all", seed=7):
    ep, _, _, store = L.episode(model, it, cards=cards, generator=torch.Generator().manual_seed(seed), passes=0)
    return ep, store


class BuildTest(unittest.TestCase):
    def test_shared_weights_random_stream_and_seeded_address(self):
        pooled = H.build("answer", "original", 1)
        after_pooled = torch.rand(4)
        model = A.build_address(1)
        after_model = torch.rand(4)
        self.assertTrue(torch.equal(after_pooled, after_model))
        sp, sm = pooled.state_dict(), model.state_dict()
        self.assertEqual(set(sm) - set(sp), {"address.weight", "address.bias"})
        self.assertTrue(all(torch.equal(sp[k], sm[k]) for k in sp))
        again, other = A.build_address(1), A.build_address(0)
        self.assertTrue(torch.equal(again.address.weight, model.address.weight))
        self.assertFalse(torch.equal(other.address.weight, model.address.weight))

    def test_decoder_reimplementation_is_exact(self):
        model = A.build_address(0)
        torch.manual_seed(5)
        x, memory = torch.randn(3, 6, 32), torch.randn(3, 20, 32)
        valid = torch.rand(3, 20) > 0.3
        valid[:, 0] = True
        self.assertTrue(torch.equal(address_reader.addressed_decoder(model.decoder, x, memory, valid),
                                    model.decoder(x, memory, valid)))


class SelectionTest(unittest.TestCase):
    def setUp(self):
        self.model, self.pooled = A.build_address(0), H.build("answer", "original", 0)
        with torch.no_grad():                                  # a non-trivial address projection
            self.model.address.weight.normal_(0.0, 0.5, generator=torch.Generator().manual_seed(3))
        self.item = item()

    def test_address_rows_are_line_token_1_and_2_embeddings_and_values_are_unchanged(self):
        ep, store = episode(self.model, self.item)
        pep, _ = episode(self.pooled, self.item)
        rows = self.pooled.config.rows
        self.assertTrue(torch.equal(ep.x[:, :rows], pep.x) and torch.equal(ep.valid[:, :rows], pep.valid))
        self.assertFalse(bool(ep.valid[:, rows:].any()))                      # address rows are never memory rows
        batch, supplied, _ = self.item
        order = torch.rand(supplied.shape, generator=torch.Generator().manual_seed(7)).argsort(1)
        chosen = supplied.gather(1, order)
        base, cards = self.model._address_base, self.model.config.cards
        for q in range(chosen.shape[0]):
            v, slot = int(batch.q_visit[q]), 0
            for line in chosen[q].tolist():
                if line < 0:
                    continue
                start = int(batch.line_start[v, line])
                self.assertTrue(torch.equal(ep.x[q, base + slot], self.model.embed.weight[batch.tokens[v, start + 1]]))
                self.assertTrue(torch.equal(ep.x[q, base + cards + slot],
                                            self.model.embed.weight[batch.tokens[v, start + 2]]))
                slot += 1

    def test_value_words_labels_and_metadata_cannot_change_selection_keys(self):
        batch, supplied, hops = self.item
        ep, _ = episode(self.model, self.item)
        keys = self.model.address_keys_of(ep.x)
        tokens = batch.tokens.clone()
        for q in range(supplied.shape[0]):                       # every supplied line's value word -> another value
            v = int(batch.q_visit[q])
            for line in supplied[q][supplied[q] >= 0].tolist():
                pos = int(batch.line_start[v, line]) + 3
                if SPEC.value(0) <= int(tokens[v, pos]) < SPEC.value(SPEC.values):
                    tokens[v, pos] = SPEC.value((int(tokens[v, pos]) - SPEC.value(0) + 5) % SPEC.values)
        changed = replace(batch, tokens=tokens, answer=torch.zeros_like(batch.answer),
                          gold_lines=torch.full_like(batch.gold_lines, -1))
        ep2, _ = episode(self.model, (changed, supplied, hops))
        self.assertTrue(torch.equal(self.model.address_keys_of(ep2.x), keys))
        self.assertFalse(torch.equal(ep2.x[:, :self.model.config.rows], ep.x[:, :self.model.config.rows]))
        tokens = batch.tokens.clone()                             # a person token DOES change the key
        q = int((hops == 1).nonzero()[0])
        v, line = int(batch.q_visit[q]), int(supplied[q, 0])
        pos = int(batch.line_start[v, line]) + 1
        tokens[v, pos] = SPEC.vocab_size + (int(tokens[v, pos]) - SPEC.vocab_size + 1) % SPEC.entities
        ep3, _ = episode(self.model, (replace(batch, tokens=tokens), supplied, hops))
        self.assertFalse(torch.equal(self.model.address_keys_of(ep3.x)[q], keys[q]))

    def test_address_swap_changes_decoder_outputs_and_no_cards_matches_the_baseline(self):
        # an address swap changes the decoder's internal first-answer-position outputs (not necessarily the
        # generated answer): evidence that selection keys are used, not that answers follow them
        batch = self.item[0]
        ep, _ = episode(self.model, self.item)
        targets, _ = L.targets_inputs(self.model, batch)
        inputs, first = self.model.qread_inputs(batch, targets)
        with torch.no_grad():
            out = self.model._decode_logits(ep.x, ep.valid, inputs)[:, first]
            swapped = ep.x.clone()                                # exchange two cards' addresses (values untouched)
            base, cards = self.model._address_base, self.model.config.cards
            for block in (base, base + cards):
                swapped[:, [block, block + 1]] = swapped[:, [block + 1, block]]
            moved = self.model._decode_logits(swapped, ep.valid, inputs)[:, first]
        self.assertFalse(torch.allclose(out, moved))
        none, _ = episode(self.model, self.item, cards="none")
        pnone, _ = episode(self.pooled, self.item, cards="none")
        with torch.no_grad():
            a = self.model._greedy(batch, none, self.model._mentions(batch), None)
            b = self.pooled._greedy(batch, pnone, self.pooled._mentions(batch), None)
        self.assertTrue(torch.equal(a[0], b[0]) and torch.equal(a[1], b[1]))

    def test_gradients_training_greedy_consistency_read_only_and_refusal(self):
        loss = L.loss_of(self.model, self.item, address_reader.VARIANT, torch.Generator().manual_seed(3))
        loss.backward()
        params = dict(self.model.named_parameters())
        for name in ("address.weight", "embed.weight", "decoder.cross_q.weight", "writer.value.weight"):
            g = params[name].grad
            self.assertTrue(g is not None and bool(torch.isfinite(g).all()) and float(g.abs().max()) > 0, name)
        batch = self.item[0]
        self.model.eval()
        ep, store = episode(self.model, self.item)
        targets, _ = L.targets_inputs(self.model, batch)
        inputs, first = self.model.qread_inputs(batch, targets)
        with torch.no_grad():
            logits = F.linear(self.model._decode_logits(ep.x, ep.valid, inputs)[:, first], self.model.embed.weight)
            tokens, _ = self.model._greedy(batch, ep, self.model._mentions(batch), None)
        banned = torch.zeros_like(logits, dtype=torch.bool)
        banned[:, self.model.config.vocab_size:] = ~self.model._mentions(batch)
        self.assertTrue(torch.equal(logits.float().masked_fill(banned, -float("inf")).argmax(-1), tokens[:, 0]))
        with read_only(self.model):
            L.predictions(self.model, self.item, cards="all", seed=5)
        with self.assertRaises(NotImplementedError):
            self.model._step(ep, torch.arange(2), 0, store)


if __name__ == "__main__":
    unittest.main()
