"""Reimplementation of the contextual-reader + 9M looped core + calculator recipe (see README caveats).

Frozen LM (LFM2.5-1.2B-Instruct) -> contextual states -> reader (LN, 2048->32, GELU, 32->256) ->
4 loops of a shared 2-block width-256 core (MoE MLP, 8 experts top-2, router zero-init) with a calculator
call read from h+e at the top of each loop (reserved value/status notebook slots) -> question positions
mapped 256->32->LM width, adaptive-avg-pooled to 8 prefix vectors -> frozen LM reads BOS + 8 prefix.
Block / MoE code copied from scripts/claude_fewex_net.py and scripts/sol_spatial_attention_core.py.
"""
import copy, math
import torch
from torch import nn
from torch.nn import functional as F

CLIP, WINDOW, D, LOOPS = 4, 1, 256, 4
ACTIONS = ("NONE", "ADD", "SUB")
LO, HI = 10, 99


class Block(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.h = h
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.out = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.mlp = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d))
        self.br = nn.Parameter(torch.zeros(h, 2 * CLIP + 1))
        self.bc = nn.Parameter(torch.zeros(h, 2 * CLIP + 1))

    def forward(self, x, dr, dc, key_ok):
        B, T, Dm = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, Dm // self.h).permute(2, 0, 3, 1, 4)
        bias = self.br[:, dr] + self.bc[:, dc]
        far = (dc - CLIP).abs() > WINDOW
        narrow = torch.zeros(self.h, 1, 1, dtype=torch.bool, device=x.device)
        narrow[: self.h // 2] = True
        bias = bias.masked_fill(narrow & far, float("-inf")).unsqueeze(0)
        bias = bias.masked_fill(~key_ok[:, None, None, :], float("-inf")).to(q.dtype)
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=bias)
        x = x + self.out(a.transpose(1, 2).reshape(B, T, Dm))
        return x + self.mlp(self.ln2(x))


class UpcycledMLP(nn.Module):
    def __init__(self, mlp, width=256, experts=8, active=2):
        super().__init__()
        self.active = active
        self.experts = nn.ModuleList(copy.deepcopy(mlp) for _ in range(experts))
        self.router = nn.Linear(width, experts)
        nn.init.zeros_(self.router.weight); nn.init.zeros_(self.router.bias)
        self.aux = torch.zeros(())

    def forward(self, x):
        shape = x.shape; x = x.reshape(-1, shape[-1])
        logits = self.router(x).float()
        values, ids = logits.topk(self.active, -1)
        weights = values.softmax(-1).to(x.dtype)
        out = torch.zeros_like(x)
        for i, expert in enumerate(self.experts):
            positions, slots = torch.where(ids == i)
            if positions.numel():
                out = out.index_add(0, positions, expert(x[positions]) * weights[positions, slots, None])
        fraction = F.one_hot(ids, len(self.experts)).float().mean((0, 1)).detach()
        self.aux = .001 * len(self.experts) * (fraction * logits.softmax(-1).mean(0)).sum()
        return out.reshape(shape)


class Reasoner(nn.Module):
    def __init__(self, lm_width):
        super().__init__()
        self.reader = nn.Sequential(nn.LayerNorm(lm_width), nn.Linear(lm_width, 32), nn.GELU(), nn.Linear(32, D))
        self.blocks = nn.ModuleList(Block(D, 8) for _ in range(2))
        for b in self.blocks:
            b.mlp = UpcycledMLP(b.mlp, D, 8, 2)
        self.ln_state = nn.LayerNorm(D)
        # calculator path (CalculatorPath-style): action head, bilinear pointers, status/role slots
        self.action = nn.Linear(D, 3)
        self.left = nn.Parameter(torch.empty(D, D)); self.right = nn.Parameter(torch.empty(D, D))
        nn.init.xavier_uniform_(self.left); nn.init.xavier_uniform_(self.right)
        self.status = nn.Embedding(4, D); nn.init.zeros_(self.status.weight)  # PENDING NONE OK ERROR
        self.role_value = nn.Parameter(torch.zeros(D)); self.role_status = nn.Parameter(torch.zeros(D))
        self.out_map = nn.Sequential(nn.Linear(D, 32), nn.GELU(), nn.Linear(32, lm_width))
        self.aux_w = 1.0

    def aux(self):
        return torch.stack([b.mlp.aux for b in self.blocks]).mean()

    def step(self, h, e, dr, dc, key_ok):
        z = h + e
        for b in self.blocks:
            z = b(z, dr, dc, key_ok)
        return self.ln_state(z)

    def forward(self, feats, qmask, lit_idx, lit_ok, lit_vals, embed_numbers, gold=None):
        """feats [B,T,LM] frozen contextual states (right padded, last valid position is EOS); qmask [B,T] bool;
        lit_idx [B,L] positions of the number literals in text order; lit_ok [B,L]; lit_vals [B,L] their integers;
        embed_numbers(values[B] long) -> [B,LM] frozen LM embedding of that number's token.
        gold (training only): action [B] (1 ADD / 2 SUB), left [B], right [B] indices into the L literals; used as
        teacher forcing for the loop-0 call, later loops are teacher-forced to NONE.
        Returns prefix [B,8,LM] and a dict of call logits and the calls actually made."""
        B, T, _ = feats.shape
        dev = feats.device
        q = self.reader(feats.float()) * qmask[..., None]
        NS = 2 * LOOPS
        n = T + NS
        r = torch.arange(T, device=dev)
        dc = torch.full((n, n), CLIP, device=dev, dtype=torch.long)
        dc[:T, :T] = (r[:, None] - r[None, :]).clamp(-CLIP, CLIP) + CLIP
        dr = torch.full((n, n), CLIP, device=dev, dtype=torch.long)
        key_ok = torch.cat([qmask, torch.ones(B, NS, dtype=torch.bool, device=dev)], 1)
        values = [self.role_value.expand(B, D) for _ in range(LOOPS)]
        stats = [self.role_status.expand(B, D) + self.status.weight[0] for _ in range(LOOPS)]  # PENDING
        h = torch.zeros(B, n, D, device=dev, dtype=q.dtype)
        ar = torch.arange(B, device=dev)
        m = qmask[..., None].to(q.dtype)
        log = {"act": [], "left": None, "right": None, "calls": []}
        for loop in range(LOOPS):
            e = torch.cat([q, torch.stack(values, 1), torch.stack(stats, 1)], 1)
            f = (h + e)[:, :T]
            qm = (f * m).sum(1) / m.sum(1)
            act_logits = self.action(qm)
            ref = torch.stack([f[ar, lit_idx[:, j]] for j in range(lit_idx.shape[1])], 1)
            ll = (torch.einsum("bd,df,blf->bl", qm, self.left, ref) / math.sqrt(D)).masked_fill(~lit_ok, -1e4)
            rl = (torch.einsum("bd,df,blf->bl", qm, self.right, ref) / math.sqrt(D)).masked_fill(~lit_ok, -1e4)
            log["act"].append(act_logits)
            if loop == 0:
                log["left"], log["right"] = ll, rl
            if gold is not None:
                act = gold["action"] if loop == 0 else torch.zeros_like(gold["action"])
                li, ri = gold["left"], gold["right"]
            else:
                act, li, ri = act_logits.argmax(-1), ll.argmax(-1), rl.argmax(-1)
            a, b = lit_vals[ar, li], lit_vals[ar, ri]
            res = torch.where(act == 1, a + b, torch.where(act == 2, a - b, torch.zeros_like(a)))
            ok = (act != 0) & (res >= LO) & (res <= HI)
            status = torch.where(act == 0, 1, torch.where(ok, 2, 3))
            log["calls"].append((act, li, ri, res, ok))
            if bool(ok.any()):
                num = self.reader(embed_numbers(res.clamp(LO, HI)).float()) * ok[:, None]
                values[loop] = values[loop] + num
            stats[loop] = self.role_status + self.status(status)
            e = torch.cat([q, torch.stack(values, 1), torch.stack(stats, 1)], 1)
            h = self.step(h, e, dr, dc, key_ok)
        hq = self.out_map(h[:, :T]) * qmask[..., None]
        lens = qmask.sum(1)
        prefix = torch.stack([F.adaptive_avg_pool1d(hq[b_, :lens[b_]].T[None], 8)[0].T for b_ in range(B)], 0)
        return prefix, log
