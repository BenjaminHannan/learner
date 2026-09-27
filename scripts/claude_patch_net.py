#!/usr/bin/env python3
"""Feedback-written rank-8 patch on the xfer-1 loop, without kind embeddings.

The caller owns episode construction, losses, optimizers, sleep, and patch lifetime.
In particular, pass the returned PatchState into later puzzles; only the recurrent
working state resets between puzzles. All parameters and patch coefficients count
toward the model's persistent-size budget.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import NamedTuple

import torch
from torch import nn
from torch.nn import functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402


WIDTH = 256
HEADS = 8
LAYERS = 2
MLP_WIDTH = 896
RANK = 8
CLIP = 4
WINDOW = 1
TRAIN_ROUNDS = 16
GRAD_ROUNDS = 6
MAX_ROUNDS = 48
RHO = 0.9
PATCH_EFFECT = 0.25
# Each factor has RANK * WIDTH entries, so clipping every entry to this
# interval gives ||A||_F <= 1 and ||B||_F <= 1. Consequently
# ||PATCH_EFFECT * sigmoid(g) * B A h|| <= PATCH_EFFECT * ||h|| per token.
SLOT_LIMIT = 1.0 / math.sqrt(RANK * WIDTH)
REFERENCE_COEFFICIENTS = 1_646_750


class PatchState(NamedTuple):
    """Functional persistent state: A [batch, rank, width], B [batch, width, rank]."""

    A: torch.Tensor
    B: torch.Tensor

    def detach(self) -> "PatchState":
        """Truncate older writes while retaining their values."""
        return PatchState(self.A.detach(), self.B.detach())


class Block(nn.Module):
    def __init__(self, d: int, heads: int, mlp_width: int) -> None:
        super().__init__()
        self.heads = heads
        self.ln1 = nn.LayerNorm(d)
        self.ln2 = nn.LayerNorm(d)
        self.qkv = nn.Linear(d, 3 * d)
        self.out = nn.Linear(d, d)
        self.mlp = nn.Sequential(nn.Linear(d, mlp_width), nn.GELU(), nn.Linear(mlp_width, d))
        self.br = nn.Parameter(torch.zeros(heads, 2 * CLIP + 1))
        self.bc = nn.Parameter(torch.zeros(heads, 2 * CLIP + 1))

    def forward(self, x: torch.Tensor, dr: torch.Tensor, dc: torch.Tensor) -> torch.Tensor:
        batch, length, width = x.shape
        q, k, v = self.qkv(self.ln1(x)).reshape(batch, length, 3, self.heads, width // self.heads).permute(2, 0, 3, 1, 4)
        bias = self.br[:, dr] + self.bc[:, dc]
        far = (dc - CLIP).abs() > WINDOW
        narrow = torch.arange(self.heads, device=x.device)[:, None, None] < self.heads // 2
        bias = bias.masked_fill(narrow & far, float("-inf"))[None, :, :, :]
        # Explicit attention supports second derivatives needed by the loop MAML control.
        scores = (q @ k.transpose(-2, -1)) / math.sqrt(width // self.heads)
        attention = torch.softmax(scores + bias, dim=-1)
        x = x + self.out((attention @ v).transpose(1, 2).reshape(batch, length, width))
        return x + self.mlp(self.ln2(x))


class Net(nn.Module):
    """Size-matched patch, full loop, and eight-layer plain arms."""

    def __init__(self, arm: str = "patch") -> None:
        super().__init__()
        if arm not in ("patch", "loop", "plain"):
            raise ValueError("arm must be 'patch', 'loop', or 'plain'")
        self.arm = arm
        d, layers, mlp_width = {
            "patch": (WIDTH, LAYERS, MLP_WIDTH),
            "loop": (WIDTH, LAYERS, 4 * WIDTH),
            "plain": (128, 8, 525),
        }[arm]
        self.width = d
        self.tok = nn.Embedding(E.VOCAB, d)
        self.slot = nn.Embedding(2, d)
        self.blocks = nn.ModuleList(Block(d, HEADS, mlp_width) for _ in range(layers))
        self.ln_state = nn.LayerNorm(d) if arm != "plain" else None
        self.ln_out = nn.LayerNorm(d)
        self.head = nn.Linear(d, E.VOCAB)
        self.halt = nn.Linear(d, 1) if arm != "plain" else None
        if arm == "patch":
            self.gate = nn.Linear(2 * WIDTH, 1)
            self.rank_slot = nn.Embedding(RANK, WIDTH)
            self.writer = nn.Sequential(
                nn.Linear(2 * WIDTH, WIDTH // 2), nn.GELU(), nn.Linear(WIDTH // 2, 2 * WIDTH)
            )

    def zero_patch(self, batch_size: int = 1, device: torch.device | str | None = None) -> PatchState:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        if device is None:
            device = self.tok.weight.device
        return PatchState(
            torch.zeros(batch_size, RANK, WIDTH, device=device, dtype=torch.float32),
            torch.zeros(batch_size, WIDTH, RANK, device=device, dtype=torch.float32),
        )

    def initial_patch(self, device: torch.device | str, batch_size: int = 1) -> PatchState:
        return self.zero_patch(batch_size=batch_size, device=device)

    @staticmethod
    def offsets(height: int, width: int, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
        row = torch.arange(height, device=device).repeat_interleave(width)
        col = torch.arange(width, device=device).repeat(height)
        dr = (row[:, None] - row[None, :]).clamp(-CLIP, CLIP) + CLIP
        dc = (col[:, None] - col[None, :]).clamp(-CLIP, CLIP) + CLIP
        return dr, dc

    def embed(self, tokens: torch.Tensor, slot: torch.Tensor) -> tuple[torch.Tensor, tuple[torch.Tensor, torch.Tensor]]:
        if tokens.shape != slot.shape or tokens.ndim != 3:
            raise ValueError("tokens and slot must have equal [batch, height, width] shapes")
        batch, height, width = tokens.shape
        e = self.tok(tokens.reshape(batch, -1)) + self.slot(slot.reshape(batch, -1))
        return e, self.offsets(height, width, tokens.device)

    def step(
        self, h: torch.Tensor, e: torch.Tensor, dr: torch.Tensor, dc: torch.Tensor,
        patch: PatchState | None = None,
    ) -> torch.Tensor:
        if self.arm == "plain":
            raise ValueError("plain arm has no recurrent step")
        z = h + e
        for block in self.blocks:
            z = block(z, dr, dc)
        z = self.ln_state(z)
        if patch is not None and self.arm == "patch":
            if patch.A.shape[0] not in (1, h.shape[0]) or patch.B.shape[0] not in (1, h.shape[0]):
                raise ValueError("patch batch must be 1 or match the puzzle batch")
            low = torch.einsum("btd,brd->btr", h, patch.A)
            delta = torch.einsum("btr,bdr->btd", low, patch.B)
            applicability = torch.sigmoid(self.gate(torch.cat((e, h), dim=-1)))
            z = z + PATCH_EFFECT * applicability * delta
        return z

    def read(self, h: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor | None]:
        z = self.ln_out(h)
        q = self.halt(z.mean(dim=1)).squeeze(-1) if self.halt is not None else None
        return self.head(z), q

    def plain_forward(self, tokens: torch.Tensor, slot: torch.Tensor) -> torch.Tensor:
        if self.arm != "plain":
            raise ValueError("plain_forward requires Net('plain')")
        h, (dr, dc) = self.embed(tokens, slot)
        for block in self.blocks:
            h = block(h, dr, dc)
        return self.read(h)[0]

    def _run_train(
        self, tokens: torch.Tensor, slot: torch.Tensor, n_free: int, n_grad: int,
        patch: PatchState | None,
    ) -> tuple[list[tuple[torch.Tensor, torch.Tensor]], torch.Tensor]:
        if n_free < 0 or n_grad < 1 or n_free + n_grad > MAX_ROUNDS:
            raise ValueError("require n_free >= 0, n_grad >= 1, total rounds <= 48")
        e, (dr, dc) = self.embed(tokens, slot)
        h = torch.zeros_like(e)
        with torch.no_grad():
            for _ in range(n_free):
                h = self.step(h, e.detach(), dr, dc, patch)
        h = h.detach()
        outputs = []
        for _ in range(n_grad):
            h = self.step(h, e, dr, dc, patch)
            outputs.append(self.read(h))
        return outputs, h

    def loop_train(
        self, tokens: torch.Tensor, slot: torch.Tensor, n_free: int, n_grad: int,
        patch: PatchState | None = None,
    ) -> list[tuple[torch.Tensor, torch.Tensor | None]]:
        if self.arm == "plain":
            return [(self.plain_forward(tokens, slot), None)]
        return self._run_train(tokens, slot, n_free, n_grad, patch)[0]

    def forward(
        self, tokens: torch.Tensor, slot: torch.Tensor, n_free: int = 0, n_grad: int = 1,
        patch: PatchState | None = None,
    ) -> list[tuple[torch.Tensor, torch.Tensor | None]]:
        """Forward wrapper suitable for torch.func.functional_call on ordinary weights."""
        return self.loop_train(tokens, slot, n_free, n_grad, patch)

    def write_support(
        self, tokens: torch.Tensor, slot: torch.Tensor, target: torch.Tensor,
        patch: PatchState, n_free: int, n_grad: int,
    ) -> PatchState:
        """Return a new patch using support activations and correct-minus-predicted feedback.

        `target` belongs only to this method. Query inference and forward have no
        target argument. To backpropagate through the last two writes, detach the
        state immediately before those writes and keep both returned states live.
        """
        if self.arm != "patch":
            raise ValueError("support writing requires Net('patch')")
        outputs, h = self._run_train(tokens, slot, n_free, n_grad, patch)
        logits = outputs[-1][0]
        batch, length, vocab = logits.shape
        if target.numel() != batch * length:
            raise ValueError("target must match the support puzzle shape")
        mask = slot.reshape(batch, length).bool()
        safe_target = torch.where(mask, target.reshape(batch, length), 0).long()
        correction = F.one_hot(safe_target, vocab).to(logits.dtype) - logits.float().softmax(dim=-1)
        correction = correction * mask.unsqueeze(-1)
        denominator = mask.sum(dim=1, keepdim=True).clamp_min(1)
        activity = (self.ln_out(h) * mask.unsqueeze(-1)).sum(dim=1) / denominator
        feedback = (correction @ self.head.weight).sum(dim=1) / denominator
        rank_context = activity[:, None, :] + self.rank_slot.weight[None, :, :]
        writer_input = torch.cat((rank_context, feedback[:, None, :].expand(-1, RANK, -1)), dim=-1)
        proposal = torch.tanh(self.writer(writer_input)) * SLOT_LIMIT
        new_a, new_b_rows = proposal.split(WIDTH, dim=-1)
        new_b = new_b_rows.transpose(1, 2)
        updated_a = (RHO * patch.A + (1.0 - RHO) * new_a).clamp(-SLOT_LIMIT, SLOT_LIMIT)
        updated_b = (RHO * patch.B + (1.0 - RHO) * new_b).clamp(-SLOT_LIMIT, SLOT_LIMIT)
        return PatchState(updated_a, updated_b)

    @torch.no_grad()
    def loop_rounds(
        self, tokens: torch.Tensor, slot: torch.Tensor, n: int,
        patch: PatchState | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Return [batch, rounds, cells] predictions and [batch, rounds] stop probabilities.

        Parent evaluation applies the rsn358a2 v2 stop rule: first round >= 3
        with p_stop > 0.5 and the same answer in the preceding two rounds;
        otherwise use round 48. The plain arm has no stop head: its single
        prediction is repeated to preserve this shape and its stop values are 0.
        """
        if n < 1 or n > MAX_ROUNDS:
            raise ValueError("n must be between 1 and 48")
        if self.arm == "plain":
            prediction = self.plain_forward(tokens, slot).argmax(dim=-1)
            return prediction[:, None, :].expand(-1, n, -1), torch.zeros(tokens.shape[0], n, device=tokens.device)
        e, (dr, dc) = self.embed(tokens, slot)
        h = torch.zeros_like(e)
        predictions, stops = [], []
        for _ in range(n):
            h = self.step(h, e, dr, dc, patch)
            logits, q = self.read(h)
            predictions.append(logits.argmax(dim=-1))
            stops.append(torch.sigmoid(q.float()))
        return torch.stack(predictions, dim=1), torch.stack(stops, dim=1)


def make_net(arm: str = "patch", device: torch.device | str | None = None) -> Net:
    net = Net(arm)
    return net.to(device=device, dtype=torch.float32) if device is not None else net


def coefficient_count(net: Net) -> int:
    """Learned weights plus persistent A/B coefficients for one episode."""
    ordinary = sum(p.numel() for p in net.parameters())
    return ordinary + (2 * RANK * WIDTH if net.arm == "patch" else 0)
