"""BM25 queries -> reciprocal-rank fusion (k=60) -> trim to the k_tokens budget with the tokenizer."""
from __future__ import annotations

from dataclasses import dataclass, field

K_TOKENS = 1500
RRF_K = 60
DEPTH = 50  # hits kept per query before fusion; deep enough that the 1.5k-token budget (about 35 turns), not the depth, limits every arm


def render_turn(t: dict) -> str:
    return f"[Day {t['day']}] {t['text']}"


def rrf(ranked_lists: list[list[int]], k: int = RRF_K) -> list[tuple[int, float]]:
    """score(d) = sum over lists of 1 / (k + rank), rank from 1. Sorted by score desc, then turn_id asc (deterministic)."""
    sc: dict[int, float] = {}
    for lst in ranked_lists:
        for r, d in enumerate(lst, 1):
            sc[d] = sc.get(d, 0.0) + 1.0 / (k + r)
    return sorted(sc.items(), key=lambda x: (-x[1], x[0]))


def trim(order: list[int], index, count_tokens, budget: int = K_TOKENS) -> tuple[list[int], int]:
    """Take turns in fused order while the rendered context stays within `budget` tokens (stop at the first that does not fit).
    Returns (kept turn ids in fused order, tokens used). Each turn costs count_tokens(rendered line + newline)."""
    kept, used = [], 0
    for d in order:
        n = count_tokens(render_turn(index.get(d)) + "\n")
        if used + n > budget:
            break
        kept.append(d)
        used += n
    return kept, used


@dataclass
class Retrieval:
    queries: list[str]
    lists: list[list[int]]
    fused: list[int]            # fused ranking before trimming
    kept: list[int]             # after trimming, fused order
    k_tokens: int
    ranking_top3: list[int] = field(default_factory=list)


def retrieve(index, queries: list[str], count_tokens, budget: int = K_TOKENS, depth: int = DEPTH) -> Retrieval:
    queries = [q for q in queries if q and q.strip()]
    lists = [index.search(q, depth) for q in queries]
    fused = [d for d, _ in rrf(lists)] if len(lists) > 1 else (lists[0] if lists else [])
    kept, used = trim(fused, index, count_tokens, budget)
    return Retrieval(queries, lists, fused, kept, used, fused[:3])


def context_text(index, kept: list[int]) -> str:
    """Chronological (day, then turn id), as the project's diary prompt shows notes."""
    ts = sorted((index.get(d) for d in kept), key=lambda t: (t["day"], t["turn_id"]))
    return "\n".join(render_turn(t) for t in ts)


def hit_at(ranking: list[int], gold: list[int] | set[int], k: int = 3) -> bool | None:
    return None if not gold else bool(set(ranking[:k]) & set(gold))
