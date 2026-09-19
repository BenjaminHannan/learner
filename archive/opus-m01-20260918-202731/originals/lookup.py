"""Contender C's plain lookup (design/06 §5): BM25 recall of a visit's earlier lines into A's window.

C is A (`Core` 4M, context 768) with a lookup in front of it. For one question:

1. Candidates: the non-question lines of the same visit before A's window start, A's window being
   `step1.build_items`' cut at `slices.CUT_MAX_LEN` (736) tokens (`cut_window` below is that cut).
2. Score: BM25 (k1 1.2, b 0.75); document frequencies, line count and mean line length come from the
   train split's non-question lines. Terms are lowercase letter/digit runs with the stream tags
   ("[world]", "[answer]" ...) removed. The query is the question's distinct terms minus English
   stopwords; a capitalised word that does not start a sentence (a name) is always kept.
3. Select: the top 8 with score > 0 (a newer line wins a tie), taken in rank order while their total
   stays within 192 tokens (the first line that would overflow ends the selection), then put back in
   chronological order.
4. Input: `<eos>`, the recalled lines, `<bos>`, then the window cut at whole lines to fill the rest of
   736 tokens (`build_items` logic: `<eos>` first when the window reaches the visit's start), then the
   question line up to "[answer]". `<bos>` never occurs in the village stream (checked on the large
   build: no "<bos>" in the text of any split, no id 1 among the 116.7M encoded train tokens), so it
   marks the end of the recalled block unambiguously. The leading `<eos>` is the training rows'
   row-start token, kept at evaluation so train and test inputs line up position by position.
5. Training rows, exactly 768 tokens each, alternate: a plain row is `<eos>` + the next 767 tokens of
   A's stream (`step1.stream_for`); a question-centred row is a train question's input as in 4, then
   its answer and feedback and the rest of its visit, `<eos>` at the visit's end and `<pad>` up to 768.
   Masked (never a target): the row-start `<eos>`, everything before the window (recalled lines,
   `<bos>`, the visit-start `<eos>`) and the padding. `Trainer._next_batch` overlaps consecutive rows by
   one token, so with seq_len 768 every input row is exactly one of these rows and each row's last
   target is the next row's masked `<eos>`.
6. Diagnostic: gold recall@8 on far questions. Each evidence line before A's window start is one
   target, hit when the lookup recalled it (`metrics.recall_at_k` over the selected lines in rank
   order); the unbudgeted top 8 is reported too.

Label-free inputs (design/06 §9.1): with `labels=False` every earlier question line keeps its question
and drops its "[answer] ... [feedback] ..." spans (`label_free`); the window cut, A's window start and
so the candidates are computed on those lines. Training rows keep labels (answers are LM targets).
"""
from __future__ import annotations

from array import array
from collections import Counter, deque
from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
import json
import math
import multiprocessing
from pathlib import Path
import random
import re
import time
from typing import Any, Callable, Iterable, Iterator, Mapping, Optional, Sequence

import torch

from learnlab import step1
from learnlab.metrics import recall_at_k
from learnlab.step1 import ANSWER_TAG, QUESTION_TAG, Question
from learnlab.tokenizer import Tokenizer

from premonition.slices import CUT_MAX_LEN, SEQ_LEN

K1 = 1.2
B = 0.75
TOP_K = 8
RECALL_TOKENS = 192
SEPARATOR = "<bos>"
FORMAT = "premonition.bm25"
VERSION = 1
STATS_FILE = f"premonition-bm25-v{VERSION}.json"
_TAG = re.compile(r"\[[^\]\s]*\]")          # stream tags: [world], [question], [answer], [feedback] ...
_TERM = re.compile(r"[^\W_]+")              # letter/digit runs
_SENTENCE_END = tuple(".!?:;\"'(")
STOPWORDS = frozenset("""
a about above after again against all am an and any are as at be because been before being below between both but
by can could did do does doing done down during each few for from further had has have having he her here hers
herself him himself his how i if in into is it its itself just me more most must my myself no nor not now of off
on once only or other our ours ourselves out over own same shall she should so some such than that the their
theirs them themselves then there these they this those through to too under until up us very was we were what
when where which while who whom whose why will with would yes you your yours yourself
""".split())

Log = Callable[[str], None]


# ----------------------------------------------------------------- text


def label_free(line: str) -> str:
    """A question line without its answer and feedback spans (design/06 §9.1); other lines unchanged."""
    if line.startswith(QUESTION_TAG) and ANSWER_TAG in line:
        return line[: line.index(ANSWER_TAG)].rstrip()
    return line


def shown(line: str, labels: bool) -> str:
    return line if labels else label_free(line)


@lru_cache(maxsize=500_000)
def terms(text: str) -> tuple[str, ...]:
    """BM25 terms of a line: lowercase letter/digit runs, stream tags removed."""
    return tuple(_TERM.findall(_TAG.sub(" ", text).lower()))


@lru_cache(maxsize=500_000)
def _doc(text: str) -> tuple[dict[str, int], int]:
    found = terms(text)
    return dict(Counter(found)), len(found)


def query_terms(question: str) -> tuple[str, ...]:
    """The question's distinct terms minus stopwords; a capitalised word inside a sentence (a name) is kept."""
    text = _TAG.sub(" ", question)
    out: list[str] = []
    for match in _TERM.finditer(text):
        raw, word = match.group(), match.group().lower()
        before = text[: match.start()].rstrip()
        name = raw[:1].isupper() and bool(before) and not before.endswith(_SENTENCE_END)
        if (word in STOPWORDS and not name) or word in out:
            continue
        out.append(word)
    return tuple(out)


# ----------------------------------------------------------------- BM25


@dataclass(frozen=True)
class Bm25:
    """BM25 statistics of the train split's non-question lines."""

    lines: int
    avgdl: float
    df: Mapping[str, int]
    k1: float = K1
    b: float = B

    def idf(self, term: str) -> float:
        n = self.df.get(term, 0)
        return math.log(1.0 + (self.lines - n + 0.5) / (n + 0.5))

    def scorer(self, query: Sequence[str]) -> Callable[[str], float]:
        """score(line text) for one query (its IDFs computed once)."""
        weights = [(term, self.idf(term)) for term in dict.fromkeys(query)]
        k1, b, avgdl = self.k1, self.b, max(self.avgdl, 1e-9)

        def score(text: str) -> float:
            counts, length = _doc(text)
            norm = k1 * (1.0 - b + b * length / avgdl)
            total = 0.0
            for term, weight in weights:
                tf = counts.get(term)
                if tf:
                    total += weight * tf * (k1 + 1.0) / (tf + norm)
            return total

        return score

    def payload(self) -> dict[str, Any]:
        return {"format": FORMAT, "version": VERSION, "lines": self.lines, "avgdl": self.avgdl,
                "k1": self.k1, "b": self.b, "df": dict(sorted(self.df.items()))}

    @property
    def digest(self) -> str:
        canonical = json.dumps(self.payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "sha256": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Bm25:
        if data.get("format") != FORMAT or data.get("version") != VERSION:
            raise ValueError(f"not a {FORMAT} v{VERSION} table")
        stats = cls(int(data["lines"]), float(data["avgdl"]), {str(k): int(v) for k, v in data["df"].items()},
                    float(data["k1"]), float(data["b"]))
        if data.get("sha256") is not None and data["sha256"] != stats.digest:
            raise ValueError("BM25 table digest mismatch")
        return stats


def fit_bm25(lines: Iterable[str], *, k1: float = K1, b: float = B) -> Bm25:
    """Statistics over `lines` (question lines are skipped)."""
    df: Counter[str] = Counter()
    count = total = 0
    for line in lines:
        if line.startswith(QUESTION_TAG):
            continue
        found = terms(line)
        count += 1
        total += len(found)
        df.update(set(found))
    return Bm25(count, total / max(count, 1), dict(df), k1, b)


def split_lines(split_dir: Path) -> Iterator[str]:
    """Every stream line of a split directory, shard by shard."""
    for text, _ in step1.shard_files(Path(split_dir)):
        for visit in step1.read_visits(text):
            for _, line in visit:
                yield line


def train_bm25(budget: Any, data_rel: str, *, log: Log = print) -> Bm25:
    """The data build's table: `<data_rel>/premonition-bm25-v1.json` if written before, else fitted on the
    train split and written there through the budget."""
    relative = f"{data_rel}/{STATS_FILE}"
    path = Path(budget.root) / relative
    if path.is_file():
        return Bm25.from_dict(json.loads(path.read_text(encoding="utf-8")))
    started = time.perf_counter()
    stats = fit_bm25(split_lines(Path(budget.root) / data_rel / "train"))
    budget.save_json(relative, stats.to_dict(), 50_000_000)
    log(f"premonition lookup: BM25 over {stats.lines:,} train lines, {len(stats.df):,} terms, mean length "
        f"{stats.avgdl:.2f} ({stats.digest[:12]}) in {time.perf_counter() - started:.1f}s")
    return stats


# ----------------------------------------------------------------- windows and inputs


class LineIds:
    """Token ids of stream lines as the model reads them (label-free if asked), each with its newline; cached."""

    def __init__(self, tokenizer: Tokenizer, labels: bool = True) -> None:
        self.tokenizer, self.labels = tokenizer, labels
        self._cache: dict[str, list[int]] = {}

    def __call__(self, line: str) -> list[int]:
        found = self._cache.get(line)
        if found is None:
            if len(self._cache) >= 200_000:
                self._cache.clear()
            found = self._cache[line] = self.tokenizer.encode(shown(line, self.labels) + "\n")
        return found


@dataclass(frozen=True)
class Window:
    """`step1.build_items`' cut: the newest whole lines that fit `room`, <eos> first if the visit starts in it."""

    ids: list[int]
    start: int              # shard line number of the first kept line (the question's own line if none)
    kept: int
    whole: bool             # every earlier line of the visit is kept
    prefix: bool            # ids begin with the visit-start <eos>


def cut_window(numbers: Sequence[int], pieces: Sequence[Sequence[int]], room: int, eos: int,
               question_line: int) -> Window:
    """The window over a visit's earlier lines (`numbers` with their token `pieces`), within `room` tokens."""
    kept: list[int] = []
    used = 0
    for index in range(len(pieces) - 1, -1, -1):
        size = len(pieces[index])
        if used + size > room:
            break
        kept.append(index)
        used += size
    kept.reverse()
    whole = len(kept) == len(pieces)
    prefix = whole and used + 1 <= room
    ids = [eos] if prefix else []
    for index in kept:
        ids.extend(pieces[index])
    return Window(ids=ids, start=numbers[kept[0]] if kept else question_line, kept=len(kept), whole=whole,
                  prefix=prefix)


def question_tail(tokenizer: Tokenizer, question: Question) -> list[int]:
    """The question's own line up to and including "[answer]"."""
    tail = tokenizer.encode(question.prompt_line)
    if tail[-1] != tokenizer.token_to_id(ANSWER_TAG):
        raise AssertionError(f"prompt for {question.id} does not end with {ANSWER_TAG}")
    return tail


def plain_input(question: Question, lines: LineIds, *, max_len: int = CUT_MAX_LEN) -> tuple[list[int], Window]:
    """A's input (step 1's `build_items` prompt, label-free when `lines` is): the window, then the question."""
    tokenizer = lines.tokenizer
    tail = question_tail(tokenizer, question)
    window = cut_window([n for n, _ in question.context], [lines(line) for _, line in question.context],
                        max_len - len(tail), tokenizer.token_to_id("<eos>"), question.line)
    return window.ids + tail, window


@dataclass(frozen=True)
class Recall:
    lines: tuple[int, ...]      # recalled shard line numbers, chronological
    ranked: tuple[int, ...]     # the same lines in rank order
    top: tuple[int, ...]        # the top TOP_K lines with score > 0, before the token budget (diagnostic)
    tokens: int                 # tokens of the recalled lines
    candidates: int


def recall(bm25: Bm25, question: str, candidates: Sequence[tuple[int, str]], length: Callable[[str], int], *,
           top_k: int = TOP_K, budget: int = RECALL_TOKENS) -> Recall:
    """design/06 §5 steps 2-3 over `candidates` ((shard line number, text), all before A's window)."""
    score = bm25.scorer(query_terms(question))
    scored = [(value, number, text) for number, text in candidates if (value := score(text)) > 0]
    scored.sort(key=lambda entry: (-entry[0], -entry[1]))       # higher score first; newer line wins a tie
    top = scored[:top_k]
    chosen: list[tuple[int, str]] = []
    used = 0
    for _, number, text in top:
        size = length(text)
        if used + size > budget:
            break
        chosen.append((number, text))
        used += size
    return Recall(lines=tuple(sorted(n for n, _ in chosen)), ranked=tuple(n for n, _ in chosen),
                  top=tuple(n for _, n, _ in top), tokens=used, candidates=len(candidates))


@dataclass(frozen=True)
class LookupInput:
    ids: list[int]              # the model input, ending with "[answer]"
    recall: Recall
    a_start: int                # A's window start (shard line): candidates are the lines before it
    window: Window              # C's own window (shorter than A's by the recalled block)
    masked: int                 # leading tokens that are never targets: <eos>, recalled lines, <bos>, visit <eos>
    evidence_before: tuple[int, ...]   # evidence lines before A's window start (the recall targets)


def candidates(question: Question, before: int) -> list[tuple[int, str]]:
    """Non-question lines of the question's visit before shard line `before`."""
    return [(n, line) for n, line in question.context if n < before and not line.startswith(QUESTION_TAG)]


def lookup_input(question: Question, lines: LineIds, bm25: Bm25, *, max_len: int = CUT_MAX_LEN,
                 top_k: int = TOP_K, budget: int = RECALL_TOKENS) -> LookupInput:
    """C's input for one question (design/06 §5 step 4)."""
    tokenizer = lines.tokenizer
    eos, bos = tokenizer.token_to_id("<eos>"), tokenizer.token_to_id(SEPARATOR)
    tail = question_tail(tokenizer, question)
    numbers = [n for n, _ in question.context]
    pieces = [lines(line) for _, line in question.context]
    a_window = cut_window(numbers, pieces, max_len - len(tail), eos, question.line)
    found = recall(bm25, question.question, candidates(question, a_window.start), lambda text: len(lines(text)),
                   top_k=top_k, budget=budget)
    text_of = dict(question.context)
    block = [eos]
    for number in found.lines:
        block.extend(lines(text_of[number]))
    block.append(bos)
    window = cut_window(numbers, pieces, max_len - len(tail) - len(block), eos, question.line)
    ids = block + window.ids + tail
    if len(ids) > max_len or ids[-1] != tail[-1]:
        raise AssertionError(f"C input for {question.id} has {len(ids)} tokens (max {max_len})")
    evidence = tuple(sorted({e for e in question.evidence if 0 <= e < a_window.start}))
    return LookupInput(ids=ids, recall=found, a_start=a_window.start, window=window,
                       masked=len(block) + int(window.prefix), evidence_before=evidence)


def is_far(question: Question, a_start: int) -> bool:
    """Knowable with an evidence line outside A's window (the canonical far tag when inputs keep labels)."""
    return question.knowable is True and any(0 <= e < a_start for e in question.evidence)


def recall_report(entries: Sequence[LookupInput], k: int = TOP_K) -> dict[str, Any]:
    """Gold recall@k of far questions' inputs (design/06 §5 step 6): one target per evidence line before
    A's window, hit when recalled; `all_gold_recalled` is over the questions that have a target."""
    ranked: list[tuple[int, ...]] = []
    top: list[tuple[int, ...]] = []
    targets: list[int] = []
    complete = with_targets = 0
    for entry in entries:
        for line in entry.evidence_before:
            ranked.append(entry.recall.ranked)
            top.append(entry.recall.top)
            targets.append(line)
        if entry.evidence_before:
            with_targets += 1
            complete += set(entry.evidence_before) <= set(entry.recall.lines)
    n = len(entries)
    return {
        "far_questions": n, "with_targets": with_targets, "targets": len(targets),
        f"recall_at_{k}": recall_at_k(ranked, targets, k) if targets else None,
        f"recall_at_{k}_unbudgeted": recall_at_k(top, targets, k) if targets else None,
        "all_gold_recalled": complete / with_targets if with_targets else None,
        "mean_recalled_lines": sum(len(e.recall.lines) for e in entries) / n if n else None,
        "mean_candidates": sum(e.recall.candidates for e in entries) / n if n else None,
    }


# ----------------------------------------------------------------- training rows


@dataclass
class ShardRows:
    tokens: torch.Tensor        # long [n, seq_len]
    mask: torch.Tensor          # bool [n, seq_len]: True where the token is a target
    stats: Counter = field(default_factory=Counter)


def question_row(question: Question, following: Sequence[str], lines: LineIds, bm25: Bm25, *,
                 seq_len: int = SEQ_LEN, max_len: int = CUT_MAX_LEN) -> tuple[list[int], list[bool], LookupInput]:
    """One question-centred row of exactly `seq_len` tokens and its target mask."""
    tokenizer = lines.tokenizer
    eos, pad = tokenizer.token_to_id("<eos>"), tokenizer.token_to_id("<pad>")
    entry = lookup_input(question, lines, bm25, max_len=max_len)
    tail = question_tail(tokenizer, question)
    full = tokenizer.encode(question.raw_line + "\n")
    if full[: len(tail)] != tail:
        raise AssertionError(f"{question.id}: the question line does not start with its prompt tokens")
    ids = entry.ids + full[len(tail):]
    for line in following:
        if len(ids) >= seq_len:
            break
        ids.extend(lines(line))
    else:
        ids.append(eos)
    ids = ids[:seq_len]
    real = len(ids)
    mask = [False] * entry.masked + [True] * (real - entry.masked) + [False] * (seq_len - real)
    return ids + [pad] * (seq_len - real), mask, entry


def shard_rows(text: Path, meta: Path, tokenizer: Tokenizer, bm25: Bm25, *, seed: Any, seq_len: int = SEQ_LEN,
               max_len: int = CUT_MAX_LEN, split: str = "train") -> ShardRows:
    """Question-centred rows for every question of one shard, in a shuffled order (`seed`)."""
    visits = step1.read_visits(Path(text))
    questions = step1.read_questions(Path(text), Path(meta), split)
    random.Random(str(seed)).shuffle(questions)
    lines = LineIds(tokenizer, labels=True)
    tokens = torch.empty(len(questions), seq_len, dtype=torch.long)
    mask = torch.empty(len(questions), seq_len, dtype=torch.bool)
    stats: Counter = Counter()
    for row, question in enumerate(questions):
        visit = visits[question.visit]
        following = [line for _, line in visit[len(question.context) + 1:]]
        ids, keep, entry = question_row(question, following, lines, bm25, seq_len=seq_len, max_len=max_len)
        tokens[row] = torch.tensor(ids, dtype=torch.long)
        mask[row] = torch.tensor(keep, dtype=torch.bool)
        stats["rows"] += 1
        stats["masked_prefix"] += entry.masked
        stats["pad"] += seq_len - sum(keep) - entry.masked
        stats["recalled_lines"] += len(entry.recall.lines)
        stats["recalled_tokens"] += entry.recall.tokens
        stats["with_recall"] += bool(entry.recall.lines)
        if is_far(question, entry.a_start):
            stats["far"] += 1
            stats["far_targets"] += len(entry.evidence_before)
            stats["far_hits"] += len(set(entry.evidence_before) & set(entry.recall.lines))
    return ShardRows(tokens, mask, stats)


_WORKER: dict[str, Any] = {}


def _init_rows(tokenizer_json: str, bm25: Mapping[str, Any]) -> None:
    _WORKER.update(tokenizer=Tokenizer.from_json(tokenizer_json), bm25=Bm25.from_dict(bm25))


def _rows_task(task: tuple[str, str, str, int, int]) -> tuple[bytes, bytes, dict[str, int], int]:
    text, meta, seed, seq_len, max_len = task
    rows = shard_rows(Path(text), Path(meta), _WORKER["tokenizer"], _WORKER["bm25"], seed=seed, seq_len=seq_len,
                      max_len=max_len)
    return (array("h", rows.tokens.reshape(-1).tolist()).tobytes(), bytes(rows.mask.reshape(-1).tolist()),
            dict(rows.stats), rows.tokens.shape[0])


class LookupStream:
    """C's endless training stream: (tokens, loss mask) rows of exactly `seq_len` tokens for `Trainer.train`,
    alternating a plain row of A's stream and a question-centred row (design/06 §5 step 5).

    Questions are visited shard by shard: each epoch shuffles the train shards, and each shard its
    questions. `workers` > 0 builds shards in that many spawned processes, at most `workers + 2` ahead.
    """

    def __init__(self, data: Any, bm25: Bm25, *, seed: int = 0, seq_len: int = SEQ_LEN,
                 max_len: int = CUT_MAX_LEN, workers: int = 0) -> None:
        if max_len >= seq_len:
            raise ValueError("max_len must leave room for the answer inside seq_len")
        self.tokenizer: Tokenizer = data.tokenizer
        self.bm25, self.seed, self.seq_len, self.max_len, self.workers = bm25, seed, seq_len, max_len, workers
        self.eos = self.tokenizer.token_to_id("<eos>")
        self.plain = step1.stream_for(data, chunk=1 << 16, seed=seed)
        self.shards = step1.shard_files(data.split_dir("train"))
        self.stats: Counter = Counter()
        self.question_epochs = 0
        self.build_seconds = 0.0
        self._pool: Any = None
        self._items = self._generate()

    # -- plain rows
    def _plain_rows(self) -> Iterator[tuple[torch.Tensor, torch.Tensor]]:
        size = self.seq_len - 1
        start = torch.tensor([self.eos], dtype=torch.long)
        mask = torch.ones(self.seq_len, dtype=torch.bool)
        mask[0] = False
        buffer = torch.empty(0, dtype=torch.long)
        for chunk in self.plain:
            buffer = torch.cat((buffer, chunk.long()))
            while buffer.numel() >= size:
                yield torch.cat((start, buffer[:size])), mask
                buffer = buffer[size:]

    # -- question rows
    def _tasks(self) -> Iterator[tuple[str, str, str, int, int]]:
        epoch = 0
        while True:
            order = list(self.shards)
            random.Random(f"{self.seed}:shards:{epoch}").shuffle(order)
            for text, meta in order:
                yield str(text), str(meta), f"{self.seed}:{epoch}:{text.name}", self.seq_len, self.max_len
            epoch += 1

    def _built(self) -> Iterator[tuple[ShardRows, int]]:
        tasks = self._tasks()
        if self.workers <= 0:
            for task in tasks:
                started = time.perf_counter()
                rows = shard_rows(Path(task[0]), Path(task[1]), self.tokenizer, self.bm25, seed=task[2],
                                  seq_len=self.seq_len, max_len=self.max_len)
                self.build_seconds += time.perf_counter() - started
                yield rows, int(task[2].split(":")[1])
            return
        with step1.spawn_safe_main():
            self._pool = multiprocessing.get_context("spawn").Pool(
                self.workers, _init_rows, (self.tokenizer.to_json(), self.bm25.to_dict()))
        pending: deque = deque()
        for task in tasks:
            pending.append((task, self._pool.apply_async(_rows_task, (task,))))
            if len(pending) < self.workers + 2:
                continue
            done, result = pending.popleft()
            started = time.perf_counter()
            tokens, mask, stats, count = result.get()
            self.build_seconds += time.perf_counter() - started
            shape = (count, self.seq_len)
            yield (ShardRows(torch.frombuffer(bytearray(tokens), dtype=torch.int16).long().reshape(shape),
                             torch.frombuffer(bytearray(mask), dtype=torch.bool).reshape(shape).clone(),
                             Counter(stats)), int(done[2].split(":")[1]))

    def _question_rows(self) -> Iterator[tuple[torch.Tensor, torch.Tensor]]:
        for rows, epoch in self._built():
            self.question_epochs = epoch
            self.stats.update(rows.stats)
            for index in range(rows.tokens.shape[0]):
                yield rows.tokens[index], rows.mask[index]

    def _generate(self) -> Iterator[tuple[torch.Tensor, torch.Tensor]]:
        plain, questions = self._plain_rows(), self._question_rows()
        while True:
            self.stats["plain_rows"] += 1
            yield next(plain)
            self.stats["question_rows"] += 1
            yield next(questions)

    def __iter__(self) -> LookupStream:
        return self

    def __next__(self) -> tuple[torch.Tensor, torch.Tensor]:
        return next(self._items)

    def close(self) -> None:
        if self._pool is not None:
            self._pool.terminate()
            self._pool = None

    def summary(self) -> dict[str, Any]:
        s = self.stats
        built = max(s["rows"], 1)
        return {
            "plain_rows": s["plain_rows"], "question_rows": s["question_rows"],
            "question_rows_built": s["rows"], "question_epochs": self.question_epochs,
            "plain_epochs": self.plain.epochs(self.plain.yielded),
            "mean_masked_prefix": s["masked_prefix"] / built, "pad_fraction": s["pad"] / (built * self.seq_len),
            "with_recall": s["with_recall"] / built, "mean_recalled_lines": s["recalled_lines"] / built,
            "mean_recalled_tokens": s["recalled_tokens"] / built,
            "train_far_questions": s["far"],
            "train_far_gold_recall": s["far_hits"] / s["far_targets"] if s["far_targets"] else None,
            "build_seconds": self.build_seconds, "workers": self.workers,
        }


__all__ = [
    "B", "Bm25", "K1", "LineIds", "LookupInput", "LookupStream", "RECALL_TOKENS", "Recall", "SEPARATOR", "STATS_FILE",
    "STOPWORDS", "ShardRows", "TOP_K", "Window", "candidates", "cut_window", "fit_bm25", "is_far", "label_free",
    "lookup_input", "plain_input", "query_terms", "question_row", "question_tail", "recall", "recall_report",
    "shard_rows", "shown", "split_lines", "terms", "train_bm25",
]
