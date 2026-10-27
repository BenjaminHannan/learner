"""Bounded device benchmark: environment facts plus timed real training steps.

Nothing here is a learning result.  It measures whether the selected device
can run the actual meta-training and PC-memory optimizer steps, how fast, and
with what peak memory, before any meaningful GPU training is attempted.
"""
from __future__ import annotations

import math
import time
from typing import Any, Callable

import torch
from torch import nn

from .experiment import environment_report, meta_train_episode, parameter_count
from .model import MainNetwork
from .positive_controls import memory_control_examples, train_memory_control_step
from .tasks import generate_episode
from .transformer_model import RecurrentTransformerLearner

MAX_BENCH_SECONDS = 540.0


def _bench_environment(device: torch.device) -> dict[str, Any]:
    report = environment_report(device)
    report["cuda_available"] = torch.cuda.is_available()
    if device.type == "cuda":
        free, total = torch.cuda.mem_get_info(device)
        report.update(free_bytes_at_start=int(free), total_bytes=int(total))
    return report


def _sync(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def _time_steps(
    step: Callable[[int], dict[str, Any]],
    *,
    device: torch.device,
    warmup: int,
    steps: int,
    deadline: float,
) -> dict[str, Any]:
    if device.type == "cuda":
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats(device)
    rows: list[dict[str, Any]] = []
    for index in range(warmup):
        rows.append(step(index))
    _sync(device)
    started = time.perf_counter()
    timed = 0
    for index in range(warmup, warmup + steps):
        if time.monotonic() >= deadline:
            break
        rows.append(step(index))
        timed += 1
    _sync(device)
    elapsed = time.perf_counter() - started
    losses = [float(row["loss"]) for row in rows]
    return {
        "warmup_steps": warmup,
        "timed_steps": timed,
        "timed_seconds": elapsed,
        "steps_per_second": timed / elapsed if timed and elapsed > 0 else 0.0,
        "all_losses_finite": all(math.isfinite(value) for value in losses),
        "first_loss": losses[0] if losses else None,
        "last_loss": losses[-1] if losses else None,
        "peak_allocated_bytes": (
            int(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else None
        ),
        "peak_reserved_bytes": (
            int(torch.cuda.max_memory_reserved(device)) if device.type == "cuda" else None
        ),
        "last_row": {
            key: value
            for key, value in rows[-1].items()
            if isinstance(value, (int, float, bool, str))
        } if rows else None,
    }


def _new_model(backbone: str, seed: int, device: torch.device) -> nn.Module:
    torch.manual_seed(seed)
    model = MainNetwork() if backbone == "gru" else RecurrentTransformerLearner()
    return model.to(device)


def run_benchmark(
    *,
    device: str = "cuda",
    backbones: tuple[str, ...] = ("transformer", "gru"),
    steps: int = 30,
    warmup: int = 3,
    seconds: float = 300.0,
    seed: int = 0,
    tiers: tuple[int, ...] = (1, 2),
    items: int = 16,
) -> dict[str, Any]:
    """Time real meta-training and PC-E/PC-W steps for each backbone."""
    if not 0.0 < seconds <= MAX_BENCH_SECONDS:
        raise ValueError(f"seconds must lie in (0,{MAX_BENCH_SECONDS:g}]")
    if steps <= 0 or warmup < 0:
        raise ValueError("steps must be positive and warmup nonnegative")
    if any(name not in ("gru", "transformer") for name in backbones) or not backbones:
        raise ValueError("backbones must be drawn from gru/transformer")
    if any(tier not in (1, 2) for tier in tiers) or not tiers:
        raise ValueError("benchmark tiers must be drawn from 1/2")
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was explicitly selected but is unavailable")
    torch_device = torch.device(device)
    started = time.monotonic()
    phases_per_backbone = 3
    phase_budget = seconds / (len(backbones) * phases_per_backbone)
    report: dict[str, Any] = {
        "environment": _bench_environment(torch_device),
        "settings": {
            "backbones": list(backbones),
            "steps": steps,
            "warmup": warmup,
            "seconds": seconds,
            "seed": seed,
            "tiers": list(tiers),
            "items": items,
        },
        "backbones": {},
    }
    for backbone in backbones:
        entry: dict[str, Any] = {}

        model = _new_model(backbone, seed, torch_device)
        entry["parameter_count"] = parameter_count(model)
        entry["persistent_memory_bytes"] = int(
            model.new_memory(batch=1).numel() * 4
        )
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)

        def meta_step(index: int) -> dict[str, Any]:
            tier = tiers[index % len(tiers)]
            episode = generate_episode("train", seed * 10_007 + index, tier=tier)
            return meta_train_episode(model, episode, optimizer, device=torch_device)

        entry["meta_train"] = _time_steps(
            meta_step,
            device=torch_device,
            warmup=warmup,
            steps=steps,
            deadline=time.monotonic() + phase_budget,
        )
        del model, optimizer

        examples = memory_control_examples("train", seed, item_count=items)
        for mode, label in (("encoder", "pc_e"), ("writer", "pc_w")):
            model = _new_model(backbone, seed, torch_device)
            optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)

            def control_step(index: int, *, mode: str = mode) -> dict[str, Any]:
                return train_memory_control_step(
                    model,
                    examples,
                    optimizer,
                    mode=mode,
                    device=torch_device,
                )

            entry[label] = _time_steps(
                control_step,
                device=torch_device,
                warmup=warmup,
                steps=steps,
                deadline=time.monotonic() + phase_budget,
            )
            del model, optimizer
        report["backbones"][backbone] = entry
        if time.monotonic() - started > seconds:
            report["truncated"] = True
            break
    report["elapsed_seconds"] = time.monotonic() - started
    return report


__all__ = ["run_benchmark"]
