"""The per-visit card store (design/06 §2).

One card per non-question line: a unit key, a value, the line index, the
source tag (the line's first token), the diary pointer (first token and
length) and the entity ids the line mentions. The store is rebuilt from the
input like a KV cache, so it holds no trained weights; the NULL card's key and
value are parameters of the card writer and are passed in.

Cards are indexed [visit, line]; score vectors are [question, lines + 1] with
NULL last. A question on line q sees only cards on lines < q (and >= its wipe
floor); NULL is always eligible.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
import hashlib
from typing import Optional

import torch
import torch.nn.functional as F

from learnlab.readonly import tensor_digest
from premonition.batch import VisitBatch

NEG_INF = float("-inf")


def age_bucket(age: torch.Tensor, buckets: int) -> torch.Tensor:
    """min(buckets - 1, floor(log2 age)) for age >= 1; 0 below."""
    return torch.log2(age.clamp_min(1).float()).floor().long().clamp(0, buckets - 1)


def set_cross_entropy(scores: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """[n]: -log sum_{c in target} softmax(scores)_c; every row needs a non-empty target."""
    return torch.logsumexp(scores, 1) - torch.logsumexp(scores.masked_fill(~target, NEG_INF), 1)


@dataclass
class CardStore:
    keys: torch.Tensor          # [B, L, dk] unit length
    values: torch.Tensor        # [B, L, d]
    valid: torch.Tensor         # [B, L] bool: the line has a card
    tags: torch.Tensor          # [B, L] long: the line's first token id (-1 without a card)
    ents: torch.Tensor          # [B, L, MAX_LINE_ENTS] long: entity ids the line mentions, -1 padding
    line_start: torch.Tensor    # [B, L] long: diary pointer, first token of the line
    line_len: torch.Tensor      # [B, L] long: diary pointer, tokens in the line
    null_key: torch.Tensor      # [dk] unit length
    null_value: torch.Tensor    # [d]
    floor: Optional[torch.Tensor] = None   # [Q] long: after a wipe, cards on lines < floor are gone

    # ---------------------------------------------------------------- writing
    @classmethod
    def write(cls, keys: torch.Tensor, values: torch.Tensor, batch: VisitBatch,
              null_key: torch.Tensor, null_value: torch.Tensor) -> CardStore:
        """Cards for every non-question line that ends inside the batch (`card_end`)."""
        visits, lines = batch.line_start.shape
        slot = batch.line_of.clamp_min(0) + lines * torch.arange(
            visits, device=batch.line_of.device).unsqueeze(1)
        real = batch.line_of >= 0
        ended = torch.zeros(visits * lines, dtype=torch.long, device=slot.device)
        ended.index_add_(0, slot[batch.card_end & real], torch.ones_like(slot[batch.card_end & real]))
        length = torch.zeros_like(ended).index_add_(0, slot[real], torch.ones_like(slot[real]))
        valid = (ended.view(visits, lines) > 0) & ~batch.line_is_question & (batch.line_start >= 0)
        first = batch.tokens.gather(1, batch.line_start.clamp_min(0))
        return cls(keys=F.normalize(keys.float(), dim=-1), values=values, valid=valid,
                   tags=torch.where(valid, first, torch.full_like(first, -1)),
                   ents=torch.where(valid.unsqueeze(-1), batch.line_ents,
                                    torch.full_like(batch.line_ents, -1)),
                   line_start=batch.line_start, line_len=length.view(visits, lines),
                   null_key=F.normalize(null_key.float(), dim=-1), null_value=null_value)

    @property
    def lines(self) -> int:
        return self.valid.shape[1]

    @property
    def null(self) -> int:
        """Index of the NULL card in score vectors."""
        return self.lines

    # --------------------------------------------------------------- reading
    def eligible(self, q_visit: torch.Tensor, q_line: torch.Tensor,
                 fetched: Optional[torch.Tensor] = None,
                 questions: Optional[torch.Tensor] = None) -> torch.Tensor:
        """[n, L + 1] bool: cards a question may be shown; NULL always, fetched real cards never.

        `questions` indexes the rows of `floor` when `q_visit`/`q_line` are a subset.
        """
        line = torch.arange(self.lines, device=q_line.device)
        ok = self.valid[q_visit] & (line < q_line.unsqueeze(1))
        if self.floor is not None:
            floor = self.floor if questions is None else self.floor[questions]
            ok &= line >= floor.unsqueeze(1)
        ok = torch.cat([ok, torch.ones_like(ok[:, :1])], dim=1)
        if fetched is not None:
            ok &= ~fetched
            ok[:, self.null] = True
        return ok

    def ages(self, q_line: torch.Tensor, buckets: int) -> torch.Tensor:
        """[n, L + 1] age buckets of every card relative to the question; NULL gets 0."""
        line = torch.arange(self.lines, device=q_line.device)
        bucket = age_bucket(q_line.unsqueeze(1) - line, buckets)
        return torch.cat([bucket, torch.zeros_like(bucket[:, :1])], dim=1)

    def ask(self, query: torch.Tensor, q_visit: torch.Tensor, q_line: torch.Tensor,
            kappa: torch.Tensor, age_bias: torch.Tensor, fetched: Optional[torch.Tensor] = None,
            questions: Optional[torch.Tensor] = None) -> torch.Tensor:
        """s_i = kappa q.k_i + b_age (fp32), -inf where the card is not eligible. [n, L + 1]."""
        query = F.normalize(query.float(), dim=-1)
        keys = torch.cat([self.keys[q_visit],
                          self.null_key.expand(q_visit.shape[0], 1, -1)], dim=1)
        scores = kappa.float() * torch.einsum("nk,nlk->nl", query, keys)
        bias = age_bias.float()[self.ages(q_line, age_bias.shape[0])]
        bias[:, self.null] = 0.0
        scores = scores + bias
        return scores.masked_fill(~self.eligible(q_visit, q_line, fetched, questions), NEG_INF)

    def top(self, scores: torch.Tensor, k: int) -> torch.Tensor:
        """[n, k] best eligible card indices (NULL = `null`), -1 where fewer are eligible."""
        k = min(k, scores.shape[1])
        best, index = scores.topk(k, dim=1)
        return index.masked_fill(best == NEG_INF, -1)

    def gather(self, index: torch.Tensor, q_visit: torch.Tensor
               ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """(values [n, K, d], ents [n, K, E], lines [n, K]) of card indices; -1 / NULL handled."""
        n, count = index.shape
        real = (index >= 0) & (index < self.lines)
        line = index.clamp(0, self.lines - 1)
        visit = q_visit.unsqueeze(1).expand(n, count)
        values = torch.where(real.unsqueeze(-1), self.values[visit, line],
                             self.null_value.to(self.values.dtype).expand(n, count, -1))
        ents = torch.where(real.unsqueeze(-1), self.ents[visit, line],
                           torch.full_like(self.ents[visit, line], -1))
        return values, ents, torch.where(real, line, torch.full_like(line, -1))

    def gold(self, gold_lines: torch.Tensor, q_visit: torch.Tensor,
             q_line: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """(G [Q, L + 1] bool, told [Q] bool, missing [Q] long).

        G holds the cards on a question's evidence lines, or NULL when it was never
        told (all gold lines -1). `missing` counts evidence lines with no eligible card
        (a data bug the tests check stays at zero); they are left out of G.
        """
        told = (gold_lines >= 0).any(1)
        present = gold_lines >= 0
        line = gold_lines.clamp(0, self.lines - 1)
        mapped = present & (gold_lines < self.lines) \
            & self.valid[q_visit.unsqueeze(1), line] & (gold_lines < q_line.unsqueeze(1))
        if self.floor is not None:
            mapped &= gold_lines >= self.floor.unsqueeze(1)
        target = torch.zeros(gold_lines.shape[0], self.lines + 1, dtype=torch.bool,
                             device=gold_lines.device)
        target.scatter_(1, torch.where(mapped, line, torch.full_like(line, self.null)),
                        mapped | ~told.unsqueeze(1))
        return target, told, (present & ~mapped).sum(1)

    # ---------------------------------------------------------------- wipes
    def wipe(self, floor: torch.Tensor) -> CardStore:
        """A view with every card on a line < floor[q] gone for question q (NULL stays)."""
        floor = floor.to(self.valid.device, torch.long)
        if self.floor is not None:
            floor = torch.maximum(floor, self.floor)
        return replace(self, floor=floor)

    def fingerprint(self) -> str:
        digest = hashlib.sha256()
        for item in fields(self):
            value = getattr(self, item.name)
            digest.update(item.name.encode())
            digest.update(tensor_digest(value.detach()).encode() if value is not None else b"none")
        return digest.hexdigest()


__all__ = ["CardStore", "age_bucket", "set_cross_entropy"]
