#!/usr/bin/env python3
"""Experiment 59: doc 57 section 3, implemented as a SINGLE change.

Imports the 43K-v2 rig (scripts/fable_widelengths43k_v2.py: wide-length data
4-12, EVAL_LENGTHS incl. 16/20/24/32/64, BalancedStart) and overrides ONLY the
counter step. Table, clues, loss, trainer, evaluation untouched.

Overridden function: `LearnedParity.cases()` from scripts/fable_learnedparity43j.py
(only this function; `address`, `matrices`, `forward`, `_sharp` inherited unchanged).

SIGNED arm (`SignedCounter`, new): per-counter start vector (K) + full KxK
softmax step (K^2) replaced by one signed scalar per counter:
    lam_c = tanh(w_c), x_0 = 1, x_t = lam_c^t,
    emitted as p_t = [(1+x_t)/2, (1-x_t)/2]  (same [n, 2*N*K] shape, K=2,
    same one-hot endpoints as the softmax rows, so the readout table is untouched).
lam=-1 is exactly the flip/odd-even counter; lam=+1 is exactly the stay counter.
Init: w_c ~ N(0,1) (plain torch.randn, the same RNG stream position as the old
start/step init would use is NOT preserved -- and must not be: no hand-balanced
start, symmetry broken only by the random sign of w_c).

CONTROL arm (`BalancedStart` from fable_widelengths43k_v2, unchanged, hand-balanced
start with LEAN=2.0): selected with FABLE59_ARM=control.

HARD=1 (test-time hardening, same flag as 43J): lam hardened to sign(lam)
(+1 when lam >= 0, else -1) before unrolling; table/readout hardening inherited.
"""

from __future__ import annotations

import os

import torch
from torch import Tensor

import fable_learnedparity43j as J
import fable_transport43g as T
import fable_widelengths43k_v2 as V2  # installs wide 4-12 data + EVAL_LENGTHS; T.Transport = BalancedStart


class SignedCounter(J.LearnedParity):
    def __init__(self) -> None:
        super().__init__()
        assert J.K == 2
        # Remove the softmax counter params; keep table + digit_logits untouched.
        del self.start
        del self.step
        self.w = torch.nn.Parameter(torch.randn(2 * J.N_COUNTERS))  # w_c ~ N(0,1)

    def lams(self) -> Tensor:
        lam = torch.tanh(self.w)
        if J.HARD:
            lam = torch.where(lam >= 0, torch.ones_like(lam), -torch.ones_like(lam))
        return lam

    def cases(self, n: int) -> Tensor:  # [n, 2*N_COUNTERS*K] -- THE override
        lam = self.lams()  # [2*N]
        t = torch.arange(n, dtype=self.w.dtype, device=self.w.device)
        x = lam[None, :] ** t[:, None]  # x_0 = 1 (lam**0 == 1); x_t = lam^t
        p = torch.stack(((1 + x) / 2, (1 - x) / 2), dim=-1)  # [n, counter, K=2]
        p = torch.cat((p[:, : J.N_COUNTERS], p[:, J.N_COUNTERS :].flip(0)), dim=1)
        return p.flatten(1)


ARM = os.environ.get("FABLE59_ARM", "signed")
T.Transport = SignedCounter if ARM == "signed" else V2.BalancedStart

if __name__ == "__main__":
    T.main()
