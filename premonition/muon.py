"""Muon for the hidden matrices, AdamW for everything else (SPEC section 8; Moonshot's Muon report).

`MuonAdamW` is one optimizer interface over `Muon` and torch's `AdamW`; its param groups carry a `muon` flag, so the
trainer's per-group lr schedule and `state_dict` checkpoints work unchanged. A Muon step is Nesterov momentum (0.95), then the momentum-corrected gradient
is orthogonalised by five Newton-Schulz iterations and applied scaled by 0.2 sqrt(max(rows, cols)), which matches the
update RMS of AdamW so both kinds of group share one lr. Weight decay is decoupled (W <- W (1 - lr wd)).
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Optional

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


class Muon(torch.optim.Optimizer):
    """Muon steps for 2-D matrices: Nesterov momentum, Newton-Schulz orthogonalisation, RMS-matched scale, decoupled
    weight decay."""

    def __init__(self, params: Iterable[Any], lr: float = 1e-3, weight_decay: float = 0.0, momentum: float = 0.95,
                 ns_steps: int = 5) -> None:
        super().__init__(params, dict(lr=lr, weight_decay=weight_decay, momentum=momentum, ns_steps=ns_steps,
                                      muon=True))
        if any(p.dim() != 2 for group in self.param_groups for p in group["params"]):
            raise ValueError("Muon groups take 2-D matrices only")

    @torch.no_grad()
    def step(self, closure: Any = None) -> Any:
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()
        for group in self.param_groups:
            lr, mu = group["lr"], group["momentum"]
            for p in group["params"]:
                if p.grad is None:
                    continue
                state = self.state[p]
                if not state:
                    state["momentum_buffer"] = torch.zeros_like(p)
                buf = state["momentum_buffer"]
                buf.mul_(mu).add_(p.grad)
                update = newton_schulz(p.grad.add(buf, alpha=mu), group["ns_steps"])      # Nesterov
                p.mul_(1 - lr * group["weight_decay"])
                p.add_(update, alpha=-lr * 0.2 * math.sqrt(max(p.shape)))
        return loss


class MuonAdamW:
    """One optimizer interface over `Muon` (groups with `muon=True`) and torch's own `AdamW` (the rest, fused on
    CUDA like the base trainer's), so the AdamW half costs what it costs today. `param_groups` lists both parts'
    groups (Muon first), so the trainer's per-group lr schedule drives them; `state_dict` holds both parts."""

    def __init__(self, params: Iterable[dict[str, Any]], lr: float = 1e-3, betas: tuple[float, float] = (0.9, 0.99),
                 eps: float = 1e-8, weight_decay: float = 0.0, momentum: float = 0.95, ns_steps: int = 5,
                 fused: Optional[bool] = None) -> None:
        groups = [dict(group) for group in params]
        if not groups or not all(isinstance(group, dict) for group in groups):
            raise ValueError("MuonAdamW takes a non-empty list of param-group dicts")
        muon = [group for group in groups if group.get("muon", False)]
        adamw = [dict(group, muon=False) for group in groups if not group.get("muon", False)]
        self.parts: list[torch.optim.Optimizer] = []
        if muon:
            self.parts.append(Muon(muon, lr=lr, weight_decay=weight_decay, momentum=momentum, ns_steps=ns_steps))
        if adamw:
            self.parts.append(torch.optim.AdamW(adamw, lr=lr, betas=betas, eps=eps, weight_decay=weight_decay,
                                                fused=fused))

    @property
    def param_groups(self) -> list[dict[str, Any]]:
        return [group for part in self.parts for group in part.param_groups]

    @property
    def state(self) -> dict[Any, Any]:
        return {p: s for part in self.parts for p, s in part.state.items()}

    def zero_grad(self, set_to_none: bool = True) -> None:
        for part in self.parts:
            part.zero_grad(set_to_none=set_to_none)

    def step(self, closure: Any = None) -> Any:
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()
        for part in self.parts:
            part.step()
        return loss

    def state_dict(self) -> dict[str, Any]:
        return {"kinds": [type(part).__name__ for part in self.parts], "parts": [part.state_dict() for part in self.parts]}

    def load_state_dict(self, state: dict[str, Any]) -> None:
        if state["kinds"] != [type(part).__name__ for part in self.parts]:
            raise ValueError(f"optimizer state holds {state['kinds']}, this optimizer has "
                             f"{[type(part).__name__ for part in self.parts]}")
        for part, saved in zip(self.parts, state["parts"]):
            part.load_state_dict(saved)


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


__all__ = ["Muon", "MuonAdamW", "muon_param_groups", "newton_schulz"]
