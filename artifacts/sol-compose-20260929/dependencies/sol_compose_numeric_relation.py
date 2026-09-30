"""Learned numeric-relation hypothesis; no dataset, checker or source-model calls.

NumericRelation(source.tok)(tokens, slots, rounds=12) -> [B,2,H,W,125].
The two default reads are rounds 11 and 12, both fully differentiable. Only a
detached copy of the externally supplied token embedding is retained. Columns
are records and rows are fields by default; all cells participate. No record
positions, task selectors, integer comparison, sorting or answer algorithm.

The disclosed talker prior maps digit token IDs 2..11 to values 0..9 and maps
a learned scalar back to digit scores. It supplies numerical semantics beyond
the frozen lexical embedding. NumericTalker is reusable by baseline controls.
Run --selftest for CPU1 random-tensor mechanics, never task training/scoring.
"""
from __future__ import annotations

import math

import torch
from torch import Tensor, nn
from torch.nn import functional as F


VOCAB = 125


class NumericTalker(nn.Module):
    """Fixed vocabulary translation only, with no trainable reasoning weights.

    Two grounded input channels: (value / 10, is_digit). Unknown tokens get
    (0, 0). Only the ordinary DIG vocabulary is grounded; VAL aliases are not.
    decode() replaces DIG scores with one shared quadratic energy, retaining
    every non-DIG lexical score. There is no per-digit learned bias/residual.
    Callers predict scalar, family_score and precision from learned state.
    """

    def __init__(self, digit_token_ids=tuple(range(2, 12))):
        super().__init__()
        ids = tuple(digit_token_ids)
        if (len(ids) != 10 or len(set(ids)) != 10 or
                any(type(i) is not int or not 0 <= i < VOCAB for i in ids)):
            raise ValueError("digit_token_ids must name ten distinct vocabulary IDs in value order")
        values = torch.zeros(VOCAB)
        mask = torch.zeros(VOCAB, dtype=torch.bool)
        values[list(ids)] = torch.arange(10, dtype=torch.float32)
        mask[list(ids)] = True
        self.register_buffer("values", values)
        self.register_buffer("digit_mask", mask)

    def ground(self, tokens: Tensor, *, enabled=True) -> Tensor:
        channels = torch.stack((self.values[tokens] / 10.,
                                self.digit_mask[tokens].to(self.values.dtype)), -1)
        return channels if enabled else torch.zeros_like(channels)

    def decode(self, lexical: Tensor, scalar: Tensor, family_score: Tensor,
               precision: Tensor, *, enabled=True) -> Tensor:
        if not enabled:
            return lexical
        numeric = family_score - precision * (scalar - self.values).square()
        return torch.where(self.digit_mask, numeric, lexical)


class PairCommunication(nn.Module):
    """Generic directed pairs; learned sigmoid gate and signed learned message.

    Both endpoints enter a learned MLP without a prescribed difference,
    comparator, diagonal mask or edge rule. A constant value channel in each
    head exposes learned gate mass, alongside seven learned message channels.
    The raw branch has no length normalization. The other branch divides by
    gate mass. The mean control substitutes that mean in BOTH feature halves.
    """

    def __init__(self, width=48, public_width=8, pair_width=32, heads=4,
                 message_width=7, *, raw_sum=True):
        super().__init__()
        self.heads, self.message_width = heads, message_width
        self.raw_sum = raw_sum
        self.endpoint = nn.Linear(2 * width + public_width, pair_width)
        self.pair = nn.Sequential(nn.Linear(2 * pair_width, pair_width), nn.GELU(),
                                  nn.Linear(pair_width, heads * (1 + message_width)))
        self.aggregate_width = heads * (message_width + 1)

    def statistics(self, context: Tensor) -> tuple[Tensor, Tensor]:
        z = F.gelu(self.endpoint(context))
        b, n, d = z.shape
        pair = torch.cat((z[:, :, None, :].expand(b, n, n, d),
                          z[:, None, :, :].expand(b, n, n, d)), -1)
        pair = self.pair(pair).reshape(b, n, n, self.heads, self.message_width + 1)
        # Accumulate in FP32; cast back only after the reductions.
        gate = pair[..., :1].float().sigmoid()
        value = pair[..., 1:].float().tanh()
        value = torch.cat((value, torch.ones_like(gate)), -1)
        weighted_sum = (gate * value).sum(2)
        mass = gate.sum(2).clamp_min(torch.finfo(torch.float32).eps)
        mean = weighted_sum / mass
        return (weighted_sum.flatten(-2).to(context.dtype),
                mean.flatten(-2).to(context.dtype))

    def forward(self, context: Tensor) -> Tensor:
        total, mean = self.statistics(context)
        first = total if self.raw_sum else mean
        return torch.cat((first, mean), -1)


class PublicMemory(nn.Module):
    """Eight persistent, unnormalized real channels per record, reset per call."""

    def __init__(self, aggregate_width=64, width=48, public_width=8):
        super().__init__()
        self.proposal = nn.Linear(aggregate_width, public_width)
        self.retention = nn.Linear(width + public_width, public_width)

    def forward(self, aggregates: Tensor, hidden: Tensor, public: Tensor) -> Tensor:
        retain = self.retention(torch.cat((hidden, public), -1)).sigmoid()
        return retain * public + (1. - retain) * self.proposal(aggregates)


class NumericRelation(nn.Module):
    """Small shared recurrent expert, with architecture-matched control flags.

    source_embedding: nn.Embedding or floating [125,D] tensor; copied, frozen.
    orientation='columns': W records, H learned field positions; 'rows': vice
    versa. Orientation is constructor configuration, never inferred from data.
    input_grounding/raw_sum are independent controls. output_grounding=False
    is an additional lexical-readout control with identical stored parameters.
    max_fields limits fields only; record count is variable with no size table.

    This is a replacement candidate, NOT a source-preserving residual. It
    retains no source reasoning blocks, source output head or source logits.
    """

    def __init__(self, source_embedding: nn.Embedding | Tensor, *,
                 orientation="columns", input_grounding=True, raw_sum=True,
                 output_grounding=True, max_fields=16, width=48, public_width=8,
                 digit_token_ids=tuple(range(2, 12))):
        super().__init__()
        weight = source_embedding.weight if isinstance(source_embedding, nn.Embedding) else source_embedding
        if (not isinstance(weight, Tensor) or weight.ndim != 2 or weight.shape[0] != VOCAB
                or not weight.is_floating_point()):
            raise ValueError("source_embedding must be a floating [125,D] embedding or tensor")
        if orientation not in ("columns", "rows"):
            raise ValueError("orientation must be columns or rows")
        if any(type(v) is not int or v < 1 for v in (max_fields, width, public_width)):
            raise ValueError("widths and max_fields must be positive integers")
        self.orientation = orientation
        self.input_grounding, self.output_grounding = input_grounding, output_grounding
        self.width, self.public_width, self.max_fields = width, public_width, max_fields
        self.source = nn.Embedding.from_pretrained(weight.detach().clone(), freeze=True)
        self.talker = NumericTalker(digit_token_ids)
        self.source_projection = nn.Linear(weight.shape[1], width)
        self.numeric_projection = nn.Linear(2, width)
        self.field_position = nn.Embedding(max_fields, width)
        self.fill = nn.Embedding(2, width)
        self.field_encoder = nn.Sequential(nn.Linear(width, width), nn.GELU(), nn.Linear(width, width))
        self.expert = PairCommunication(width, public_width, raw_sum=raw_sum)
        aggregates = 2 * self.expert.aggregate_width
        self.public_memory = PublicMemory(aggregates, width, public_width)
        self.recurrent = nn.GRUCell(width + aggregates + public_width, width)
        self.read_features = nn.Linear(2 * width, width)
        self.lexical_head = nn.Linear(width + public_width, VOCAB)
        self.scalar_head = nn.Linear(width + public_width, 1)
        self.family_head = nn.Linear(width + public_width, 1)
        self.precision_raw = nn.Parameter(torch.tensor(math.log(math.expm1(1.))))
        self.to(device=weight.device, dtype=weight.dtype)
        if self.counts()["stored_parameters"] > 150_000:
            raise ValueError("configuration exceeds the 150,000 stored-parameter bound")

    def encode(self, tokens: Tensor, slots: Tensor) -> tuple[Tensor, Tensor]:
        if (tokens.ndim != 3 or tokens.shape != slots.shape or min(tokens.shape) < 1
                or tokens.dtype != torch.long):
            raise ValueError("tokens must be nonempty int64 [B,H,W]; slots must match shape")
        if tokens.device != self.source.weight.device or slots.device != tokens.device:
            raise ValueError("tokens, slots and model must share a device")
        if bool(((tokens < 0) | (tokens >= VOCAB)).any()):
            raise ValueError("token outside full 125-token vocabulary")
        if bool(((slots != 0) & (slots != 1)).any()):
            raise ValueError("slots must contain only zero and one")
        # Transpose views only; caller tensors are never changed.
        t = tokens.transpose(1, 2) if self.orientation == "columns" else tokens
        s = slots.transpose(1, 2) if self.orientation == "columns" else slots
        fields = t.shape[2]
        if fields > self.max_fields:
            raise ValueError("field dimension exceeds configured max_fields")
        field_ids = torch.arange(fields, device=t.device)
        x = (self.source_projection(self.source(t)) + self.fill(s.long()) +
             self.field_position(field_ids)[None, None, :, :] +
             self.numeric_projection(self.talker.ground(t, enabled=self.input_grounding)))
        x = self.field_encoder(F.gelu(x))
        # Every field enters the same learned encoder, then mean pooling.
        # No special input/answer row, digit row or slot-only routing.
        return x, x.mean(2)

    def initial_state(self, anchor: Tensor) -> tuple[Tensor, Tensor]:
        return torch.zeros_like(anchor), anchor.new_zeros(*anchor.shape[:2], self.public_width)

    def step(self, anchor: Tensor, hidden: Tensor, public: Tensor) -> tuple[Tensor, Tensor]:
        aggregates = self.expert(torch.cat((anchor, hidden, public), -1))
        new_public = self.public_memory(aggregates, hidden, public)
        inp = torch.cat((anchor, aggregates, new_public), -1)
        new_hidden = self.recurrent(inp.flatten(0, 1), hidden.flatten(0, 1)).reshape_as(hidden)
        return new_hidden, new_public

    def read(self, fields: Tensor, hidden: Tensor, public: Tensor) -> Tensor:
        h = hidden[:, :, None, :].expand_as(fields)
        z = F.gelu(self.read_features(torch.cat((fields, h), -1)))
        p = public[:, :, None, :].expand(*fields.shape[:3], self.public_width)
        z = torch.cat((z, p), -1)  # Unnormalized public lane directly reaches all heads.
        logits = self.talker.decode(self.lexical_head(z), self.scalar_head(z),
                                    self.family_head(z), F.softplus(self.precision_raw) + 1e-4,
                                    enabled=self.output_grounding)
        return logits.transpose(1, 2) if self.orientation == "columns" else logits

    def forward(self, tokens: Tensor, slots: Tensor, *, rounds=12, grad_rounds=2,
                output_rounds=None) -> Tensor:
        """Return [B,len(output_rounds),H,W,125], default final two reads.

        Earlier recurrence is detached burn-in; at least the last two steps
        retain full gradients when caller grad mode is enabled. grad_rounds=None
        retains the entire rollout. Explicit reads during grad-enabled calls
        must lie inside that window. Under torch.no_grad(), any read is allowed.
        No implicit train/eval mode change, tuning, optimizer or batch cache.
        """
        if type(rounds) is not int or rounds < 2:
            raise ValueError("rounds must be an integer >= 2")
        if grad_rounds is None:
            grad_rounds = rounds
        if type(grad_rounds) is not int or not 2 <= grad_rounds <= rounds:
            raise ValueError("grad_rounds must be None or in [2,rounds]")
        reads = (rounds - 1, rounds) if output_rounds is None else tuple(output_rounds)
        if (not reads or any(type(r) is not int or not 1 <= r <= rounds for r in reads)
                or any(a >= b for a, b in zip(reads, reads[1:]))):
            raise ValueError("output_rounds must be strictly increasing, one-based valid steps")
        track = torch.is_grad_enabled()
        burn = rounds - grad_rounds
        if track and reads[0] <= burn:
            raise ValueError("grad-enabled reads must lie inside the retained gradient window")
        fields, anchor = self.encode(tokens, slots)
        hidden, public = self.initial_state(anchor)
        outputs = []
        for step in range(1, rounds + 1):
            with torch.set_grad_enabled(track and step > burn):
                hidden, public = self.step(anchor, hidden, public)
                if step in reads:
                    outputs.append(self.read(fields, hidden, public))
        return torch.stack(outputs, 1)

    def counts(self, *, batch=1, records=9, fields=2) -> dict:
        stored = sum(p.numel() for p in self.parameters())
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        return {"stored_parameters": stored, "trainable_parameters": trainable,
                "frozen_source_parameters": self.source.weight.numel(),
                "persistent_state_scalars_per_item": records * (self.width + self.public_width),
                "public_state_scalars_per_item": records * self.public_width,
                "input_field_scalars_per_item": records * fields * self.width,
                "one_pair_hidden_tensor_fp32_bytes": 4 * batch * records * records * 32,
                "state_lifetime": "one forward only; initial zeros; no cross-call cache",
                "pair_cost": "dense O(B*records^2); tensor estimate is not peak/autograd memory",
                "orientation": self.orientation, "input_grounding": self.input_grounding,
                "output_grounding": self.output_grounding, "raw_sum": self.expert.raw_sum}


