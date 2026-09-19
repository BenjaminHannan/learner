"""The contract between `premonition.data` (which builds batches) and `premonition.model` (which reads them).

One batch holds B whole visits, pointerized (design/06 §2): every person or village name is replaced by
one of `N_ENT` entity ids, numbered in order of first mention (randomly permuted per visit in training),
and the exact spellings live in each visit's `NameTable`. Token ids below `vocab_size` are tokenizer ids;
`vocab_size + e` is entity e.

Lines are the visit's text lines. Every non-question line is a card candidate; question lines never are.
All questions of the batch are flattened into one list of length Q, each pointing back at its visit.
Padding: token/line positions past a visit's end hold `PAD_ID` / `-1`; unused gold slots hold `-1`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import torch

N_ENT = 16           # entity ids per visit: 5-12 people plus the village name fit (scheduler.Village)
MAX_ANSWER = 32      # answer tokens per question, including the closing <eos>
MAX_GOLD = 16        # evidence lines per question: sets reach 14 (count questions); ~1% exceed 8
MAX_LINE_ENTS = 4    # entity ids recorded per line
PAD_ID = 0           # ASSUMPTION checked by data.py: the tokenizer's <pad> id


@dataclass
class NameTable:
    """One visit's entity id -> exact spelling (as first written in the raw text)."""

    spellings: dict[int, str] = field(default_factory=dict)

    def spelling(self, ent: int) -> str:
        return self.spellings[ent]


@dataclass
class VisitBatch:
    # ---- per token: [B, T]
    tokens: torch.Tensor          # long: pointerized ids; PAD_ID past the end
    line_of: torch.Tensor         # long: the line index each token belongs to; -1 on padding
    card_end: torch.Tensor        # bool: last token of a non-question line (where its card is written)
    lengths: torch.Tensor         # long [B]: real tokens per visit
    lm_mask: torch.Tensor         # bool: positions whose next token is trained by L_lm (answer spans masked out)
    # ---- per line: [B, L]
    line_is_question: torch.Tensor  # bool
    line_start: torch.Tensor        # long: first token index of the line; -1 on padding
    line_ents: torch.Tensor         # long [B, L, MAX_LINE_ENTS]: entity ids the line mentions; -1 padding
    # ---- per question: flattened over the batch, length Q
    q_visit: torch.Tensor         # long [Q]: which visit (row of the token tensors)
    q_line: torch.Tensor          # long [Q]: the question's own line; only cards on earlier lines are visible
    q_span: torch.Tensor          # long [Q, 2]: token range [start, end) of the question text up to and incl. "[answer]"
    answer: torch.Tensor          # long [Q, MAX_ANSWER]: pointerized answer ids ending in <eos>; -100 padding
    gold_lines: torch.Tensor      # long [Q, MAX_GOLD]: evidence lines (oracle); all -1 means "never told" (NULL card)
    depth: torch.Tensor           # long [Q]: oracle derivation depth (0 for "not told")
    question_ids: list[str]       # [Q]: the shard question ids, to join slice tags and reports
    names: list[NameTable]        # [B]
    slices: Optional[dict[str, torch.Tensor]] = None  # optional per-question bool tags, e.g. "far", "multi_hop"

    @property
    def size(self) -> tuple[int, int, int]:
        """(visits, tokens per visit, questions)."""
        return self.tokens.shape[0], self.tokens.shape[1], self.q_visit.shape[0]

    def to(self, device: torch.device) -> "VisitBatch":
        moved = {name: value.to(device) if isinstance(value, torch.Tensor) else value
                 for name, value in self.__dict__.items()}
        if self.slices is not None:
            moved["slices"] = {name: tag.to(device) for name, tag in self.slices.items()}
        return VisitBatch(**moved)
