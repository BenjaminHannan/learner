"""CPU tests for the KL guards in sleep (sleep1.py / sleepb.py) and rlaif (rollout.py _lp_kl):  python backbone/think/test_kl_guard.py

K1  sleep direction, KL(ref || cur) with grad on cur: at cur == ref (fresh LoRA, B = 0) the fixed KL gives exactly 0 gradient on the
    LoRA parameter; the standard F.kl_div line gives a non-zero one (fp32 and bf16 logits).
K2  rlaif direction, KL(view || sg other) with grad on view: same check.
K3  fixed_reverse_kl matches plain autograd (fp64) on random, unequal logits, forward and gradient.
"""
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xent import fixed_kl  # noqa: E402
from xent_reverse import fixed_reverse_kl  # noqa: E402

V, D, R, N = 5000, 32, 4, 16
g = torch.Generator().manual_seed(0)
W, h, A = torch.randn(V, D, generator=g) * 0.6, torch.randn(N, D, generator=g), torch.randn(R, D, generator=g) / D ** 0.5


def lora_grad(kl_fn, dtype):
    B = torch.zeros(D, R, requires_grad=True)  # PEFT init: adapted model == reference bitwise
    cur = ((h + (h @ A.T) @ B.T) @ W.T).to(dtype)
    with torch.no_grad():
        ref = (h @ W.T).to(dtype)
    assert torch.equal(cur.detach(), ref)
    kl_fn(cur.float(), ref.float()).backward()
    return B.grad.abs().max().item()


def test_k1():
    for dt in (torch.float32, torch.bfloat16):
        std = lora_grad(lambda c, r: F.kl_div(F.log_softmax(c, -1), F.log_softmax(r, -1), log_target=True, reduction="batchmean"), dt)
        fix = lora_grad(lambda c, r: fixed_kl(c, r, reduction="sum") / c.shape[0], dt)
        assert fix == 0.0 and std > 0.0, (dt, std, fix)
        print(f"K1 {dt}: standard KL grad on LoRA B {std:.1e}, fixed {fix}")


def test_k2():
    def std(v, o):
        lp, lq = F.log_softmax(v, -1), F.log_softmax(o, -1)
        return (lp.exp() * (lp - lq)).sum(-1).mean()
    for dt in (torch.float32, torch.bfloat16):
        s = lora_grad(std, dt)
        f = lora_grad(lambda v, o: fixed_reverse_kl(v, o).mean(), dt)
        assert f == 0.0 and s > 0.0, (dt, s, f)
        print(f"K2 {dt}: standard reverse KL grad on LoRA B {s:.1e}, fixed {f}")


def test_k3():
    zv = (torch.randn(8, 300, generator=g, dtype=torch.float64) * 3).requires_grad_(True)
    zo = torch.randn(8, 300, generator=g, dtype=torch.float64) * 3
    lp, lq = F.log_softmax(zv, -1), F.log_softmax(zo, -1)
    ref = (lp.exp() * (lp - lq)).sum(-1)
    (gr,) = torch.autograd.grad((ref * torch.arange(1.0, 9.0, dtype=torch.float64)).sum(), zv)
    zv2 = zv.detach().clone().requires_grad_(True)
    mine = fixed_reverse_kl(zv2, zo)
    (mine * torch.arange(1.0, 9.0, dtype=torch.float64)).sum().backward()
    ef, eg = (mine - ref).abs().max().item(), (zv2.grad - gr).abs().max().item()
    assert ef < 1e-12 and eg < 1e-12, (ef, eg)
    print(f"K3 ok: reverse KL forward err {ef:.1e}, grad err {eg:.1e} (fp64)")


if __name__ == "__main__":
    test_k1(); test_k2(); test_k3()
    print("K1-K3 passed")
