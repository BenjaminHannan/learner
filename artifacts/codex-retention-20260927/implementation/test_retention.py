"""Behavioral tests for request routing, interference and retention accounting."""
import concurrent.futures
import asyncio
import copy
import sys
import threading
import unittest
from pathlib import Path

import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts"))
from retention import RequestScopedAdapter, retention_counts, zero_failure_upper_bound
from claude_blurt2 import add_lora


class Toy(nn.Module):
    def __init__(self):
        super().__init__()
        self.q_proj = nn.Linear(3, 4)
        self.register_buffer("buffer", torch.ones(1))

    def forward(self, x):
        return self.q_proj(x)

    def generate(self, input_ids, **kwargs):
        return self(input_ids)


class TestRetention(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(191)
        self.m = Toy().eval()
        self.base = copy.deepcopy(self.m)
        add_lora(self.m, r=2, dropout=0.0)
        with torch.no_grad():
            self.m.q_proj.B.normal_()
        self.m.eval()
        self.x = torch.randn(2, 3)
        self.original_keys = tuple(self.m.state_dict())
        self.original_on = self.m(self.x).detach().clone()
        self.controller = RequestScopedAdapter(self.m)

    def test_same_adapter_state_and_exact_base(self):
        self.assertEqual(self.original_keys, tuple(self.m.state_dict()))
        self.assertTrue(torch.equal(self.controller.generate(input_ids=self.x), self.base(self.x)))
        self.assertTrue(torch.equal(self.controller.generate(enabled=True, input_ids=self.x), self.original_on))
        self.assertFalse(torch.equal(self.original_on, self.base(self.x)))

    def test_poisoned_disabled_adapter_never_evaluated(self):
        with torch.no_grad():
            self.m.q_proj.A.fill_(float("nan"))
        self.assertTrue(torch.equal(self.controller.generate(input_ids=self.x), self.base(self.x)))
        self.assertTrue(torch.isnan(self.controller.generate(enabled=True, input_ids=self.x)).all())

    def test_nested_exception_restores_route(self):
        with self.controller.scope(True):
            with self.assertRaises(RuntimeError):
                with self.controller.scope(False):
                    self.assertFalse(self.controller.enabled)
                    raise RuntimeError("generation failed")
            self.assertTrue(self.controller.enabled)
        self.assertFalse(self.controller.enabled)

    def test_threads_do_not_change_each_others_route(self):
        barrier = threading.Barrier(2)
        def work(enabled):
            with self.controller.scope(enabled):
                barrier.wait(timeout=5)
                return self.m(self.x).detach().clone()
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            off = pool.submit(work, False)
            on = pool.submit(work, True)
            self.assertTrue(torch.equal(off.result(), self.base(self.x)))
            self.assertTrue(torch.equal(on.result(), self.original_on))

    def test_async_work_cannot_inherit_expired_route(self):
        async def check():
            ready = asyncio.Event()
            async def deferred():
                await ready.wait()
                return self.m(self.x)
            with self.controller.scope(True):
                task = asyncio.create_task(deferred())
            ready.set()
            with self.assertRaisesRegex(RuntimeError, "scope ended"):
                await task
            self.assertFalse(self.controller.enabled)
        asyncio.run(check())

    def test_training_adapter_does_not_change_base(self):
        digest = self.controller.base_digest()
        opt = torch.optim.AdamW([p for p in self.m.parameters() if p.requires_grad], lr=.1, weight_decay=.1)
        with self.controller.scope(True):
            for _ in range(3):
                opt.zero_grad(set_to_none=True)
                self.m(self.x).square().mean().backward()
                opt.step()
        self.assertEqual(digest, self.controller.base_digest())
        self.assertTrue(torch.equal(self.controller.generate(input_ids=self.x), self.base(self.x)))
        self.assertFalse(torch.equal(self.controller.generate(enabled=True, input_ids=self.x), self.original_on))

    def test_persistence_and_base_buffer_integrity(self):
        import io
        f = io.BytesIO()
        torch.save(self.m.state_dict(), f)
        f.seek(0)
        m = add_lora(Toy(), r=2, dropout=0.0).eval()
        m.load_state_dict(torch.load(f, weights_only=True))
        c = RequestScopedAdapter(m)
        self.assertTrue(torch.equal(c.generate(enabled=True, input_ids=self.x), self.original_on))
        before = c.base_digest()
        m.buffer.add_(1)
        self.assertNotEqual(before, c.base_digest())

    def test_bad_request_and_duplicate_install(self):
        with self.assertRaises(ValueError):
            self.controller.generate(input_ids=self.x, past_key_values=object())
        with self.assertRaises(ValueError):
            RequestScopedAdapter(self.m)
        with self.assertRaises(TypeError), self.controller.scope([True, False]):
            pass
        self.m.train()
        with self.assertRaises(ValueError):
            self.controller.generate(input_ids=self.x)

    def test_unfrozen_shared_parameter_is_rejected(self):
        m = add_lora(Toy(), r=2)
        m.shared_embedding = nn.Parameter(torch.ones(4))
        with self.assertRaisesRegex(ValueError, "Base parameter is trainable"):
            RequestScopedAdapter(m)

    def test_gains_cannot_hide_losses(self):
        c = retention_counts([1, 1, 0, 0], [1, 0, 1, 1])
        self.assertEqual((c.previously_correct, c.lost, c.gained, c.retained), (2, 1, 2, 1))
        self.assertAlmostEqual(zero_failure_upper_bound(200), .014867039, places=8)
        for a, b in (([], []), ([1], [1, 0]), ([2], [1])):
            with self.assertRaises(ValueError):
                retention_counts(a, b)


if __name__ == "__main__":
    unittest.main()
