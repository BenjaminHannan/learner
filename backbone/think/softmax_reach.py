"""Is the Softmax Cancellation bug reachable in sleep1/sleepb (KL guard) and rlaif (JOLT+ KL), and does it matter?  CPU only.

A LoRA-style toy: logits = (h + scale * (h @ A.T) @ B.T) @ W.T with Qwen3's vocab (151,936), B = 0 at the start (as PEFT inits it),
so at step 0 the adapted model equals the reference bitwise, which is sleep's "start of a night" case.
  R1  KL-only gradient on B at B = 0: standard F.kl_div vs xent.fixed_kl (sleep direction).
  R2  CE gradient on B on the same batch, for scale.
  R3  KL-only Adam for 100 steps from B = 0: how far B drifts (should stay 0).
  R4  CE + KL, one Adam step: how much the standard residual changes the update vs the fixed KL.
  R5  rlaif direction (gradient on the view side): residual at equal logits vs the real gradient when the "other" view's hidden state
      differs only by bf16 rounding (the smallest difference two different contexts can produce).
Writes softmax_reach.json next to this file.   python backbone/think/softmax_reach.py
"""
import json
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xent import fixed_kl  # noqa: E402
from xent_reverse import fixed_reverse_kl  # noqa: E402

V, D, R, N, SCALE = 151_936, 64, 8, 64, 2.0
g = torch.Generator().manual_seed(0)
W = torch.randn(V, D, generator=g) * 0.6
h = torch.randn(N, D, generator=g)
A = torch.randn(R, D, generator=g) / D ** 0.5
tgt = torch.randint(0, V, (N,), generator=g)


def logits(B, hh=h):
    return (hh + SCALE * (hh @ A.T) @ B.T) @ W.T


def std_kl(cur, ref):  # sleep1.py / sleepb.py line, batchmean
    return F.kl_div(F.log_softmax(cur.float(), -1), F.log_softmax(ref.float(), -1), log_target=True, reduction="batchmean")


def fix_kl(cur, ref):
    return fixed_kl(cur.float(), ref.float(), reduction="sum") / cur.shape[0]


def std_rkl(zv, zo):  # rlaif/rollout.py _lp_kl
    lp, lq = F.log_softmax(zv.float(), -1), F.log_softmax(zo.float(), -1)
    return (lp.exp() * (lp - lq)).sum(-1).sum() / zv.shape[0]


def fix_rkl(zv, zo):
    return fixed_reverse_kl(zv.float(), zo.float()).sum() / zv.shape[0]


def grad_B(loss_fn, B0=None):
    B = (torch.zeros(D, R) if B0 is None else B0.clone()).requires_grad_(True)
    loss_fn(B).backward()
    return B.grad


def adam_drift(kl_fn, steps=100, lr=1e-4):
    B = torch.zeros(D, R, requires_grad=True)
    opt = torch.optim.AdamW([B], lr=lr, weight_decay=0.0)
    with torch.no_grad():
        ref = logits(torch.zeros(D, R))
    for _ in range(steps):
        opt.zero_grad()
        kl_fn(logits(B), ref).backward()
        opt.step()
    with torch.no_grad():
        return B.abs().max().item(), float(std_kl(logits(B), ref))


out = {}
with torch.no_grad():
    z0 = logits(torch.zeros(D, R))
    p = F.softmax(z0, -1)
out["toy"] = {"V": V, "max_prob_median": p.max(-1).values.median().item(), "entropy_nats_median": (-(p * p.clamp_min(1e-30).log()).sum(-1)).median().item()}

for name, dt in (("fp32", torch.float32), ("bf16", torch.bfloat16)):
    ref = z0.to(dt)
    gs = grad_B(lambda B: std_kl(logits(B).to(dt), ref))
    gf = grad_B(lambda B: fix_kl(logits(B).to(dt), ref))
    out[f"R1_{name}"] = {"std_kl_gradB_max": gs.abs().max().item(), "fixed_kl_gradB_max": gf.abs().max().item()}

gce = grad_B(lambda B: F.cross_entropy(logits(B), tgt))
out["R2"] = {"ce_gradB_max": gce.abs().max().item(), "ce_gradB_median": gce.abs().median().item()}

for name, fn in (("std", std_kl), ("fixed", fix_kl)):
    bmax, kl = adam_drift(fn)
    out[f"R3_{name}"] = {"B_absmax_after_100_adam_steps_lr1e-4": bmax, "kl_after": kl}


def one_step(kl_fn, lr=1e-4):
    B = torch.zeros(D, R, requires_grad=True)
    opt = torch.optim.AdamW([B], lr=lr, weight_decay=0.0)
    (F.cross_entropy(logits(B), tgt) + kl_fn(logits(B), z0)).backward()
    opt.step()
    return B.detach()


us, uf = one_step(std_kl), one_step(fix_kl)
out["R4"] = {"update_absmax": uf.abs().max().item(), "std_minus_fixed_absmax": (us - uf).abs().max().item(),
             "rel": ((us - uf).abs().max() / uf.abs().max()).item()}

h_other = h.bfloat16().float()  # nearest different context: bf16 rounding of the hidden state
with torch.no_grad():
    zo_same, zo_near = z0, logits(torch.zeros(D, R), h_other)
for name, zo in (("equal", zo_same), ("bf16_near", zo_near)):
    gs = grad_B(lambda B: std_rkl(logits(B), zo))
    gf = grad_B(lambda B: fix_rkl(logits(B), zo))
    out[f"R5_{name}"] = {"std_rkl_gradB_max": gs.abs().max().item(), "fixed_rkl_gradB_max": gf.abs().max().item(),
                         "kl": float(fix_rkl(z0, zo))}

print(json.dumps(out, indent=1))
(Path(__file__).resolve().parent / "softmax_reach.json").write_text(json.dumps(out, indent=1) + "\n")
