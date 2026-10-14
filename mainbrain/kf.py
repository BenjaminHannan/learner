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
    the covariance G of the gradient arriving there. All-zero rows are skipped.
    pad_mask (constants "protect_pad_mask"): positions that are padding also stay out of A and G, and the per-example
    normalisation of G sees only the example's real positions. Layers whose inputs have a position axis that is aligned with a
    padding mask get it (self.masked lists them, name -> number of hooked calls that used it):
      - reader.blocks.*.conv (Conv1d): output positions where the reader's prompt_mask is False. The reader runs on the prompt
        and, per tape entry, on the entry's chars; a forward pre-hook on the reader takes the mask of whichever batch it is given.
      - core.*.kv, the call on the prompt memory X (mask = batch prompt_mask) and the call on the tape memory Xt (mask = the
        positions where Xt is exactly 0, i.e. padding chars and empty entries). Found by call order inside Tool.run (kvx, kvs0, kvt),
        through an instance-level kv_of wrapper and an instance-level run wrapper, removed by close().
    Everything else is as without the flag: the slot call of core.*.kv (no prompt position), the thinker rounds (core.*.q/o/qkv/p/fc/out,
    17 tokens), the heads (op_head, W_a, W_b, q_s, g_s, mode_head, q_word, stop_s), the cell / word axes (q_cp, g_cp, k_word, k_wc), and
    k_cp / k_s (their padded rows are exact zeros already, so the all-zero-row rule drops them)."""

    def __init__(self, m, norm=None, pad_mask=False):
        assert norm in (None, 'example'), norm
        self.norm = norm
        self.pad_mask = bool(pad_mask)
        self.masked = {}
        self.rmask = None        # reader's prompt_mask while the reader runs
        self.pending = {}        # kv module name -> mask of the call about to run
        self.restore = []
        self.hs = []
        self.mods = gp.projected_modules(m)
        if self.pad_mask:
            self._install_mask(m)
        self.A = {n: None for n, _ in self.mods}
        self.G = {n: None for n, _ in self.mods}
        self.hs += [mod.register_forward_hook(self._hook(n)) for n, mod in self.mods]

    def _install_mask(self, m):
        st = dict(pm=None, calls={})
        rd = m.reader
        self.hs.append(rd.register_forward_pre_hook(lambda mod, a: setattr(self, 'rmask', a[0]['prompt_mask'])))
        self.hs.append(rd.register_forward_hook(lambda mod, a, o: setattr(self, 'rmask', None)))
        prev_run = m.__dict__.get('run')
        orig_run = m.run

        def run(batch, *a, **k):
            st['pm'], st['calls'] = batch['prompt_mask'], {}
            return orig_run(batch, *a, **k)
        m.run = run
        self.restore.append(lambda: m.__dict__.pop('run', None) if prev_run is None else m.__dict__.__setitem__('run', prev_run))
        ref = m.src.weight[1].detach()
        for i, blk in enumerate(m.core):
            name = 'core.%d.kv' % i
            prev_kv = blk.__dict__.get('kv_of')
            orig_kv = blk.kv_of

            def kv_of(mem, name=name, orig_kv=orig_kv):
                c = st['calls'].get(name, 0)
                st['calls'][name] = c + 1
                if c == 0:                                  # kvx: the prompt memory X + src[1]
                    assert mem.shape[1] == st['pm'].shape[1], (mem.shape, st['pm'].shape)
                    self.pending[name] = st['pm']
                elif c >= 2:                                # kvt: the tape memory Xt + src[1] (c == 1 is the 16 number slots)
                    self.pending[name] = (mem.detach().float() - ref.float()).abs().amax(-1) > 0
                return orig_kv(mem)
            blk.kv_of = kv_of
            self.restore.append(lambda blk=blk, prev_kv=prev_kv: blk.__dict__.pop('kv_of', None) if prev_kv is None else blk.__dict__.__setitem__('kv_of', prev_kv))

    def _pmask(self, name, mod, x):
        """[B, T] bool mask of the real positions for this hooked call, or None (no mask for this layer / call)."""
        if not self.pad_mask:
            return None
        if isinstance(mod, torch.nn.Conv1d):
            pm = self.rmask
            if pm is not None:
                assert x.shape[0] == pm.shape[0] and x.shape[2] == pm.shape[1] and mod.stride[0] == 1 and 2 * mod.padding[0] + 1 == mod.kernel_size[0]
        else:
            pm = self.pending.pop(name, None)
            if pm is not None:
                assert x.shape[:2] == pm.shape, (name, x.shape, pm.shape)
        if pm is not None:
            self.masked[name] = self.masked.get(name, 0) + 1
        return pm

    def _add(self, d, name, X):
        c = X.T @ X
        d[name] = c if d[name] is None else d[name] + c

    def _hook(self, name):
        def hook(mod, inp, out):
            pm = self._pmask(name, mod, inp[0])
            X = gp._rows_of(inp[0].detach().float(), mod)
            keep = X.abs().sum(1) > 0
            if pm is not None:
                keep = keep & pm.reshape(-1)
            X = X[keep]
            if len(X):
                self._add(self.A, name, torch.cat([X, torch.ones(len(X), 1)], 1))
            if out.requires_grad:
                conv = isinstance(mod, torch.nn.Conv1d)

                def ghook(g):
                    if pm is not None:                   # padded positions: out of G and out of the per-example norm
                        g = g * (pm[:, None, :] if conv else pm[..., None]).to(g.dtype)
                    if self.norm == 'example':   # g has the batch as dim 0 ([B, T, out], Conv1d [B, out, T], or [B, out])
                        f = g.detach().float().flatten(1)
                        mx = f.abs().amax(1)                       # scale by the max first so tiny gradients do not underflow
                        n = torch.where(mx > 0, mx * (f / mx.clamp(min=1e-38)[:, None]).norm(dim=1), torch.ones_like(mx))
                        v = [-1] + [1] * (g.dim() - 1)
                        small = (mx > 0) & (mx < 1e-30)            # subnormal gradient: float32 mx*norm underflows to 0 (-> g/0 = inf -> NaN G)
                        if small.any():                            # redo those examples in float64; healthy examples keep the exact float32 path
                            f64 = f.double()
                            m64 = f64.abs().amax(1).clamp(min=1e-300)
                            n64 = m64 * (f64 / m64[:, None]).norm(dim=1)
                            g64 = g.detach().double() / n64.view(v)
                            g64 = torch.where(torch.isfinite(g64), g64, torch.zeros_like(g64)).to(g.dtype)   # non-finite block: skip it
                            g = torch.where(small.view(v), g64, g / n.view(v).to(g.dtype))
                        else:
                            g = g / n.view(v).to(g.dtype)
                    Y = (g.transpose(1, 2) if conv else g).reshape(-1, g.shape[1] if conv else g.shape[-1]).detach().float()
                    Y = Y[Y.abs().sum(1) > 0]
                    if len(Y):
                        self._add(self.G, name, Y)
                out.register_hook(ghook)
        return hook

    def close(self):
        for h in self.hs:
            h.remove()
        for r in self.restore:
            r()


def kfac_stats(m, rows, bs=64, norm=None, pad_mask=False, report=None):
    """A and G per module over the model's own old answers (rows' targets), eval mode (no drills). Parameters' grads are
    cleared afterwards. norm='example': each example's output-gradient block is scaled to unit Frobenius norm per layer
    before it enters G (A unchanged). pad_mask: see KCovs (report, a dict, gets .masked of the pass). -> {name: (A, G)}."""
    was = {n: p.requires_grad for n, p in m.named_parameters()}
    for p in m.parameters():
        p.requires_grad_(True)
    kc = KCovs(m, norm, pad_mask)
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
        if report is not None:
            report.update(kc.masked)
        for n, p in m.named_parameters():
            p.requires_grad_(was[n])
    return {n: (kc.A[n], kc.G[n]) for n, _ in kc.mods}


def eig(C):
    lam, V = torch.linalg.eigh(C.double())
    return lam.flip(0).clamp(min=0).float(), V.flip(1).float()


def mask_for(a, g, energy, soft=None):
    """M [out, in+1]: 0 on the pairs (j, i) holding the top `energy` share of sum a_i g_j, 1 elsewhere.
    soft (positive number s, graded mask): inside the set M = min(1, tau / (s * p)), p = g_j a_i, tau = p of the least important
    pair inside the set (so with s=1 the boundary pair gets 1 and a pair 10x more important gets 0.1); outside M stays 1.
    soft None or 0: the hard mask above, unchanged."""
    S = g[:, None] * a[None, :]
    flat = S.flatten()
    order = torch.argsort(flat, descending=True)
    cum = torch.cumsum(flat[order], 0) / flat.sum()
    k = int((cum < energy).sum().item()) + 1
    M = torch.ones_like(flat)
    if not soft:
        M[order[:k]] = 0.0
    else:
        top = order[:k]
        tau = flat[order[k - 1]]
        p = flat[top].clamp(min=1e-30)
        M[top] = torch.clamp(tau / (soft * p), max=1.0)
    return M.view_as(S), k


def factors(stats, energy, soft=None):
    """{name: (U, V, M)} and a per-layer summary. soft: see mask_for; adds m_median, frac_gt_0_1 (share of protected pairs with
    M > 0.1) and soft to each layer's summary."""
    F, info = {}, {}
    for n, (A, G) in stats.items():
        if A is None or G is None:
            continue
        a, U = eig(A)
        g, V = eig(G)
        M, k = mask_for(a, g, energy, soft)
        F[n] = (U, V, M)
        info[n] = dict(pairs=M.numel(), protected=k, free_share=round(1 - k / M.numel(), 4))
        if soft:
            prot = (g[:, None] * a[None, :]).flatten().argsort(descending=True)[:k]
            Mp = M.flatten()[prot]
            info[n].update(m_median=float(Mp.median()), frac_gt_0_1=float((Mp > 0.1).float().mean()), soft=soft)
    return F, info


def project(D, f):
    U, V, M = f
    return V @ ((V.T @ D @ U) * M) @ U.T


def project_both(D, f, f0):
    """project(project(D, f), f0); a missing factor (None) is skipped."""
    if f is not None:
        D = project(D, f)
    if f0 is not None:
        D = project(D, f0)
    return D


class KFOptimizer:
    """Wraps an optimizer: after each step, each module's change in [W | b] is projected with its (U, V, M).
    refresh (optional): a function returning new factors, called after every `every` steps, so the protected directions
    follow the weights as they move during a long night (the projection is a small-step rule).
    F0 (optional, arm U "protect_parent"): the factors measured on the parent weights. The change is then projected by the
    night's own factors and then by F0: D <- project(project(D, F[n]), F0[n]); a module in only one dict gets the one it has.
    F0=None is the plain behaviour."""

    def __init__(self, m, base, F, refresh=None, every=0, F0=None):
        self.m, self.base, self.refresh, self.every, self.n, self.F0 = m, base, refresh, every, 0, F0
        self._set(F)
        self.param_groups = base.param_groups

    def _set(self, F):
        if self.F0 is None:
            self.mods = [(n, mod, F[n]) for n, mod in gp.projected_modules(self.m) if n in F]
        else:
            self.mods = [(n, mod, (F.get(n), self.F0.get(n))) for n, mod in gp.projected_modules(self.m) if n in F or n in self.F0]

    def step(self):
        old = [gp.aug_weight(mod).detach().clone() for _, mod, _ in self.mods]
        self.base.step()
        for (n, mod, f), A0 in zip(self.mods, old):
            if self.F0 is None:
                gp.set_aug(mod, A0 + project(gp.aug_weight(mod).detach() - A0, f))
            else:
                gp.set_aug(mod, A0 + project_both(gp.aug_weight(mod).detach() - A0, *f))
        self.n += 1
        if self.refresh and self.every and self.n % self.every == 0:
            was = self.m.training
            self._set(self.refresh())   # after this step's update; it clears grads, which train_night clears next anyway
            self.m.train(was)

    def zero_grad(self, set_to_none=True):
        self.base.zero_grad(set_to_none=set_to_none)

    def state_dict(self):
        return self.base.state_dict()


class SplitKFOptimizer:
    """Arm R ("protect_replay": "free"): the new-lesson half of a batch is stepped as KFOptimizer does (AdamW with weight decay, then
    each module's change in [W | b] projected with (U, V, M)); the replay half, whose clipped gradients the loss wrapper stashed
    (fullrun.split_loss), is stepped by a second AdamW (base_rep, no weight decay) and is NOT projected.
    `stash` is a dict {param: grad} filled by the wrapper before each step and cleared here. The guess head (guess.make_opt) is a
    param group of base_new only; it is not in m.parameters(), so base_rep (built from m.parameters()) never contains it."""

    def __init__(self, m, base_new, base_rep, F, stash):
        self.m, self.base_new, self.base_rep, self.stash = m, base_new, base_rep, stash
        self.mods = [(n, mod, F[n]) for n, mod in gp.projected_modules(m) if n in F]
        self.param_groups = base_new.param_groups

    def step(self):
        old = [gp.aug_weight(mod).detach().clone() for _, mod, _ in self.mods]
        self.base_new.step()
        for (n, mod, f), A0 in zip(self.mods, old):
            gp.set_aug(mod, A0 + project(gp.aug_weight(mod).detach() - A0, f))
        for g in self.base_rep.param_groups:
            for p in g['params']:
                p.grad = self.stash.get(p)
        self.base_rep.step()
        for g in self.base_rep.param_groups:
            for p in g['params']:
                p.grad = None
        self.stash.clear()

    def zero_grad(self, set_to_none=True):
        self.base_new.zero_grad(set_to_none=set_to_none)
        self.base_rep.zero_grad(set_to_none=set_to_none)

    def state_dict(self):
        return self.base_new.state_dict()


class PrecondReplayKFOptimizer:
    """Arm R2 ("protect_replay": "precond"): base_new steps the new-lesson half and each module's change in [W | b] is projected
    (with (U, V, M), then F0 too if given, as KFOptimizer). The replay half's clipped gradient g (stashed by fullrun.split_loss) is
    then applied as p -= lr * g / (sqrt(v_hat) + eps), v_hat = base_new's bias-corrected second moment of p: no second AdamW, no
    momentum, no weight decay, no projection. A parameter base_new has no exp_avg_sq for yet is skipped that step. `stash` is
    cleared each step. The guess head is a param group of base_new only and never has a stashed grad."""

    def __init__(self, m, base_new, F, stash, F0=None):
        self.m, self.base_new, self.stash, self.F0 = m, base_new, stash, F0
        if F0 is None:
            self.mods = [(n, mod, F[n]) for n, mod in gp.projected_modules(m) if n in F]
        else:
            self.mods = [(n, mod, (F.get(n), F0.get(n))) for n, mod in gp.projected_modules(m) if n in F or n in F0]
        self.param_groups = base_new.param_groups

    def step(self):
        old = [gp.aug_weight(mod).detach().clone() for _, mod, _ in self.mods]
        self.base_new.step()
        for (n, mod, f), A0 in zip(self.mods, old):
            if self.F0 is None:
                gp.set_aug(mod, A0 + project(gp.aug_weight(mod).detach() - A0, f))
            else:
                gp.set_aug(mod, A0 + project_both(gp.aug_weight(mod).detach() - A0, *f))
        with torch.no_grad():
            for grp in self.base_new.param_groups:
                beta2, eps, lr = grp['betas'][1], grp['eps'], grp['lr']
                for p in grp['params']:
                    g = self.stash.get(p)
                    st = self.base_new.state.get(p)
                    if g is None or not st or 'exp_avg_sq' not in st:
                        continue
                    v_hat = st['exp_avg_sq'] / (1 - beta2 ** float(st['step']))
                    p.sub_(lr * g / (v_hat.sqrt() + eps))
        self.stash.clear()

    def zero_grad(self, set_to_none=True):
        self.base_new.zero_grad(set_to_none=set_to_none)

    def state_dict(self):
        return self.base_new.state_dict()
