#!/usr/bin/env python3
"""Experiment 43I (step 1): callable skills + router, but the model must LEARN where to look.

43G/43H gave the model six ready-made places to read.  Here that list is removed.
For answer place t the model may read ANY of the n input places j.  Its only clues are
four length-proof distances between "me" (t) and "you" (j):
    d1 = j - t                 you relative to me
    d2 = j - (n-1-t)           you relative to my mirror image
    d3 = 2j - t                you at double scale, from the start   (halving)
    d4 = 2(n-1-j) - t          you at double scale, from the end
each clipped to -4..+4 (anything further shares the edge bucket).  Per skill and parity
case the model learns a score table [4 clues, 9 buckets]; the score of place j is the sum
of its four table entries; a softmax over all n places gives the read weights.
Still given by hand (unchanged from 43G): the two parity facts about t, the wired-in
output length, and the digit table form.  One change from 43G-v2: the address rule.
Imports 43G read-only and reuses its training, evaluation and router-sleep code.
"""

from __future__ import annotations

import torch
from torch import Tensor, nn

import fable_transport43g as T

CLIP = 4
BUCKETS = 2 * CLIP + 1


def clues(n: int) -> Tensor:
    t = torch.arange(n)[:, None]
    j = torch.arange(n)[None, :]
    d = torch.stack((j - t, j - (n - 1 - t), 2 * j - t, 2 * (n - 1 - j) - t))      # [4, n, n]
    return d.clamp(-CLIP, CLIP) + CLIP


class LearnedAddress(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.table = nn.Parameter(torch.zeros(len(T.OPS), 4, 4, BUCKETS))          # [skill, parity case, clue, bucket]
        self.digit_logits = nn.Parameter(torch.zeros(len(T.OPS), 10, 10))

    def address(self) -> Tensor:                                                     # for the report only
        return self.table.flatten(2).softmax(-1)

    def matrices(self, n: int) -> tuple[Tensor, Tensor]:
        rows = self.table[:, T.bit_combo(n)]                                         # [skill, n, clue, bucket]
        c = clues(n)                                                                 # [clue, n, n]
        score = sum(rows[:, :, k, :].gather(2, c[k][None].expand(len(T.OPS), -1, -1)) for k in range(4))
        return score.softmax(-1), self.digit_logits.softmax(-1)                      # A [skill,n,n], D [skill,10,10]

    def forward(self, x: Tensor, ops: Tensor) -> Tensor:
        a, d = self.matrices(x.shape[1])
        return a[ops] @ x @ d[ops]


T.Transport = LearnedAddress

if __name__ == "__main__":
    T.main()
