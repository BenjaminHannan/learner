#!/usr/bin/env python3
"""Experiment 43K-v2: 43K with ONE change — a balanced start for the counters.

43K failed only on seed 4111, where by chance none of the 8 randomly started counters leaned toward
"change state every step", so odd/even was never found.  Here the start is no longer left to chance:
in each direction counters 0,1 start leaning "change state" and counters 2,3 start leaning "stay"
(+/-2 on the matching step-rule entries, plus the same small random jitter as before, scaled by 0.5).
Everything is still learned from there; no counter is told which skill needs it, or that odd/even matters.
"""

from __future__ import annotations

import torch
from torch import nn

import fable_widelengths43k as K43                    # installs wide-length data + 43J model
import fable_learnedparity43j as J
import fable_transport43g as T

LEAN = 2.0


class BalancedStart(J.LearnedParity):
    def __init__(self) -> None:
        super().__init__()
        assert J.K == 2 and J.N_COUNTERS % 2 == 0
        eye = torch.eye(2)
        sign = torch.tensor([-1.0 if (c % J.N_COUNTERS) < J.N_COUNTERS // 2 else 1.0 for c in range(2 * J.N_COUNTERS)])
        with torch.no_grad():
            self.step.copy_(0.5 * self.step + LEAN * sign[:, None, None] * (2 * eye - 1))


T.Transport = BalancedStart

if __name__ == "__main__":
    T.main()
