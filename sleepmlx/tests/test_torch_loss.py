"""Numerical backend regressions; optional torch, CPU only, no model download."""
from contextlib import contextmanager
import unittest

try:
    import torch
except ImportError:
    torch = None

from sleepmlx.torch_backend import TorchBackend


@unittest.skipIf(torch is None, "optional torch dependency is not installed")
class ReplayLossTests(unittest.TestCase):
    def test_ignored_replay_prefix_does_not_dilute_kl_or_gradient(self):
        class Model(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.logits = torch.nn.Parameter(torch.tensor([1.0, -1.0]))
                self.disabled = False

            @contextmanager
            def disable_adapter(self):
                self.disabled = True
                try:
                    yield
                finally:
                    self.disabled = False

        backend = TorchBackend.__new__(TorchBackend)
        backend.torch, backend.device = torch, "cpu"
        backend.model, backend.opt = Model(), None
        backend.tok_budget, backend.stop_id = 64, 0
        backend._logits = lambda ids, att, bi, ti: (
            torch.zeros(len(bi), 2) if backend.model.disabled else backend.model.logits.expand(len(bi), 2)
        )
        results = []
        for replay in ([([0, 1], 1)], [([0, 0, 0, 0, 1], 4)]):
            backend.model.zero_grad(set_to_none=True)
            result = backend._train_step([], replay, 0, update=False)
            results.append((result["kl"], backend.model.logits.grad.clone()))
        expected = torch.nn.functional.kl_div(
            torch.log_softmax(torch.tensor([1.0, -1.0]), -1),
            torch.log_softmax(torch.zeros(2), -1), log_target=True, reduction="sum",
        ).item()
        self.assertGreater(expected, 0)
        for loss, gradient in results:
            self.assertAlmostEqual(loss, expected, places=6)
            torch.testing.assert_close(gradient, results[0][1])


if __name__ == "__main__":
    unittest.main()
