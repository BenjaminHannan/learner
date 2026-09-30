"""Syntactic atom binding and learned record/atom recurrence, development only.

No dataset, environment, checker, or baseline-model imports. A caller supplies
the qualified source module/embedding and explicit per-call translated inputs.
Run this file with --selftest-out for small synthetic CPU mechanics checks only.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, fields
from typing import Sequence

import torch
from torch import Tensor, nn
from torch.nn import functional as F

WIDTH, SOURCE_WIDTH, VOCAB, PORTS = 64, 256, 125, 16
ATOM_START, ATOM_COUNT = 75, 40  # Lexical namespace, not label semantics.
RESIDUAL_PARAMETERS = 149_727


@dataclass(frozen=True)
class TranslatedBatch:
    """All identity is per-call; token_ids contains 0 in every atom span.

    B: [batch,rows,ports,atoms], atom_mask: [batch,atoms]. Both are bool.
    atom_spans and field_mask: [batch,rows,ports]. Slots has the same shape.
    Padded atoms/fields have no incidence. No raw atom labels are retained.
    """

    token_ids: Tensor
    slots: Tensor
    B: Tensor
    atom_mask: Tensor
    atom_spans: Tensor
    field_mask: Tensor

    def to(self, device) -> TranslatedBatch:
        return TranslatedBatch(**{f.name: getattr(self, f.name).to(device) for f in fields(self)})

    def same_atom(self, dtype=torch.float32) -> Tensor:
        b, r, p, a = self.B.shape
        incidence = self.B.reshape(b, r * p, a).to(dtype)
        return incidence @ incidence.transpose(1, 2)


class Translator(nn.Module):
    """Equality grouping only. Random handle permutation uses a CPU generator.

    The collapsed label vector is a fixed registered buffer. This module owns
    no parameters, embedding table, previous batch, or random-generator state.
    """

    def __init__(self, source_embedding: nn.Embedding | Tensor):
        super().__init__()
        weight = source_embedding.weight if isinstance(source_embedding, nn.Embedding) else source_embedding
        if weight.shape != (VOCAB, SOURCE_WIDTH):
            raise ValueError("source embedding must have shape [125,256]")
        self.register_buffer("collapsed_label", weight.detach()[ATOM_START:ATOM_START + ATOM_COUNT].mean(0).clone())

    def forward(self, tokens: Tensor, slots: Tensor, *, generator: torch.Generator | None = None,
                pad_atoms_to: int | None = None, field_mask: Tensor | None = None) -> TranslatedBatch:
        if tokens.ndim != 3 or any(n < 1 for n in tokens.shape):
            raise ValueError("tokens must be a nonempty [batch,rows,ports] grid")
        if tokens.dtype != torch.long or slots.shape != tokens.shape or slots.device != tokens.device:
            raise ValueError("tokens must be int64; slots must have identical shape/device")
        if tokens.shape[2] > PORTS or bool(((tokens < 0) | (tokens >= VOCAB)).any()):
            raise ValueError("maximum 16 ports and vocabulary 0..124")
        if bool(((slots != 0) & (slots != 1)).any()):
            raise ValueError("slots must be binary")
        valid = torch.ones_like(tokens, dtype=torch.bool) if field_mask is None else field_mask
        if valid.shape != tokens.shape or valid.device != tokens.device or valid.dtype != torch.bool:
            raise ValueError("field_mask must be bool with token shape/device")
        spans = (tokens >= ATOM_START) & (tokens < ATOM_START + ATOM_COUNT) & valid
        handle_grids, counts = [], []
        for row, is_atom in zip(tokens, spans):
            labels, inverse = torch.unique(row[is_atom], sorted=True, return_inverse=True)
            n = labels.numel()
            permutation = torch.randperm(n, generator=generator, device="cpu").to(tokens.device)
            handles = torch.full_like(row, -1)
            handles[is_atom] = permutation[inverse]
            handle_grids.append(handles)
            counts.append(n)
        atoms = max(counts)
        if pad_atoms_to is not None:
            if not isinstance(pad_atoms_to, int) or pad_atoms_to < atoms:
                raise ValueError("pad_atoms_to must be an integer >= the largest atom count")
            atoms = pad_atoms_to
        ids = torch.arange(atoms, device=tokens.device)
        B = torch.stack(handle_grids)[..., None] == ids
        atom_mask = ids[None] < torch.tensor(counts, device=tokens.device)[:, None]
        # Even the structured batch cannot leak the original label identities.
        sanitized = tokens.masked_fill(spans | ~valid, 0)
        return TranslatedBatch(sanitized, slots.long().clone(), B, atom_mask, spans, valid.clone())

    def embedding_fields(self, batch: TranslatedBatch, embedding: nn.Embedding) -> Tensor:
        """[batch,rows,ports,256], token-only; NO source slot embedding added.

        Literal embeddings retain autograd for the adaptable dense control.
        The residual detaches this tensor to enforce its frozen-source contract.
        """
        if embedding.weight.shape != (VOCAB, SOURCE_WIDTH):
            raise ValueError("embedding must have shape [125,256]")
        ordinary = embedding(batch.token_ids)
        collapsed = self.collapsed_label.to(device=ordinary.device, dtype=ordinary.dtype)
        return torch.where(batch.atom_spans[..., None], collapsed, ordinary) * batch.field_mask[..., None]


def _rounds(rounds: int, output_rounds: Sequence[int] | None) -> tuple[int, ...]:
    if not isinstance(rounds, int) or rounds < 1:
        raise ValueError("rounds must be positive")
    selected = tuple(range(1, rounds + 1)) if output_rounds is None else tuple(output_rounds)
    if not selected or any(not isinstance(r, int) or r < 1 or r > rounds for r in selected):
        raise ValueError("output_rounds must be nonempty one-based rounds within the rollout")
    if tuple(sorted(set(selected))) != selected:
        raise ValueError("output_rounds must be strictly increasing")
    return selected


@dataclass(frozen=True)
class ResidualResult:
    logits: Tensor  # [batch,selected_rounds,rows,ports,125]
    output_rounds: tuple[int, ...]
    records: Tensor  # final [batch,rows,64]
    atoms: Tensor  # final [batch,atoms,64], padding exactly zero


class RecordAtomResidual(nn.Module):
    """Exactly 149,727 parameters in all arms; no source parameters owned.

    forward(fields,B,slots,L0,atom_mask=...) returns full-vocabulary logits.
    Select late output_rounds without detaching ANY earlier recurrent steps.
    Valid arms: bound, dense, overwrite. State resets on every forward/run call.
    """

    def __init__(self, arm: str = "bound"):
        super().__init__()
        if arm not in ("bound", "dense", "overwrite"):
            raise ValueError("arm must be bound, dense or overwrite")
        self.arm = arm
        self.field = nn.Linear(SOURCE_WIDTH, WIDTH)
        self.port = nn.Embedding(PORTS, WIDTH)
        self.fill = nn.Embedding(2, WIDTH)
        self.read_score = nn.Sequential(nn.Linear(3 * WIDTH, 32), nn.GELU(), nn.Linear(32, 1))
        self.write_score = nn.Sequential(nn.Linear(3 * WIDTH, 32), nn.GELU(), nn.Linear(32, 1))
        self.beta_read = nn.Parameter(torch.zeros(PORTS))
        self.beta_write = nn.Parameter(torch.zeros(PORTS))
        self.read_value = nn.Linear(WIDTH, WIDTH)
        self.write_value = nn.Linear(2 * WIDTH, WIDTH)
        self.record_gru = nn.GRUCell(3 * WIDTH, WIDTH)
        self.atom_gru = nn.GRUCell(2 * WIDTH, WIDTH)
        self.head = nn.Sequential(nn.Linear(3 * WIDTH, WIDTH), nn.GELU(), nn.Linear(WIDTH, VOCAB))
        with torch.no_grad():
            for gru in (self.record_gru, self.atom_gru):
                gru.bias_ih[WIDTH:2 * WIDTH].add_(1.)
                gru.bias_hh[WIDTH:2 * WIDTH].zero_()
            self.head[-1].weight.zero_()
            self.head[-1].bias.zero_()
        assert self.weight_count() == RESIDUAL_PARAMETERS

    def weight_count(self) -> int:
        return sum(p.numel() for p in self.parameters())

    @staticmethod
    def _scores(module: nn.Sequential, records: Tensor, feature: Tensor, atoms: Tensor) -> Tensor:
        # Exactly the specified concat MLP, factorizing its FIRST linear map to
        # avoid materializing [batch,rows,ports,atoms,192]. No parameter change.
        rp = torch.cat((records[:, :, None].expand_as(feature), feature), -1)
        first = module[0]
        left = F.linear(rp, first.weight[:, :2 * WIDTH], first.bias)
        right = F.linear(atoms, first.weight[:, 2 * WIDTH:])
        hidden = module[1](left[..., None, :] + right[:, None, None, :, :])
        return module[2](hidden).squeeze(-1)

    def _gates(self, module, records, feature, atoms, incidence, beta, allowed):
        score = self._scores(module, records, feature, atoms)
        score = score + beta[:feature.shape[2]][None, None, :, None] * incidence
        gates = score.sigmoid() * allowed
        return gates if self.arm == "dense" else gates * incidence

    def run(self, source_fields: Tensor, B: Tensor, slots: Tensor, L0: Tensor, *,
            atom_mask: Tensor, field_mask: Tensor | None = None, rounds: int = 12,
            output_rounds: Sequence[int] | None = None) -> ResidualResult:
        selected = _rounds(rounds, output_rounds)
        if source_fields.ndim != 4 or source_fields.shape[-1] != SOURCE_WIDTH:
            raise ValueError("source_fields must have shape [batch,rows,ports,256]")
        b, r, p, _ = source_fields.shape
        if min(b, r, p) < 1 or p > PORTS or slots.shape != (b, r, p):
            raise ValueError("nonempty fields with <=16 ports and matching slots required")
        if B.ndim != 4 or B.shape[:3] != (b, r, p) or B.dtype != torch.bool:
            raise ValueError("B must be bool [batch,rows,ports,atoms]")
        a = B.shape[-1]
        if atom_mask.shape != (b, a) or atom_mask.dtype != torch.bool:
            raise ValueError("atom_mask must be bool [batch,atoms]")
        if L0.shape != (b, r, p, VOCAB):
            raise ValueError("L0 must be [batch,rows,ports,125]")
        valid = torch.ones((b, r, p), dtype=torch.bool, device=B.device) if field_mask is None else field_mask
        if valid.shape != (b, r, p) or valid.dtype != torch.bool:
            raise ValueError("field_mask must be bool [batch,rows,ports]")
        if any(t.device != source_fields.device for t in (B, slots, L0, atom_mask, valid)):
            raise ValueError("all inputs must share a device")
        if L0.dtype != source_fields.dtype or source_fields.dtype != self.field.weight.dtype:
            raise ValueError("fields, L0 and model must share floating-point dtype")
        if bool(((slots != 0) & (slots != 1)).any()):
            raise ValueError("slots must be binary")
        allowed = valid[..., None] & atom_mask[:, None, None, :]
        if bool((B & ~allowed).any()) or bool((B.sum(-1) > 1).any()):
            raise ValueError("each valid field binds at most one nonpadded atom")
        incidence = B.to(source_fields.dtype)
        feature = F.gelu(self.field(source_fields.detach()) +
                         self.port(torch.arange(p, device=B.device))[None, None] + self.fill(slots.long()))
        feature = feature * valid[..., None]
        context = feature.sum(2) / valid.sum(2).clamp_min(1)[..., None]
        records = context
        atoms = feature.new_zeros(b, a, WIDTH)
        row_mask = valid.any(2)[..., None]
        outputs = []
        for index in range(1, rounds + 1):
            gr = self._gates(self.read_score, records, feature, atoms, incidence, self.beta_read, allowed)
            sum_r = gr.sum(2) @ self.read_value(atoms)
            mass_r = gr.sum((2, 3))[..., None]
            rin = torch.cat((context, sum_r / 8., sum_r / mass_r.clamp_min(1.)), -1)
            records = self.record_gru(rin.reshape(b * r, 3 * WIDTH),
                                      records.reshape(b * r, WIDTH)).reshape(b, r, WIDTH) * row_mask
            gw = self._gates(self.write_score, records, feature, atoms, incidence, self.beta_write, allowed)
            value = self.write_value(torch.cat((records[:, :, None].expand_as(feature), feature), -1))
            sum_a = gw.reshape(b, r * p, a).transpose(1, 2) @ value.reshape(b, r * p, WIDTH)
            mass_a = gw.sum((1, 2))[..., None]
            ain = torch.cat((sum_a / 8., sum_a / mass_a.clamp_min(1.)), -1)
            if a:
                previous = torch.zeros_like(atoms) if self.arm == "overwrite" else atoms
                atoms = self.atom_gru(ain.reshape(b * a, 2 * WIDTH),
                                      previous.reshape(b * a, WIDTH)).reshape(b, a, WIDTH)
                atoms = atoms * atom_mask[..., None]
            if index in selected:
                bound = (incidence.reshape(b, r * p, a) @ atoms).reshape(b, r, p, WIDTH)
                delta = self.head(torch.cat((records[:, :, None].expand_as(feature), feature, bound), -1))
                outputs.append(L0.detach() + delta * valid[..., None])
        return ResidualResult(torch.stack(outputs, 1), selected, records, atoms)

    def forward(self, source_fields, B, slots, L0, *, atom_mask, field_mask=None,
                rounds=12, output_rounds=None) -> Tensor:
        return self.run(source_fields, B, slots, L0, atom_mask=atom_mask, field_mask=field_mask,
                        rounds=rounds, output_rounds=output_rounds).logits

    def training_logits(self, source_fields, B, slots, L0, *, atom_mask, field_mask=None,
                        rounds=12) -> Tensor:
        if rounds < 2:
            raise ValueError("last-two supervision requires at least two rounds")
        return self(source_fields, B, slots, L0, atom_mask=atom_mask, field_mask=field_mask,
                    rounds=rounds, output_rounds=(rounds - 1, rounds))


