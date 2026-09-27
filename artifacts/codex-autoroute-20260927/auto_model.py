"""Task-blind front end for the sealed e4 small dense loop.

One complete 1,646,750-parameter model serves every request. The old four-row
environment embedding is renamed, with its initialization and weights intact,
and selected from visible puzzle tokens and answer slots alone.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn.functional as F

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import claude_rsn358e4_replayall as E4  # noqa: E402

X, R, E, M = E4.X, E4.X.R, E4.X.E, E4.X.M
EXPECTED_PARAMS = 1_646_750


@dataclass(frozen=True)
class PuzzleRequest:
    """The entire model-visible request; no task ID, answer, or checker metadata."""

    tokens: tuple[tuple[int, ...], ...]
    slot: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        tokens = tuple(tuple(int(x) for x in row) for row in self.tokens)
        slot = tuple(tuple(int(x) for x in row) for row in self.slot)
        if not tokens or not tokens[0] or any(len(row) != len(tokens[0]) for row in tokens):
            raise ValueError("tokens must be a nonempty rectangular puzzle")
        if len(slot) != len(tokens) or any(len(row) != len(tokens[0]) for row in slot):
            raise ValueError("slot must have the same shape as tokens")
        if any(x not in (0, 1) for row in slot for x in row):
            raise ValueError("slot values must be 0 or 1")
        object.__setattr__(self, "tokens", tokens)
        object.__setattr__(self, "slot", slot)


def visible_batch(requests: list[PuzzleRequest], device: str | torch.device):
    """Tensorize visible fields only; reject ragged batches rather than pad."""
    if not requests or any(not isinstance(request, PuzzleRequest) for request in requests):
        raise ValueError("a nonempty batch of PuzzleRequest is required")
    shape = (len(requests[0].tokens), len(requests[0].tokens[0]))
    if any((len(req.tokens), len(req.tokens[0])) != shape for req in requests):
        raise ValueError("mixed shapes require separate calls; padding is not supported")
    tokens = torch.tensor([req.tokens for req in requests], dtype=torch.long, device=device)
    slots = torch.tensor([req.slot for req in requests], dtype=torch.long, device=device)
    return tokens, slots


class AutoNet(R.Net):
    """Unchanged small dense blocks, answer head and stop head; learned visible context."""

    def __init__(self):
        # X.make_net("dense", "small") sets this same sealed configuration.
        R.ARMS["dense"] = dict(X.SIZES["small"])
        super().__init__("dense")
        if self.env.num_embeddings != 4 or self.env.embedding_dim != 256:
            raise RuntimeError("unexpected sealed environment embedding shape")
        self.contexts = self.env
        del self.env
        if sum(p.numel() for p in self.parameters()) != EXPECTED_PARAMS:
            raise RuntimeError("task-blind model exceeded the exact parameter budget")
        if not all(p.requires_grad for p in self.parameters()):
            raise RuntimeError("every parameter must remain trainable")

    def embed_inputs(self, tokens: torch.Tensor, slots: torch.Tensor):
        if tokens.ndim != 3 or slots.shape != tokens.shape:
            raise ValueError("tokens and slots must have matching [B,H,W] shapes")
        if tokens.dtype != torch.long or slots.dtype != torch.long:
            raise TypeError("tokens and slots must be long tensors")
        batch, height, width = tokens.shape
        base = self.tok(tokens.reshape(batch, -1)) + self.slot(slots.reshape(batch, -1))
        query = base.mean(dim=1)
        weights = self.contexts.weight
        context_probs = F.softmax((query @ weights.T / math.sqrt(256)).float(), dim=-1)
        context = context_probs @ weights
        embedding = base + context[:, None, :]
        return embedding, self.offsets(height, width, tokens.device), context_probs

    def train_rounds(self, tokens: torch.Tensor, slots: torch.Tensor, n_free: int, n_grad: int):
        """Sealed loop schedule; answer and stop losses train contexts end to end."""
        if n_free < 0 or n_grad < 1:
            raise ValueError("n_free must be nonnegative and n_grad positive")
        self.train()
        embedding, (dr, dc), _ = self.embed_inputs(tokens, slots)
        state = torch.zeros_like(embedding)
        with torch.no_grad():
            for _ in range(n_free):
                state = self.step(state, embedding.detach(), dr, dc)
        state = state.detach()
        outputs = []
        for _ in range(n_grad):
            state = self.step(state, embedding, dr, dc)
            outputs.append(self.read(state))
        return outputs

    @torch.no_grad()
    def infer(self, tokens: torch.Tensor, slots: torch.Tensor, rounds: int = 48):
        """Return raw per-round predictions, stop probabilities and context weights."""
        if rounds < 1:
            raise ValueError("rounds must be positive")
        self.eval()
        embedding, (dr, dc), context_probs = self.embed_inputs(tokens, slots)
        state = torch.zeros_like(embedding)
        predictions, stop_probs = [], []
        for _ in range(rounds):
            state = self.step(state, embedding, dr, dc)
            logits, halt_logit = self.read(state)
            predictions.append(logits.argmax(dim=-1))
            stop_probs.append(torch.sigmoid(halt_logit.float()))
        return torch.stack(predictions, dim=1), torch.stack(stop_probs, dim=1), context_probs

    # The inherited APIs expect an oracle env ID. Fail closed if called by an old runner.
    def embed(self, *_args, **_kwargs):
        raise TypeError("use embed_inputs(tokens, slots); task IDs are forbidden")

    def loop_train(self, *_args, **_kwargs):
        raise TypeError("use train_rounds(tokens, slots, n_free, n_grad)")

    def loop_rounds(self, *_args, **_kwargs):
        raise TypeError("use infer(tokens, slots, rounds)")

    def plain_forward(self, *_args, **_kwargs):
        raise TypeError("the task-ID plain forward path is forbidden")


__all__ = ("AutoNet", "PuzzleRequest", "visible_batch", "E4", "X", "R", "E", "M", "torch", "EXPECTED_PARAMS")
