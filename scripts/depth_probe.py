#!/usr/bin/env python3
"""Read-only reasoning-depth probe for a trained transformer PC-memory checkpoint."""

from __future__ import annotations

import argparse
import json

import torch
import torch.nn.functional as F

from memorylab.checkpoint import inspect_checkpoint_config, load_scored_restart
from memorylab.positive_controls import (
    _ControlTheta,
    _model_config,
    _oracle_contents,
    _write_control_memory,
    evaluate_memory_control,
    memory_control_examples,
)
from memorylab.tasks import batch_queries
from memorylab.transformer_model import RecurrentTransformerLearner


MAX_CHECKPOINT_BYTES = 64 * 1024 * 1024


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate the same PC-E/PC-W checkpoint at several reasoning depths."
    )
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--worlds", type=int, default=4)
    parser.add_argument("--items", type=int, default=16)
    parser.add_argument("--max-depth", type=int, default=8)
    parser.add_argument("--trace-worlds", type=int, default=4)
    return parser


def trace_reads(
    model: RecurrentTransformerLearner,
    *,
    seed: int,
    worlds: int,
    items: int,
    depth: int,
    device: torch.device,
) -> list[dict[str, float | int]]:
    query_cosines: list[list[float]] = [[] for _ in range(depth)]
    read_cosines: list[list[float]] = [[] for _ in range(depth)]
    with torch.no_grad():
        for world in range(worlds):
            examples = memory_control_examples(
                "validation",
                seed * 10_007 + world,
                item_count=items,
            )
            weights, keys, _, _ = _write_control_memory(
                model,
                examples,
                device=device,
                oracle_content=True,
            )
            queries = tuple(query for _, query in examples)
            oracle = _oracle_contents(
                queries,
                width=model.memory_width,
                heads=model.memory_heads,
                device=device,
            )
            batch = batch_queries(queries, device=device)
            expanded = weights.expand(items, *([-1] * (weights.ndim - 1)))
            encoded = model.encode(batch.token_ids, lengths=batch.lengths)
            reasoning = model.reason(encoded, expanded, steps=depth)
            for index, step in enumerate(reasoning.steps):
                query_cosines[index].append(
                    float(F.cosine_similarity(step.query, keys, dim=-1).mean().cpu())
                )
                read_cosines[index].append(
                    float(F.cosine_similarity(step.memory_read, oracle, dim=-1).mean().cpu())
                )
    return [
        {
            "step": index + 1,
            "matched_key_cosine": sum(query_cosines[index]) / len(query_cosines[index]),
            "matched_read_cosine": sum(read_cosines[index]) / len(read_cosines[index]),
        }
        for index in range(depth)
    ]


def main() -> int:
    args = build_parser().parse_args()
    if not 1 <= args.max_depth <= 32:
        raise SystemExit("--max-depth must be in [1,32]")
    if not 1 <= args.worlds <= 64:
        raise SystemExit("--worlds must be in [1,64]")
    if not 1 <= args.trace_worlds <= args.worlds:
        raise SystemExit("--trace-worlds must be in [1,--worlds]")

    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but unavailable")

    model = RecurrentTransformerLearner().to(device)
    expected = {
        "checkpoint_role": "memory_positive_control",
        "control": "PC-W",
        "model": _model_config(model),
    }
    stored = inspect_checkpoint_config(args.checkpoint, max_bytes=MAX_CHECKPOINT_BYTES)
    if stored != expected:
        raise SystemExit("checkpoint is incompatible with the current transformer semantics")

    restored = load_scored_restart(
        args.checkpoint,
        _ControlTheta(model),
        model.writer,
        map_location=device,
        max_bytes=MAX_CHECKPOINT_BYTES,
        expected_config=expected,
    )
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)

    depths: list[dict[str, object]] = []
    for depth in range(1, args.max_depth + 1):
        pc_e = evaluate_memory_control(
            model,
            mode="encoder",
            worlds=args.worlds,
            item_count=args.items,
            seed=args.seed,
            device=device,
            reasoning_steps=depth,
        )
        pc_w = evaluate_memory_control(
            model,
            mode="writer",
            worlds=args.worlds,
            item_count=args.items,
            seed=args.seed,
            device=device,
            reasoning_steps=depth,
        )
        pc_e.pop("_restart_fixture", None)
        pc_w.pop("_restart_fixture", None)
        depths.append(
            {
                "depth": depth,
                "pc_e_exact_match_rate": pc_e["exact_match_rate"],
                "pc_e_no_w_exact_match_rate": pc_e["no_w_exact_match_rate"],
                "pc_e_memory_exact_match_gain": pc_e["memory_exact_match_gain"],
                "pc_w_exact_match_rate": pc_w["exact_match_rate"],
                "pc_w_no_w_exact_match_rate": pc_w["no_w_exact_match_rate"],
                "pc_w_memory_exact_match_gain": pc_w["memory_exact_match_gain"],
            }
        )

    payload = {
        "checkpoint": args.checkpoint,
        "reader_version": model.reader_version,
        "default_reasoning_steps": model.reasoning_steps,
        "workspace_is_none_after_restore": restored.workspace is None,
        "seed": args.seed,
        "worlds": args.worlds,
        "items": args.items,
        "depths": depths,
        "trace_worlds": args.trace_worlds,
        "trace_by_step": trace_reads(
            model,
            seed=args.seed,
            worlds=args.trace_worlds,
            items=args.items,
            depth=args.max_depth,
            device=device,
        ),
        "peak_cuda_memory_bytes": (
            int(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else None
        ),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
