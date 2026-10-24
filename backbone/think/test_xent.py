"""CPU tests X1-X4 for xent.py:  python backbone/think/test_xent.py   (test_think1.py imports and calls test_x1..test_x4)

The bug these tests document (measured with torch 2.14.1 CPU; the margin m = z_t - LSE_{j!=t} z_j, V = 1000, 4 rows):
  F.cross_entropy fp32: target gradient is -4.5e-5 at m=10, -2.4e-7 at m=15 and exactly 0 at m>=16 (also 17, 18, 20, 30), while
                        3,996 of the 3,996 other entries keep non-zero gradients (~exp(-m)); the row then sums to +exp(-m), not 0.
  F.cross_entropy bf16: target gradient is exactly 0 from m=6 (also 7, 8, 10); the others stay non-zero.
The fixed loss keeps the target gradient at -sum of the others (a few e-9 at m=20) and every row sums to 0.
"""
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xent as X


def margin_logits(margin, dtype, n=4, v=1000, seed=0):
    """Random logits whose target has margin exactly `margin` over LSE of the other classes (set in fp64, then cast)."""
    g = torch.Generator().manual_seed(seed)
    z = torch.randn(n, v, dtype=torch.float64, generator=g)
    t = torch.randint(0, v, (n,), generator=g)
    for i in range(n):
        o = z[i].clone()
        o[t[i]] = float("-inf")
        z[i, t[i]] = torch.logsumexp(o, 0) + margin
    return z.to(dtype), t


def grad_of(fn, z, t=None):
    z = z.detach().clone().requires_grad_(True)
    out = fn(z) if t is None else fn(z, t)
    out.backward()
    return z.grad, out.detach()


def ref64(z, t):
    """float64 reference built from softplus(LSE_{j!=t}(z_j - z_t)) with plain autograd (no custom backward); (loss, grad)."""
    z = z.detach().double().requires_grad_(True)
    d = (z - z.gather(1, t[:, None])).scatter(1, t[:, None], float("-inf"))
    loss = F.softplus(torch.logsumexp(d, 1))
    loss.sum().backward()
    return loss.detach(), z.grad


def rowsum_rel(g):
    g = g.double()
    return (g.sum(1).abs() / g.abs().sum(1)).max().item()


def test_x1():
    """Forward equals F.cross_entropy (1e-6, fp32) on ordinary logits, with ignored rows; gradients agree too."""
    g = torch.Generator().manual_seed(1)
    z = torch.randn(64, 300, generator=g) * 3
    t = torch.randint(0, 300, (64,), generator=g)
    t[::7] = -100
    for red in ("none", "sum", "mean"):
        mine, out = grad_of(lambda a: X.fixed_cross_entropy(a, t, reduction=red).sum(), z)
        ref, outr = grad_of(lambda a: F.cross_entropy(a, t, reduction=red).sum(), z)
        e = (X.fixed_cross_entropy(z, t, reduction=red) - F.cross_entropy(z, t, reduction=red)).abs().max().item()
        assert e <= 1e-6 * max(1.0, F.cross_entropy(z, t, reduction=red).abs().max().item()), (red, e)
        assert (mine - ref).abs().max().item() <= 5e-6, (red, (mine - ref).abs().max().item())
    assert mine[t == -100].abs().max().item() == 0.0 and X.fixed_cross_entropy(z, t, reduction="none")[t == -100].abs().max() == 0
    for dt in (torch.float32, torch.bfloat16, torch.float64):  # an ignored row with far-apart logits: grad exactly 0, never NaN (exp(200) * 0)
        zi = torch.tensor([[0.0, 0.0, 0.0, 200.0, 0.0], [1.0, 2.0, 3.0, 4.0, 5.0], [0.0, 90.0, 0.0, -90.0, 0.0]], dtype=dt)
        ti = torch.tensor([-100, 2, -100])
        gi, li = grad_of(lambda a, b: X.fixed_cross_entropy(a, b, reduction="none").sum(), zi, ti)
        assert torch.isfinite(gi).all() and gi[0].abs().max() == 0 and gi[2].abs().max() == 0 and li.isfinite(), (dt, gi)
        assert gi[1].abs().max() > 0 and li.item() == X.fixed_cross_entropy(zi[1:2], ti[1:2], reduction="sum").item()
    big = torch.randn(8, 5000, generator=g) * 2
    tb = torch.randint(0, 5000, (8,), generator=g)
    e = (X.fixed_cross_entropy(big, tb, reduction="none") - F.cross_entropy(big, tb, reduction="none")).abs().max().item()
    assert e <= 1e-6, e
    print(f"X1 ok: forward/grad match F.cross_entropy (V=300 with ignored rows, V=5000 forward err {e:.1e}); ignored rows with far-apart logits give exactly 0 grad")


def test_x2():
    """Large margins: loss > 0 = softplus value, target grad non-zero, rows sum to 0, matches a float64 reference."""
    for dtype, margins, tol in ((torch.float32, (10, 17, 20, 30), 1e-4), (torch.bfloat16, (6, 8), 1e-2)):
        for m in margins:
            z, t = margin_logits(m, dtype)
            ar = torch.arange(len(t))
            gf, lf = grad_of(lambda a, b: X.fixed_cross_entropy(a, b, reduction="none").sum(), z, t)
            z64 = z.double()
            lr, gr = ref64(z, t)  # float64 reference; F.cross_entropy itself loses the tail in fp64 beyond m~25
            if m <= 20:
                gstd, _ = grad_of(lambda a, b: F.cross_entropy(a, b, reduction="none").sum(), z64, t)
                assert ((gstd - gr).abs() <= 1e-6 * gr.abs().clamp(min=1e-30) + 1e-15).all()
            loss = X.fixed_cross_entropy(z, t, reduction="none")
            assert (loss > 0).all(), (dtype, m, loss)
            assert ((loss.double() - lr).abs() <= 1e-4 * lr).all(), (dtype, m)
            assert (gf[ar, t] != 0).all() and (gf[ar, t].double() * gr[ar, t] > 0).all(), (dtype, m, gf[ar, t])
            err = ((gf.double() - gr).abs() / gr.abs().clamp(min=1e-30)).max().item()
            assert err <= tol, (dtype, m, err)
            rs = rowsum_rel(gf)
            assert rs <= (1e-6 if dtype == torch.float32 else 1e-2), (dtype, m, rs)  # bf16: the output grad itself is rounded to bf16
            if dtype == torch.bfloat16:
                rs32 = rowsum_rel(grad_of(lambda a, b: X.fixed_cross_entropy(a, b, reduction="none").sum(), z.float(), t)[0])
                assert rs32 <= 1e-6, rs32  # same values, fp32 output: the kernel's row sum is 0 before the bf16 cast
            gs, _ = grad_of(lambda a, b: F.cross_entropy(a, b, reduction="none").sum(), z, t)  # the bug, for the printout
            print(f"X2 {str(dtype)[6:]:8s} m={m:>2}: fixed target grad {gf[ar, t].double().mean():.3e} rowsum_rel {rs:.1e} "
                  f"max rel err vs fp64 {err:.1e} | standard target grad {gs[ar, t].float().abs().max():.1e}, "
                  f"others nonzero {int(((gs != 0).sum() - (gs[ar, t] != 0).sum()))}")
    z, t = margin_logits(20, torch.float32)
    gs, _ = grad_of(lambda a, b: F.cross_entropy(a, b, reduction="sum"), z, t)
    ar = torch.arange(len(t))
    assert (gs[ar, t] == 0).all(), "standard fp32 cross-entropy no longer collapses at margin 20 (torch changed?)"
    mask = torch.ones_like(gs, dtype=torch.bool)
    mask[ar, t] = False
    assert (gs[mask] != 0).all()
    zb, tb = margin_logits(8, torch.bfloat16)
    gb, _ = grad_of(lambda a, b: F.cross_entropy(a, b, reduction="sum"), zb, tb)
    assert (gb[ar, tb] == 0).all()
    zs, ts = torch.randn(3, 6, dtype=torch.float64), torch.tensor([2, -100, 5])
    zs.requires_grad_(True)
    assert torch.autograd.gradcheck(lambda a: X.fixed_cross_entropy(a, ts, reduction="none"), (zs,))
    assert torch.autograd.gradcheck(lambda a: X.fixed_cross_entropy(a, ts, reduction="mean"), (zs,))
    print("X2 ok: standard CE collapses (target grad 0, others non-zero) at fp32 m=20 and bf16 m=8; fixed CE does not; gradcheck ok")


def test_x3():
    """student == teacher: fixed_kl (and fixed soft CE) gradient is exactly 0 in fp32 and bf16; standard F.kl_div is not."""
    g = torch.Generator().manual_seed(3)
    for dtype in (torch.float32, torch.bfloat16):
        zt = (torch.randn(32, 500, generator=g) * 5).to(dtype)
        for name, fn in (("fixed_kl", X.fixed_kl), ("fixed_soft_ce", X.fixed_soft_cross_entropy)):
            gz, out = grad_of(lambda a: fn(a, zt), zt)
            assert torch.count_nonzero(gz) == 0, (dtype, name, gz.abs().max())
            if name == "fixed_kl":
                assert out.item() == 0.0, out
        std, _ = grad_of(lambda a: F.kl_div(F.log_softmax(a, -1), F.log_softmax(zt, -1), log_target=True, reduction="sum"), zt)
        print(f"X3 {str(dtype)[6:]:8s}: fixed_kl grad max |g| = 0 (exact); standard F.kl_div grad max |g| = {std.abs().max():.2e}, "
              f"non-zero entries {int(torch.count_nonzero(std))}/{std.numel()}")
    zt = torch.randn(8, 100, generator=g) * 3
    shift = grad_of(lambda a: X.fixed_kl(a, zt + 1.5), zt)[0].abs().max().item()  # student = teacher - 1.5: same softmax
    print(f"X3 info: student = teacher shifted by a constant (fp32) grad max |g| = {shift:.1e}")
    assert shift <= 1e-6
    print("X3 ok")


def test_x4():
    """Away from equality: fixed_kl / fixed soft CE values and gradients match autograd of the standard losses (fp64, 1e-5)."""
    g = torch.Generator().manual_seed(4)
    zt = torch.randn(16, 200, dtype=torch.float64, generator=g) * 3
    zs = zt + torch.randn(16, 200, dtype=torch.float64, generator=g) * 2
    lp = lambda a: F.log_softmax(a, -1)
    kl = lambda a: F.kl_div(lp(a), lp(zt), log_target=True, reduction="sum")
    sce = lambda a: -(F.softmax(zt, -1) * lp(a)).sum()
    gk, vk = grad_of(lambda a: X.fixed_kl(a, zt), zs)
    gr, vr = grad_of(kl, zs)
    assert (gk - gr).abs().max().item() <= 1e-5 and abs(vk.item() - vr.item()) <= 1e-9 * max(1, abs(vr.item())), (gk - gr).abs().max()
    gc, vc = grad_of(lambda a: X.fixed_soft_cross_entropy(a, zt), zs)
    gcr, vcr = grad_of(sce, zs)
    assert (gc - gcr).abs().max().item() <= 1e-5 and abs(vc.item() - vcr.item()) <= 1e-9 * abs(vcr.item())
    assert (gk - gc).abs().max().item() <= 1e-12, "KL and soft CE must have the same gradient"
    assert abs(X.fixed_kl(zs, zt, reduction="mean").item() - vk.item() / 16) < 1e-12
    assert X.fixed_kl(zs, zt, reduction="none").shape == (16,)
    assert rowsum_rel(gk) <= 1e-10
    z32s, z32t = zs.float().requires_grad_(True), zt.float()
    X.fixed_kl(z32s, z32t).backward()
    assert (z32s.grad.double() - gr).abs().max().item() <= 1e-5, (z32s.grad.double() - gr).abs().max()
    a = zs.clone().requires_grad_(True)
    assert torch.autograd.gradcheck(lambda s: X.fixed_kl(s, zt[:3, :7], reduction="none"), (a[:3, :7].detach().clone().requires_grad_(True),))
    assert torch.autograd.gradcheck(lambda s: X.fixed_soft_cross_entropy(s, zt[:3, :7]), (a[:3, :7].detach().clone().requires_grad_(True),))
    print(f"X4 ok: fixed_kl vs autograd F.kl_div max grad diff {(gk - gr).abs().max():.1e} (fp64), fp32 {(z32s.grad.double() - gr).abs().max():.1e}")


def run_all():
    for f in (test_x1, test_x2, test_x3, test_x4):
        f()


if __name__ == "__main__":
    run_all()
    print("X1-X4 passed")
