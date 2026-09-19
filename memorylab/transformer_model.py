"""Depth-recurrent transformer candidate selected by the architecture review.

This is the higher-capacity sibling of ``memorylab.model.MainNetwork``.  It
keeps the same central contract--a sentence-only writer, closed-form delta
writes, fresh temporary state, and pure reads--while replacing the single GRU
workspace with token-structured recurrent transformer state and four memory
heads.  The older GRU remains available as the measured ablation baseline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch
from torch import nn

from .model import (
    DecodeTrace,
    EncodedSequence,
    ReasonStepTrace,
    ReasonTrace,
    TokenSpec,
    WriteResult,
    WriterTrace,
    _require_finite,
    _task_token_spec,
    unit,
)


class MultiHeadMatrixMemory:
    """Four independent fp32 delta-rule matrices by default."""

    def __init__(self, heads: int = 4, width: int = 128) -> None:
        if heads <= 0 or width <= 0:
            raise ValueError("memory heads and width must be positive")
        self.heads = heads
        self.width = width

    @property
    def persistent_shape(self) -> tuple[int, int, int]:
        return (self.heads, self.width, self.width)

    @property
    def bytes_per_item(self) -> int:
        return self.heads * self.width * self.width * 4

    def empty(
        self,
        batch: int = 1,
        device: Optional[torch.device | str] = None,
    ) -> torch.Tensor:
        if batch <= 0:
            raise ValueError("batch size must be positive")
        return torch.zeros(
            batch,
            self.heads,
            self.width,
            self.width,
            dtype=torch.float32,
            device=device,
        )

    def _validate(self, weights: torch.Tensor, batch: Optional[int] = None) -> None:
        expected = (self.heads, self.width, self.width)
        if weights.ndim != 4 or tuple(weights.shape[1:]) != expected:
            raise ValueError(
                f"memory must have shape [batch,{self.heads},{self.width},{self.width}]"
            )
        if batch is not None and weights.shape[0] != batch:
            raise ValueError("memory batch dimension does not match input")
        if weights.dtype != torch.float32:
            raise ValueError("persistent memory W must remain float32")
        _require_finite("multi-head memory", weights)

    def read(self, weights: torch.Tensor, query: torch.Tensor) -> torch.Tensor:
        self._validate(weights, query.shape[0] if query.ndim == 3 else None)
        expected = (weights.shape[0], self.heads, self.width)
        if query.shape != expected:
            raise ValueError(f"query must have shape {expected}")
        if query.device != weights.device:
            raise ValueError("memory and query must share a device")
        result = torch.einsum("bhij,bhj->bhi", weights, unit(query).float())
        _require_finite("multi-head memory read", result)
        return result

    def delta_write(
        self,
        weights: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
    ) -> torch.Tensor:
        self._validate(weights)
        expected = (weights.shape[0], self.heads, self.width)
        if key.shape != expected or value.shape != expected:
            raise ValueError(f"key and value must have shape {expected}")
        if key.device != weights.device or value.device != weights.device:
            raise ValueError("memory, key, and value must share a device")
        k = unit(key).float()
        v = value.float()
        current = torch.einsum("bhij,bhj->bhi", weights, k)
        error = v - current
        updated = weights + torch.einsum("bhi,bhj->bhij", error, k)
        _require_finite("updated multi-head memory", updated)
        return updated

    write = delta_write


class TransformerWriter(nn.Module):
    """Sentence-only one-layer transformer writer for four (key, value) pairs."""

    def __init__(
        self,
        model_width: int = 256,
        memory_heads: int = 4,
        memory_width: int = 128,
        attention_heads: int = 4,
        ffn_width: int = 1024,
    ) -> None:
        super().__init__()
        self.model_width = model_width
        self.memory_heads = memory_heads
        self.memory_width = memory_width
        self.body = nn.TransformerEncoderLayer(
            d_model=model_width,
            nhead=attention_heads,
            dim_feedforward=ffn_width,
            dropout=0.0,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        output_width = memory_heads * memory_width
        self.key = nn.Linear(model_width, output_width)
        self.value = nn.Linear(model_width, output_width)

    def forward(self, teaching: EncodedSequence) -> WriterTrace:
        if teaching.states.ndim != 3 or teaching.states.shape[-1] != self.model_width:
            raise ValueError("teaching encoding has the wrong width")
        states = self.body(
            teaching.states,
            src_key_padding_mask=~teaching.mask,
        )
        # BOS is the writer's CLS token.  It is part of the ordinary sentence
        # encoding, so no target, W, or workspace enters this computation.
        cls = states[:, 0]
        batch = cls.shape[0]
        key = self.key(cls).reshape(batch, self.memory_heads, self.memory_width)
        value = self.value(cls).reshape(batch, self.memory_heads, self.memory_width)
        key = unit(key).float()
        value = torch.tanh(value).float()
        _require_finite("transformer writer key", key)
        _require_finite("transformer writer value", value)
        return WriterTrace(key=key, value=value)


@dataclass(frozen=True)
class TransformerOutput:
    encoding: EncodedSequence
    reasoning: ReasonTrace
    decoding: DecodeTrace


class SlotCrossAttentionDecoder(nn.Module):
    """Bounded non-autoregressive answer slots over the recurrent workspace."""

    def __init__(
        self,
        model_width: int,
        vocab_size: int,
        pad_id: int,
        eos_id: int,
        *,
        attention_heads: int = 4,
        max_slots: int = 16,
    ) -> None:
        super().__init__()
        self.model_width = model_width
        self.vocab_size = vocab_size
        self.pad_id = pad_id
        self.eos_id = eos_id
        self.max_slots = max_slots
        self.slots = nn.Parameter(torch.empty(max_slots, model_width))
        nn.init.normal_(self.slots, std=model_width ** -0.5)
        self.attention = nn.MultiheadAttention(
            model_width,
            attention_heads,
            dropout=0.0,
            batch_first=True,
        )
        self.norm = nn.LayerNorm(model_width)
        self.output = nn.Linear(model_width, vocab_size)

    def forward(
        self,
        states: torch.Tensor,
        mask: torch.Tensor,
        *,
        targets: Optional[torch.Tensor] = None,
        max_new_tokens: Optional[int] = None,
    ) -> DecodeTrace:
        if targets is not None:
            steps = targets.shape[1]
        else:
            steps = self.max_slots if max_new_tokens is None else max_new_tokens
        if not 1 <= steps <= self.max_slots:
            raise ValueError("decode length is outside the bounded slot count")
        batch = states.shape[0]
        slots = self.slots[:steps].unsqueeze(0).expand(batch, -1, -1)
        decoded, attention = self.attention(
            slots,
            states,
            states,
            key_padding_mask=~mask,
            need_weights=True,
            average_attn_weights=True,
        )
        decoded = self.norm(decoded + slots)
        logits = self.output(decoded)
        predicted = logits.argmax(dim=-1)
        positions = torch.arange(steps, device=states.device).unsqueeze(0)
        eos_hits = predicted.eq(self.eos_id)
        has_eos = eos_hits.any(dim=-1)
        first_eos = torch.where(
            has_eos,
            eos_hits.float().argmax(dim=-1).long(),
            torch.full((batch,), steps - 1, dtype=torch.long, device=states.device),
        )
        lengths = torch.where(has_eos, first_eos + 1, torch.full_like(first_eos, steps))
        visible = torch.where(
            positions > first_eos.unsqueeze(1),
            torch.full_like(predicted, self.pad_id),
            predicted,
        )
        _require_finite("slot decoder logits", logits)
        _require_finite("slot decoder attention", attention)
        return DecodeTrace(
            logits=logits,
            tokens=visible,
            attention=attention,
            lengths=lengths,
        )


class RecurrentTransformerLearner(nn.Module):
    """~4.8M token-workspace learner with four persistent delta memories.

    Each recurrent step presents fresh read slots to the shared core. The token
    workspace absorbs those reads and carries prior-step information forward;
    the decoder additionally receives the transformed slots from the *latest*
    read. Reader v4 also carries the previous memory query through a learned
    gate, so extra recurrent steps do not immediately destroy a useful address
    while later workspace state can still propose a different key.
    """

    # Bumped whenever reader semantics change under an unchanged tensor
    # layout, so old checkpoints are rejected instead of silently reused.
    reader_version = 4

    def __init__(
        self,
        model_width: int = 256,
        memory_width: int = 128,
        memory_heads: int = 4,
        attention_heads: int = 4,
        ffn_width: int = 1024,
        reasoning_steps: int = 6,
        max_reasoning_steps: int = 32,
        max_sequence_length: int = 64,
        max_decode_len: int = 16,
        token_spec: Optional[TokenSpec] = None,
    ) -> None:
        super().__init__()
        if not 1 <= reasoning_steps <= max_reasoning_steps:
            raise ValueError("reasoning steps are outside the safety bound")
        if model_width <= 0 or memory_width <= 0 or memory_heads <= 0:
            raise ValueError("model and memory dimensions must be positive")
        if model_width % attention_heads:
            raise ValueError("model width must be divisible by attention heads")
        spec = _task_token_spec() if token_spec is None else token_spec
        self.model_width = model_width
        self.hidden_width = model_width
        self.memory_width = memory_width
        self.memory_heads = memory_heads
        self.attention_heads = attention_heads
        self.ffn_width = ffn_width
        self.reasoning_steps = reasoning_steps
        self.max_reasoning_steps = max_reasoning_steps
        self.max_sequence_length = max_sequence_length
        self.max_decode_len = max_decode_len
        self.token_spec = spec
        self.pad_id = spec.pad_id
        self.eos_id = spec.eos_id
        self.vocab_size = spec.vocab_size

        self.embedding = nn.Embedding(spec.vocab_size, model_width, padding_idx=spec.pad_id)
        # nn.Embedding's N(0,1) default gives token states norm ~sqrt(width),
        # swamping the unit-scale memory tokens; match the positional scale.
        nn.init.normal_(self.embedding.weight, std=model_width ** -0.5)
        with torch.no_grad():
            self.embedding.weight[spec.pad_id].zero_()
        self.positions = nn.Parameter(torch.empty(max_sequence_length, model_width))
        nn.init.normal_(self.positions, std=model_width ** -0.5)
        layer_kwargs = dict(
            d_model=model_width,
            nhead=attention_heads,
            dim_feedforward=ffn_width,
            dropout=0.0,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.prelude = nn.TransformerEncoderLayer(**layer_kwargs)
        self.core = nn.ModuleList(
            [nn.TransformerEncoderLayer(**layer_kwargs) for _ in range(2)]
        )
        self.coda = nn.TransformerEncoderLayer(**layer_kwargs)
        self.memory_query = nn.Linear(model_width, memory_heads * memory_width)
        self.query_update_gate = nn.Linear(memory_width * 2, 1)
        nn.init.zeros_(self.query_update_gate.weight)
        nn.init.constant_(self.query_update_gate.bias, -4.0)
        self.memory_to_token = nn.Linear(memory_width, model_width)
        self.memory_head_embedding = nn.Parameter(
            torch.empty(memory_heads, model_width)
        )
        nn.init.normal_(self.memory_head_embedding, std=model_width ** -0.5)
        self.update_gate = nn.Linear(model_width * 2, model_width)
        self.loop_norm = nn.LayerNorm(model_width)
        self.memory = MultiHeadMatrixMemory(memory_heads, memory_width)
        self.writer = TransformerWriter(
            model_width,
            memory_heads,
            memory_width,
            attention_heads,
            ffn_width,
        )
        self.decoder = SlotCrossAttentionDecoder(
            model_width,
            spec.vocab_size,
            spec.pad_id,
            spec.eos_id,
            attention_heads=attention_heads,
            max_slots=max_decode_len,
        )

    @property
    def persistent_memory_bytes(self) -> int:
        return self.memory.bytes_per_item

    def new_memory(
        self,
        batch: int = 1,
        device: Optional[torch.device | str] = None,
    ) -> torch.Tensor:
        return self.memory.empty(batch=batch, device=device)

    def _validate_tokens(
        self,
        tokens: torch.Tensor,
        lengths: Optional[torch.Tensor],
    ) -> torch.Tensor:
        if tokens.ndim != 2 or tokens.shape[0] == 0 or tokens.shape[1] == 0:
            raise ValueError("tokens must have non-empty [batch,time] shape")
        if tokens.dtype != torch.long:
            raise ValueError("tokens must use torch.long ids")
        if tokens.shape[1] > self.max_sequence_length:
            raise ValueError("input exceeds max_sequence_length")
        if bool(((tokens < 0) | (tokens >= self.vocab_size)).any().item()):
            raise ValueError("token id lies outside vocabulary")
        if lengths is None:
            lengths = tokens.ne(self.pad_id).sum(dim=-1)
        if lengths.shape != (tokens.shape[0],) or lengths.dtype != torch.long:
            raise ValueError("lengths must be torch.long [batch]")
        if bool(((lengths <= 0) | (lengths > tokens.shape[1])).any().item()):
            raise ValueError("invalid sequence length")
        positions = torch.arange(tokens.shape[1], device=tokens.device).unsqueeze(0)
        if not bool(torch.equal(positions < lengths.unsqueeze(1), tokens.ne(self.pad_id))):
            raise ValueError("padding must be right-aligned")
        return lengths

    def encode(
        self,
        tokens: torch.Tensor,
        lengths: Optional[torch.Tensor] = None,
    ) -> EncodedSequence:
        lengths = self._validate_tokens(tokens, lengths)
        width = tokens.shape[1]
        mask = torch.arange(width, device=tokens.device).unsqueeze(0) < lengths.unsqueeze(1)
        states = self.embedding(tokens) + self.positions[:width].unsqueeze(0)
        states = self.prelude(states, src_key_padding_mask=~mask)
        states = states.masked_fill(~mask.unsqueeze(-1), 0.0)
        pooled = states[:, 0]
        _require_finite("transformer encoded states", states)
        return EncodedSequence(states=states, pooled=pooled, mask=mask, lengths=lengths)

    @staticmethod
    def _pool_workspace(workspace: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        counts = mask.sum(dim=-1, keepdim=True).clamp_min(1)
        return (workspace * mask.unsqueeze(-1)).sum(dim=1) / counts

    def reason(
        self,
        encoded: EncodedSequence,
        weights: torch.Tensor,
        *,
        steps: Optional[int] = None,
        query_overrides: Optional[dict[int, torch.Tensor]] = None,
    ) -> ReasonTrace:
        batch, time, width = encoded.states.shape
        if width != self.model_width:
            raise ValueError("encoded workspace has the wrong width")
        self.memory._validate(weights, batch=batch)
        count = self.reasoning_steps if steps is None else steps
        if not isinstance(count, int) or not 1 <= count <= self.max_reasoning_steps:
            raise ValueError("reasoning depth is outside the safety bound")
        overrides = {} if query_overrides is None else dict(query_overrides)
        expected_override_shape = (batch, self.memory_heads, self.memory_width)
        if any(not isinstance(index, int) or not 0 <= index < count for index in overrides):
            raise ValueError("query override index is outside the requested reasoning depth")
        for override in overrides.values():
            if tuple(override.shape) != expected_override_shape:
                raise ValueError("query override has the wrong shape")
            if override.device != encoded.states.device:
                raise ValueError("query override and workspace must share a device")
            _require_finite("query override", override)
        z = encoded.states
        initial = z
        traces: list[ReasonStepTrace] = []
        memory_mask = torch.ones(
            batch,
            self.memory_heads,
            dtype=torch.bool,
            device=z.device,
        )
        combined_mask = torch.cat([encoded.mask, memory_mask], dim=1)
        slot_base = self.memory_head_embedding.unsqueeze(0).expand(batch, -1, -1)
        final_slots = slot_base
        previous_query: Optional[torch.Tensor] = None
        for index in range(count):
            before = z
            pooled = self._pool_workspace(z, encoded.mask)
            proposal = self.memory_query(pooled).reshape(
                batch, self.memory_heads, self.memory_width
            )
            proposal = unit(proposal)
            if index in overrides:
                query = unit(overrides[index]).to(dtype=proposal.dtype)
            elif previous_query is None:
                query = proposal
            else:
                query_gate = torch.sigmoid(
                    self.query_update_gate(torch.cat([previous_query, proposal], dim=-1))
                )
                query = unit((1.0 - query_gate) * previous_query + query_gate * proposal)
            previous_query = query
            memory_read = self.memory.read(weights, query)
            memory_tokens = slot_base + self.memory_to_token(memory_read)
            combined = torch.cat([z, memory_tokens.to(dtype=z.dtype)], dim=1)
            for layer in self.core:
                combined = layer(combined, src_key_padding_mask=~combined_mask)
            candidate = combined[:, :time]
            final_slots = combined[:, time:]
            gate = torch.sigmoid(self.update_gate(torch.cat([before, candidate], dim=-1)))
            z = self.loop_norm((1.0 - gate) * before + gate * candidate)
            z = z.masked_fill(~encoded.mask.unsqueeze(-1), 0.0)
            _require_finite("recurrent transformer workspace", z)
            traces.append(
                ReasonStepTrace(
                    index=index,
                    query=query,
                    memory_read=memory_read,
                    workspace_before=before,
                    workspace_after=z,
                )
            )
        _require_finite("recurrent transformer memory slots", final_slots)
        final = torch.cat([z, final_slots], dim=1)
        return ReasonTrace(initial_workspace=initial, steps=tuple(traces), final_workspace=final)

    def _workspace_mask(self, encoded: EncodedSequence) -> torch.Tensor:
        slots = torch.ones(
            encoded.mask.shape[0],
            self.memory_heads,
            dtype=torch.bool,
            device=encoded.mask.device,
        )
        return torch.cat([encoded.mask, slots], dim=1)

    def initial_memory_query(self, encoded: EncodedSequence) -> torch.Tensor:
        """Return all first-step head queries without reading W."""
        pooled = self._pool_workspace(encoded.states, encoded.mask)
        query = self.memory_query(pooled).reshape(
            encoded.states.shape[0],
            self.memory_heads,
            self.memory_width,
        )
        return unit(query)

    def write_from_teaching(
        self,
        teaching_tokens: torch.Tensor,
        weights: torch.Tensor,
        *,
        lengths: Optional[torch.Tensor] = None,
    ) -> WriteResult:
        teaching = self.encode(teaching_tokens, lengths=lengths)
        self.memory._validate(weights, batch=teaching_tokens.shape[0])
        proposal = self.writer(teaching)
        updated = self.memory.delta_write(weights, proposal.key, proposal.value)
        return WriteResult(weights=updated, encoding=teaching, writer=proposal)

    def decode(
        self,
        encoded: EncodedSequence,
        reasoning: ReasonTrace,
        *,
        targets: Optional[torch.Tensor] = None,
        max_new_tokens: Optional[int] = None,
        teacher_forcing: bool = True,
    ) -> DecodeTrace:
        del teacher_forcing
        mask = self._workspace_mask(encoded)
        states = self.coda(
            reasoning.final_workspace,
            src_key_padding_mask=~mask,
        )
        return self.decoder(
            states,
            mask,
            targets=targets,
            max_new_tokens=max_new_tokens,
        )

    def forward(
        self,
        query_tokens: torch.Tensor,
        weights: torch.Tensor,
        *,
        targets: Optional[torch.Tensor] = None,
        lengths: Optional[torch.Tensor] = None,
        teacher_forcing: bool = True,
        steps: Optional[int] = None,
    ) -> TransformerOutput:
        encoded = self.encode(query_tokens, lengths=lengths)
        reasoning = self.reason(encoded, weights, steps=steps)
        decoding = self.decode(
            encoded,
            reasoning,
            targets=targets,
            teacher_forcing=teacher_forcing,
        )
        return TransformerOutput(encoded, reasoning, decoding)

    def generate(
        self,
        query_tokens: torch.Tensor,
        weights: torch.Tensor,
        *,
        lengths: Optional[torch.Tensor] = None,
        max_new_tokens: Optional[int] = None,
        steps: Optional[int] = None,
    ) -> TransformerOutput:
        encoded = self.encode(query_tokens, lengths=lengths)
        reasoning = self.reason(encoded, weights, steps=steps)
        decoding = self.decode(
            encoded,
            reasoning,
            max_new_tokens=max_new_tokens,
            teacher_forcing=False,
        )
        return TransformerOutput(encoded, reasoning, decoding)


__all__ = [
    "MultiHeadMatrixMemory",
    "RecurrentTransformerLearner",
    "SlotCrossAttentionDecoder",
    "TransformerOutput",
    "TransformerWriter",
]
