"""Surprise-picked replay (T2 mechanism 1, toy PASS 3/3 on 2026-11-04 as `mix2`; see premonition-sleeplab-t2).

Plain version: at the same number of training steps, half of each step's cards are picked by how SURPRISED the
current adapter still is by them (how badly it predicts the card's answer), the other half is ordinary rehearsal
(today's priority draw). Cards whose truth is not consistent (the same question logged with different answers:
"TV static") never count as surprising and are not trained on at all, because no update can learn them.

Automatic and mathematical: the score is the model's own log-loss on the card's answer, computed by formula; the
model never chooses what is stored.

Toy evidence only (tiny transformer + LoRA, 3 seeds): +13 to +23 points recall of new facts under a held-out wording,
general set within 2 points of uniform, TV static < 1 % of draws. Untested on Nanbeige: the morning check reports
what it did on the real night.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

FLOOR = 0.05   # every scored card keeps 5 % of the mean surprise as weight (toy value)


def qnorm(q: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", str(q).lower()).split())


def conflicted_questions(items: Iterable) -> Set[str]:
    """Normalized questions that live items answer in more than one way (inconsistent truth -> noise).
    `items` have .dead and .qa = [[q, a], ...]. A correction retires (kills) the old item, so a corrected
    question is consistent again."""
    answers: Dict[str, set] = defaultdict(set)
    for it in items:
        if getattr(it, "dead", False):
            continue
        for qa in getattr(it, "qa", None) or []:
            answers[qnorm(qa[0])].add(qnorm(qa[1]))
    return {q for q, a in answers.items() if len(a) > 1}


def clean_qa(it, conflicted: Set[str]) -> List:
    return [qa for qa in (it.qa or []) if qnorm(qa[0]) not in conflicted]


def item_cards(it, conflicted: Set[str]) -> List:
    """The cards an item may train on under the picker: its text cards and its consistent Q&A."""
    return list(it.para or []) + clean_qa(it, conflicted)


def surprise_weights(scores: Sequence[Optional[float]], floor: float = FLOOR) -> List[float]:
    """scores: per item mean answer log-loss (None = not scored / nothing consistent to score -> weight 0)."""
    vals = [max(0.0, s) for s in scores if s is not None]
    mean = (sum(vals) / len(vals)) if vals else 0.0
    eps = floor * (mean if mean > 0 else 1.0)
    return [0.0 if s is None else max(0.0, s) + eps for s in scores]


def split(n: int, share: float) -> Tuple[int, int]:
    """n cards -> (surprise-picked, rehearsal)."""
    k = int(round(max(0.0, min(1.0, share)) * n))
    return k, n - k


def mean_or_none(xs: Sequence[float]) -> Optional[float]:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None
