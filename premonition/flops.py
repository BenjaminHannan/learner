"""Training-FLOP measurement and budgets (design/06 §4).

`count_flops` wraps `torch.utils.flop_counter.FlopCounterMode`, which counts
matmuls and attention kernels only (elementwise work such as the minGRU scan is
skipped). Torch registers no formula for the CPU flash-attention kernel, so it
is added here with the same formula torch uses for the CUDA kernels: dense
attention (a causal mask is not discounted) and a backward pass that recomputes
the scores (2.5x the forward attention FLOPs).

For `Core` a hand count in that same convention must agree with the counter
within 10%. For Premonition-mini, whose cost depends on how many questions are
asked and for how many loops, measured batches are fitted to
    FLOPs per training step = a * tokens + b * sum(questions x loops)
where tokens are the padded [B, T] positions the reader runs over.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence

import torch
from torch.utils import flop_counter
from torch.utils.flop_counter import FlopCounterMode

from learnlab.core import Core, CoreConfig, lm_loss
from premonition.batch import VisitBatch

aten = torch.ops.aten


def _cpu_sdpa(query_shape, key_shape, value_shape, *args, out_shape=None, **kwargs) -> int:
    return flop_counter.sdpa_flop_count(query_shape, key_shape, value_shape)


def _cpu_sdpa_backward(grad_out_shape, query_shape, key_shape, value_shape, *args,
                       out_shape=None, **kwargs) -> int:
    return flop_counter.sdpa_backward_flop_count(grad_out_shape, query_shape, key_shape, value_shape)


EXTRA_FORMULAS = {
    aten._scaled_dot_product_flash_attention_for_cpu: _cpu_sdpa,
    aten._scaled_dot_product_flash_attention_for_cpu_backward: _cpu_sdpa_backward,
}


def count_flops(step: Callable[[], Optional[torch.Tensor]]) -> int:
    """FLOPs of `step()` plus, when it returns a loss, that loss's backward pass."""
    with FlopCounterMode(display=False, custom_mapping=EXTRA_FORMULAS) as counter:
        loss = step()
        if loss is not None:
            loss.backward()
    return int(counter.get_total_flops())


# ---------------------------------------------------------------------------- Core (A, B, C, E)
def core_flops_per_token(config: CoreConfig, seq_len: Optional[int] = None,
                         training: bool = True) -> float:
    """Hand count per token in FlopCounterMode's convention.

    Forward: 2 x weight-matrix entries (biases and norms are not matmuls), dense attention
    4 T d per layer (QK^T and AV over the whole row, as the kernels are counted), and the
    tied head 2 V d. Training: matmuls x3, attention x3.5 (the backward recomputes scores).
    """
    d, layers, length = config.d_model, config.n_layers, seq_len or config.context
    matrices = layers * (3 * d * d + d * d + 2 * config.mlp_ratio * d * d)
    dense = 2 * matrices + 2 * config.vocab_size * d
    attention = 4 * layers * length * d
    return 3.0 * dense + 3.5 * attention if training else float(dense + attention)


def spec_core_flops_per_token(config: CoreConfig, parameters: int, seq_len: Optional[int] = None
                              ) -> float:
    """design/06 §4's formula: 3 (2 N_blocks + 2 L ctx d + 2 V d), attention causal-discounted
    and without the backward recompute. Kept for comparison with the counter."""
    length = seq_len or config.context
    return 3.0 * (2 * parameters + 2 * config.n_layers * length * config.d_model
                  + 2 * config.vocab_size * config.d_model)


def measure_core(model: Core, tokens: torch.Tensor) -> int:
    """Counted FLOPs of one training step (forward + backward) on tokens [B, T + 1]."""
    inputs, targets = tokens[:, :-1], tokens[:, 1:]
    model.zero_grad(set_to_none=True)
    flops = count_flops(lambda: lm_loss(model(inputs), targets))
    model.zero_grad(set_to_none=True)
    return flops


# ---------------------------------------------------------------------------- Premonition-mini (D)
@dataclass(frozen=True)
class FlopSample:
    flops: int
    tokens: int              # padded [B, T] positions
    question_loops: int      # sum over questions of the think loops run


def measure_mini(model: torch.nn.Module, batch: VisitBatch, **forward_kwargs) -> FlopSample:
    """Counted FLOPs of one training step of `PremonitionMini` on `batch`."""
    seen: dict[str, int] = {}

    def step() -> torch.Tensor:
        out = model(batch, **forward_kwargs)
        seen["loops"] = int(out["metrics"]["question_loops"])
        return out["loss"]

    model.zero_grad(set_to_none=True)
    flops = count_flops(step)
    model.zero_grad(set_to_none=True)
    return FlopSample(flops, int(batch.tokens.numel()), seen["loops"])


@dataclass(frozen=True)
class FlopFit:
    a: float                 # FLOPs per padded token
    b: float                 # FLOPs per (question, loop)
    worst: float             # largest relative residual over the fitted samples

    def __call__(self, tokens: float, question_loops: float) -> float:
        return self.a * tokens + self.b * question_loops

    def per_token(self, question_loops_per_token: float) -> float:
        return self.a + self.b * question_loops_per_token


def fit_flops(samples: Sequence[FlopSample]) -> FlopFit:
    """Least-squares FLOPs = a tokens + b question_loops (no intercept), rows weighted by 1 / FLOPs
    so the fit is in relative error."""
    if len(samples) < 2:
        raise ValueError("need at least two samples")
    x = torch.tensor([[s.tokens, s.question_loops] for s in samples], dtype=torch.float64)
    y = torch.tensor([s.flops for s in samples], dtype=torch.float64)
    weight = 1.0 / y
    solution = torch.linalg.lstsq(x * weight.unsqueeze(1), y * weight).solution
    a, b = solution.tolist()
    worst = ((x @ solution - y).abs() / y).max().item()
    return FlopFit(a, b, worst)


def mini_hand_count(config, batch: VisitBatch, question_loops: int, training: bool = True) -> float:
    """Hand count of the matmul and attention FLOPs of one step of D, in the counter's convention.

    Covers the reader, the card writer, the LM head, and per (question, loop) the think block,
    the heads, ASK scoring and the decoder at the batch's answer length. Leaves out the slot
    binder and the first-loop recall diagnostic (both < 1%).
    """
    d, dk, v = config.d_model, config.key_dim, config.total_vocab
    visits, length = batch.tokens.shape
    lines = batch.line_start.shape[1]
    padded = visits * (-(-length // config.window)) * config.window
    lm_tokens = int((batch.lm_mask[:, :-1] & (batch.line_of[:, 1:] >= 0)).sum())
    answer_len = int((batch.answer != -100).sum(1).max()) if batch.answer.numel() else 0
    answer_tokens = int((batch.answer != -100).sum())
    rows = config.rows
    dense = visits * length * (sum(8 * d * d + 4 * config.reader_mlp * d * d for _ in config.reader)
                               + 2 * d)
    dense += lm_tokens * 2 * v * d
    attention = padded * 8 * config.window * d * config.reader.count("attn")
    if config.store:
        dense += visits * lines * (2 * d * dk + 2 * d * d)
    per_loop = config.think_layers * 2 * rows * (4 * d * d + 2 * config.think_mlp * d * d) + 2 * d
    per_loop_attention = config.think_layers * 4 * rows * rows * d
    if config.store:
        per_loop += 2 * d * dk + 2 * d + 2 * dk * (lines + 1)
    per_loop += answer_len * (8 + 2 + 2 + 4 * config.decoder_mlp) * d * d + 4 * rows * d * d
    per_loop_attention += 4 * answer_len * answer_len * d + 4 * answer_len * rows * d
    questions = max(batch.q_visit.shape[0], 1)
    dense += question_loops * per_loop + question_loops / questions * answer_tokens * 2 * v * d
    attention += question_loops * per_loop_attention
    return 3.0 * dense + 3.5 * attention if training else float(dense + attention)


__all__ = ["EXTRA_FORMULAS", "FlopFit", "FlopSample", "core_flops_per_token", "count_flops",
           "fit_flops", "measure_core", "measure_mini", "mini_hand_count", "spec_core_flops_per_token"]
