"""K2 Horizon (dense) for mlx-lm: Llama layout, but every RMSNorm normalizes `layernorm_num_groups` slices of the
hidden dim independently (IFM modeling_k2_horizon.K2HorizonRMSNorm). Written for Practice-1M; dense configs only
(no MoE / MoVA / attention gate / q-k norm / partial rope)."""
from dataclasses import dataclass
from typing import Any, Dict, Optional

import mlx.core as mx
import mlx.nn as nn

from . import llama


@dataclass
class ModelArgs(llama.ModelArgs):
    rope_theta: float = 10_000_000.0
    layernorm_num_groups: int = 2
    rope_parameters: Optional[Dict[str, Any]] = None
    num_experts: int = 0
    query_key_norm: bool = False
    attention_gate_func: Optional[str] = None
    rope_head_dim: Optional[int] = None

    def __post_init__(self):
        if self.rope_parameters:
            self.rope_theta = float(self.rope_parameters.get("rope_theta", self.rope_theta))
            if self.rope_parameters.get("rope_type", "default") != "default" and self.rope_scaling is None:
                self.rope_scaling = dict(self.rope_parameters)
        if self.num_experts or self.query_key_norm or self.attention_gate_func:
            raise ValueError("k2_horizon: only the dense config (no MoE, q/k norm or attention gate) is supported")
        hd = self.head_dim or self.hidden_size // self.num_attention_heads
        if self.rope_head_dim not in (None, hd):
            raise ValueError("k2_horizon: partial rope (rope_head_dim != head_dim) is not supported")
        super().__post_init__()


class GroupRMSNorm(nn.Module):
    def __init__(self, dims: int, eps: float, groups: int):
        super().__init__()
        assert dims % groups == 0
        self.weight = mx.ones((dims,))
        self.eps = eps
        self.groups = groups

    def __call__(self, x):
        y = mx.fast.rms_norm(x.reshape(*x.shape[:-1], self.groups, -1), None, self.eps)
        return self.weight * y.reshape(x.shape)


def _norm(args):
    return GroupRMSNorm(args.hidden_size, args.rms_norm_eps, args.layernorm_num_groups)


class Model(llama.Model):
    def __init__(self, args: ModelArgs):
        super().__init__(args)
        for layer in self.model.layers:
            layer.input_layernorm = _norm(args)
            layer.post_attention_layernorm = _norm(args)
        self.model.norm = _norm(args)
