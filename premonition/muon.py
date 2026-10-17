"""Muon for the hidden matrices, AdamW for everything else (SPEC section 8; Moonshot's Muon report).

`MuonAdamW` is one optimizer whose param groups carry a `muon` flag, so the trainer's per-group lr schedule and
`state_dict` checkpoints work unchanged. A Muon step is Nesterov momentum (0.95), then the momentum-corrected gradient
is orthogonalised by five Newton-Schulz iterations and applied scaled by 0.2 sqrt(max(rows, cols)), which matches the
update RMS of AdamW so both kinds of group share one lr. Weight decay is decoupled (W <- W (1 - lr wd)).
"""
from __future__ import annotations

import math
from typing import Any, Iterable

import torch
from torch import nn

NS_COEFFICIENTS = (3.4445, -4.7750, 2.0315)
# Linear weights that Muon takes, by module path. Everything else (embeddings incl. the tied head, norms, biases,
# gates, sinks, gains, pseudo-queries, engram tables, heads.*, the binder and delta_*, writer.pool, 1-row matrices)
# goes to AdamW.
MUON_PREFIXES = ("reader.", "think.layers.", "decoder.")
MUON_MODULES = ("writer.key", "writer.value")
MUON_EXCLUDED = ("decoder.cross_gate",)


def newton_schulz(G: torch.Tensor, steps: int = 5) -> torch.Tensor:
    """Quintic Newton-Schulz iteration: the orthogonal factor of G (singular values pushed to ~[0.7, 1.2]).
    fp32 on CPU, bf16 on CUDA."""
    if G.dim() != 2:
        raise ValueError("newton_schulz takes a matrix")
    a, b, c = NS_COEFFICIENTS
    X = G.to(torch.bfloat16 if G.is_cuda else torch.float32)
    X = X / (torch.linalg.matrix_norm(X) + 1e-7)
    tall = X.shape[0] > X.shape[1]
    if tall:
        X = X.T
    for _ in range(steps):
        A = X @ X.T
        X = a * X + (b * A + c * A @ A) @ X
    return (X.T if tall else X).to(G.dtype)


class MuonAdamW(torch.optim.Optimizer):
    """Param groups with `muon=True` take Muon steps; the rest take AdamW steps (decoupled decay, bias-corrected)."""

    def __init__(self, params: Iterable[Any], lr: float = 1e-3, betas: tuple[float, float] = (0.9, 0.99),
                 eps: float = 1e-8, weight_decay: float = 0.0, momentum: float = 0.95, ns_steps: int = 5) -> None:
        defaults = dict(lr=lr, betas=betas, eps=eps, weight_decay=weight_decay, momentum=momentum,
                        ns_steps=ns_steps, muon=False)
        super().__init__(params, defaults)
        for group in self.param_groups:
            if group["muon"] and any(p.dim() != 2 for p in group["params"]):
                raise ValueError("Muon groups take 2-D matrices only")

    @torch.no_grad()
    def step(self, closure: Any = None) -> Any:
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()
        for group in self.param_groups:
            for p in group["params"]:
                if p.grad is None:
                    continue
                state = self.state[p]
                if group["muon"]:
                    self._muon(p, p.grad, state, group)
                else:
                    self._adamw(p, p.grad, state, group)
        return loss

    @staticmethod
    def _muon(p: torch.Tensor, grad: torch.Tensor, state: dict[str, Any], group: dict[str, Any]) -> None:
        lr, mu = group["lr"], group["momentum"]
        if not state:
            state["momentum_buffer"] = torch.zeros_like(p)
        buf = state["momentum_buffer"]
        buf.mul_(mu).add_(grad)
        update = newton_schulz(grad.add(buf, alpha=mu), group["ns_steps"])      # Nesterov
        p.mul_(1 - lr * group["weight_decay"])
        p.add_(update, alpha=-lr * 0.2 * math.sqrt(max(p.shape)))

    @staticmethod
    def _adamw(p: torch.Tensor, grad: torch.Tensor, state: dict[str, Any], group: dict[str, Any]) -> None:
        lr, (beta1, beta2) = group["lr"], group["betas"]
        if not state:
            state["step"] = 0
            state["exp_avg"] = torch.zeros_like(p)
            state["exp_avg_sq"] = torch.zeros_like(p)
        state["step"] += 1
        step = state["step"]
        state["exp_avg"].mul_(beta1).add_(grad, alpha=1 - beta1)
        state["exp_avg_sq"].mul_(beta2).addcmul_(grad, grad, value=1 - beta2)
        denom = (state["exp_avg_sq"].sqrt() / math.sqrt(1 - beta2 ** step)).add_(group["eps"])
        p.mul_(1 - lr * group["weight_decay"])
        p.addcdiv_(state["exp_avg"], denom, value=-lr / (1 - beta1 ** step))


def is_muon_weight(name: str, module: nn.Module) -> bool:
    """Is parameter-owning `module` (at path `name`) a Linear whose weight Muon takes?"""
    if not isinstance(module, nn.Linear) or min(module.weight.shape) < 2:
        return False
    if any(name == m or name.startswith(m + ".") for m in MUON_EXCLUDED):
        return False
    return name in MUON_MODULES or name.startswith(MUON_PREFIXES)


def muon_param_groups(model: nn.Module, weight_decay: float) -> list[dict[str, Any]]:
    """[Muon matrices, AdamW matrices (decayed), AdamW the rest (not decayed)], empty groups dropped.
    Works for any model whose modules are named as in `PremonitionMini` (missing modules are simply absent)."""
    muon_ids = {id(m.weight) for name, m in model.named_modules() if is_muon_weight(name, m)}
    params = list(model.parameters())
    muon = [p for p in params if id(p) in muon_ids]
    matrices = [p for p in params if id(p) not in muon_ids and p.dim() >= 2]
    rest = [p for p in params if id(p) not in muon_ids and p.dim() < 2]
    groups = [dict(params=muon, muon=True, weight_decay=weight_decay),
              dict(params=matrices, muon=False, weight_decay=weight_decay),
              dict(params=rest, muon=False, weight_decay=0.0)]
    return [g for g in groups if g["params"]]


__all__ = ["MuonAdamW", "muon_param_groups", "newton_schulz"]
