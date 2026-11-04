"""Reference writers for calibrating the binding toy. Each is a KNOWN method.

- MeanPool: uniform mean of the line (tried in the project, FAIL on the ladder).
- TwoPool: separate softmax pools for key and value (Key-Value Memory Networks
  style; tried in the project, FAIL on the ladder).
- MultiHeadPool: several learned pooling queries (PMA / Set Transformer).
- OracleAddress: NOT a legal writer. It is handed the person and relation
  states by role (worker.py passes roles to trusted writers only), the analogue
  of the ladder's "address told" upper bound (choose 91-98%).
"""

import torch
import torch.nn as nn


def _pool(score, mask, states):
    w = torch.softmax(score.masked_fill(~mask, float("-inf")), dim=-1)
    return torch.einsum("bcl,bcld->bcd", w, states)


class MeanPool(nn.Module):
    def __init__(self, d, dk):
        super().__init__()
        self.key, self.value = nn.Linear(d, dk), nn.Linear(d, d)

    def forward(self, states, mask):
        p = _pool(torch.zeros(mask.shape), mask, states)
        return self.key(p), self.value(p)


class TwoPool(nn.Module):
    def __init__(self, d, dk):
        super().__init__()
        self.pk, self.pv = nn.Linear(d, 1), nn.Linear(d, 1)
        self.key, self.value = nn.Linear(d, dk), nn.Linear(d, d)

    def forward(self, states, mask):
        return (self.key(_pool(self.pk(states).squeeze(-1), mask, states)),
                self.value(_pool(self.pv(states).squeeze(-1), mask, states)))


class MultiHeadPool(nn.Module):
    def __init__(self, d, dk, heads=4):
        super().__init__()
        self.p = nn.Linear(d, heads)
        self.key, self.value = nn.Linear(heads * d, dk), nn.Linear(heads * d, d)

    def forward(self, states, mask):
        s = self.p(states).permute(0, 1, 3, 2)                   # [B,C,H,L]
        w = torch.softmax(s.masked_fill(~mask.unsqueeze(2), float("-inf")), dim=-1)
        p = torch.einsum("bchl,bcld->bchd", w, states).flatten(-2)
        return self.key(p), self.value(p)


ROLES = None  # set by worker.py for trusted runs: [B, C, L] roles for the current batch


class OracleAddress(nn.Module):
    """Key from the true person + relation states, value from the true value state."""

    def __init__(self, d, dk):
        super().__init__()
        self.key, self.value = nn.Linear(2 * d, dk), nn.Linear(d, d)

    def forward(self, states, mask):
        r = ROLES[: states.shape[0]]
        pick = lambda k: (states * (r == k).unsqueeze(-1)).sum(2)
        return self.key(torch.cat([pick(1), pick(2)], -1)), self.value(pick(3))
