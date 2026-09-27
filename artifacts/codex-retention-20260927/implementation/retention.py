"""Request-scoped adapters and itemwise retention checks.

An inactive adapter is bypassed completely. Its tensors, dropout and scale are
never evaluated on that path. This protects the base function, conditional on
selecting that path; it does not prove that a learned router selects correctly.

Load/save ordinary model state_dicts as before. Install after loading an adapter,
then use one scope for the ENTIRE prefill/generation. Published model weights
must remain read-only; train candidate models separately.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import hashlib
import math
from typing import Iterator, Sequence

import torch
from torch import nn


@dataclass
class _RouteLease:
    enabled: bool
    active: bool = True


def _route_enabled(context: ContextVar) -> bool:
    lease = context.get()
    if lease is None:
        return False
    if not lease.active:
        raise RuntimeError("Adapter request scope ended before deferred work ran")
    return lease.enabled


class _ScopedLinear(nn.Module):
    """Same state_dict names and arithmetic as claude_blurt2.add_lora."""

    def __init__(self, old: nn.Module, enabled: ContextVar):
        super().__init__()
        self.base, self.A, self.B = old.base, old.A, old.B
        self.drop, self.scale = old.drop, old.scale
        self._enabled = enabled
        self.train(old.training)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if not _route_enabled(self._enabled):
            return self.base(x)
        up = (self.drop(x).float() @ self.A.t() @ self.B.t()) * self.scale
        return self.base(x) + up.to(x.dtype)


class RequestScopedAdapter:
    """Control one existing unmerged B2-style LoRA without mutable scale flags.

The default is base-only, including requests without a routing decision. Scopes
nest and restore on exceptions; concurrent threads/tasks have separate choices.
This is synchronous generation: do not return a lazy generator from a scope.
Decide once from frozen-base prompt features, before creating an attention cache.
"""

    def __init__(self, model: nn.Module):
        self.model = model
        self._enabled = ContextVar(f"adapter_{id(self)}", default=None)
        if any(isinstance(m, _ScopedLinear) for m in model.modules()):
            raise ValueError("Model already has a request-scoped adapter")
        candidates = []
        for name, mod in list(model.named_modules()):
            if all(hasattr(mod, attr) for attr in ("base", "A", "B", "drop", "scale")):
                if not isinstance(mod.base, nn.Linear):
                    raise TypeError(f"Unsupported adapter base at {name}")
                if any(p.requires_grad for p in mod.base.parameters()):
                    raise ValueError(f"Adapter base is trainable at {name}")
                if not name:
                    raise ValueError("Pass the enclosing model, not a single LoRA layer")
                candidates.append((name, mod))
        if not candidates:
            raise ValueError("No unmerged B2-style LoRA layers found")
        adapter_parameters = {id(p) for _, mod in candidates for p in (mod.A, mod.B)}
        for name, param in model.named_parameters():
            if id(param) not in adapter_parameters and param.requires_grad:
                raise ValueError(f"Base parameter is trainable: {name}")
        self.layer_names = tuple(name for name, _ in candidates)
        for name, mod in candidates:
            parent_name, _, child = name.rpartition(".")
            parent = model.get_submodule(parent_name) if parent_name else model
            setattr(parent, child, _ScopedLinear(mod, self._enabled))

    @contextmanager
    def scope(self, enabled: bool) -> Iterator[None]:
        """Low-level scope for fresh-cache helpers or base feature extraction.

        Prefer generate() for serving: helpers used here MUST NOT accept or reuse
        another request's KV cache. Detached work cannot outlive this scope.
        """
        if type(enabled) is not bool:
            raise TypeError("Routing must be a single boolean for the whole request")
        lease = _RouteLease(enabled)
        token = self._enabled.set(lease)
        try:
            yield
        finally:
            lease.active = False
            self._enabled.reset(token)

    @property
    def enabled(self) -> bool:
        return _route_enabled(self._enabled)

    def generate(self, *, enabled: bool = False, **kwargs):
        """Start a fresh, synchronous generation with one fixed adapter choice."""
        if self.model.training:
            raise ValueError("Serving requires model.eval()")
        if kwargs.get("past_key_values") is not None or kwargs.get("cache") is not None:
            raise ValueError("Do not reuse attention caches across routed requests")
        with self.scope(enabled), torch.inference_mode():
            return self.model.generate(**kwargs)

    def base_digest(self) -> str:
        """Fingerprint frozen weights and buffers, excluding adapter A/B tensors."""
        excluded = {f"{name}.{suffix}" for name in self.layer_names for suffix in ("A", "B")}
        digest = hashlib.sha256()
        for name, tensor in sorted(self.model.state_dict().items()):
            if name in excluded:
                continue
            t = tensor.detach().cpu().contiguous()
            digest.update(f"{name}:{t.dtype}:{tuple(t.shape)}\n".encode())
            digest.update(t.reshape(-1).view(torch.uint8).numpy().tobytes())
        return digest.hexdigest()


@dataclass(frozen=True)
class RetentionCounts:
    total: int
    previously_correct: int
    lost: int
    gained: int
    retained: int


def retention_counts(before: Sequence[bool], after: Sequence[bool]) -> RetentionCounts:
    """Track lost correct answers independently of gains and net accuracy."""
    if len(before) != len(after) or not len(before):
        raise ValueError("Need aligned, nonempty itemwise correctness panels")
    if any(x not in (0, 1, False, True) for x in (*before, *after)):
        raise ValueError("Correctness values must be binary")
    previous = sum(bool(x) for x in before)
    lost = sum(bool(a) and not bool(b) for a, b in zip(before, after))
    gained = sum(not bool(a) and bool(b) for a, b in zip(before, after))
    return RetentionCounts(len(before), previous, lost, gained, previous - lost)


def zero_failure_upper_bound(n: int, confidence: float = 0.95) -> float:
    """One-sided binomial upper bound after zero failures (independent trials).

    A finite clean retention panel is evidence, not a universal guarantee.
    For 200 independent trials, zero failures still permits about a 1.49% rate.
    """
    if n < 1 or not 0 < confidence < 1:
        raise ValueError("Need positive n and confidence strictly between 0 and 1")
    return -math.expm1(math.log1p(-confidence) / n)
