"""Direct contextual-state reader (milestone-3 continuation diagnostic; NOT a default, NOT promoted).

Spec: design/research/final-sweep-2026-09-19/03-learning.md ("hold selected indices fixed and expose their original
contextual token states from the same causal reader pass, versus pooling those states") and Astra's milestone-3
review. Declared diagnostic: synthetic-vocabulary toy ladder, supplied gold-evidence cards (privileged), answer-only
decode with no Think passes (nothink+qread).

Pooled baseline (D): a selected line l enters the decoder memory as ONE row
    value(sum_t w_t h_t) + age(l) + type_card,   w = softmax of the writer's learned pool over the line's positions.
Direct reader (this variant): the SAME selected line enters as one row PER TOKEN POSITION of that line
    value(h_t) + age(l) + type_card,              t over exactly the positions the writer pools,
where h_t are the reader states of the SAME causal pass that built the cards (no raw-token access, no re-encoding
of the line, no new parameters, no within-line position embedding). Because `value` is affine and w sums to 1, the
pooled row is the w-weighted mean of the direct rows: the decoder's question-conditioned cross-attention replaces
the question-blind pool. Everything else is unchanged and matched: the same selected card indices in the same
order, the same age and row-type metadata, the same question rows, entity slots (still bound with the pooled
card value, as in D) and registers. The pooled card rows stay in the episode but are masked out of the decoder
memory, so the pooled baseline and this variant differ only in how the selected lines' content is exposed.

Decode-only: Think passes (`_step`) are refused, and so is a second insertion into the same episode (the FIFO
card-row semantics of multi-loop retrieval are not defined for token rows). With no cards inserted the episode is
identical to the baseline's. Token rows live on the episode, never on the module (read-only evaluation).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import torch

from premonition.model import ROW_CARD
from premonition.ovn_qread import QReadMini
from premonition.store import age_bucket

VERSION = 1
VARIANT = "nothink+qread+directread"


def line_positions(batch) -> torch.Tensor:
    """[V, lines, Lmax] token positions of each line (exactly the positions the writer pools), -1 padded."""
    line_of = batch.line_of
    visits, width = line_of.shape
    lines = batch.line_start.shape[1]
    real = line_of >= 0
    visit = torch.arange(visits, device=line_of.device).unsqueeze(1).expand(visits, width)
    position = torch.arange(width, device=line_of.device).unsqueeze(0).expand(visits, width)
    line = line_of.clamp_min(0)
    rank = position - batch.line_start[visit, line]
    if bool((rank[real] < 0).any()):
        raise ValueError("a line's positions start before its line_start")
    longest = int(rank[real].max()) + 1 if bool(real.any()) else 1
    table = torch.full((visits, lines, longest), -1, dtype=torch.long, device=line_of.device)
    table[visit[real], line[real], rank[real]] = position[real]
    counts = real.long().new_zeros(visits * lines).index_add_(
        0, (visit * lines + line)[real], torch.ones_like(line[real]))
    if int(counts.max()) != longest or bool(((table >= 0).sum(-1).view(-1) != counts).any()):
        raise ValueError("line positions are not contiguous")
    return table


class DirectReaderQReadMini(QReadMini):
    """nothink+qread with the direct contextual-state reader for inserted cards (see module docstring)."""

    variant_name = "D+qread+directread"
    direct_reader = True

    def _start(self, batch, hidden, store, mentions):
        episode = super()._start(batch, hidden, store, mentions)
        episode.direct_hidden = hidden                   # the SAME reader pass that built the store
        episode.direct_lines = line_positions(batch)
        episode.direct_inserted = False
        return episode

    def _step(self, episode, index, step, store):
        raise NotImplementedError("the direct-reader diagnostic is decode-only (nothink); Think passes are refused")

    def _insert(self, episode, store, index, cards):
        if not bool((cards >= 0).any()):
            return
        if episode.direct_inserted:
            raise NotImplementedError("the direct-reader diagnostic inserts supplied cards once per episode")
        config = self.config
        before = episode.valid.clone()
        super()._insert(episode, store, index, cards)                  # pooled rows, slots, count, fetched
        region = slice(self._card_base, self._card_base + config.cards)
        added = episode.valid[:, region] & ~before[:, region]
        episode.valid = episode.valid.clone()
        episode.valid[:, region] &= ~added                                # pooled card rows leave the memory
        _, _, lines = store.gather(cards, episode.q_visit[index])         # [n, K], -1 = none / NULL
        visit = episode.q_visit[index].unsqueeze(1).expand_as(lines)
        table = episode.direct_lines
        positions = table[visit, lines.clamp_min(0)]                      # [n, K, Lmax]
        ok = (positions >= 0) & (lines >= 0).unsqueeze(-1)
        states = episode.direct_hidden[visit.unsqueeze(-1).expand_as(positions), positions.clamp_min(0)]
        bucket = age_bucket(episode.q_line[index].unsqueeze(1) - lines, config.age_buckets)
        bucket = torch.where(lines >= 0, bucket, torch.zeros_like(bucket))
        rows = (self.writer.value(states.float()) + self.think.age(bucket).float().unsqueeze(2)
                + self.think.row_type.weight[ROW_CARD].float())                   # [n, K, Lmax, d]
        n, k, longest, d = rows.shape
        count = episode.x.shape[0]
        extra = episode.x.new_zeros(count, k * longest, d)
        extra_ok = torch.zeros(count, k * longest, dtype=torch.bool, device=episode.x.device)
        extra = extra.index_copy(0, index, (rows * ok.unsqueeze(-1)).view(n, k * longest, d).to(extra.dtype))
        extra_ok = extra_ok.index_copy(0, index, ok.view(n, k * longest))
        episode.x = torch.cat([episode.x, extra], dim=1)
        episode.valid = torch.cat([episode.valid, extra_ok], dim=1)
        episode.direct_rows = (episode.x.shape[1] - k * longest, k * longest)
        episode.direct_inserted = True


def identity(config) -> dict:
    return {"variant": VARIANT, "class": "DirectReaderQReadMini", "module": "premonition/direct_reader.py",
            "version": VERSION, "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "new_parameters": 0, "memory": "selected lines' contextual reader states (same pass), one row per "
            "pooled position; pooled card rows masked; slots, question rows, registers, ages, types unchanged",
            "default": False, "purpose": "diagnostic"}


__all__ = ["DirectReaderQReadMini", "VARIANT", "VERSION", "identity", "line_positions"]
