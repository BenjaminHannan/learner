"""Overnight (run ovn-20260918-235851) diagnostic: a question-conditioned answer read ("+qread").

D's decoder starts from the `[answer]` token alone, so its first cross-attention query is the SAME for every
question: it cannot pick the card that matches the question unless Think has already marked it. With +qread the
decoder input is the question's own tokens (up to and including `[answer]`, left-padded with <pad> to a common
length) followed by the answer, so the first answer position attends to the think rows with a query that has
seen the question (as a query embedding does in End-To-End Memory Networks, Sukhbaatar et al. 2015, and as any
decoder-only reader does). No new parameters, no extra information: the question tokens are already D's input.
Cost: up to `PREFIX` extra decoder positions per decode. Baseline D and every other variant are untouched.
"""
from __future__ import annotations

import math
from typing import Iterable, Optional

import torch
import torch.nn.functional as F

from premonition.model import PremonitionMini
from premonition.ovn_variants import ThinkCenteredMini

PREFIX = 6          # longest question up to [answer] is 5 tokens ("[question] ENT LINK REL [answer]")


def question_prefix(batch, pad_id: int) -> torch.Tensor:
    """[Q, PREFIX] question tokens through `[answer]`, left-padded with pad_id (the last column is `[answer]`)."""
    start, end = batch.q_span[:, 0], batch.q_span[:, 1]
    offset = torch.arange(PREFIX, device=start.device) - PREFIX + 1          # ..., -1, 0
    position = end.unsqueeze(1) - 1 + offset
    inside = position >= start.unsqueeze(1)
    tokens = batch.tokens[batch.q_visit.unsqueeze(1), position.clamp_min(0)]
    return torch.where(inside, tokens, torch.full_like(tokens, pad_id))


class QReadMixin:
    """Decoder inputs = question prefix + answer; `_greedy` starts from the prefix."""

    qread = True

    def qread_inputs(self, batch, targets: torch.Tensor) -> tuple[torch.Tensor, int]:
        """(inputs [Q, PREFIX + T - 1], first scored position): position PREFIX - 1 + t predicts targets[:, t]."""
        prefix = question_prefix(batch, self.config.pad_id)
        tail = targets[:, :-1].masked_fill(targets[:, :-1] < 0, self.config.pad_id)
        return torch.cat([prefix, tail], dim=1), PREFIX - 1

    def _greedy(self, batch, episode, mentions, stop: Optional[Iterable[int]]):
        config = self.config
        count = batch.q_visit.shape[0]
        device = episode.x.device
        stop_ids = torch.tensor(sorted(set(stop) if stop is not None else {config.eos_id}), dtype=torch.long,
                                device=device)
        banned = torch.zeros(count, config.total_vocab, dtype=torch.bool, device=device)
        if config.pointers:
            banned[:, config.vocab_size:] = ~mentions
        sequence = question_prefix(batch, config.pad_id)
        out = torch.full((count, config.max_answer), config.pad_id, dtype=torch.long, device=device)
        lengths = torch.full((count,), config.max_answer, dtype=torch.long, device=device)
        done = torch.zeros(count, dtype=torch.bool, device=device)
        for position in range(config.max_answer):
            hidden = self._decode_logits(episode.x, episode.valid, sequence)[:, -1]
            logits = F.linear(hidden, self.embed.weight).float().masked_fill(banned, -math.inf)
            token = logits.argmax(-1)
            token = torch.where(done, torch.full_like(token, config.pad_id), token)
            out[:, position] = token
            ended = ~done & torch.isin(token, stop_ids)
            lengths = torch.where(ended, torch.full_like(lengths, position + 1), lengths)
            done |= ended
            if done.all():
                break
            sequence = torch.cat([sequence, token.unsqueeze(1)], dim=1)
        return out, lengths


class QReadMini(QReadMixin, PremonitionMini):
    variant_name = "D+qread"


class ThinkCenteredQReadMini(QReadMixin, ThinkCenteredMini):
    variant_name = "D-think-centered+qread"


CLASSES = {"D+qread": QReadMini, "D-think-centered+qread": ThinkCenteredQReadMini}

__all__ = ["CLASSES", "PREFIX", "QReadMini", "QReadMixin", "ThinkCenteredQReadMini", "question_prefix"]
