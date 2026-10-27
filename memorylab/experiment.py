"""Runnable meta-training and evaluation harness for the persistent learner."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import sys
import time
from typing import Any, Iterable, Optional

import torch
from torch import nn
from torch.nn import functional as F

from .checkpoint import (
    inspect_checkpoint_config,
    load_checkpoint,
    load_scored_restart,
    save_checkpoint,
)
from .model import MainNetwork, TokenSpec, unit
from .transformer_model import RecurrentTransformerLearner
from .positive_controls import (
    PC_C_THRESHOLD,
    PC_MEMORY_ITEMS,
    PC_R_THRESHOLD,
    run_memory_positive_controls,
    run_pc_c_control,
    run_pc_r_control,
)
from .tasks import (
    BOS,
    EOS,
    ID_TO_TOKEN,
    NAME_END,
    NAME_START,
    PAD,
    PAD_ID,
    Query,
    accepted_teaching,
    batch_queries,
    batch_query_targets,
    batch_teachings,
    generate_episode,
    relation_value_key_probe,
    support_query_for_teaching,
)


CHECKPOINT_MAX_BYTES = 64 * 1024 * 1024
RESULT_MAX_BYTES = 2 * 1024 * 1024
MAX_EVAL_WORLDS_PER_TIER = 64
MAX_RECORDED_TRAINING_ATTEMPTS = 128
TIER3_GATE_REASON = (
    "tier 3 persistent-memory training is gated until the implemented "
    "W-disabled PC-R in-context reader reaches its 0.95 validation threshold"
)


class _ThetaState(nn.Module):
    """Checkpoint view of theta that deliberately excludes writer phi."""

    def __init__(self, model: nn.Module) -> None:
        super().__init__()
        # Root-level tensors (the transformer's positions and memory-head
        # embeddings) are theta too; named_children() alone would silently
        # drop them from every checkpoint.
        for name, parameter in model.named_parameters(recurse=False):
            self.register_parameter(name, parameter)
        for name, buffer in model.named_buffers(recurse=False):
            self.register_buffer(
                name,
                buffer,
                persistent=name not in model._non_persistent_buffers_set,
            )
        for name, module in model.named_children():
            if name == "writer":
                continue
            self.add_module(name, module)


def model_config(model: nn.Module) -> dict[str, Any]:
    spec = model.token_spec
    common = {
        "architecture": type(model).__name__,
        "reasoning_steps": model.reasoning_steps,
        "max_reasoning_steps": model.max_reasoning_steps,
        "max_decode_len": model.max_decode_len,
        "token_spec": {
            "vocab_size": spec.vocab_size,
            "pad_id": spec.pad_id,
            "eos_id": spec.eos_id,
        },
    }
    if isinstance(model, RecurrentTransformerLearner):
        common.update({
            "model_width": model.model_width,
            "memory_width": model.memory_width,
            "memory_heads": model.memory_heads,
            "attention_heads": model.attention_heads,
            "ffn_width": model.ffn_width,
            "max_sequence_length": model.max_sequence_length,
            "reader_version": model.reader_version,
        })
    else:
        common.update({
            "embed_width": model.embed_width,
            "hidden_width": model.hidden_width,
        })
    return common


def _fresh_model_like(model: nn.Module) -> nn.Module:
    config = model_config(model)
    architecture = config.pop("architecture")
    spec_data = config.pop("token_spec")
    spec = TokenSpec(**spec_data)
    if architecture == "RecurrentTransformerLearner":
        config.pop("reader_version")
        return RecurrentTransformerLearner(token_spec=spec, **config)
    return MainNetwork(token_spec=spec, **config)


def _expand_memory(weights: torch.Tensor, batch: int) -> torch.Tensor:
    return weights.expand(batch, *([-1] * (weights.ndim - 1)))


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


def _checkpoint_limit(model: nn.Module) -> int:
    return 64 * 1024 * 1024 if isinstance(model, RecurrentTransformerLearner) else 16 * 1024 * 1024


def parse_tiers(value: str | Iterable[int]) -> tuple[int, ...]:
    if isinstance(value, str):
        try:
            tiers = tuple(int(part.strip()) for part in value.split(",") if part.strip())
        except ValueError as error:
            raise argparse.ArgumentTypeError(
                "tiers must be a comma-separated subset of 1,2,3"
            ) from error
    else:
        tiers = tuple(int(item) for item in value)
    if not tiers or any(tier not in (1, 2, 3) for tier in tiers):
        raise argparse.ArgumentTypeError("tiers must be a non-empty subset of 1,2,3")
    return tuple(dict.fromkeys(tiers))


def _select_device(requested: str) -> torch.device:
    if requested == "cpu":
        return torch.device("cpu")
    if requested == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was explicitly selected but is not available")
        return torch.device("cuda")
    raise ValueError("device must be 'cpu' or 'cuda'")


def _seed_everything(seed: int, device: torch.device) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(seed)


def _grad_norm(parameters: Iterable[torch.nn.Parameter]) -> float:
    total = 0.0
    for parameter in parameters:
        if parameter.grad is None:
            continue
        value = parameter.grad.detach().float()
        total += float(torch.sum(value * value).item())
    return math.sqrt(total)


def _memory_query_module(model: nn.Module) -> nn.Module:
    """Reader projection that turns the workspace into memory queries."""
    if isinstance(model, RecurrentTransformerLearner):
        return model.memory_query
    return model.query


def environment_report(device: torch.device) -> dict[str, Any]:
    """Software/device provenance recorded with every result."""
    report: dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "torch": torch.__version__,
        "cuda_build": torch.version.cuda,
        "cudnn": (
            torch.backends.cudnn.version()
            if torch.backends.cudnn.is_available()
            else None
        ),
        "device": str(device),
    }
    if device.type == "cuda":
        capability = torch.cuda.get_device_capability(device)
        arch_list = torch.cuda.get_arch_list()
        report.update(
            device_name=torch.cuda.get_device_name(device),
            compute_capability=list(capability),
            arch_list=arch_list,
            native_arch_compiled=f"sm_{capability[0]}{capability[1]}" in arch_list,
        )
    return report


def _per_example_nll(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """Mean non-padding token NLL for each batch item."""
    token_losses = F.cross_entropy(
        logits.reshape(-1, logits.shape[-1]),
        targets.reshape(-1),
        ignore_index=PAD_ID,
        reduction="none",
    ).reshape_as(targets)
    mask = targets.ne(PAD_ID)
    counts = mask.sum(dim=-1).clamp_min(1)
    return (token_losses * mask).sum(dim=-1) / counts


def _initial_memory_cue(model: MainNetwork, query: Query, device: torch.device) -> torch.Tensor:
    """Compute q(x,z0) for an evaluator-paired text without reading W."""
    batch = batch_queries([query], device=device)
    encoded = model.encode(batch.token_ids, lengths=batch.lengths)
    return model.initial_memory_query(encoded)


def _symmetric_contrastive_alignment(
    keys: torch.Tensor,
    cues: torch.Tensor,
    *,
    temperature: float = 0.07,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Align matched addresses while explicitly rejecting collapsed keys.

    Positive-only cosine alignment admits the degenerate solution in which
    every fact uses one address.  This in-batch objective makes every other
    distinct fact a negative in both directions.  Corrections are deduplicated
    by support-query text before this helper is called, so two versions of the
    same fact are never treated as negatives.
    """
    if keys.ndim != 2 or cues.shape != keys.shape or keys.shape[0] == 0:
        raise ValueError("contrastive keys and cues must share non-empty [items,width] shape")
    if temperature <= 0:
        raise ValueError("contrastive temperature must be positive")
    keys = unit(keys)
    cues = unit(cues)
    matched = F.cosine_similarity(keys, cues, dim=-1, eps=1e-8).mean()
    if keys.shape[0] == 1:
        zero = matched.new_zeros(())
        return 1.0 - matched, matched, zero
    logits = torch.matmul(keys, cues.transpose(0, 1)) / temperature
    labels = torch.arange(keys.shape[0], device=keys.device)
    loss = 0.5 * (
        F.cross_entropy(logits, labels)
        + F.cross_entropy(logits.transpose(0, 1), labels)
    )
    diagonal = torch.eye(keys.shape[0], dtype=torch.bool, device=keys.device)
    max_off_diagonal = torch.matmul(keys, keys.transpose(0, 1)).masked_fill(
        diagonal, -1.0
    ).max()
    return loss, matched, max_off_diagonal


def _key_orthogonality_loss(keys: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    if keys.ndim == 2:
        keys = keys.unsqueeze(1)
    if keys.ndim != 3 or keys.shape[0] == 0:
        raise ValueError("keys must have [items,width] or [items,heads,width] shape")
    keys = unit(keys)
    if keys.shape[0] == 1:
        zero = keys.new_zeros(())
        return zero, zero
    gram = torch.einsum("ihd,jhd->hij", keys, keys)
    eye = torch.eye(keys.shape[0], dtype=torch.bool, device=keys.device).unsqueeze(0)
    off_diagonal = gram.masked_select(~eye.expand_as(gram))
    return off_diagonal.square().mean(), off_diagonal.abs().max()


def apply_teachings(
    model: MainNetwork,
    teachings: Iterable[Any],
    *,
    device: torch.device | str,
    track_grad: bool,
) -> torch.Tensor:
    """Start W at zero and functionally apply every accepted teaching."""
    device = torch.device(device)
    weights = model.new_memory(batch=1, device=device)
    context = torch.enable_grad() if track_grad else torch.no_grad()
    with context:
        for teaching in teachings:
            feedback = accepted_teaching(teaching)
            if not feedback.accepted:
                continue
            batch = batch_teachings([teaching], device=device)
            weights = model.write_from_teaching(
                batch.token_ids,
                weights,
                lengths=batch.lengths,
            ).weights
    return weights


def meta_train_episode(
    model: MainNetwork,
    episode: Any,
    optimizer: torch.optim.Optimizer,
    *,
    device: torch.device | str = "cpu",
    grad_clip: float = 1.0,
    support_loss_weight: float = 0.5,
    memory_contrast_weight: float = 1.0,
    memory_margin: float = 0.5,
    key_alignment_weight: float = 1.0,
    key_orthogonality_weight: float = 5.0,
    value_key_alignment_weight: float = 1.0,
) -> dict[str, Any]:
    """Run one real differentiable meta-training episode."""
    if episode.split != "train":
        raise ValueError("Meta-training is restricted to split=train")
    if grad_clip <= 0:
        raise ValueError("grad_clip must be positive")
    if support_loss_weight < 0:
        raise ValueError("support_loss_weight must be nonnegative")
    if memory_contrast_weight < 0 or memory_margin < 0:
        raise ValueError("memory contrast weight and margin must be nonnegative")
    if (
        key_alignment_weight < 0
        or key_orthogonality_weight < 0
        or value_key_alignment_weight < 0
    ):
        raise ValueError("key alignment weights must be nonnegative")
    device = torch.device(device)
    model.train()
    optimizer.zero_grad(set_to_none=True)

    weights = model.new_memory(batch=1, device=device)
    support_losses: list[torch.Tensor] = []
    # Latest version wins: using the support text as the identity keeps a
    # correction and its superseded value from becoming false negatives.
    key_alignment_pairs: dict[str, tuple[torch.Tensor, torch.Tensor]] = {}
    value_key_alignment_losses: list[torch.Tensor] = []
    for teaching in episode.teachings:
        feedback = accepted_teaching(teaching)
        if not feedback.accepted:
            continue
        teaching_batch = batch_teachings([teaching], device=device)
        write = model.write_from_teaching(
            teaching_batch.token_ids,
            weights,
            lengths=teaching_batch.lengths,
        )
        weights = write.weights
        support = support_query_for_teaching(teaching)
        if support is not None:
            if key_alignment_weight > 0.0:
                support_cue = _initial_memory_cue(model, support, device)
                key_alignment_pairs[support.text] = (
                    write.writer.key.squeeze(0),
                    support_cue.squeeze(0),
                )
            probe = relation_value_key_probe(teaching)
            if probe is not None and value_key_alignment_weight > 0.0:
                next_cue = _initial_memory_cue(model, probe, device)
                value_key_alignment_losses.append(
                    1.0
                    - F.cosine_similarity(
                        write.writer.value,
                        next_cue,
                        dim=-1,
                        eps=1e-8,
                    ).mean()
                )
        if support is not None and support_loss_weight > 0.0:
            support_batch = batch_queries([support], device=device)
            support_targets = batch_query_targets([support], device=device)
            support_output = model(
                support_batch.token_ids,
                weights,
                targets=support_targets.token_ids,
                lengths=support_batch.lengths,
                teacher_forcing=True,
            )
            support_logits = support_output.decoding.logits
            support_losses.append(
                F.cross_entropy(
                    support_logits.reshape(-1, support_logits.shape[-1]),
                    support_targets.token_ids.reshape(-1),
                    ignore_index=PAD_ID,
                )
            )
    queries = batch_queries(episode.queries, device=device)
    targets = batch_query_targets(episode.queries, device=device)
    expanded_weights = _expand_memory(weights, len(episode.queries))
    output = model(
        queries.token_ids,
        expanded_weights,
        targets=targets.token_ids,
        lengths=queries.lengths,
        teacher_forcing=True,
    )
    logits = output.decoding.logits
    query_loss = F.cross_entropy(
        logits.reshape(-1, logits.shape[-1]),
        targets.token_ids.reshape(-1),
        ignore_index=PAD_ID,
    )
    support_loss = (
        torch.stack(support_losses).mean()
        if support_losses
        else query_loss.new_zeros(())
    )
    if key_alignment_pairs:
        alignment_keys = torch.stack(
            [pair[0] for pair in key_alignment_pairs.values()]
        )
        alignment_cues = torch.stack(
            [pair[1] for pair in key_alignment_pairs.values()]
        )
        (
            key_alignment_loss,
            key_alignment_matched_cosine,
            _,
        ) = _symmetric_contrastive_alignment(
            alignment_keys.flatten(1),
            alignment_cues.flatten(1),
        )
        key_orthogonality_loss, key_alignment_max_off_diagonal = (
            _key_orthogonality_loss(alignment_keys)
        )
    else:
        key_alignment_loss = query_loss.new_zeros(())
        key_orthogonality_loss = query_loss.new_zeros(())
        key_alignment_matched_cosine = query_loss.new_zeros(())
        key_alignment_max_off_diagonal = query_loss.new_zeros(())
    value_key_alignment_loss = (
        torch.stack(value_key_alignment_losses).mean()
        if value_key_alignment_losses
        else query_loss.new_zeros(())
    )
    zero_output = model(
        queries.token_ids,
        torch.zeros_like(expanded_weights),
        targets=targets.token_ids,
        lengths=queries.lengths,
        teacher_forcing=True,
    )
    with_w_nll = _per_example_nll(logits, targets.token_ids)
    no_w_nll = _per_example_nll(zero_output.decoding.logits, targets.token_ids)
    memory_dependent = torch.tensor(
        [query.purpose != "unknown_control" for query in episode.queries],
        dtype=torch.bool,
        device=device,
    )
    if bool(memory_dependent.any().item()):
        target_advantage = no_w_nll[memory_dependent] - with_w_nll[memory_dependent]
        memory_margin_loss = F.relu(memory_margin - target_advantage).mean()
        mean_target_advantage = target_advantage.mean()
    else:
        memory_margin_loss = query_loss.new_zeros(())
        mean_target_advantage = query_loss.new_zeros(())
    loss = (
        query_loss
        + support_loss_weight * support_loss
        + memory_contrast_weight * memory_margin_loss
        + key_alignment_weight * key_alignment_loss
        + key_orthogonality_weight * key_orthogonality_loss
        + value_key_alignment_weight * value_key_alignment_loss
    )
    loss.backward()

    writer_grad_norm = _grad_norm(model.writer.parameters())
    memory_query_grad_norm = _grad_norm(_memory_query_module(model).parameters())
    encoder_module = model.encoder if hasattr(model, "encoder") else model.prelude
    encoder_grad_norm = _grad_norm(
        list(model.embedding.parameters()) + list(encoder_module.parameters())
    )
    total_grad_norm = float(
        torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip).detach().cpu().item()
    )
    optimizer.step()
    return {
        "seed": episode.seed,
        "episode": episode.episode,
        "tier": episode.tier,
        "loss": float(loss.detach().cpu().item()),
        "query_loss": float(query_loss.detach().cpu().item()),
        "support_loss": float(support_loss.detach().cpu().item()),
        "support_queries": len(support_losses),
        "support_loss_weight": support_loss_weight,
        "no_w_query_loss": float(no_w_nll.mean().detach().cpu().item()),
        "memory_margin_loss": float(memory_margin_loss.detach().cpu().item()),
        "memory_target_nll_advantage": float(
            mean_target_advantage.detach().cpu().item()
        ),
        "memory_contrast_weight": memory_contrast_weight,
        "memory_margin": memory_margin,
        "key_alignment_loss": float(key_alignment_loss.detach().cpu().item()),
        "key_alignment_pairs": len(key_alignment_pairs),
        "key_alignment_matched_cosine": float(
            key_alignment_matched_cosine.detach().cpu().item()
        ),
        "key_alignment_max_off_diagonal": float(
            key_alignment_max_off_diagonal.detach().cpu().item()
        ),
        "key_alignment_weight": key_alignment_weight,
        "key_orthogonality_loss": float(
            key_orthogonality_loss.detach().cpu().item()
        ),
        "key_orthogonality_weight": key_orthogonality_weight,
        "value_key_alignment_loss": float(
            value_key_alignment_loss.detach().cpu().item()
        ),
        "value_key_alignment_weight": value_key_alignment_weight,
        "writer_grad_norm": writer_grad_norm,
        "encoder_grad_norm": encoder_grad_norm,
        "memory_query_grad_norm": memory_query_grad_norm,
        "preclip_grad_norm": total_grad_norm,
        "w_change_norm": float(torch.linalg.vector_norm(weights.detach()).cpu().item()),
    }


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def decode_token_ids(token_ids: Iterable[int]) -> str:
    pieces: list[str] = []
    name_chars: list[str] = []
    in_name = False
    for raw_id in token_ids:
        token = ID_TO_TOKEN.get(int(raw_id), "<invalid>")
        if token == EOS:
            break
        if token in (PAD, BOS):
            continue
        if token == NAME_START:
            if in_name and name_chars:
                pieces.append("".join(name_chars))
            in_name = True
            name_chars = []
            continue
        if token == NAME_END:
            if in_name:
                pieces.append("".join(name_chars))
            in_name = False
            name_chars = []
            continue
        if in_name and token.startswith("@") and len(token) == 2:
            name_chars.append(token[1])
            continue
        if in_name:
            if name_chars:
                pieces.append("".join(name_chars))
            in_name = False
            name_chars = []
        pieces.append(token)
    if in_name and name_chars:
        pieces.append("".join(name_chars))
    return normalize_text(" ".join(pieces))


def causal_generate(
    model: MainNetwork,
    query: Query,
    weights: torch.Tensor,
    *,
    device: torch.device | str = "cpu",
) -> dict[str, Any]:
    """Generate with learned W and with W zeroed, changing only the memory read."""
    device = torch.device(device)
    batch = batch_queries([query], device=device)
    zero_weights = torch.zeros_like(weights)
    with torch.no_grad():
        with_w = model.generate(batch.token_ids, weights, lengths=batch.lengths)
        no_w = model.generate(batch.token_ids, zero_weights, lengths=batch.lengths)

    with_tokens = with_w.decoding.tokens[0].detach().cpu().tolist()
    no_w_tokens = no_w.decoding.tokens[0].detach().cpu().tolist()
    generated = decode_token_ids(with_tokens)
    no_w_generated = decode_token_ids(no_w_tokens)
    expected = normalize_text(query.expected)
    first_step_delta = float(
        (with_w.decoding.logits[0, 0] - no_w.decoding.logits[0, 0])
        .abs()
        .max()
        .detach()
        .cpu()
        .item()
    )
    return {
        "query": query.text,
        "expected": expected,
        "generated": generated,
        "no_w_generated": no_w_generated,
        "exact_match": generated == expected,
        "no_w_exact_match": no_w_generated == expected,
        "tokens": with_tokens,
        "no_w_tokens": no_w_tokens,
        "token_output_changed": with_tokens != no_w_tokens,
        "first_step_logit_max_abs_delta": first_step_delta,
    }


def _episode_index(seed: int, tier: int, ordinal: int) -> int:
    base = (abs(seed) * 1009 + tier * 100_003) % 900_000
    return (base + ordinal) % 1_000_000


def _summarize_query_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    exact = sum(bool(record["exact_match"]) for record in records)
    no_w_exact = sum(bool(record["no_w_exact_match"]) for record in records)
    changed = sum(bool(record["token_output_changed"]) for record in records)
    causal = sum(record["first_step_logit_max_abs_delta"] > 0.0 for record in records)
    with_w_only = sum(
        bool(record["exact_match"]) and not bool(record["no_w_exact_match"])
        for record in records
    )
    no_w_only = sum(
        bool(record["no_w_exact_match"]) and not bool(record["exact_match"])
        for record in records
    )
    return {
        "queries": total,
        "exact_matches": exact,
        "exact_match_rate": exact / total if total else 0.0,
        "no_w_exact_matches": no_w_exact,
        "no_w_exact_match_rate": no_w_exact / total if total else 0.0,
        "token_output_changes": changed,
        "positive_logit_causal_deltas": causal,
        "with_w_only_exact_matches": with_w_only,
        "no_w_only_exact_matches": no_w_only,
        "memory_exact_match_gain": (
            (exact - no_w_exact) / total if total else 0.0
        ),
    }


def evaluate_model(
    model: MainNetwork,
    *,
    split: str,
    tiers: tuple[int, ...],
    worlds_per_tier: int,
    seed: int,
    device: torch.device | str = "cpu",
    deadline: Optional[float] = None,
) -> tuple[dict[str, Any], Optional[dict[str, Any]], bool]:
    if split not in ("validation", "test"):
        raise ValueError("Evaluation is restricted to validation/test splits")
    if not 1 <= worlds_per_tier <= MAX_EVAL_WORLDS_PER_TIER:
        raise ValueError(f"worlds_per_tier must be in [1,{MAX_EVAL_WORLDS_PER_TIER}]")

    device = torch.device(device)
    model.eval()
    active_tiers = tuple(tier for tier in tiers if tier in (1, 2))
    report: dict[str, Any] = {
        "split": split,
        "worlds_per_tier": worlds_per_tier,
        "tiers": {},
        "worlds": [],
        "tier3_gate": {
            "implemented": False,
            "pc_r_implemented": True,
            "status": "gated",
            "reason": TIER3_GATE_REASON,
        },
    }
    if 3 in tiers:
        report["tiers"]["3"] = {
            "status": "gated",
            "reason": TIER3_GATE_REASON,
            "queries": 0,
        }

    restart_candidate: Optional[dict[str, Any]] = None
    timed_out = False
    for tier in active_tiers:
        tier_records: list[dict[str, Any]] = []
        purpose_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
        w_norms: list[float] = []
        tier_worlds = 0
        for ordinal in range(worlds_per_tier):
            if deadline is not None and time.monotonic() >= deadline:
                timed_out = True
                break
            episode_index = _episode_index(seed, tier, ordinal)
            episode = generate_episode(split, episode_index, tier=tier)
            weights = apply_teachings(model, episode.teachings, device=device, track_grad=False)
            w_norm = float(torch.linalg.vector_norm(weights).cpu().item())
            w_norms.append(w_norm)
            world: dict[str, Any] = {
                "seed": episode.seed,
                "episode": episode.episode,
                "tier": tier,
                "w_change_norm": w_norm,
                "queries": [],
            }
            for query in episode.queries:
                if deadline is not None and time.monotonic() >= deadline:
                    timed_out = True
                    break
                record = causal_generate(model, query, weights, device=device)
                record["purpose"] = query.purpose
                record["tier"] = query.tier
                world["queries"].append(record)
                tier_records.append(record)
                purpose_records[query.purpose].append(record)
                if restart_candidate is None:
                    restart_candidate = {
                        "weights": weights.detach().clone(),
                        "query": query,
                        "tokens": list(record["tokens"]),
                        "seed": episode.seed,
                        "tier": tier,
                    }
            report["worlds"].append(world)
            tier_worlds += 1
            if timed_out:
                break
        summary = _summarize_query_records(tier_records)
        summary.update(
            status="evaluated",
            worlds=tier_worlds,
            w_change_norms=w_norms,
            purposes={
                purpose: _summarize_query_records(records)
                for purpose, records in sorted(purpose_records.items())
            },
        )
        report["tiers"][str(tier)] = summary
        if timed_out:
            break

    all_records = [
        query
        for world in report["worlds"]
        for query in world["queries"]
    ]
    all_w_norms = [float(world["w_change_norm"]) for world in report["worlds"]]
    report["overall"] = _summarize_query_records(all_records)
    report["overall"]["all_exact"] = bool(all_records) and all(
        bool(record["exact_match"]) for record in all_records
    )
    report["w_change_norm"] = {
        "values": all_w_norms,
        "mean": sum(all_w_norms) / len(all_w_norms) if all_w_norms else 0.0,
        "min": min(all_w_norms) if all_w_norms else 0.0,
        "max": max(all_w_norms) if all_w_norms else 0.0,
    }
    return report, restart_candidate, timed_out


def restart_identity_check(
    model: MainNetwork,
    candidate: dict[str, Any],
    *,
    budget: Any,
    device: torch.device | str,
    artifact_name: str,
) -> dict[str, Any]:
    """Persist theta/phi/W, restore a fresh object, and compare greedy tokens."""
    device = torch.device(device)
    weights = candidate["weights"]
    expected_shape = tuple(model.new_memory(batch=1, device=device).shape)
    if tuple(weights.shape) != expected_shape:
        raise ValueError(
            f"checkpoint restart requires model memory shape {expected_shape}"
        )
    checkpoint_path = save_checkpoint(
        budget,
        artifact_name,
        _ThetaState(model),
        model.writer,
        weights[0],
        config={"model": model_config(model)},
        max_bytes=_checkpoint_limit(model),
    )

    fresh = _fresh_model_like(model).to(device)
    fresh.eval()
    restart = load_scored_restart(
        checkpoint_path,
        _ThetaState(fresh),
        fresh.writer,
        map_location=device,
        max_bytes=_checkpoint_limit(fresh),
        expected_config={"model": model_config(fresh)},
    )
    query = candidate["query"]
    batch = batch_queries([query], device=device)
    with torch.no_grad():
        before = model.generate(batch.token_ids, weights, lengths=batch.lengths)
        after = fresh.generate(
            batch.token_ids,
            restart.W.unsqueeze(0),
            lengths=batch.lengths,
        )
    before_tokens = before.decoding.tokens[0].detach().cpu().tolist()
    after_tokens = after.decoding.tokens[0].detach().cpu().tolist()
    # Greedy tokens alone pass vacuously for a degenerate model; the restored
    # object must reproduce the exact logits bit for bit.
    identical_logits = bool(torch.equal(before.decoding.logits, after.decoding.logits))
    logits_max_abs_diff = float(
        (before.decoding.logits - after.decoding.logits).abs().max().cpu().item()
    )
    try:
        relative = str(Path(checkpoint_path).resolve().relative_to(Path(budget.root).resolve()))
    except (AttributeError, ValueError):
        relative = str(checkpoint_path)
    return {
        "checkpoint": relative,
        "seed": candidate["seed"],
        "tier": candidate["tier"],
        "workspace_is_none": restart.workspace is None,
        "tokens_before": before_tokens,
        "tokens_after": after_tokens,
        "identical_tokens": before_tokens == after_tokens,
        "identical_logits": identical_logits,
        "logits_max_abs_diff": logits_max_abs_diff,
    }


def _training_summary(
    attempts: list[dict[str, Any]],
    max_steps: int,
    max_seconds: float,
) -> dict[str, Any]:
    by_tier: dict[str, Any] = {}
    for tier in sorted({attempt["tier"] for attempt in attempts}):
        rows = [attempt for attempt in attempts if attempt["tier"] == tier]
        by_tier[str(tier)] = {
            "steps": len(rows),
            "mean_loss": sum(row["loss"] for row in rows) / len(rows),
            "writer_grad_norms": [row["writer_grad_norm"] for row in rows],
            "encoder_grad_norms": [row["encoder_grad_norm"] for row in rows],
        }
    if len(attempts) <= MAX_RECORDED_TRAINING_ATTEMPTS:
        recorded_attempts = attempts
    else:
        half = MAX_RECORDED_TRAINING_ATTEMPTS // 2
        recorded_attempts = attempts[:half] + attempts[-half:]
    return {
        "optimizer": "AdamW",
        "steps_completed": len(attempts),
        "max_optimizer_steps": max_steps,
        "max_seconds": max_seconds,
        "attempts": recorded_attempts,
        "attempts_recorded": len(recorded_attempts),
        "attempts_truncated": len(recorded_attempts) != len(attempts),
        "tiers": by_tier,
    }


def _evaluation_reserve(max_seconds: float, command: str) -> float:
    """Reserve part of a bounded train run for evaluation and restart checks."""
    if command == "evaluate":
        return 0.0
    # Ten seconds is enough for the tiny smoke harness on the reference CPU;
    # longer pilots reserve one quarter of the run.  The half-run ceiling keeps
    # very short explicit runs useful for at least one optimizer step.
    return min(max(10.0, max_seconds * 0.25), max_seconds * 0.5)


def _training_checkpoint_reserve(command: str, model: nn.Module) -> float:
    """Reserve measured recovery-checkpoint time for full transformer pilots.

    On BensPC, the selected 4.84M-parameter transformer's AdamW recovery
    checkpoint is about 58 MiB and its serialization/hash step can consume
    roughly two minutes. Without a separate reserve, a measured 300 s pilot
    ran for 346.7 s and exhausted the evaluation window before scoring.

    Keep this evidence-based reserve scoped to the selected full transformer;
    the small test fixtures and GRU checkpoints do not show this bottleneck.
    """
    if (
        command == "pilot"
        and isinstance(model, RecurrentTransformerLearner)
        and parameter_count(model) >= 4_000_000
    ):
        return 120.0
    return 0.0


def _training_checkpoint_config(
    *,
    model: MainNetwork,
    seed: int,
    tiers: tuple[int, ...],
    learning_rate: float,
    grad_clip: float,
    support_loss_weight: float,
    memory_contrast_weight: float,
    memory_margin: float,
    key_alignment_weight: float,
    key_orthogonality_weight: float,
    value_key_alignment_weight: float,
    global_step: int,
) -> dict[str, Any]:
    return {
        "checkpoint_role": "meta_training",
        "model": model_config(model),
        "training": {
            "seed": seed,
            "tiers": list(tiers),
            "learning_rate": learning_rate,
            "grad_clip": grad_clip,
            "support_loss_weight": support_loss_weight,
            "memory_contrast_weight": memory_contrast_weight,
            "memory_margin": memory_margin,
            "key_alignment_weight": key_alignment_weight,
            "key_orthogonality_weight": key_orthogonality_weight,
            "value_key_alignment_weight": value_key_alignment_weight,
            "global_step": global_step,
        },
    }


def _validate_training_checkpoint_config(
    stored: dict[str, Any],
    *,
    model: MainNetwork,
    expected_training: Optional[dict[str, Any]] = None,
) -> int:
    """Validate semantic compatibility and return the saved episode cursor."""
    if set(stored) != {"checkpoint_role", "model", "training"}:
        raise ValueError("Training checkpoint config has unexpected fields")
    if stored["checkpoint_role"] != "meta_training":
        raise ValueError("Checkpoint is not a meta-training recovery checkpoint")
    if stored["model"] != model_config(model):
        raise ValueError("Checkpoint model configuration is incompatible")
    training = stored["training"]
    if not isinstance(training, dict):
        raise ValueError("Training checkpoint metadata is malformed")
    global_step = training.get("global_step")
    if isinstance(global_step, bool) or not isinstance(global_step, int) or global_step < 0:
        raise ValueError("Training checkpoint global_step is invalid")
    if expected_training is not None:
        observed = dict(training)
        observed.pop("global_step", None)
        if observed != expected_training:
            raise ValueError("Resume settings do not match the training checkpoint")
    return global_step


def run_experiment(
    command: str,
    budget: Any,
    *,
    seed: int = 0,
    device: str = "cpu",
    tiers: tuple[int, ...] | str | None = None,
    steps: Optional[int] = None,
    seconds: Optional[float] = None,
    eval_split: str = "validation",
    eval_worlds: Optional[int] = None,
    learning_rate: float = 3e-4,
    grad_clip: float = 1.0,
    support_loss_weight: float = 0.5,
    memory_contrast_weight: float = 1.0,
    memory_margin: float = 0.5,
    key_alignment_weight: float = 1.0,
    key_orthogonality_weight: float = 5.0,
    value_key_alignment_weight: float = 1.0,
    backbone: str = "gru",
    resume_checkpoint: Optional[str | Path] = None,
    checkpoint: Optional[str | Path] = None,
    model: Optional[nn.Module] = None,
    save_result: bool = True,
    emit_model: bool = False,
) -> dict[str, Any]:
    """Execute exactly one smoke, pilot, or evaluate command."""
    defaults = {
        "smoke": {"tiers": (1,), "steps": 2, "seconds": 30.0, "eval_worlds": 1},
        "pilot": {"tiers": (1, 2), "steps": 10_000, "seconds": 480.0, "eval_worlds": 4},
        "evaluate": {"tiers": (1, 2), "steps": 0, "seconds": 60.0, "eval_worlds": 2},
    }
    if command not in defaults:
        raise ValueError("command must be smoke, pilot, or evaluate")
    settings = defaults[command]
    selected_tiers = parse_tiers(settings["tiers"] if tiers is None else tiers)
    max_steps = settings["steps"] if steps is None else int(steps)
    max_seconds = settings["seconds"] if seconds is None else float(seconds)
    worlds_per_tier = settings["eval_worlds"] if eval_worlds is None else int(eval_worlds)
    if max_seconds <= 0:
        raise ValueError("seconds must be positive")
    if command == "pilot" and max_seconds > 600:
        raise ValueError("pilot seconds must be <= 600")
    if command == "smoke" and not 1 <= max_steps <= 3:
        raise ValueError("smoke steps must be in [1,3]")
    if command == "pilot" and max_steps <= 0:
        raise ValueError("pilot steps must be positive")
    if command == "evaluate" and max_steps != 0:
        raise ValueError("evaluate performs no optimizer steps")
    if learning_rate <= 0 or grad_clip <= 0:
        raise ValueError("learning_rate and grad_clip must be positive")
    if support_loss_weight < 0:
        raise ValueError("support_loss_weight must be nonnegative")
    if memory_contrast_weight < 0 or memory_margin < 0:
        raise ValueError("memory contrast weight and margin must be nonnegative")
    if (
        key_alignment_weight < 0
        or key_orthogonality_weight < 0
        or value_key_alignment_weight < 0
    ):
        raise ValueError("key alignment weights must be nonnegative")
    if not 1 <= worlds_per_tier <= MAX_EVAL_WORLDS_PER_TIER:
        raise ValueError(f"eval_worlds must be in [1,{MAX_EVAL_WORLDS_PER_TIER}]")
    if eval_split not in ("validation", "test"):
        raise ValueError("eval_split must be validation or test")
    if backbone not in ("gru", "transformer"):
        raise ValueError("backbone must be gru or transformer")
    if command == "evaluate" and checkpoint is None:
        raise ValueError("evaluate requires a meta-training --checkpoint")
    if command == "evaluate" and resume_checkpoint is not None:
        raise ValueError("evaluate does not accept resume_checkpoint")
    if command != "evaluate" and checkpoint is not None:
        raise ValueError("checkpoint is only valid for evaluate")

    started = time.monotonic()
    torch_device = _select_device(device)
    _seed_everything(seed, torch_device)
    if torch_device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(torch_device)
    if model is None:
        model = MainNetwork() if backbone == "gru" else RecurrentTransformerLearner()
    else:
        observed_backbone = (
            "transformer" if isinstance(model, RecurrentTransformerLearner) else "gru"
        )
        if backbone != "gru" and backbone != observed_backbone:
            raise ValueError("explicit model and backbone disagree")
        backbone = observed_backbone
    model = model.to(torch_device)
    config = model_config(model)
    loaded_checkpoint: Optional[dict[str, Any]] = None
    if command == "evaluate":
        stored = inspect_checkpoint_config(
            checkpoint,
            max_bytes=CHECKPOINT_MAX_BYTES,
        )
        global_step = _validate_training_checkpoint_config(stored, model=model)
        restored = load_scored_restart(
            checkpoint,
            _ThetaState(model),
            model.writer,
            map_location=torch_device,
            max_bytes=CHECKPOINT_MAX_BYTES,
            expected_config=stored,
        )
        if bool(torch.count_nonzero(restored.W).item()):
            raise ValueError("Meta-training recovery checkpoint W must be exactly zero")
        loaded_checkpoint = {
            "path": str(checkpoint),
            "global_step": global_step,
            "workspace_is_none": restored.workspace is None,
        }
    params = parameter_count(model)
    trainable = sum(
        parameter.numel() for parameter in model.parameters() if parameter.requires_grad
    )
    if emit_model:
        print(
            "model "
            + json.dumps(
                {
                    "parameter_count": params,
                    "trainable_parameter_count": trainable,
                    "config": config,
                    "device": str(torch_device),
                },
                sort_keys=True,
            )
        )

    stamp = f"{command}-{seed}-{time.time_ns()}-{os.getpid()}"
    deadline = started + max_seconds
    evaluation_reserve = _evaluation_reserve(max_seconds, command)
    checkpoint_reserve = _training_checkpoint_reserve(command, model)
    training_deadline = deadline - evaluation_reserve - checkpoint_reserve
    attempts: list[dict[str, Any]] = []
    timed_out = False
    training_time_limit_reached = False
    resume_step = 0
    optimizer: Optional[torch.optim.Optimizer] = None
    active_train_tiers = tuple(tier for tier in selected_tiers if tier in (1, 2))
    if command in ("smoke", "pilot"):
        optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
        if resume_checkpoint is not None:
            stored = inspect_checkpoint_config(
                resume_checkpoint,
                max_bytes=CHECKPOINT_MAX_BYTES,
            )
            expected_training = {
                "seed": seed,
                "tiers": list(active_train_tiers),
                "learning_rate": learning_rate,
                "grad_clip": grad_clip,
                "support_loss_weight": support_loss_weight,
                "memory_contrast_weight": memory_contrast_weight,
                "memory_margin": memory_margin,
                "key_alignment_weight": key_alignment_weight,
                "key_orthogonality_weight": key_orthogonality_weight,
                "value_key_alignment_weight": value_key_alignment_weight,
            }
            resume_step = _validate_training_checkpoint_config(
                stored,
                model=model,
                expected_training=expected_training,
            )
            restored = load_checkpoint(
                resume_checkpoint,
                _ThetaState(model),
                model.writer,
                optimizer=optimizer,
                map_location=torch_device,
                restore_rng=True,
                max_bytes=CHECKPOINT_MAX_BYTES,
                expected_config=stored,
            )
            if bool(torch.count_nonzero(restored.W).item()):
                raise ValueError("Meta-training recovery checkpoint W must be exactly zero")
            loaded_checkpoint = {
                "path": str(resume_checkpoint),
                "global_step": resume_step,
                "workspace_is_none": restored.workspace is None,
            }
        if active_train_tiers:
            for step_index in range(max_steps):
                if time.monotonic() >= training_deadline:
                    training_time_limit_reached = True
                    break
                global_step = resume_step + step_index
                tier = active_train_tiers[global_step % len(active_train_tiers)]
                episode = generate_episode(
                    "train",
                    _episode_index(seed, tier, global_step),
                    tier=tier,
                )
                attempts.append(
                    meta_train_episode(
                        model,
                        episode,
                        optimizer,
                        device=torch_device,
                        grad_clip=grad_clip,
                        support_loss_weight=support_loss_weight,
                        memory_contrast_weight=memory_contrast_weight,
                        memory_margin=memory_margin,
                        key_alignment_weight=key_alignment_weight,
                        key_orthogonality_weight=key_orthogonality_weight,
                        value_key_alignment_weight=value_key_alignment_weight,
                    )
                )
                if time.monotonic() >= training_deadline and step_index + 1 < max_steps:
                    training_time_limit_reached = True
                    break

    training = _training_summary(attempts, max_steps, max_seconds)
    training["wall_clock_seconds_budget"] = max(
        0.0,
        max_seconds - evaluation_reserve - checkpoint_reserve,
    )
    training["evaluation_reserve_seconds"] = evaluation_reserve
    training["checkpoint_reserve_seconds"] = checkpoint_reserve
    training["global_step_start"] = resume_step
    training["global_step_end"] = resume_step + len(attempts)
    if command == "evaluate":
        training["stop_reason"] = "not_applicable"
    elif not active_train_tiers:
        training["stop_reason"] = "no_ungated_training_tiers"
    elif training_time_limit_reached:
        training["stop_reason"] = "training_time_budget"
    else:
        training["stop_reason"] = "max_steps"
    training["tier3_gate"] = {
        "implemented": False,
        "pc_r_implemented": True,
        "requested": 3 in selected_tiers,
        "reason": TIER3_GATE_REASON,
    }

    training_checkpoint_report: Optional[dict[str, Any]] = None
    if command in ("smoke", "pilot") and optimizer is not None and attempts:
        recovery_config = _training_checkpoint_config(
            model=model,
            seed=seed,
            tiers=active_train_tiers,
            learning_rate=learning_rate,
            grad_clip=grad_clip,
            support_loss_weight=support_loss_weight,
            memory_contrast_weight=memory_contrast_weight,
            memory_margin=memory_margin,
            key_alignment_weight=key_alignment_weight,
            key_orthogonality_weight=key_orthogonality_weight,
            value_key_alignment_weight=value_key_alignment_weight,
            global_step=resume_step + len(attempts),
        )
        recovery_path = save_checkpoint(
            budget,
            f"artifacts/training-{stamp}.mlckpt",
            _ThetaState(model),
            model.writer,
            model.new_memory(batch=1, device=torch_device)[0],
            optimizer=optimizer,
            config=recovery_config,
            max_bytes=_checkpoint_limit(model),
        )
        try:
            recovery_relative = str(
                Path(recovery_path).resolve().relative_to(Path(budget.root).resolve())
            )
        except (AttributeError, ValueError):
            recovery_relative = str(recovery_path)
        training_checkpoint_report = {
            "checkpoint": recovery_relative,
            "global_step": resume_step + len(attempts),
            "resumed_from": None if loaded_checkpoint is None else loaded_checkpoint["path"],
            "persistent_w_is_zero": True,
        }
        timed_out = time.monotonic() >= deadline

    evaluation: dict[str, Any] = {
        "split": eval_split,
        "tiers": {},
        "worlds": [],
        "overall": _summarize_query_records([]),
        "tier3_gate": {
            "implemented": False,
            "pc_r_implemented": True,
            "status": "gated",
            "reason": TIER3_GATE_REASON,
        },
    }
    restart_report: Optional[dict[str, Any]] = None
    if not timed_out:
        evaluation, candidate, eval_timed_out = evaluate_model(
            model,
            split=eval_split,
            tiers=selected_tiers,
            worlds_per_tier=worlds_per_tier,
            seed=seed,
            device=torch_device,
            deadline=deadline,
        )
        timed_out = eval_timed_out or time.monotonic() >= deadline
        if not timed_out and candidate is not None:
            restart_report = restart_identity_check(
                model,
                candidate,
                budget=budget,
                device=torch_device,
                artifact_name=f"artifacts/restart-{stamp}.mlckpt",
            )
            timed_out = time.monotonic() >= deadline

    training_grad_control = True
    if command in ("smoke", "pilot") and active_train_tiers:
        training_grad_control = bool(attempts) and all(
            attempt["writer_grad_norm"] > 0.0
            and attempt["encoder_grad_norm"] > 0.0
            and attempt["memory_query_grad_norm"] > 0.0
            for attempt in attempts
        )
    worlds = evaluation.get("worlds", [])
    w_control = bool(worlds) and all(
        float(world["w_change_norm"]) > 0.0 for world in worlds
    )
    records = [query for world in worlds for query in world["queries"]]
    causal_control = bool(records) and any(
        float(record["first_step_logit_max_abs_delta"]) > 0.0 for record in records
    )
    restart_control = bool(
        restart_report
        and restart_report["workspace_is_none"]
        and restart_report["identical_tokens"]
        and restart_report["identical_logits"]
    )
    controls = {
        "evaluation_split_is_disjoint": eval_split in ("validation", "test"),
        "training_writer_and_encoder_gradients": training_grad_control,
        "persistent_w_changed": w_control,
        "no_w_causal_path_observed": causal_control,
        "restart_workspace_is_none": bool(
            restart_report and restart_report["workspace_is_none"]
        ),
        "restart_token_identity": bool(
            restart_report and restart_report["identical_tokens"]
        ),
        "restart_logit_identity": bool(
            restart_report and restart_report["identical_logits"]
        ),
        "tier3_positive_control_reader": "implemented_not_yet_passed",
    }

    if timed_out:
        status = "time_limit"
    elif not (
        controls["evaluation_split_is_disjoint"]
        and controls["training_writer_and_encoder_gradients"]
        and controls["persistent_w_changed"]
        and controls["no_w_causal_path_observed"]
        and restart_control
    ):
        status = "failed_controls"
    else:
        status = "completed"

    peak_cuda = (
        int(torch.cuda.max_memory_allocated(torch_device))
        if torch_device.type == "cuda"
        else None
    )
    result: dict[str, Any] = {
        "status": status,
        "command": command,
        "seed": seed,
        "device": str(torch_device),
        "backbone": backbone,
        "peak_cuda_memory_bytes": peak_cuda,
        "peak_cuda_reserved_bytes": (
            int(torch.cuda.max_memory_reserved(torch_device))
            if torch_device.type == "cuda"
            else None
        ),
        "environment": environment_report(torch_device),
        "model": {
            "parameter_count": params,
            "trainable_parameter_count": trainable,
            "config": config,
        },
        "limits": {
            "optimizer_steps": max_steps,
            "wall_clock_seconds": max_seconds,
            "training_wall_clock_seconds": max(
                0.0,
                max_seconds - evaluation_reserve - checkpoint_reserve,
            ),
            "evaluation_reserve_seconds": evaluation_reserve,
            "checkpoint_reserve_seconds": checkpoint_reserve,
        },
        "requested_tiers": list(selected_tiers),
        "training": training,
        "loaded_checkpoint": loaded_checkpoint,
        "training_checkpoint": training_checkpoint_report,
        "evaluation": evaluation,
        "restart_identity": restart_report,
        "controls": controls,
        "quality": {
            "all_exact": bool(evaluation.get("overall", {}).get("all_exact", False)),
            "exact_match_rate": float(
                evaluation.get("overall", {}).get("exact_match_rate", 0.0)
            ),
            "no_w_exact_match_rate": float(
                evaluation.get("overall", {}).get("no_w_exact_match_rate", 0.0)
            ),
            "memory_exact_match_gain": float(
                evaluation.get("overall", {}).get("memory_exact_match_gain", 0.0)
            ),
        },
        "elapsed_seconds": time.monotonic() - started,
        "artifacts": {
            "training_checkpoint": (
                None
                if training_checkpoint_report is None
                else training_checkpoint_report["checkpoint"]
            ),
            "restart_checkpoint": (
                None if restart_report is None else restart_report["checkpoint"]
            ),
            "result_json": None,
        },
    }
    if save_result:
        relative = f"artifacts/result-{stamp}.json"
        result["artifacts"]["result_json"] = relative
        budget.save_json(relative, result, max_bytes=RESULT_MAX_BYTES)
    return result


def _add_common(
    parser: argparse.ArgumentParser,
    *,
    default_seconds: float,
    default_tiers: str,
    default_eval_worlds: int,
) -> None:
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--seconds", type=float, default=default_seconds)
    parser.add_argument("--tiers", type=parse_tiers, default=parse_tiers(default_tiers))
    parser.add_argument("--eval-split", choices=("validation", "test"), default="validation")
    parser.add_argument("--eval-worlds", type=int, default=default_eval_worlds)


def configure_subcommands(subparsers: Any) -> None:
    smoke = subparsers.add_parser("smoke", help="1-3 step CPU-friendly tier-1 smoke run")
    _add_common(smoke, default_seconds=30.0, default_tiers="1", default_eval_worlds=1)
    smoke.add_argument("--steps", type=int, default=2)
    smoke.add_argument("--lr", type=float, default=3e-4)
    smoke.add_argument("--grad-clip", type=float, default=1.0)
    smoke.add_argument("--support-loss-weight", type=float, default=0.5)
    smoke.add_argument("--memory-contrast-weight", type=float, default=1.0)
    smoke.add_argument("--memory-margin", type=float, default=0.5)
    smoke.add_argument("--key-alignment-weight", type=float, default=1.0)
    smoke.add_argument("--key-orthogonality-weight", type=float, default=5.0)
    smoke.add_argument("--value-key-alignment-weight", type=float, default=1.0)
    smoke.add_argument("--backbone", choices=("gru", "transformer"), default="gru")

    pilot = subparsers.add_parser("pilot", help="bounded meta-training pilot")
    _add_common(pilot, default_seconds=480.0, default_tiers="1,2", default_eval_worlds=4)
    pilot.add_argument("--steps", type=int, default=10_000)
    pilot.add_argument("--lr", type=float, default=3e-4)
    pilot.add_argument("--grad-clip", type=float, default=1.0)
    pilot.add_argument("--support-loss-weight", type=float, default=0.5)
    pilot.add_argument("--memory-contrast-weight", type=float, default=1.0)
    pilot.add_argument("--memory-margin", type=float, default=0.5)
    pilot.add_argument("--key-alignment-weight", type=float, default=1.0)
    pilot.add_argument("--key-orthogonality-weight", type=float, default=5.0)
    pilot.add_argument("--value-key-alignment-weight", type=float, default=1.0)
    pilot.add_argument("--resume-checkpoint")
    pilot.add_argument("--backbone", choices=("gru", "transformer"), default="gru")

    evaluate = subparsers.add_parser("evaluate", help="evaluate without optimizer updates")
    _add_common(evaluate, default_seconds=60.0, default_tiers="1,2", default_eval_worlds=2)
    evaluate.add_argument("--checkpoint", required=True)
    evaluate.add_argument("--backbone", choices=("gru", "transformer"), default="gru")

    pc_reader = subparsers.add_parser(
        "pc-reader",
        help="train/evaluate the W-disabled in-context reader ceiling",
    )
    _add_common(
        pc_reader,
        default_seconds=480.0,
        default_tiers="2,3",
        default_eval_worlds=8,
    )
    pc_reader.add_argument("--steps", type=int, default=10_000)
    pc_reader.add_argument("--lr", type=float, default=3e-4)
    pc_reader.add_argument("--grad-clip", type=float, default=1.0)
    pc_reader.add_argument("--threshold", type=float, default=PC_R_THRESHOLD)

    pc_memory = subparsers.add_parser(
        "pc-memory",
        help="train/evaluate staged PC-E oracle-content and PC-W full-writer controls",
    )
    pc_memory.add_argument("--seed", type=int, default=0)
    pc_memory.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    pc_memory.add_argument("--seconds", type=float, default=480.0)
    pc_memory.add_argument("--encoder-steps", type=int, default=1_000)
    pc_memory.add_argument("--writer-steps", type=int, default=1_000)
    pc_memory.add_argument("--eval-worlds", type=int, default=8)
    pc_memory.add_argument("--items", type=int, default=PC_MEMORY_ITEMS)
    pc_memory.add_argument("--lr", type=float, default=1e-3)
    pc_memory.add_argument("--grad-clip", type=float, default=1.0)
    pc_memory.add_argument("--address-weight", type=float, default=1.0)
    pc_memory.add_argument("--orthogonality-weight", type=float, default=5.0)
    pc_memory.add_argument(
        "--backbone",
        choices=("gru", "transformer"),
        default="gru",
    )
    pc_memory.add_argument("--resume-checkpoint")

    pc_chain = subparsers.add_parser(
        "pc-chain",
        help="train/evaluate PC-C with oracle chain memory and an injected second-hop key",
    )
    pc_chain.add_argument("--seed", type=int, default=0)
    pc_chain.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    pc_chain.add_argument("--seconds", type=float, default=480.0)
    pc_chain.add_argument("--steps", type=int, default=2_000)
    pc_chain.add_argument("--eval-worlds", type=int, default=16)
    pc_chain.add_argument("--lr", type=float, default=3e-4)
    pc_chain.add_argument("--grad-clip", type=float, default=1.0)
    pc_chain.add_argument("--threshold", type=float, default=PC_C_THRESHOLD)
    pc_chain.add_argument(
        "--backbone",
        choices=("gru", "transformer"),
        default="transformer",
    )


def run_from_args(
    args: argparse.Namespace,
    budget: Any,
    runtime: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    del runtime
    if args.command == "pc-memory":
        result = run_memory_positive_controls(
            budget=budget,
            seed=args.seed,
            device=args.device,
            encoder_steps=args.encoder_steps,
            writer_steps=args.writer_steps,
            seconds=args.seconds,
            eval_worlds=args.eval_worlds,
            item_count=args.items,
            learning_rate=args.lr,
            grad_clip=args.grad_clip,
            address_weight=args.address_weight,
            orthogonality_weight=args.orthogonality_weight,
            backbone=args.backbone,
            resume_checkpoint=args.resume_checkpoint,
        )
        stamp = f"pc-memory-{args.seed}-{time.time_ns()}-{os.getpid()}"
        relative = f"artifacts/result-{stamp}.json"
        result["artifacts"] = {
            "result_json": relative,
            "checkpoint": (
                None
                if result["restart_identity"] is None
                else result["restart_identity"]["checkpoint"]
            ),
        }
        budget.save_json(relative, result, max_bytes=RESULT_MAX_BYTES)
        print(json.dumps(result, indent=2, sort_keys=True))
        return result
    if args.command == "pc-chain":
        result = run_pc_c_control(
            budget=budget,
            seed=args.seed,
            device=args.device,
            steps=args.steps,
            seconds=args.seconds,
            eval_worlds=args.eval_worlds,
            learning_rate=args.lr,
            grad_clip=args.grad_clip,
            threshold=args.threshold,
            backbone=args.backbone,
        )
        stamp = f"pc-chain-{args.seed}-{time.time_ns()}-{os.getpid()}"
        relative = f"artifacts/result-{stamp}.json"
        result["artifacts"] = {
            "result_json": relative,
            "checkpoint": (
                None
                if result["restart_identity"] is None
                else result["restart_identity"]["checkpoint"]
            ),
        }
        budget.save_json(relative, result, max_bytes=RESULT_MAX_BYTES)
        print(json.dumps(result, indent=2, sort_keys=True))
        return result
    if args.command == "pc-reader":
        result = run_pc_r_control(
            seed=args.seed,
            device=args.device,
            tiers=args.tiers,
            steps=args.steps,
            seconds=args.seconds,
            eval_worlds=args.eval_worlds,
            learning_rate=args.lr,
            grad_clip=args.grad_clip,
            threshold=args.threshold,
        )
        stamp = f"pc-reader-{args.seed}-{time.time_ns()}-{os.getpid()}"
        relative = f"artifacts/result-{stamp}.json"
        result["artifacts"] = {"result_json": relative}
        budget.save_json(relative, result, max_bytes=RESULT_MAX_BYTES)
        print(json.dumps(result, indent=2, sort_keys=True))
        return result
    kwargs = {
        "seed": args.seed,
        "device": args.device,
        "tiers": args.tiers,
        "seconds": args.seconds,
        "eval_split": args.eval_split,
        "eval_worlds": args.eval_worlds,
        "backbone": args.backbone,
        "emit_model": True,
    }
    if args.command in ("smoke", "pilot"):
        kwargs.update(
            steps=args.steps,
            learning_rate=args.lr,
            grad_clip=args.grad_clip,
            support_loss_weight=args.support_loss_weight,
            memory_contrast_weight=args.memory_contrast_weight,
            memory_margin=args.memory_margin,
            key_alignment_weight=args.key_alignment_weight,
            key_orthogonality_weight=args.key_orthogonality_weight,
            value_key_alignment_weight=args.value_key_alignment_weight,
        )
        if args.command == "pilot":
            kwargs["resume_checkpoint"] = args.resume_checkpoint
    elif args.command == "evaluate":
        kwargs["checkpoint"] = args.checkpoint
    result = run_experiment(args.command, budget, **kwargs)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main(
    argv: list[str],
    budget: Any,
    runtime: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    parser = argparse.ArgumentParser(prog="run.py")
    subparsers = parser.add_subparsers(dest="command", required=True)
    configure_subcommands(subparsers)
    args = parser.parse_args(argv)
    return run_from_args(args, budget, runtime)


__all__ = [
    "apply_teachings",
    "causal_generate",
    "configure_subcommands",
    "decode_token_ids",
    "evaluate_model",
    "main",
    "meta_train_episode",
    "model_config",
    "normalize_text",
    "parameter_count",
    "parse_tiers",
    "restart_identity_check",
    "run_experiment",
    "run_from_args",
]
