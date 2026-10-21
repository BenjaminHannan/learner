"""The V1 join: D (d128) and the creative module (d256) exchange hidden-state summaries through ONE linear projection each way.

P_dc: Linear(128 -> 256) carries D's summary into the creative controller; P_cd: Linear(256 -> 128) carries the creative registers'
summary into D's register rows. Both are ZERO-initialised (weight and bias), so at step 0 each side computes exactly what it computes
with the bridge off (tested bit-for-bit in v1/tests/test_joint.py). Each side adds the projected vector as a residual (no extra
attention row, so there is no softmax weight to leak).

The summaries are EMA buffers of the other side's detached state (momentum MOM), so a prediction never depends on the other items
of its batch and evaluation is deterministic (buffers are frozen at eval). Only the two projections receive gradient from the
bridge; each side's own parameters are trained by its own loss.
"""
from __future__ import annotations

from typing import Optional

import torch
from torch import nn

MOM = 0.99


class Bridge(nn.Module):
    def __init__(self, d_d: int = 128, d_c: int = 256, momentum: float = MOM) -> None:
        super().__init__()
        self.p_dc = nn.Linear(d_d, d_c)
        self.p_cd = nn.Linear(d_c, d_d)
        for lin in (self.p_dc, self.p_cd):
            nn.init.zeros_(lin.weight)
            nn.init.zeros_(lin.bias)
        self.register_buffer("ctx_d", torch.zeros(d_d))
        self.register_buffer("ctx_c", torch.zeros(d_c))
        self.register_buffer("seen_d", torch.zeros(()))
        self.register_buffer("seen_c", torch.zeros(()))
        self.momentum = momentum
        self.enabled = True
        self.frozen_ctx = False          # True at evaluation: summaries are not updated

    # ---- vectors added to each side (called inside that side's forward) ----
    def to_creative(self) -> torch.Tensor:
        return self.p_dc(self.ctx_d)

    def to_d(self) -> torch.Tensor:
        return self.p_cd(self.ctx_c)

    # ---- summaries observed from each side (called with that side's hidden states) ----
    def _ema(self, buf: torch.Tensor, seen: torch.Tensor, x: torch.Tensor) -> None:
        x = x.detach().float().mean(0)
        if float(seen) == 0:
            buf.copy_(x)
        else:
            buf.mul_(self.momentum).add_(x, alpha=1 - self.momentum)
        seen.add_(1)

    def observe_d(self, h: torch.Tensor) -> None:         # h [n, 128]: D's register-0 states
        if not self.frozen_ctx and self.enabled:
            with torch.no_grad():
                self._ema(self.ctx_d, self.seen_d, h)

    def observe_c(self, R: torch.Tensor) -> None:         # R [B, 9, 256]: the creative registers
        if not self.frozen_ctx and self.enabled:
            with torch.no_grad():
                self._ema(self.ctx_c, self.seen_c, R.mean(1))

    # ---- wiring ----
    def attach(self, d_model, creative) -> "Bridge":
        """Install the hooks. Idempotent; `detach()` restores both sides to their bridge-off paths."""
        d_model.bridge_in = lambda: self.to_d() if self.enabled else torch.zeros(self.p_cd.out_features, device=self.ctx_c.device)
        creative.bridge_in = lambda: self.to_creative() if self.enabled else torch.zeros(self.p_dc.out_features, device=self.ctx_d.device)
        creative.bridge_out = self.observe_c
        self._hook = d_model.heads.halt.register_forward_hook(lambda _m, args, _o: self.observe_d(args[0]))
        self._d, self._c = d_model, creative
        return self

    def attach_creative(self, creative) -> None:
        """Hook one more creative model (sleep stages load several) to this same bridge."""
        creative.bridge_in = lambda: self.to_creative() if self.enabled else torch.zeros(self.p_dc.out_features, device=self.ctx_d.device)
        creative.bridge_out = self.observe_c

    def detach(self) -> None:
        self._d.bridge_in = None
        self._c.bridge_in = None
        self._c.bridge_out = None
        self._hook.remove()

    def stats(self) -> dict:
        return {"p_dc_weight_norm": float(self.p_dc.weight.detach().norm()), "p_cd_weight_norm": float(self.p_cd.weight.detach().norm()),
                "p_dc_grad_norm": None if self.p_dc.weight.grad is None else float(self.p_dc.weight.grad.norm()),
                "p_cd_grad_norm": None if self.p_cd.weight.grad is None else float(self.p_cd.weight.grad.norm()),
                "ctx_d_norm": float(self.ctx_d.detach().norm()), "ctx_c_norm": float(self.ctx_c.detach().norm())}
