#!/usr/bin/env python3
"""rsn-353 runner: exactly rsn-296's runner (varied generator, loop arm 2x1024, steps, batches, lr,
reward, fact-check, seeds, eval), with ONE change: the loop's per-pass step embedding is no longer
added to the state (LoopThinker.forward without `+ self.step.weight[t]`). The parameter still exists
(unused), so checkpoints keep the same keys.

Why: CPU diagnosis artifacts/claude-loopdiag-20260925/DIAG.md. At width 256, 3 seeds, the loop without
the step embedding trained like the plain net (copy ce 0.52/0.54 vs plain 0.47), while the loop as built
stayed at 1.10/1.30.

  python claude_rsn353_run.py train --arm loop --seed 1 --out DIR
  python claude_rsn353_run.py dev|eval ...   (same arguments as claude_rsn294_run.py)
"""
import runpy
import sys
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_rsn294_core as C  # noqa: E402
import claude_rsn296_gen  # noqa: E402,F401  (replaces claude_rsn294_core.gen_episode, as in 296)


def forward353(self, e, steps: int = 6):
    x0, m = self.emb(e)
    x = x0
    for t in range(steps):
        x = self.inject(torch.cat([x, x0], -1))          # the one change: no step embedding
        for L in self.block:
            x = L(x, src_key_padding_mask=~m)
    return self.heads(x, e)


C.LoopThinker.forward = forward353

if __name__ == "__main__":
    runpy.run_path(str(HERE / "claude_rsn294_run.py"), run_name="__main__")
