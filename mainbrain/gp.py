"""Null-space learning for the main brain (GP): learn a new subject only in directions its old questions do not use.

Main-brain thread (ultracode), 10-10/11. Idea from GPM (Saha et al. 2021), Adam-NSCL (Wang et al. 2021) and AlphaEdit (2025):
before a night, the model runs its own old questions (its diary: TRAIN prompts answered by its pre-mode self) and records,
for every Linear and Conv1d layer, which input directions those questions use (the covariance of the layer's inputs, with a
constant 1 appended so the bias is handled with the weight). The directions holding a share `energy` of that input energy
are the protected subspace U. During the night every optimizer step is applied as usual (AdamW, weight decay, clip), then
the change of each layer's weight and bias is projected so it no longer acts on U:

    [dW db] <- [dW db] (I - U U^T)

so, to first order, the layer's output on an old question's input is unchanged, and so is every later layer's input.
The update is projected after the optimizer, not the raw gradient, because Adam rescales each weight and weight decay
shrinks every direction, either of which would leak back into U (Adam-NSCL's point).

Parameters that cannot be projected this way are frozen: embedding tables, LayerNorm gains and biases, and the talker's
output bias. They act on every question at once.

Everything here is the model measuring itself (its own old questions, its own activations) with fixed rules and one
constant (`energy`), the same for every subject. No panel or DEV row is read.
"""
import math

import torch
import torch.nn.functional as F

from custom_io.data import Dataset, collate, to_device


def projected_modules(m):
    """(name, module) for every Linear and Conv1d of the model."""
    return [(n, mod) for n, mod in m.named_modules() if isinstance(mod, (torch.nn.Linear, torch.nn.Conv1d))]


def _rows_of(x, mod):
    """The inputs a module saw, as rows [N, in(*k)] (Conv1d: one row per output position, the k-wide patch)."""
    if isinstance(mod, torch.nn.Linear):
        return x.reshape(-1, x.shape[-1])
    k, pad = mod.kernel_size[0], mod.padding[0]
    xp = F.pad(x, (pad, pad))                                      # x: [B, C, T]
    P = xp.unfold(2, k, mod.stride[0])                             # [B, C, T', k]
    return P.permute(0, 2, 1, 3).reshape(-1, x.shape[1] * k)       # matches weight.reshape(out, C * k)


class Covs:
    """Forward hooks that add each module's input covariance (with a constant 1 appended) over the batches run while on.
    All-zero rows (padding, masked positions) are skipped, so padding does not inflate the bias direction."""

    def __init__(self, m):
        self.mods = projected_modules(m)
        self.C = {n: None for n, _ in self.mods}
        self.N = {n: 0 for n, _ in self.mods}
        self.on = False
        self.hs = [mod.register_forward_hook(self._hook(n)) for n, mod in self.mods]

    def _hook(self, name):
        def hook(mod, inp, out):
            if not self.on:
                return
            X = _rows_of(inp[0].detach().float(), mod)
            X = X[X.abs().sum(1) > 0]
            if not len(X):
                return
            X = torch.cat([X, torch.ones(len(X), 1)], 1)
            c = X.T @ X
            self.C[name] = c if self.C[name] is None else self.C[name] + c
            self.N[name] += len(X)
        return hook

    def close(self):
        for h in self.hs:
            h.remove()


def run_rows(m, rows, bs=64, greedy_pass=True, loss_pass=True):
    """Run the model on rows the way it answers (greedy run + talk) and the way it trains (loss, eval mode: no drills)."""
    m.eval()
    with torch.no_grad():
        for s in range(0, len(rows), bs):
            chunk = rows[s:s + bs]
            if greedy_pass:
                ds = Dataset([{'id': f'c{i}', 'prompt': r['prompt'], 'answer': '', 'accepted': [], 'family': '', 'level': 0}
                              for i, r in enumerate(chunk)], m.vocab, strict=False)
                b = to_device(collate([ds[i] for i in range(len(chunk))]), 'cpu')
                o = m.run(b)
                m.talk(m.state_of(o), b)
            if loss_pass:
                ds = Dataset(chunk, m.vocab)
                m.loss(to_device(collate([ds[i] for i in range(len(chunk))]), 'cpu'))


def covariances(m, rows, bs=64):
    """-> {name: (C [in+1, in+1], N)} over the given rows."""
    cv = Covs(m)
    cv.on = True
    try:
        run_rows(m, rows, bs)
    finally:
        cv.on = False
        cv.close()
    return {n: (cv.C[n], cv.N[n]) for n, _ in cv.mods}


def basis(C, energy):
    """Eigenvectors of C holding at least `energy` of its trace, largest first. -> (U [d, k], eigenvalues all, k)."""
    lam, V = torch.linalg.eigh(C.double())
    lam, V = lam.flip(0).clamp(min=0), V.flip(1)
    cum = torch.cumsum(lam, 0) / lam.sum()
    k = int((cum < energy).sum().item()) + 1
    k = min(k, len(lam))
    return V[:, :k].float(), lam, k


def projectors(covs, energy):
    """{name: P = I - U U^T} and a per-layer summary (kept dims, free dims)."""
    P, info = {}, {}
    for n, (C, N) in covs.items():
        if C is None:
            continue
        U, lam, k = basis(C, energy)
        P[n] = torch.eye(C.shape[0]) - U @ U.T
        info[n] = dict(dim=C.shape[0], protected=k, free=C.shape[0] - k, rows=N)
    return P, info


def aug_weight(mod):
    """[W.reshape(out, -1) | b] as one matrix [out, in(*k) + 1]."""
    W = mod.weight.reshape(mod.weight.shape[0], -1)
    b = mod.bias if mod.bias is not None else torch.zeros(W.shape[0])
    return torch.cat([W, b[:, None]], 1)


def set_aug(mod, A):
    with torch.no_grad():
        mod.weight.copy_(A[:, :-1].reshape(mod.weight.shape))
        if mod.bias is not None:
            mod.bias.copy_(A[:, -1])


def freeze_unprojected(m):
    """Freeze every parameter that is not the weight or bias of a projected module. -> names frozen."""
    keep = set()
    for n, mod in projected_modules(m):
        keep.add(id(mod.weight))
        if mod.bias is not None:
            keep.add(id(mod.bias))
    frozen = []
    for n, p in m.named_parameters():
        if id(p) not in keep:
            p.requires_grad_(False)
            frozen.append(n)
    return frozen


class GPOptimizer:
    """Wraps an optimizer: after each step, each projected module's change in [W | b] is projected by its P."""

    def __init__(self, m, base, P):
        self.base = base
        self.mods = [(n, mod, P[n]) for n, mod in projected_modules(m) if n in P]
        self.param_groups = base.param_groups

    def step(self):
        old = [aug_weight(mod).detach().clone() for _, mod, _ in self.mods]
        self.base.step()
        for (n, mod, P), A0 in zip(self.mods, old):
            set_aug(mod, A0 + (aug_weight(mod).detach() - A0) @ P)

    def zero_grad(self, set_to_none=True):
        self.base.zero_grad(set_to_none=set_to_none)

    def state_dict(self):
        return self.base.state_dict()
