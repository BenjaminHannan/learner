"""Chained-call variant of model.py: up to two calculator calls; second call may point at the first call's result slot."""
import math
import torch
from torch import nn
from torch.nn import functional as F
from model import Block, UpcycledMLP, CLIP, D, LOOPS, LO, HI


class Reasoner2(nn.Module):
    NL, NS = 3, 2  # literal candidates, result-slot candidates
    def __init__(self, lm_width):
        super().__init__()
        self.reader = nn.Sequential(nn.LayerNorm(lm_width), nn.Linear(lm_width, 32), nn.GELU(), nn.Linear(32, D))
        self.blocks = nn.ModuleList(Block(D, 8) for _ in range(2))
        for b in self.blocks:
            b.mlp = UpcycledMLP(b.mlp, D, 8, 2)
        self.ln_state = nn.LayerNorm(D)
        self.action = nn.Linear(D, 3)
        self.left = nn.Parameter(torch.empty(D, D)); self.right = nn.Parameter(torch.empty(D, D))
        nn.init.xavier_uniform_(self.left); nn.init.xavier_uniform_(self.right)
        self.status = nn.Embedding(4, D); nn.init.zeros_(self.status.weight)
        self.role_value = nn.Parameter(torch.zeros(D)); self.role_status = nn.Parameter(torch.zeros(D))
        self.out_map = nn.Sequential(nn.Linear(D, 32), nn.GELU(), nn.Linear(32, lm_width))

    def aux(self):
        return torch.stack([b.mlp.aux for b in self.blocks]).mean()

    def step(self, h, e, dr, dc, key_ok):
        z = h + e
        for b in self.blocks:
            z = b(z, dr, dc, key_ok)
        return self.ln_state(z)

    def forward(self, feats, qmask, lit_idx, lit_ok, lit_vals, embed_numbers, gold=None):
        """lit_idx/lit_ok/lit_vals [B,3]. gold (train): action [B,LOOPS], left [B,LOOPS], right [B,LOOPS] indices into the 5 candidates
        (0-2 literals, 3-4 result slots of loops 0-1). Returns prefix [B,8,LM], log with per-loop logits and calls, and final copy result."""
        B, T, _ = feats.shape
        dev = feats.device
        q = self.reader(feats.float()) * qmask[..., None]
        NS = 2 * LOOPS; n = T + NS
        r = torch.arange(T, device=dev)
        dc = torch.full((n, n), CLIP, device=dev, dtype=torch.long)
        dc[:T, :T] = (r[:, None] - r[None, :]).clamp(-CLIP, CLIP) + CLIP
        dr = torch.full((n, n), CLIP, device=dev, dtype=torch.long)
        key_ok = torch.cat([qmask, torch.ones(B, NS, dtype=torch.bool, device=dev)], 1)
        values = [self.role_value.expand(B, D) for _ in range(LOOPS)]
        stats = [self.role_status.expand(B, D) + self.status.weight[0] for _ in range(LOOPS)]
        h = torch.zeros(B, n, D, device=dev, dtype=q.dtype)
        ar = torch.arange(B, device=dev)
        m = qmask[..., None].to(q.dtype)
        log = {"act": [], "left": [], "right": [], "calls": []}
        slot_vals = torch.zeros(B, self.NS, dtype=torch.long, device=dev)
        slot_ok = torch.zeros(B, self.NS, dtype=torch.bool, device=dev)
        final_res = torch.zeros(B, dtype=torch.long, device=dev); final_ok = torch.zeros(B, dtype=torch.bool, device=dev)
        for loop in range(LOOPS):
            e = torch.cat([q, torch.stack(values, 1), torch.stack(stats, 1)], 1)
            hf = h + e
            f = hf[:, :T]
            qm = (f * m).sum(1) / m.sum(1)
            act_logits = self.action(qm)
            refs = [f[ar, lit_idx[:, j]] for j in range(self.NL)] + [hf[:, T + k] for k in range(self.NS)]
            ref = torch.stack(refs, 1)
            cand_ok = torch.cat([lit_ok, slot_ok], 1)
            cand_vals = torch.cat([lit_vals, slot_vals], 1)
            ll = (torch.einsum("bd,df,blf->bl", qm, self.left, ref) / math.sqrt(D)).masked_fill(~cand_ok, -1e4)
            rl = (torch.einsum("bd,df,blf->bl", qm, self.right, ref) / math.sqrt(D)).masked_fill(~cand_ok, -1e4)
            log["act"].append(act_logits); log["left"].append(ll); log["right"].append(rl)
            if gold is not None:
                act, li, ri = gold["action"][:, loop], gold["left"][:, loop], gold["right"][:, loop]
            else:
                act, li, ri = act_logits.argmax(-1), ll.argmax(-1), rl.argmax(-1)
            a, b = cand_vals[ar, li], cand_vals[ar, ri]
            res = torch.where(act == 1, a + b, torch.where(act == 2, a - b, torch.zeros_like(a)))
            ok = (act != 0) & (res >= LO) & (res <= HI) & cand_ok[ar, li] & cand_ok[ar, ri]
            status = torch.where(act == 0, 1, torch.where(ok, 2, 3))
            log["calls"].append((act, li, ri, res, ok))
            if loop < self.NS:
                slot_vals = slot_vals.clone(); slot_ok = slot_ok.clone()
                slot_vals[:, loop] = torch.where(ok, res, torch.zeros_like(res)); slot_ok[:, loop] = ok
            final_res = torch.where(ok, res, final_res); final_ok = final_ok | ok
            if bool(ok.any()):
                values[loop] = values[loop] + self.reader(embed_numbers(res.clamp(LO, HI)).float()) * ok[:, None]
            stats[loop] = self.role_status + self.status(status)
            e = torch.cat([q, torch.stack(values, 1), torch.stack(stats, 1)], 1)
            h = self.step(h, e, dr, dc, key_ok)
        hq = self.out_map(h[:, :T]) * qmask[..., None]
        lens = qmask.sum(1)
        prefix = torch.stack([F.adaptive_avg_pool1d(hq[b_, :lens[b_]].T[None], 8)[0].T for b_ in range(B)], 0)
        return prefix, log, final_res, final_ok
