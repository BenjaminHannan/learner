"""M1 "one shelf": five rank-8 pieces and one skill readout inside one model file (marks: cohesive-model/M1-MARKS-2026-10-10.md).

piece_from      the difference between a run's final checkpoint and the parent, as rank-8 factors per Linear weight
workspace_features / reader_features   what the readout looks at (arm T / arm R)
both_features   reader mean (256) then workspace (2,048) side by side, 2,304 columns (arm TR), plus the glance answers
fit_router / route   the 6-way softmax readout (none, sheet, rpn, stats, invoice, py)
Shelf           parent + pieces + readout; save / load one file; use(k) adds piece k in place; answer(prompts)
"""
import contextlib

import torch

from custom_io.data import CharVocab
from custom_io.models import build
from domain import route as _route
from domain.mode import Dataset, collate, to_device

SUBJECTS = ('sheet', 'rpn', 'stats', 'invoice', 'py')
CLASSES = ('none',) + SUBJECTS
RECON_TOL = 1e-4
N_CTRL = 8


def linear_names(m):
    """Names of the 2-D weights of the model's nn.Linear modules."""
    return [n + '.weight' for n, x in m.named_modules() if isinstance(x, torch.nn.Linear)]


def piece_from(parent_sd, final_sd, linear, rank=8, with_report=False):
    """{name: (B [out, r], A [r, in])} with B @ A = final - parent (truncated SVD, r = min(rank, rows)).
    Asserts the same tensor names, that only 2-D Linear weights differ, and a max abs reconstruction error < 1e-4."""
    assert set(parent_sd) == set(final_sd), 'checkpoints have different tensors'
    linear = set(linear)
    out, rep = {}, dict(changed=0, numbers=0, max_err=0.0)
    for k in parent_sd:
        a, b = parent_sd[k], final_sd[k]
        assert a.shape == b.shape, f'shape differs: {k}'
        if torch.equal(a, b):
            continue
        assert k in linear and a.dim() == 2, f'a tensor other than a Linear weight differs: {k}'
        D = (b.double() - a.double())
        r = min(rank, D.shape[0], D.shape[1])
        U, S, Vh = torch.linalg.svd(D, full_matrices=False)
        B, A = U[:, :r] * S[:r], Vh[:r]
        err = (B @ A - D).abs().max().item()
        assert err < RECON_TOL, f'{k}: rank-{r} reconstruction error {err}'
        out[k] = (B.float().contiguous(), A.float().contiguous())
        rep['changed'] += 1
        rep['numbers'] += r * (D.shape[0] + D.shape[1])
        rep['max_err'] = max(rep['max_err'], err)
    return (out, rep) if with_report else out


def _batch(m, chunk):
    ds = Dataset([{'id': f'g{i}', 'prompt': p, 'answer': '', 'accepted': [], 'family': '', 'level': 0}
                  for i, p in enumerate(chunk)], m.vocab, strict=False)
    return to_device(collate([ds[i] for i in range(len(chunk))]), 'cpu')


def workspace_features(m, prompts, bs=64, loops=None):
    """The parent's greedy pass exactly as domain.mode.greedy does it, with the workspace captured after the last round.
    -> (features float32 [N, 2048] = Z[:, :8].flatten(1), [(calls, answer)]).
    loops=k (M3-1): only k rounds are run (m.run(batch, loops=k)); the features are Z[:, :8] after round k and there are no
    glance answers (the second item is None)."""
    m.eval()
    feats, res = [], []
    for s in range(0, len(prompts), bs):
        chunk = prompts[s:s + bs]
        batch = _batch(m, chunk)
        last = {}

        def each(t, state):
            last['Z'] = state['Z']
            return False
        with torch.no_grad():
            if loops is not None:
                m.run(batch, loops=loops, each=each)
                feats.append(last['Z'][:, :N_CTRL].flatten(1).float().clone())
                continue
            o = m.run(batch, each=each)
            ans = m.talk(m.state_of(o), batch)
        feats.append(last['Z'][:, :N_CTRL].flatten(1).float().clone())
        res += [([(op, a, b, r) for (t, op, a, b, r) in o['calls'][i]], ans[i]) for i in range(len(chunk))]
    return torch.cat(feats), (res if loops is None else None)


def reader_features(m, prompts):
    """Arm R: the existing switch's features (mean of the reader's output over the letters)."""
    return _route.features(m, prompts).float()


def both_features(m, prompts, bs=64, loops=None):
    """Arm TR: reader mean (256) then workspace (2,048) side by side. -> (float32 [N, 2304], [(calls, answer)] from the glance pass;
    None when loops is set)."""
    Xw, glance = workspace_features(m, prompts, bs, loops)
    return torch.cat([reader_features(m, prompts), Xw], 1), glance


def fit_router(X, y, n_classes=6, kind='workspace', feats='workspace', epochs=400, lr=0.01, l2=1e-4, seed=0, classes=None, look_loops=None):
    """n_classes-way softmax on standardised features (default 6; classes, if given, names the classes and sets n_classes);
    every class's rows share total weight 1/n_classes.
    feats records which features the router reads: 'workspace', 'reader' or 'reader+workspace'."""
    if classes is not None:
        n_classes = len(classes)
    assert feats in ('workspace', 'reader', 'reader+workspace'), feats
    X = X.float()
    y = torch.as_tensor(y, dtype=torch.long)
    g = torch.Generator().manual_seed(seed)
    mu, sd = X.mean(0), X.std(0).clamp(min=1e-6)
    Z = (X - mu) / sd
    W = (torch.randn(n_classes, Z.shape[1], generator=g) * 0.01).requires_grad_(True)
    b = torch.zeros(n_classes, requires_grad=True)
    cnt = torch.bincount(y, minlength=n_classes).float()
    cw = (1.0 / (n_classes * cnt.clamp(min=1)))[y]
    opt = torch.optim.Adam([W, b], lr=lr)
    for _ in range(epochs):
        loss = (torch.nn.functional.cross_entropy(Z @ W.T + b, y, reduction='none') * cw).sum() + l2 * (W * W).sum()
        opt.zero_grad()
        loss.backward()
        opt.step()
    with torch.no_grad():
        acc = ((Z @ W.T + b).argmax(1) == y).float().mean().item()
    return dict(mu=mu, sd=sd, W=W.detach(), b=b.detach(), classes=list(classes) if classes is not None else (list(CLASSES[:n_classes]) if n_classes <= 6 else list(range(n_classes))),
                kind=kind, feats=feats, look_loops=look_loops, train_acc=acc, n_train=int(len(y)), class_counts=[int(c) for c in cnt])


def route(router, X):
    """Class index per row (0 = none): argmax of the standardised logits."""
    with torch.no_grad():
        return ((X.float() - router['mu']) / router['sd'] @ router['W'].T + router['b']).argmax(1)


class Shelf:
    def __init__(self, ck, pieces, router):
        """ck: the parent's checkpoint dict (model, name, cfg, chars, step). pieces: list of {name: (B, A)}, piece k-1 = class k of the router (SUBJECTS order by default)."""
        self.ck, self.pieces, self.router = ck, pieces, router
        self.m = build(ck['name'], CharVocab(ck['chars']), **ck['cfg'])
        self.m.load_state_dict(ck['model'])
        self.m.eval()

    def numbers(self):
        n_par = sum(p.numel() for p in self.m.parameters())
        n_pieces = sum(B.numel() + A.numel() for pc in self.pieces for B, A in pc.values())
        n_router = sum(self.router[k].numel() for k in ('mu', 'sd', 'W', 'b'))
        return dict(parent=n_par, pieces=n_pieces, router=n_router, total=n_par + n_pieces + n_router)

    def save(self, path):
        torch.save(dict(self.ck, shelf_pieces=self.pieces, shelf_router=self.router), path)

    @classmethod
    def load(cls, path):
        ck = torch.load(path, map_location='cpu')
        pieces, router = ck.pop('shelf_pieces'), ck.pop('shelf_router')
        return cls(ck, pieces, router)

    @contextlib.contextmanager
    def use(self, k):
        """Piece k on (k = 1..len(pieces), the router's class index; 0 = nothing): adds B @ A into each Linear weight in place, restores exactly."""
        if k == 0:
            yield self.m
            return
        params = dict(self.m.named_parameters())
        piece = self.pieces[k - 1]
        saved = {n: params[n].detach().clone() for n in piece}
        try:
            with torch.no_grad():
                for n, (B, A) in piece.items():
                    params[n].add_(B @ A)
            yield self.m
        finally:
            with torch.no_grad():
                for n, v in saved.items():
                    params[n].copy_(v)
            assert all(torch.equal(params[n].detach(), v) for n, v in saved.items()), 'restore was not bit-identical'

    def answer(self, prompts, bs=64, features=None):
        """-> (answers in input order, route per prompt). Glance pass -> workspace -> route -> greedy with the piece on."""
        from domain.mode import greedy
        ll = self.router.get('look_loops')              # missing key / None = the whole parent pass
        if features is not None:
            X, glance = features
        else:
            feats = self.router.get('feats', 'workspace')
            if feats == 'reader+workspace':
                X, glance = both_features(self.m, prompts, bs) if ll is None else both_features(self.m, prompts, bs, ll)
            else:
                X, glance = workspace_features(self.m, prompts, bs) if ll is None else workspace_features(self.m, prompts, bs, ll)
                if feats == 'reader':
                    X = reader_features(self.m, prompts)
        r = route(self.router, X).tolist()
        if glance is None:                              # one-round look: "none" answers are the parent's full greedy pass
            ix0 = [i for i, c in enumerate(r) if c == 0]
            ans = [None] * len(prompts)
            for i, (_, a) in zip(ix0, greedy(self.m, [prompts[i] for i in ix0], bs) if ix0 else []):
                ans[i] = a
        else:
            ans = [g[1] for g in glance]
        for k in range(1, len(self.pieces) + 1):
            ix = [i for i, c in enumerate(r) if c == k]
            if not ix:
                continue
            with self.use(k) as m:
                for i, (_, a) in zip(ix, greedy(m, [prompts[i] for i in ix], bs)):
                    ans[i] = a
        return ans, r
