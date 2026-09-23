#!/usr/bin/env python3
"""Experiment 43J: 43I, but the two hand-given parity facts are removed.

43I told every answer place t two facts: "t is odd" and "t is the last place of an
odd-length input".  Here nobody tells it.  Instead the model owns two tiny learned
counters, shared by all six skills:
    forward counter   starts at the first place and steps right   f[t] = f[t-1] @ Mf
    backward counter  starts at the last place and steps left     b[t] = b[t+1] @ Mb
Each counter has K soft states, a learned starting state and a learned K x K step rule
(softmax rows).  There are N_COUNTERS counters per direction, each starting from different
random weights.  The score table of 43I is indexed by counter state instead of by the given
parity case, and the contributions of all counters are ADDED.
A counter that learns "flip every step" IS odd/even; one that learns "A once, then B
forever" IS "am I the last place".  Both work at any length.
Still given by hand: the four distance clues, the wired-in output length, K itself.
One change from 43I: parity facts given -> learned counters (small random start, so
seeds now differ in their starting weights too).  Imports 43G/43I read-only.
"""

from __future__ import annotations

import os

import torch
from torch import Tensor, nn

import fable_transport43g as T
import fable_learnedaddr43i as L

K = int(os.environ.get("FABLE43J_K", "2"))            # states per counter
N_COUNTERS = int(os.environ.get("FABLE43J_C", "4"))   # counters per direction (each starts from different random weights)
DROP = float(os.environ.get("FABLE43J_DROP", "0"))    # arm "drop": in training each distance clue is hidden with this chance per batch
HARD = os.environ.get("FABLE43J_HARD", "0") == "1"    # test-time only: harden counter steps and reads


class LearnedParity(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.table = nn.Parameter(torch.zeros(len(T.OPS), 2 * N_COUNTERS * K, 4, L.BUCKETS))  # [skill, counter state, clue, bucket]
        self.digit_logits = nn.Parameter(torch.zeros(len(T.OPS), 10, 10))
        self.start = nn.Parameter(torch.randn(2 * N_COUNTERS, K))                  # first half forward, second half backward
        self.step = nn.Parameter(torch.randn(2 * N_COUNTERS, K, K))                # [counter, from, to]

    def _sharp(self, logits: Tensor) -> Tensor:
        p = logits.softmax(-1)
        return nn.functional.one_hot(p.argmax(-1), p.shape[-1]).float() if HARD else p

    def cases(self, n: int) -> Tensor:                                               # [n, 2*N_COUNTERS*K]
        s, step, tape = self._sharp(self.start), self._sharp(self.step), []
        for _ in range(n):
            tape.append(s)
            s = torch.einsum("ck,ckj->cj", s, step)
        tape = torch.stack(tape)                                                     # [n, counter, state]
        tape = torch.cat((tape[:, :N_COUNTERS], tape[:, N_COUNTERS:].flip(0)), dim=1)
        return tape.flatten(1)

    def address(self) -> Tensor:                                                     # for the report only
        return self.table.flatten(2).softmax(-1)

    def matrices(self, n: int) -> tuple[Tensor, Tensor]:
        rows = torch.einsum("nc,sckb->snkb", self.cases(n), self.table)             # [skill, n, clue, bucket]
        c = L.clues(n)
        keep = (torch.rand(len(T.OPS), 4) >= DROP).float() if DROP and torch.is_grad_enabled() else torch.ones(len(T.OPS), 4)
        score = sum(keep[:, k, None, None] * rows[:, :, k, :].gather(2, c[k][None].expand(len(T.OPS), -1, -1))
                    for k in range(4))
        a = score.softmax(-1)
        if HARD:
            a = nn.functional.one_hot(a.argmax(-1), n).float()
        return a, self.digit_logits.softmax(-1)

    def forward(self, x: Tensor, ops: Tensor) -> Tensor:
        a, d = self.matrices(x.shape[1])
        return a[ops] @ x @ d[ops]


T.Transport = LearnedParity

if __name__ == "__main__":
    T.main()
