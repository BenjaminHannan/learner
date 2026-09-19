"""Controlled-English persistent learner with one functional matrix memory.

The persistent state is an external float32 matrix ``W``. Teaching is the
only operation that changes it; reasoning always creates a fresh temporary
workspace and performs a fixed number of adaptive reads.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch
from torch import nn


def _require_finite(name: str, value: torch.Tensor) -> None:
    if value.is_floating_point() and not bool(torch.isfinite(value).all().item()):
        raise ValueError(f"{name} contains non-finite values")


def unit(value: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
    """Return unit vectors along the final dimension, rejecting zero cues."""
    _require_finite("vector", value)
    norm = value.norm(dim=-1, keepdim=True)
    if bool((norm <= eps).any().item()):
        raise ValueError("Cannot normalize a zero-length memory key")
    return value / norm


@dataclass(frozen=True)
class TokenSpec:
    vocab_size: int
    pad_id: int
    eos_id: int


def _task_token_spec() -> TokenSpec:
    """Load token metadata lazily so model import cannot create a task cycle."""
    from . import tasks

    vocab = getattr(tasks, "VOCAB", None)
    if not isinstance(vocab, dict) or not vocab:
        raise ValueError("memorylab.tasks.VOCAB must be a non-empty token->id mapping")
    ids = list(vocab.values())
    if any(not isinstance(index, int) or index < 0 for index in ids):
        raise ValueError("VOCAB ids must be non-negative integers")

    def explicit_id(names: tuple[str, ...]) -> Optional[int]:
        for name in names:
            value = getattr(tasks, name, None)
            if isinstance(value, int):
                return value
        return None

    pad_id = explicit_id(("PAD_ID", "PAD_TOKEN_ID"))
    if pad_id is None:
        for token in ("<pad>", "pad", "PAD"):
            if token in vocab:
                pad_id = vocab[token]
                break
    if pad_id is None:
        raise ValueError("tasks must define a PAD id or PAD token in VOCAB")

    eos_id = explicit_id(("EOS_ID", "EOS_TOKEN_ID"))
    if eos_id is None:
        for token in ("<eos>", "eos", "EOS"):
            if token in vocab:
                eos_id = vocab[token]
                break
    # The old task vocabulary has no EOS token. Reserve one cleanly instead
    # of conflating EOS with PAD; future task code may expose it explicitly.
    if eos_id is None:
        eos_id = max(ids) + 1

    vocab_size = max(max(ids), pad_id, eos_id) + 1
    if pad_id == eos_id:
        raise ValueError("PAD and EOS must have distinct token ids")
    return TokenSpec(vocab_size=vocab_size, pad_id=pad_id, eos_id=eos_id)


@dataclass(frozen=True)
class EncodedSequence:
    states: torch.Tensor       # [batch, time, memory_width]
    pooled: torch.Tensor       # [batch, memory_width]
    mask: torch.Tensor         # [batch, time], True for real tokens
    lengths: torch.Tensor      # [batch]


@dataclass(frozen=True)
class ReasonStepTrace:
    index: int
    query: torch.Tensor        # q_t
    memory_read: torch.Tensor  # W q_t
    workspace_before: torch.Tensor
    workspace_after: torch.Tensor


@dataclass(frozen=True)
class ReasonTrace:
    initial_workspace: torch.Tensor
    steps: tuple[ReasonStepTrace, ...]
    final_workspace: torch.Tensor


@dataclass(frozen=True)
class WriterTrace:
    key: torch.Tensor
    value: torch.Tensor


@dataclass(frozen=True)
class WriteResult:
    weights: torch.Tensor
    encoding: EncodedSequence
    writer: WriterTrace


@dataclass(frozen=True)
class DecodeTrace:
    logits: torch.Tensor       # [batch, generated_time, vocab]
    tokens: torch.Tensor       # greedy predictions, [batch, generated_time]
    attention: torch.Tensor    # [batch, generated_time, query_time]
    lengths: torch.Tensor      # first EOS position + 1, else generated_time


@dataclass(frozen=True)
class ModelOutput:
    encoding: EncodedSequence
    reasoning: ReasonTrace
    decoding: DecodeTrace


class MatrixMemory:
    """One differentiable float32 matrix per batch item."""

    def __init__(self, width: int = 128):
        if width <= 0:
            raise ValueError("Memory width must be positive")
        self.width = width

    def empty(self, batch: int = 1, device: Optional[torch.device | str] = None) -> torch.Tensor:
        if batch <= 0:
            raise ValueError("Batch size must be positive")
        return torch.zeros(batch, self.width, self.width, dtype=torch.float32, device=device)

    def _validate(self, weights: torch.Tensor, batch: Optional[int] = None) -> None:
        if weights.ndim != 3 or weights.shape[1:] != (self.width, self.width):
            raise ValueError(
                f"Memory must have shape [batch,{self.width},{self.width}], got {tuple(weights.shape)}"
            )
        if batch is not None and weights.shape[0] != batch:
            raise ValueError("Memory batch dimension does not match the input batch")
        if weights.dtype != torch.float32:
            raise ValueError("Persistent memory W must remain float32")
        _require_finite("memory", weights)

    def read(self, weights: torch.Tensor, query: torch.Tensor) -> torch.Tensor:
        self._validate(weights, query.shape[0] if query.ndim == 2 else None)
        if query.shape != (weights.shape[0], self.width):
            raise ValueError(f"Query must have shape [batch,{self.width}]")
        if query.device != weights.device:
            raise ValueError("Memory and query must be on the same device")
        q = unit(query).float()
        result = torch.bmm(weights, q.unsqueeze(-1)).squeeze(-1)
        _require_finite("memory read", result)
        return result

    def delta_write(
        self,
        weights: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
    ) -> torch.Tensor:
        """Apply W' = W + (v - Wk) k^T with unit-normalized k."""
        self._validate(weights)
        expected = (weights.shape[0], self.width)
        if key.shape != expected or value.shape != expected:
            raise ValueError(f"Key and value must both have shape {expected}")
        if key.device != weights.device or value.device != weights.device:
            raise ValueError("Memory, key, and value must be on the same device")
        _require_finite("write key", key)
        _require_finite("write value", value)
        k = unit(key).float()
        v = value.float()
        current = torch.bmm(weights, k.unsqueeze(-1)).squeeze(-1)
        error = v - current
        updated = weights + error.unsqueeze(-1) * k.unsqueeze(-2)
        _require_finite("updated memory", updated)
        return updated

    write = delta_write


class Writer(nn.Module):
    """W-blind writer: its only input is the accepted teaching encoding."""

    def __init__(self, width: int = 128):
        super().__init__()
        self.width = width
        # A final recurrent state is a poor place to ask one vector to preserve
        # both an early subject name and a late value token.  Keep the writer
        # W-blind, but let its two outputs attend to different teaching tokens.
        # With zero-initialized scorers this starts as ordinary masked mean
        # pooling, making the change stable and easy to inspect.
        self.key_attention = nn.Linear(width, 1, bias=False)
        self.value_attention = nn.Linear(width, 1, bias=False)
        nn.init.zeros_(self.key_attention.weight)
        nn.init.zeros_(self.value_attention.weight)
        self.key = nn.Sequential(
            nn.Linear(width, width),
            nn.Tanh(),
            nn.Linear(width, width),
        )
        self.value = nn.Sequential(
            nn.Linear(width, width * 2),
            nn.Tanh(),
            nn.Linear(width * 2, width),
            nn.Tanh(),
        )

    @staticmethod
    def _attend(
        teaching: EncodedSequence,
        scorer: nn.Linear,
    ) -> torch.Tensor:
        scores = scorer(teaching.states).squeeze(-1)
        scores = scores.masked_fill(
            ~teaching.mask,
            torch.finfo(scores.dtype).min,
        )
        attention = torch.softmax(scores, dim=-1)
        pooled = torch.bmm(attention.unsqueeze(1), teaching.states).squeeze(1)
        _require_finite("writer attention", attention)
        _require_finite("writer attended teaching", pooled)
        return pooled

    def forward(self, teaching: EncodedSequence) -> WriterTrace:
        if teaching.pooled.ndim != 2 or teaching.pooled.shape[-1] != self.width:
            raise ValueError("Teaching encoding has the wrong hidden width")
        if teaching.states.ndim != 3 or teaching.states.shape[-1] != self.width:
            raise ValueError("Teaching token states have the wrong hidden width")
        key_input = self._attend(teaching, self.key_attention)
        value_input = self._attend(teaching, self.value_attention)
        key = unit(self.key(key_input)).float()
        value = self.value(value_input).float()
        _require_finite("writer key", key)
        _require_finite("writer value", value)
        return WriterTrace(key=key, value=value)


class AttentiveDecoder(nn.Module):
    """Greedy autoregressive decoder with attention over query encoder states."""

    def __init__(
        self,
        vocab_size: int,
        embed_width: int,
        hidden_width: int,
        pad_id: int,
        eos_id: int,
    ):
        super().__init__()
        self.vocab_size = vocab_size
        self.hidden_width = hidden_width
        self.pad_id = pad_id
        self.eos_id = eos_id
        self.embedding = nn.Embedding(vocab_size, embed_width, padding_idx=pad_id)
        self.start = nn.Parameter(torch.zeros(embed_width))
        self.initial = nn.Linear(hidden_width * 2, hidden_width)
        self.attn_states = nn.Linear(hidden_width, hidden_width, bias=False)
        self.attn_query = nn.Linear(hidden_width, hidden_width, bias=False)
        self.attn_score = nn.Linear(hidden_width, 1, bias=False)
        self.cell = nn.GRUCell(embed_width + hidden_width * 2, hidden_width)
        self.output = nn.Sequential(
            nn.Linear(hidden_width * 3, hidden_width),
            nn.Tanh(),
            nn.Linear(hidden_width, vocab_size),
        )

    def _attend(
        self,
        states: torch.Tensor,
        mask: torch.Tensor,
        hidden: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        scores = self.attn_score(
            torch.tanh(self.attn_states(states) + self.attn_query(hidden).unsqueeze(1))
        ).squeeze(-1)
        scores = scores.masked_fill(~mask, torch.finfo(scores.dtype).min)
        weights = torch.softmax(scores, dim=-1)
        context = torch.bmm(weights.unsqueeze(1), states).squeeze(1)
        _require_finite("decoder attention", weights)
        _require_finite("decoder context", context)
        return context, weights

    def forward(
        self,
        query: EncodedSequence,
        workspace: torch.Tensor,
        *,
        targets: Optional[torch.Tensor] = None,
        max_new_tokens: int = 16,
        teacher_forcing: bool = True,
    ) -> DecodeTrace:
        batch = query.pooled.shape[0]
        if workspace.shape != (batch, self.hidden_width):
            raise ValueError("Decoder workspace has the wrong shape")
        if targets is not None:
            if targets.ndim != 2 or targets.shape[0] != batch or targets.shape[1] == 0:
                raise ValueError("Decoder targets must have shape [batch,time] with time > 0")
            if targets.dtype != torch.long:
                raise ValueError("Decoder targets must use torch.long token ids")
            if bool(((targets < 0) | (targets >= self.vocab_size)).any().item()):
                raise ValueError("Decoder target token id is outside the vocabulary")
            steps = targets.shape[1]
        else:
            if max_new_tokens <= 0:
                raise ValueError("max_new_tokens must be positive")
            steps = max_new_tokens

        hidden = torch.tanh(self.initial(torch.cat([query.pooled, workspace], dim=-1)))
        previous = self.start.unsqueeze(0).expand(batch, -1)
        finished = torch.zeros(batch, dtype=torch.bool, device=workspace.device)
        lengths = torch.zeros(batch, dtype=torch.long, device=workspace.device)
        all_logits: list[torch.Tensor] = []
        all_tokens: list[torch.Tensor] = []
        all_attention: list[torch.Tensor] = []

        for step in range(steps):
            context, _ = self._attend(query.states, query.mask, hidden)
            hidden = self.cell(torch.cat([previous, context, workspace], dim=-1), hidden)
            context, attention = self._attend(query.states, query.mask, hidden)
            logits = self.output(torch.cat([hidden, context, workspace], dim=-1))
            _require_finite("decoder logits", logits)
            predicted = logits.argmax(dim=-1)

            visible = torch.where(finished, torch.full_like(predicted, self.pad_id), predicted)
            just_finished = (~finished) & predicted.eq(self.eos_id)
            lengths = torch.where(just_finished, torch.full_like(lengths, step + 1), lengths)
            finished = finished | just_finished

            all_logits.append(logits)
            all_tokens.append(visible)
            all_attention.append(attention)

            if targets is not None and teacher_forcing:
                previous_ids = targets[:, step]
            else:
                previous_ids = torch.where(finished, torch.full_like(predicted, self.pad_id), predicted)
            previous = self.embedding(previous_ids)

            if targets is None and bool(finished.all().item()):
                break

        logits = torch.stack(all_logits, dim=1)
        tokens = torch.stack(all_tokens, dim=1)
        attention = torch.stack(all_attention, dim=1)
        lengths = torch.where(lengths.eq(0), torch.full_like(lengths, tokens.shape[1]), lengths)
        return DecodeTrace(logits=logits, tokens=tokens, attention=attention, lengths=lengths)


class MainNetwork(nn.Module):
    """Recurrent sequence learner with a single persistent matrix memory."""

    def __init__(
        self,
        embed_width: int = 64,
        hidden_width: int = 128,
        reasoning_steps: int = 6,
        max_reasoning_steps: int = 32,
        max_decode_len: int = 16,
        token_spec: Optional[TokenSpec] = None,
    ):
        super().__init__()
        if embed_width <= 0 or hidden_width <= 0:
            raise ValueError("Embedding and hidden widths must be positive")
        if not 1 <= reasoning_steps <= max_reasoning_steps:
            raise ValueError("Reasoning steps must be within the fixed safety bound")
        if max_decode_len <= 0:
            raise ValueError("max_decode_len must be positive")

        spec = _task_token_spec() if token_spec is None else token_spec
        if not 0 <= spec.pad_id < spec.vocab_size or not 0 <= spec.eos_id < spec.vocab_size:
            raise ValueError("TokenSpec ids must lie inside the vocabulary")
        if spec.pad_id == spec.eos_id:
            raise ValueError("PAD and EOS ids must differ")

        self.embed_width = embed_width
        self.hidden_width = hidden_width
        self.reasoning_steps = reasoning_steps
        self.max_reasoning_steps = max_reasoning_steps
        self.max_decode_len = max_decode_len
        self.token_spec = spec
        self.pad_id = spec.pad_id
        self.eos_id = spec.eos_id
        self.vocab_size = spec.vocab_size

        self.embedding = nn.Embedding(spec.vocab_size, embed_width, padding_idx=spec.pad_id)
        self.encoder = nn.GRU(embed_width, hidden_width, batch_first=True)
        self.workspace_initial = nn.Linear(hidden_width, hidden_width)
        self.query = nn.Sequential(
            nn.Linear(hidden_width * 2, hidden_width),
            nn.Tanh(),
            nn.Linear(hidden_width, hidden_width),
        )
        self.reason_cell = nn.GRUCell(hidden_width * 2, hidden_width)
        self.memory = MatrixMemory(hidden_width)
        self.writer = Writer(hidden_width)
        self.decoder = AttentiveDecoder(
            spec.vocab_size,
            embed_width,
            hidden_width,
            spec.pad_id,
            spec.eos_id,
        )

    def _validate_tokens(
        self,
        tokens: torch.Tensor,
        lengths: Optional[torch.Tensor],
        name: str,
    ) -> torch.Tensor:
        if tokens.ndim != 2 or tokens.shape[0] == 0 or tokens.shape[1] == 0:
            raise ValueError(f"{name} tokens must have shape [batch,time] with non-zero dimensions")
        if tokens.dtype != torch.long:
            raise ValueError(f"{name} tokens must use torch.long ids")
        if bool(((tokens < 0) | (tokens >= self.vocab_size)).any().item()):
            raise ValueError(f"{name} contains a token id outside the vocabulary")

        if lengths is None:
            inferred = tokens.ne(self.pad_id).sum(dim=-1)
            positions = torch.arange(tokens.shape[1], device=tokens.device).unsqueeze(0)
            prefix = positions < inferred.unsqueeze(1)
            if not bool(torch.equal(prefix, tokens.ne(self.pad_id))):
                raise ValueError(f"{name} padding must be right-aligned")
            lengths = inferred
        else:
            if lengths.shape != (tokens.shape[0],) or lengths.dtype != torch.long:
                raise ValueError(f"{name} lengths must be torch.long with shape [batch]")
            if lengths.device != tokens.device:
                raise ValueError(f"{name} lengths and tokens must be on the same device")
        if bool(((lengths <= 0) | (lengths > tokens.shape[1])).any().item()):
            raise ValueError(f"{name} lengths must be in [1,time]")
        return lengths

    def new_memory(
        self,
        batch: int = 1,
        device: Optional[torch.device | str] = None,
    ) -> torch.Tensor:
        return self.memory.empty(batch=batch, device=device)

    def encode(
        self,
        tokens: torch.Tensor,
        lengths: Optional[torch.Tensor] = None,
    ) -> EncodedSequence:
        """Encode a right-padded sentence into sequence states and a pooled state."""
        lengths = self._validate_tokens(tokens, lengths, "Input")
        embedded = self.embedding(tokens)
        states, _ = self.encoder(embedded)
        indices = lengths - 1
        pooled = states[torch.arange(tokens.shape[0], device=tokens.device), indices]
        positions = torch.arange(tokens.shape[1], device=tokens.device).unsqueeze(0)
        mask = positions < lengths.unsqueeze(1)
        _require_finite("encoder states", states)
        _require_finite("encoder pooled state", pooled)
        return EncodedSequence(states=states, pooled=pooled, mask=mask, lengths=lengths)

    def reason(
        self,
        encoded: EncodedSequence,
        weights: torch.Tensor,
        *,
        steps: Optional[int] = None,
        query_overrides: Optional[dict[int, torch.Tensor]] = None,
    ) -> ReasonTrace:
        """Reason from a fresh workspace, recomputing q(x,z) at every fixed step."""
        if encoded.pooled.ndim != 2 or encoded.pooled.shape[-1] != self.hidden_width:
            raise ValueError("Encoded query has the wrong hidden width")
        batch = encoded.pooled.shape[0]
        self.memory._validate(weights, batch=batch)
        if weights.device != encoded.pooled.device:
            raise ValueError("Encoded query and memory must be on the same device")
        count = self.reasoning_steps if steps is None else steps
        if not isinstance(count, int) or not 1 <= count <= self.max_reasoning_steps:
            raise ValueError("Reasoning step count is outside the fixed safety bound")
        overrides = {} if query_overrides is None else dict(query_overrides)
        if any(not isinstance(index, int) or not 0 <= index < count for index in overrides):
            raise ValueError("query override index is outside the requested reasoning depth")
        for override in overrides.values():
            if override.shape != (batch, self.hidden_width):
                raise ValueError("query override has the wrong shape")
            if override.device != encoded.pooled.device:
                raise ValueError("query override and encoded query must share a device")
            _require_finite("query override", override)

        x = encoded.pooled
        z = torch.tanh(self.workspace_initial(x))
        _require_finite("initial workspace", z)
        initial = z
        traces: list[ReasonStepTrace] = []
        for index in range(count):
            before = z
            q = unit(self.query(torch.cat([x, before], dim=-1)))
            if index in overrides:
                q = unit(overrides[index]).to(dtype=q.dtype)
            memory_read = self.memory.read(weights, q)
            z = self.reason_cell(torch.cat([x, memory_read.to(dtype=x.dtype)], dim=-1), before)
            _require_finite("workspace", z)
            traces.append(
                ReasonStepTrace(
                    index=index,
                    query=q,
                    memory_read=memory_read,
                    workspace_before=before,
                    workspace_after=z,
                )
            )
        return ReasonTrace(initial_workspace=initial, steps=tuple(traces), final_workspace=z)

    def initial_memory_query(self, encoded: EncodedSequence) -> torch.Tensor:
        """Return the first q(x,z0) without reading or mutating memory."""
        initial = torch.tanh(self.workspace_initial(encoded.pooled))
        return unit(self.query(torch.cat([encoded.pooled, initial], dim=-1)))

    def write_from_teaching(
        self,
        teaching_tokens: torch.Tensor,
        weights: torch.Tensor,
        *,
        lengths: Optional[torch.Tensor] = None,
    ) -> WriteResult:
        """Encode one accepted teaching sentence and make exactly one delta write.

        No target answer, future query, memory contents, or workspace trace is
        passed to ``Writer``. The enclosing method applies its (k, v) to W.
        """
        teaching = self.encode(teaching_tokens, lengths=lengths)
        self.memory._validate(weights, batch=teaching_tokens.shape[0])
        if weights.device != teaching_tokens.device:
            raise ValueError("Teaching tokens and memory must be on the same device")
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
        return self.decoder(
            encoded,
            reasoning.final_workspace,
            targets=targets,
            max_new_tokens=self.max_decode_len if max_new_tokens is None else max_new_tokens,
            teacher_forcing=teacher_forcing,
        )

    def generate(
        self,
        query_tokens: torch.Tensor,
        weights: torch.Tensor,
        *,
        lengths: Optional[torch.Tensor] = None,
        max_new_tokens: Optional[int] = None,
        steps: Optional[int] = None,
    ) -> ModelOutput:
        """Greedily generate from a fresh query workspace; no sampling is used."""
        encoded = self.encode(query_tokens, lengths=lengths)
        reasoning = self.reason(encoded, weights, steps=steps)
        decoding = self.decode(
            encoded,
            reasoning,
            targets=None,
            max_new_tokens=max_new_tokens,
            teacher_forcing=False,
        )
        return ModelOutput(encoding=encoded, reasoning=reasoning, decoding=decoding)

    def forward(
        self,
        query_tokens: torch.Tensor,
        weights: torch.Tensor,
        *,
        targets: Optional[torch.Tensor] = None,
        lengths: Optional[torch.Tensor] = None,
        teacher_forcing: bool = True,
        steps: Optional[int] = None,
    ) -> ModelOutput:
        """Trainer-facing pass with optional deterministic teacher forcing."""
        encoded = self.encode(query_tokens, lengths=lengths)
        reasoning = self.reason(encoded, weights, steps=steps)
        decoding = self.decode(
            encoded,
            reasoning,
            targets=targets,
            teacher_forcing=teacher_forcing,
        )
        return ModelOutput(encoding=encoded, reasoning=reasoning, decoding=decoding)


# Descriptive alias for new trainer code; MainNetwork remains the stable import.
PersistentLearner = MainNetwork
