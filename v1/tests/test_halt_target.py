"""Fix #10: MiniConfig.halt_target. Default 'correct' is the v1 target (bit-identical); 'correct_and_evidence' multiplies it by have_all."""
import random
import unittest
from unittest import mock

import torch

import premonition.model as pm
from premonition.config import MiniConfig
from premonition.model import PremonitionMini
from premonition.toy import ToySpec, make_batch
from premonition.train import label_free, mini_config_dict, mini_config_from

SPEC = ToySpec()


def model(seed=0, **over):
    torch.manual_seed(seed)
    return PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=SPEC.vocab_size, window=64, **over))


def batch(seed=0):
    return label_free(make_batch(SPEC, 3, random.Random(seed)))


def capture(m, b, mode="teacher"):
    """Run one forward; return (output, list of (logits, target) given to the HALT BCE)."""
    seen = []
    real = pm.F.binary_cross_entropy_with_logits

    def spy(inp, tgt, **kw):
        seen.append((inp.detach().clone(), tgt.detach().clone()))
        return real(inp, tgt, **kw)

    with mock.patch.object(pm.F, "binary_cross_entropy_with_logits", spy):
        torch.manual_seed(1)
        out = m(b, mode=mode)
    return out, seen


class Config(unittest.TestCase):
    def test_default_and_validation(self):
        self.assertEqual(MiniConfig.preset("D", "tiny").halt_target, "correct")
        with self.assertRaises(ValueError):
            MiniConfig.preset("D", "tiny", halt_target="nope")
        with self.assertRaises(ValueError):                       # no card store, no gold cards
            MiniConfig.preset("D-noask", "tiny", halt_target="correct_and_evidence")
        MiniConfig.preset("D", "tiny", halt_target="correct_and_evidence")

    def test_dict_roundtrip_and_v1_dict_unchanged(self):
        d = mini_config_dict(MiniConfig.preset("D", "tiny"))
        self.assertNotIn("halt_target", d)                         # v1 dicts / digests are as before
        e = mini_config_dict(MiniConfig.preset("D", "tiny", halt_target="correct_and_evidence"))
        self.assertEqual(e["halt_target"], "correct_and_evidence")
        self.assertEqual(mini_config_from(e).halt_target, "correct_and_evidence")
        self.assertEqual(mini_config_from(d).halt_target, "correct")


class Target(unittest.TestCase):
    def test_default_target_is_correct_and_matches_explicit(self):
        b = batch()
        out_a, seen_a = capture(model(), b)
        out_b, seen_b = capture(model(halt_target="correct"), b)
        self.assertEqual(len(seen_a), len(seen_b))
        for (la, ta), (lb, tb) in zip(seen_a, seen_b):
            self.assertTrue(torch.equal(la, lb) and torch.equal(ta, tb))
        self.assertTrue(torch.equal(out_a["loss"], out_b["loss"]))

    def test_evidence_target_is_correct_times_have_all(self):
        b = batch()
        _, base = capture(model(), b)
        _, new = capture(model(halt_target="correct_and_evidence"), b)
        self.assertEqual(len(base), len(new))
        for (lb, tb), (ln, tn) in zip(base, new):
            self.assertTrue(torch.equal(lb, ln))                    # same weights and inputs: same HALT logits at loop 0
            self.assertTrue(bool((tn <= tb).all()))                 # never turns a 0 into a 1
            break                                                   # later loops depend on the changed training path only through fetches

    def test_function_truth_table(self):
        correct = torch.tensor([1.0, 1.0, 0.0, 0.0])
        have = torch.tensor([True, False, True, False])
        self.assertTrue(torch.equal(pm.halt_target_for("correct", correct, have), correct))
        self.assertTrue(torch.equal(pm.halt_target_for("correct_and_evidence", correct, have), torch.tensor([1.0, 0.0, 0.0, 0.0])))

    def test_model_passes_have_all_through(self):
        """Every (correct, have_all) pair the model computes goes through halt_target_for, and the BCE target is its result."""
        b = batch()
        calls = []
        real = pm.halt_target_for

        def spy(kind, correct, have_all):
            out = real(kind, correct, have_all)
            calls.append((kind, correct.clone(), have_all.clone(), out.clone()))
            return out

        with mock.patch.object(pm, "halt_target_for", spy):
            _, seen = capture(model(halt_target="correct_and_evidence"), b)
        self.assertGreaterEqual(len(seen), len(calls))                 # (the ASK loss also uses a BCE)
        self.assertTrue(any(not h.all() for _, _, h, _ in calls), "toy batch must have some unfetched gold cards")
        for kind, c, h, out in calls:
            self.assertEqual(kind, "correct_and_evidence")
            self.assertTrue(torch.equal(out, c * h.float()))
            self.assertTrue(bool((out[~h] == 0).all()))
            self.assertTrue(any(t.shape == out.shape and torch.equal(t, out) for _, t in seen))     # it is what the BCE got


if __name__ == "__main__":
    unittest.main()
