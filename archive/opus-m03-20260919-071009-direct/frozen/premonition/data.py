"""Premonition-mini data (design/06 §3, §6): a pointerized visit cache built from step-1 shards, and a
length-bucketed collator that yields `premonition.batch.VisitBatch`.

The cache holds one split, entities numbered by first mention (identity order); the collator renumbers each
visit with a fresh random order when given an rng (training). Layout (one `torch.save` file, loaded with
`weights_only=True`):

  tokens            int16 [N]          every visit's lines back to back, each line encoded with its newline
                                       (`step1.encode_lines`), names as vocab_size + entity; no <eos> or <bos>
  line_offsets      int32 [lines + 1]  first token of each line (global); a visit's tokens are its lines' tokens
  visit_lines       int64 [V + 1]      first line of each visit
  line_is_question  bool  [lines]
  line_ents         int8  [lines, MAX_LINE_ENTS]  distinct entities the line mentions, in order; a question line
                                       counts only its question text (up to "[answer]"), never its answer; -1 pad
  visit_questions   int64 [V + 1]      first question of each visit (questions in stream order)
  q_line            int64 [Q]          the question's line, within its visit
  q_span            int64 [Q, 2]       [question line start, "[answer]" + 1), token positions within the visit
  answer_end        int64 [Q]          end of the answer in the stream (the "[feedback]" token, else the newline)
  answer_offsets / answer_ids          ragged pointerized answers: the stream tokens after "[answer]" without
                                       trailing whitespace pieces, then <eos>
  gold_offsets / gold                  ragged evidence lines (oracle `evidence_text_lines`), within the visit,
                                       sorted and distinct; none for a question that is not knowable
  depth int8 [Q], knowable bool [Q], question_ids [Q], visit_ids [V], names [V][entity] -> spelling, info

Every gold line is checked to be a non-question line of the same visit before the question (ShardFormatError
otherwise). Unrendered evidence (a silent record) is dropped and counted. The batch holds the newest MAX_GOLD
gold lines and the first MAX_ANSWER answer tokens; the cache keeps them whole and counts what a batch would cut.
Pass `detector=None` for the names-as-ordinary-tokens control (D-noptr).

Two cache kinds (design/06 §11.1):

- regime=None: the LEGACY v1 cache, unchanged (its files keep their old path and identity). It encodes whole
  question lines, answers and feedback included, and binds names over them; `train.label_free` then only
  drops answer tokens from batches, so names seen only in labels still enter the name table and shift the
  entity numbering. Core training streams (E) use it: their answers are LM targets.
- regime="label-free" (what D trains and is evaluated on): a v2 cache built with `premonition.preprocess`.
  Question lines are cut through "[answer]" BEFORE names are bound and anything is encoded, so the tokens,
  offsets, spans, card boundaries, entity mentions, name tables and masks are all computed on the visible
  text. `answer_end` is then one past the newline after "[answer]" (so L_lm skips "[answer]" -> newline),
  targets are bound with the visible prefix's names, and `target_unbound` [Q] flags a target naming someone
  the visible prefix never did. Its path carries the preprocessing digest: premonition-v2-<tokenizer>-<names>-
  <preprocess>/<split>.pt, so a changed rule never reuses an old file.
"""
from __future__ import annotations

from array import array
from collections import Counter
from dataclasses import dataclass, field, fields
from functools import cached_property
import io
import json
import multiprocessing
from pathlib import Path
import random
import time
from typing import Any, Callable, Iterable, Iterator, Mapping, Optional, Sequence

import torch

from learnlab import step1
from learnlab.step1 import ANSWER_TAG, FEEDBACK_TAG, QUESTION_TAG, ShardFormatError
from learnlab.tokenizer import Tokenizer

from . import preprocess
from .batch import MAX_ANSWER, MAX_GOLD, MAX_LINE_ENTS, N_ENT, PAD_ID, NameTable, VisitBatch
from .pointer import NameDetector, lowercase_words, pointerize_lines, random_order

CACHE_FORMAT = "premonition.visits"
CACHE_VERSION = 1                   # the legacy with-labels cache (regime=None)
PREPARED_CACHE_VERSION = 2          # caches built through premonition.preprocess (they record its identity)
DETECTOR_FILE = "premonition-names.json"
IGNORE = -100
Log = Callable[[str], None]


def check_tokenizer(tokenizer: Tokenizer) -> None:
    """The ids the batch contract assumes: <pad> is PAD_ID, and every entity id fits the int16 cache."""
    pad = tokenizer.token_to_id("<pad>")
    if pad != PAD_ID:
        raise ValueError(f"the tokenizer's <pad> is id {pad}, but premonition.batch.PAD_ID is {PAD_ID}")
    if tokenizer.vocab_size + N_ENT > 32767:
        raise ValueError(f"vocab {tokenizer.vocab_size} + {N_ENT} entities does not fit the int16 cache")


# ----------------------------------------------------------------- the name detector


def pattern_templates(split_dir: Path) -> list[str]:
    """The template texts the split was rendered with (its manifest names the pattern version)."""
    from learnlab.village.render import FALLBACK_VERSION, PatternSource
    from learnlab.village.stream import default_source
    manifest = Path(split_dir) / "manifest.json"
    version = json.loads(manifest.read_text(encoding="utf-8")).get("patterns") if manifest.is_file() else None
    source = default_source()
    if version is not None and version != source.version:
        if version != FALLBACK_VERSION:
            raise ValueError(f"{split_dir} was rendered with patterns {version}, but {source.version} is loaded")
        source = PatternSource.fallback()
    return list(source.text.values())


def _shard_words(text_path: str) -> set[str]:
    return lowercase_words(Path(text_path).read_text(encoding="utf-8"))


def fit_detector(train_dir: Path, *, templates: Optional[Iterable[str]] = None, workers: int = 1) -> NameDetector:
    """The name rule fitted on every train shard's text and the pattern templates (design/06 §2)."""
    texts = [str(text) for text, _ in step1.shard_files(Path(train_dir))]
    if workers > 1 and len(texts) > 1:
        with step1.spawn_safe_main():
            with multiprocessing.get_context("spawn").Pool(min(workers, len(texts))) as pool:
                found = pool.map(_shard_words, texts)
    else:
        found = [_shard_words(text) for text in texts]
    if templates is None:
        templates = pattern_templates(Path(train_dir))
    detector = NameDetector.fit((), templates)
    return NameDetector(detector.lowercase.union(*found), detector.template)


def name_detector(budget: Any, data_rel: str, *, templates: Optional[Iterable[str]] = None, workers: int = 1,
                  log: Log = print) -> NameDetector:
    """The data directory's detector: loaded from `<data_rel>/premonition-names.json`, else fitted and saved."""
    relative = f"{data_rel}/{DETECTOR_FILE}"
    path = Path(budget.root) / relative
    if path.is_file():
        return NameDetector.load(path)
    started = time.perf_counter()
    detector = fit_detector(Path(budget.root) / data_rel / "train", templates=templates, workers=workers)
    data = detector.to_json().encode("utf-8")
    budget.atomic_write(relative, len(data), lambda handle: handle.write(data))
    from learnlab.village.names import all_names
    blocked = [name for name in all_names() if not detector.is_name(name)]
    log(f"premonition names: {len(detector.lowercase):,} lowercase and {len(detector.template):,} template words "
        f"({detector.digest[:12]}) in {time.perf_counter() - started:.1f}s; pool names the rule misses: "
        f"{len(blocked)}{' (' + ', '.join(blocked[:10]) + ')' if blocked else ''}")
    return detector


# ----------------------------------------------------------------- the cache


@dataclass
class VisitCache:
    """One split's pointerized visits (see the module docstring for every field)."""

    split: str
    vocab_size: int
    tokens: torch.Tensor
    line_offsets: torch.Tensor
    visit_lines: torch.Tensor
    line_is_question: torch.Tensor
    line_ents: torch.Tensor
    visit_questions: torch.Tensor
    q_line: torch.Tensor
    q_span: torch.Tensor
    answer_end: torch.Tensor
    answer_offsets: torch.Tensor
    answer_ids: torch.Tensor
    gold_offsets: torch.Tensor
    gold: torch.Tensor
    depth: torch.Tensor
    knowable: torch.Tensor
    question_ids: list[str]
    visit_ids: list[str]
    names: list[list[str]]
    info: dict[str, Any] = field(default_factory=dict)
    target_unbound: Optional[torch.Tensor] = None   # bool [Q] (v2 caches): the target names someone unbound

    def __len__(self) -> int:
        return len(self.visit_ids)

    @property
    def regime(self) -> str:
        """The input regime of the cached tokens: a legacy v1 cache holds whole lines (with labels)."""
        return self.info.get("regime", preprocess.WITH_LABELS)

    @property
    def preprocess_identity(self) -> Optional[dict[str, Any]]:
        """`preprocess.identity` of a v2 cache; None for a legacy v1 cache."""
        return self.info.get("preprocess")

    @cached_property
    def lengths(self) -> torch.Tensor:
        """Tokens per visit."""
        starts = self.line_offsets[self.visit_lines].long()
        return starts[1:] - starts[:-1]

    @cached_property
    def line_counts(self) -> torch.Tensor:
        """Lines per visit."""
        return self.visit_lines[1:] - self.visit_lines[:-1]

    def visit_tokens(self, index: int) -> torch.Tensor:
        """Visit `index`'s pointerized tokens (identity numbering), as long."""
        first, last = int(self.visit_lines[index]), int(self.visit_lines[index + 1])
        return self.tokens[int(self.line_offsets[first]):int(self.line_offsets[last])].long()

    def questions_of(self, index: int) -> range:
        return range(int(self.visit_questions[index]), int(self.visit_questions[index + 1]))

    def answer(self, question: int) -> list[int]:
        return self.answer_ids[int(self.answer_offsets[question]):int(self.answer_offsets[question + 1])].tolist()

    def gold_lines(self, question: int) -> list[int]:
        return self.gold[int(self.gold_offsets[question]):int(self.gold_offsets[question + 1])].tolist()

    def name_table(self, index: int) -> NameTable:
        return NameTable(dict(enumerate(self.names[index])))

    def tags(self, sets: Mapping[str, Iterable[str]]) -> dict[str, torch.Tensor]:
        """Question-id sets as bool tags over this cache's questions, for `collate(..., slices=...)`."""
        position = {qid: i for i, qid in enumerate(self.question_ids)}
        out = {}
        for name, ids in sets.items():
            tag = torch.zeros(len(self.question_ids), dtype=torch.bool)
            tag[torch.tensor([position[qid] for qid in ids if qid in position], dtype=torch.long)] = True
            out[name] = tag
        return out

    def to_bytes(self) -> bytes:
        buffer = io.BytesIO()
        version = PREPARED_CACHE_VERSION if self.preprocess_identity else CACHE_VERSION
        values = {f.name: getattr(self, f.name) for f in fields(self)}
        if version == CACHE_VERSION:
            values.pop("target_unbound")            # the v1 layout, byte for byte
        torch.save({"format": CACHE_FORMAT, "version": version, **values}, buffer)
        return bytes(buffer.getbuffer())

    @classmethod
    def load(cls, path: Path) -> VisitCache:
        data = torch.load(Path(path), weights_only=True)
        found, version = data.pop("format", None), data.pop("version", None)
        if found != CACHE_FORMAT or version not in (CACHE_VERSION, PREPARED_CACHE_VERSION):
            raise ValueError(f"{path} is not a {CACHE_FORMAT} v{CACHE_VERSION}/v{PREPARED_CACHE_VERSION} file")
        cache = cls(**data)
        if version == PREPARED_CACHE_VERSION:
            problems = preprocess.identity_problems(cache.preprocess_identity)
            if problems:
                raise ValueError(f"{path}: {'; '.join(problems)}")
        elif cache.preprocess_identity is not None:
            raise ValueError(f"{path}: a v{CACHE_VERSION} file must not claim a preprocessing identity")
        return cache


_WORKER: dict[str, Any] = {}


def _init_worker(tokenizer_json: str, detector_json: Optional[str]) -> None:
    _WORKER.update(tokenizer=Tokenizer.from_json(tokenizer_json),
                   detector=None if detector_json is None else NameDetector.from_json(detector_json), cache={})


def _encode_plain(lines: Sequence[str], tokenizer: Tokenizer, cache: dict[str, list[int]]) -> list[list[int]]:
    out = []
    for line in lines:
        found = cache.get(line)
        if found is None:
            if len(cache) >= 200_000:
                cache.clear()
            found = cache[line] = tokenizer.encode(line + "\n")
        out.append(found)
    return out


def encode_shard(text: Path, meta: Path, split: str, tokenizer: Tokenizer, detector: Optional[NameDetector],
                 cache: Optional[dict[str, list[int]]] = None, regime: Optional[str] = None) -> dict[str, Any]:
    """One shard's visits and questions as plain lists (merged by `build_cache`); `regime` None is legacy v1."""
    if regime is not None:
        return _encode_prepared(text, meta, split, tokenizer, detector, {} if cache is None else cache, regime)
    cache = {} if cache is None else cache
    base = tokenizer.vocab_size
    answer_id, feedback_id, eos = (tokenizer.token_to_id(t) for t in (ANSWER_TAG, FEEDBACK_TAG, "<eos>"))
    question_id = tokenizer.token_to_id(QUESTION_TAG)
    visits = step1.read_visits(Path(text))
    rows = step1.read_records(Path(meta), "visit")
    if rows and len(rows) != len(visits):
        raise ShardFormatError(f"{Path(text).name}: {len(visits)} visits but {len(rows)} visit records")
    by_visit: dict[int, list[step1.Question]] = {}
    for question in step1.read_questions(Path(text), Path(meta), split):
        by_visit.setdefault(question.visit, []).append(question)
    stats: Counter[str] = Counter()
    out: dict[str, Any] = {key: [] for key in (
        "line_lengths", "visit_line_counts", "line_is_question", "line_ents", "visit_question_counts", "q_line",
        "q_span", "answer_end", "answers", "gold", "depth", "knowable", "question_ids", "visit_ids", "names")}
    tokens = array("h")
    for v, visit in enumerate(visits):
        first = visit[0][0]
        lines = [line for _, line in visit]
        if rows:
            row = rows[v]
            if row.get("first_line") != first or row.get("lines") != len(lines):
                raise ShardFormatError(f"{Path(text).name}: visit record {v} does not match the text")
        if detector is None:
            ids, spellings = _encode_plain(lines, tokenizer, cache), []
        else:
            ids, table = pointerize_lines(lines, tokenizer, detector, cache=cache)
            spellings = [table.spellings[e] for e in range(len(table.spellings))]
        starts = [0]
        first_seen: dict[int, int] = {}   # entity token -> its first position in the visit
        for piece in ids:
            for position, i in enumerate(piece):
                if i >= base and i not in first_seen:
                    first_seen[i] = starts[-1] + position
            starts.append(starts[-1] + len(piece))
        is_question = [line.startswith(QUESTION_TAG) for line in lines]
        spans: dict[int, int] = {}   # question line -> position of its [answer] within the line
        for k, piece in enumerate(ids):
            if is_question[k]:
                if piece[0] != question_id or answer_id not in piece:
                    raise ShardFormatError(f"{Path(text).name}:{first + k + 1}: question line without {ANSWER_TAG}")
                spans[k] = piece.index(answer_id)
            shown = piece[:spans[k] + 1] if is_question[k] else piece
            ents = list(dict.fromkeys(i - base for i in shown if i >= base))
            stats["line_ents_over_max"] += len(ents) > MAX_LINE_ENTS
            out["line_ents"].append(ents[:MAX_LINE_ENTS] + [-1] * (MAX_LINE_ENTS - len(ents[:MAX_LINE_ENTS])))
            tokens.extend(piece)
        out["line_lengths"].extend(len(piece) for piece in ids)
        out["line_is_question"].extend(is_question)
        out["visit_line_counts"].append(len(lines))
        out["visit_ids"].append(str(rows[v]["id"]) if rows else f"{Path(text).stem}/{v}")
        out["names"].append(spellings)
        stats["names_max"] = max(stats["names_max"], len(spellings))
        questions = by_visit.get(v, [])
        out["visit_question_counts"].append(len(questions))
        for question in questions:
            k = question.line - first
            if not (0 <= k < len(lines) and is_question[k]):
                raise ShardFormatError(f"{question.id}: line {question.line} is not a question line of its visit")
            piece, a = ids[k], spans[k]
            end = piece.index(feedback_id, a) if feedback_id in piece[a:] else len(piece) - 1
            answer = piece[a + 1:end]
            while answer and answer[-1] < base and not tokenizer.decode(answer[-1:]).strip():
                answer = answer[:-1]
            if not answer:
                raise ShardFormatError(f"{question.id}: empty answer in the stream")
            stats["answer_names_unseen"] += any(first_seen.get(i, 0) > starts[k] + a for i in answer if i >= base)
            stats["answers_over_max"] += len(answer) + 1 > MAX_ANSWER
            gold: list[int] = []
            for line in question.evidence:
                if line < 0:
                    stats["evidence_unrendered"] += 1
                    continue
                local = line - first
                if not (0 <= local < k) or is_question[local]:
                    raise ShardFormatError(f"{question.id}: evidence line {line} is not a card before the question")
                gold.append(local)
            gold = sorted(set(gold))
            knowable = question.knowable is not False
            if not knowable and gold:
                stats["unknowable_with_evidence"] += 1
                gold = []
            stats["knowable_without_gold"] += knowable and not gold
            stats["gold_over_max"] += len(gold) > MAX_GOLD
            stats["gold_max"] = max(stats["gold_max"], len(gold))
            stats["answer_max"] = max(stats["answer_max"], len(answer) + 1)
            stats["question_max"] = max(stats["question_max"], a + 1)
            out["q_line"].append(k)
            out["q_span"].append((starts[k], starts[k] + a + 1))
            out["answer_end"].append(starts[k] + end)
            out["answers"].append(answer + [eos])
            out["gold"].append(gold)
            out["depth"].append(int(question.depth or 0) if knowable else 0)
            out["knowable"].append(knowable)
            out["question_ids"].append(question.id)
        stats["visit_tokens_max"] = max(stats["visit_tokens_max"], starts[-1])
    if sum(out["visit_question_counts"]) != sum(len(qs) for qs in by_visit.values()):
        raise ShardFormatError(f"{Path(text).name}: questions outside every visit")
    out["tokens"] = tokens.tobytes()
    out["stats"] = dict(stats)
    return out


def _shard_questions(text: Path, meta: Path, split: str) -> tuple[list[list[tuple[int, str]]], list[dict[str, Any]],
                                                                   dict[int, list[step1.Question]]]:
    visits = step1.read_visits(Path(text))
    rows = step1.read_records(Path(meta), "visit")
    if rows and len(rows) != len(visits):
        raise ShardFormatError(f"{Path(text).name}: {len(visits)} visits but {len(rows)} visit records")
    by_visit: dict[int, list[step1.Question]] = {}
    for question in step1.read_questions(Path(text), Path(meta), split):
        by_visit.setdefault(question.visit, []).append(question)
    return visits, rows, by_visit


def _encode_prepared(text: Path, meta: Path, split: str, tokenizer: Tokenizer, detector: Optional[NameDetector],
                     cache: dict[str, list[int]], regime: str) -> dict[str, Any]:
    """`encode_shard` for a v2 cache: every line through `preprocess.prepare_visit` (see the module doc)."""
    preprocess.check_regime(regime)
    base = tokenizer.vocab_size
    answer_id, feedback_id = tokenizer.token_to_id(ANSWER_TAG), tokenizer.token_to_id(FEEDBACK_TAG)
    visits, rows, by_visit = _shard_questions(text, meta, split)
    stats: Counter[str] = Counter()
    out: dict[str, Any] = {key: [] for key in (
        "line_lengths", "visit_line_counts", "line_is_question", "line_ents", "visit_question_counts", "q_line",
        "q_span", "answer_end", "answers", "gold", "depth", "knowable", "question_ids", "visit_ids", "names",
        "target_unbound")}
    tokens = array("h")
    for v, visit in enumerate(visits):
        first = visit[0][0]
        lines = [line for _, line in visit]
        if rows:
            row = rows[v]
            if row.get("first_line") != first or row.get("lines") != len(lines):
                raise ShardFormatError(f"{Path(text).name}: visit record {v} does not match the text")
        try:
            prepared = preprocess.prepare_visit(lines, tokenizer, detector, regime=regime, cache=cache)
        except (preprocess.MalformedInput, preprocess.MalformedTarget) as error:
            raise ShardFormatError(f"{Path(text).name}: visit {v}: {error}") from None
        ids, starts = prepared.pieces, prepared.starts
        spellings = [prepared.table.spellings[e] for e in range(len(prepared.table.spellings))]
        is_question = [line.startswith(QUESTION_TAG) for line in lines]
        for k, piece in enumerate(ids):
            shown = piece[:prepared.questions[k].span[1] - starts[k]] if is_question[k] else piece
            ents = list(dict.fromkeys(i - base for i in shown if i >= base))
            stats["line_ents_over_max"] += len(ents) > MAX_LINE_ENTS
            out["line_ents"].append(ents[:MAX_LINE_ENTS] + [-1] * (MAX_LINE_ENTS - len(ents[:MAX_LINE_ENTS])))
            tokens.extend(piece)
        out["line_lengths"].extend(len(piece) for piece in ids)
        out["line_is_question"].extend(is_question)
        out["visit_line_counts"].append(len(lines))
        out["visit_ids"].append(str(rows[v]["id"]) if rows else f"{Path(text).stem}/{v}")
        out["names"].append(spellings)
        stats["names_max"] = max(stats["names_max"], len(spellings))
        stats["label_only_names"] += len(prepared.label_only_names)
        stats["visits_with_label_only_names"] += bool(prepared.label_only_names)
        questions = by_visit.get(v, [])
        out["visit_question_counts"].append(len(questions))
        for question in questions:
            k = question.line - first
            if not (0 <= k < len(lines) and is_question[k]):
                raise ShardFormatError(f"{question.id}: line {question.line} is not a question line of its visit")
            asked = prepared.questions[k]
            start, end = asked.span
            if regime == preprocess.WITH_LABELS:
                piece, a = ids[k], end - 1 - starts[k]
                stop = starts[k] + (piece.index(feedback_id, a) if feedback_id in piece[a:] else len(piece) - 1)
            else:
                stop = end + 1                      # mask only "[answer]" -> newline
            gold: list[int] = []
            for line in question.evidence:
                if line < 0:
                    stats["evidence_unrendered"] += 1
                    continue
                local = line - first
                if not (0 <= local < k) or is_question[local]:
                    raise ShardFormatError(f"{question.id}: evidence line {line} is not a card before the question")
                gold.append(local)
            gold = sorted(set(gold))
            knowable = question.knowable is not False
            if not knowable and gold:
                stats["unknowable_with_evidence"] += 1
                gold = []
            stats["knowable_without_gold"] += knowable and not gold
            stats["gold_over_max"] += len(gold) > MAX_GOLD
            stats["gold_max"] = max(stats["gold_max"], len(gold))
            stats["answer_max"] = max(stats["answer_max"], len(asked.target))
            stats["question_max"] = max(stats["question_max"], end - start)
            stats["answers_over_max"] += len(asked.target) > MAX_ANSWER
            stats["target_names_unbound"] += bool(asked.unbound)
            if ids[k][end - 1 - starts[k]] != answer_id:
                raise ShardFormatError(f"{question.id}: its span does not end at {ANSWER_TAG}")
            out["q_line"].append(k)
            out["q_span"].append((start, end))
            out["answer_end"].append(stop)
            out["answers"].append(list(asked.target))
            out["target_unbound"].append(bool(asked.unbound))
            out["gold"].append(gold)
            out["depth"].append(int(question.depth or 0) if knowable else 0)
            out["knowable"].append(knowable)
            out["question_ids"].append(question.id)
        stats["visit_tokens_max"] = max(stats["visit_tokens_max"], starts[-1])
    if sum(out["visit_question_counts"]) != sum(len(qs) for qs in by_visit.values()):
        raise ShardFormatError(f"{Path(text).name}: questions outside every visit")
    out["tokens"] = tokens.tobytes()
    out["stats"] = dict(stats)
    return out


def _encode_task(task: tuple[str, str, str, Optional[str]]) -> dict[str, Any]:
    text, meta, split, regime = task
    return encode_shard(Path(text), Path(meta), split, _WORKER["tokenizer"], _WORKER["detector"], _WORKER["cache"],
                        regime=regime)


def _offsets(counts: Iterable[int], dtype: torch.dtype = torch.long) -> torch.Tensor:
    return torch.cumsum(torch.tensor([0, *counts], dtype=torch.long), 0).to(dtype)


def _ragged(rows: Sequence[Sequence[int]], dtype: torch.dtype) -> tuple[torch.Tensor, torch.Tensor]:
    return _offsets(len(r) for r in rows), torch.tensor([x for r in rows for x in r], dtype=dtype)


def build_cache(split_dir: Path, tokenizer: Tokenizer, detector: Optional[NameDetector], *,
                split: Optional[str] = None, workers: int = 1, regime: Optional[str] = None) -> VisitCache:
    """Encode every shard of `split_dir` (split: the directory name before any "-suffix", unless given).

    `regime` None builds the legacy v1 cache (whole lines); a regime builds a v2 cache through
    `premonition.preprocess` ("label-free" for D).
    """
    check_tokenizer(tokenizer)
    if regime is not None:
        preprocess.check_regime(regime)
    split_dir = Path(split_dir)
    split = split or split_dir.name.split("-")[0]
    pairs = step1.shard_files(split_dir)
    tasks = [(str(text), str(meta), split, regime) for text, meta in pairs]
    payload = (tokenizer.to_json(), None if detector is None else detector.to_json())
    if workers > 1 and len(tasks) > 1:
        with step1.spawn_safe_main():
            context = multiprocessing.get_context("spawn")
            with context.Pool(min(workers, len(tasks)), _init_worker, payload) as pool:
                parts = pool.map(_encode_task, tasks)
    else:
        _init_worker(*payload)
        parts = [_encode_task(task) for task in tasks]
    merged: dict[str, list] = {}
    for part in parts:
        for key, value in part.items():
            if key not in ("tokens", "stats"):
                merged.setdefault(key, []).extend(value)
    unbound = merged.pop("target_unbound", None)
    tokens = torch.frombuffer(bytearray(b"".join(part["tokens"] for part in parts)) or bytearray(2),
                              dtype=torch.int16)[: sum(merged["line_lengths"])].clone()
    stats: Counter[str] = Counter()
    for part in parts:
        for key, value in part["stats"].items():
            stats[key] = max(stats[key], value) if key.endswith("_max") else stats[key] + value
    answer_offsets, answer_ids = _ragged(merged["answers"], torch.int16)
    gold_offsets, gold = _ragged(merged["gold"], torch.int16)
    line_ents = torch.tensor(merged["line_ents"], dtype=torch.int8).reshape(-1, MAX_LINE_ENTS)
    cache = VisitCache(
        split=split, vocab_size=tokenizer.vocab_size, tokens=tokens,
        line_offsets=_offsets(merged["line_lengths"], torch.int32),
        visit_lines=_offsets(merged["visit_line_counts"]),
        line_is_question=torch.tensor(merged["line_is_question"], dtype=torch.bool),
        line_ents=line_ents, visit_questions=_offsets(merged["visit_question_counts"]),
        q_line=torch.tensor(merged["q_line"], dtype=torch.long),
        q_span=torch.tensor(merged["q_span"], dtype=torch.long).reshape(-1, 2),
        answer_end=torch.tensor(merged["answer_end"], dtype=torch.long),
        answer_offsets=answer_offsets, answer_ids=answer_ids, gold_offsets=gold_offsets, gold=gold,
        depth=torch.tensor(merged["depth"], dtype=torch.int8),
        knowable=torch.tensor(merged["knowable"], dtype=torch.bool),
        question_ids=merged["question_ids"], visit_ids=merged["visit_ids"], names=merged["names"],
        info={"source": str(split_dir), "shards": [text.name for text, _ in pairs],
              "tokenizer_sha256": tokenizer.digest,
              "detector_sha256": None if detector is None else detector.digest, "pointers": detector is not None,
              "visits": len(merged["visit_ids"]), "questions": len(merged["question_ids"]),
              "tokens": int(tokens.numel()), "stats": dict(stats),
              **({} if regime is None else {"regime": regime, "preprocess": preprocess.identity(regime)})},
        target_unbound=None if regime is None else torch.tensor(unbound or [], dtype=torch.bool),
    )
    return cache


def cache_relative(data_rel: str, name: str, tokenizer: Tokenizer, detector: Optional[NameDetector],
                   regime: Optional[str] = None) -> str:
    """Where a cache lives. Legacy v1 (regime None): premonition-v1-<tokenizer>-<names>/<name>.pt, as before.
    v2: premonition-v2-<tokenizer>-<names>-<preprocessing digest>/<name>.pt."""
    names = "plain" if detector is None else detector.digest[:12]
    if regime is None:
        return f"{data_rel}/premonition-v{CACHE_VERSION}-{tokenizer.digest[:12]}-{names}/{name}.pt"
    return (f"{data_rel}/premonition-v{PREPARED_CACHE_VERSION}-{tokenizer.digest[:12]}-{names}-"
            f"{preprocess.digest(regime)[:12]}/{name}.pt")


def load_or_build(budget: Any, data_rel: str, name: str, tokenizer: Tokenizer, detector: Optional[NameDetector], *,
                  split: Optional[str] = None, workers: int = 1, regime: Optional[str] = None,
                  log: Log = print) -> VisitCache:
    """The cache of `<data_rel>/<name>/`: loaded when written before, else built and written through the budget.

    `regime` None is the legacy v1 cache; "label-free" the v2 cache D reads (see the module doc).
    """
    relative = cache_relative(data_rel, name, tokenizer, detector, regime)
    path = Path(budget.root) / relative
    if path.is_file():
        cache = VisitCache.load(path)
        if regime is not None and (cache.preprocess_identity or {}).get("regime") != regime:
            raise ValueError(f"{relative} holds a {cache.regime} cache, not {regime}")
        return cache
    started = time.perf_counter()
    cache = build_cache(Path(budget.root) / data_rel / name, tokenizer, detector, split=split, workers=workers,
                        regime=regime)
    data = cache.to_bytes()
    budget.atomic_write(relative, len(data), lambda handle: handle.write(data))
    stats = cache.info["stats"]
    log(f"premonition cache {name} [{regime or 'legacy v1'}]: {len(cache):,} visits, "
        f"{cache.info['questions']:,} questions, "
        f"{cache.info['tokens']:,} tokens in {time.perf_counter() - started:.1f}s; stats {json.dumps(stats)}")
    if stats.get("gold_over_max") or stats.get("answers_over_max"):
        log(f"premonition cache {name}: WARNING {stats.get('gold_over_max', 0)} questions have more than "
            f"{MAX_GOLD} gold lines (a batch keeps the newest) and {stats.get('answers_over_max', 0)} answers "
            f"exceed {MAX_ANSWER} tokens (a batch cuts them)")
    return cache


# ----------------------------------------------------------------- batches


def collate(cache: VisitCache, visits: Sequence[int], *, rng: Optional[random.Random] = None,
            slices: Optional[Mapping[str, torch.Tensor]] = None) -> VisitBatch:
    """The `VisitBatch` of cache visits `visits`, in that order; with `rng`, each visit gets a fresh entity order.

    `slices` are bool tags over the cache's questions (`VisitCache.tags`); the batch carries its questions' rows.
    """
    base = cache.vocab_size
    count = len(visits)
    if count == 0:
        raise ValueError("an empty batch")
    chosen = torch.tensor(list(visits), dtype=torch.long)
    lengths, line_counts = cache.lengths[chosen], cache.line_counts[chosen]
    width, height = int(lengths.max()), int(line_counts.max())
    tokens = torch.full((count, width), PAD_ID, dtype=torch.long)
    line_of = torch.full((count, width), -1, dtype=torch.long)
    card_end = torch.zeros((count, width), dtype=torch.bool)
    lm_mask = torch.zeros((count, width), dtype=torch.bool)
    line_is_question = torch.zeros((count, height), dtype=torch.bool)
    line_start = torch.full((count, height), -1, dtype=torch.long)
    line_ents = torch.full((count, height, MAX_LINE_ENTS), -1, dtype=torch.long)
    lookup = torch.arange(base + N_ENT)
    q_rows: list[int] = []
    q_visit: list[int] = []
    answers: list[list[int]] = []
    names: list[NameTable] = []
    for row, index in enumerate(visits):
        first, last = int(cache.visit_lines[index]), int(cache.visit_lines[index + 1])
        offsets = cache.line_offsets[first:last + 1].long()
        offsets = offsets - offsets[0]
        size, lines = int(offsets[-1]), last - first
        order = random_order(rng) if rng is not None else list(range(N_ENT))
        lookup[base:] = base + torch.tensor(order)
        entity = torch.tensor(order + [-1])   # entity -1 (padding) stays -1
        tokens[row, :size] = lookup[cache.visit_tokens(index)]
        line_of[row, :size] = torch.repeat_interleave(torch.arange(lines), offsets[1:] - offsets[:-1])
        questions = cache.line_is_question[first:last]
        line_is_question[row, :lines] = questions
        line_start[row, :lines] = offsets[:-1]
        line_ents[row, :lines] = entity[cache.line_ents[first:last].long()]
        card_end[row, (offsets[1:] - 1)[~questions]] = True
        lm_mask[row, :size - 1] = True
        for q in cache.questions_of(index):
            end, stop = int(cache.q_span[q, 1]), int(cache.answer_end[q])
            lm_mask[row, end - 1:stop - 1] = False       # positions whose next token is part of the answer
            q_rows.append(q)
            q_visit.append(row)
            answers.append(lookup[torch.tensor(cache.answer(q), dtype=torch.long)].tolist())
        names.append(NameTable({order[e]: spelling for e, spelling in enumerate(cache.names[index])}))
    answer = torch.full((len(q_rows), MAX_ANSWER), IGNORE, dtype=torch.long)
    gold_lines = torch.full((len(q_rows), MAX_GOLD), -1, dtype=torch.long)
    for i, (q, ids) in enumerate(zip(q_rows, answers)):
        ids = ids[:MAX_ANSWER]
        answer[i, :len(ids)] = torch.tensor(ids, dtype=torch.long)
        gold = cache.gold_lines(q)[-MAX_GOLD:]   # the newest when there are more
        gold_lines[i, :len(gold)] = torch.tensor(gold, dtype=torch.long)
    index = torch.tensor(q_rows, dtype=torch.long)
    return VisitBatch(
        tokens=tokens, line_of=line_of, card_end=card_end, lengths=lengths.long(), lm_mask=lm_mask,
        line_is_question=line_is_question, line_start=line_start, line_ents=line_ents,
        q_visit=torch.tensor(q_visit, dtype=torch.long), q_line=cache.q_line[index].clone(),
        q_span=cache.q_span[index].clone().reshape(-1, 2), answer=answer, gold_lines=gold_lines,
        depth=cache.depth[index].long(), question_ids=[cache.question_ids[q] for q in q_rows], names=names,
        slices=None if slices is None else {name: tag[index].clone() for name, tag in slices.items()},
    )


def length_batches(lengths: Sequence[int], max_tokens: int, *, rng: Optional[random.Random] = None,
                   pool: Optional[int] = 64, max_visits: Optional[int] = None) -> list[list[int]]:
    """Visit indices grouped so that visits x longest visit <= max_tokens (a longer visit goes alone).

    Without `rng`: one pass sorted by length. With `rng`: shuffled, sorted by length within pools of about
    `pool` batches, and the batches shuffled, so each epoch groups visits afresh.
    """
    if max_tokens < 1:
        raise ValueError("max_tokens must be positive")
    order = list(range(len(lengths)))
    if rng is None:
        pools = [order]
    else:
        rng.shuffle(order)
        mean = max(1, sum(lengths) // max(1, len(lengths)))
        size = len(order) if pool is None else max(1, pool * max(1, max_tokens // mean))
        pools = [order[start:start + size] for start in range(0, len(order), size)]
    batches: list[list[int]] = []
    for part in pools:
        batch: list[int] = []
        longest = 0
        for index in sorted(part, key=lambda i: lengths[i]):
            wider = max(longest, lengths[index])
            if batch and (wider * (len(batch) + 1) > max_tokens or (max_visits and len(batch) >= max_visits)):
                batches.append(batch)
                batch, wider = [], lengths[index]
            batch.append(index)
            longest = wider
        if batch:
            batches.append(batch)
    if rng is not None:
        rng.shuffle(batches)
    return batches


def batches(cache: VisitCache, max_tokens: int, *, seed: Optional[int] = None, epochs: Optional[int] = 1,
            permute: bool = True, max_visits: Optional[int] = None,
            slices: Optional[Mapping[str, torch.Tensor]] = None) -> Iterator[VisitBatch]:
    """Length-bucketed `VisitBatch`es over the cache.

    `seed=None`: one deterministic pass (evaluation), identity entity numbering. With a seed: `epochs` shuffled
    epochs (None = endless), each visit renumbered by a fresh random entity order when `permute`.
    """
    lengths = cache.lengths.tolist()
    if seed is None:
        for group in length_batches(lengths, max_tokens, max_visits=max_visits):
            yield collate(cache, group, slices=slices)
        return
    rng = random.Random(seed)
    epoch = 0
    while epochs is None or epoch < epochs:
        for group in length_batches(lengths, max_tokens, rng=rng, max_visits=max_visits):
            yield collate(cache, group, rng=rng if permute else None, slices=slices)
        epoch += 1


__all__ = [
    "CACHE_FORMAT", "CACHE_VERSION", "PREPARED_CACHE_VERSION", "VisitCache", "batches", "build_cache",
    "cache_relative", "check_tokenizer",
    "collate", "encode_shard", "fit_detector", "length_batches", "load_or_build", "name_detector",
    "pattern_templates",
]
