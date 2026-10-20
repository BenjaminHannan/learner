"""Swarm of desks (design/swarm): `thinkers = M` desks per question, one batched think call per round.

DESKS    each question runs M independent episodes (rows `qm = q * M + m`), identical to the single thinker
         except for a learned desk embedding added to its registers. All Q*M desks go through ONE
         `model._step` per round: that is the concurrency.
BOARD    the only channel between desks (`config.swarm_board`): every desk's register-1 note plus the
         cards any desk fetched ("posted"), re-written into a read-only region at the end of every desk's
         rows before each round. Off = S0 (independent desks); on = S1.
COMBINER the decoder reads every desk's rows plus one copy of the board. Entity slots a desk bound are
         shown from that desk; unbound duplicates are hidden (entity nobody bound: desk 0's copy).
ASK      training-only balanced assignment (uses gold labels, never an inference channel): the cards
         still missing from the union of the desks' fetches are split across desks by their own scores.

Built on `model._start / _step / _insert / _teacher_cards / _greedy`, so subclasses compose. Called
from `PremonitionMini.forward` and `.answer` when `config.thinkers > 1`; the flag-off path is untouched.
"""
from __future__ import annotations

from dataclasses import replace
import math
from typing import Any, Iterable, Optional

import torch
import torch.nn.functional as F

from learnlab.core import IGNORE_INDEX
from premonition.batch import VisitBatch
from premonition.store import CardStore, age_bucket, set_cross_entropy

MODES = ("gold", "teacher", "own")
LESIONS = (None, "board", "notes", "cards")
COLLAPSE_COS, COLLAPSE_OVERLAP = 0.95, 0.8     # the pre-registered collapse line


# ----------------------------------------------------------------------------- board
class Board:
    """Per-question board of `M` note rows and `C` posted-card rows (FIFO); [Q, M + C, d] with a validity mask."""

    def __init__(self, model: Any, count: int, store: Optional[CardStore], q_visit: torch.Tensor,
                 q_line: torch.Tensor, device: torch.device) -> None:
        config = model.config
        self.model, self.store = model, store
        self.q_visit, self.q_line = q_visit, q_line
        self.desks, self.size = config.thinkers, config.board_cards
        d = config.d_model
        self.notes = torch.zeros(count, self.desks, d, device=device)
        self.notes_ok = torch.zeros(count, self.desks, dtype=torch.bool, device=device)
        self.cards = torch.zeros(count, self.size, d, device=device)
        self.cards_ok = torch.zeros(count, self.size, dtype=torch.bool, device=device)
        self.count = torch.zeros(count, dtype=torch.long, device=device)
        self.slot_card = torch.full((count, self.size), -1, dtype=torch.long, device=device)   # card held per row

    @property
    def posted(self) -> Optional[torch.Tensor]:
        """[Q, L + 1] bool: the cards on the board now (derived from `slot_card`, never stored apart)."""
        if self.store is None:
            return None
        width = self.store.lines + 2                                                   # last column: empty rows
        index = torch.where(self.slot_card >= 0, self.slot_card, torch.full_like(self.slot_card, width - 1))
        return torch.zeros(self.count.shape[0], width, dtype=torch.bool, device=index.device).scatter_(
            1, index, True)[:, :-1]

    def rows(self) -> tuple[torch.Tensor, torch.Tensor]:
        """(x [Q, M + C, d], ok [Q, M + C])."""
        return torch.cat([self.notes, self.cards], 1), torch.cat([self.notes_ok, self.cards_ok], 1)

    def write_notes(self, register: torch.Tensor) -> None:
        """notes[q, m] = register row of desk (q, m) + note type + desk embedding. register [Q*M, d]."""
        think = self.model.think
        desk = think.desk.weight
        self.notes = (register.float().view(-1, self.desks, register.shape[-1])
                      + think.board_type.weight[0].float() + desk.float())
        self.notes_ok = torch.ones_like(self.notes_ok)

    def post(self, cards: torch.Tensor) -> None:
        """Post the round's fetched cards [Q*M, K] (-1 = none) exactly as a one-by-one FIFO would.

        Walk the M*K columns in desk order. A card is new if it is real, not NULL and not on the board at
        that moment: a card evicted earlier in the same round, even one that was there when the round
        began, is posted again when a later desk fetched it. A new card takes row count % C, evicting
        the card held there. Every step is a whole-tensor op (no boolean-mask indexing, no `.any()` read
        on the host, no `F.one_hot` range check), so no step forces a host sync: test `NoSyncTest`.
        """
        store = self.store
        if store is None:
            return
        think, config = self.model.think, self.model.config
        count, per = self.cards.shape[0], cards.shape[1]
        flat = cards.reshape(count, self.desks * per)                                  # [Q, M*K]
        values, _, lines = store.gather(flat, self.q_visit)
        bucket = age_bucket(self.q_line.unsqueeze(1) - lines, config.age_buckets)
        bucket = torch.where(lines >= 0, bucket, torch.zeros_like(bucket))
        author = torch.arange(flat.shape[1], device=flat.device) // per
        rows = (values.float() + think.age(bucket).float() + think.board_type.weight[1].float()
                + think.desk.weight[author].float())                                   # [Q, M*K, d]
        row_index = torch.arange(self.size, device=flat.device)
        slot_card, pointer = self.slot_card, self.count
        source = torch.full_like(slot_card, -1)                     # [Q, C]: the column that last wrote each row
        for column in range(flat.shape[1]):                         # the FIFO runs on ids only (small tensors)
            card = flat[:, column]
            new = (card >= 0) & (card != store.null) & ~(slot_card == card.unsqueeze(1)).any(1)
            write = (row_index == (pointer % self.size).unsqueeze(1)) & new.unsqueeze(1)   # [Q, C]
            slot_card = torch.where(write, card.unsqueeze(1), slot_card)
            source = torch.where(write, torch.full_like(source, column), source)
            pointer = pointer + new.long()
        written = source >= 0                                       # then the board is written once
        picked = rows.gather(1, source.clamp_min(0).unsqueeze(-1).expand(-1, -1, rows.shape[-1]))
        self.cards = torch.where(written.unsqueeze(-1), picked, self.cards)
        self.slot_card, self.cards_ok, self.count = slot_card, self.cards_ok | written, pointer


# ----------------------------------------------------------------------------- combiner
def entity_table(store: CardStore, n_ent: int) -> torch.Tensor:
    """[B, L, n_ent] bool: line l of visit b names entity e (from the card ents; -1 padding ignored)."""
    ents = store.ents
    if ents.numel():          # range check with no host sync: a device-side assert on CUDA, raises at once on CPU
        torch._assert_async(ents.max() < n_ent, "swarm entity_table: an entity id is >= n_ent")
    table = torch.zeros(*ents.shape[:2], n_ent + 1, dtype=torch.bool, device=ents.device)
    return table.scatter_(2, torch.where(ents >= 0, ents, torch.full_like(ents, n_ent)), True)[..., :n_ent]


def merge_mask(model: Any, valid: torch.Tensor, fetched: Optional[torch.Tensor], store: Optional[CardStore],
               q_visit: torch.Tensor, desks: int, named: Optional[torch.Tensor] = None) -> torch.Tensor:
    """[Q, M * R] bool decoder visibility of every desk's rows (valid [Q*M, R]), with the bound-slot merge.

    Slot (q, m, e) is shown iff it is a mention AND (desk m fetched a real card naming e, or nobody did
    and m == 0). Without a binder every valid row is shown. `named` [Q*M, L, n_ent] is
    `entity_table(store)[q_visit]`, built once per forward by `_Swarm` (it depends only on the visit).
    """
    count, rows = valid.shape[0] // desks, valid.shape[1]
    if model.think.binder is None:
        return valid.reshape(count, desks * rows)
    config = model.config
    first = config.question_rows
    if named is None:
        named = entity_table(store, config.n_ent)[q_visit]                  # [Q*M, L, n_ent]
    bound = (fetched[:, :store.lines].unsqueeze(-1) & named).any(1).view(count, desks, config.n_ent)
    lead = torch.arange(desks, device=valid.device).view(1, desks, 1) == 0
    show = bound | (~bound.any(1, keepdim=True) & lead)                     # [Q, M, n_ent]
    out = valid.clone()
    out[:, first:first + config.slots] &= show.reshape(count * desks, config.n_ent)
    return out.reshape(count, desks * rows)


def combiner_memory(model: Any, episode: Any, store: Optional[CardStore], desk_rows: int, desks: int,
                    board: Optional[Board], named: Optional[torch.Tensor] = None) -> tuple[torch.Tensor, torch.Tensor]:
    """(memory [Q, M * R + B, d], valid): all desks' rows (without board copies) plus one board copy."""
    count, width = episode.x.shape[0] // desks, episode.x.shape[-1]
    memory = episode.x[:, :desk_rows].reshape(count, desks * desk_rows, width)
    valid = merge_mask(model, episode.valid[:, :desk_rows], episode.fetched, store, episode.q_visit, desks, named)
    if board is not None:
        rows, ok = board.rows()
        memory = torch.cat([memory, rows.to(memory.dtype)], 1)
        valid = torch.cat([valid, ok], 1)
    return memory, valid


# ----------------------------------------------------------------------------- ASK assignment
def balanced_assignment(prefs: torch.Tensor, need: torch.Tensor, picks: Optional[int] = None) -> torch.Tensor:
    """T [Q, M, N] bool: split each question's `need` [Q, N] across its M desks by `prefs` [Q, M, N].

    The split rule (RUNCARD-S0 §1, part of the mechanism): with n = |need|, every desk gets floor(n / M) or
    ceil(n / M) cards. Greedy: while some desk is below floor(n / M), only those desks may take a card;
    after that, desks below ceil(n / M). Each pick takes, per question, the best (eligible desk, unassigned
    card) pair by preference. The result is disjoint and covers `need`.
    `picks` bounds the loop. Pass a static bound (training passes the batch's gold width + 1) to keep it
    free of host syncs. None reads max |need| once, a sync, which is fine for tests.
    """
    count, desks, width = prefs.shape
    prefs = prefs.clamp_min(-1e9)
    total = need.sum(1)
    floor, cap = total // desks, -(-total // desks)
    load = torch.zeros(count, desks, dtype=torch.long, device=need.device)
    free = need.clone()
    out = torch.zeros(count, desks, width, dtype=torch.bool, device=need.device)
    desk_ids = torch.arange(desks, device=need.device)
    pair_ids = torch.arange(desks * width, device=need.device)
    for _ in range(int(total.max()) if picks is None and count else (picks or 0)):
        short = load < floor.unsqueeze(1)                                       # desks still below the floor
        open_ = torch.where(short.any(1, keepdim=True), short, load < cap.unsqueeze(1))
        ok = open_.unsqueeze(2) & free.unsqueeze(1)                             # [Q, M, N]
        best = prefs.masked_fill(~ok, -math.inf).reshape(count, -1).argmax(1)
        live = ok.reshape(count, -1).any(1)                                     # a pick remains (device-side)
        chosen = (pair_ids == best.unsqueeze(1)) & live.unsqueeze(1)            # unmasked writes: no sync
        out |= chosen.view(count, desks, width)
        load += ((desk_ids == (best // width).unsqueeze(1)) & live.unsqueeze(1)).long()
        free &= ~chosen.view(count, desks, width).any(1)
    return out


# ----------------------------------------------------------------------------- shared setup
class _Swarm:
    """The desk episode of a batch: replicated batch/store, desk embeddings, board, index maps."""

    def __init__(self, model: Any, batch: VisitBatch, hidden: torch.Tensor, store: Optional[CardStore],
                 mentions: torch.Tensor, board: bool = True) -> None:
        config = model.config
        self.model, self.config = model, config
        self.desks = M = config.thinkers
        self.count = Q = batch.q_visit.shape[0]
        device = hidden.device
        self.device = device
        rep = lambda t: t.repeat_interleave(M, 0)  # noqa: E731
        self.owner = torch.arange(Q, device=device).repeat_interleave(M)
        self.desk_of = torch.arange(M, device=device).repeat(Q)
        self.all = torch.arange(Q * M, device=device)
        self.batch = replace(batch, q_visit=rep(batch.q_visit), q_line=rep(batch.q_line), q_span=rep(batch.q_span))
        self.store = (replace(store, floor=rep(store.floor)) if store is not None and store.floor is not None
                      else store)
        self.episode = model._start(self.batch, hidden, self.store, rep(mentions))
        base, regs = model._register_base, config.registers
        x = self.episode.x
        self.episode.x = torch.cat([x[:, :base], x[:, base:base + regs] + model.think.desk.weight[self.desk_of].unsqueeze(1),
                                    x[:, base + regs:]], 1)
        self.desk_rows = self.episode.x.shape[1]
        self.board = (Board(model, Q, store, batch.q_visit, batch.q_line, device)
                      if config.swarm_board and board else None)
        self.named = (entity_table(store, config.n_ent)[self.batch.q_visit]
                      if store is not None and model.think.binder is not None else None)   # once per forward

    def write_board(self) -> None:
        """Append (first round) or overwrite the board region at the end of every desk's rows."""
        if self.board is None:
            return
        episode = self.episode
        rows, ok = self.board.rows()
        episode.x = torch.cat([episode.x[:, :self.desk_rows], rows[self.owner].to(episode.x.dtype)], 1)
        episode.valid = torch.cat([episode.valid[:, :self.desk_rows], ok[self.owner]], 1)

    def round(self, step: int) -> tuple[torch.Tensor, ...]:
        """Board in, ONE batched think call for all Q*M desks: (rows, halt, ask, scores)."""
        self.write_board()
        return self.model._step(self.episode, self.all, step, self.store)

    def memory(self) -> tuple[torch.Tensor, torch.Tensor]:
        return combiner_memory(self.model, self.episode, self.store, self.desk_rows, self.desks, self.board,
                               self.named)

    def insert(self, cards: torch.Tensor) -> None:
        """Cards [Q*M, K] into the fetching desks, then posted to the question's board."""
        self.model._insert(self.episode, self.store, self.all, cards)
        if self.board is not None:
            self.board.post(cards)

    def registers(self) -> torch.Tensor:
        base = self.model._register_base
        return self.episode.x[:, base:base + self.config.registers].reshape(
            self.count, self.desks, self.config.registers, -1)

    def desk_fetched(self) -> Optional[torch.Tensor]:
        fetched = self.episode.fetched
        return None if fetched is None else fetched.view(self.count, self.desks, -1)


# ----------------------------------------------------------------------------- diversity
def _pairs(desks: int) -> tuple[torch.Tensor, torch.Tensor]:
    return torch.triu_indices(desks, desks, 1)


def fetch_overlap(desk_fetched: torch.Tensor) -> float:
    """Mean Jaccard of two desks' fetched real cards over questions and desk pairs; NaN with no non-empty pair."""
    real = desk_fetched[..., :-1]
    i, j = _pairs(real.shape[1])
    inter = (real[:, i] & real[:, j]).sum(-1).float()
    union = (real[:, i] | real[:, j]).sum(-1).float()
    keep = union > 0
    return float((inter[keep] / union[keep]).mean()) if keep.any() else float("nan")


def register_cos(registers: torch.Tensor) -> float:
    """Mean cosine of two desks' flattened final registers over questions and desk pairs."""
    flat = F.normalize(registers.float().flatten(2), dim=-1)
    i, j = _pairs(flat.shape[1])
    return float((flat[:, i] * flat[:, j]).sum(-1).mean())


def is_collapsed(cos: float, overlap: float) -> bool:
    return bool(cos > COLLAPSE_COS and overlap > COLLAPSE_OVERLAP)


def diversity(swarm: dict[str, Any]) -> dict[str, Any]:
    """Collapse report of `Answers.swarm`: fetch overlap, register cosine, per-desk ask rate and fetch count."""
    fetched, asks = swarm["desk_fetched"], swarm["desk_asks"]
    rounds = swarm.get("rounds") or max(1, int(asks.max()))
    cos, overlap = register_cos(swarm["registers"]), fetch_overlap(fetched)
    ask_rate = (asks.float() / rounds).mean(0)
    return {"fetch_overlap": overlap, "register_cos": cos, "ask_rate": ask_rate.tolist(),
            "fetch_count": fetched[..., :-1].sum(-1).float().mean(0).tolist(),
            "collapsed": is_collapsed(cos, overlap), "silent_desks": int((ask_rate < 0.05).sum())}


# ----------------------------------------------------------------------------- training
def _gold_cards(gold: torch.Tensor, desks: int, width: int) -> torch.Tensor:
    """[Q*M, ceil(width / M)] the question's `width` LATEST gold cards (as the single thinker's preload keeps),
    dealt round-robin over its desks in line order: kept card i -> desk i % M. NULL, the last index, is a
    never-told question's only card and goes to desk 0. -1 pads."""
    count, size = gold.shape
    line = torch.arange(size, device=gold.device).expand(count, size)
    latest = torch.where(gold, line, torch.full_like(line, -1)).topk(width, 1).values
    ordered = latest.masked_fill(latest < 0, size).sort(1).values
    ordered = ordered.masked_fill(ordered == size, -1)
    ordered = F.pad(ordered, (0, -ordered.shape[1] % desks), value=-1)
    return ordered.view(count, -1, desks).permute(0, 2, 1).reshape(count * desks, -1)


def swarm_forward(model: Any, batch: VisitBatch, mode: str = "teacher", p_own: float = 0.0,
                  loops: Optional[int] = None, weights: Optional[dict[str, float]] = None,
                  generator: Optional[torch.Generator] = None) -> dict[str, Any]:
    """`PremonitionMini.forward` for M desks: same losses and return dict (see the module docstring).

    Fixed rounds for every question: `loops`, else 2 for "gold", else `swarm_rounds`. L_ans comes from the
    combiner each round; HALT is the mean desk logit; ASK is trained with `balanced_assignment`;
    `metrics["question_loops"]` counts desk-rounds (Q * rounds * M).
    """
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; choose from {MODES}")
    config = model.config
    M = config.thinkers
    hidden = model.read(batch)
    l_lm = model.lm_loss(hidden, batch)
    store = model.build_store(hidden, batch)
    count = batch.q_visit.shape[0]
    zero = hidden.sum() * 0.0
    metrics: dict[str, torch.Tensor] = {}
    if weights is None:
        weights = {"lm": config.w_lm, "ask": config.w_ask, "ans": config.w_ans, "halt": config.w_halt}
        if mode == "gold":
            weights.update(ask=0.0, halt=0.0)
    if count == 0:
        losses = {"lm": l_lm, "ask": zero, "ans": zero, "halt": zero}
        metrics["question_loops"] = torch.zeros((), dtype=torch.long)
        return {**losses, "loss": sum(weights[k] * v for k, v in losses.items()), "metrics": metrics}

    device = hidden.device
    rounds = loops if loops is not None else 2 if mode == "gold" else config.swarm_rounds
    rounds = max(1, min(rounds, config.max_loops))
    swarm = _Swarm(model, batch, hidden, store, model._mentions(batch))
    desk_store, episode = swarm.store, swarm.episode
    gold = None
    if store is not None:
        gold, told, missing = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
        metrics["gold_missing"] = missing.sum()
        if mode == "gold":
            width = min(gold.shape[1], batch.gold_lines.shape[1] + 1, M * config.card_rows)   # each desk <= card_rows
            swarm.insert(_gold_cards(gold, M, width))

    answer = batch.answer
    length = int((answer != IGNORE_INDEX).sum(1).max().item())
    targets = answer[:, :max(length, 1)]
    start_token = batch.tokens[batch.q_visit, batch.q_span[:, 1] - 1]
    inputs = torch.cat([start_token.unsqueeze(1), targets[:, :-1]], dim=1)
    inputs = inputs.masked_fill(inputs == IGNORE_INDEX, config.pad_id)
    keep = targets != IGNORE_INDEX

    ans_terms, halt_terms, set_terms, bce_terms = [], [], [], []
    for step in range(rounds):
        rows, halt, ask, scores = swarm.round(step)
        if swarm.board is not None:
            swarm.board.write_notes(rows[:, model._register_base + 1])
        memory, valid = swarm.memory()
        hidden_ans = model._decode_logits(memory, valid, inputs)
        logits = F.linear(hidden_ans[keep], model.embed.weight).float()
        owner = torch.nonzero(keep)[:, 0]
        token_ce = F.cross_entropy(logits, targets[keep], reduction="none")
        per_question = torch.zeros(count, device=device).index_add(0, owner, token_ce)
        per_question = per_question / keep.sum(1).clamp_min(1)
        wrong = torch.zeros(count, device=device).index_add(
            0, owner, (logits.argmax(-1) != targets[keep]).float())
        correct = (wrong == 0).float()
        union = swarm.desk_fetched().any(1) if store is not None else None
        if gold is not None:
            scale = torch.where(~(gold & ~union).any(1), 1.0, config.early_ans)
        else:
            scale = torch.ones_like(per_question)
        ans_terms.append(scale * per_question)
        halt_terms.append(F.binary_cross_entropy_with_logits(halt.view(count, M).mean(1), correct,
                                                             reduction="none"))
        if step == 0:
            metrics["answer_acc_first"] = correct.mean().detach()
        if step == rounds - 1:
            metrics["answer_acc"] = correct.mean().detach()
        if store is None:
            continue
        # L_ask: balanced assignment of the cards no desk has fetched yet.
        need_union = gold & ~union
        prefs = scores.detach().view(count, M, -1)
        target = balanced_assignment(prefs, need_union, picks=batch.gold_lines.shape[1] + 1).view(count * M, -1)
        asks = target.any(1)
        bce_terms.append(F.binary_cross_entropy_with_logits(ask, asks.float(), reduction="none"))
        if asks.any():
            set_terms.append(set_cross_entropy(scores[asks], target[asks]))
        if step == 0:
            metrics["recall_at_k"] = _recall(model, swarm, rows, gold).detach()
        if mode == "gold" or step == rounds - 1:
            continue
        cards = model._teacher_cards(desk_store, episode, swarm.all, target,
                                     gold.repeat_interleave(M, 0), generator)
        if mode == "own" and p_own > 0:
            own = store.top(scores.detach(), config.top_k).masked_fill((ask <= 0).unsqueeze(1), -1)
            own = F.pad(own, (0, cards.shape[1] - own.shape[1]), value=-1)
            pick = torch.rand(count * M, device=device, generator=generator) < p_own
            cards = torch.where(pick.unsqueeze(1), own, cards)
        swarm.insert(cards)

    l_ans = torch.stack(ans_terms).sum() / (count * rounds)
    l_halt = torch.cat(halt_terms).mean()
    l_ask = zero
    if bce_terms:
        l_ask = torch.cat(bce_terms).mean()
        if set_terms:
            l_ask = l_ask + torch.cat(set_terms).mean()
    metrics["question_loops"] = torch.tensor(count * rounds * M)
    # No per-step swarm diagnostics (review round 3, item c): MiniTrainer never read them and they synced the
    # host every step, charging S0's training clock. The diversity report runs at eval (`swarm_answer`).
    losses = {"lm": l_lm, "ask": l_ask, "ans": l_ans, "halt": l_halt}
    total = sum(weights.get(name, 0.0) * value for name, value in losses.items())
    return {**losses, "loss": total, "metrics": metrics}


def _recall(model: Any, swarm: _Swarm, rows: torch.Tensor, gold: torch.Tensor) -> torch.Tensor:
    """Gold recall@top_k of desk 0's first ASK over eligible cards (told questions). Desk 0 only, so that it is
    comparable with D1's training recall and with validation's `first_top` (also desk 0)."""
    from premonition.model import _norm
    store, episode, config = swarm.store, swarm.episode, model.config
    told = gold[:, :store.null].any(1)
    if not told.any():
        return torch.zeros(())
    with torch.no_grad():
        register = _norm(rows[:, model._register_base])
        scores = store.ask(model.heads.query(register), episode.q_visit, episode.q_line,
                           model.heads.log_kappa.exp(), model.think.age_bias, questions=swarm.all)
        top = store.top(scores, config.top_k).view(swarm.count, swarm.desks, -1)[:, 0]
        found = torch.zeros(gold.shape, dtype=torch.long, device=gold.device).scatter_add(
            1, top.clamp_min(0), (top >= 0).long()) > 0
        hit = (gold & found).sum(1).float()
        return (hit / gold.sum(1).clamp_min(1))[told].mean()


# ----------------------------------------------------------------------------- evaluation
@torch.no_grad()
def swarm_answer(model: Any, batch: VisitBatch, *, wipe: Optional[str] = None,
                 window_line: Optional[torch.Tensor] = None, stop: Optional[Iterable[int]] = None,
                 max_loops: Optional[int] = None, lesion: Optional[str] = None) -> Any:
    """`PremonitionMini.answer` for M desks: fixed rounds, each desk fetches its own top-k when its ASK
    logit > 0, the combiner decodes after the last round. `lesion` (eval-only, S1 models): "board" = the
    board is never written (an S1 run as S0), "notes" = cards posted but notes never written, "cards" =
    notes written but no cards posted. `Answers.swarm` carries the per-desk readouts for `diversity`."""
    from premonition.model import Answers, _Episode, crop_to_windows
    if lesion not in LESIONS:
        raise ValueError(f"unknown lesion {lesion!r}; choose from {LESIONS}")
    config = model.config
    if lesion is not None and not config.swarm_board:
        raise ValueError("lesion needs a swarm with a board (swarm_board)")
    M = config.thinkers
    low = None
    if wipe is not None:
        if wipe not in ("store", "full") or window_line is None:
            raise ValueError('wipe must be "store" or "full", with window_line')
        window_line = window_line.to(batch.q_line.device)
        if wipe == "full":
            batch = crop_to_windows(batch, window_line)
        else:
            low = batch.line_start[batch.q_visit, window_line]
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    if store is not None and wipe is not None:
        store = store.wipe(window_line)
    count = batch.q_visit.shape[0]
    device = hidden.device
    if count == 0:
        empty = torch.zeros(0, dtype=torch.long, device=device)
        return Answers(torch.zeros(0, config.max_answer, dtype=torch.long, device=device), empty,
                       empty, torch.zeros(0, config.top_k, dtype=torch.long, device=device),
                       None if store is None else torch.zeros(0, store.lines + 1, dtype=torch.bool,
                                                              device=device),
                       torch.zeros(0, device=device))
    mentions = model._mentions(batch, low)
    swarm = _Swarm(model, batch, hidden, store, mentions, board=lesion != "board")
    board = swarm.board
    rounds = max(1, min(max_loops or config.swarm_rounds, config.max_loops))
    first_top = torch.full((count, config.top_k), -1, dtype=torch.long, device=device)
    asks = torch.zeros(count, M, dtype=torch.long, device=device)
    halt_prob = torch.zeros(count, device=device)
    for step in range(rounds):
        rows, halt, ask, scores = swarm.round(step)
        halt_prob = torch.sigmoid(halt.view(count, M).mean(1))    # the logit HALT is trained on
        if board is not None and lesion != "notes":
            board.write_notes(rows[:, model._register_base + 1])
        if store is None:
            continue
        asks += (ask > 0).long().view(count, M)
        top = store.top(scores, config.top_k)
        if step == 0:
            lead = top.view(count, M, -1)[:, 0]
            first_top = lead.masked_fill(lead == store.null, -1)
        cards = top.masked_fill((ask <= 0).unsqueeze(1) | (step + 1 == rounds), -1)
        if lesion == "cards":
            swarm.model._insert(swarm.episode, swarm.store, swarm.all, cards)
        else:
            swarm.insert(cards)
    memory, valid = swarm.memory()
    final = _Episode(memory, valid, torch.zeros(count, dtype=torch.long, device=device), None,
                     batch.q_visit, batch.q_line)
    tokens, lengths = model._greedy(batch, final, mentions, stop)
    fetched = swarm.desk_fetched()
    union = None if fetched is None else fetched.any(1)
    if fetched is None:
        fetched = torch.zeros(count, M, 1, dtype=torch.bool, device=device)
    detail = {"desk_fetched": fetched, "desk_asks": asks, "registers": swarm.registers().float(),
              "notes": board.notes.clone() if board is not None and lesion != "notes" else None,
              "rounds": rounds}
    return Answers(tokens, lengths, torch.full((count,), rounds, dtype=torch.long, device=device),
                   first_top, union, halt_prob, detail)


__all__ = ["Board", "balanced_assignment", "combiner_memory", "diversity", "entity_table", "fetch_overlap", "is_collapsed",
           "merge_mask", "register_cos", "swarm_answer", "swarm_forward"]
