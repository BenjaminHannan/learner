#!/usr/bin/env python3
"""Episode-local learned scratch cards for the small recurrent puzzle net.

The shared recurrent core writes and reads soft-addressed latent cards. No card
survives a model call, and no solver or puzzle-specific rule is used at inference.
"""
from __future__ import annotations

import math

import torch
from torch import nn
import torch.nn.functional as F


class CardScratchpad(nn.Module):
    def __init__(self, d: int, slots: int = 8, rank: int = 16):
        super().__init__()
        self.slots, self.rank = slots, rank
        self.wq = nn.Linear(d, rank, bias=False)
        self.wk = nn.Linear(d, rank, bias=False)
        self.wv = nn.Linear(d, rank, bias=False)
        self.read_gate = nn.Linear(d, 1)
        self.write_gate = nn.Linear(d, 1)
        self.addresses = nn.Parameter(torch.empty(slots, rank))
        nn.init.normal_(self.addresses, std=rank ** -0.5)

    def initial_state(self, batch: int, tokens: int, ref: torch.Tensor):
        keys = ref.new_zeros(batch, self.slots, self.rank)
        values = ref.new_zeros(batch, self.slots, tokens, self.rank)
        return keys, values

    def step(self, core, h, e, dr, dc, state, wipe_cards: bool = False):
        keys, values = state
        if wipe_cards:
            keys = torch.zeros_like(keys)
            values = torch.zeros_like(values)
        pooled = h.mean(dim=1)
        addresses = keys + self.addresses.unsqueeze(0)
        query = self.wq(pooled)
        read_weights = torch.softmax(torch.einsum("br,bsr->bs", query, addresses) /
                                     math.sqrt(self.rank), dim=1)
        recalled = torch.einsum("bs,bstr->btr", read_weights, values)
        # F.linear uses [out,in] weights. wv.weight.T is the tied biasless decoder.
        decoded = F.linear(recalled, self.wv.weight.T)
        read_gate = torch.sigmoid(self.read_gate(pooled)).unsqueeze(1)
        h_next = core.step(h + read_gate * decoded, e, dr, dc)

        after = h_next.mean(dim=1)
        key = self.wk(after)
        write_weights = torch.softmax(torch.einsum("br,bsr->bs", key, addresses) /
                                      math.sqrt(self.rank), dim=1)
        write_mass = torch.sigmoid(self.write_gate(after)) * write_weights
        payload = self.wv(h_next)
        keys = keys * (1 - write_mass.unsqueeze(-1)) + write_mass.unsqueeze(-1) * key.unsqueeze(1)
        values = (values * (1 - write_mass[:, :, None, None]) +
                  write_mass[:, :, None, None] * payload[:, None, :, :])
        return h_next, (keys, values)


def extra_weights(d: int, slots: int = 8, rank: int = 16):
    return 3 * d * rank + 2 * (d + 1) + slots * rank
