"""Guard metric of the decoder_reader_kv A/B: does the thinker still ASK and fetch?

The new decoder path can answer from the reader states directly, which would let the writer
bypass the thinker. Per question, on the model's own greedy answers (`PremonitionMini.answer`):

  asks[q]   loops whose ASK fetched: ASK logit > 0 on a loop that did not end (halt or limit),
            exactly the condition under which `answer` inserts cards
  cards[q]  distinct real cards fetched (the NULL card is counted apart, in nulls[q])

`summarize` adds loops_mean and halt_rate as `train.validate` defines them, and fetched_any_rate:
the share of questions that fetched at least one real card (what `train.validate` calls asked_rate).

`guard_verdict` applies the run card's rule: the gain is not counted when the flag-on arm's
mean cards fetched per question falls more than 20% below control's (pooled over the paired
seeds), or when control fetches nothing (the guard cannot be read).
"""
from __future__ import annotations

from typing import Any, Optional, Sequence

import torch

MAX_FETCH_DROP = 0.20


def guard_counts(model, batch, *, max_loops: Optional[int] = None, **answer_kwargs: Any):
    """(answers, asks [Q] long, cards [Q] long, nulls [Q] long) for one batch."""
    count = batch.q_visit.shape[0]
    asks = torch.zeros(count, dtype=torch.long, device=batch.q_visit.device)
    limit = min(max_loops or model.config.max_loops, model.config.max_loops)
    step = model._step

    def counting(episode, index, loop, store):
        rows, halt, ask, scores = step(episode, index, loop, store)
        if ask is not None:
            done = (torch.sigmoid(halt) > 0.5) | (loop + 1 == limit)
            asks.index_add_(0, index.to(asks.device), ((ask > 0) & ~done).long().to(asks.device))
        return rows, halt, ask, scores

    model._step = counting
    try:
        answers = model.answer(batch, max_loops=max_loops, **answer_kwargs)
    finally:
        del model._step
    if answers.fetched is None:
        zero = torch.zeros_like(asks)
        return answers, asks, zero, zero
    return answers, asks, answers.fetched[:, :-1].sum(1), answers.fetched[:, -1].long()


def summarize(answers, asks: torch.Tensor, cards: torch.Tensor, nulls: torch.Tensor) -> dict[str, float]:
    """Per-question means for one arm and seed; the arguments are `guard_counts`' four results."""
    n = max(int(asks.numel()), 1)
    return {"questions": int(asks.numel()), "asks_per_question": float(asks.sum()) / n,
            "cards_per_question": float(cards.sum()) / n, "null_per_question": float(nulls.sum()) / n,
            "fetched_any_rate": float((cards > 0).sum()) / n,
            "loops_mean": float(answers.loops.sum()) / n, "halt_rate": float((answers.halt_prob > 0.5).sum()) / n}


def guard_verdict(control: Sequence[dict], treated: Sequence[dict],
                  max_drop: float = MAX_FETCH_DROP) -> dict[str, Any]:
    """Paired per-seed `summarize` rows (same seed order) -> the guard reading, per seed and pooled."""
    if len(control) != len(treated) or not control:
        raise ValueError("guard needs the same, non-zero number of control and treated seeds")
    rows = []
    for c, t in zip(control, treated):
        base = c["cards_per_question"]
        rows.append({"control_cards": base, "treated_cards": t["cards_per_question"],
                     "control_asks": c["asks_per_question"], "treated_asks": t["asks_per_question"],
                     "relative_drop": (1 - t["cards_per_question"] / base) if base > 0 else None})
    base = sum(c["cards_per_question"] for c in control) / len(control)
    mean = sum(t["cards_per_question"] for t in treated) / len(treated)
    if base <= 0:
        return {"per_seed": rows, "pooled_drop": None, "holds": False,
                "reading": "guard not readable (control fetches no cards): gain not counted"}
    drop = 1 - mean / base
    holds = drop <= max_drop
    return {"per_seed": rows, "pooled_drop": drop, "holds": holds,
            "reading": "guard holds" if holds else "gain not counted (writer bypassed the thinker)"}


__all__ = ["MAX_FETCH_DROP", "guard_counts", "guard_verdict", "summarize"]
