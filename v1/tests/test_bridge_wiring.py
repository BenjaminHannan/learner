"""Wiring tests for the two bugs found after the first arms (2026-10-21):
 1. the Bridge must own ONLY its two projections (it once registered D and the creative model as submodules, so its optimizer and clip
    covered every weight of D);
 2. with a NONZERO bridge, sampling (creative/sampler.py, creative/legal.py) must agree with Ledger.run: same greedy program."""
import os, unittest
import torch

from premonition.config import MiniConfig
from premonition.model import PremonitionMini
from v1.joint import Bridge


def small_d():
    return PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=300, window=64))


class BridgeOwnership(unittest.TestCase):
    def test_parameters_are_only_the_two_projections(self):
        from custom_io.data import CharVocab
        from custom_io.models import build
        c = build("ledger", CharVocab("abcdefghijklmnopqrstuvwxyz0123456789 "), copy=True)
        d = small_d()
        b = Bridge(d.config.d_model, c.d).attach(d, c)
        own = {id(p) for lin in (b.p_dc, b.p_cd) for p in lin.parameters()}
        self.assertEqual({id(p) for p in b.parameters()}, own)
        self.assertEqual(sorted(b.state_dict()), sorted(["p_dc.weight", "p_dc.bias", "p_cd.weight", "p_cd.bias", "ctx_d", "ctx_c", "seen_d", "seen_c"]))
        self.assertFalse(own & {id(p) for p in d.parameters()} or own & {id(p) for p in c.parameters()})

    def test_bridge_optimizer_leaves_d_untouched(self):
        from custom_io.data import CharVocab
        from custom_io.models import build
        c = build("ledger", CharVocab("abcdefghijklmnopqrstuvwxyz0123456789 "), copy=True)
        d = small_d()
        b = Bridge(d.config.d_model, c.d).attach(d, c)
        opt = torch.optim.AdamW(b.parameters(), lr=1e-2, weight_decay=0.0)
        before = {n: p.detach().clone() for n, p in d.named_parameters()}
        for p in d.parameters():
            p.grad = torch.ones_like(p)                 # D has gradients; the bridge optimizer must not touch them
        torch.nn.utils.clip_grad_norm_(b.parameters(), 1.0)
        opt.step()
        self.assertTrue(all(torch.equal(before[n], p.detach()) for n, p in d.named_parameters()))
        self.assertTrue(all(torch.equal(torch.ones_like(p), p.grad) for p in d.parameters()), "the bridge clip rescaled D's gradients")


@unittest.skipUnless(os.environ.get("B2_CKPT") and os.environ.get("SKILLS_TRAIN"), "needs B2_CKPT and SKILLS_TRAIN")
class SamplerAgreesWithRun(unittest.TestCase):
    def test_nonzero_bridge_same_greedy_program(self):
        from creative import sleep
        from creative.sampler import sample_run
        from creative.legal import sample_run_masked
        from custom_io.data import Dataset, collate, load_rows, to_device
        m, vocab, _ = sleep.load_parent(os.environ["B2_CKPT"], "cpu")
        m.eval()
        rows = [r for r in load_rows(os.environ["SKILLS_TRAIN"], limit=4000) if r.get("family") and r.get("steps")][:96]
        batch = to_device(collate([Dataset(rows, vocab, strict=False)[i] for i in range(len(rows))]), "cpu")
        d = small_d()
        b = Bridge(d.config.d_model, m.d).attach(d, m)
        torch.manual_seed(0)
        torch.nn.init.normal_(b.p_dc.weight, std=0.5)    # a clearly nonzero bridge
        b.ctx_d.copy_(torch.randn(d.config.d_model))
        b.seen_d.fill_(1)
        with torch.no_grad():
            ref = m.run(batch)["prog"]
            got = sample_run(m, batch, greedy=True)
            k = torch.zeros(len(rows), dtype=torch.long)
            got0 = sample_run_masked(m, batch, k, level=0, greedy=True)
            b.enabled = False
            off = sample_run(m, batch, greedy=True)
        n = len(rows)
        same = lambda o: float(sum(bool(torch.equal(ref[i][r], o[key][r])) for r in range(n) for i, key in enumerate(("ops", "a", "b"))) / (3 * n))
        self.assertEqual(same(got), 1.0, "sampler.sample_run disagrees with Ledger.run under a nonzero bridge")
        self.assertEqual(same(got0), 1.0)
        self.assertLess(same(off), 1.0, "the nonzero bridge changed nothing: the test is not sensitive")


if __name__ == "__main__":
    unittest.main()
