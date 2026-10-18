"""Span cards: the card layout is decided by the model, not by line breaks (design/span-cards/01-design.md §3-5).

DRAFT research prototype. Nothing here is trained or used in any compared experiment; `SpanConfig.enabled` is False
by default and `build_model` then returns today's `PremonitionMini` (same class, construction and random stream).

What changes (reader, think loop, ASK, binder, decoder, losses and curriculum are the parent's):
- `SpanCardWriter` replaces `CardWriter`. A gate gives every token a boundary probability
  p_t = sigmoid(base + c_nl [token_{t-1} is a newline] + w . [h_{t-1}; h_t]), on DETACHED reader states (so
  neither the surrogate nor the rate loss trains the reader). A hard card starts at t iff t follows a
  wall (question line, padding, visit start) or p_t > 1/2, and is forced to start every `max_span` tokens. A card is
  today's softmax pool over exactly its tokens, written at its LAST token. `pool`, `key`, `value`, `null_key` and
  `null_value` are the parent's modules, so a per-line parent's state loads with only the gate parameters missing.
- Layout training route: the forward VALUE is the hard pool. In training a soft surrogate (`soft_pool`) lets content
  cross a boundary in proportion to 1 - p, with a_{e,t} ~ exp(s_t + sum_{t < u <= e} log(1 - p_u)) over the
  `max_span` tokens ending at e, in the same wall region, built from stop-gradient reader states and scores. The
  writer adds `soft - stopgrad(soft)`, so only the gate receives its gradient; the reader and pool gradients are the
  hard pool's. Starts the gate did not choose (walls, the cap) are hard boundaries in the surrogate too
  (`surrogate_stay`), so at saturated gates the surrogate equals the hard pool. `rate_loss` (H-Net's ratio loss) holds the
  tokens-per-card at `tokens_per_card`; set it to `tokens_per_line` of the training cache for an equal-count A/B.
- `SpanCardStore` is indexed by token position (card id = position of its last token, width T, NULL = T). Eligibility
  uses the card's last line; after a wipe a card must also START at or after the floor. A card is gold iff it holds a
  token of a gold line; `missing` counts gold lines with no token inside an eligible card.
- `SpanCardMini.answer` maps `first_top` and `fetched` back to line indices (a card's last line), so
  `train.validate`'s accuracy, slices and asked rate stay valid; its line-based recall and `cards` block are only
  approximate for span cards. `SpanTrainer` replaces the `cards` block by `layout_card_stats` (gold sets are card
  columns) and logs the gate statistics. `card_economy` is layout-aware and runs on a plain `PremonitionMini` too.

Initial state: gate weight 0, bias `base_logit` = -4, newline weight 8, so p = 0.982 after a newline and 0.018 elsewhere:
exactly one card per non-question line, with the parent's content. Construction is built inside `fork_rng` and
loaded from the base writer, so the global random stream after construction equals `PremonitionMini`'s.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
import math
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional, Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F

from premonition.batch import MAX_LINE_ENTS, VisitBatch
from premonition.config import MiniConfig
from premonition.model import Answers, CardWriter, PremonitionMini
from premonition.store import CardStore, age_bucket
from premonition.train import InsertLog, MiniTrainer

VARIANT = "D-span-cards"
LOG_STAY_FLOOR = -30.0
TOKEN_BINS = ("1", "2", "3-4", "5-8", "9-16", "17-32", "33-64", "65+")
BIN_EDGES = (1, 2, 4, 8, 16, 32, 64)


def source_digest() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True)
class SpanConfig:
    enabled: bool = False
    max_span: int = 64              # a card is forced closed after this many tokens (also the surrogate window)
    tokens_per_card: float = 12.0   # rate target N (> 1)
    w_rate: float = 0.03            # weight of the rate loss (H-Net's value; an assumption)
    newline_prior: float = 8.0      # initial weight of the newline feature
    base_logit: float = -4.0        # initial gate bias
    newline_id: int = 23            # "\n" in premonition-tok-v1 / v2

    def __post_init__(self) -> None:
        if self.max_span < 1:
            raise ValueError("max_span must be at least 1")
        if not self.tokens_per_card > 1.0:
            raise ValueError("tokens_per_card must be greater than 1")
        if not self.w_rate >= 0.0:
            raise ValueError("w_rate must be non-negative")
        if not (math.isfinite(self.newline_prior) and math.isfinite(self.base_logit)):
            raise ValueError("newline_prior and base_logit must be finite")
        if self.newline_id < 0:
            raise ValueError("newline_id must be a token id")


def rate_loss(start_rate: Any, gate_mean: Any, tokens_per_card: float) -> Any:
    """H-Net ratio loss N/(N-1) ((N-1) F G + (1-F)(1-G)); F: share of tokens that start a card (a count, no
    gradient), G: mean p (trained). Bilinear, so F = G = 1/N (value 1) is a saddle; with F fixed, dL/dG is
    proportional to N F - 1, which drives the hard card rate toward 1/N."""
    n = float(tokens_per_card)
    return n / (n - 1.0) * ((n - 1.0) * start_rate * gate_mean + (1.0 - start_rate) * (1.0 - gate_mean))


def log_stay(logit: torch.Tensor) -> torch.Tensor:
    """log(1 - sigmoid(logit)) = -softplus(logit), floored at -30 (finite gradient at saturated gates)."""
    return (-F.softplus(logit)).clamp_min(LOG_STAY_FLOOR)


def surrogate_stay(logit: torch.Tensor, forced: torch.Tensor) -> torch.Tensor:
    """`log_stay` for the soft surrogate, with every FORCED start (after a wall, or the `max_span` cap) a hard
    boundary (the floor, no gate gradient): the gate did not choose those cuts, so the surrogate must not let
    content leak across them, else it differs from the hard pool even with saturated gates."""
    return torch.where(forced, torch.full_like(logit, LOG_STAY_FLOOR), log_stay(logit))


@dataclass
class Layout:
    """One writer forward's hard layout: [B, T] tensors."""

    cardable: torch.Tensor      # bool: tokens that may enter a card (not question lines, not padding)
    after_wall: torch.Tensor    # bool: t = 0 or the previous token is not cardable
    after_newline: torch.Tensor  # bool: the previous token is the newline id
    logit: torch.Tensor         # float: gate logit (gradient reaches only the gate parameters)
    p: torch.Tensor             # float: sigmoid(logit)
    start: torch.Tensor         # bool: a hard card starts here
    forced: torch.Tensor        # bool: a start the gate did not choose (wall or cap)


def soft_pool(hidden: torch.Tensor, score: torch.Tensor, stay: torch.Tensor, cardable: torch.Tensor,
              region: torch.Tensor, ends_b: torch.Tensor, ends_e: torch.Tensor, max_span: int) -> torch.Tensor:
    """[n, d] soft surrogate pools of the cards ending at (ends_b, ends_e).

    For the W = max_span positions t_j = e - W + 1 + j: logw_j = s_{t_j} + sum_{j < i <= W-1} stay_{t_i}, masked to -inf
    where t_j < 0, is not cardable or lies in another wall region than e; soft = sum_j softmax(logw)_j h_{t_j}.
    `stay` [B, T] is log(1 - p) (carries the gate gradient); `hidden` and `score` are used detached.
    """
    width = max_span
    t = ends_e.unsqueeze(1) - width + 1 + torch.arange(width, device=hidden.device)
    col = t.clamp_min(0)
    row = ends_b.unsqueeze(1).expand_as(col)
    ok = (t >= 0) & cardable[row, col] & (region[row, col] == region[ends_b, ends_e].unsqueeze(1))
    kept = torch.where(ok, stay[row, col], torch.zeros_like(stay[row, col]))
    after = F.pad(kept.flip(1).cumsum(1).flip(1)[:, 1:], (0, 1))        # sum over i > j
    logw = (score.detach().float()[row, col] + after).masked_fill(~ok, -math.inf)
    weight = torch.softmax(logw, dim=1)
    return (weight.unsqueeze(-1) * hidden.detach().float()[row, col]).sum(1)


# ----------------------------------------------------------------------------- the store
@dataclass
class SpanCardStore(CardStore):
    """Cards indexed [visit, token position of the card's last token]; score vectors are [question, T + 1], NULL last."""

    card_line: Optional[torch.Tensor] = None    # [B, T] long: line of the card's last token (-1 without a card)
    first_line: Optional[torch.Tensor] = None   # [B, T] long: line of the card's first token
    token_line: Optional[torch.Tensor] = None   # [B, T] long: line of every token (the batch's line_of)
    card_of: Optional[torch.Tensor] = None      # [B, T] long: card (end position) holding the token; -1 outside cards
    last_gold = None                            # set by `gold`: the [Q, T + 1] matrix, for the trainer's statistics
    rate = None                                 # set by the writer: the rate loss of this layout (with gradient)
    stats = None                                # set by the writer: detached 0-d layout statistics (no host sync)

    def eligible(self, q_visit: torch.Tensor, q_line: torch.Tensor,
                 fetched: Optional[torch.Tensor] = None,
                 questions: Optional[torch.Tensor] = None) -> torch.Tensor:
        """[n, T + 1] bool: cards that END on a line before the question (and START at or after a wipe floor);
        NULL always, fetched real cards never."""
        ok = self.valid[q_visit] & (self.card_line[q_visit] < q_line.unsqueeze(1))
        if self.floor is not None:
            floor = self.floor if questions is None else self.floor[questions]
            ok &= self.first_line[q_visit] >= floor.unsqueeze(1)
        ok = torch.cat([ok, torch.ones_like(ok[:, :1])], dim=1)
        if fetched is not None:
            ok &= ~fetched
            ok[:, self.null] = True
        return ok

    def ages(self, q_line: torch.Tensor, buckets: int, q_visit: Optional[torch.Tensor] = None) -> torch.Tensor:
        """[n, T + 1] age buckets of every card's last line relative to the question; NULL gets 0."""
        if q_visit is None:
            raise ValueError("span cards need q_visit to find each card's line")
        bucket = age_bucket(q_line.unsqueeze(1) - self.card_line[q_visit], buckets)
        return torch.cat([bucket, torch.zeros_like(bucket[:, :1])], dim=1)

    def ask(self, query: torch.Tensor, q_visit: torch.Tensor, q_line: torch.Tensor,
            kappa: torch.Tensor, age_bias: torch.Tensor, fetched: Optional[torch.Tensor] = None,
            questions: Optional[torch.Tensor] = None) -> torch.Tensor:
        """s_i = kappa q.k_i + b_age (fp32), -inf where the card is not eligible. [n, T + 1]."""
        query = F.normalize(query.float(), dim=-1)
        keys = torch.cat([self.keys[q_visit],
                          self.null_key.expand(q_visit.shape[0], 1, -1)], dim=1)
        scores = kappa.float() * torch.einsum("nk,nlk->nl", query, keys)
        bias = age_bias.float()[self.ages(q_line, age_bias.shape[0], q_visit)]
        bias[:, self.null] = 0.0
        scores = scores + bias
        return scores.masked_fill(~self.eligible(q_visit, q_line, fetched, questions), -math.inf)

    def gather(self, index: torch.Tensor, q_visit: torch.Tensor
               ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """(values [n, K, d], ents [n, K, E], lines [n, K]) of card indices; `lines` are the cards' last lines
        (the model's age embedding reads them), -1 for NULL / none."""
        n, count = index.shape
        real = (index >= 0) & (index < self.lines)
        column = index.clamp(0, self.lines - 1)
        visit = q_visit.unsqueeze(1).expand(n, count)
        values = torch.where(real.unsqueeze(-1), self.values[visit, column],
                             self.null_value.to(self.values.dtype).expand(n, count, -1))
        ents = torch.where(real.unsqueeze(-1), self.ents[visit, column],
                           torch.full_like(self.ents[visit, column], -1))
        line = self.card_line[visit, column]
        return values, ents, torch.where(real, line, torch.full_like(line, -1))

    def gold(self, gold_lines: torch.Tensor, q_visit: torch.Tensor,
             q_line: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """(G [Q, T + 1] bool, told [Q] bool, missing [Q] long).

        G holds the eligible cards that contain a token of one of the question's evidence lines (a merged card
        holding a gold line is gold; a gold line split over two cards makes both gold), or only NULL when the
        question was never told. `missing` counts evidence lines with no token inside any eligible card.
        """
        told = (gold_lines >= 0).any(1)
        present = gold_lines >= 0
        eligible = self.eligible(q_visit, q_line)[:, :self.null]                    # [Q, T]
        card = self.card_of[q_visit]
        inside = (card >= 0) & eligible.gather(1, card.clamp_min(0))               # token is in an eligible card
        match = (self.token_line[q_visit].unsqueeze(2) == gold_lines.unsqueeze(1)) & present.unsqueeze(1)
        hit = torch.zeros(gold_lines.shape[0], self.lines + 1, dtype=torch.long, device=gold_lines.device)
        hit.scatter_add_(1, torch.where(inside, card, torch.full_like(card, self.null)),
                         (match.any(2) & inside).long())
        target = hit > 0
        target[:, self.null] = ~told
        covered = (match & inside.unsqueeze(2)).any(1)                              # [Q, MAX_GOLD]
        self.last_gold = target
        return target, told, (present & ~covered).sum(1)


# ----------------------------------------------------------------------------- the writer
class SpanCardWriter(CardWriter):
    """CardWriter with a learned boundary gate; cards are variable spans written at their last token."""

    def __init__(self, config: MiniConfig, span: SpanConfig) -> None:
        super().__init__(config)
        self.config = config
        self.span = span
        self.gate = nn.Linear(2 * config.d_model, 1)
        self.newline_weight = nn.Parameter(torch.tensor(float(span.newline_prior)))
        self.init_gate()

    def init_gate(self) -> None:
        """Gate weight 0, bias `base_logit`, newline weight `newline_prior`: the per-line layout."""
        with torch.no_grad():
            self.gate.weight.zero_()
            self.gate.bias.fill_(self.span.base_logit)
            self.newline_weight.fill_(self.span.newline_prior)

    def layout(self, hidden: torch.Tensor, batch: VisitBatch) -> Layout:
        """The hard layout. The gate reads DETACHED reader states, so neither the surrogate nor the rate loss
        trains the reader: reader and pool gradients stay exactly the hard pool's (design §3.2)."""
        span = self.span
        visits, width, _ = hidden.shape
        tokens, line_of = batch.tokens, batch.line_of
        cardable = (line_of >= 0) & ~batch.line_is_question.gather(1, line_of.clamp_min(0))
        after_wall = F.pad(~cardable[:, :-1], (1, 0), value=True)                   # t = 0 counts as after a wall
        after_newline = F.pad(tokens[:, :-1] == span.newline_id, (1, 0), value=False)
        state = hidden.detach()
        previous = F.pad(state[:, :-1], (0, 0, 1, 0))
        logit = self.gate(torch.cat([previous, state], dim=-1)).squeeze(-1).float() \
            + self.newline_weight * after_newline.float()
        p = torch.sigmoid(logit)
        chosen = cardable & (p.detach() > 0.5)
        start = chosen | (cardable & after_wall)
        position = torch.arange(width, device=hidden.device).expand(visits, width)
        last = torch.cummax(torch.where(start, position, torch.full_like(position, -1)), dim=1).values
        run = position - last
        start = start | (cardable & (run > 0) & (run % span.max_span == 0))
        return Layout(cardable, after_wall, after_newline, logit, p, start, start & ~chosen)

    def forward(self, hidden: torch.Tensor, batch: VisitBatch) -> SpanCardStore:
        span = self.span
        visits, width, d = hidden.shape
        device = hidden.device
        tokens, line_of = batch.tokens, batch.line_of
        lay = self.layout(hidden, batch)
        cardable, after_wall, after_newline, logit, p, start = (
            lay.cardable, lay.after_wall, lay.after_newline, lay.logit, lay.p, lay.start)

        # Segments over the cardable tokens (row-major; every row's first cardable token is a start).
        flat_start, flat_cardable = start.flatten(), cardable.flatten()
        n_seg = int(flat_start.sum())
        seg = (flat_start.long().cumsum(0) - 1)[flat_cardable]
        flat_pos = torch.arange(visits * width, device=device)
        token_pos = flat_pos[flat_cardable]
        first_flat = flat_pos[flat_start]
        seg_row, seg_start = first_flat // width, first_flat % width
        seg_len = torch.bincount(seg, minlength=n_seg)
        seg_end = seg_start + seg_len - 1

        # Hard pool: CardWriter.forward's arithmetic over the segments.
        score = self.pool(hidden).squeeze(-1).float()
        s = score[cardable]
        peak = torch.full((n_seg,), -math.inf, device=device)
        peak = peak.scatter_reduce(0, seg, s.detach(), "amax").clamp_min(-1e30)
        weight = torch.exp(s - peak[seg])
        total = torch.zeros(n_seg, device=device).index_add(0, seg, weight)
        weight = weight / total[seg]
        pooled = torch.zeros(n_seg, d, device=device).index_add(
            0, seg, weight.unsqueeze(-1) * hidden[cardable].float())

        # Soft surrogate: the forward value stays the hard pool; only the gate receives its gradient.
        if torch.is_grad_enabled() and self.training and n_seg:
            region = (cardable & after_wall).long().cumsum(1)
            soft = soft_pool(hidden, score, surrogate_stay(logit, lay.forced), cardable, region, seg_row, seg_end, span.max_span)
            pooled = pooled + (soft - soft.detach())

        # Rate loss and statistics.
        n_cardable = int(flat_cardable.sum())
        if n_cardable:
            start_rate = start[cardable].float().mean().detach()
            gate_mean = p[cardable].mean()
            rate = rate_loss(start_rate, gate_mean, span.tokens_per_card)
        else:
            rate = p.sum() * 0.0

        ents_seg, ents_over = self._entities(tokens, token_pos, seg, n_seg)
        stats = self._stats(p, start, cardable, after_newline, n_seg, visits, ents_over)

        # Store tensors: a card lives at its end position.
        key_rows, value_rows = self.key(pooled), self.value(pooled)
        keys = key_rows.new_zeros(visits, width, key_rows.shape[-1]).index_put((seg_row, seg_end), key_rows)
        values = value_rows.new_zeros(visits, width, d).index_put((seg_row, seg_end), value_rows)

        def place(rows: torch.Tensor, fill: int) -> torch.Tensor:
            return torch.full((visits, width), fill, dtype=torch.long, device=device).index_put(
                (seg_row, seg_end), rows)

        valid = torch.zeros(visits, width, dtype=torch.bool, device=device)
        valid[seg_row, seg_end] = True
        ents = torch.full((visits, width, MAX_LINE_ENTS), -1, dtype=torch.long, device=device)
        ents[seg_row, seg_end] = ents_seg
        card_of = torch.full((visits * width,), -1, dtype=torch.long, device=device)
        card_of[token_pos] = seg_end[seg]
        store = SpanCardStore(
            keys=F.normalize(keys.float(), dim=-1), values=values, valid=valid,
            tags=place(tokens[seg_row, seg_start], -1), ents=ents,
            line_start=place(seg_start, -1), line_len=place(seg_len, 0),
            null_key=F.normalize(self.null_key.float(), dim=-1), null_value=self.null_value,
            card_line=place(line_of[seg_row, seg_end], -1), first_line=place(line_of[seg_row, seg_start], -1),
            token_line=line_of, card_of=card_of.view(visits, width))
        store.rate, store.stats = rate, stats
        return store

    def _entities(self, tokens: torch.Tensor, token_pos: torch.Tensor, seg: torch.Tensor, n_seg: int
                  ) -> tuple[torch.Tensor, torch.Tensor]:
        """([n_seg, MAX_LINE_ENTS] distinct entity ids per card in order of first appearance, -1 padding;
        number of cards with more than MAX_LINE_ENTS distinct entities)."""
        config, device = self.config, tokens.device
        entity = tokens.flatten()[token_pos] - config.vocab_size
        is_entity = (entity >= 0) & (entity < config.n_ent)
        never = tokens.numel()
        first = torch.full((n_seg * config.n_ent,), never, dtype=torch.long, device=device).scatter_reduce(
            0, seg[is_entity] * config.n_ent + entity[is_entity], token_pos[is_entity], "amin")
        first = first.view(n_seg, config.n_ent)
        rank, order = first.sort(1)
        keep = min(MAX_LINE_ENTS, config.n_ent)
        ents = torch.where(rank[:, :keep] < never, order[:, :keep], torch.full_like(order[:, :keep], -1))
        ents = F.pad(ents, (0, MAX_LINE_ENTS - keep), value=-1)
        return ents, ((first < never).sum(1) > MAX_LINE_ENTS).sum()

    @torch.no_grad()
    def _stats(self, p: torch.Tensor, start: torch.Tensor, cardable: torch.Tensor, after_newline: torch.Tensor,
               n_seg: int, visits: int, ents_over: torch.Tensor) -> dict[str, torch.Tensor]:
        """Detached 0-d layout statistics of this forward, kept on the device (read on logged steps only)."""
        n = cardable.sum().clamp_min(1).float()
        starts = start.sum().clamp_min(1).float()
        newline_tokens = (after_newline & cardable).sum().clamp_min(1).float()
        mid = (p > 0.4) & (p < 0.6) & cardable
        values = torch.stack([
            start.sum() / n, (p * cardable).sum() / n, cardable.sum() / max(n_seg, 1),
            (start & after_newline).sum() / starts, (start & after_newline & cardable).sum() / newline_tokens,
            mid.sum() / n, torch.tensor(n_seg / max(visits, 1), device=p.device), ents_over.float()])
        names = ("start_rate", "gate_mean", "tokens_per_card", "newline_precision", "newline_recall", "gate_mid",
                 "cards_per_visit", "ents_overflow")
        return dict(zip(names, values.float().unbind()))


# ----------------------------------------------------------------------------- the model
class SpanCardMini(PremonitionMini):
    """PremonitionMini whose writer is a `SpanCardWriter`; the loss gains `w_rate` x the rate loss.

    No per-call state survives a call (so `learnlab.readonly.read_only` evaluation works): the store a call builds,
    its gold matrix and the insertion trace live in a capture dict that exists only inside `scope()`. `forward` and
    `answer` open one when none is open; `SpanTrainer` opens one around a step and reads it before it closes.
    """

    variant_name = VARIANT
    CAPTURE = "_span_capture"

    def __init__(self, config: MiniConfig, span: SpanConfig) -> None:
        super().__init__(config)
        if self.writer is None:
            raise ValueError("span cards need a card store (not D-noask)")
        self.span = span
        with torch.random.fork_rng(devices=[]):
            writer = SpanCardWriter(config, span)
        missing, unexpected = writer.load_state_dict(self.writer.state_dict(), strict=False)
        if unexpected or set(missing) != {"gate.weight", "gate.bias", "newline_weight"}:
            raise RuntimeError(f"writer state mismatch: missing={missing}, unexpected={unexpected}")
        writer.init_gate()
        self.writer = writer

    @contextmanager
    def scope(self) -> Iterator[dict[str, Any]]:
        """The open capture dict, or a fresh one removed again on exit (never left on the model)."""
        open_ = self.__dict__.get(self.CAPTURE)
        if open_ is not None:
            yield open_
            return
        capture: dict[str, Any] = {}
        self.__dict__[self.CAPTURE] = capture
        try:
            yield capture
        finally:
            self.__dict__.pop(self.CAPTURE, None)

    def build_store(self, hidden: torch.Tensor, batch: VisitBatch) -> Optional[CardStore]:
        store = super().build_store(hidden, batch)
        capture = self.__dict__.get(self.CAPTURE)
        if capture is not None:
            capture["store"] = store
        return store

    def forward(self, batch: VisitBatch, *args: Any, **kwargs: Any) -> dict[str, Any]:
        with self.scope() as capture:
            out = super().forward(batch, *args, **kwargs)
            store = capture.pop("store")
        out["rate"] = store.rate
        out["loss"] = out["loss"] + self.span.w_rate * store.rate
        metrics = out["metrics"]
        for name, value in store.stats.items():
            metrics[f"span_{name}"] = value
        metrics["span_rate"] = store.rate.detach().float()
        if store.last_gold is not None:
            capture["gold_matrix"] = store.last_gold.detach()
        return out

    def _insert(self, episode: Any, store: CardStore, index: torch.Tensor, cards: torch.Tensor) -> None:
        capture = self.__dict__.get(self.CAPTURE)
        if capture is not None and "trace" in capture:
            capture["trace"].append((index.detach().cpu(), cards.detach().cpu()))
        super()._insert(episode, store, index, cards)

    @torch.no_grad()
    def answer(self, batch: VisitBatch, *, wipe: Optional[str] = None, window_line: Optional[torch.Tensor] = None,
               stop: Optional[Iterable[int]] = None, max_loops: Optional[int] = None) -> Answers:
        """`PremonitionMini.answer` with `first_top` and `fetched` in line indices (a card's last line); the raw
        card-indexed pair is left in an OPEN capture as "raw_answer" (callers that want it open `scope()`)."""
        with self.scope() as capture:
            out = super().answer(batch, wipe=wipe, window_line=window_line, stop=stop, max_loops=max_loops)
            store = capture.pop("store", None)
            capture["raw_answer"] = (out.first_top, out.fetched)
        lines = batch.line_start.shape[1]
        count = out.tokens.shape[0]
        device = out.tokens.device
        if store is None or out.fetched is None:
            return out
        rows = torch.arange(count, device=device) if wipe == "full" else batch.q_visit
        top = out.first_top
        mapped = store.card_line[rows.unsqueeze(1), top.clamp_min(0)]
        first_top = torch.where(top >= 0, mapped, torch.full_like(top, -1))
        fetched = torch.zeros(count, lines + 1, dtype=torch.bool, device=device)
        who, card = torch.nonzero(out.fetched[:, :store.null], as_tuple=True)
        line = store.card_line[rows[who], card]
        fetched[who[line >= 0], line[line >= 0]] = True
        fetched[:, lines] = out.fetched[:, store.null]
        return Answers(out.tokens, out.lengths, out.loops, first_top, fetched, out.halt_prob)


def build_model(config: MiniConfig, span: SpanConfig = SpanConfig()) -> PremonitionMini:
    """`PremonitionMini(config)` unchanged when `span.enabled` is False, else a `SpanCardMini`."""
    if not span.enabled:
        return PremonitionMini(config)
    if not config.store:
        raise ValueError("span cards need a card store (not D-noask)")
    return SpanCardMini(config, span)


# ----------------------------------------------------------------------------- trainer
def matrix_gold_sets(gold_matrix: torch.Tensor, batch: VisitBatch) -> tuple[list[set[int]], list[bool]]:
    """Per question: G as score-vector columns of a [Q, W + 1] gold matrix (NULL = W when never told), and told.
    A told question with no gold card has the unfetchable set {-2}."""
    told = (batch.gold_lines.cpu() >= 0).any(1).tolist()
    null = gold_matrix.shape[1] - 1
    sets = []
    for row, was_told in zip(gold_matrix.cpu(), told):
        sets.append(set(torch.nonzero(row).flatten().tolist()) or ({-2} if was_told else {null}))
    return sets, told


def card_stats_from_sets(calls: Sequence[tuple[torch.Tensor, torch.Tensor]], sets: Sequence[set[int]],
                         told: Sequence[bool], loops: torch.Tensor, card_rows: int, *, offset: int
                         ) -> dict[str, Any]:
    """`train.card_stats` with the gold sets and told flags given instead of derived from line numbers."""
    count = len(sets)
    sequences: list[list[tuple[int, int]]] = [[] for _ in range(count)]
    for call, (index, cards) in enumerate(calls):
        for row, question in enumerate(index.tolist()):
            sequences[question].extend((card, call + offset) for card in cards[row].tolist() if card >= 0)
    loops = loops.cpu().tolist()
    out = dict(questions=count, told=sum(told), multi_gold=0, big_gold=0, any_gold=0, full_gold=0,
               multi_full=0, overflow=0, gold_evicted=0, early_terms=0, answer_terms=0, never_full=0)
    for q in range(count):
        gold, seq, n = sets[q], sequences[q], int(loops[q])
        got: set[int] = set()
        full_loop = None
        for card, loop in seq:
            got.add(card)
            if full_loop is None and gold <= got:
                full_loop = loop
        out["answer_terms"] += n
        out["early_terms"] += n if full_loop is None else min(max(full_loop, 0), n)
        out["never_full"] += full_loop is None or full_loop >= n
        overflow = max(0, len(seq) - card_rows)
        out["overflow"] += overflow > 0
        if overflow and gold & {card for card, _ in seq[:overflow]}:
            out["gold_evicted"] += 1
        if told[q]:
            out["any_gold"] += bool(gold & got)
            out["full_gold"] += gold <= got
            out["multi_gold"] += len(gold) > 1
            out["multi_full"] += len(gold) > 1 and gold <= got
            out["big_gold"] += len(gold) > 10
    return out


def layout_card_stats(calls: Sequence[tuple[torch.Tensor, torch.Tensor]], gold_matrix: torch.Tensor,
                      batch: VisitBatch, loops: torch.Tensor, card_rows: int, *, offset: int) -> dict[str, Any]:
    """`train.card_stats` for span cards: the gold sets are the columns of `gold_matrix` (`store.gold`), and
    `calls` hold card columns. Same keys, so `train.summarize_cards` takes it unchanged."""
    sets, told = matrix_gold_sets(gold_matrix, batch)
    return card_stats_from_sets(calls, sets, told, loops, card_rows, offset=offset)


class SpanTrainer(MiniTrainer):
    """MiniTrainer whose logged `cards` block is layout-aware, plus `span_log` (gate statistics per logged step)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.span_log: list[dict[str, Any]] = []

    def _train_step(self, batch: VisitBatch, plan: Any, loops: torch.Tensor, track: bool) -> dict[str, Any]:
        model = self.model
        if not isinstance(model, SpanCardMini):
            return super()._train_step(batch, plan, loops, track)
        with model.scope() as capture:
            if track:
                capture["trace"] = []
            result = super()._train_step(batch, plan, loops, track)
            if track:
                gold = capture.get("gold_matrix")
                if gold is not None:
                    result["cards"] = layout_card_stats(capture["trace"], gold, batch, loops, model.config.card_rows,
                                                        offset=0 if plan.mode == "gold" else 1)
                logged = {name: float(value) for name, value in result["metrics"].items()
                          if name.startswith("span_")}
                self.span_log.append({"step": self.step, **logged, "rate": logged.get("span_rate")})
        return result


# ----------------------------------------------------------------------------- the report
def tokens_per_line(cache: Any) -> float:
    """Mean tokens per non-question line of a `premonition.data.VisitCache`: the rate target for an equal-count A/B."""
    lengths = cache.line_offsets.long().diff()
    return float(lengths[~cache.line_is_question].float().mean())


def _layout(store: CardStore) -> tuple[torch.Tensor, ...]:
    """(row, start, length, first_line, last_line) of every card of a line store or a span store."""
    row, column = torch.nonzero(store.valid, as_tuple=True)
    if isinstance(store, SpanCardStore):
        first, last = store.first_line[row, column], store.card_line[row, column]
    else:
        first = last = column
    return row, store.line_start[row, column], store.line_len[row, column], first, last


def _token_cards(row: torch.Tensor, start: torch.Tensor, length: torch.Tensor, shape: tuple[int, int]
                 ) -> torch.Tensor:
    """[B, T] long: the card (index into the layout) holding each token, -1 outside cards."""
    out = torch.full(shape, -1, dtype=torch.long, device=row.device)
    if row.numel():
        card = torch.arange(row.numel(), device=row.device).repeat_interleave(length)
        offset = torch.arange(card.numel(), device=row.device) - (length.cumsum(0) - length)[card]
        out[row[card], start[card] + offset] = card
    return out


@torch.no_grad()
def card_economy(model: PremonitionMini, batches: Iterable[VisitBatch], *,
                 device: Optional[torch.device] = None) -> dict[str, Any]:
    """Layout-aware card report over `batches`, valid for a plain `PremonitionMini` (cards are lines) and a
    `SpanCardMini`. The model is put in eval mode for the duration.

    "layout", "visits", "cards", "cards_per_visit" {mean, p10, p50, p90}, "tokens_per_card" {mean, hist, hist_share};
    "line_aligned" (cards that are exactly one whole non-question line), "merged" (cards over > 1 line),
    "split_lines" (non-question lines touched by > 1 card), "newline_precision" / "newline_recall" (card starts vs
    non-question line starts), "ents_overflow" (cards with > MAX_LINE_ENTS distinct entities); from `store.gold`:
    "gold_cards_per_told_q", "gold_card_tokens", "gold_missing"; from `answer` under `InsertLog`: "asked_rate",
    "fetches_per_q", "null_share", "first_ask_recall" (told questions: gold cards among the cards of the first
    insert call that held any card, over |gold|; 0 when never fetched), "full_gold_fetched", "questions", "told".
    """
    config = model.config
    if not config.store:
        raise ValueError("card_economy needs a card store (not D-noask)")
    device = device or next(model.parameters()).device
    modes = [(module, module.training) for module in model.modules()]
    model.eval()
    layout = "line"
    counts: list[torch.Tensor] = []
    lengths: list[torch.Tensor] = []
    sums: dict[str, float] = {}

    def add(**values: float) -> None:
        for name, value in values.items():
            sums[name] = sums.get(name, 0.0) + float(value)

    try:
        for batch in batches:
            batch = batch.to(device)
            visits, width = batch.tokens.shape
            lines = batch.line_start.shape[1]
            store = model.build_store(model.read(batch), batch)
            if isinstance(store, SpanCardStore):
                layout = "span"
            row, start, length, first, last = _layout(store)
            n = row.numel()
            counts.append(torch.bincount(row, minlength=visits).cpu())
            lengths.append(length.cpu())
            line_tokens = torch.zeros(visits, lines, dtype=torch.long, device=device)
            real = batch.line_of >= 0
            line_tokens.index_put_((torch.arange(visits, device=device).unsqueeze(1).expand_as(batch.line_of)[real],
                                    batch.line_of[real]), torch.ones_like(batch.line_of[real]), accumulate=True)
            plain = ~batch.line_is_question & (batch.line_start >= 0)               # existing non-question lines
            one_line = (first == last) & plain[row, first.clamp_min(0)]
            aligned = one_line & (start == batch.line_start[row, first.clamp_min(0)]) \
                & (length == line_tokens[row, first.clamp_min(0)])
            token_card = _token_cards(row, start, length, (visits, width))
            inside = (token_card >= 0) & real
            line_key = (torch.arange(visits, device=device).unsqueeze(1) * lines + batch.line_of.clamp_min(0))
            pair = torch.unique(line_key[inside] * (n + 1) + token_card[inside])
            touched = torch.bincount(pair // (n + 1), minlength=visits * lines).view(visits, lines)
            line_grid = torch.zeros(visits, width, dtype=torch.bool, device=device)
            line_rows, line_ids = torch.nonzero(plain, as_tuple=True)
            line_grid[line_rows, batch.line_start[line_rows, line_ids]] = True
            card_grid = torch.zeros_like(line_grid)
            card_grid[row, start] = True
            entity = batch.tokens - config.vocab_size
            is_entity = inside & (entity >= 0) & (entity < config.n_ent)
            distinct = torch.unique(token_card[is_entity] * config.n_ent + entity[is_entity])
            per_card = torch.bincount(distinct // config.n_ent, minlength=n)
            add(visits=visits, cards=n, aligned=aligned.sum(), merged=(first != last).sum(),
                lines=plain.sum(), split=((touched > 1) & plain).sum(), card_starts=card_grid.sum(),
                line_starts=line_grid.sum(), both_starts=(card_grid & line_grid).sum(),
                ents_over=(per_card > MAX_LINE_ENTS).sum())
            count = batch.q_visit.shape[0]
            if not count:
                continue
            gold, told, missing = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
            real_gold = gold[:, :store.null]
            size = store.line_len[batch.q_visit]
            add(gold_cards=real_gold[told].sum(), gold_tokens=(real_gold * size)[told].sum(),
                gold_missing=missing.sum(), questions=count, told=told.sum())
            with InsertLog(model) as log:
                model.answer(batch)
            fetched = torch.zeros(count, store.null + 1, dtype=torch.bool, device=device)
            first_set = torch.zeros_like(fetched)
            seen = torch.zeros(count, dtype=torch.bool, device=device)
            real_inserts = torch.zeros(count, device=device)
            null_inserts = torch.zeros(count, device=device)
            for index, cards in log.calls:
                index, cards = index.to(device), cards.to(device)
                present = cards >= 0
                null = cards == store.null
                real_inserts.index_add_(0, index, (present & ~null).sum(1).float())
                null_inserts.index_add_(0, index, null.sum(1).float())
                fetched[index.unsqueeze(1).expand_as(cards)[present], cards[present]] = True
                for i in torch.nonzero(present.any(1) & ~seen[index]).flatten().tolist():
                    first_set[index[i], cards[i][present[i]]] = True
                    seen[index[i]] = True
            have = real_gold.sum(1)
            got = (real_gold & first_set[:, :store.null]).sum(1)
            full = told & (have > 0) & ~(real_gold & ~fetched[:, :store.null]).any(1)
            add(asked=(real_inserts > 0).sum(), real_inserts=real_inserts.sum(), null_inserts=null_inserts.sum(),
                first_recall=(got.float() / have.clamp_min(1))[told].sum(), full_gold=full.sum())
    finally:
        for module, was in modes:
            module.training = was

    def share(top: str, bottom: str) -> Optional[float]:
        return sums.get(top, 0.0) / sums[bottom] if sums.get(bottom) else None

    all_counts = torch.cat(counts).float() if counts else torch.zeros(0)
    all_lengths = torch.cat(lengths) if lengths else torch.zeros(0, dtype=torch.long)
    quantile = (lambda q: float(all_counts.quantile(q))) if all_counts.numel() else (lambda q: None)
    bins = torch.bucketize(all_lengths, torch.tensor(BIN_EDGES)).bincount(minlength=len(TOKEN_BINS)).tolist()
    inserts = sums.get("real_inserts", 0.0) + sums.get("null_inserts", 0.0)
    return {
        "layout": layout, "visits": int(sums.get("visits", 0)), "cards": int(sums.get("cards", 0)),
        "cards_per_visit": {"mean": float(all_counts.mean()) if all_counts.numel() else None,
                            "p10": quantile(0.1), "p50": quantile(0.5), "p90": quantile(0.9)},
        "tokens_per_card": {"mean": float(all_lengths.float().mean()) if all_lengths.numel() else None,
                            "hist": dict(zip(TOKEN_BINS, bins)),
                            "hist_share": {name: count / max(len(all_lengths), 1)
                                           for name, count in zip(TOKEN_BINS, bins)}},
        "line_aligned": share("aligned", "cards"), "merged": share("merged", "cards"),
        "split_lines": share("split", "lines"),
        "newline_precision": share("both_starts", "card_starts"), "newline_recall": share("both_starts", "line_starts"),
        "ents_overflow": share("ents_over", "cards"),
        "gold_cards_per_told_q": share("gold_cards", "told"), "gold_card_tokens": share("gold_tokens", "gold_cards"),
        "gold_missing": int(sums.get("gold_missing", 0)),
        "asked_rate": share("asked", "questions"), "fetches_per_q": share("real_inserts", "questions"),
        "null_share": sums.get("null_inserts", 0.0) / inserts if inserts else 0.0,
        "first_ask_recall": share("first_recall", "told"), "full_gold_fetched": share("full_gold", "told"),
        "questions": int(sums.get("questions", 0)), "told": int(sums.get("told", 0)),
    }


def identity(span: SpanConfig, config: MiniConfig) -> dict[str, Any]:
    return {"variant": VARIANT, "base_variant": config.variant, "purpose": "diagnostic",
            "adjustment": "card writer: boundary-gated span cards (learned layout, soft surrogate, rate loss)"
                          if span.enabled else "none (span cards disabled: the plain per-line model)",
            "span": asdict(span), "reader_path": "D", "module": "premonition/span_cards.py",
            "source_sha256": source_digest()}


__all__ = ["SpanCardMini", "SpanCardStore", "SpanCardWriter", "SpanConfig", "SpanTrainer", "VARIANT",
           "build_model", "card_economy", "card_stats_from_sets", "identity", "layout_card_stats", "log_stay",
           "matrix_gold_sets", "rate_loss", "soft_pool", "source_digest", "tokens_per_line"]
