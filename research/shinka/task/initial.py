"""Seed program: PremonitionMini's card writer (premonition/model.py CardWriter).

One softmax attention pool over the line's reader states gives p;
key = W_k p, value = W_v p. Key and value come from the same pooled vector.
(The harness normalises keys before scoring, as CardStore.write does.)
"""

import torch
import torch.nn as nn


# EVOLVE-BLOCK-START
class CardWriter(nn.Module):
    """Turn one line's reader states into one card (key, value).

    states: [B, C, L, d] reader states of C lines of L tokens.
    mask:   [B, C, L] bool, True where a token is real.
    returns keys [B, C, dk], values [B, C, d].
    """

    def __init__(self, d: int, dk: int):
        super().__init__()
        self.pool = nn.Linear(d, 1)
        self.key = nn.Linear(d, dk)
        self.value = nn.Linear(d, d)

    def forward(self, states: torch.Tensor, mask: torch.Tensor):
        score = self.pool(states).squeeze(-1).masked_fill(~mask, float("-inf"))
        weight = torch.softmax(score, dim=-1)
        pooled = torch.einsum("bcl,bcld->bcd", weight, states)
        return self.key(pooled), self.value(pooled)
# EVOLVE-BLOCK-END
