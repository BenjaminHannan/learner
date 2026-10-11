"""Kronecker-factored protection (KF): protect only the weight directions the old answers actually depend on.

GP (gp.py) protects every input direction old questions use, for every output of a layer. KF also asks which outputs
matter: for each Linear and Conv1d layer it measures, on the model's own old answers (its diary), the input covariance A
(as gp.py) and the covariance G of the loss gradient at the layer's output (how much each output direction moves the old
answers). With A = U diag(a) U^T and G = V diag(g) V^T (K-FAC, Martens and Grosse 2015; Ritter et al. 2018), the weight
direction v_j u_i^T has importance a_i * g_j. The pairs holding a share `energy` of the total importance are protected:
after each optimizer step the change of [W | b] is rotated into that basis, the protected entries are zeroed, and it is
rotated back:

    D <- V ((V^T D U) * M) U^T,   M_ij = 0 for protected pairs, 1 otherwise

The rest of gp.py applies: the update is projected after AdamW, unprojectable parameters (embeddings, LayerNorm, output
bias) are frozen, and the only constant is `energy`, the same for every subject. Only the model's own old questions and
its own answers to them are read.
"""
import torch

from custom_io.data import Dataset, collate, to_device
from mainbrain import gp


class KCovs:
    """Forward hooks: input covariance A (with a constant 1) per module, and a tensor hook on the module's output that adds
    the covariance G of the gradient arriving there. All-zero rows are skipped."""

    def __init__(self, m, norm=None):
        assert norm in (None, 'example'), norm
        self.norm = norm
        self.mods = gp.projected_modules(m)
        self.A = {n: None for n, _ in self.mods}
        self.G = {n: None for n, _ in self.mods}
        self.hs = [mod.register_forward_hook(self._hook(n)) for n, mod in self.mods]

    def _add(self, d, name, X):
        c = X.T @ X
        d[name] = c if d[name] is None else d[name] + c

    def _hook(self, name):
        def hook(mod, inp, out):
            X = gp._rows_of(inp[0].detach().float(), mod)
            X = X[X.abs().sum(1) > 0]
            if len(X):
                self._add(self.A, name, torch.cat([X, torch.ones(len(X), 1)], 1))
            if out.requires_grad:
                conv = isinstance(mod, torch.nn.Conv1d)

                def ghook(g):
                    if self.norm == 'example':   # g has the batch as dim 0 ([B, T, out], Conv1d [B, out, T], or [B, out])
                        f = g.detach().float().flatten(1)
                        mx = f.abs().amax(1)                       # scale by the max first so tiny gradients do not underflow
                        n = torch.where(mx > 0, mx * (f / mx.clamp(min=1e-38)[:, None]).norm(dim=1), torch.ones_like(mx))
                        g = g / n.view(-1, *([1] * (g.dim() - 1))).to(g.dtype)
                    Y = (g.transpose(1, 2) if conv else g).reshape(-1, g.shape[1] if conv else g.shape[-1]).detach().float()
                    Y = Y[Y.abs().sum(1) > 0]
                    if len(Y):
                        self._add(self.G, name, Y)
                out.register_hook(ghook)
        return hook

    def close(self):
        for h in self.hs:
            h.remove()


def kfac_stats(m, rows, bs=64, norm=None):
    """A and G per module over the model's own old answers (rows' targets), eval mode (no drills). Parameters' grads are
    cleared afterwards. norm='example': each example's output-gradient block is scaled to unit Frobenius norm per layer
    before it enters G (A unchanged). -> {name: (A, G)}."""
    was = {n: p.requires_grad for n, p in m.named_parameters()}
    for p in m.parameters():
        p.requires_grad_(True)
    kc = KCovs(m, norm)
    m.eval()
    try:
        ds = Dataset(rows, m.vocab)
        for s in range(0, len(rows), bs):
            idx = range(s, min(s + bs, len(rows)))
            out = m.loss(to_device(collate([ds[i] for i in idx]), 'cpu'))
            (out[0] if isinstance(out, tuple) else out).backward()
            m.zero_grad(set_to_none=True)
    finally:
        kc.close()
        for n, p in m.named_parameters():
            p.requires_grad_(was[n])
    return {n: (kc.A[n], kc.G[n]) for n, _ in kc.mods}


def eig(C):
    lam, V = torch.linalg.eigh(C.double())
    return lam.flip(0).clamp(min=0).float(), V.flip(1).float()


def mask_for(a, g, energy):
    """M [out, in+1]: 0 on the pairs (j, i) holding the top `energy` share of sum a_i g_j, 1 elsewhere."""
    S = g[:, None] * a[None, :]
    flat = S.flatten()
    order = torch.argsort(flat, descending=True)
    cum = torch.cumsum(flat[order], 0) / flat.sum()
    k = int((cum < energy).sum().item()) + 1
    M = torch.ones_like(flat)
    M[order[:k]] = 0.0
    return M.view_as(S), k


def factors(stats, energy):
    """{name: (U, V, M)} and a per-layer summary."""
    F, info = {}, {}
    for n, (A, G) in stats.items():
        if A is None or G is None:
            continue
        a, U = eig(A)
        g, V = eig(G)
        M, k = mask_for(a, g, energy)
        F[n] = (U, V, M)
        info[n] = dict(pairs=M.numel(), protected=k, free_share=round(1 - k / M.numel(), 4))
    return F, info


def project(D, f):
    U, V, M = f
    return V @ ((V.T @ D @ U) * M) @ U.T


class KFOptimizer:
    """Wraps an optimizer: after each step, each module's change in [W | b] is projected with its (U, V, M).
    refresh (optional): a function returning new factors, called after every `every` steps, so the protected directions
    follow the weights as they move during a long night (the projection is a small-step rule)."""

    def __init__(self, m, base, F, refresh=None, every=0):
        self.m, self.base, self.refresh, self.every, self.n = m, base, refresh, every, 0
        self._set(F)
        self.param_groups = base.param_groups

    def _set(self, F):
        self.mods = [(n, mod, F[n]) for n, mod in gp.projected_modules(self.m) if n in F]

    def step(self):
        old = [gp.aug_weight(mod).detach().clone() for _, mod, _ in self.mods]
        self.base.step()
        for (n, mod, f), A0 in zip(self.mods, old):
            gp.set_aug(mod, A0 + project(gp.aug_weight(mod).detach() - A0, f))
        self.n += 1
        if self.refresh and self.every and self.n % self.every == 0:
            was = self.m.training
            self._set(self.refresh())   # after this step's update; it clears grads, which train_night clears next anyway
            self.m.train(was)

    def zero_grad(self, set_to_none=True):
        self.base.zero_grad(set_to_none=set_to_none)

    def state_dict(self):
        return self.base.state_dict()
