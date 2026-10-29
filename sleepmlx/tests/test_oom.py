import unittest

from sleepmlx import torch_backend as T


class _Mps:
    def __init__(self):
        self.emptied = 0

    def empty_cache(self):
        self.emptied += 1


class _Torch:
    def __init__(self):
        self.mps = _Mps()


def fake_backend(gen_batch=8, tok_budget=512):
    be = T.TorchBackend.__new__(T.TorchBackend)
    be.torch, be.device, be.gen_batch, be.tok_budget, be.opt = _Torch(), "mps", gen_batch, tok_budget, None
    return be


class OomTests(unittest.TestCase):
    def test_generate_halves_batch_on_oom(self):
        be = fake_backend(gen_batch=8)
        calls = []

        def gen(prompts, *a):
            calls.append(len(prompts))
            if len(prompts) > 2:
                raise RuntimeError("MPS backend out of memory (MPS allocated: 6.12 GB, other allocations: 3.02 GB, max allowed: 9.31 GB)")
            return [p.upper() for p in prompts]
        be._generate = gen
        out = be.generate(["a", "b", "c", "d", "e", "f", "g", "h"], 10)
        self.assertEqual(out, list("ABCDEFGH"))
        self.assertLessEqual(be.gen_batch, 2)
        self.assertGreater(be.torch.mps.emptied, 0)

    def test_generate_other_errors_propagate(self):
        be = fake_backend()
        be._generate = lambda *a: (_ for _ in ()).throw(RuntimeError("shape mismatch"))
        with self.assertRaises(RuntimeError):
            be.generate(["a", "b"], 5)

    def test_train_step_shrinks_tok_budget_and_retries(self):
        be = fake_backend(tok_budget=512)
        zeroed = []
        be.model = type("M", (), {"zero_grad": lambda self, set_to_none=True: zeroed.append(1)})()

        def step(batch, replay, step, update):
            if be.tok_budget > 128:
                raise RuntimeError("MPS backend out of memory")
            return {"ce": 1.0, "kl": 0.0}
        be._train_step = step
        self.assertEqual(be.train_step([], [], 0), {"ce": 1.0, "kl": 0.0})
        self.assertEqual(be.tok_budget, 128)
        self.assertEqual(len(zeroed), 2)

    def test_train_step_gives_up_at_64(self):
        be = fake_backend(tok_budget=64)
        be.model = type("M", (), {"zero_grad": lambda self, set_to_none=True: None})()
        be._train_step = lambda *a: (_ for _ in ()).throw(RuntimeError("out of memory"))
        with self.assertRaises(RuntimeError):
            be.train_step([], [], 0)


if __name__ == "__main__":
    unittest.main()
