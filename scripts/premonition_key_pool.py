"""A separate pooling scorer for card KEYS (Claude, 2026-09-19) -- ADDITIVE variant.

The frozen `CardWriter` (archive/opus-ovn-20260918-235851/frozen/premonition/model.py lines 171-197) pools
each line's reader states ONCE and feeds that single pooled vector to both projections:

    score = pool(hidden) -> softmax over the line's tokens -> p
    key   = normalize(W_k p),   value = W_v p

So the card's address and the card's contents are read off the same mixture of the line's tokens. A line is
"<tag> SUBJ REL OBJ ..."; the address wants the subject and the relation, the contents want the object.
This module gives the KEY its own scorer:

    p_V = softmax-pool with `pool`      -> value = W_v p_V          (unchanged)
    p_K = softmax-pool with `key_pool`  -> key   = normalize(W_k p_K)   NEW

`key_pool` is an `nn.Linear(d_model, 1)` CLONED from `pool` (weight AND bias) at build time, so at
initialisation p_K == p_V and the model's outputs are EXACTLY the baseline's with the same seed. Nothing
else changes: the NULL card, W_k, W_v, the masks, the curriculum, the losses and the optimiser are all
untouched. New parameters: d_model + 1 (33 on this toy ladder, where d_model = 32).

`apply_key_pool` swaps `model.writer` for a wrapper that REUSES the existing writer's submodules and
parameters (so `writer.pool.*`, `writer.key.*`, `writer.value.*`, `writer.null_key`, `writer.null_value`
keep their state_dict names and values, and `writer.key_pool.*` is added). It is class-agnostic, so it
composes with the relation-shortcut subclass, and it consumes no RNG, so init parity holds.

    PY -B scripts/premonition_key_pool.py            # runs tests/test_premonition_key_pool.py
"""
from __future__ import annotations

import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402

torch = None
_CLASS = None

NEW_KEYS = ("writer.key_pool.bias", "writer.key_pool.weight")


def _imports() -> None:
    """Pull the frozen names into this module's globals (only valid after L.bootstrap())."""
    global torch
    import torch as _torch
    torch = _torch


def key_pool_class():
    """The CardWriter replacement; built on first use so it sees the frozen package."""
    global _CLASS
    if _CLASS is not None:
        return _CLASS
    _imports()
    from premonition.store import CardStore
    from torch import nn

    class KeyPoolCardWriter(nn.Module):
        """Frozen `CardWriter` with a SECOND softmax pooling scorer used only for the card keys.

        Built from an existing `CardWriter` (or from another `KeyPoolCardWriter`): `pool`, `key`, `value`,
        `null_key` and `null_value` are the SAME objects, so no value changes and the state_dict keys are
        the frozen ones plus `key_pool.weight` / `key_pool.bias`.
        """

        key_pool_writer = True

        def __init__(self, writer) -> None:
            super().__init__()
            self.pool = writer.pool                # reused, same parameters
            self.key = writer.key
            self.value = writer.value
            self.null_key = writer.null_key
            self.null_value = writer.null_value
            # NEW. `nn.Linear.__init__` draws from the global RNG, so it is forked and restored: applying
            # this wrapper must not shift the stream any later build would see.
            with torch.random.fork_rng(devices=[]):
                self.key_pool = nn.Linear(self.pool.in_features, 1)
            self.clone_pool()

        def clone_pool(self) -> None:
            """key_pool := pool (weight and bias), so p_K == p_V and the model matches the baseline."""
            with torch.no_grad():
                self.key_pool.weight.copy_(self.pool.weight)
                self.key_pool.bias.copy_(self.pool.bias)

        @staticmethod
        def _pooled(scorer, hidden, real, slot, visits, lines):
            """The frozen CardWriter.forward pooling (model.py 186-196), verbatim, for one scorer."""
            score = scorer(hidden).squeeze(-1).float()[real]
            peak = torch.full((visits * lines,), -math.inf, device=hidden.device)
            peak = peak.scatter_reduce(0, slot, score.detach(), "amax").clamp_min(-1e30)
            weight = torch.exp(score - peak[slot])
            total = torch.zeros(visits * lines, device=hidden.device).index_add(0, slot, weight)
            weight = weight / total[slot]
            return torch.zeros(visits * lines, hidden.shape[-1], device=hidden.device).index_add(
                0, slot, weight.unsqueeze(-1) * hidden[real].float()).view(visits, lines, -1)

        def forward(self, hidden, batch):
            """Frozen `CardWriter.forward` copied, with the pooling done TWICE (marked EDITED)."""
            visits, lines = batch.line_start.shape
            real = batch.line_of >= 0
            slot = (batch.line_of.clamp_min(0)
                    + lines * torch.arange(visits, device=hidden.device).unsqueeze(1))[real]
            pooled = self._pooled(self.pool, hidden, real, slot, visits, lines)            # EDITED (values)
            pooled_key = self._pooled(self.key_pool, hidden, real, slot, visits, lines)    # EDITED (keys)
            return CardStore.write(self.key(pooled_key), self.value(pooled), batch,        # EDITED
                                   self.null_key, self.null_value)

    _CLASS = KeyPoolCardWriter
    return _CLASS


def apply_key_pool(model):
    """Replace `model.writer` with a KeyPoolCardWriter cloned from it. Class-agnostic; no RNG consumed."""
    _imports()
    writer = getattr(model, "writer", None)
    if writer is None:
        raise SystemExit("the key-pool variant needs a card store (model.writer is None)")
    if getattr(writer, "key_pool_writer", False):
        return model                       # already applied
    model.writer = key_pool_class()(writer)
    model.key_pool = True
    return model


def build(arm: str, seed: int, early_ans: float = 0.2, shortcut: bool = False):
    """R.build (or the relation-shortcut build) for `arm`, then the key pool: same init, 2 new tensors."""
    _imports()
    if shortcut:
        import premonition_relation_shortcut as RS
        model = RS.build(arm, seed, early_ans, shortcut=True)
    else:
        model = R.build(arm, seed, early_ans)
    apply_key_pool(model)
    model.key_pool = True
    return model


if __name__ == "__main__":
    L.bootstrap()
    sys.path.insert(0, str(L.ROOT / "tests"))
    from test_premonition_key_pool import main as _main
    raise SystemExit(_main())
