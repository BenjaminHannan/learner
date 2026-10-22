"""Reflow a `premonition.data.VisitCache`: move line breaks so they no longer coincide with facts, keep the labels true.

Memory cards are written one per text line (`premonition.batch`), so a model can lean on "one line, one fact". This
module is a data-stress transform for evaluation (and optional training augmentation) that breaks that coincidence,
by two edits on NON-question lines only; question lines are never touched, only moved:

  merge  consecutive non-question lines become one line: the first line's trailing newline is dropped, and the
         next line loses a leading token sequence from `drop_prefixes` (e.g. the "[world]" tag) if it starts with one.
  split  one non-question line becomes two lines, a newline inserted before an interior token. Only lines that were
         NOT merged are split (merged lines stay whole), so no line is ever edited twice.

Per visit the lines are walked in order with `random.Random(f"{seed}:{visit_id}")`, so a visit's result depends on
the seed and its own id only, never on the other visits or their order. At a non-question line `k` the line is
extended with line `k+1`, `k+2`, ... while the next line exists and is not a question, fewer than `max_merge`
original lines are joined, and `rng.random() < merge`. A line left alone then splits when `rng.random() < split`:
the split point is drawn uniformly among interior positions `1 <= i <= len-2` (both halves keep a non-newline token),
restricted to word starts when `word_start` is given: `word_start[token]` for a tokenizer id, and always true for an
entity id (>= `vocab_size`). A line with no valid split point stays as it is.

Everything the cache stores about lines and positions is remapped to the new layout:

  tokens, line_offsets, visit_lines    rebuilt (int16, int32, int64 as in the input)
  line_is_question, visit_questions    questions keep their order; `visit_questions` is unchanged
  line_ents                            a question line keeps its row; an unchanged non-question line keeps its row;
                                       a merged or split-off line gets the distinct entity ids (token - vocab_size)
                                       in order of first appearance, the first MAX_LINE_ENTS, -1 padded, int8
                                       (what `premonition.data` computes), so a merge can push a line past the cap
  q_line                               the question's new line index within its visit
  q_span, answer_end                   shifted by the change of the question line's start offset within the visit
  gold                                 each old gold line becomes the new line(s) holding its tokens: a merged line
                                       maps to the merged line, a split line to BOTH halves; sorted, distinct
  info                                 a deep copy plus `info["reflow"]` (the arguments and the stats below); the
                                       build-time `info["tokens"]` count, when present, is updated to the new total

`merge == split == 0` returns a cache equal to the input in every field except the added `info["reflow"]`.
Every line of the input (questions too) must end with `newline_id`, else ValueError. A merged line can exceed
`MAX_LINE_ENTS` entities and a batch then sees only the first ones; `stats["ents_over_max"]` counts those lines.
A split can push a question past `MAX_GOLD` evidence lines, and a batch then keeps only the newest `MAX_GOLD`:
`stats["gold_over_max"]` counts those questions (`gold_over_max_before` the input's). When any line changed, the
build-time `info["stats"]` counts `gold_over_max`, `gold_max` and `line_ents_over_max` are replaced by the new
layout's, so a reflowed cache never reports its old counts.
"""
from __future__ import annotations

import copy
import random
from typing import Any, Optional, Sequence

import torch

from .batch import MAX_GOLD, MAX_LINE_ENTS
from .data import VisitCache


def _check_lines(cache: VisitCache, newline_id: int) -> None:
    """Every line is non-empty and ends with `newline_id` (ValueError naming the first offender otherwise)."""
    offsets = cache.line_offsets.long()
    lengths = offsets[1:] - offsets[:-1]
    bad = (lengths < 1).nonzero().flatten().tolist()
    if not bad:
        bad = (cache.tokens[offsets[1:] - 1] != newline_id).nonzero().flatten().tolist()
    if bad:
        visit = int(torch.searchsorted(cache.visit_lines, torch.tensor(bad[0]), right=True)) - 1
        raise ValueError(f"line {bad[0]} (visit {visit}, {cache.visit_ids[visit]!r}) does not end with the "
                         f"newline token {newline_id}")


def _starts_with(line: torch.Tensor, prefix: Sequence[int]) -> bool:
    return len(prefix) < line.numel() and line[:len(prefix)].tolist() == list(prefix)


def _entities(line: torch.Tensor, base: int) -> list[int]:
    """The distinct entity ids (token - base) of a line, in order of first appearance."""
    found = line[line >= base]
    return list(dict.fromkeys((found.long() - base).tolist())) if found.numel() else []


def _merged(lines: Sequence[torch.Tensor], prefixes: Sequence[Sequence[int]]) -> torch.Tensor:
    """Lines joined: every trailing newline but the last dropped, a leading drop-prefix removed from every line but the first."""
    parts = []
    for j, line in enumerate(lines):
        if j > 0:
            drop = max((len(p) for p in prefixes if _starts_with(line, p)), default=0)
            line = line[drop:]
        parts.append(line if j == len(lines) - 1 else line[:-1])
    return torch.cat(parts)


def _split_points(line: torch.Tensor, base: int, word_start: Optional[torch.Tensor]) -> list[int]:
    """Interior positions i (1 <= i <= len-2) where a newline may be inserted before token i."""
    if line.numel() < 3:
        return []
    inner = line[1:-1].long()
    if word_start is None:
        return list(range(1, line.numel() - 1))
    allowed = (inner >= base) | word_start[inner.clamp(max=base - 1)]
    return (allowed.nonzero().flatten() + 1).tolist()


def _offsets(counts: Sequence[int], dtype: torch.dtype) -> torch.Tensor:
    return torch.cumsum(torch.tensor([0, *counts], dtype=torch.long), 0).to(dtype)


def reflow_cache(cache: VisitCache, *, merge: float = 0.0, split: float = 0.0, seed: int = 0, newline_id: int,
                 drop_prefixes: Sequence[Sequence[int]] = (), word_start: Optional[torch.Tensor] = None,
                 max_merge: int = 3, return_map: bool = False) -> Any:
    """The cache with its non-question lines merged and split (see the module doc); the input is not modified.

    `merge` / `split`: probabilities in [0, 1]. `max_merge`: most original lines in one merged line. `word_start`:
    bool tensor over tokenizer ids (at least `cache.vocab_size` long). With `return_map` the result is
    `(cache, maps)` where `maps[v][old_line]` is the list of new lines (within visit `v`) holding that old line's
    tokens: one line when it was kept or merged, two when it was split.
    """
    if not (0.0 <= merge <= 1.0 and 0.0 <= split <= 1.0):
        raise ValueError(f"merge and split must lie in [0, 1], got {merge} and {split}")
    if max_merge < 1:
        raise ValueError("max_merge must be at least 1")
    prefixes = [list(p) for p in drop_prefixes]
    if any(not p for p in prefixes):
        raise ValueError("a drop prefix must not be empty")
    base = cache.vocab_size
    if word_start is not None and (word_start.dtype != torch.bool or word_start.dim() != 1
                                   or word_start.numel() < base):
        raise ValueError(f"word_start must be a bool vector over the {base} tokenizer ids")
    _check_lines(cache, newline_id)

    tokens, offsets, is_question = cache.tokens, cache.line_offsets.long(), cache.line_is_question
    newline = torch.tensor([newline_id], dtype=tokens.dtype)
    stats = {"lines_before": int(is_question.numel()), "lines_after": 0, "merged_lines": 0, "split_lines": 0,
             "ents_over_max": 0, "gold_over_max": 0, "gold_over_max_before": 0}
    parts: list[torch.Tensor] = []          # new token pieces, in order
    run: list[int] = []                     # [start, end) of a pending run of unchanged original tokens
    lengths: list[int] = []                 # new line lengths
    new_question: list[bool] = []
    copied: list[tuple[int, int]] = []      # (new global line, old global line) whose line_ents row is kept
    computed: set[int] = set()              # new global lines made by a merge or split (their line_ents are recomputed)
    visit_counts: list[int] = []
    maps: list[list[list[int]]] = []
    q_shift = torch.zeros(len(cache.question_ids), dtype=torch.long)
    q_line = cache.q_line.clone()
    gold_rows: list[list[int]] = []

    def flush() -> None:
        if run:
            parts.append(tokens[run[0]:run[1]])
            run.clear()

    def unchanged(old: int) -> None:
        start, end = int(offsets[old]), int(offsets[old + 1])
        if run and run[1] == start:
            run[1] = end
        else:
            flush()
            run.extend((start, end))
        lengths.append(end - start)

    def changed(piece: torch.Tensor) -> None:
        flush()
        parts.append(piece)
        lengths.append(piece.numel())

    for v in range(len(cache)):
        first, last = int(cache.visit_lines[v]), int(cache.visit_lines[v + 1])
        rng = random.Random(f"{seed}:{cache.visit_ids[v]}")
        new_first = len(lengths)
        mapping: list[list[int]] = [[] for _ in range(last - first)]
        k = first
        while k < last:
            new = len(lengths)
            if bool(is_question[k]):
                end = k + 1
                unchanged(k)
                copied.append((new, k))
                new_question.append(True)
                pieces = [new]
            else:
                end = k + 1
                while end < last and end - k < max_merge and not bool(is_question[end]) and rng.random() < merge:
                    end += 1
                lines = [tokens[int(offsets[j]):int(offsets[j + 1])] for j in range(k, end)]
                if end - k > 1:
                    changed(_merged(lines, prefixes))
                    stats["merged_lines"] += 1
                    computed.add(new)
                    new_question.append(False)
                    pieces = [new]
                else:
                    points = _split_points(lines[0], base, word_start) if rng.random() < split else []
                    if points:
                        i = rng.choice(points)
                        changed(torch.cat([lines[0][:i], newline]))
                        changed(lines[0][i:])
                        stats["split_lines"] += 1
                        computed.update((new, new + 1))
                        new_question.extend((False, False))
                        pieces = [new, new + 1]
                    else:
                        unchanged(k)
                        copied.append((new, k))
                        new_question.append(False)
                        pieces = [new]
            for j in range(k, end):
                mapping[j - first] = [p - new_first for p in pieces]
            k = end
        visit_counts.append(len(lengths) - new_first)
        maps.append(mapping)
        starts = [0]
        for length in lengths[new_first:]:
            starts.append(starts[-1] + length)
        base_offset = int(offsets[first])
        for q in cache.questions_of(v):
            old = int(cache.q_line[q])
            if not (0 <= old < last - first and bool(is_question[first + old])):
                raise ValueError(f"question {cache.question_ids[q]!r}: line {old} is not a question line of visit {v}")
            new = mapping[old][0]
            q_line[q] = new
            q_shift[q] = starts[new] - (int(offsets[first + old]) - base_offset)
            lines_of = sorted({n for g in cache.gold_lines(q) for n in _gold_lines(mapping, g, cache.question_ids[q])})
            gold_rows.append(lines_of)
            stats["gold_over_max"] += len(lines_of) > MAX_GOLD
            stats["gold_over_max_before"] += len(cache.gold_lines(q)) > MAX_GOLD
    flush()

    new_tokens = torch.cat(parts) if parts else tokens[:0].clone()
    stats["lines_after"] = len(lengths)
    # line_ents: copy the kept rows, recompute the rest from the new tokens.
    new_offsets = _offsets(lengths, torch.long)
    line_ents = torch.full((len(lengths), MAX_LINE_ENTS), -1, dtype=cache.line_ents.dtype)
    if copied:
        new_rows, old_rows = (torch.tensor(x, dtype=torch.long) for x in zip(*copied))
        line_ents[new_rows] = cache.line_ents[old_rows]
    for n in range(len(lengths)):
        if new_question[n]:
            continue
        ents = _entities(new_tokens[int(new_offsets[n]):int(new_offsets[n + 1])], base)
        stats["ents_over_max"] += len(ents) > MAX_LINE_ENTS
        if n in computed:
            shown = ents[:MAX_LINE_ENTS]
            line_ents[n, :len(shown)] = torch.tensor(shown, dtype=line_ents.dtype)

    gold_counts = [len(row) for row in gold_rows]
    info = copy.deepcopy(cache.info)
    if "tokens" in info:
        info["tokens"] = int(new_tokens.numel())
    if isinstance(info.get("stats"), dict) and (stats["merged_lines"] or stats["split_lines"]):
        # The build-time counts describe the old layout; a split can push a question past MAX_GOLD gold lines
        # (a batch then keeps only the newest MAX_GOLD) and a merge a line past MAX_LINE_ENTS entities.
        info["stats"]["gold_over_max"] = stats["gold_over_max"]
        info["stats"]["line_ents_over_max"] = stats["ents_over_max"]
        if "gold_max" in info["stats"]:
            info["stats"]["gold_max"] = max((len(row) for row in gold_rows), default=0)
    info["reflow"] = {"merge": merge, "split": split, "seed": seed, "max_merge": max_merge, "stats": stats}
    out = VisitCache(
        split=cache.split, vocab_size=cache.vocab_size, tokens=new_tokens,
        line_offsets=_offsets(lengths, cache.line_offsets.dtype), visit_lines=_offsets(visit_counts, torch.long),
        line_is_question=torch.tensor(new_question, dtype=torch.bool), line_ents=line_ents,
        visit_questions=cache.visit_questions.clone(), q_line=q_line, q_span=cache.q_span + q_shift[:, None],
        answer_end=cache.answer_end + q_shift, answer_offsets=cache.answer_offsets.clone(),
        answer_ids=cache.answer_ids.clone(), gold_offsets=_offsets(gold_counts, cache.gold_offsets.dtype),
        gold=torch.tensor([g for row in gold_rows for g in row], dtype=cache.gold.dtype),
        depth=cache.depth.clone(), knowable=cache.knowable.clone(), question_ids=list(cache.question_ids),
        visit_ids=list(cache.visit_ids), names=[list(n) for n in cache.names], info=info,
        target_unbound=None if cache.target_unbound is None else cache.target_unbound.clone())
    return (out, maps) if return_map else out


def _gold_lines(mapping: Sequence[Sequence[int]], line: int, question_id: str) -> Sequence[int]:
    if not 0 <= line < len(mapping):
        raise ValueError(f"question {question_id!r}: gold line {line} is outside its visit")
    return mapping[line]


__all__ = ["reflow_cache"]
