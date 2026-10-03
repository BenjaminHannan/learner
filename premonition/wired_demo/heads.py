"""Action heads on the 8 registers: structured, argmax-decodable actions.

reg0 -> kind and arith op; reg1 -> ptr_a; reg2 -> ptr_b; reg3 -> slot; reg4 -> span start; reg5 -> span end;
regs 6-7 are free. claims: plumbing only; toy data; not an eval.
"""
from __future__ import annotations

from dataclasses import dataclass
import torch
from torch import nn
from .workspace import WIDTH

KINDS = ["CALC", "NOTE_WRITE", "ANSWER", "DONE"]
OPS = ["ADD", "SUB", "MUL", "DIV"]
NEG = -1e9


@dataclass
class ActionLogits:
    kind: torch.Tensor    # [B,4]
    arith: torch.Tensor   # [B,4]
    ptr_a: torch.Tensor   # [B,C]
    ptr_b: torch.Tensor   # [B,C]
    slot: torch.Tensor    # [B,S+1]  last = NEW
    start: torch.Tensor   # [B,Tq]
    end: torch.Tensor     # [B,Tq]


class ActionHeads(nn.Module):
    def __init__(self, d=WIDTH, key=64):
        super().__init__()
        self.kind, self.arith = nn.Linear(d, len(KINDS)), nn.Linear(d, len(OPS))
        self.q = nn.ModuleDict({f: nn.Linear(d, key) for f in ("ptr_a", "ptr_b", "slot", "start", "end")})
        self.k_reg, self.k_slot, self.k_span = nn.Linear(d, key), nn.Linear(d, key), nn.Linear(d, key)
        self.new_slot = nn.Parameter(torch.randn(d) * 0.02)
        self.key = key

    def _score(self, name, reg, cand, present):
        s = torch.einsum("bk,bck->bc", self.q[name](reg), cand) / self.key ** 0.5
        return s.masked_fill(~present, NEG)

    def forward(self, tokens, registers, reg_pool, reg_present, slot_pool, slot_present, span_ok):
        """tokens [B,N,256]; registers [B,8,256]; reg_pool [B,C,N] / slot_pool [B,S,N] mean-pool weights over rows;
        *_present bool masks; span_ok bool [B,N] = question rows (spans may only point into the question)."""
        reg_c = self.k_reg(torch.bmm(reg_pool, tokens))
        slot_c = self.k_slot(torch.cat([torch.bmm(slot_pool, tokens),
                                        self.new_slot.expand(tokens.shape[0], 1, -1)], 1))
        slot_ok = torch.cat([slot_present, torch.ones_like(slot_present[:, :1])], 1)
        span_c = self.k_span(tokens)
        return ActionLogits(
            kind=self.kind(registers[:, 0]), arith=self.arith(registers[:, 0]),
            ptr_a=self._score("ptr_a", registers[:, 1], reg_c, reg_present),
            ptr_b=self._score("ptr_b", registers[:, 2], reg_c, reg_present),
            slot=self._score("slot", registers[:, 3], slot_c, slot_ok),
            start=self._score("start", registers[:, 4], span_c, span_ok),
            end=self._score("end", registers[:, 5], span_c, span_ok))
