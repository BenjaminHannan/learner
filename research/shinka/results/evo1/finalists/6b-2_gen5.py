"""Seed program: PremonitionMini's card writer (premonition/model.py CardWriter).

One softmax attention pool over the line's reader states gives p;
key = W_k p, value = W_v p. Key and value come from the same pooled vector.
(The harness normalises keys before scoring, as CardStore.write does.)
"""

import torch
import torch.nn as nn


# EVOLVE-BLOCK-START
class CardWriter(nn.Module):
    def __init__(self, d: int, dk: int):
        super().__init__()
        budget = 18500
        rounds = 1
        for t in (4, 3, 2, 1):
            n = t * (d + 1) + t * d * dk + dk + d * d + d + t + t * d
            if n <= budget:
                rounds = t
                break
        self.rounds = rounds
        self.d = d
        self.scorers = nn.ModuleList([nn.Linear(d, 1) for i in range(rounds)])
        self.key = nn.Linear(rounds * d, dk)
        self.value = nn.Linear(d, d)
        self.mix = nn.Parameter(torch.ones(rounds) / rounds)
        # per-round diagonal gain on atoms before key projection
        self.gain = nn.Parameter(torch.ones(rounds, d))

    def forward(self, states: torch.Tensor, mask: torch.Tensor):
        resid = states
        maskf = mask.unsqueeze(-1).to(states.dtype)
        atoms = []
        vsum = 0.0
        for t in range(self.rounds):
            score = self.scorers[t](resid).squeeze(-1)
            score = score.masked_fill(~mask, float("-inf"))
            w = torch.softmax(score, dim=-1)
            w = torch.nan_to_num(w, nan=0.0)
            atom = torch.einsum("bcl,bcld->bcd", w, resid)
            orig = torch.einsum("bcl,bcld->bcd", w, states)
            vsum = vsum + self.mix[t] * orig
            atoms.append(atom * self.gain[t])
            # deflate: remove atom direction from all residual token states
            u = atom / (atom.norm(dim=-1, keepdim=True) + 1e-6)
            proj = torch.einsum("bcld,bcd->bcl", resid, u)
            resid = (resid - proj.unsqueeze(-1) * u.unsqueeze(-2)) * maskf
        keys = self.key(torch.cat(atoms, dim=-1))
        values = self.value(vsum)
        return keys, values
# EVOLVE-BLOCK-END
