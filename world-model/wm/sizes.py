"""Size ladder for the scaling runs, built from the vendored config classes.

S/M/L/P are the training ladder (D = d_board 256, R = 64 rows). `tiny` is a CPU test config.
`P` is the production trunk: counted and probed, never trained here.
"""
from __future__ import annotations

from typing import Dict, Tuple

from premonition_core_v2.board_swarm import (
    BoardSwarmConfig, active_param_count, build, build_on_meta,
)
from premonition_core_v2.config import CoreDims, RowLayout

__all__ = ["SIZES", "make_cfg", "count_report", "EXPECTED_M"]

# size -> (d_inner d, n_blocks L)
SIZES: Dict[str, Tuple[int, int]] = {
    "S": (320, 6), "M": (448, 10), "L": (640, 14), "Lp": (576, 12), "P": (896, 16),
    # PROBLEM-7 shape race: 4 wide blocks at matched total params (counted 2026-11-24)
    "Sw4": (384, 4), "Pw4": (1792, 4),
    "P7toy": (256, 2),  # PROBLEM-7 planned ~3M-active toy (2.61M active, 6.28M total)
}

# expected (total, active) in millions, from the brief; tests assert within +/- 0.2M
EXPECTED_M: Dict[str, Tuple[float, float]] = {
    "S": (23.8, 6.6), "M": (74.3, 18.1), "L": (209.0, 48.4), "Lp": (145.7, 34.2),
    "P": (465.6, 105.9),
}


def _dims(size: str) -> CoreDims:
    if size == "tiny":
        return CoreDims(preset="debug_tiny", d_board=32, rows=RowLayout(8, 3), inbox_rows=24, ctx_extra_rows=8,
                        k_max=4, n_shared_scratch=2, answer_dim=32, summary_dim=32, n_candidates=8, max_ticks=24)
    return CoreDims(preset="dryrun_50m", d_board=256, rows=RowLayout(64, 24), inbox_rows=24, ctx_extra_rows=8,
                    k_max=4, n_shared_scratch=2, answer_dim=256, summary_dim=32, n_candidates=8, max_ticks=24)


def make_cfg(size: str, *, lb_weight: float = 0.01, z_weight: float = 1e-3,
             gate_bias_init: float = -2.0) -> BoardSwarmConfig:
    """The vendored BoardSwarmConfig for one ladder rung (no vendored code edited)."""
    dims = _dims(size)
    if size == "tiny":
        d, L, n_heads = 64, 2, 1
        n_experts, top_k, expert_hidden = 4, 2, 64
        head_hidden, tension_hidden, critic_hidden, glance_dim = 32, 16, 16, 8
    else:
        if size not in SIZES:
            raise ValueError(f"unknown size {size!r}; choose one of {sorted(list(SIZES) + ['tiny'])}")
        d, L = SIZES[size]
        n_heads = d // 64
        n_experts, top_k, expert_hidden = 16, 2, d
        head_hidden, tension_hidden, critic_hidden, glance_dim = 256, 128, 128, 32
    return BoardSwarmConfig(
        dims=dims, d_inner=d, n_blocks=L, n_heads=n_heads, n_experts=n_experts, top_k=top_k,
        expert_hidden=expert_hidden, cone_block=-1, n_pool=4, head_hidden=head_hidden,
        tension_hidden=tension_hidden, critic_hidden=critic_hidden, glance_dim=glance_dim,
        aux_lb_weight=lb_weight, aux_z_weight=z_weight, checkpoint_ticks=False,
        gate_bias_init=gate_bias_init,
    )


def count_report(size: str) -> Dict[str, object]:
    """Parameter counts for one rung.

    total        : every trainable number of the built board (board only, readout excluded)
    expert       : the expert MLP numbers inside all SparseMoE blocks
    active       : what one tick of one row touches (vendored active_param_count)
    trunk_active : block parameters with experts charged at top_k / n_experts
    """
    cfg = make_cfg(size)
    module = build_on_meta(lambda: build(cfg))
    total, expert, active = active_param_count(module)

    block_total = 0
    block_expert = 0
    for name, p in module.named_parameters():
        if ".blocks." in name:
            block_total += p.numel()
            if ".moe.experts." in name:
                block_expert += p.numel()
    share = cfg.top_k / cfg.n_experts
    trunk_active = block_total - block_expert + int(round(block_expert * share))

    return {
        "size": size,
        "total": int(total),
        "expert": int(expert),
        "active": int(active),
        "trunk_active": int(trunk_active),
        "total_m": total / 1e6,
        "expert_m": expert / 1e6,
        "active_m": active / 1e6,
        "trunk_active_m": trunk_active / 1e6,
    }
