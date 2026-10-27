"""Bounded positive controls for the persistent-memory learner.

PC-R is a separately trained in-context ceiling: it receives accepted teaching
sentences and the query in one input, while persistent memory W is fixed to
zero.  It therefore tests whether this reader width can interpret the task at
all before tier 3 is attributed to a learned writer or matrix memory.
"""
from __future__ import annotations

from collections import defaultdict
import math
import random
import time
from typing import Any, Iterable, Optional

import torch
from torch import nn
from torch.nn import functional as F

from .checkpoint import inspect_checkpoint_config, load_scored_restart, save_checkpoint
from .model import MainNetwork, ModelOutput, TokenSpec, unit
from .transformer_model import RecurrentTransformerLearner
from .tasks import (
    EOS_ID,
    PAD_ID,
    SYMBOLS,
    Episode,
    Query,
    Teaching,
    batch_teachings,
    batch_queries,
    batch_query_targets,
    decode_token_ids,
    generate_episode,
    normalize_text,
    relation_value_key_probe,
    support_query_for_teaching,
)


PC_R_THRESHOLD = 0.95
PC_R_TIERS = (2, 3)
MAX_PC_R_WORLDS_PER_TIER = 64
MAX_RECORDED_PC_R_ATTEMPTS = 128

PC_E_THRESHOLD = 0.95
PC_W_THRESHOLD = 0.90
PC_MEMORY_ITEMS = 16
MAX_PC_MEMORY_ITEMS = 128
MAX_RECORDED_PC_MEMORY_ATTEMPTS = 128

PC_C_THRESHOLD = 0.90
MAX_PC_C_WORLDS = 64
MAX_RECORDED_PC_C_ATTEMPTS = 128


class _ControlTheta(nn.Module):
    """Checkpoint view that keeps writer phi separate from theta."""

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


def _model_config(model: nn.Module) -> dict[str, Any]:
    common = {
        "architecture": type(model).__name__,
        "reasoning_steps": model.reasoning_steps,
        "max_reasoning_steps": model.max_reasoning_steps,
        "max_decode_len": model.max_decode_len,
        "token_spec": {
            "vocab_size": model.token_spec.vocab_size,
            "pad_id": model.token_spec.pad_id,
            "eos_id": model.token_spec.eos_id,
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
        return common
    return {
        **common,
        "embed_width": model.embed_width,
        "hidden_width": model.hidden_width,
    }


def _fresh_model_like(model: nn.Module) -> nn.Module:
    config = _model_config(model)
    architecture = config.pop("architecture")
    spec = TokenSpec(**config.pop("token_spec"))
    if architecture == "RecurrentTransformerLearner":
        config.pop("reader_version")
        return RecurrentTransformerLearner(token_spec=spec, **config)
    return MainNetwork(token_spec=spec, **config)


def memory_control_examples(
    split: str,
    seed: int,
    *,
    item_count: int = PC_MEMORY_ITEMS,
) -> tuple[tuple[Teaching, Query], ...]:
    """Collect distinct uncorrected tag facts for a bounded memory control.

    The returned Query still carries its expected value only on the evaluator
    side.  Model-facing batching below serializes Teaching.text or Query.text
    and never serializes Query.expected.
    """
    if split not in ("train", "validation", "test"):
        raise ValueError("memory controls require train/validation/test split")
    if not 1 <= item_count <= MAX_PC_MEMORY_ITEMS:
        raise ValueError(f"item_count must be in [1,{MAX_PC_MEMORY_ITEMS}]")
    examples: list[tuple[Teaching, Query]] = []
    seen_queries: set[str] = set()
    ordinal = 0
    while len(examples) < item_count:
        episode = generate_episode(
            split,
            _episode_index(seed, 1, ordinal),
            tier=1,
        )
        ordinal += 1
        for teaching in episode.teachings:
            if teaching.correction:
                continue
            query = support_query_for_teaching(teaching)
            if query is None or query.text in seen_queries:
                continue
            seen_queries.add(query.text)
            examples.append((teaching, query))
            if len(examples) == item_count:
                break
    return tuple(examples)


def _oracle_contents(
    queries: tuple[Query, ...],
    *,
    width: int,
    heads: Optional[int] = None,
    device: torch.device,
) -> torch.Tensor:
    """Fixed orthogonal tag codes used only by the oracle-content PC-E arm."""
    if width < len(SYMBOLS):
        raise ValueError("memory width is too small for the oracle tag codes")
    shape = (len(queries), width) if heads is None else (len(queries), heads, width)
    result = torch.zeros(*shape, dtype=torch.float32, device=device)
    symbol_to_index = {symbol: index for index, symbol in enumerate(SYMBOLS)}
    for row, query in enumerate(queries):
        try:
            if heads is None:
                result[row, symbol_to_index[query.expected]] = 1.0
            else:
                result[row, :, symbol_to_index[query.expected]] = 1.0
        except KeyError as error:
            raise ValueError("memory control expects a single tag target") from error
    return result


def _initial_cues(
    model: nn.Module,
    queries: tuple[Query, ...],
    device: torch.device,
) -> torch.Tensor:
    batch = batch_queries(queries, device=device)
    encoded = model.encode(batch.token_ids, lengths=batch.lengths)
    return model.initial_memory_query(encoded)


def _contrastive_address_loss(
    keys: torch.Tensor,
    cues: torch.Tensor,
    *,
    temperature: float = 0.07,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    if keys.ndim != 2 or cues.shape != keys.shape or keys.shape[0] == 0:
        raise ValueError("keys and cues must share non-empty [items,width] shape")
    keys = unit(keys)
    cues = unit(cues)
    positive = F.cosine_similarity(keys, cues, dim=-1, eps=1e-8).mean()
    if keys.shape[0] == 1:
        return 1.0 - positive, positive, positive.new_zeros(())
    logits = torch.matmul(keys, cues.transpose(0, 1)) / temperature
    labels = torch.arange(keys.shape[0], device=keys.device)
    loss = 0.5 * (
        F.cross_entropy(logits, labels)
        + F.cross_entropy(logits.transpose(0, 1), labels)
    )
    eye = torch.eye(keys.shape[0], dtype=torch.bool, device=keys.device)
    max_key_overlap = torch.matmul(keys, keys.transpose(0, 1)).masked_fill(
        eye, -1.0
    ).max()
    return loss, positive, max_key_overlap


def _key_orthogonality_loss(keys: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Penalize interference within each delta bank, not just retrieval ranking."""
    if keys.ndim == 2:
        keys = keys.unsqueeze(1)
    if keys.ndim != 3 or keys.shape[0] == 0:
        raise ValueError("keys must have [items,width] or [items,heads,width] shape")
    normalized = unit(keys)
    # [heads, items, items]; every memory head needs low overlap independently.
    gram = torch.einsum("ihd,jhd->hij", normalized, normalized)
    item_count = keys.shape[0]
    if item_count == 1:
        zero = gram.new_zeros(())
        return zero, zero
    eye = torch.eye(item_count, dtype=torch.bool, device=keys.device).unsqueeze(0)
    off_diagonal = gram.masked_select(~eye.expand_as(gram))
    return off_diagonal.square().mean(), off_diagonal.abs().max()


def _write_control_memory(
    model: nn.Module,
    examples: tuple[tuple[Teaching, Query], ...],
    *,
    device: torch.device,
    oracle_content: bool,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    teachings = tuple(teaching for teaching, _ in examples)
    queries = tuple(query for _, query in examples)
    teaching_batch = batch_teachings(teachings, device=device)
    encoding = model.encode(teaching_batch.token_ids, lengths=teaching_batch.lengths)
    proposal = model.writer(encoding)
    content_shape = proposal.value.shape[1:]
    oracle = _oracle_contents(
        queries,
        width=content_shape[-1],
        heads=None if len(content_shape) == 1 else content_shape[0],
        device=device,
    )
    values = oracle if oracle_content else proposal.value
    weights = model.new_memory(batch=1, device=device)
    for index in range(len(examples)):
        weights = model.memory.delta_write(
            weights,
            proposal.key[index : index + 1],
            values[index : index + 1],
        )
    cues = _initial_cues(model, queries, device)
    return weights, proposal.key, proposal.value, cues


def _payload_and_eos_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    if logits.shape[1] < 2 or targets.shape[1] < 2:
        raise ValueError("memory control targets must contain payload and EOS")
    payload = F.cross_entropy(logits[:, 0], targets[:, 0])
    eos = F.cross_entropy(logits[:, 1], targets[:, 1])
    return payload + 0.25 * eos, payload, eos


def train_memory_control_step(
    model: nn.Module,
    examples: tuple[tuple[Teaching, Query], ...],
    optimizer: torch.optim.Optimizer,
    *,
    mode: str,
    device: torch.device | str = "cpu",
    grad_clip: float = 1.0,
    address_weight: float = 1.0,
    orthogonality_weight: float = 5.0,
    value_weight: float = 1.0,
) -> dict[str, Any]:
    """Train one PC-E (oracle content) or PC-W (full writer) batch."""
    if mode not in ("encoder", "writer"):
        raise ValueError("mode must be encoder (PC-E) or writer (PC-W)")
    if not examples:
        raise ValueError("memory control requires at least one example")
    if (
        grad_clip <= 0
        or address_weight < 0
        or orthogonality_weight < 0
        or value_weight < 0
    ):
        raise ValueError("invalid memory-control optimization weight")
    device = torch.device(device)
    model.train()
    optimizer.zero_grad(set_to_none=True)
    queries = tuple(query for _, query in examples)
    weights, keys, writer_values, cues = _write_control_memory(
        model,
        examples,
        device=device,
        oracle_content=mode == "encoder",
    )
    query_batch = batch_queries(queries, device=device)
    targets = batch_query_targets(queries, device=device)
    output = model(
        query_batch.token_ids,
        weights.expand(len(examples), *([-1] * (weights.ndim - 1))),
        targets=targets.token_ids,
        lengths=query_batch.lengths,
        teacher_forcing=True,
    )
    query_loss, payload_loss, eos_loss = _payload_and_eos_loss(
        output.decoding.logits,
        targets.token_ids,
    )
    address_loss, positive_cosine, _ = _contrastive_address_loss(
        keys.flatten(1),
        cues.flatten(1),
    )
    orthogonality_loss, max_key_overlap = _key_orthogonality_loss(keys)
    content_shape = writer_values.shape[1:]
    oracle = _oracle_contents(
        queries,
        width=content_shape[-1],
        heads=None if len(content_shape) == 1 else content_shape[0],
        device=device,
    )
    if mode == "writer":
        # This is target-side supervision, not a writer input: phi still receives
        # only the teaching encoding.  It gives PC-W an inspectable canonical
        # value representation after PC-E has established the reader ceiling.
        value_loss = (
            1.0
            - F.cosine_similarity(writer_values, oracle, dim=-1, eps=1e-8).mean()
            + 0.1 * (writer_values.norm(dim=-1) - 1.0).square().mean()
        )
    else:
        value_loss = query_loss.new_zeros(())
    loss = (
        query_loss
        + address_weight * address_loss
        + orthogonality_weight * orthogonality_loss
        + value_weight * value_loss
    )
    loss.backward()
    key_modules = [model.writer.key]
    if hasattr(model.writer, "key_attention"):
        key_modules.append(model.writer.key_attention)
    value_modules = [model.writer.value]
    if hasattr(model.writer, "value_attention"):
        value_modules.append(model.writer.value_attention)
    key_grad = _grad_norm(
        parameter for module in key_modules for parameter in module.parameters()
    )
    value_grad = _grad_norm(
        parameter for module in value_modules for parameter in module.parameters()
    )
    encoder_modules = [model.embedding]
    encoder_modules.append(model.encoder if hasattr(model, "encoder") else model.prelude)
    encoder_grad = _grad_norm(
        parameter for module in encoder_modules for parameter in module.parameters()
    )
    preclip = float(torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip).item())
    optimizer.step()
    return {
        "mode": "PC-E" if mode == "encoder" else "PC-W",
        "items": len(examples),
        "loss": float(loss.detach().cpu().item()),
        "query_loss": float(query_loss.detach().cpu().item()),
        "payload_loss": float(payload_loss.detach().cpu().item()),
        "eos_loss": float(eos_loss.detach().cpu().item()),
        "address_loss": float(address_loss.detach().cpu().item()),
        "orthogonality_loss": float(orthogonality_loss.detach().cpu().item()),
        "orthogonality_weight": orthogonality_weight,
        "value_loss": float(value_loss.detach().cpu().item()),
        "matched_address_cosine": float(positive_cosine.detach().cpu().item()),
        "max_key_overlap": float(max_key_overlap.detach().cpu().item()),
        "writer_key_grad_norm": key_grad,
        "writer_value_grad_norm": value_grad,
        "encoder_grad_norm": encoder_grad,
        "preclip_grad_norm": preclip,
        "w_change_norm": float(weights.detach().norm().cpu().item()),
    }


def evaluate_memory_control(
    model: nn.Module,
    *,
    mode: str,
    split: str = "validation",
    worlds: int = 8,
    item_count: int = PC_MEMORY_ITEMS,
    seed: int = 0,
    device: torch.device | str = "cpu",
    threshold: Optional[float] = None,
    deadline: Optional[float] = None,
    reasoning_steps: Optional[int] = None,
) -> dict[str, Any]:
    """Greedily evaluate PC-E or PC-W on held-out N-item memories."""
    if mode not in ("encoder", "writer"):
        raise ValueError("mode must be encoder or writer")
    if split not in ("validation", "test"):
        raise ValueError("memory-control evaluation is held-out only")
    if not 1 <= worlds <= 64:
        raise ValueError("worlds must be in [1,64]")
    if not 1 <= item_count <= MAX_PC_MEMORY_ITEMS:
        raise ValueError(f"item_count must be in [1,{MAX_PC_MEMORY_ITEMS}]")
    selected_threshold = (
        PC_E_THRESHOLD if mode == "encoder" else PC_W_THRESHOLD
    ) if threshold is None else threshold
    if not 0.0 <= selected_threshold <= 1.0:
        raise ValueError("threshold must lie in [0,1]")
    if reasoning_steps is not None:
        if not isinstance(model, RecurrentTransformerLearner):
            raise ValueError("reasoning_steps override requires the transformer backbone")
        if not 1 <= reasoning_steps <= model.max_reasoning_steps:
            raise ValueError("reasoning_steps override is outside the model limit")
    device = torch.device(device)
    model.eval()
    rows: list[dict[str, Any]] = []
    completed_worlds = 0
    first_fixture: Optional[dict[str, Any]] = None
    timed_out = False
    with torch.no_grad():
        for world in range(worlds):
            if deadline is not None and time.monotonic() >= deadline:
                timed_out = True
                break
            examples = memory_control_examples(
                split,
                seed * 10_007 + world,
                item_count=item_count,
            )
            weights, keys, _, cues = _write_control_memory(
                model,
                examples,
                device=device,
                oracle_content=mode == "encoder",
            )
            queries = tuple(query for _, query in examples)
            batch = batch_queries(queries, device=device)
            expanded = weights.expand(item_count, *([-1] * (weights.ndim - 1)))
            step_kwargs = {} if reasoning_steps is None else {"steps": reasoning_steps}
            with_w = model.generate(
                batch.token_ids,
                expanded,
                lengths=batch.lengths,
                max_new_tokens=2,
                **step_kwargs,
            )
            no_w = model.generate(
                batch.token_ids,
                torch.zeros_like(expanded),
                lengths=batch.lengths,
                max_new_tokens=2,
                **step_kwargs,
            )
            if first_fixture is None:
                first_fixture = {
                    "examples": examples,
                    "weights": weights.detach().clone(),
                    "tokens": with_w.decoding.tokens.detach().cpu().clone(),
                    "logits": with_w.decoding.logits.detach().cpu().clone(),
                }
            for index, query in enumerate(queries):
                generated = decode_token_ids(
                    with_w.decoding.tokens[index].detach().cpu().tolist()
                )
                no_w_generated = decode_token_ids(
                    no_w.decoding.tokens[index].detach().cpu().tolist()
                )
                expected = normalize_text(query.expected)
                rows.append(
                    {
                        "world": world,
                        "expected": expected,
                        "generated": generated,
                        "no_w_generated": no_w_generated,
                        "exact_match": generated == expected,
                        "no_w_exact_match": no_w_generated == expected,
                    }
                )
            completed_worlds += 1

    exact = sum(bool(row["exact_match"]) for row in rows)
    no_w_exact = sum(bool(row["no_w_exact_match"]) for row in rows)
    total = len(rows)
    rate = exact / total if total else 0.0
    no_w_rate = no_w_exact / total if total else 0.0
    return {
        "status": "time_limit" if timed_out else "completed",
        "control": "PC-E" if mode == "encoder" else "PC-W",
        "reasoning_steps": (
            reasoning_steps
            if reasoning_steps is not None
            else getattr(model, "reasoning_steps", None)
        ),
        "split": split,
        "worlds_requested": worlds,
        "worlds_completed": completed_worlds,
        "items_per_world": item_count,
        "queries": total,
        "exact_matches": exact,
        "exact_match_rate": rate,
        "no_w_exact_matches": no_w_exact,
        "no_w_exact_match_rate": no_w_rate,
        "memory_exact_match_gain": rate - no_w_rate,
        "threshold": selected_threshold,
        "threshold_passed": (
            not timed_out
            and completed_worlds == worlds
            and rate >= selected_threshold
        ),
        "records": rows,
        # Kept out of serialized reports by the bounded runner below.
        "_restart_fixture": first_fixture,
    }


def _restart_memory_control(
    model: nn.Module,
    fixture: dict[str, Any],
    *,
    budget: Any,
    artifact_name: str,
    device: torch.device,
    mode: str,
) -> dict[str, Any]:
    config = {
        "checkpoint_role": "memory_positive_control",
        "control": "PC-E" if mode == "encoder" else "PC-W",
        "model": _model_config(model),
    }
    path = save_checkpoint(
        budget,
        artifact_name,
        _ControlTheta(model),
        model.writer,
        fixture["weights"][0],
        config=config,
        max_bytes=64 * 1024 * 1024,
    )
    fresh = _fresh_model_like(model).to(device)
    restored = load_scored_restart(
        path,
        _ControlTheta(fresh),
        fresh.writer,
        map_location=device,
        max_bytes=64 * 1024 * 1024,
        expected_config=config,
    )
    examples = fixture["examples"]
    queries = tuple(query for _, query in examples)
    batch = batch_queries(queries, device=device)
    restored_batch = restored.W.unsqueeze(0)
    expanded = restored_batch.expand(
        len(examples),
        *([-1] * (restored_batch.ndim - 1)),
    )
    fresh.eval()
    with torch.no_grad():
        output = fresh.generate(
            batch.token_ids,
            expanded,
            lengths=batch.lengths,
            max_new_tokens=2,
        )
    after = output.decoding.tokens.detach().cpu()
    before = fixture["tokens"]
    # Tokens alone pass vacuously for a degenerate model; require exact logits.
    after_logits = output.decoding.logits.detach().cpu()
    before_logits = fixture["logits"]
    try:
        relative = str(path.resolve().relative_to(budget.root.resolve()))
    except (AttributeError, ValueError):
        relative = str(path)
    return {
        "checkpoint": relative,
        "workspace_is_none": restored.workspace is None,
        "identical_tokens": bool(torch.equal(before, after)),
        "identical_logits": bool(torch.equal(before_logits, after_logits)),
        "logits_max_abs_diff": float((before_logits - after_logits).abs().max().item()),
        "items": len(examples),
    }


def _recorded_attempts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(rows) <= MAX_RECORDED_PC_MEMORY_ATTEMPTS:
        return rows
    half = MAX_RECORDED_PC_MEMORY_ATTEMPTS // 2
    return rows[:half] + rows[-half:]


def run_memory_positive_controls(
    *,
    budget: Any,
    seed: int = 0,
    device: str = "cpu",
    encoder_steps: int = 1_000,
    writer_steps: int = 1_000,
    seconds: float = 480.0,
    eval_worlds: int = 8,
    item_count: int = PC_MEMORY_ITEMS,
    learning_rate: float = 1e-3,
    grad_clip: float = 1.0,
    address_weight: float = 1.0,
    orthogonality_weight: float = 5.0,
    backbone: str = "gru",
    resume_checkpoint: Optional[str] = None,
    model: Optional[nn.Module] = None,
) -> dict[str, Any]:
    """Run the staged PC-E -> PC-W ladder and prove serialized restart identity."""
    if encoder_steps <= 0 or writer_steps <= 0:
        raise ValueError("encoder_steps and writer_steps must be positive")
    if not 0.0 < seconds <= 600.0:
        raise ValueError("seconds must lie in (0,600]")
    if (
        learning_rate <= 0
        or grad_clip <= 0
        or address_weight < 0
        or orthogonality_weight < 0
    ):
        raise ValueError("learning rate and grad clip must be positive")
    if backbone not in ("gru", "transformer"):
        raise ValueError("backbone must be 'gru' or 'transformer'")
    if device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was explicitly selected but is unavailable")
        torch_device = torch.device("cuda")
    elif device == "cpu":
        torch_device = torch.device("cpu")
    else:
        raise ValueError("device must be 'cpu' or 'cuda'")

    random.seed(seed)
    torch.manual_seed(seed)
    if torch_device.type == "cuda":
        torch.cuda.manual_seed_all(seed)
        torch.cuda.reset_peak_memory_stats(torch_device)
    if model is None:
        active = (
            MainNetwork()
            if backbone == "gru"
            else RecurrentTransformerLearner()
        )
    else:
        active = model
        observed_backbone = (
            "transformer" if isinstance(active, RecurrentTransformerLearner) else "gru"
        )
        if backbone != "gru" and backbone != observed_backbone:
            raise ValueError("explicit model and backbone disagree")
        backbone = observed_backbone
    active = active.to(torch_device)
    loaded_checkpoint: Optional[dict[str, Any]] = None
    if resume_checkpoint is not None:
        stored = inspect_checkpoint_config(
            resume_checkpoint,
            max_bytes=64 * 1024 * 1024,
        )
        expected = {
            "checkpoint_role": "memory_positive_control",
            "control": "PC-W",
            "model": _model_config(active),
        }
        if stored != expected:
            raise ValueError("PC-memory resume checkpoint is incompatible")
        restored = load_scored_restart(
            resume_checkpoint,
            _ControlTheta(active),
            active.writer,
            map_location=torch_device,
            max_bytes=64 * 1024 * 1024,
            expected_config=expected,
        )
        loaded_checkpoint = {
            "path": str(resume_checkpoint),
            "workspace_is_none": restored.workspace is None,
            "saved_w_ignored_for_meta_training": True,
        }
    optimizer = torch.optim.AdamW(active.parameters(), lr=learning_rate)
    started = time.monotonic()
    deadline = started + seconds
    evaluation_reserve = min(max(20.0, seconds * 0.20), seconds * 0.40)
    training_deadline = deadline - evaluation_reserve
    total_requested = encoder_steps + writer_steps
    encoder_fraction = encoder_steps / total_requested
    encoder_deadline = started + (training_deadline - started) * encoder_fraction
    attempts_e: list[dict[str, Any]] = []
    attempts_w: list[dict[str, Any]] = []

    for step in range(encoder_steps):
        if time.monotonic() >= encoder_deadline:
            break
        examples = memory_control_examples(
            "train",
            seed * 1_000_003 + step,
            item_count=item_count,
        )
        attempts_e.append(
            train_memory_control_step(
                active,
                examples,
                optimizer,
                mode="encoder",
                device=torch_device,
                grad_clip=grad_clip,
                address_weight=address_weight,
                orthogonality_weight=orthogonality_weight,
            )
        )

    for step in range(writer_steps):
        if time.monotonic() >= training_deadline:
            break
        examples = memory_control_examples(
            "train",
            seed * 2_000_003 + step,
            item_count=item_count,
        )
        attempts_w.append(
            train_memory_control_step(
                active,
                examples,
                optimizer,
                mode="writer",
                device=torch_device,
                grad_clip=grad_clip,
                address_weight=address_weight,
                orthogonality_weight=orthogonality_weight,
            )
        )

    pc_e = evaluate_memory_control(
        active,
        mode="encoder",
        worlds=eval_worlds,
        item_count=item_count,
        seed=seed,
        device=torch_device,
        deadline=deadline,
    )
    fixture_e = pc_e.pop("_restart_fixture")
    pc_w = evaluate_memory_control(
        active,
        mode="writer",
        worlds=eval_worlds,
        item_count=item_count,
        seed=seed,
        device=torch_device,
        deadline=deadline,
    )
    fixture_w = pc_w.pop("_restart_fixture")
    restart: Optional[dict[str, Any]] = None
    if fixture_w is not None and time.monotonic() < deadline:
        stamp = f"pc-memory-{seed}-{time.time_ns()}"
        restart = _restart_memory_control(
            active,
            fixture_w,
            budget=budget,
            artifact_name=f"artifacts/checkpoint-{stamp}.mlckpt",
            device=torch_device,
            mode="writer",
        )
    gradients_ok = (
        bool(attempts_e)
        and bool(attempts_w)
        and all(row["writer_key_grad_norm"] > 0.0 for row in attempts_e)
        and all(row["writer_value_grad_norm"] == 0.0 for row in attempts_e)
        and all(row["writer_value_grad_norm"] > 0.0 for row in attempts_w)
    )
    restart_ok = bool(
        restart
        and restart["workspace_is_none"]
        and restart["identical_tokens"]
        and restart["identical_logits"]
    )
    threshold_passed = bool(
        pc_e["threshold_passed"]
        and pc_w["threshold_passed"]
        and restart_ok
    )
    timed_out = (
        pc_e["status"] == "time_limit"
        or pc_w["status"] == "time_limit"
        or time.monotonic() >= deadline
    )
    return {
        "status": "time_limit" if timed_out else (
            "completed" if gradients_ok and restart_ok else "failed_controls"
        ),
        "control": "PC-E+PC-W",
        "backbone": backbone,
        "device": str(torch_device),
        "seed": seed,
        "model": {
            "parameter_count": sum(parameter.numel() for parameter in active.parameters()),
            "config": _model_config(active),
        },
        "limits": {
            "encoder_steps": encoder_steps,
            "writer_steps": writer_steps,
            "wall_clock_seconds": seconds,
            "evaluation_reserve_seconds": evaluation_reserve,
            "items_per_world": item_count,
            "address_weight": address_weight,
            "orthogonality_weight": orthogonality_weight,
        },
        "training": {
            "pc_e_steps_completed": len(attempts_e),
            "pc_w_steps_completed": len(attempts_w),
            "pc_e_attempts": _recorded_attempts(attempts_e),
            "pc_w_attempts": _recorded_attempts(attempts_w),
            "attempts_truncated": (
                len(attempts_e) > MAX_RECORDED_PC_MEMORY_ATTEMPTS
                or len(attempts_w) > MAX_RECORDED_PC_MEMORY_ATTEMPTS
            ),
        },
        "controls": {
            "train_text_only": True,
            "validation_held_out": True,
            "pc_e_oracle_content": True,
            "pc_w_writer_input_is_teaching_only": True,
            "gradients_ok": gradients_ok,
            "restart_identity": restart_ok,
        },
        "evaluation": {"PC-E": pc_e, "PC-W": pc_w},
        "restart_identity": restart,
        "loaded_checkpoint": loaded_checkpoint,
        "threshold_passed": threshold_passed,
        "elapsed_seconds": time.monotonic() - started,
        "peak_cuda_memory_bytes": (
            int(torch.cuda.max_memory_allocated(torch_device))
            if torch_device.type == "cuda"
            else None
        ),
    }


def pc_c_examples(
    split: str,
    seed: int,
    *,
    worlds: int = 1,
) -> tuple[tuple[Query, Query], ...]:
    """Return two-hop queries paired with their evaluator-side second-hop probe.

    The first Query is the model-facing scored query. The second Query is the
    canonical ``tag(b)`` probe produced by ``relation_value_key_probe``; only
    its text is used to construct the teacher-forced memory key. Its placeholder
    expected value is deliberately ignored. The oracle constant value comes
    from the scored query target and never participates in key construction.
    """
    if split not in ("train", "validation", "test"):
        raise ValueError("PC-C requires train/validation/test split")
    if not 1 <= worlds <= MAX_PC_C_WORLDS:
        raise ValueError(f"worlds must be in [1,{MAX_PC_C_WORLDS}]")
    rows: list[tuple[Query, Query]] = []
    for ordinal in range(worlds):
        episode = generate_episode(
            split,
            _episode_index(seed, 2, ordinal),
            tier=2,
        )
        second = next(
            probe
            for teaching in episode.teachings
            if (probe := relation_value_key_probe(teaching)) is not None
        )
        firsts = tuple(
            query
            for query in episode.queries
            if query.purpose in ("corrected_two_hop", "two_hop_paraphrase")
        )
        if len(firsts) != 2:
            raise RuntimeError("tier-2 PC-C world is missing its two-hop query pair")
        rows.extend((first, second) for first in firsts)
    return tuple(rows)


def _pc_c_orthogonal_second_key(
    first: torch.Tensor,
    second: torch.Tensor,
) -> torch.Tensor:
    """Make the injected second-hop key interference-free from the first key."""
    if first.shape != second.shape or first.ndim not in (2, 3):
        raise ValueError("PC-C keys must share [batch,width] or [batch,heads,width] shape")
    first = unit(first.float())
    second = unit(second.float())
    orthogonal = second - (second * first).sum(dim=-1, keepdim=True) * first
    tiny = orthogonal.norm(dim=-1, keepdim=True) <= 1e-6
    if bool(tiny.any().item()):
        # Deterministic fallback: choose the basis coordinate least aligned to
        # the first key, then remove its remaining projection.
        basis = torch.zeros_like(first)
        index = first.abs().argmin(dim=-1, keepdim=True)
        basis.scatter_(-1, index, 1.0)
        fallback = basis - (basis * first).sum(dim=-1, keepdim=True) * first
        orthogonal = torch.where(tiny, fallback, orthogonal)
    return unit(orthogonal)


def _pc_c_oracle_memory(
    model: nn.Module,
    examples: tuple[tuple[Query, Query], ...],
    *,
    device: torch.device,
) -> dict[str, Any]:
    """Install the exact two-link chain without invoking the learned writer.

    W stores ``first_key -> second_key`` and ``second_key -> tag_code``.  Only
    ``second_key`` is later injected into reasoning; the scored target never
    participates in either key computation.
    """
    if not examples:
        raise ValueError("PC-C requires at least one example")
    first_queries = tuple(first for first, _ in examples)
    second_queries = tuple(second for _, second in examples)
    first_batch = batch_queries(first_queries, device=device)
    second_batch = batch_queries(second_queries, device=device)
    with torch.no_grad():
        first_encoded = model.encode(first_batch.token_ids, lengths=first_batch.lengths)
        second_encoded = model.encode(second_batch.token_ids, lengths=second_batch.lengths)
        first_key = model.initial_memory_query(first_encoded).float()
        raw_second_key = model.initial_memory_query(second_encoded).float()
        second_key = _pc_c_orthogonal_second_key(first_key, raw_second_key)
        heads = None if first_key.ndim == 2 else first_key.shape[1]
        tag_value = _oracle_contents(
            first_queries,
            width=first_key.shape[-1],
            heads=heads,
            device=device,
        )
        weights = model.new_memory(batch=len(examples), device=device)
        weights = model.memory.delta_write(weights, first_key, second_key)
        weights = model.memory.delta_write(weights, second_key, tag_value)
    return {
        "weights": weights.detach(),
        "first_key": first_key.detach(),
        "second_key": second_key.detach(),
        "tag_value": tag_value.detach(),
        "first_batch": first_batch,
        "second_batch": second_batch,
    }


def _pc_c_forward(
    model: nn.Module,
    examples: tuple[tuple[Query, Query], ...],
    oracle: dict[str, Any],
    *,
    targets: Optional[torch.Tensor] = None,
    zero_memory: bool = False,
) -> tuple[Any, Any, Any]:
    """Run exactly two reasoning steps with only step 1 teacher-forced."""
    batch = oracle["first_batch"]
    encoded = model.encode(batch.token_ids, lengths=batch.lengths)
    weights = torch.zeros_like(oracle["weights"]) if zero_memory else oracle["weights"]
    reasoning = model.reason(
        encoded,
        weights,
        steps=2,
        query_overrides={1: oracle["second_key"]},
    )
    decoding = model.decode(
        encoded,
        reasoning,
        targets=targets,
        max_new_tokens=2,
        teacher_forcing=targets is not None,
    )
    return encoded, reasoning, decoding


def _pc_c_single_hop_oracle(
    model: nn.Module,
    examples: tuple[tuple[Query, Query], ...],
    *,
    device: torch.device,
) -> dict[str, Any]:
    """Build the direct tag-read control paired to the same PC-C worlds."""
    single_queries = tuple(
        Query(second.text, first.expected, tier=2, purpose="single_hop_control")
        for first, second in examples
    )
    batch = batch_queries(single_queries, device=device)
    with torch.no_grad():
        encoded = model.encode(batch.token_ids, lengths=batch.lengths)
        key = model.initial_memory_query(encoded).float()
        heads = None if key.ndim == 2 else key.shape[1]
        tag_value = _oracle_contents(
            single_queries,
            width=key.shape[-1],
            heads=heads,
            device=device,
        )
        weights = model.new_memory(batch=len(examples), device=device)
        weights = model.memory.delta_write(weights, key, tag_value)
    return {
        "queries": single_queries,
        "batch": batch,
        "weights": weights.detach(),
        "key": key.detach(),
        "tag_value": tag_value.detach(),
    }


def _pc_c_single_hop_forward(
    model: nn.Module,
    oracle: dict[str, Any],
    *,
    targets: Optional[torch.Tensor] = None,
    zero_memory: bool = False,
) -> tuple[Any, Any, Any]:
    batch = oracle["batch"]
    encoded = model.encode(batch.token_ids, lengths=batch.lengths)
    weights = torch.zeros_like(oracle["weights"]) if zero_memory else oracle["weights"]
    reasoning = model.reason(encoded, weights, steps=1)
    decoding = model.decode(
        encoded,
        reasoning,
        targets=targets,
        max_new_tokens=2,
        teacher_forcing=targets is not None,
    )
    return encoded, reasoning, decoding


def train_pc_c_step(
    model: nn.Module,
    examples: tuple[tuple[Query, Query], ...],
    optimizer: torch.optim.Optimizer,
    *,
    device: torch.device | str = "cpu",
    grad_clip: float = 1.0,
) -> dict[str, Any]:
    """Train the reader on one oracle-memory, teacher-forced chain batch."""
    if grad_clip <= 0:
        raise ValueError("grad_clip must be positive")
    if any(first.purpose not in ("corrected_two_hop", "two_hop_paraphrase") for first, _ in examples):
        raise ValueError("PC-C training expects tier-2 two-hop queries")
    device = torch.device(device)
    model.train()
    optimizer.zero_grad(set_to_none=True)
    oracle = _pc_c_oracle_memory(model, examples, device=device)
    targets = batch_query_targets(tuple(first for first, _ in examples), device=device)
    _, reasoning, decoding = _pc_c_forward(
        model,
        examples,
        oracle,
        targets=targets.token_ids,
    )
    chain_loss, payload_loss, eos_loss = _payload_and_eos_loss(
        decoding.logits,
        targets.token_ids,
    )
    single_oracle = _pc_c_single_hop_oracle(model, examples, device=device)
    single_targets = batch_query_targets(single_oracle["queries"], device=device)
    _, single_reasoning, single_decoding = _pc_c_single_hop_forward(
        model,
        single_oracle,
        targets=single_targets.token_ids,
    )
    single_loss, single_payload_loss, single_eos_loss = _payload_and_eos_loss(
        single_decoding.logits,
        single_targets.token_ids,
    )
    loss = chain_loss + single_loss
    loss.backward()
    writer_grad = _grad_norm(model.writer.parameters())
    reader_grad = _grad_norm(
        parameter
        for name, parameter in model.named_parameters()
        if not name.startswith("writer.")
    )
    preclip = float(
        torch.nn.utils.clip_grad_norm_(
            [parameter for parameter in model.parameters() if parameter.requires_grad],
            grad_clip,
        ).item()
    )
    optimizer.step()
    first_cosine = F.cosine_similarity(
        reasoning.steps[0].memory_read.float(),
        oracle["second_key"],
        dim=-1,
        eps=1e-8,
    ).mean()
    second_cosine = F.cosine_similarity(
        reasoning.steps[1].memory_read.float(),
        oracle["tag_value"],
        dim=-1,
        eps=1e-8,
    ).mean()
    single_cosine = F.cosine_similarity(
        single_reasoning.steps[0].memory_read.float(),
        single_oracle["tag_value"],
        dim=-1,
        eps=1e-8,
    ).mean()
    return {
        "loss": float(loss.detach().cpu().item()),
        "chain_loss": float(chain_loss.detach().cpu().item()),
        "payload_loss": float(payload_loss.detach().cpu().item()),
        "eos_loss": float(eos_loss.detach().cpu().item()),
        "single_hop_loss": float(single_loss.detach().cpu().item()),
        "single_hop_payload_loss": float(single_payload_loss.detach().cpu().item()),
        "single_hop_eos_loss": float(single_eos_loss.detach().cpu().item()),
        "reader_grad_norm": reader_grad,
        "writer_grad_norm": writer_grad,
        "preclip_grad_norm": preclip,
        "first_hop_read_cosine": float(first_cosine.detach().cpu().item()),
        "second_hop_read_cosine": float(second_cosine.detach().cpu().item()),
        "single_hop_read_cosine": float(single_cosine.detach().cpu().item()),
        "examples": len(examples),
    }


def evaluate_pc_c(
    model: nn.Module,
    *,
    split: str = "validation",
    worlds: int = 16,
    seed: int = 0,
    device: torch.device | str = "cpu",
    threshold: float = PC_C_THRESHOLD,
    deadline: Optional[float] = None,
) -> dict[str, Any]:
    """Score the teacher-forced two-hop reader on held-out tier-2 worlds."""
    if split not in ("validation", "test"):
        raise ValueError("PC-C evaluation must use validation/test split")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0,1]")
    device = torch.device(device)
    model.eval()
    examples = pc_c_examples(split, seed, worlds=worlds)
    oracle = _pc_c_oracle_memory(model, examples, device=device)
    single_oracle = _pc_c_single_hop_oracle(model, examples, device=device)
    with torch.no_grad():
        _, reasoning, decoding = _pc_c_forward(model, examples, oracle)
        _, _, zero_decoding = _pc_c_forward(
            model,
            examples,
            oracle,
            zero_memory=True,
        )
        _, single_reasoning, single_decoding = _pc_c_single_hop_forward(
            model,
            single_oracle,
        )
        _, _, single_zero_decoding = _pc_c_single_hop_forward(
            model,
            single_oracle,
            zero_memory=True,
        )
    records: list[dict[str, Any]] = []
    by_purpose: dict[str, list[int]] = defaultdict(list)
    correct = 0
    zero_correct = 0
    single_correct = 0
    single_zero_correct = 0
    for index, (first, second) in enumerate(examples):
        if deadline is not None and time.monotonic() >= deadline:
            break
        generated = decode_token_ids(decoding.tokens[index].detach().cpu().tolist())
        zero_generated = decode_token_ids(zero_decoding.tokens[index].detach().cpu().tolist())
        single_generated = decode_token_ids(
            single_decoding.tokens[index].detach().cpu().tolist()
        )
        single_zero_generated = decode_token_ids(
            single_zero_decoding.tokens[index].detach().cpu().tolist()
        )
        exact = normalize_text(generated) == normalize_text(first.expected)
        zero_exact = normalize_text(zero_generated) == normalize_text(first.expected)
        single_exact = normalize_text(single_generated) == normalize_text(first.expected)
        single_zero_exact = (
            normalize_text(single_zero_generated) == normalize_text(first.expected)
        )
        correct += int(exact)
        zero_correct += int(zero_exact)
        single_correct += int(single_exact)
        single_zero_correct += int(single_zero_exact)
        by_purpose[first.purpose].append(int(exact))
        records.append({
            "purpose": first.purpose,
            "query": first.text,
            "second_hop_query": second.text,
            "expected": first.expected,
            "generated": generated,
            "exact": exact,
            "zero_w_generated": zero_generated,
            "zero_w_exact": zero_exact,
            "single_hop_generated": single_generated,
            "single_hop_exact": single_exact,
            "single_hop_zero_w_generated": single_zero_generated,
            "single_hop_zero_w_exact": single_zero_exact,
        })
    scored = len(records)
    rate = correct / scored if scored else 0.0
    zero_rate = zero_correct / scored if scored else 0.0
    single_rate = single_correct / scored if scored else 0.0
    single_zero_rate = single_zero_correct / scored if scored else 0.0
    first_cosine = F.cosine_similarity(
        reasoning.steps[0].memory_read.float(),
        oracle["second_key"],
        dim=-1,
        eps=1e-8,
    ).mean()
    second_cosine = F.cosine_similarity(
        reasoning.steps[1].memory_read.float(),
        oracle["tag_value"],
        dim=-1,
        eps=1e-8,
    ).mean()
    single_cosine = F.cosine_similarity(
        single_reasoning.steps[0].memory_read.float(),
        single_oracle["tag_value"],
        dim=-1,
        eps=1e-8,
    ).mean()
    completed = scored == len(examples)
    fixture = None
    if examples:
        fixture_oracle = _pc_c_oracle_memory(model, (examples[0],), device=device)
        with torch.no_grad():
            _, _, fixture_decoding = _pc_c_forward(
                model,
                (examples[0],),
                fixture_oracle,
            )
        fixture = {
            "example": examples[0],
            "weights": fixture_oracle["weights"].detach().cpu(),
            "tokens": fixture_decoding.tokens.detach().cpu(),
            "logits": fixture_decoding.logits.detach().cpu(),
        }
    return {
        "status": "completed" if completed else "time_limit",
        "split": split,
        "worlds": worlds,
        "queries": scored,
        "exact_matches": correct,
        "exact_match_rate": rate,
        "zero_w_exact_match_rate": zero_rate,
        "single_hop_exact_match_rate": single_rate,
        "single_hop_zero_w_exact_match_rate": single_zero_rate,
        "threshold": threshold,
        "threshold_passed": bool(
            completed and rate >= threshold and single_rate >= threshold
        ),
        "by_purpose": {
            purpose: {
                "queries": len(values),
                "exact_match_rate": sum(values) / len(values),
            }
            for purpose, values in sorted(by_purpose.items())
        },
        "first_hop_read_cosine": float(first_cosine.detach().cpu().item()),
        "second_hop_read_cosine": float(second_cosine.detach().cpu().item()),
        "single_hop_read_cosine": float(single_cosine.detach().cpu().item()),
        "teacher_forced_second_hop": True,
        "first_hop_teacher_forced": False,
        "target_used_for_key": False,
        "records": records,
        "_restart_fixture": fixture,
    }


def _restart_pc_c(
    model: nn.Module,
    fixture: dict[str, Any],
    *,
    budget: Any,
    artifact_name: str,
    device: torch.device,
) -> dict[str, Any]:
    config = {
        "checkpoint_role": "chain_positive_control",
        "control": "PC-C",
        "model": _model_config(model),
    }
    path = save_checkpoint(
        budget,
        artifact_name,
        _ControlTheta(model),
        model.writer,
        fixture["weights"][0],
        config=config,
        max_bytes=64 * 1024 * 1024,
    )
    verification_device = torch.device("cpu")
    reference = _fresh_model_like(model).to(verification_device)
    reference.load_state_dict(
        {
            name: tensor.detach().to(verification_device)
            for name, tensor in model.state_dict().items()
        },
        strict=True,
    )
    example = fixture["example"]
    reference_oracle = _pc_c_oracle_memory(
        reference,
        (example,),
        device=verification_device,
    )
    reference_oracle["weights"] = fixture["weights"].to(verification_device)
    reference.eval()
    with torch.no_grad():
        _, _, reference_decoding = _pc_c_forward(
            reference,
            (example,),
            reference_oracle,
        )
    before_tokens = reference_decoding.tokens.detach().cpu()
    before_logits = reference_decoding.logits.detach().cpu()

    fresh = _fresh_model_like(model).to(verification_device)
    restored = load_scored_restart(
        path,
        _ControlTheta(fresh),
        fresh.writer,
        map_location=verification_device,
        max_bytes=64 * 1024 * 1024,
        expected_config=config,
    )
    oracle = _pc_c_oracle_memory(fresh, (example,), device=verification_device)
    oracle["weights"] = restored.W.unsqueeze(0)
    fresh.eval()
    with torch.no_grad():
        _, _, decoding = _pc_c_forward(fresh, (example,), oracle)
    after_tokens = decoding.tokens.detach().cpu()
    after_logits = decoding.logits.detach().cpu()
    try:
        relative = str(path.resolve().relative_to(budget.root.resolve()))
    except (AttributeError, ValueError):
        relative = str(path)
    return {
        "checkpoint": relative,
        "verification_device": str(verification_device),
        "workspace_is_none": restored.workspace is None,
        "identical_tokens": bool(torch.equal(before_tokens, after_tokens)),
        "identical_logits": bool(torch.equal(before_logits, after_logits)),
        "logits_max_abs_diff": float((before_logits - after_logits).abs().max().item()),
    }


def run_pc_c_control(
    *,
    budget: Any,
    seed: int = 0,
    device: str = "cpu",
    steps: int = 2_000,
    seconds: float = 480.0,
    eval_worlds: int = 16,
    learning_rate: float = 3e-4,
    grad_clip: float = 1.0,
    threshold: float = PC_C_THRESHOLD,
    backbone: str = "transformer",
    model: Optional[nn.Module] = None,
) -> dict[str, Any]:
    """Bounded PC-C runner with frozen writer and bit-exact restart check."""
    if steps <= 0:
        raise ValueError("steps must be positive")
    if not 0.0 < seconds <= 600.0:
        raise ValueError("seconds must lie in (0,600]")
    if learning_rate <= 0 or grad_clip <= 0:
        raise ValueError("learning_rate and grad_clip must be positive")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0,1]")
    if backbone not in ("gru", "transformer"):
        raise ValueError("backbone must be 'gru' or 'transformer'")
    if device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was explicitly selected but is unavailable")
        torch_device = torch.device("cuda")
    elif device == "cpu":
        torch_device = torch.device("cpu")
    else:
        raise ValueError("device must be 'cpu' or 'cuda'")

    random.seed(seed)
    torch.manual_seed(seed)
    if torch_device.type == "cuda":
        torch.cuda.manual_seed_all(seed)
        torch.cuda.reset_peak_memory_stats(torch_device)
    if model is None:
        active = MainNetwork() if backbone == "gru" else RecurrentTransformerLearner()
    else:
        active = model
        observed = "transformer" if isinstance(active, RecurrentTransformerLearner) else "gru"
        if backbone != "transformer" and backbone != observed:
            raise ValueError("explicit model and backbone disagree")
        backbone = observed
    active = active.to(torch_device)
    if active.max_reasoning_steps < 2:
        raise ValueError("PC-C requires a model with at least two reasoning steps")
    for parameter in active.writer.parameters():
        parameter.requires_grad_(False)
    trainable = [parameter for parameter in active.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=learning_rate)

    started = time.monotonic()
    # The default transformer's safe checkpoint is tens of MiB. Preserve the
    # measured serialization reserve so the outer 10-minute cap stays real.
    full_transformer = (
        isinstance(active, RecurrentTransformerLearner)
        and active.model_width >= 256
        and active.memory_width >= 128
    )
    checkpoint_reserve = min(120.0 if full_transformer else 2.0, seconds * 0.30)
    evaluation_reserve = min(max(10.0, seconds * 0.10), seconds * 0.25)
    training_deadline = started + max(
        0.0,
        seconds - checkpoint_reserve - evaluation_reserve,
    )
    attempts: list[dict[str, Any]] = []
    for step in range(steps):
        if time.monotonic() >= training_deadline:
            break
        examples = pc_c_examples("train", seed * 1_000_003 + step, worlds=1)
        attempts.append(
            train_pc_c_step(
                active,
                examples,
                optimizer,
                device=torch_device,
                grad_clip=grad_clip,
            )
        )

    deadline = started + seconds
    evaluation = evaluate_pc_c(
        active,
        split="validation",
        worlds=eval_worlds,
        seed=seed,
        device=torch_device,
        threshold=threshold,
        deadline=deadline,
    )
    fixture = evaluation.pop("_restart_fixture")
    restart = None
    if fixture is not None and time.monotonic() < deadline:
        stamp = f"pc-c-{seed}-{time.time_ns()}"
        restart = _restart_pc_c(
            active,
            fixture,
            budget=budget,
            artifact_name=f"artifacts/checkpoint-{stamp}.mlckpt",
            device=torch_device,
        )
    restart_ok = bool(
        restart
        and restart["workspace_is_none"]
        and restart["identical_tokens"]
        and restart["identical_logits"]
    )
    gradients_ok = bool(
        attempts
        and all(row["reader_grad_norm"] > 0.0 for row in attempts)
        and all(row["writer_grad_norm"] == 0.0 for row in attempts)
    )
    threshold_passed = bool(evaluation["threshold_passed"] and restart_ok)
    timed_out = evaluation["status"] == "time_limit" or time.monotonic() >= deadline
    return {
        "status": "time_limit" if timed_out else (
            "completed" if gradients_ok and restart_ok else "failed_controls"
        ),
        "control": "PC-C",
        "backbone": backbone,
        "device": str(torch_device),
        "seed": seed,
        "model": {
            "parameter_count": sum(parameter.numel() for parameter in active.parameters()),
            "trainable_parameter_count": sum(parameter.numel() for parameter in trainable),
            "config": _model_config(active),
        },
        "limits": {
            "steps": steps,
            "wall_clock_seconds": seconds,
            "checkpoint_reserve_seconds": checkpoint_reserve,
            "evaluation_reserve_seconds": evaluation_reserve,
            "eval_worlds": eval_worlds,
        },
        "training": {
            "steps_completed": len(attempts),
            "attempts": _recorded_attempts(attempts[:MAX_RECORDED_PC_C_ATTEMPTS]),
            "attempts_truncated": len(attempts) > MAX_RECORDED_PC_C_ATTEMPTS,
        },
        "controls": {
            "oracle_written_twin_and_constant_entries": True,
            "only_second_hop_key_injected": True,
            "target_used_for_key": False,
            "writer_frozen": True,
            "gradients_ok": gradients_ok,
            "restart_identity": restart_ok,
        },
        "evaluation": evaluation,
        "restart_identity": restart,
        "threshold_passed": threshold_passed,
        "elapsed_seconds": time.monotonic() - started,
        "peak_cuda_memory_bytes": (
            int(torch.cuda.max_memory_allocated(torch_device))
            if torch_device.type == "cuda"
            else None
        ),
    }


def build_in_context_query(episode: Episode, query: Query) -> Query:
    """Place teachings and one query in context without evaluator metadata."""
    if query not in episode.queries:
        raise ValueError("query must belong to the supplied episode")
    text = " ".join(
        [*(teaching.text for teaching in episode.teachings), query.text]
    )
    # expected/tier/purpose remain evaluator-side Query fields. batch_queries
    # serializes only text, and program is deliberately discarded here.
    return Query(
        text=text,
        expected=query.expected,
        tier=query.tier,
        purpose=f"pc_r:{query.purpose}",
        program=None,
    )


def in_context_examples(episode: Episode) -> tuple[Query, ...]:
    return tuple(build_in_context_query(episode, query) for query in episode.queries)


class InContextReader(nn.Module):
    """Same-width reader network whose persistent-memory argument is always zero."""

    def __init__(self, network: Optional[MainNetwork] = None) -> None:
        super().__init__()
        self.network = MainNetwork() if network is None else network
        # The writer is irrelevant to PC-R and must not absorb training signal.
        for parameter in self.network.writer.parameters():
            parameter.requires_grad_(False)

    @property
    def hidden_width(self) -> int:
        return self.network.hidden_width

    def zero_memory(self, batch: int, device: torch.device | str) -> torch.Tensor:
        return self.network.new_memory(batch=batch, device=device)

    def forward(
        self,
        token_ids: torch.Tensor,
        *,
        lengths: torch.Tensor,
        targets: Optional[torch.Tensor] = None,
    ) -> tuple[ModelOutput, torch.Tensor]:
        memory = self.zero_memory(token_ids.shape[0], token_ids.device)
        output = self.network(
            token_ids,
            memory,
            targets=targets,
            lengths=lengths,
            teacher_forcing=True,
        )
        return output, memory

    def generate(
        self,
        token_ids: torch.Tensor,
        *,
        lengths: torch.Tensor,
    ) -> tuple[ModelOutput, torch.Tensor]:
        memory = self.zero_memory(token_ids.shape[0], token_ids.device)
        output = self.network.generate(token_ids, memory, lengths=lengths)
        return output, memory


def _grad_norm(parameters: Iterable[torch.nn.Parameter]) -> float:
    total = 0.0
    for parameter in parameters:
        if parameter.grad is None:
            continue
        value = parameter.grad.detach().float()
        total += float(torch.sum(value * value).item())
    return math.sqrt(total)


def train_pc_r_episode(
    reader: InContextReader,
    episode: Episode,
    optimizer: torch.optim.Optimizer,
    *,
    device: torch.device | str = "cpu",
    grad_clip: float = 1.0,
) -> dict[str, Any]:
    """Take one supervised PC-R step on a train-split tier-2/3 episode."""
    if episode.split != "train":
        raise ValueError("PC-R updates are restricted to split=train")
    if episode.tier not in PC_R_TIERS:
        raise ValueError("PC-R trains only on tiers 2 and 3")
    if grad_clip <= 0:
        raise ValueError("grad_clip must be positive")
    device = torch.device(device)
    reader.train()
    optimizer.zero_grad(set_to_none=True)
    examples = in_context_examples(episode)
    inputs = batch_queries(examples, device=device)
    targets = batch_query_targets(examples, device=device)
    output, memory = reader(
        inputs.token_ids,
        lengths=inputs.lengths,
        targets=targets.token_ids,
    )
    logits = output.decoding.logits
    loss = F.cross_entropy(
        logits.reshape(-1, logits.shape[-1]),
        targets.token_ids.reshape(-1),
        ignore_index=PAD_ID,
    )
    loss.backward()
    encoder_grad = _grad_norm(
        list(reader.network.embedding.parameters())
        + list(reader.network.encoder.parameters())
    )
    writer_grad = _grad_norm(reader.network.writer.parameters())
    preclip = float(
        torch.nn.utils.clip_grad_norm_(
            [parameter for parameter in reader.parameters() if parameter.requires_grad],
            grad_clip,
        ).detach().cpu().item()
    )
    optimizer.step()
    return {
        "seed": episode.seed,
        "episode": episode.episode,
        "tier": episode.tier,
        "examples": len(examples),
        "loss": float(loss.detach().cpu().item()),
        "encoder_grad_norm": encoder_grad,
        "writer_grad_norm": writer_grad,
        "preclip_grad_norm": preclip,
        "zero_memory_max_abs": float(memory.detach().abs().max().cpu().item()),
    }


def _episode_index(seed: int, tier: int, ordinal: int) -> int:
    return (abs(seed) * 1013 + tier * 100_019 + ordinal) % 1_000_000


def evaluate_pc_r(
    reader: InContextReader,
    *,
    split: str = "validation",
    tiers: tuple[int, ...] = PC_R_TIERS,
    worlds_per_tier: int = 8,
    seed: int = 0,
    device: torch.device | str = "cpu",
    threshold: float = PC_R_THRESHOLD,
    deadline: Optional[float] = None,
) -> dict[str, Any]:
    """Greedily score the W-disabled reader on held-out episodes."""
    if split not in ("validation", "test"):
        raise ValueError("PC-R evaluation is restricted to validation/test")
    if not tiers or any(tier not in PC_R_TIERS for tier in tiers):
        raise ValueError("PC-R tiers must be a non-empty subset of 2,3")
    if not 1 <= worlds_per_tier <= MAX_PC_R_WORLDS_PER_TIER:
        raise ValueError(
            f"worlds_per_tier must be in [1,{MAX_PC_R_WORLDS_PER_TIER}]"
        )
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must lie in [0,1]")
    device = torch.device(device)
    reader.eval()
    records: dict[int, list[dict[str, Any]]] = defaultdict(list)
    zero_memory_control = True
    timed_out = False
    with torch.no_grad():
        for tier in tiers:
            for ordinal in range(worlds_per_tier):
                if deadline is not None and time.monotonic() >= deadline:
                    timed_out = True
                    break
                episode = generate_episode(
                    split,
                    _episode_index(seed, tier, ordinal),
                    tier=tier,
                )
                for original, example in zip(
                    episode.queries, in_context_examples(episode)
                ):
                    if deadline is not None and time.monotonic() >= deadline:
                        timed_out = True
                        break
                    inputs = batch_queries([example], device=device)
                    output, memory = reader.generate(
                        inputs.token_ids,
                        lengths=inputs.lengths,
                    )
                    zero_memory_control = zero_memory_control and bool(
                        torch.count_nonzero(memory).item() == 0
                    )
                    generated = decode_token_ids(
                        output.decoding.tokens[0].detach().cpu().tolist()
                    )
                    expected = normalize_text(original.expected)
                    records[tier].append(
                        {
                            "episode": episode.episode,
                            "purpose": original.purpose,
                            "expected": expected,
                            "generated": generated,
                            "exact_match": generated == expected,
                        }
                    )
                if timed_out:
                    break
            if timed_out:
                break

    tier_reports: dict[str, Any] = {}
    for tier in tiers:
        rows = records[tier]
        exact = sum(bool(row["exact_match"]) for row in rows)
        rate = exact / len(rows) if rows else 0.0
        tier_reports[str(tier)] = {
            "queries": len(rows),
            "exact_matches": exact,
            "exact_match_rate": rate,
            "threshold": threshold,
            "threshold_passed": bool(rows) and rate >= threshold,
            "records": rows,
        }
    completed = not timed_out and all(tier_reports[str(tier)]["queries"] for tier in tiers)
    threshold_passed = completed and all(
        tier_reports[str(tier)]["threshold_passed"] for tier in tiers
    )
    return {
        "status": "completed" if completed else "time_limit",
        "control": "PC-R",
        "split": split,
        "tiers": tier_reports,
        "worlds_per_tier": worlds_per_tier,
        "persistent_memory_enabled": False,
        "zero_memory_control": zero_memory_control,
        "threshold": threshold,
        "threshold_passed": threshold_passed,
    }


def run_pc_r_control(
    *,
    seed: int = 0,
    device: str = "cpu",
    tiers: tuple[int, ...] = PC_R_TIERS,
    steps: int = 10_000,
    seconds: float = 480.0,
    eval_worlds: int = 8,
    learning_rate: float = 3e-4,
    grad_clip: float = 1.0,
    threshold: float = PC_R_THRESHOLD,
    reader: Optional[InContextReader] = None,
) -> dict[str, Any]:
    """Run a bounded PC-R train/validation attempt with honest quality status."""
    if steps <= 0:
        raise ValueError("steps must be positive")
    if not 0.0 < seconds <= 600.0:
        raise ValueError("seconds must lie in (0,600]")
    if learning_rate <= 0 or grad_clip <= 0:
        raise ValueError("learning_rate and grad_clip must be positive")
    if not tiers or any(tier not in PC_R_TIERS for tier in tiers):
        raise ValueError("PC-R tiers must be a non-empty subset of 2,3")
    if device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was explicitly selected but is unavailable")
        torch_device = torch.device("cuda")
    elif device == "cpu":
        torch_device = torch.device("cpu")
    else:
        raise ValueError("device must be 'cpu' or 'cuda'")

    random.seed(seed)
    torch.manual_seed(seed)
    if torch_device.type == "cuda":
        torch.cuda.manual_seed_all(seed)
        torch.cuda.reset_peak_memory_stats(torch_device)
    active_reader = InContextReader() if reader is None else reader
    active_reader = active_reader.to(torch_device)
    optimizer = torch.optim.AdamW(
        [parameter for parameter in active_reader.parameters() if parameter.requires_grad],
        lr=learning_rate,
    )
    started = time.monotonic()
    deadline = started + seconds
    evaluation_reserve = min(max(10.0, seconds * 0.25), seconds * 0.5)
    training_deadline = deadline - evaluation_reserve
    attempts: list[dict[str, Any]] = []
    stop_reason = "max_steps"
    for step in range(steps):
        if time.monotonic() >= training_deadline:
            stop_reason = "training_time_budget"
            break
        tier = tiers[step % len(tiers)]
        episode = generate_episode(
            "train", _episode_index(seed, tier, step), tier=tier
        )
        attempts.append(
            train_pc_r_episode(
                active_reader,
                episode,
                optimizer,
                device=torch_device,
                grad_clip=grad_clip,
            )
        )
        if time.monotonic() >= training_deadline and step + 1 < steps:
            stop_reason = "training_time_budget"
            break

    evaluation = evaluate_pc_r(
        active_reader,
        split="validation",
        tiers=tiers,
        worlds_per_tier=eval_worlds,
        seed=seed,
        device=torch_device,
        threshold=threshold,
        deadline=deadline,
    )
    gradients_ok = bool(attempts) and all(
        row["encoder_grad_norm"] > 0.0
        and row["writer_grad_norm"] == 0.0
        and row["zero_memory_max_abs"] == 0.0
        for row in attempts
    )
    completed = evaluation["status"] == "completed" and gradients_ok
    if len(attempts) <= MAX_RECORDED_PC_R_ATTEMPTS:
        recorded_attempts = attempts
    else:
        half = MAX_RECORDED_PC_R_ATTEMPTS // 2
        recorded_attempts = attempts[:half] + attempts[-half:]
    return {
        "status": "completed" if completed else (
            "time_limit" if evaluation["status"] == "time_limit" else "failed_controls"
        ),
        "control": "PC-R",
        "device": str(torch_device),
        "seed": seed,
        "model": {
            "hidden_width": active_reader.hidden_width,
            "parameter_count": sum(p.numel() for p in active_reader.parameters()),
            "trainable_parameter_count": sum(
                p.numel() for p in active_reader.parameters() if p.requires_grad
            ),
        },
        "limits": {
            "optimizer_steps": steps,
            "wall_clock_seconds": seconds,
            "evaluation_reserve_seconds": evaluation_reserve,
        },
        "training": {
            "steps_completed": len(attempts),
            "stop_reason": stop_reason,
            "attempts": recorded_attempts,
            "attempts_recorded": len(recorded_attempts),
            "attempts_truncated": len(recorded_attempts) != len(attempts),
        },
        "controls": {
            "train_split_only": True,
            "held_out_validation": True,
            "persistent_memory_disabled": evaluation["zero_memory_control"],
            "encoder_gradients_and_frozen_writer": gradients_ok,
        },
        "evaluation": evaluation,
        # Quality is deliberately independent from harness completion.
        "threshold_passed": bool(evaluation["threshold_passed"]),
        "elapsed_seconds": time.monotonic() - started,
        "peak_cuda_memory_bytes": (
            int(torch.cuda.max_memory_allocated(torch_device))
            if torch_device.type == "cuda"
            else None
        ),
    }


__all__ = [
    "InContextReader",
    "PC_C_THRESHOLD",
    "PC_E_THRESHOLD",
    "PC_MEMORY_ITEMS",
    "PC_R_THRESHOLD",
    "PC_W_THRESHOLD",
    "build_in_context_query",
    "evaluate_memory_control",
    "evaluate_pc_r",
    "in_context_examples",
    "memory_control_examples",
    "pc_c_examples",
    "run_memory_positive_controls",
    "run_pc_c_control",
    "run_pc_r_control",
    "train_pc_c_step",
    "train_memory_control_step",
    "train_pc_r_episode",
]
