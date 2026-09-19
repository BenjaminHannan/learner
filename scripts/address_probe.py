#!/usr/bin/env python3
"""Read-only PC-memory probe that separates address quality from decode quality."""

from __future__ import annotations

import argparse
import json

import torch

from memorylab.checkpoint import inspect_checkpoint_config, load_scored_restart
from memorylab.positive_controls import (
    _ControlTheta,
    _model_config,
    _write_control_memory,
    memory_control_examples,
)
from memorylab.tasks import batch_queries, decode_token_ids, normalize_text
from memorylab.transformer_model import RecurrentTransformerLearner


MAX_CHECKPOINT_BYTES = 64 * 1024 * 1024


def _rate(rows: list[bool]) -> float:
    return sum(rows) / len(rows) if rows else 0.0


def _generate_with_overrides(
    model: RecurrentTransformerLearner,
    token_ids: torch.Tensor,
    lengths: torch.Tensor,
    weights: torch.Tensor,
    keys: torch.Tensor,
    *,
    steps: int,
) -> torch.Tensor:
    encoded = model.encode(token_ids, lengths=lengths)
    overrides = {index: keys for index in range(steps)}
    reasoning = model.reason(
        encoded,
        weights,
        steps=steps,
        query_overrides=overrides,
    )
    return model.decode(
        encoded,
        reasoning,
        max_new_tokens=2,
        teacher_forcing=False,
    ).tokens


def evaluate_mode(
    model: RecurrentTransformerLearner,
    *,
    mode: str,
    seed: int,
    worlds: int,
    items: int,
    device: torch.device,
) -> dict[str, float | int]:
    normal_exact: list[bool] = []
    oracle_address_exact: list[bool] = []
    oracle_address_zero_w_exact: list[bool] = []
    first_query_cosines: list[float] = []

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
                oracle_content=mode == "encoder",
            )
            queries = tuple(query for _, query in examples)
            batch = batch_queries(queries, device=device)
            expanded = weights.expand(items, *([-1] * (weights.ndim - 1)))
            normal = model.generate(
                batch.token_ids,
                expanded,
                lengths=batch.lengths,
                max_new_tokens=2,
            )
            oracle_tokens = _generate_with_overrides(
                model,
                batch.token_ids,
                batch.lengths,
                expanded,
                keys,
                steps=model.reasoning_steps,
            )
            zero_tokens = _generate_with_overrides(
                model,
                batch.token_ids,
                batch.lengths,
                torch.zeros_like(expanded),
                keys,
                steps=model.reasoning_steps,
            )
            encoded = model.encode(batch.token_ids, lengths=batch.lengths)
            first_query = model.initial_memory_query(encoded)
            first_query_cosines.append(
                float(torch.nn.functional.cosine_similarity(first_query, keys, dim=-1).mean().cpu())
            )

            for index, query in enumerate(queries):
                expected = normalize_text(query.expected)
                normal_text = decode_token_ids(normal.decoding.tokens[index].cpu().tolist())
                oracle_text = decode_token_ids(oracle_tokens[index].cpu().tolist())
                zero_text = decode_token_ids(zero_tokens[index].cpu().tolist())
                normal_exact.append(normal_text == expected)
                oracle_address_exact.append(oracle_text == expected)
                oracle_address_zero_w_exact.append(zero_text == expected)

    return {
        "queries": len(normal_exact),
        "normal_exact_match_rate": _rate(normal_exact),
        "oracle_address_exact_match_rate": _rate(oracle_address_exact),
        "oracle_address_zero_w_exact_match_rate": _rate(oracle_address_zero_w_exact),
        "mean_first_query_to_writer_key_cosine": (
            sum(first_query_cosines) / len(first_query_cosines)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--worlds", type=int, default=16)
    parser.add_argument("--items", type=int, default=16)
    args = parser.parse_args()

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
    model.eval()

    payload = {
        "checkpoint": args.checkpoint,
        "reader_version": model.reader_version,
        "workspace_is_none_after_restore": restored.workspace is None,
        "pc_e": evaluate_mode(
            model,
            mode="encoder",
            seed=args.seed,
            worlds=args.worlds,
            items=args.items,
            device=device,
        ),
        "pc_w": evaluate_mode(
            model,
            mode="writer",
            seed=args.seed,
            worlds=args.worlds,
            items=args.items,
            device=device,
        ),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
