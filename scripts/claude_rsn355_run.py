#!/usr/bin/env python3
"""rsn-355 runner: exactly rsn-296's runner (varied generator, plain arm 6x640, steps, batches, lr,
reward, fact-check, seeds, eval), with ONE change: the steps of the question's chain no longer get one
separate input slot each. Every chain step gets the same learned "chain step" vector, the first step
also gets a "first step" vector, and every later step gets a learned link from the relation of the step
before it. So step 3 is built from the same trained parts as step 2.

Why: sleep research round 2 (design/v3/30-modes/sleep-research-round2-2026-09-25.md). In 294/296 each
step has its own slot (Embed.slot rows 1+MAX_WHO+i). No practice kind ever has 3 steps (value3 is
dev/panel only), so the third slot kept its random starting value in every checkpoint, and three-step
questions were 0/30 by construction.

The old slot rows stay in the table (unused for chain steps), so all other keys are unchanged.

  python claude_rsn355_run.py train --arm plain --seed 1 --out DIR
  python claude_rsn355_run.py dev|eval ...   (same arguments as claude_rsn294_run.py)
"""
import runpy
import sys
from pathlib import Path

import torch
import torch.nn as nn

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_rsn294_core as C  # noqa: E402
import claude_rsn296_gen  # noqa: E402,F401  (replaces claude_rsn294_core.gen_episode, as in 296)

_embed_init = C.Embed.__init__


def init355(self, d: int):
    _embed_init(self, d)
    self.hop = nn.Parameter(torch.randn(d))          # shared "chain step" role (same scale as a slot)
    self.hop_first = nn.Parameter(torch.randn(d))    # marks the first step
    self.hop_prev = nn.Linear(d, d, bias=False)      # link from the previous step's relation


def forward355(self, e):
    B, R = e.subj.shape
    ids = torch.arange(4 + C.MAX_WHO + C.MAX_HOPS, device=e.subj.device)
    S = self.slot(ids)
    head = [self.kind(e.kind) + self.dirn(e.dirn) + S[0]]
    for i in range(C.MAX_WHO):
        head.append(self.subj_p(self.sym(e.who[:, i])) + S[1 + i])
    for i in range(C.MAX_HOPS):                      # the one change: shared step role + link
        link = self.hop_first if i == 0 else self.hop_prev(self.rel(e.frels[:, i - 1]))
        head.append(self.rel(e.frels[:, i]) + self.hop + link)
    head.append(self.val_p(self.sym(e.fval)) + self.fnum(e.fnum) + S[1 + C.MAX_WHO + C.MAX_HOPS])
    h = torch.stack(head, 1)
    rows = (self.subj_p(self.sym(e.subj)) + self.rel(e.rel) + self.val_p(self.sym(e.val))
            + self.num(e.num) + S[-1])
    x = torch.cat([h, rows], 1)
    hm = torch.cat([(e.who != 0), (e.frels != 0)], 1)
    m = torch.cat([torch.ones(B, 1, dtype=torch.bool, device=x.device), hm,
                   torch.ones(B, 1, dtype=torch.bool, device=x.device), e.mask], 1)
    return x, m


C.Embed.__init__ = init355
C.Embed.forward = forward355

if __name__ == "__main__":
    runpy.run_path(str(HERE / "claude_rsn294_run.py"), run_name="__main__")
