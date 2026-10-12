"""Distil day (GW-PC, addendum A19): put the T0 policy into the add-on, so the run can then learn at T = 1.

The parent plays at T0 (view-blind, flat); on the views of that play the add-on alone is trained at T = 1 to minimise
KL(p || softmax(log-probs)), p = the parent's softmax(log-probs / T0). A seeded 90/10 split of the views gives a held-out KL;
training stops after the pass where it is <= KL_STOP, or after MAX_PASSES.
"""
import time

import numpy as np
import torch

from game import pg, play

DISTIL_DAY, DISTIL_VIEWS, HOLDOUT, MAX_PASSES, KL_STOP = 50, 4096, 0.1, 12, 0.05
LR, MINIBATCH, CHUNK = 1e-3, 256, 64


def targets(m, views, T0, bs=64):
    """p = row softmax(move_logprobs / T0) -> float64 [n, 17]."""
    z = play.move_logprobs(m, views, bs) / T0
    z = z - z.max(-1, keepdims=True)
    p = np.exp(z)
    return p / p.sum(-1, keepdims=True)


def kl(p, logq):
    """Mean over rows of sum p (log p - logq), 0 log 0 = 0. numpy [n, 17] each."""
    p = np.asarray(p, float)
    with np.errstate(divide='ignore', invalid='ignore'):
        t = np.where(p > 0, p * (np.log(p) - logq), 0.0)
    return float(t.sum(-1).mean()) if len(p) else 0.0


def kl_torch(p, logq):
    """As kl for torch tensors (grad flows through logq)."""
    t = torch.where(p > 0, p * (torch.log(p.clamp_min(1e-300)) - logq), torch.zeros_like(p))
    return t.sum(-1).mean()


def heldout(m, views, p, bs=64):
    """-> (KL(p || softmax(log-probs)), mean entropy of that softmax), add-on state as the caller left it, no grad."""
    lp = play.move_logprobs(m, views, bs)
    logq = lp - lp.max(-1, keepdims=True)
    logq = logq - np.log(np.exp(logq).sum(-1, keepdims=True))
    return kl(p, logq), pg.entropy(lp)


def run(m, addon, views, p, seed):
    """Train the add-on on views [n] with targets p [n, 17]. -> (stats dict, per-minibatch losses). Deterministic for `seed`."""
    n = len(views)
    t0 = time.time()
    perm = np.random.default_rng(seed).permutation(n)
    n_held = min(max(round(HOLDOUT * n), 1), n - 1)
    held, train = perm[:n_held].tolist(), perm[n_held:].tolist()
    hv, hp = [views[i] for i in held], p[held]
    pt = torch.as_tensor(p, dtype=torch.float32)
    torch.manual_seed(seed)
    addon.on = True
    params = addon.params()
    opt = torch.optim.Adam(params, lr=LR)
    gen = torch.Generator().manual_seed(seed)
    tr = torch.as_tensor(train)
    losses, train_kl, held_kl, ent = [], [], [], None
    for _ in range(MAX_PASSES):
        order = tr[torch.randperm(len(tr), generator=gen)]
        pl = []
        for i in range(0, len(order), MINIBATCH):
            ix = order[i:i + MINIBATCH]
            opt.zero_grad(set_to_none=True)
            mb = 0.0
            for c in range(0, len(ix), CHUNK):   # chunks with summed gradients, as pg.night
                cx = ix[c:c + CHUNK]
                w = len(cx) / len(ix)
                lg = play.move_logprobs_grad(m, [views[j] for j in cx.tolist()])
                loss = kl_torch(pt[cx], torch.log_softmax(lg.float(), -1))
                (loss * w).backward()
                mb += float(loss.detach()) * w
            torch.nn.utils.clip_grad_norm_(params, pg.MAX_GRAD_NORM)
            opt.step()
            losses.append(mb)
            pl.append(mb)
        train_kl.append(round(float(np.mean(pl)), 5))
        k, ent = heldout(m, hv, hp)
        held_kl.append(round(k, 5))
        if k <= KL_STOP:
            break
    m.eval()
    return dict(passes=len(held_kl), train_kl_per_pass=train_kl, heldout_kl_per_pass=held_kl, heldout_kl=held_kl[-1],
                heldout_entropy=round(ent, 4), n_train=len(train), n_heldout=len(held), updates=len(losses),
                seconds=round(time.time() - t0, 1)), losses
