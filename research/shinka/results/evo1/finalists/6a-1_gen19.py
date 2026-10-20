"""Seed program: PremonitionMini's card writer (premonition/model.py CardWriter).

One softmax attention pool over the line's reader states gives p;
key = W_k p, value = W_v p. Key and value come from the same pooled vector.
(The harness normalises keys before scoring, as CardStore.write does.)
"""

import torch
import torch.nn as nn


# EVOLVE-BLOCK-START
def make_iso(d, dk, a, b, c):
    i = torch.arange(d, dtype=torch.float32).unsqueeze(1)
    j = torch.arange(dk, dtype=torch.float32).unsqueeze(0)
    M = torch.sin(i * a + j * b + i * j * c) + 0.5 * torch.cos(i * 2.413 - j * 1.127 + c)
    if d >= dk:
        Q, R = torch.linalg.qr(M)
        return Q.contiguous()
    Q, R = torch.linalg.qr(M.t())
    return Q.t().contiguous()


class CardWriter(nn.Module):
    def __init__(self, d: int, dk: int):
        super().__init__()
        K = 2
        S = 3
        r = max(2, min(8, d // 4))

        def count(K, S, r, mix):
            n = (K + 2 + S) * d * dk + dk          # key linear
            n += (K + 3) * (d + 1)                 # scorers (K pursuit, nov, dis, mass)
            n += d * r + 1                         # subspace + gain
            n += 4 + S + 2                         # gains, echoes, slot gains, scale
            n += S * d                             # slot prototypes
            n += (2 + S) * d * dk                  # frozen isometries
            n += d * d + d                         # value
            if mix:
                n += d * d
            return n

        while S > 1 and count(K, S, r, False) > 19000:
            S -= 1
        while K > 1 and count(K, S, r, False) > 19000:
            K -= 1
        while r > 1 and count(K, S, r, False) > 19000:
            r -= 1
        self.K = K
        self.S = S
        self.use_mix = count(K, S, r, True) <= 19000
        self.scorers = nn.ModuleList([nn.Linear(d, 1) for k in range(K)])
        self.nov_scorer = nn.Linear(d, 1)
        self.dis_scorer = nn.Linear(d, 1)
        self.mass_scorer = nn.Linear(d, 1)
        self.basis = nn.Parameter(torch.randn(d, r) / (d ** 0.5))
        self.gain = nn.Parameter(torch.tensor(4.0))
        self.dgain = nn.Parameter(torch.tensor(4.0))
        self.dgain2 = nn.Parameter(torch.tensor(2.0))
        self.mgain = nn.Parameter(torch.tensor(4.0))
        self.echo = nn.Parameter(torch.tensor(1.0))
        self.echo2 = nn.Parameter(torch.tensor(1.0))
        self.slot_gain = nn.Parameter(torch.full((S,), 0.7))
        self.scale = nn.Parameter(torch.tensor(5.0))
        self.protos = nn.Parameter(torch.randn(S, d) / (d ** 0.5))
        self.key = nn.Linear((K + 2 + S) * d, dk)
        self.value = nn.Linear(d, d)
        if self.use_mix:
            self.value2 = nn.Linear(d, d, bias=False)
        self.register_buffer("iso", make_iso(d, dk, 1.618, 0.737, 0.311))
        self.register_buffer("iso2", make_iso(d, dk, 0.917, 1.913, 0.173))
        isos = [make_iso(d, dk, 2.718 + 0.37 * s, 1.414 + 0.53 * s, 0.577 + 0.11 * s)
                for s in range(S)]
        self.register_buffer("isos", torch.stack(isos, 0))

    def forward(self, states: torch.Tensor, mask: torch.Tensor):
        dt = states.dtype
        m = mask.unsqueeze(-1).to(dt)
        x = states * m
        neg = torch.finfo(dt).min
        maskf = mask.to(dt)

        def unit(a):
            return a / a.norm(dim=-1, keepdim=True).clamp_min(1e-5)

        def pool(score, src):
            score = score.masked_fill(~mask, neg)
            w = torch.softmax(score, dim=-1) * maskf
            w = w / w.sum(-1, keepdim=True).clamp_min(1e-6)
            return torch.einsum("bcl,bcld->bcd", w, src), w

        # --- familiar evidence: deflation pursuit ---
        resid = x
        atoms = []
        for k in range(self.K):
            atom, wa = pool(self.scorers[k](resid).squeeze(-1), resid)
            atoms.append(atom)
            u = unit(atom)
            proj = (resid * u.unsqueeze(-2)).sum(-1, keepdim=True)
            resid = (resid - proj * u.unsqueeze(-2)) * m

        # --- global-subspace novelty ---
        Q, Rm = torch.linalg.qr(self.basis)
        out = x - (x @ Q) @ Q.t()
        frac = (out * out).sum(-1) / ((x * x).sum(-1) + 1e-6)
        nov, w_nov = pool(self.nov_scorer(x).squeeze(-1) + self.gain * frac, out)

        # --- intra-line distinctiveness ---
        cnt = maskf.sum(-1, keepdim=True).clamp_min(1.0)
        mean = x.sum(-2) / cnt
        xc = (x - mean.unsqueeze(-2)) * m
        xn = unit(x)
        G = xn @ xn.transpose(-1, -2)
        L = x.shape[-2]
        eye = torch.eye(L, dtype=dt, device=x.device)
        pair = maskf.unsqueeze(-1) * maskf.unsqueeze(-2) * (1.0 - eye)
        others = pair.sum(-1).clamp_min(1.0)
        meancos = (G * pair).sum(-1) / others
        Gm = G.masked_fill(pair <= 0, -4.0)
        smax = torch.clamp(torch.logsumexp(Gm * 6.0, dim=-1) / 6.0, max=1.0)
        dscore = (self.dis_scorer(x).squeeze(-1)
                  + self.dgain * (1.0 - meancos) + self.dgain2 * (1.0 - smax))
        dis, w_dis = pool(dscore, xc)

        wc = w_nov * w_dis * maskf
        wc = wc / wc.sum(-1, keepdim=True).clamp_min(1e-12)
        conj = torch.einsum("bcl,bcld->bcd", wc, x)

        # --- quota evidence: entropic transport tokens -> prototype slots ---
        S = self.S
        mscore = self.mass_scorer(x).squeeze(-1) + self.mgain * frac
        mscore = mscore.masked_fill(~mask, -1e4)
        loga = torch.log_softmax(mscore, dim=-1)
        loga = loga.masked_fill(~mask, -1e4)
        pn = unit(self.protos)
        logK = self.scale * (xn @ pn.t())                     # [B,C,L,S]
        logb = -torch.log(torch.tensor(float(S), dtype=dt, device=x.device))
        uu = torch.zeros_like(loga)
        vv = torch.zeros(logK.shape[:-2] + (S,), dtype=dt, device=x.device)
        for it in range(6):
            uu = loga - torch.logsumexp(logK + vv.unsqueeze(-2), dim=-1)
            vv = logb - torch.logsumexp(logK + uu.unsqueeze(-1), dim=-2)
        T = torch.exp(logK + uu.unsqueeze(-1) + vv.unsqueeze(-2)) * maskf.unsqueeze(-1)
        slots = torch.einsum("bcls,bcld->bcsd", T, x) * float(S)   # [B,C,S,d]
        slot_list = [slots[:, :, s, :] for s in range(S)]

        # --- key assembly ---
        feats = atoms + [nov, dis] + slot_list
        keys = self.key(torch.cat(feats, dim=-1))
        kn = keys.norm(dim=-1, keepdim=True).detach().clamp_min(1e-3)
        echo = self.echo * (unit(dis) @ self.iso) + self.echo2 * (unit(conj) @ self.iso2)
        su = unit(slots)                                          # [B,C,S,d]
        sec = torch.einsum("bcsd,sdk->bcsk", su, self.isos)
        echo = echo + (sec * self.slot_gain.view(1, 1, S, 1)).sum(-2)
        keys = keys + kn * echo

        # --- value ---
        total = atoms[0]
        for a in atoms[1:]:
            total = total + a
        values = self.value(total)
        if self.use_mix:
            values = values + self.value2(atoms[0])
        return keys, values
# EVOLVE-BLOCK-END