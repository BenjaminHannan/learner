"""Bridge invariants: zero-init == no bridge, shuffle really permutes, no batch leakage in real mode."""
import pytest
import torch

from bridgelab import task
from bridgelab.models import ARMS, Pair, ablate, derangement

PER_ITEM = [a for a in ARMS if a not in ("none",)]


def _data(n: int = 16, seed: int = 0) -> dict:
    return task.make_batch(n, torch.Generator().manual_seed(seed))


def _pair(arm: str) -> Pair:
    torch.manual_seed(0)
    return Pair(arm).eval()


@pytest.mark.parametrize("arm", PER_ITEM)
def test_zero_init_equals_none(arm):
    d = _data()
    none, other = _pair("none"), _pair(arm)
    # copy every shared (non-bridge) weight so the only difference is the bridge
    other.load_state_dict({k: v for k, v in none.state_dict().items()}, strict=False)
    with torch.no_grad():
        ln, lo = none(d["xa"], d["xb"]), other(d["xa"], d["xb"])
    for x, y in zip(ln, lo):
        assert torch.equal(x, y), f"{arm}: zero-init bridge changes the output"


def test_shuffle_permutes():
    msg = torch.arange(10.0)[:, None].expand(10, 3).clone()
    gen = torch.Generator().manual_seed(1)
    out = ablate(msg, "shuffle", gen)
    assert sorted(out[:, 0].tolist()) == list(range(10))          # a permutation
    assert (out[:, 0] != msg[:, 0]).all()                         # nobody keeps their own message
    assert (derangement(500, gen) != torch.arange(500)).all()
    assert torch.equal(ablate(msg, "mean")[0], msg.mean(0)) and ablate(msg, "off") is None


def _perturb(model: Pair, arm: str) -> None:
    """Make the bridge non-trivial (random weights, non-zero gates) so leakage would show."""
    g = torch.Generator().manual_seed(5)
    for n, p in model.named_parameters():
        if "ab." in n or "ba." in n:
            p.data = torch.randn(p.shape, generator=g) * 0.3


@pytest.mark.parametrize("arm", PER_ITEM)
def test_no_batch_leakage(arm):
    d = _data(16)
    m = _pair(arm)
    _perturb(m, arm)
    d2 = {k: v.clone() for k, v in d.items()}
    d2["xa"][8:], d2["xb"][8:] = _data(8, seed=9)["xa"], _data(8, seed=9)["xb"]   # change half the batch
    with torch.no_grad():
        a, b = m(d["xa"], d["xb"]), m(d2["xa"], d2["xb"])
    for x, y in zip(a, b):
        assert torch.allclose(x[:8], y[:8], atol=1e-5), f"{arm}: items depend on other items"
        assert not torch.allclose(x[8:], y[8:], atol=1e-5)
    # sanity: the perturbed bridge actually matters (off differs from real)
    with torch.no_grad():
        off = m(d["xa"], d["xb"], "off")
    assert not torch.allclose(a[1], off[1], atol=1e-5)
