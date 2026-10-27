"""Overnight diagnostics (run ovn-20260918-235851): the ladder task, the row-centred Think update and the
question-conditioned read. CPU, tiny preset; no training."""
from __future__ import annotations

import random
import unittest

import torch

from premonition import ovn_qread, ovn_variants, toy_ladder
from premonition.config import MiniConfig
from premonition.model import PremonitionMini

SPEC = toy_ladder.LadderSpec()


def tiny(seed: int = 0) -> PremonitionMini:
    torch.manual_seed(seed)
    return PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=SPEC.vocab_size, window=64))


def cards(batch, v, lines):
    return [batch.tokens[v, int(batch.line_start[v, l]):int(batch.line_start[v, l]) + 4].tolist() for l in lines]


class LadderTest(unittest.TestCase):
    def test_targets_evidence_and_mirror_decoys(self):
        batch, supplied, hops = toy_ladder.make(SPEC, 8, random.Random(3), training=False)
        for q in range(len(hops)):
            v = int(batch.q_visit[q])
            ask = batch.tokens[v, int(batch.q_span[q, 0]):int(batch.q_span[q, 1])].tolist()
            real = [l for l in supplied[q].tolist() if l >= 0]
            self.assertEqual(len(set(real)), 4 if int(hops[q]) == 1 else 6)
            got = cards(batch, v, real)
            if int(hops[q]) == 1:
                self.assertEqual(got[0][1:3], ask[1:3])                   # gold first: the asked person and relation
                attrs = [c for c in got]
                self.assertEqual(sum(c[1] == ask[1] for c in attrs), 2)   # two cards about the person
                self.assertEqual(sum(c[2] == ask[2] for c in attrs), 2)   # two cards with the relation
            else:
                link, answer = got[0], got[1]
                self.assertEqual((link[1], link[2]), (ask[1], SPEC.link))
                self.assertEqual((answer[1], answer[2]), (link[3], ask[3]))
                decoy_link, decoy_answer = got[3], got[4]
                self.assertEqual(decoy_link[2], SPEC.link)
                self.assertEqual((decoy_answer[1], decoy_answer[2]), (decoy_link[3], ask[3]))
                self.assertNotIn(decoy_link[1], (ask[1], link[3]))
                self.assertNotIn(decoy_link[3], (ask[1], link[3]))
            self.assertEqual(int(batch.answer[q, 0]), got[0][3] if int(hops[q]) == 1 else got[1][3])

    def test_training_visits_never_ask_the_heldout_combination(self):
        for _ in range(5):
            batch, _, _ = toy_ladder.make(SPEC, 8, random.Random(_), training=True)
            self.assertFalse(bool(batch.slices["heldout"].any()))

    def test_replay_with_an_edited_fact_changes_only_that_fact(self):
        rng = random.Random(11)
        lines, world, plan = toy_ladder.visit(SPEC, rng, training=False)
        edited = toy_ladder.World(list(world.ents), dict(world.attr), dict(world.friend))
        key = next(iter(edited.attr))
        edited.attr[key] = (edited.attr[key] + 1) % SPEC.values
        again, _, _ = toy_ladder.visit(SPEC, rng, training=False, world=edited, plan=plan)
        diff = [i for i, (a, b) in enumerate(zip(lines, again)) if a.tokens != b.tokens]
        self.assertTrue(1 <= len(diff) <= 1 + SPEC.one_hop + SPEC.two_hop)  # the fact line (+ questions it answers)


class VariantTest(unittest.TestCase):
    def test_centred_update_has_zero_mean_over_valid_rows(self):
        model = ovn_variants.from_base(ovn_variants.THINK_CENTERED, tiny())
        for p in model.think.parameters():
            torch.nn.init.normal_(p, std=0.3)                            # a non-trivial update
        x = torch.randn(3, model.config.rows, model.config.d_model)
        valid = torch.rand(3, model.config.rows) > 0.3
        valid[:, -1] = True
        update = model.think(x, valid, 0) - x
        mean = (update * valid.unsqueeze(-1)).sum(1) / valid.sum(1, keepdim=True)
        self.assertLess(float(mean.abs().max()), 1e-4)

    def test_qread_prefix_ends_at_answer_and_decodes(self):
        batch, supplied, hops = toy_ladder.make(SPEC, 4, random.Random(5), training=False)
        prefix = ovn_qread.question_prefix(batch, 0)
        self.assertTrue(bool((prefix[:, -1] == toy_ladder.ANSWER).all()))
        self.assertTrue(bool((prefix[hops == 1, :2] == 0).all()))       # 4-token questions are left-padded twice
        base = tiny()
        model = ovn_qread.QReadMini(base.config)
        model.load_state_dict(base.state_dict())
        with torch.no_grad():
            answers = model.answer(batch, max_loops=2)
        self.assertEqual(answers.tokens.shape[0], len(hops))

    def test_identities(self):
        ident = ovn_variants.identity(ovn_variants.THINK_CENTERED, tiny().config)
        self.assertEqual((ident["variant"], ident["purpose"]), ("D-think-centered", "diagnostic"))


if __name__ == "__main__":
    unittest.main()
