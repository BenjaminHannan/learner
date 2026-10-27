"""Binding probe mechanics (scripts/premonition_binding_probe.py): faithful ablations from one starting state,
attention reconstruction, card bookkeeping. CPU; random-init models; no training."""
from __future__ import annotations

from pathlib import Path
import random
import sys
import unittest

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_binding_probe as P  # noqa: E402
import premonition_direct_reader as D  # noqa: E402
import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402
import premonition_pool_controls as H  # noqa: E402

from premonition import toy_ladder  # noqa: E402
from premonition.ovn_qread import question_prefix  # noqa: E402

H.L, H.R = L, R
D.H, D.L, D.R = H, L, R
P.D, P.H, P.L = D, H, L
SPEC = toy_ladder.LadderSpec()


def setup(model, seed=4):
    item = L.label_free_item(toy_ladder.make(SPEC, 4, random.Random(seed), training=False))
    order = torch.rand(item[1].shape, generator=torch.Generator().manual_seed(1)).argsort(1)
    with torch.no_grad():
        state = P.start_state(model, item, order)
    return item, order, state


def models():
    pooled, direct = H.build("answer", "original", 0), D.build_direct(0)
    weight = torch.randn(pooled.writer.pool.weight.shape, generator=torch.Generator().manual_seed(2))
    with torch.no_grad():
        for m in (pooled, direct):
            m.writer.pool.weight.copy_(weight)
            m.eval()
    return {"pooled": pooled, "direct": direct}


class ProbeTest(unittest.TestCase):
    def test_ablations_are_faithful_and_share_one_starting_state(self):
        for name, model in models().items():
            item, order, (ep, pre_x, pre_valid, mentions, chosen) = setup(model)
            mems, facts = P.memories(model, ep, pre_x, pre_valid)
            self.assertEqual((facts["x_changed_outside_slots_cards"], facts["valid_changed_outside_cards"],
                              facts["slot_valid_changed"]), (0, 0, 0), name)
            self.assertGreater(facts["slot_rows_changed"], 0, name)                 # binding really wrote slots
            reg = P.regions(model, pre_x.shape[1], ep.x.shape[1])
            s = slice(*reg["slots"])
            self.assertTrue(torch.equal(mems["no_slots"][0][:, s], pre_x[:, s]))
            self.assertTrue(torch.equal(mems["no_evidence"][0], ep.x))              # slots stay bound
            self.assertTrue(torch.equal(mems["no_slots"][1], ep.valid))             # evidence stays visible
            keep = torch.ones(ep.x.shape[1], dtype=torch.bool)
            keep[slice(*reg["cards"])] = False
            keep[slice(*reg["tokens"])] = False
            self.assertTrue(torch.equal(mems["no_evidence"][1][:, keep], ep.valid[:, keep]))
            self.assertFalse(bool(mems["no_evidence"][1][:, ~keep].any()))
            batch = item[0]
            with torch.no_grad():
                neither = P.decode(model, batch, mentions, *mems["neither"])
                none = P.decode(model, batch, mentions, pre_x, pre_valid)
                full = P.decode(model, batch, mentions, *mems["full"])
                reference = model._greedy(batch, ep, mentions, None)
            self.assertEqual(neither, none, name)
            self.assertEqual(full, [reference[0][q, :int(reference[1][q])].tolist() for q in range(len(full))])

    def test_attention_is_reconstructed_from_the_decoder_and_covers_every_row(self):
        for name, model in models().items():
            item, order, (ep, pre_x, pre_valid, mentions, chosen) = setup(model)
            prefix = question_prefix(item[0], model.config.pad_id)
            with torch.no_grad():
                weights, err_att, err_dec = P.cross_attention(model, ep.x, ep.valid, prefix)
            self.assertLess(err_att, 1e-5, name)
            self.assertLess(err_dec, 1e-5, name)
            rows_before = pre_x.shape[1]
            longest = (ep.x.shape[1] - rows_before) // chosen.shape[1] if ep.x.shape[1] > rows_before else 0
            for q in (item[2] == 1).nonzero().squeeze(1).tolist():
                v = int(item[0].q_visit[q])
                end = int(item[0].q_span[q, 1])
                e = int(item[0].tokens[v, end - 3]) - SPEC.vocab_size
                other = int(item[0].tokens[v, int(item[0].line_start[v, int(item[1][q, 2])]) + 1]) - SPEC.vocab_size
                att = P.attention_by_type(model, weights, q, chosen, order, rows_before, longest, e, other)
                total = sum(att[k] for k in att if not k.startswith("role_"))
                self.assertAlmostEqual(total, 1.0, places=5)
                if longest:
                    self.assertAlmostEqual(sum(att[k] for k in att if k.startswith("role_")),
                                           sum(att[f"card_{t}"] for t in P.CARD_TYPES), places=5)

    def test_card_values_follow_the_supplied_columns(self):
        item = L.label_free_item(toy_ladder.make(SPEC, 4, random.Random(8), training=False))
        batch, supplied, hops = item
        for q in (hops == 1).nonzero().squeeze(1).tolist():
            values = P.card_values(batch, supplied, q)
            self.assertEqual(values[0], int(batch.answer[q, 0]))                  # gold card holds the answer
            self.assertEqual(P.source(values[0], values), "gold" if values.count(values[0]) == 1 else "ambiguous")
        self.assertEqual(P.source(-1, [1, 2, 3, 4]), "not_on_cards")


if __name__ == "__main__":
    unittest.main()
