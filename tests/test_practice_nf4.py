"""--nf4: the flag reaches load_model on night workers, and load_model builds an NF4 BitsAndBytesConfig without moving the 4-bit model."""
import types

import torch

from practice import job
from sleep2.askonce import model_io


def test_flag_parsed():
    a = job.build_parser().parse_args(["--arm", "P", "--nf4"])
    assert a.nf4 is True
    assert job.build_parser().parse_args(["--arm", "P"]).nf4 is False


def test_load_model_nf4_config(monkeypatch):
    seen = {}

    class FakeModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.w = torch.nn.Parameter(torch.zeros(1))
            self.config = types.SimpleNamespace(use_cache=False)

        def to(self, *a, **k):
            raise AssertionError("a 4-bit model must not be moved")

    def fake_from_pretrained(src, **kw):
        seen.update(kw)
        return FakeModel()

    import transformers
    monkeypatch.setattr(transformers.AutoModelForCausalLM, "from_pretrained", staticmethod(fake_from_pretrained))
    m = model_io.load_model("some/k2", torch.float16, "cuda", nf4=True)
    q = seen["quantization_config"]
    assert q.load_in_4bit and q.bnb_4bit_quant_type == "nf4" and q.bnb_4bit_compute_dtype == torch.float16
    assert seen["device_map"] == {"": 0}
    assert m.config.use_cache is True


def test_night_worker_passes_nf4(monkeypatch):
    calls = []
    monkeypatch.setattr(job, "load_model", lambda name, dt, dev, nf4=False: calls.append(nf4) or object())
    monkeypatch.setattr(job, "assert_finite_forward", lambda *a, **k: None)
    lane = job.Lane.__new__(job.Lane)
    lane.a = types.SimpleNamespace(nf4=True)
    lane.wmode, lane.kind, lane.name, lane.dt, lane.dev, lane.adapter = "hf", "night", "k2", torch.float16, "cuda", None
    lane.tok, lane.log = None, print
    lane.setup_worker()
    assert calls == [True]


def test_cuda_cap_env_ignored_on_cpu(monkeypatch):
    monkeypatch.setenv("PRACTICE_CUDA_CAP_GIB", "14")
    monkeypatch.setattr(job, "load_model", lambda name, dt, dev, nf4=False: object())
    monkeypatch.setattr(job, "assert_finite_forward", lambda *a, **k: None)
    lane = job.Lane.__new__(job.Lane)
    lane.a = types.SimpleNamespace(nf4=False)
    lane.wmode, lane.kind, lane.name, lane.dt, lane.dev, lane.adapter = "hf", "night", "k2", torch.float32, "cpu", None
    lane.tok, lane.log = None, print
    lane.setup_worker()
