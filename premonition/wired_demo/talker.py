"""PrefixAdapter + Talker: 8 registers -> 8 prefix vectors (1:1, no pooling) -> frozen LM text.

claims: plumbing only; toy data; not an eval.
"""
from __future__ import annotations

import torch
from torch import nn
import torch.nn.functional as F
from .workspace import WIDTH


class PrefixAdapter(nn.Module):
    def __init__(self, lm_width: int, registers: int = 8, hidden: int = 32):
        super().__init__()
        self.R = registers
        self.net = nn.Sequential(nn.Linear(WIDTH + registers, hidden), nn.GELU(), nn.Linear(hidden, lm_width))

    def forward(self, registers: torch.Tensor) -> torch.Tensor:
        b = registers.shape[0]
        onehot = torch.eye(self.R, device=registers.device).expand(b, -1, -1)
        return self.net(torch.cat([registers, onehot], -1))   # [B,8,D_lm]


class Talker:
    def __init__(self, lm, adapter: PrefixAdapter):
        self.lm, self.adapter = lm, adapter

    def loss(self, registers, target_ids):
        """target_ids [B,Tt] int64, -100 = pad, ending in <eos>. Layout [prefix ; bos, t1..] -> predict t1.."""
        prefix = self.adapter(registers)
        b, R = prefix.shape[:2]
        safe = target_ids.clamp(min=0)
        bos = torch.full((b, 1), self.lm.bos_id, dtype=torch.long)
        inp = torch.cat([bos, safe[:, :-1]], 1)
        ok = torch.cat([torch.ones(b, R, dtype=torch.bool), torch.ones(b, 1, dtype=torch.bool),
                        target_ids[:, :-1] != -100], 1)
        logits = self.lm.logits_from_embeds(torch.cat([prefix, self.lm.embed(inp)], 1), ok)
        logits = logits[:, R:]
        return F.cross_entropy(logits.reshape(-1, logits.shape[-1]), target_ids.reshape(-1), ignore_index=-100)

    @torch.no_grad()
    def generate(self, registers, max_tokens: int = 8):
        prefix = self.adapter(registers)
        b, R = prefix.shape[:2]
        ids = torch.full((b, 1), self.lm.bos_id, dtype=torch.long)
        done = torch.zeros(b, dtype=torch.bool)
        out = [[] for _ in range(b)]
        for _ in range(max_tokens):
            x = torch.cat([prefix, self.lm.embed(ids)], 1)
            nxt = self.lm.logits_from_embeds(x, torch.ones(x.shape[:2], dtype=torch.bool))[:, -1].argmax(-1)
            for i in range(b):
                if not done[i]:
                    if nxt[i].item() == self.lm.eos_id: done[i] = True
                    else: out[i].append(int(nxt[i]))
            if done.all(): break
            ids = torch.cat([ids, nxt[:, None]], 1)
        return out
