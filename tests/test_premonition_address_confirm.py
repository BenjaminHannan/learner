"""Fresh-data confirmation mechanics (scripts/premonition_address_confirm.py). CPU; no training; random-init models."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import random
import sys
import unittest

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_address_confirm as C  # noqa: E402
import premonition_address_keys as A  # noqa: E402
import premonition_direct_reader as D  # noqa: E402
import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402
import premonition_pool_controls as H  # noqa: E402

from premonition import ladder_triplets as T, toy_ladder  # noqa: E402

H.L, H.R = L, R
D.H, D.L, D.R = H, L, R
A.D, A.H, A.L, A.R = D, H, L, R
C.A, C.D, C.H, C.L = A, D, H, L
SPEC = toy_ladder.LadderSpec()


class RenameTest(unittest.TestCase):
    def test_permutations_are_fixed_point_free_and_deterministic(self):
        for b in range(5):
            perm = C.permutation(b)
            self.assertEqual(sorted(perm), list(range(toy_ladder.N_ENT)))
            self.assertTrue(all(perm[e] != e for e in range(len(perm))))
            self.assertEqual(perm, C.permutation(b))

    def test_renaming_keeps_answers_values_and_verified_triplets(self):
        rng, edit = random.Random(1), random.Random(2)
        perm = C.permutation(0)
        for _ in range(6):
            t = T.make_triplet(SPEC, rng, edit, training=False)
            key = lambda k: (perm[k[0]], k[1])
            r = replace(t, x=C.rename_lines(t.x, perm, SPEC), u=C.rename_lines(t.u, perm, SPEC),
                        v=C.rename_lines(t.v, perm, SPEC), changed_u=tuple(key(k) for k in t.changed_u),
                        changed_v=tuple(key(k) for k in t.changed_v),
                        worlds=tuple(C.rename_world(w, perm) for w in t.worlds))
            T.verify(SPEC, r)
            for a, b in zip(t.x, r.x):
                self.assertEqual(len(a.tokens), len(b.tokens))
                self.assertEqual(a.answer, b.answer)                          # answers are value words: unchanged
                for p, q in zip(a.tokens, b.tokens):
                    if SPEC.vocab_size <= p < SPEC.vocab_size + toy_ladder.N_ENT:
                        self.assertEqual(q, SPEC.vocab_size + perm[p - SPEC.vocab_size])
                    else:
                        self.assertEqual(p, q)

    def test_world_fingerprint_from_text_matches_the_world_and_training_replay_matches_the_stream(self):
        lines, world, _ = toy_ladder.visit(SPEC, random.Random(5), training=True)
        facts = C.facts_of_tokens([t for line in lines for t in line.tokens], SPEC)
        want = sorted([("attr", SPEC.vocab_size + e, SPEC.relation(r), SPEC.value(v)) for (e, r), v in world.attr.items()]
                      + [("link", SPEC.vocab_size + e, SPEC.vocab_size + f) for e, f in world.friend.items()])
        self.assertEqual(facts, tuple(want))
        first = next(L.train_stream())
        self.assertEqual(C.training_worlds(SPEC, 1), set(C.batch_worlds(first, SPEC)))


class DecodeTest(unittest.TestCase):
    def test_greedy_matches_the_ladder_predictions(self):
        item = L.label_free_item(toy_ladder.make(SPEC, 4, random.Random(9), training=False))
        for model in (H.build("answer", "original", 0), A.build_address(0)):
            model.eval()
            with torch.no_grad():
                order = torch.rand(item[1].shape, generator=torch.Generator().manual_seed(4)).argsort(1)
                mine = C.greedy(model, item, "all", order)
                _, ok = L.predictions(model, item, cards="all", seed=4)
                gold = C.greedy(model, item, "gold", None)
                _, ok_gold = L.predictions(model, item, cards="gold", seed=4)
            targets = [row[row != -100].tolist() for row in item[0].answer]
            self.assertEqual([m == t for m, t in zip(mine, targets)], ok.tolist())
            self.assertEqual([g == t for g, t in zip(gold, targets)], ok_gold.tolist())


if __name__ == "__main__":
    unittest.main()
