"""Step 1 (childhood): village data, tokenizer, token stream, read-only QA evaluation and the gate.

Pipeline (design/04 row 1; design/05 sections 5-7):

1. Data. `learnlab.village.shards.write_shards` writes train/validation/test
   shards (stream text plus one JSONL record per question) under
   `data/village/stream/cache/<tag>/<split>/`. The tokenizer (vocab 8000) is
   trained on TRAIN-split text plus the teacher-written simple English only,
   and saved once to `data/tokenizer/premonition-tok-v2.json`. Train shards are
   encoded to uint16 token files with `<eos>` after every visit. The first
   visits of the first train shard form the forgetting probe: they are
   trained exactly once, at the very start, and never revisited.
   (The stream cache sits in a directory named `cache` on purpose: the BensPC
   sync skips such directories, so the remote builds its own shards from the
   same deterministic simulator while the small tokenizer file is synced.)
2. Stream. `TokenStream` feeds pre-encoded train tokens to `Trainer`, cycling
   reshuffled epochs over the non-probe files and timing its own stalls.
3. Evaluation, always through `Trainer.evaluate` (read-only). A question's
   input is the visit text before it, cut from the left at whole lines to fit
   the context, then `[question] <q> [answer]`; the model greedily decodes
   until a special token (such as `[feedback]`), a newline or `max_new`
   tokens. Scoring is exact match after `leaks.normalize`; a plan (Q12) also
   counts when the oracle's `check_plan` can act it out (design/05 5b). The
   oracle index (built with the data by replaying the deterministic village)
   supplies each question's world and its (bank, slots) identity, so an input
   that already shows the same question answered earlier in the visit is
   found exactly; such repeats are reported and never gated.
4. Gate: every criterion of design/04 row 1 as PASS / FAIL / INSUFFICIENT,
   deciding on one-sided 99% Wilson bounds and never passing on small n.

On BensPC (scripts/remote_benspc.sh; every argument fits its whitelist):
  sh scripts/remote_benspc.sh sync      # code, patterns and data/tokenizer/ (not the stream cache)
  sh scripts/remote_benspc.sh launch step1 --build-only --visits=medium --workers=11
  sh scripts/remote_benspc.sh launch step1 --size=4M --device=cuda --seconds=600 --visits=medium
  sh scripts/remote_benspc.sh status RUN_ID ; sh scripts/remote_benspc.sh fetch RUN_ID
The remote builds its own shards (the simulator is deterministic in its seed);
fit the tokenizer locally first so both machines share one digest.
"""
from __future__ import annotations

from array import array
from collections import Counter, defaultdict
import contextlib
from dataclasses import asdict, dataclass, field, replace
import hashlib
import inspect
import json
import math
import multiprocessing
import os
from pathlib import Path
import pickle
import random
import re
import sys
import time
from typing import Any, Callable, Iterable, Iterator, Mapping, Optional, Sequence

import torch
import torch.nn.functional as F
from torch import nn

from learnlab.core import SIZES, Core, CoreConfig, lm_loss
from learnlab.leaks import QAExample, example_presence_chance, normalize
from learnlab.metrics import binomial_greater, wilson_interval
from learnlab.policy import ALPHA, MIN_ITEMS
from learnlab.tokenizer import Tokenizer
from learnlab.train import MemoryGuardError, TrainConfig, Trainer

MODEL_NAME = "premonition"
# v2 splits made-up names into their syllables. v1 files predate that: the train
# names they saw became whole-word tokens while fresh names shatter into rare
# pieces, so `build_tokenizer` refuses them (and leaves them on disk).
TOKENIZER_NAME = "premonition-tok-v2"
TOKENIZER_PATH = "data/tokenizer/premonition-tok-v2.json"
TOKENIZER_MANIFEST = "data/tokenizer/premonition-tok-v2.manifest.json"
# Until the verified pattern bank (data/village/patterns/bank-v1.json) exists the
# village renders hand-written fallback patterns; a tokenizer fitted on those is
# provisional and kept apart, so v2 is only ever fitted on the real bank.
PROVISIONAL_TOKENIZER_PATH = "data/tokenizer/premonition-tok-v2-fallback.json"
PROVISIONAL_TOKENIZER_MANIFEST = "data/tokenizer/premonition-tok-v2-fallback.manifest.json"
FALLBACK_PATTERNS_PREFIX = "village-fallback"
STREAM_ROOT = "data/village/stream/cache"
ENGLISH_GLOB = "data/english/raw/*.jsonl"
VOCAB_SIZE = 8000
TOKENIZER_CHAR_CAP = 60_000_000     # train-split village characters used to fit the tokenizer
NAME_PIECE_GAP = 0.5                # largest train vs held-out gap in mean pieces per name (name_token_audit)
SPLITS = ("train", "validation", "test")
HELDOUT = ("validation", "test")
GATE_ACCURACY = 0.90
WORLD_BOTTLENECK = 0.05
MAX_SECONDS = 4 * 3600   # longest Step 1 run (rented GPUs; the old 600 s cap was for BensPC pilots)
LEAK_COVERAGE = 0.9   # a clean leak verdict needs classes big enough to test holding this share of the items
MIN_NAME_ITEMS = 30
# --visits presets: (train visits, validation visits = test visits)
VISIT_PRESETS = {
    "tiny": (60, 24),
    "small": (2_000, 300),
    "medium": (20_000, 600),
    "large": (100_000, 1_000),
}
TEST_SIZES = {"tiny": (32, 2, 2)}   # d_model, layers, heads; unit tests only
DEFAULT_LR = {"4M": 1e-3, "28M": 6e-4, "90M": 3e-4, "tiny": 3e-3}
QUESTION_TAG, ANSWER_TAG, FEEDBACK_TAG = "[question]", "[answer]", "[feedback]"
_NOT_NAMES = frozenset({
    "yes", "no", "nobody", "nothing", "north", "south", "east", "west", "morning", "noon",
    "evening", "night", "right", "wrong", "none",
})
_NAME_LIKE = re.compile(r"^[A-Z][a-z'\-]+$")

Writer = Callable[..., Any]
Log = Callable[[str], None]


class ShardFormatError(ValueError):
    """Shard text and metadata do not follow the village record/stream contract."""


# ----------------------------------------------------------------- shards


@dataclass(frozen=True)
class Question:
    """One question record joined with the stream text it was asked in."""

    id: str
    split: str
    shard: str
    visit: int                          # visit index within the shard
    line: int                           # 0-based line number of the question in the shard text
    raw_line: str                       # the full "[question] ... [answer] ... [feedback] ..." line
    question: str
    answer: str                         # canonical answer from the record
    context: tuple[tuple[int, str], ...]  # (line number, text) of the visit lines before it
    qtype: str
    depth: Optional[int]
    visible: bool
    knowable: Optional[bool]
    twin: Optional[str]
    templates: tuple[str, ...]
    style: Optional[str]
    rule_families: tuple[str, ...]
    evidence: tuple[int, ...]
    bank: Optional[str]
    # What makes two askings "the same question": the scheduler's (bank, slots)
    # from the oracle index when there is one, else the normalised question text.
    signature: Optional[str] = None
    earlier: tuple[tuple[int, str], ...] = ()   # (line, answer) of earlier askings in the visit
    action: Optional[str] = None                # a hypothetical's action bank ("ev.open"), else None

    @property
    def prompt_line(self) -> str:
        """The question line cut just after "[answer]": nothing of the answer remains."""
        return self.raw_line[: self.raw_line.index(ANSWER_TAG) + len(ANSWER_TAG)]


def _get(record: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if record.get(name) is not None:
            return record[name]
    return default


def _strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(str(item) for item in value)
    return (str(value),)


def family_ids(values: Iterable[str], *, derivation: bool = True) -> tuple[str, ...]:
    """Rule families without the split suffix the registry adds ("R1:train" -> "R1").

    A question whose derivation combines two or more different families is
    an R9 chain (design/05 section 3; the scheduler's "R9-style" questions),
    so it also carries "R9". A visit's provenance is not a derivation.
    """
    families = tuple(dict.fromkeys(str(value).split(":")[0] for value in values if str(value)))
    if derivation and len(set(families) - {"R9"}) >= 2 and "R9" not in families:
        families += ("R9",)
    return families


def _visible(record: Mapping[str, Any]) -> bool:
    value = record.get("visible")
    if isinstance(value, bool):
        return value
    kind = _get(record, "visibility", "range", "reach", "horizon")
    if isinstance(kind, str):
        return kind.strip().lower() == "visible"
    long_range = record.get("long_range")
    if isinstance(long_range, bool):
        return not long_range
    raise ShardFormatError(f"record {record.get('id')!r} has no visible/long_range tag")


def parse_question_line(line: str) -> tuple[str, str, str]:
    """(question, answer, feedback) of a "[question] q [answer] a [feedback] f" stream line."""
    if not line.startswith(QUESTION_TAG) or ANSWER_TAG not in line:
        raise ShardFormatError(f"not a question line: {line[:80]!r}")
    body = line[len(QUESTION_TAG):]
    question, _, rest = body.partition(ANSWER_TAG)
    answer, _, feedback = rest.partition(FEEDBACK_TAG)
    return question.strip(), answer.strip(), feedback.strip()


def read_visits(path: Path) -> list[list[tuple[int, str]]]:
    """Visits of a shard text file: runs of non-blank lines, as (0-based line number, text)."""
    visits: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").split("\n")):
        line = raw.rstrip("\r")
        if line.strip():
            current.append((number, line))
        elif current:
            visits.append(current)
            current = []
    if current:
        visits.append(current)
    return visits


def read_records(path: Path, kind: str = "question") -> list[dict[str, Any]]:
    """The records of one kind in a shard's JSONL, in order (rows without a kind are questions)."""
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if line.strip():
            try:
                record = json.loads(line)
            except ValueError as error:
                raise ShardFormatError(f"{path.name}:{number + 1}: bad JSON: {error}") from None
            if not isinstance(record, dict):
                raise ShardFormatError(f"{path.name}:{number + 1}: not a JSON object")
            if record.get("kind", "question") == kind:
                records.append(record)
    return records


def shard_files(split_dir: Path) -> list[tuple[Path, Path]]:
    """(text, metadata) pairs of a split directory, sorted by name.

    A text file `x.txt` pairs with the one `.jsonl` file in the same directory
    whose name starts with `x.` or `x-` or `x_` (x.jsonl, x.meta.jsonl, ...).
    """
    pairs = []
    for text in sorted(split_dir.rglob("*.txt")):
        metas = [
            meta for meta in text.parent.glob(f"{text.stem}*.jsonl")
            if meta.name[len(text.stem):len(text.stem) + 1] in (".", "-", "_")
        ]
        if len(metas) != 1:
            raise ShardFormatError(f"{text}: expected one metadata .jsonl, found {len(metas)}")
        pairs.append((text, metas[0]))
    if not pairs:
        raise ShardFormatError(f"no shard text files in {split_dir}")
    return pairs


def read_questions(text: Path, meta: Path, split: str,
                   signatures: Optional[Mapping[str, str]] = None) -> list[Question]:
    """Join a shard's question records, in order, with its "[question]" lines.

    The i-th record belongs to the i-th question line. The record's answer must
    match the answer written in the line after normalisation, and its split
    (when given) must be `split`; anything else is a contract violation.
    `signatures` (question id -> the scheduler's bank and slots, from the
    oracle index) identify repeated askings of one question in a visit; a
    question without one falls back to its normalised text, which misses a
    repeat worded differently or wrapped by the teacher.
    """
    visits = read_visits(text)
    records = read_records(meta)
    places = [(v, k) for v, visit in enumerate(visits)
              for k, (_, line) in enumerate(visit) if line.startswith(QUESTION_TAG)]
    if len(places) != len(records):
        raise ShardFormatError(
            f"{text.name}: {len(places)} question lines but {len(records)} records in {meta.name}")
    questions = []
    for index, ((v, k), record) in enumerate(zip(places, records)):
        number, line = visits[v][k]
        asked, written, _ = parse_question_line(line)
        answer = str(_get(record, "answer", "canonical_answer", default=written))
        if normalize(answer) != normalize(written):
            raise ShardFormatError(
                f"{text.name}:{number + 1}: record answer {answer!r} != stream answer {written!r}")
        record_split = record.get("split")
        if record_split is not None and record_split != split:
            raise ShardFormatError(f"{text.name}: record split {record_split!r} in the {split} split")
        # Line numbers may be shard-file indices or visit-relative ones; `text_line`
        # (when present) tells which, and must point at this very line.
        offset = 0
        stated = record.get("text_line")
        if isinstance(stated, int) and not isinstance(stated, bool):
            if stated == number:
                offset = 0
            elif stated == k:
                offset = visits[v][0][0]
            else:
                raise ShardFormatError(
                    f"{text.name}:{number + 1}: record text_line {stated} is not this question line")
        if "evidence_text_lines" in record:
            raw_evidence = record.get("evidence_text_lines") or []
        else:
            raw_evidence = _get(record, "evidence_lines", "evidence", default=[])
        evidence = tuple(-1 if not isinstance(e, int) or isinstance(e, bool) else e + offset
                         for e in (raw_evidence if isinstance(raw_evidence, list) else [raw_evidence]))
        templates = tuple(dict.fromkeys(
            _strings(record.get("template")) + _strings(_get(record, "templates", "template_ids"))
            + _strings(record.get("evidence_templates"))))
        depth = record.get("depth")
        knowable = record.get("knowable")
        twin = _get(record, "twin", "twin_id", "pair", "pair_id")
        bank = record.get("bank")
        style = _get(record, "style", "teacher_style")
        questions.append(Question(
            id=str(_get(record, "id", "qid", default=f"{split}/{text.stem}/{index}")),
            split=split, shard=text.stem, visit=v, line=number, raw_line=line,
            question=asked, answer=answer, context=tuple(visits[v][:k]),
            qtype=str(_get(record, "qtype", "type", "question_type", default="?")),
            depth=int(depth) if isinstance(depth, (int, float)) and not isinstance(depth, bool) else None,
            visible=_visible(record),
            knowable=knowable if isinstance(knowable, bool) else None,
            twin=None if twin is None else str(twin),
            templates=templates,
            style=None if style is None else str(style),
            rule_families=family_ids(_strings(_get(record, "rule_families", "families", "rule_family"))),
            evidence=evidence,
            bank=None if bank is None else str(bank),
            action=None if not record.get("action") else str(record["action"]),
        ))
    asked: dict[tuple[int, str], list[tuple[int, str]]] = defaultdict(list)
    marked = []
    for question in questions:
        signature = (signatures or {}).get(question.id) or "text:" + normalize(question.question)
        before = asked[question.visit, signature]
        marked.append(replace(question, signature=signature, earlier=tuple(before)))
        before.append((question.line, question.answer))
    return marked


def summarize_split(split_dir: Path, split: str) -> dict[str, Any]:
    """Counts and the seen template/style/family sets of one generated split (validates it)."""
    visits = questions = visible = 0
    text_bytes = 0
    qtypes: Counter[str] = Counter()
    depths: Counter[str] = Counter()
    templates: set[str] = set()
    styles: set[str] = set()
    families: set[str] = set()
    banks: set[str] = set()
    names: set[str] = set()
    shards = []
    for text, meta in shard_files(split_dir):
        # Visit provenance lists every template, style, family and name the text used.
        for row in read_records(meta, "visit"):
            provenance = row.get("provenance") or {}
            templates.update(_strings(provenance.get("template")))
            styles.update(_strings(provenance.get("teacher_style")))
            families.update(family_ids(_strings(provenance.get("rule_family")), derivation=False))
            names.update(_strings(provenance.get("name")))
        items = read_questions(text, meta, split)
        shard_visits = len(read_visits(text))
        visits += shard_visits
        questions += len(items)
        visible += sum(item.visible for item in items)
        for item in items:
            qtypes[item.qtype] += 1
            depths[str(item.depth)] += 1
            templates.update(item.templates)
            families.update(item.rule_families)
            if item.style is not None:
                styles.add(item.style)
            if item.bank is not None:
                banks.add(item.bank)
        size = text.stat().st_size
        text_bytes += size
        shards.append({"text": text.relative_to(split_dir).as_posix(),
                       "meta": meta.relative_to(split_dir).as_posix(),
                       "bytes": size, "visits": shard_visits, "questions": len(items),
                       "sha256": hashlib.sha256(text.read_bytes()).hexdigest()})
    return {
        "split": split, "visits": visits, "questions": questions, "visible_questions": visible,
        "text_bytes": text_bytes, "qtypes": dict(sorted(qtypes.items())),
        "depths": dict(sorted(depths.items())), "templates": sorted(templates),
        "styles": sorted(styles), "rule_families": sorted(families), "banks": sorted(banks),
        "names": len(names), "shards": shards,
    }


# ----------------------------------------------------------------- data build


def resolve_visits(visits: Any) -> tuple[str, int, int]:
    """(label, train visits, eval visits per held-out split) from a preset name or a count."""
    if isinstance(visits, str) and visits in VISIT_PRESETS:
        train, held = VISIT_PRESETS[visits]
        return visits, train, held
    try:
        train = int(visits)
    except (TypeError, ValueError):
        raise ValueError(f"--visits must be one of {sorted(VISIT_PRESETS)} or a positive integer") from None
    if train <= 0:
        raise ValueError("--visits must be positive")
    return f"n{train}", train, max(24, min(1_000, train // 10))


def default_writer() -> Writer:
    try:
        from learnlab.village.shards import write_shards
    except ImportError as error:
        raise RuntimeError(
            "the village simulator (learnlab.village.shards) is not available yet: " + str(error)
        ) from None
    return write_shards


def writer_digest(writer: Writer, root: Path) -> str:
    """Digest of the simulator: its package sources for the real writer, else its declared version."""
    module = getattr(writer, "__module__", "") or ""
    if module.startswith("learnlab.village"):
        digest = hashlib.sha256()
        package = root / "learnlab" / "village"
        sources = (sorted(package.glob("*.py")) + [root / "learnlab" / "patterns.py"]
                   + sorted((root / "data" / "village" / "patterns").glob("bank-*.json")))
        for path in sources:
            if path.is_file():
                digest.update(path.name.encode() + b"\0" + path.read_bytes() + b"\0")
        return digest.hexdigest()
    label = f"{module}.{getattr(writer, '__qualname__', repr(writer))}:{getattr(writer, 'version', '')}"
    return hashlib.sha256(label.encode()).hexdigest()


def patterns_version(writer: Writer) -> Optional[str]:
    """The pattern-bank version the writer renders with (None when it does not say)."""
    module = getattr(writer, "__module__", "") or ""
    if module.startswith("learnlab.village"):
        try:
            from learnlab.village.render import PatternSource
        except ImportError:
            return None
        return PatternSource.load().version
    version = getattr(writer, "patterns", None)
    return None if version is None else str(version)


PAIR_GENERATOR = "learnlab.step1:pair_visit"
PAIR_SEED_OFFSET = 500_000_000     # pair visits never share a seed with the plain stream's visits
_PAIRS: dict[tuple[str, int, int], tuple[Any, Any]] = {}


def pair_visit(split: str, index: int, *, seed: int, registry: Any) -> Any:
    """A `write_shards` generator whose visits 2k and 2k+1 are one counterfactual pair.

    Uses the village's own `scheduler.counterfactual_pair` (a visit and its
    sibling differing by one move; same-wording questions with different
    answers are linked by "twin" ids). The pair is cached so its second visit
    is not simulated twice; shards hold an even number of visits, so a pair
    never straddles two shards.
    """
    from learnlab.village.scheduler import counterfactual_pair

    key = (split, seed, index // 2)
    pair = _PAIRS.get(key)
    if pair is None:
        _PAIRS.clear()
        pair = _PAIRS[key] = counterfactual_pair(
            split, seed * 1_000_000_000 + PAIR_SEED_OFFSET + index // 2, registry=registry)
    return pair[index % 2]


def _accepts(writer: Writer, name: str) -> bool:
    try:
        return name in inspect.signature(writer).parameters
    except (TypeError, ValueError):
        return False


@contextlib.contextmanager
def spawn_safe_main() -> Iterator[None]:
    """Stop spawned worker processes from re-running the caller's script.

    `run.py` has no `if __name__ == "__main__"` guard, and multiprocessing's
    spawn start method (macOS, Windows) re-executes the main script in every
    worker. Hiding `__main__.__file__` while workers start makes them import
    only the modules their tasks need.
    """
    main = sys.modules.get("__main__")
    hidden = (main is not None and getattr(main, "__spec__", None) is None
              and "__file__" in vars(main))
    saved = vars(main).pop("__file__") if hidden else None
    try:
        yield
    finally:
        if hidden:
            main.__file__ = saved


def _call_writer(writer: Writer, split: str, visits: int, out_dir: Path, workers: int,
                 seed: int, extra: Optional[Mapping[str, Any]] = None) -> Any:
    kwargs = {"seed": seed} if _accepts(writer, "seed") else {}
    kwargs.update(extra or {})
    with spawn_safe_main():
        return writer(split, visits, out_dir, workers, **kwargs)


def _dir_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _save_json(budget: Any, relative: str, value: Any, limit: int = 50_000_000) -> None:
    budget.save_json(relative, value, limit)


def generate_split(budget: Any, data_rel: str, split: str, visits: int, *, seed: int, workers: int,
                   writer: Writer, log: Log, name: Optional[str] = None,
                   extra: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """Generate one split once into `<name>/` (default: the split's name).

    `<name>/COMPLETE.json` marks a finished, validated split; `extra` goes to
    the writer (e.g. another visit generator).
    """
    name = name or split
    root = Path(budget.root)
    final = root / data_rel / name
    marker = final / "COMPLETE.json"
    if marker.is_file():
        return json.loads(marker.read_text(encoding="utf-8"))
    if final.exists():
        raise RuntimeError(f"{final} exists without COMPLETE.json; move it aside and rerun")
    staging_rel = f"{data_rel}/.staging-{name}-{os.getpid()}-{time.time_ns()}"
    staging = root / staging_rel
    # The simulator writes its own files; reserve generously (32 KB of text and
    # metadata per visit) and verify the real size afterwards.
    cap = max(8_000_000, visits * 32_768)
    log(f"step1 data: generating {visits} {name} visits with {workers} worker(s) ...")
    started = time.perf_counter()
    with budget.reserve(f"village {split} shards", cap):
        staging.mkdir(parents=True, exist_ok=False)
        _call_writer(writer, split, visits, staging, workers, seed, extra)
    seconds = time.perf_counter() - started
    size = _dir_bytes(staging)
    if size > cap:
        raise RuntimeError(f"village {split} shards took {size} bytes, above the {cap}-byte reservation")
    summary = summarize_split(staging, split)
    if split == "train" and summary["visits"] < 2:
        raise RuntimeError("the train split needs at least two visits")
    os.rename(staging, final)
    summary.update(requested_visits=visits, seed=seed, workers=workers,
                   generate_seconds=seconds, bytes=size)
    _save_json(budget, f"{data_rel}/{name}/COMPLETE.json", summary)
    log(f"step1 data: {name}: {summary['visits']} visits, {summary['questions']} questions "
        f"({summary['visible_questions']} visible), {size / 1e6:.1f} MB in {seconds:.1f}s")
    return summary


def english_texts(root: Path, pattern: str = ENGLISH_GLOB) -> tuple[list[str], list[dict[str, Any]]]:
    """The "text" fields of the teacher-written simple English (whatever exists now)."""
    texts, sources = [], []
    for path in sorted(root.glob(pattern)):
        count = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                text = json.loads(line).get("text")
            except (ValueError, AttributeError):
                continue
            if isinstance(text, str) and text.strip():
                texts.append(text)
                count += 1
        sources.append({"path": path.relative_to(root).as_posix(), "texts": count,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return texts, sources


def tokenizer_corpus(shards: Sequence[tuple[str, Path]], char_cap: int = TOKENIZER_CHAR_CAP
                     ) -> tuple[list[str], list[dict[str, Any]]]:
    """Visit texts of TRAIN shards only, up to `char_cap` characters.

    Each shard is given with its split; a shard of any other split is refused,
    so held-out text can never reach the tokenizer.
    """
    texts, used, total = [], [], 0
    for split, text_path in shards:
        if split != "train":
            raise ValueError(f"tokenizer corpus refuses {split} text: {text_path}")
        if total >= char_cap:
            break
        count = 0
        for visit in read_visits(text_path):
            text = "\n".join(line for _, line in visit) + "\n"
            texts.append(text)
            total += len(text)
            count += 1
            if total >= char_cap:
                break
        used.append({"split": split, "path": text_path.name, "visits": count})
    return texts, used


def next_version(path: str) -> str:
    """`path` with the last -v<N> of its file name bumped, else with -v2 before the extensions
    ("premonition-tok-v1-fallback.manifest.json" -> "premonition-tok-v2-fallback.manifest.json")."""
    folder, slash, name = path.rpartition("/")
    stem, dot, extensions = name.partition(".")
    found = list(re.finditer(r"-v(\d+)\b", stem))
    if found:
        last = found[-1]
        stem = f"{stem[:last.start()]}-v{int(last.group(1)) + 1}{stem[last.end():]}"
    else:
        stem += "-v2"
    return folder + slash + stem + dot + extensions


def build_tokenizer(budget: Any, train_dir: Path, *, path: str = TOKENIZER_PATH,
                    manifest_path: str = TOKENIZER_MANIFEST, english_glob: str = ENGLISH_GLOB,
                    vocab_size: int = VOCAB_SIZE, char_cap: int = TOKENIZER_CHAR_CAP,
                    patterns: Optional[str] = None, log: Log = print
                    ) -> tuple[Tokenizer, dict[str, Any]]:
    """Load the saved tokenizer, or fit it on train village text plus simple English and save it.

    A saved file that does not split names into the village's syllables is
    refused and left untouched; the tokenizer is then loaded from (or fitted
    into) `next_version(path)`, and `info["skipped"]` lists the refused files.
    """
    from learnlab.village.names import SYLLABLES

    root = Path(budget.root)
    target = root / path
    if target.is_file():
        tokenizer = Tokenizer.load(target)          # verifies the embedded digest
        if set(tokenizer.syllables) != set(SYLLABLES):
            new_path, new_manifest = next_version(path), next_version(manifest_path)
            reason = "has no name syllables" if not tokenizer.syllables else "has other name syllables"
            log(f"step1 tokenizer: WARNING not using {path} (sha256 {tokenizer.digest[:12]}): it {reason} "
                "than learnlab.village.names.SYLLABLES, so the train names it saw are whole-word tokens "
                f"while held-out names split into rare pieces. Left on disk; using {new_path}")
            tokenizer, info = build_tokenizer(budget, train_dir, path=new_path, manifest_path=new_manifest,
                                              english_glob=english_glob, vocab_size=vocab_size,
                                              char_cap=char_cap, patterns=patterns, log=log)
            info["skipped"] = [path, *info.get("skipped", ())]
            return tokenizer, info
        info = {"path": path, "sha256": tokenizer.digest, "vocab_size": tokenizer.vocab_size,
                "built": False}
        manifest_file = root / manifest_path
        if manifest_file.is_file():
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            if manifest.get("sha256") != tokenizer.digest:
                raise RuntimeError(f"{manifest_path} does not describe {path}")
            if manifest.get("village_splits") != ["train"]:
                raise RuntimeError(f"{path} was not fitted on train text only")
            info.update(manifest=manifest_path, village_patterns=manifest.get("village_patterns"))
            if patterns is not None and manifest.get("village_patterns") != patterns:
                info["patterns_mismatch"] = True
                log(f"step1 tokenizer: WARNING {path} was fitted on patterns "
                    f"{manifest.get('village_patterns')!r}; the village now renders {patterns!r}")
        return tokenizer, info
    shards = [("train", text) for text, _ in shard_files(train_dir)]
    village, used = tokenizer_corpus(shards, char_cap)
    english, english_sources = english_texts(root, english_glob)
    log(f"step1 tokenizer: fitting vocab {vocab_size} on {sum(map(len, village)) / 1e6:.1f}M "
        f"train village chars + {len(english)} English texts ...")
    started = time.perf_counter()
    tokenizer = Tokenizer.train(village + english, vocab_size=vocab_size, syllables=SYLLABLES)
    seconds = time.perf_counter() - started
    payload = tokenizer.to_json().encode("utf-8")
    budget.atomic_write(path, len(payload), lambda handle: handle.write(payload))
    manifest = {
        "name": Path(path).stem, "path": path, "sha256": tokenizer.digest,
        "vocab_size": tokenizer.vocab_size, "requested_vocab_size": vocab_size,
        "specials": list(tokenizer.specials), "village_splits": ["train"],
        "village_patterns": patterns,
        "village_sources": used, "village_chars": sum(map(len, village)),
        "english_sources": english_sources, "english_texts": len(english),
        "fit_seconds": seconds, "created_ns": time.time_ns(),
    }
    _save_json(budget, manifest_path, manifest, 2_000_000)
    log(f"step1 tokenizer: {tokenizer.vocab_size} ids in {seconds:.1f}s -> {path} "
        f"(sha256 {tokenizer.digest[:12]})")
    return tokenizer, {"path": path, "sha256": tokenizer.digest, "vocab_size": tokenizer.vocab_size,
                       "built": True, "manifest": manifest_path, "village_patterns": patterns}


def name_token_audit(tokenizer: Tokenizer) -> Optional[dict[str, Any]]:
    """Pieces per made-up name by split, each name encoded as it appears mid-line (" Kelo").

    Only train names reach the tokenizer's corpus, so a tokenizer that does not
    split names into syllables merges them into whole-word tokens while fresh
    names break into rare pieces, and answers that are fresh names cannot be
    learned. Means are compared per syllable count (people 2, villages 3), since
    the splits mix the two kinds differently. `warning` is set when some splits
    have single-token names and others none, or a held-out mean differs from
    train's by more than NAME_PIECE_GAP. None without the village package.
    """
    try:
        from learnlab.village.names import all_names
        registry = _oracle_registry()
    except ImportError:
        return None
    pieces: dict[str, dict[int, list[int]]] = {split: defaultdict(list) for split in SPLITS}
    for name in all_names():
        pieces[registry.split_of("name", name)][len(name) // 2].append(len(tokenizer.encode(" " + name)))
    splits = {}
    for split, groups in pieces.items():
        counts = [n for group in groups.values() for n in group]
        splits[split] = {
            "names": len(counts), "single_token": counts.count(1), "max_pieces": max(counts, default=None),
            "mean_pieces": sum(counts) / len(counts) if counts else None,
            "mean_pieces_by_syllables": {str(k): sum(v) / len(v) for k, v in sorted(groups.items())},
        }
    single = [split for split in SPLITS if splits[split]["single_token"]]
    train_means = splits["train"]["mean_pieces_by_syllables"]
    gap = max((abs(mean - train_means[k]) for split in HELDOUT
               for k, mean in splits[split]["mean_pieces_by_syllables"].items() if k in train_means), default=0.0)
    audit: dict[str, Any] = {"tokenizer_sha256": tokenizer.digest, "name_syllables": len(tokenizer.syllables),
                             "splits": splits, "single_token_mismatch": 0 < len(single) < len(SPLITS),
                             "max_mean_gap": gap, "warning": None}
    if audit["single_token_mismatch"] or gap > NAME_PIECE_GAP:
        shown = ", ".join(f"{s} {splits[s]['single_token']}/{splits[s]['names']} single-token, "
                          f"{_num(splits[s]['mean_pieces'], '.2f')} pieces" for s in SPLITS)
        audit["warning"] = (f"train and held-out names tokenize differently ({shown}; largest gap {gap:.2f} "
                            f"pieces per name); fresh-name answers are handicapped. Tokenizer "
                            f"{tokenizer.digest[:12]} has {len(tokenizer.syllables)} name syllables")
    return audit


def encode_lines(tokenizer: Tokenizer, lines: Iterable[str]) -> list[list[int]]:
    """Each stream line encoded with its trailing newline.

    Specials split the text before anything else, and every stream line
    starts with one, so concatenating these equals encoding the joined text.
    """
    return [tokenizer.encode(line + "\n") for line in lines]


def encode_visit(tokenizer: Tokenizer, lines: Sequence[str], eos: int) -> list[int]:
    ids: list[int] = []
    for piece in encode_lines(tokenizer, lines):
        ids.extend(piece)
    ids.append(eos)
    return ids


_WORKER_TOKENIZER: Optional[Tokenizer] = None


def _init_encoder(payload: str) -> None:
    global _WORKER_TOKENIZER
    _WORKER_TOKENIZER = Tokenizer.from_json(payload)


def _encode_shard(text_path: str) -> tuple[bytes, list[int]]:
    """uint16 bytes of a whole shard (<eos> after each visit) and per-visit token counts."""
    tokenizer = _WORKER_TOKENIZER
    eos = tokenizer.token_to_id("<eos>")
    out, counts = array("H"), []
    for visit in read_visits(Path(text_path)):
        ids = encode_visit(tokenizer, [line for _, line in visit], eos)
        out.extend(ids)
        counts.append(len(ids))
    return out.tobytes(), counts


def encode_train(budget: Any, data_rel: str, tokenizer: Tokenizer, *, probe_visits: int,
                 workers: int, log: Log) -> dict[str, Any]:
    """Encode the train split once per tokenizer into `tokens-<digest>/`; returns its manifest."""
    if tokenizer.vocab_size > 32767:
        raise ValueError("token files are read back as int16; vocab must stay below 32768")
    token_rel = f"{data_rel}/tokens-{tokenizer.digest[:16]}"
    root = Path(budget.root)
    marker = root / token_rel / "MANIFEST.json"
    if marker.is_file():
        return json.loads(marker.read_text(encoding="utf-8"))
    train_dir = root / data_rel / "train"
    texts = [text for text, _ in shard_files(train_dir)]
    log(f"step1 data: encoding {len(texts)} train shard(s) with {workers} worker(s) ...")
    started = time.perf_counter()
    if workers > 1 and len(texts) > 1:
        with spawn_safe_main():
            context = multiprocessing.get_context("spawn")
            with context.Pool(min(workers, len(texts)), _init_encoder, (tokenizer.to_json(),)) as pool:
                encoded = pool.map(_encode_shard, [str(path) for path in texts])
    else:
        _init_encoder(tokenizer.to_json())
        encoded = [_encode_shard(str(path)) for path in texts]
    seconds = time.perf_counter() - started
    files, probe_files = [], []
    for index, (text, (data, counts)) in enumerate(zip(texts, encoded)):
        pieces = [(f"{text.stem}.tok", data, len(counts))]
        if index == 0 and probe_visits > 0:
            probe = min(probe_visits, max(1, len(counts) // 2))
            cut = 2 * sum(counts[:probe])
            pieces = [(f"probe-{text.stem}.tok", data[:cut], probe),
                      (f"{text.stem}.tok", data[cut:], len(counts) - probe)]
        for name, chunk, visits in pieces:
            if not chunk:
                continue
            budget.atomic_write(f"{token_rel}/{name}", len(chunk),
                                lambda handle, chunk=chunk: handle.write(chunk))
            entry = {"file": name, "tokens": len(chunk) // 2, "visits": visits, "shard": text.stem}
            (probe_files if name.startswith("probe-") else files).append(entry)
    manifest = {
        "tokenizer_sha256": tokenizer.digest, "split": "train", "dtype": "uint16",
        "separator": "<eos>", "files": files, "probe_files": probe_files,
        "tokens": sum(entry["tokens"] for entry in files),
        "probe_tokens": sum(entry["tokens"] for entry in probe_files),
        "encode_seconds": seconds, "workers": workers,
    }
    _save_json(budget, f"{token_rel}/MANIFEST.json", manifest, 5_000_000)
    log(f"step1 data: {manifest['tokens'] + manifest['probe_tokens']:,} train tokens "
        f"({manifest['probe_tokens']:,} in the forgetting probe) in {seconds:.1f}s")
    return manifest


# ----------------------------------------------------------------- oracle index
#
# The shard JSONL carries no slots and no world state, so two things need the
# simulator itself: telling a repeated asking of one question apart from a
# look-alike (the teacher's quiz-later wrapper and a fresh question template
# both change the wording), and grading plans (Q12) the way design/05 says,
# by acting them out with the oracle's `check_plan` on the world as it was
# when the question was asked. The village is deterministic in (split, visit
# seed), so each visit is replayed once at build time, every replayed answer
# is checked against the shard, and the results are cached next to the split.

ORACLE_INDEX = "ORACLE.json"
ORACLE_PLANS = "ORACLE-PLANS.pkl"     # pickled worlds: a local, digest-keyed cache written here
ORACLE_FORMAT = 1
PLAN_BANK = "q.plan_get"
TRAIN_ORACLE_SHARDS = 2               # the probe and held-in questions come from the first shards
_ORACLE_STATE: dict[str, Any] = {}


def is_village_writer(writer: Writer) -> bool:
    return (getattr(writer, "__module__", "") or "").startswith("learnlab.village")


def question_signature(bank: str, slots: Mapping[str, Any]) -> str:
    return f"{bank}|{json.dumps(slots, sort_keys=True, default=str)}"


@contextlib.contextmanager
def capture_asks(sink: list[tuple[Any, dict[str, Any], Any]]) -> Iterator[None]:
    """Record (visit records, question record, world copy or None) for every question the scheduler asks.

    Wraps the scheduler's private `_Visit._do_ask` for the duration only; the
    world is copied for plan questions, whose grading needs it.
    """
    from learnlab.village import scheduler

    original = scheduler._Visit._do_ask

    def spy(self: Any, step: dict[str, Any]) -> bool:
        done = original(self, step)
        if done:
            record = self.questions[step["key"]]
            world = self.world.copy() if record.get("bank") == PLAN_BANK else None
            sink.append((self.records, record, world))
        return done

    scheduler._Visit._do_ask = spy
    try:
        yield
    finally:
        scheduler._Visit._do_ask = original


def _oracle_registry() -> Any:
    """The registry `write_shards` builds (default patterns and the world's families)."""
    registry = _ORACLE_STATE.get("registry")
    if registry is None:
        from learnlab.village.render import PatternSource, village_registry
        from learnlab.village.shards import FAMILIES
        from learnlab.village.stream import load_callable

        registry = _ORACLE_STATE["registry"] = village_registry(PatternSource.load(), load_callable(FAMILIES)())
    return registry


def replay_questions(task: tuple[str, bool, Sequence[str]]) -> dict[str, dict[str, Any]]:
    """Replay visits of one split; question id -> {sig, bank, answer, knowable, plan}.

    `task` is (split, pairs, visit ids). Plain visits are `generate_visit`
    seeds ("<split>-<seed>"); in a pair set (`pair_visit`) a "-cf" id is the
    counterfactual sibling from `counterfactual_pair` of the same seed.
    `plan` is (world when asked, person, object) for answerable plan questions.
    """
    from learnlab.village import scheduler

    split, pairs, visit_ids = task
    registry = _oracle_registry()
    out: dict[str, dict[str, Any]] = {}
    done: set[int] = set()
    for visit_id in visit_ids:
        match = re.fullmatch(rf"{re.escape(split)}-(\d+)(-cf)?", visit_id)
        if match is None:
            raise ShardFormatError(f"cannot replay visit {visit_id!r}: not a standalone {split} visit id")
        seed = int(match.group(1))
        if seed in done:
            continue
        done.add(seed)
        sink: list[tuple[Any, dict[str, Any], Any]] = []
        with capture_asks(sink):
            if pairs:
                packages = scheduler.counterfactual_pair(split, seed, registry=registry)
            else:
                packages = (scheduler.generate_visit(split, seed, registry=registry),)
        for package in packages:
            for records, record, world in sink:
                if records is not package["records"]:
                    continue        # a sibling the pair search tried and dropped
                plan = None
                if record["bank"] == PLAN_BANK and record.get("knowable", True):
                    plan = (world, record["slots"]["person"], record["slots"]["object"])
                out[str(record["id"])] = {
                    "sig": question_signature(record["bank"], record["slots"]), "bank": record["bank"],
                    "answer": str(record["answer"]), "plan": plan}
    return out


def build_oracle(budget: Any, data_rel: str, name: str, split: str, *, workers: int, log: Log,
                 max_shards: Optional[int] = None) -> dict[str, Any]:
    """Replay (once) the visits of `<name>/` and cache question signatures and plan worlds.

    Every replayed question must match its shard record (id, bank, answer);
    a mismatch means the cache does not come from this simulator.
    """
    root = Path(budget.root)
    split_dir = root / data_rel / name
    index_path = split_dir / ORACLE_INDEX
    if index_path.is_file():
        index = json.loads(index_path.read_text(encoding="utf-8"))
        return {key: value for key, value in index.items() if key != "questions"}
    pairs = name.endswith("-pairs")
    files = shard_files(split_dir)[: max_shards or None]
    tasks = []
    for _, meta in files:
        ids = [str(row["id"]) for row in read_records(meta, "visit")]
        tasks.extend((split, pairs, ids[start:start + 32]) for start in range(0, len(ids), 32))
    started = time.perf_counter()
    if workers > 1 and len(tasks) > 1:
        with spawn_safe_main():
            context = multiprocessing.get_context("spawn")
            with context.Pool(min(workers, len(tasks))) as pool:
                parts = pool.map(replay_questions, tasks)
    else:
        parts = [replay_questions(task) for task in tasks]
    replayed: dict[str, dict[str, Any]] = {}
    for part in parts:
        replayed.update(part)
    signatures, plans = {}, {}
    for text, meta in files:
        for record in read_records(meta):
            qid = str(record.get("id"))
            entry = replayed.get(qid)
            if entry is None or entry["bank"] != record.get("bank") or entry["answer"] != str(record.get("answer")):
                raise ShardFormatError(f"{text.name}: replaying question {qid} does not reproduce its record; "
                                       "the cached shards do not come from this simulator")
            signatures[qid] = entry["sig"]
            if entry["plan"] is not None:
                plans[qid] = entry["plan"]
    seconds = time.perf_counter() - started
    payload = pickle.dumps(plans, protocol=4)
    budget.atomic_write(f"{data_rel}/{name}/{ORACLE_PLANS}", len(payload), lambda handle: handle.write(payload))
    summary = {"format": ORACLE_FORMAT, "name": name, "split": split, "pairs": pairs,
               "shards": [text.stem for text, _ in files], "questions_indexed": len(signatures),
               "plan_worlds": len(plans), "seconds": seconds}
    _save_json(budget, f"{data_rel}/{name}/{ORACLE_INDEX}", {**summary, "questions": signatures}, 50_000_000)
    log(f"step1 data: oracle index {name}: {len(signatures)} questions, {len(plans)} plan worlds "
        f"in {seconds:.1f}s")
    return summary


def load_oracle(split_dir: Path) -> tuple[dict[str, str], dict[str, tuple[Any, str, str]], list[str]]:
    """(question id -> signature, question id -> plan world, indexed shard stems); empty without an index."""
    index_path = split_dir / ORACLE_INDEX
    if not index_path.is_file():
        return {}, {}, []
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if index.get("format") != ORACLE_FORMAT:
        raise RuntimeError(f"{index_path} has format {index.get('format')}, expected {ORACLE_FORMAT}")
    plans_path = split_dir / ORACLE_PLANS
    plans = pickle.loads(plans_path.read_bytes()) if plans_path.is_file() else {}
    return index["questions"], plans, list(index["shards"])


@dataclass
class StepData:
    root: Path                  # absolute data directory
    rel: str                    # the same, relative to the budget root
    tag: str
    splits: dict[str, dict[str, Any]]
    tokenizer: Tokenizer
    tokenizer_info: dict[str, Any]
    tokens: dict[str, Any]      # token manifest
    token_dir: Path
    seconds: float
    pairs: dict[str, dict[str, Any]] = field(default_factory=dict)   # "<split>-pairs" -> summary
    oracle: dict[str, dict[str, Any]] = field(default_factory=dict)  # directory -> oracle index summary
    _oracle_cache: dict[str, Any] = field(default_factory=dict, repr=False)

    def split_dir(self, split: str) -> Path:
        return self.root / split

    def oracle_for(self, directory: str) -> tuple[dict[str, str], dict[str, tuple[Any, str, str]], list[str]]:
        found = self._oracle_cache.get(directory)
        if found is None:
            found = self._oracle_cache[directory] = load_oracle(self.split_dir(directory))
        return found

    def summary(self) -> dict[str, Any]:
        splits = {
            name: {key: value for key, value in info.items()
                   if key not in ("templates", "shards")}
            | {"templates": len(info.get("templates", ())), "shards": len(info.get("shards", ()))}
            for name, info in {**self.splits, **self.pairs}.items()
        }
        return {"dir": self.rel, "tag": self.tag, "splits": splits, "tokenizer": self.tokenizer_info,
                "train_tokens": self.tokens["tokens"], "probe_tokens": self.tokens["probe_tokens"],
                "token_files": len(self.tokens["files"]), "oracle": self.oracle, "seconds": self.seconds}


def build_data(budget: Any, *, visits: Any = "small", seed: int = 0, workers: int = 1,
               writer: Optional[Writer] = None, stream_root: str = STREAM_ROOT,
               tokenizer_path: str = TOKENIZER_PATH, tokenizer_manifest: str = TOKENIZER_MANIFEST,
               english_glob: str = ENGLISH_GLOB, vocab_size: int = VOCAB_SIZE,
               probe_visits: Optional[int] = None, pair_count: int = 150, log: Log = print) -> StepData:
    """Generate (once) every split, the tokenizer and the encoded train tokens; all cached."""
    started = time.perf_counter()
    writer = writer or default_writer()
    label, train_visits, held_visits = resolve_visits(visits)
    root = Path(budget.root)
    digest = writer_digest(writer, root)
    tag = f"{label}-seed{seed}-{digest[:12]}"
    data_rel = f"{stream_root}/{tag}"
    splits = {}
    for split in SPLITS:
        count = train_visits if split == "train" else held_visits
        splits[split] = generate_split(budget, data_rel, split, count, seed=seed,
                                       workers=workers, writer=writer, log=log)
    pairs = {}
    if _accepts(writer, "generator"):
        # The plain stream links no twins, so each held-out split gets a set of
        # counterfactual pairs of its own (an even number of visits).
        for split in HELDOUT:
            count = 2 * max(pair_count, held_visits // 2)
            pairs[f"{split}-pairs"] = generate_split(
                budget, data_rel, split, count, seed=seed, workers=workers, writer=writer, log=log,
                name=f"{split}-pairs", extra={"generator": PAIR_GENERATOR})
    oracle = {}
    if is_village_writer(writer):
        for name, split, limit in [(s, s, None) for s in HELDOUT] + [(n, pairs[n]["split"], None) for n in pairs] \
                + [("train", "train", TRAIN_ORACLE_SHARDS)]:
            oracle[name] = build_oracle(budget, data_rel, name, split, workers=workers, log=log, max_shards=limit)
    # Spawned simulator workers import whatever sources are on disk, so an edit
    # during the build could mix two simulators under one tag.
    if writer_digest(writer, root) != digest:
        raise RuntimeError(f"the village simulator changed while {data_rel} was being built; its splits may "
                           "mix two versions. Rerun (the new sources get a new data directory).")
    patterns = patterns_version(writer)
    provisional = bool(patterns) and patterns.startswith(FALLBACK_PATTERNS_PREFIX)
    if provisional and tokenizer_path == TOKENIZER_PATH:
        tokenizer_path, tokenizer_manifest = PROVISIONAL_TOKENIZER_PATH, PROVISIONAL_TOKENIZER_MANIFEST
        log(f"step1 tokenizer: the village renders fallback patterns ({patterns}); using the "
            f"provisional {tokenizer_path}, not {TOKENIZER_PATH}")
    tokenizer, tokenizer_info = build_tokenizer(
        budget, root / data_rel / "train", path=tokenizer_path, manifest_path=tokenizer_manifest,
        english_glob=english_glob, vocab_size=vocab_size, patterns=patterns, log=log)
    tokenizer_info["provisional"] = provisional
    if probe_visits is None:
        probe_visits = max(1, min(200, train_visits // 20))
    tokens = encode_train(budget, data_rel, tokenizer, probe_visits=probe_visits,
                          workers=workers, log=log)
    if tokens["tokenizer_sha256"] != tokenizer.digest:
        raise RuntimeError("encoded train tokens were made with another tokenizer")
    return StepData(root=root / data_rel, rel=data_rel, tag=tag, splits=splits,
                    tokenizer=tokenizer, tokenizer_info=tokenizer_info, tokens=tokens,
                    token_dir=root / data_rel / f"tokens-{tokenizer.digest[:16]}",
                    seconds=time.perf_counter() - started, pairs=pairs, oracle=oracle)


# ----------------------------------------------------------------- stream


def load_tokens(path: Path) -> torch.Tensor:
    data = path.read_bytes()
    if not data:
        return torch.empty(0, dtype=torch.long)
    return torch.frombuffer(bytearray(data), dtype=torch.int16).long()


class TokenStream:
    """Endless stream of pre-encoded train tokens for `Trainer.train`.

    Epoch 0 reads the probe files first, then every other file in name
    order; later epochs reshuffle the other files and never revisit the
    probe, so the probe measures forgetting of material seen exactly once.
    Time spent producing tokens is accumulated in `stall_seconds`.
    """

    def __init__(self, files: Sequence[Path], probe: Sequence[Path] = (), *, chunk: int = 1 << 16,
                 seed: int = 0, align: Optional[tuple[int, int]] = None) -> None:
        if not files and not probe:
            raise ValueError("TokenStream needs at least one token file")
        if chunk <= 0:
            raise ValueError("chunk must be positive")
        self.files, self.probe = list(files), list(probe)
        self.chunk, self.seed = chunk, seed
        # align=(length, eos): yield one (tokens, mask) item per visit, "<eos> visit <eos>" cut or padded
        # (masked) to exactly `length`, so every trainer row starts at a visit start like an eval prompt.
        # Unaligned 768-token windows mostly lacked the scene introduction that answers the questions.
        self.align = align
        self.truncated_visits = self.visits = 0
        self.train_tokens = sum(path.stat().st_size // 2 for path in self.files)
        self.probe_tokens = sum(path.stat().st_size // 2 for path in self.probe)
        self.yielded = 0
        self.epoch = 0
        self.stall_seconds = 0.0
        self._items = self._generate()

    def order(self, epoch: int) -> list[Path]:
        files = list(self.files)
        if epoch > 0:
            random.Random(f"{self.seed}:{epoch}").shuffle(files)
        return (self.probe if epoch == 0 else []) + files

    def _generate(self) -> Iterator[torch.Tensor]:
        epoch = 0
        while True:
            for path in self.order(epoch):
                tokens = load_tokens(path)
                if self.align is not None:
                    yield from self._aligned(tokens)
                    continue
                for start in range(0, tokens.numel(), self.chunk):
                    yield tokens[start:start + self.chunk]
            epoch += 1
            self.epoch = epoch
            if not self.files:
                return

    def _aligned(self, tokens: torch.Tensor) -> Iterator[tuple[torch.Tensor, torch.Tensor]]:
        length, eos = self.align
        ends = (tokens == eos).nonzero().flatten().tolist()
        start = 0
        for end in ends:
            visit = torch.cat([tokens.new_tensor([eos]), tokens[start:end + 1]])
            start = end + 1
            self.visits += 1
            if visit.numel() > length:
                self.truncated_visits += 1
                visit = visit[:length]
            mask = torch.zeros(length, dtype=torch.bool)
            mask[:visit.numel()] = True
            padded = torch.full((length,), eos, dtype=tokens.dtype)
            padded[:visit.numel()] = visit
            yield padded, mask

    def __iter__(self) -> TokenStream:
        return self

    def __next__(self) -> torch.Tensor:
        started = time.perf_counter()
        try:
            item = next(self._items)
        finally:
            self.stall_seconds += time.perf_counter() - started
        self.yielded += (item[1].sum().item() if isinstance(item, tuple) else item.numel())
        return item

    def epochs(self, trained_tokens: int) -> float:
        """Passes over the non-probe train tokens that `trained_tokens` amounts to."""
        if not self.train_tokens:
            return 0.0
        return max(0, trained_tokens - self.probe_tokens) / self.train_tokens


def stream_for(data: StepData, *, chunk: int, seed: int, align: Optional[tuple[int, int]] = None) -> TokenStream:
    files = [data.token_dir / entry["file"] for entry in data.tokens["files"]]
    probe = [data.token_dir / entry["file"] for entry in data.tokens["probe_files"]]
    return TokenStream(files, probe, chunk=chunk, seed=seed, align=align)


# ----------------------------------------------------------------- evaluation items


@dataclass
class EvalItem:
    question: Question
    prompt: list[int]
    context_text: str           # the kept context lines, as the model sees them
    kept_lines: int
    truncated: bool
    evidence_kept: Optional[bool]
    repeat_in_context: bool     # the same question with the same answer is already in the input
    name_answer: bool
    template: str               # seen / unseen / unknown (templates vs the train split)
    style_status: str           # seen / unseen / unknown
    heldout_family: bool        # uses a rule family never seen in train
    changed_since_asked: bool = False   # asked earlier in the input with a different answer


def name_like(answer: str, context: str) -> bool:
    """A single capitalised word that also appears capitalised in the context: a person's name."""
    word = answer.strip().rstrip(".")
    return bool(_NAME_LIKE.match(word)) and word.lower() not in _NOT_NAMES and word in context


def build_items(tokenizer: Tokenizer, questions: Sequence[Question], *, max_len: int,
                seen: Mapping[str, set[str]]) -> list[EvalItem]:
    """Model inputs for `questions`, each ending with the [answer] token and nothing after it."""
    eos, answer_id = tokenizer.token_to_id("<eos>"), tokenizer.token_to_id(ANSWER_TAG)
    cache: dict[str, list[int]] = {}

    def ids(line: str) -> list[int]:
        found = cache.get(line)
        if found is None:
            found = cache[line] = tokenizer.encode(line + "\n")
        return found

    items = []
    for question in questions:
        tail = tokenizer.encode(question.prompt_line)
        if tail[-1] != answer_id or not question.prompt_line.endswith(ANSWER_TAG):
            raise AssertionError(f"prompt for {question.id} does not end with {ANSWER_TAG}")
        room = max_len - len(tail)
        if room < 0:
            raise ValueError(f"question {question.id} alone is longer than {max_len} tokens")
        kept: list[tuple[int, str]] = []
        used = 0
        for number, line in reversed(question.context):
            size = len(ids(line))
            if used + size > room:
                break
            kept.append((number, line))
            used += size
        kept.reverse()
        whole = len(kept) == len(question.context)
        prompt = [eos] if whole and used + 1 <= room else []
        for _, line in kept:
            prompt.extend(ids(line))
        prompt.extend(tail)
        assert prompt[-1] == answer_id and len(prompt) <= max_len
        context_text = "\n".join(line for _, line in kept)
        numbers = {number for number, _ in kept}
        evidence_kept = None
        if question.evidence:
            evidence_kept = all(line in numbers for line in question.evidence)
        # An earlier asking of this very question that is still in the input
        # already shows its answer when the answer has not changed since.
        shown = [answer for line, answer in question.earlier if line in numbers]
        gold = normalize(question.answer)
        repeat = any(normalize(answer) == gold for answer in shown)
        target = normalize(f"{QUESTION_TAG} {question.question} {ANSWER_TAG} {question.answer}")
        repeat = repeat or any(normalize(line).startswith(target) for _, line in kept
                               if line.startswith(QUESTION_TAG))
        templates = question.templates
        if not templates:
            template = "unknown"
        else:
            template = "seen" if all(t in seen["templates"] for t in templates) else "unseen"
        style = question.style
        style_status = "unknown" if style is None else ("seen" if style in seen["styles"] else "unseen")
        items.append(EvalItem(
            question=question, prompt=prompt, context_text=context_text, kept_lines=len(kept),
            truncated=not whole, evidence_kept=evidence_kept, repeat_in_context=repeat,
            name_answer=name_like(question.answer, context_text), template=template,
            style_status=style_status,
            heldout_family=any(f not in seen["rule_families"] for f in question.rule_families),
            changed_since_asked=bool(shown) and not repeat,
        ))
    return items


def sample_questions(questions: Sequence[Question], limit: int, seed: int) -> list[Question]:
    """A deterministic sample of whole twin pairs (so pairs stay intact), in stream order.

    Twins share a group whether `twin` names the other record's id or is a
    pair id both records carry.
    """
    if limit <= 0 or len(questions) <= limit:
        return list(questions)
    ids = {q.id for q in questions}

    def group(q: Question) -> str:
        if q.twin is None or q.twin == q.id:
            return q.id
        return "|".join(sorted((q.id, q.twin))) if q.twin in ids else q.twin

    def rank(key: str) -> str:
        return hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()

    chosen: list[Question] = []
    groups: dict[str, list[Question]] = defaultdict(list)
    for q in questions:
        groups[group(q)].append(q)
    for key in sorted(groups, key=rank):
        if len(chosen) + len(groups[key]) > limit:
            continue
        chosen.extend(groups[key])
        if len(chosen) >= limit:
            break
    order = {q.id: i for i, q in enumerate(questions)}
    return sorted(chosen, key=lambda q: order[q.id])


# ----------------------------------------------------------------- decoding and scoring


def last_logits(model: nn.Module, tokens: torch.Tensor, positions: torch.Tensor) -> torch.Tensor:
    """Logits at one position per row; only those rows go through the output head."""
    rows = torch.arange(tokens.shape[0], device=tokens.device)
    if isinstance(model, Core):
        hidden = model.embed(tokens) + model.pos[: tokens.shape[1]]
        for block in model.blocks:
            hidden = block(hidden)
        return F.linear(model.norm(hidden[rows, positions]), model.embed.weight)
    return model(tokens)[rows, positions]


def _cached_steps(model: Core, tokens: torch.Tensor, lengths: torch.Tensor, max_new: int,
                  stop_mask: torch.Tensor) -> int:
    """Greedy decoding with a key/value cache for `Core`, writing into `tokens` in place.

    Mirrors `Core.forward` exactly: one causal prefill over the prompts (right
    padded), then one token per row per step, attending only to its own
    positions 0..p. A pad's cached key/value is overwritten before any row can
    attend to it. Returns the number of steps taken.
    """
    config = model.config
    batch, width = tokens.shape
    heads, dim = config.n_heads, config.d_model
    head_dim = dim // heads
    device = tokens.device
    prefill = int(lengths.max())
    rows = torch.arange(batch, device=device)
    hidden = model.embed(tokens[:, :prefill]) + model.pos[:prefill]
    caches = []
    for block in model.blocks:
        q, k, v = (block.qkv(block.norm1(hidden)).view(batch, prefill, 3, heads, head_dim)
                   .permute(2, 0, 3, 1, 4))
        keys = torch.zeros(batch, heads, width, head_dim, dtype=k.dtype, device=device)
        values = torch.zeros_like(keys)
        keys[:, :, :prefill], values[:, :, :prefill] = k, v
        caches.append((keys, values))
        attended = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        hidden = hidden + block.proj(attended.transpose(1, 2).reshape(batch, prefill, dim))
        hidden = hidden + block.out(block.act(block.fc(block.norm2(hidden))))
    logits = F.linear(model.norm(hidden[rows, lengths - 1]), model.embed.weight)
    positions = torch.arange(width, device=device)
    where = lengths.clone()
    done = torch.zeros(batch, dtype=torch.bool, device=device)
    steps = 0
    while True:
        chosen = logits.float().argmax(-1)
        tokens[rows, where] = torch.where(done, tokens[rows, where], chosen)
        done |= stop_mask[chosen]
        steps += 1
        if steps >= max_new or bool(done.all()):
            return steps
        step = (model.embed(chosen) + model.pos[where]).unsqueeze(1)          # [batch, 1, dim]
        visible = (positions.unsqueeze(0) <= where.unsqueeze(1))[:, None, None, :]
        for block, (keys, values) in zip(model.blocks, caches):
            q, k, v = (block.qkv(block.norm1(step)).view(batch, 1, 3, heads, head_dim)
                       .permute(2, 0, 3, 1, 4))
            keys[rows, :, where] = k[:, :, 0].to(keys.dtype)
            values[rows, :, where] = v[:, :, 0].to(values.dtype)
            attended = F.scaled_dot_product_attention(q, keys, values, attn_mask=visible)
            step = step + block.proj(attended.transpose(1, 2).reshape(batch, 1, dim))
            step = step + block.out(block.act(block.fc(block.norm2(step))))
        logits = F.linear(model.norm(step[:, 0]), model.embed.weight)
        where = where + 1


def stop_ids(tokenizer: Tokenizer) -> tuple[frozenset[int], frozenset[int]]:
    """(every id that ends an answer, the subset that are newline pieces)."""
    specials = set(range(len(tokenizer.specials)))
    newline = {i for i in range(len(tokenizer.specials), tokenizer.vocab_size)
               if "\n" in tokenizer.decode([i])}
    return frozenset(specials | newline), frozenset(newline)


def _stop_mask(stop: Iterable[int], size: int, device: torch.device) -> torch.Tensor:
    mask = torch.zeros(size, dtype=torch.bool, device=device)
    mask[torch.tensor([s for s in stop if 0 <= s < size], dtype=torch.long, device=device)] = True
    return mask


def greedy_decode(model: nn.Module, prompts: Sequence[Sequence[int]], *, max_new: int,
                  stop: Iterable[int], batch_size: int = 64, pad_id: int = 0,
                  use_cache: bool = True) -> list[list[int]]:
    """Greedy continuations, batched with right padding (causal attention never sees the pads).

    Prompts are sorted by length and batched; every row writes its next token
    at its own position. A `Core` decodes with a key/value cache
    (`_cached_steps`); any other model, or `use_cache=False`, recomputes the
    whole prefix each step. A row's output ends at (and includes) its first
    stop token, or after `max_new` tokens.
    """
    if max_new <= 0 or batch_size <= 0:
        raise ValueError("max_new and batch_size must be positive")
    device = next(model.parameters()).device
    context = getattr(getattr(model, "config", None), "context", None)
    stop_set = set(stop)
    outputs: list[list[int]] = [[] for _ in prompts]
    order = sorted(range(len(prompts)), key=lambda i: len(prompts[i]))
    for start in range(0, len(order), batch_size):
        index = order[start:start + batch_size]
        lengths = [len(prompts[i]) for i in index]
        if min(lengths) == 0:
            raise ValueError("empty prompt")
        width = max(lengths) + max_new
        if context is not None and width > context:
            raise ValueError(f"prompt + max_new = {width} exceeds the context {context}")
        tokens = torch.full((len(index), width), pad_id, dtype=torch.long)
        for row, i in enumerate(index):
            tokens[row, : lengths[row]] = torch.as_tensor(list(prompts[i]), dtype=torch.long)
        tokens = tokens.to(device)
        where = torch.tensor(lengths, dtype=torch.long, device=device)  # next position per row
        rows = torch.arange(len(index), device=device)
        done = torch.zeros(len(index), dtype=torch.bool, device=device)
        steps = 0
        if use_cache and isinstance(model, Core):
            stop_mask = _stop_mask(stop_set, model.config.vocab_size, device)
            with torch.autocast(device.type, dtype=torch.bfloat16, enabled=device.type == "cuda"):
                steps = _cached_steps(model, tokens, where, max_new, stop_mask)
        else:
            stop_mask: Optional[torch.Tensor] = None
            while steps < max_new:
                with torch.autocast(device.type, dtype=torch.bfloat16, enabled=device.type == "cuda"):
                    logits = last_logits(model, tokens[:, : int(where.max())], where - 1)
                if stop_mask is None:
                    stop_mask = _stop_mask(stop_set, logits.shape[-1], device)
                chosen = logits.float().argmax(-1)
                tokens[rows, where] = torch.where(done, tokens[rows, where], chosen)
                done |= stop_mask[chosen]
                where = where + 1
                steps += 1
                if bool(done.all()):
                    break
        tokens = tokens.cpu()
        for row, i in enumerate(index):
            generated = tokens[row, lengths[row]: lengths[row] + steps].tolist()
            for k, token in enumerate(generated):
                if token in stop_set:
                    generated = generated[: k + 1]
                    break
            outputs[i] = generated
    return outputs


def answer_text(tokenizer: Tokenizer, generated: Sequence[int], stops: frozenset[int],
                newline: frozenset[int]) -> str:
    """The answer a continuation spells: text before the first special token or newline."""
    kept: list[int] = []
    for token in generated:
        if token in stops and token not in newline:
            break
        kept.append(token)
        if token in newline:
            break
    return tokenizer.decode(kept).split("\n")[0].strip()


def exact_match(prediction: str, answer: str) -> bool:
    gold = normalize(answer)
    return bool(gold) and normalize(prediction) == gold


_PLAN_WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*")


def plan_works(plan: tuple[Any, str, str], prediction: str) -> bool:
    """design/05 Q12: any plan the oracle's `check_plan` can act out counts.

    The tokenizer lowercases, so person names are restored to the world's
    spelling first (places and objects are lowercase surfaces already).
    """
    from learnlab.village.oracle import check_plan

    world, person, item = plan
    names = {name.lower(): name for name in world.people}
    text = _PLAN_WORD.sub(lambda m: names.get(m.group(0).lower(), m.group(0)), prediction.strip())
    try:
        return bool(check_plan(world, person, item, text))
    except (KeyError, ValueError, TypeError):
        return False


def score_items(model: nn.Module, tokenizer: Tokenizer, items: Sequence[EvalItem], *, max_new: int,
                batch_size: int, plans: Optional[Mapping[str, tuple[Any, str, str]]] = None
                ) -> list[dict[str, Any]]:
    """Greedy answers for `items`; the input always ends at [answer].

    Scoring is exact match, except that an answerable plan question (Q12)
    whose world is in `plans` also counts any plan the oracle accepts.
    """
    stops, newline = stop_ids(tokenizer)
    answer_id = tokenizer.token_to_id(ANSWER_TAG)
    for item in items:
        if item.prompt[-1] != answer_id:
            raise AssertionError("an evaluation input must end with [answer]")
    generated = greedy_decode(model, [item.prompt for item in items], max_new=max_new,
                              stop=stops, batch_size=batch_size,
                              pad_id=tokenizer.token_to_id("<pad>"))
    results = []
    for item, tokens in zip(items, generated):
        prediction = answer_text(tokenizer, tokens, stops, newline)
        q = item.question
        exact = exact_match(prediction, q.answer)
        plan = (plans or {}).get(q.id) if q.qtype == "Q12" else None
        results.append({
            "id": q.id, "split": q.split, "qtype": q.qtype, "depth": q.depth,
            "visible": q.visible, "knowable": q.knowable, "rule_families": list(q.rule_families),
            "heldout_family": item.heldout_family, "template": item.template,
            "style": q.style, "style_status": item.style_status, "name_answer": item.name_answer,
            "truncated": item.truncated, "evidence_kept": item.evidence_kept,
            "repeat_in_context": item.repeat_in_context, "changed_since_asked": item.changed_since_asked,
            "twin": q.twin, "answer": q.answer, "prediction": prediction,
            "exact": exact, "plan_checked": plan is not None,
            "correct": exact or (plan is not None and bool(prediction) and plan_works(plan, prediction)),
        })
    return results


def lm_rows(tokens: torch.Tensor, seq_len: int, max_rows: int) -> torch.Tensor:
    """Up to `max_rows` non-overlapping rows of seq_len + 1 tokens (sharing one boundary token)."""
    rows = min(max_rows, (tokens.numel() - 1) // seq_len)
    if rows <= 0:
        return torch.empty(0, seq_len + 1, dtype=torch.long)
    return tokens[: rows * seq_len + 1].unfold(0, seq_len + 1, seq_len)


def lm_loss_of(model: nn.Module, rows: torch.Tensor, batch_size: int = 8) -> Optional[float]:
    """Mean next-token loss over `rows` (read-only callers only)."""
    if rows.numel() == 0:
        return None
    device = next(model.parameters()).device
    total, count = 0.0, 0
    for start in range(0, rows.shape[0], batch_size):
        chunk = rows[start:start + batch_size].to(device)
        with torch.autocast(device.type, dtype=torch.bfloat16, enabled=device.type == "cuda"):
            logits = model(chunk[:, :-1])
        targets = chunk[:, 1:]
        total += float(lm_loss(logits, targets)) * targets.numel()
        count += targets.numel()
    return total / count


# ----------------------------------------------------------------- summaries


def cell(hits: int, n: int) -> dict[str, Any]:
    interval = list(wilson_interval(hits, n)) if n else [None, None]
    return {"n": n, "hits": hits, "accuracy": hits / n if n else None, "wilson95": interval}


def breakdown(results: Sequence[Mapping[str, Any]], keys: Callable[[Mapping[str, Any]], Iterable[Any]]
              ) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for result in results:
        for key in keys(result):
            groups[str(key)][0] += bool(result["correct"])
            groups[str(key)][1] += 1
    return {key: cell(hits, n) for key, (hits, n) in sorted(groups.items())}


def _knowable(result: Mapping[str, Any]) -> str:
    value = result["knowable"]
    return "unknown" if value is None else ("knowable" if value else "not_told")


def summarize(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Accuracy with Wilson intervals overall and along every reported axis."""
    hits = sum(bool(r["correct"]) for r in results)
    return {
        "overall": cell(hits, len(results)),
        "by_split": breakdown(results, lambda r: [r["split"]]),
        "by_qtype": breakdown(results, lambda r: [r["qtype"]]),
        "by_depth": breakdown(results, lambda r: [r["depth"]]),
        "by_rule_family": breakdown(results, lambda r: r["rule_families"] or ["none"]),
        "by_heldout_family": breakdown(results, lambda r: ["heldout" if r["heldout_family"] else "seen"]),
        "by_knowable": breakdown(results, lambda r: [_knowable(r)]),
        "by_template": breakdown(results, lambda r: [r["template"]]),
        "by_style": breakdown(results, lambda r: [r["style"]]),
        "by_style_status": breakdown(results, lambda r: [r["style_status"]]),
        "by_name_answer": breakdown(results, lambda r: ["name" if r["name_answer"] else "other"]),
        "by_truncated": breakdown(results, lambda r: ["truncated" if r["truncated"] else "whole_visit"]),
        "by_evidence_kept": breakdown(results, lambda r: [r["evidence_kept"]]),
        "by_repeat_in_context": breakdown(results, lambda r: [r["repeat_in_context"]]),
    }


def pair_summary(results: Sequence[Mapping[str, Any]], examples: Mapping[str, QAExample]
                 ) -> dict[str, Any]:
    """Counterfactual twins both answered right, against the chance of guessing both.

    Per-item chance is the larger of 1/K (K distinct answers of that question
    type) and the presence chance (guessing among answer-type candidates in
    its own context); pair chance multiplies the two members' chances.
    """
    by_id = {r["id"]: r for r in results}
    pairs: dict[str, tuple[str, str]] = {}
    groups: dict[str, list[str]] = defaultdict(list)
    for r in results:
        if r["twin"] is None:
            continue
        if r["twin"] in by_id and r["twin"] != r["id"]:
            key = "|".join(sorted((r["id"], r["twin"])))
            pairs[key] = tuple(sorted((r["id"], r["twin"])))
        else:
            groups[r["twin"]].append(r["id"])
    for members in groups.values():
        if len(members) == 2:
            pairs["|".join(sorted(members))] = tuple(sorted(members))
    if not pairs:
        return {"n": 0, "hits": 0, "accuracy": None, "chance": None, "p_value": None}
    answers: dict[str, set[str]] = defaultdict(set)
    for r in results:
        answers[r["qtype"]].add(r["answer"])
    presence = {qtype: example_presence_chance(sorted(vocab)) for qtype, vocab in answers.items()}

    def chance(identifier: str) -> float:
        r = by_id[identifier]
        guess = 1.0 / max(1, len({normalize(a) for a in answers[r["qtype"]]}))
        return max(guess, presence[r["qtype"]](examples[identifier]))

    hits, chances = 0, []
    for a, b in pairs.values():
        hits += bool(by_id[a]["correct"]) and bool(by_id[b]["correct"])
        chances.append(chance(a) * chance(b))
    n = len(pairs)
    mean_chance = sum(chances) / n
    return {"n": n, "hits": hits, "accuracy": hits / n, "chance": mean_chance,
            "wilson95": list(wilson_interval(hits, n)),
            "p_value": binomial_greater(hits, n, min(1.0, mean_chance))}


def name_gap(heldin: Sequence[Mapping[str, Any]], heldout: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Accuracy on name answers: train-split names (seen) minus held-out names (never seen)."""
    seen = [r for r in heldin if r["name_answer"]]
    fresh = [r for r in heldout if r["name_answer"]]
    report = {"seen_names": cell(sum(r["correct"] for r in seen), len(seen)),
              "fresh_names": cell(sum(r["correct"] for r in fresh), len(fresh))}
    if len(seen) < MIN_NAME_ITEMS or len(fresh) < MIN_NAME_ITEMS:
        report.update(measurable=False, gap=None,
                      note=f"needs >= {MIN_NAME_ITEMS} name-answer items on each side")
    else:
        report.update(measurable=True,
                      gap=report["seen_names"]["accuracy"] - report["fresh_names"]["accuracy"],
                      note="train-split vs held-out questions; templates and styles also differ")
    return report


def forgetting_summary(points: Sequence[Mapping[str, Any]], probe_tokens: int) -> dict[str, Any]:
    """The forgetting baseline: probe accuracy and loss at every evaluation point."""
    columns = ["probe", "probe_visible", "probe_long_range", "train_heldin", "validation"]
    matrix = [[p["step"], p["tokens"]] + [p[c]["accuracy"] if p.get(c) else None for c in columns]
              for p in points]
    report: dict[str, Any] = {
        "probe": "questions and text of the first train visits, trained once at the start",
        "probe_tokens": probe_tokens, "points": len(points),
        "matrix": {"columns": ["step", "tokens"] + columns, "rows": matrix},
        "probe_lm_loss": [[p["step"], p.get("probe_lm_loss")] for p in points],
    }
    after = [p for p in points if p["tokens"] > probe_tokens]
    accuracies = [p["probe_visible"]["accuracy"] for p in after
                  if p.get("probe_visible") and p["probe_visible"]["accuracy"] is not None]
    losses = [p["probe_lm_loss"] for p in after if p.get("probe_lm_loss") is not None]
    if accuracies:
        report.update(probe_accuracy_peak=max(accuracies), probe_accuracy_final=accuracies[-1],
                      probe_accuracy_forgetting=max(accuracies) - accuracies[-1])
    if losses:
        report.update(probe_lm_loss_best=min(losses), probe_lm_loss_final=losses[-1],
                      probe_lm_loss_rise=losses[-1] - min(losses))
    return report


# ----------------------------------------------------------------- gate


def _accuracy_criterion(name: str, hits: int, n: int, threshold: float, min_items: int,
                        what: str) -> dict[str, Any]:
    entry: dict[str, Any] = {"criterion": name, "what": what, "threshold": threshold,
                             "n": n, "hits": hits, "accuracy": hits / n if n else None}
    if n < min_items:
        entry.update(status="INSUFFICIENT", reason=f"n={n} < {min_items} items")
        return entry
    low, high = wilson_interval(hits, n, alpha=2 * ALPHA)   # one-sided (1 - ALPHA) bounds
    entry["bounds_99"] = [low, high]
    if low >= threshold:
        entry.update(status="PASS", reason=f"{hits}/{n}: lower 99% bound {low:.3f} >= {threshold}")
    elif high < threshold:
        entry.update(status="FAIL", reason=f"{hits}/{n}: upper 99% bound {high:.3f} < {threshold}")
    else:
        entry.update(status="INSUFFICIENT",
                     reason=f"{hits}/{n}: 99% bounds [{low:.3f}, {high:.3f}] straddle {threshold}")
    return entry


def step1_gate(metrics: Mapping[str, Any], *, threshold: float = GATE_ACCURACY,
               min_items: int = MIN_ITEMS, bottleneck: float = WORLD_BOTTLENECK) -> dict[str, Any]:
    """The design/04 row-1 gate from plain numbers.

    `metrics`: heldout_visible, unseen_templates, unseen_styles,
    heldout_rule_families (each {"hits", "n"}); pairs {"hits", "n", "chance"};
    leak_status ("clean" / "leaking" / "insufficient"); forgetting_points
    (evaluation points recorded); world_stall_fraction (or None).
    """
    criteria = []
    for key, what in (
        ("heldout_visible", "visible-text questions of the held-out splits"),
        ("unseen_templates", "held-out visible questions using templates never seen in train"),
        ("unseen_styles", "held-out visible questions in teacher styles never seen in train"),
        ("heldout_rule_families", "held-out visible questions about rule families never in train"),
    ):
        counts = metrics.get(key) or {"hits": 0, "n": 0}
        criteria.append(_accuracy_criterion(key, int(counts["hits"]), int(counts["n"]),
                                            threshold, min_items, what))
    pairs = metrics.get("pairs") or {"hits": 0, "n": 0, "chance": None}
    entry: dict[str, Any] = {"criterion": "counterfactual_pairs", "what": "both twins right vs chance",
                             "n": pairs["n"], "hits": pairs["hits"], "chance": pairs.get("chance")}
    if pairs["n"] < min_items or pairs.get("chance") is None:
        entry.update(status="INSUFFICIENT", reason=f"{pairs['n']} pairs < {min_items}")
    else:
        p = binomial_greater(int(pairs["hits"]), int(pairs["n"]), min(1.0, float(pairs["chance"])))
        entry["p_value"] = p
        accuracy = pairs["hits"] / pairs["n"]
        if p < ALPHA and accuracy > pairs["chance"]:
            entry.update(status="PASS", reason=f"{accuracy:.3f} vs chance {pairs['chance']:.3f}, p={p:.2g}")
        else:
            entry.update(status="FAIL", reason=f"{accuracy:.3f} vs chance {pairs['chance']:.3f}, p={p:.2g}")
    criteria.append(entry)
    leak = metrics.get("leak_status")
    detail = "; ".join(metrics.get("leak_detail") or ())
    criteria.append({"criterion": "leak_detectors", "what": "per-answer-class leak reports over train vs held-out questions",
                     "value": leak,
                     "status": {"clean": "PASS", "leaking": "FAIL"}.get(leak, "INSUFFICIENT"),
                     "reason": f"leak report status {leak!r}" + (f": {detail}" if detail else "")})
    points = int(metrics.get("forgetting_points") or 0)
    criteria.append({"criterion": "forgetting_baseline", "what": "probe scored at every evaluation point",
                     "value": points, "status": "PASS" if points >= 2 else "INSUFFICIENT",
                     "reason": f"{points} evaluation point(s) recorded"})
    stall = metrics.get("world_stall_fraction")
    world = {"criterion": "world_bottleneck", "what": "share of training time spent waiting for data",
             "value": stall, "threshold": bottleneck}
    if stall is None:
        world.update(status="INSUFFICIENT", reason="not measured")
    elif stall <= bottleneck:
        world.update(status="PASS", reason=f"stall {stall:.2%} <= {bottleneck:.0%}")
    else:
        world.update(status="FAIL", reason=f"stall {stall:.2%} > {bottleneck:.0%}")
    criteria.append(world)
    statuses = [c["status"] for c in criteria]
    overall = "FAIL" if "FAIL" in statuses else ("PASS" if all(s == "PASS" for s in statuses)
                                                 else "INSUFFICIENT")
    reasons = [f"{c['criterion']}: {c['status']} ({c['reason']})" for c in criteria
               if c["status"] != "PASS"]
    return {"status": overall, "criteria": criteria, "reasons": reasons}


# ----------------------------------------------------------------- orchestration


@dataclass
class EvalSets:
    heldout: list[EvalItem]
    heldout_subset: list[EvalItem]
    heldout_long_range: list[EvalItem]
    heldin: list[EvalItem]
    heldin_subset: list[EvalItem]
    probe: list[EvalItem]
    probe_rows: torch.Tensor
    world_rows: torch.Tensor
    pairs: list[EvalItem] = field(default_factory=list)   # twin-linked visible held-out questions
    seen: dict[str, set[str]] = field(default_factory=dict)
    plans: dict[str, tuple[Any, str, str]] = field(default_factory=dict)   # question id -> plan world
    signature_source: dict[str, str] = field(default_factory=dict)        # directory -> oracle / text

    def items(self) -> list[EvalItem]:
        return [*self.heldout, *self.heldout_long_range, *self.heldin, *self.probe, *self.pairs]

    def counts(self) -> dict[str, int]:
        return {"heldout": len(self.heldout), "heldout_subset": len(self.heldout_subset),
                "heldout_long_range": len(self.heldout_long_range), "heldin": len(self.heldin),
                "heldin_subset": len(self.heldin_subset), "probe": len(self.probe),
                "pairs": len(self.pairs), "probe_lm_rows": int(self.probe_rows.shape[0]),
                "heldout_world_lm_rows": int(self.world_rows.shape[0])}


def _questions(data: StepData, split: str, directory: Optional[str] = None) -> list[Question]:
    """Every question of a split's directory (default: the split's own)."""
    signatures = data.oracle_for(directory or split)[0]
    out = []
    for text, meta in shard_files(data.split_dir(directory or split)):
        out.extend(read_questions(text, meta, split, signatures))
    return out


def build_eval_sets(data: StepData, *, seq_len: int, max_new: int, heldout_limit: int,
                    heldin_limit: int, probe_limit: int, subset: int, seed: int,
                    lm_rows_limit: int = 32) -> EvalSets:
    tokenizer = data.tokenizer
    train = data.splits["train"]
    seen = {"templates": set(train["templates"]), "styles": set(train["styles"]),
            "rule_families": set(train["rule_families"])}
    max_len = seq_len - max_new
    heldout_q, long_q = [], []
    for split in HELDOUT:
        questions = _questions(data, split)
        heldout_q.extend(sample_questions([q for q in questions if q.visible], heldout_limit, seed))
        long_q.extend(sample_questions([q for q in questions if not q.visible], heldout_limit // 4, seed))
    probe_visits = sum(entry["visits"] for entry in data.tokens["probe_files"])
    first_texts = shard_files(data.split_dir("train"))
    train_signatures, _, indexed = data.oracle_for("train")
    if indexed:     # held-in questions come from shards the oracle replayed, so repeats are exact
        first_texts = [pair for pair in first_texts if pair[0].stem in indexed] or first_texts[:1]
    probe_q = [q for q in read_questions(*first_texts[0], "train", train_signatures)
               if q.visit < probe_visits]
    probe_q = sample_questions(probe_q, probe_limit, seed)
    heldin_q: list[Question] = []
    for index, (text, meta) in enumerate(first_texts):
        items = [q for q in read_questions(text, meta, "train", train_signatures)
                 if q.visible and (index > 0 or q.visit >= probe_visits)]
        heldin_q.extend(items)
        if len(heldin_q) >= 3 * max(1, heldin_limit):
            break
    heldin_q = sample_questions(heldin_q, heldin_limit, seed)
    pair_q: list[Question] = []
    for name in sorted(data.pairs):
        visible = [q for q in _questions(data, data.pairs[name]["split"], name) if q.visible]
        ids = {q.id for q in visible}
        pair_q.extend(sample_questions([q for q in visible if q.twin in ids], heldout_limit, seed))
    heldout = build_items(tokenizer, heldout_q, max_len=max_len, seen=seen)
    heldin = build_items(tokenizer, heldin_q, max_len=max_len, seen=seen)
    probe = build_items(tokenizer, probe_q, max_len=max_len, seen=seen)
    long_range = build_items(tokenizer, long_q, max_len=max_len, seen=seen)
    probe_tokens = torch.cat([load_tokens(data.token_dir / entry["file"])
                              for entry in data.tokens["probe_files"]] or [torch.empty(0, dtype=torch.long)])
    eos = tokenizer.token_to_id("<eos>")
    world: list[int] = []
    need = lm_rows_limit * seq_len + 1
    for text, _ in shard_files(data.split_dir("validation")):
        for visit in read_visits(text):
            lines = [line for _, line in visit if not line.startswith(QUESTION_TAG)]
            world.extend(encode_visit(tokenizer, lines, eos))
            if len(world) >= need:
                break
        if len(world) >= need:
            break

    sets = EvalSets(
        heldout=heldout, heldout_subset=pick(heldout, subset, seed + 1), heldout_long_range=long_range,
        heldin=heldin, heldin_subset=pick(heldin, max(1, subset // 2), seed + 1), probe=probe,
        probe_rows=lm_rows(probe_tokens, seq_len, lm_rows_limit),
        world_rows=lm_rows(torch.tensor(world, dtype=torch.long), seq_len, lm_rows_limit),
        pairs=build_items(tokenizer, pair_q, max_len=max_len, seen=seen), seen=seen)
    wanted = {item.question.id for item in sets.items()}
    for directory in [*HELDOUT, *sorted(data.pairs), "train"]:
        signatures, plans, _ = data.oracle_for(directory)
        sets.signature_source[directory] = "oracle" if signatures else "text"
        sets.plans.update((qid, plan) for qid, plan in plans.items() if qid in wanted)
    return sets


def pick(items: Sequence[EvalItem], count: int, seed: int) -> list[EvalItem]:
    """A deterministic subset of `count` items that keeps twin pairs together, in order."""
    chosen = {q.id for q in sample_questions([item.question for item in items], count, seed)}
    return [item for item in items if item.question.id in chosen]


def decode_cost(model: nn.Module, items: Sequence[EvalItem], *, max_new: int, batch_size: int) -> float:
    """Worst-case seconds per item: the longest prompts decoded for the full `max_new` steps."""
    sample = sorted(items, key=lambda item: len(item.prompt))[-batch_size:]
    if not sample:
        return 0.0
    started = time.perf_counter()
    greedy_decode(model, [item.prompt for item in sample], max_new=max_new, stop=(),
                  batch_size=batch_size)
    return (time.perf_counter() - started) / len(sample)


def fit_eval_sets(sets: EvalSets, per_item: float, seconds: float, points: int, seed: int,
                  *, final_share: float = 0.3, point_share: float = 0.2) -> dict[str, Any]:
    """Shrink the evaluation sets (in place) so worst-case decoding fits the time budget.

    The final evaluation may take `final_share` of `seconds`, and `points`
    periodic evaluations together `point_share`. Sets shrink proportionally,
    keeping twin pairs whole; nothing shrinks when it already fits.
    """
    final = [sets.heldout, sets.heldout_long_range, sets.heldin, sets.probe, sets.pairs]
    periodic = [sets.probe, sets.heldin_subset, sets.heldout_subset]
    final_cost = per_item * sum(map(len, final))
    point_cost = per_item * points * sum(map(len, periodic))
    final_scale = min(1.0, final_share * seconds / final_cost) if final_cost > 0 else 1.0
    point_scale = min(1.0, point_share * seconds / point_cost) if point_cost > 0 else 1.0
    if final_scale < 1.0:
        sets.heldout = pick(sets.heldout, int(len(sets.heldout) * final_scale), seed)
        sets.heldout_long_range = pick(sets.heldout_long_range,
                                       int(len(sets.heldout_long_range) * final_scale), seed)
        sets.heldin = pick(sets.heldin, int(len(sets.heldin) * final_scale), seed)
        sets.pairs = pick(sets.pairs, int(len(sets.pairs) * final_scale), seed)
    if point_scale < 1.0:
        sets.heldout_subset = pick(sets.heldout_subset, int(len(sets.heldout_subset) * point_scale), seed)
        sets.heldin_subset = pick(sets.heldin_subset, int(len(sets.heldin_subset) * point_scale), seed)
    probe_scale = min(final_scale, point_scale)
    if probe_scale < 1.0:
        sets.probe = pick(sets.probe, int(len(sets.probe) * probe_scale), seed)
    return {"worst_case_seconds_per_item": per_item, "final_scale": final_scale,
            "point_scale": point_scale, "shrunk": final_scale < 1.0 or point_scale < 1.0,
            "worst_case_final_seconds": per_item * sum(map(len, (sets.heldout, sets.heldout_long_range,
                                                                  sets.heldin, sets.probe, sets.pairs)))}


def base_qtype(question: Question) -> str:
    """The question's type before "not told" relabelling: Q10 is the answer "not told" itself.

    The village writes qtype "Q10" exactly when the answer is "not told", so
    handing Q10 to the metadata detector hands it the label. The bank (e.g.
    q.who_has) gives the type the question was asked as.
    """
    try:
        from learnlab.village.oracle import QTYPES
    except ImportError:
        return question.qtype
    return QTYPES.get(question.bank or "", question.qtype)


def qa_example(item: EvalItem) -> QAExample:
    q = item.question
    # The village's `to_qa_examples` metadata (question template, style, type, bank,
    # families, a hypothetical's action), except that the type is the asked type, not the answer's Q10.
    meta = {"template": q.templates[0] if q.templates else "", "style": q.style or "",
            "qtype": base_qtype(q), "bank": q.bank or "", "rule_family": "+".join(q.rule_families) or "none"}
    if q.action:
        meta["action"] = q.action
    return QAExample(item.context_text, q.question, q.answer, meta, group=f"{q.split}/{q.shard}/{q.visit}")


def choice_qtypes() -> frozenset[str]:
    """Question types that name their answer among options (left out of the leak report)."""
    try:
        from learnlab.village.stream import CHOICE_QTYPES
    except ImportError:
        return frozenset({"Q13"})
    return frozenset(CHOICE_QTYPES)


def combine_leak_reports(reports: Mapping[str, Mapping[str, Any]], *,
                         min_share: float = LEAK_COVERAGE) -> dict[str, Any]:
    """One status from the village's per-answer-class leak reports.

    "leaking" if any class leaks; "clean" if none does and the classes too small to test
    ("insufficient") hold under `1 - min_share` of the tested items; else "insufficient".
    """
    total = sum(int(r.get("n", 0)) for r in reports.values())
    tested = sum(int(r.get("n", 0)) for r in reports.values() if r.get("status") in ("clean", "leaking"))
    leaking = {name: r for name, r in reports.items() if r.get("status") == "leaking"}
    if leaking:
        status = "leaking"
    elif total and tested / total >= min_share:
        status = "clean"
    else:
        status = "insufficient"
    detectors = {f"{name}/{det}": d for name, r in sorted(reports.items())
                 for det, d in sorted((r.get("detectors") or {}).items()) if d.get("leaking")}
    return {"status": status, "n": total, "tested_share": tested / total if total else 0.0,
            "classes": {name: r.get("status") for name, r in sorted(reports.items())},
            "insufficient_classes": sorted(name for name, r in reports.items() if r.get("status") == "insufficient"),
            "leaking_detectors": sorted(detectors), "detectors": detectors, "reports": dict(reports)}


def cached_leak_report(budget: Any, data: StepData, train: Sequence[EvalItem],
                       test: Sequence[EvalItem], log: Log) -> dict[str, Any]:
    """The village's per-answer-class leak reports (train questions vs held-out), combined and cached per data
    build and item set.

    One pooled report would be wrong: its nulls (one guess among K answers) assume one answer class, so a
    yes/no or count answer beats 1/K just by its type (`village.stream.leak_reports`). Choice questions ("more
    at L or at L2?") are left out, as in the village's own `to_qa_examples`: their answer is necessarily in
    the question.
    """
    choice = choice_qtypes()
    excluded = sum(item.question.qtype in choice for item in (*train, *test))
    train = [item for item in train if item.question.qtype not in choice]
    test = [item for item in test if item.question.qtype not in choice]
    if not test:
        return {"status": "insufficient", "n": 0, "excluded_choice_items": excluded}
    key = hashlib.sha256(json.dumps(
        [[i.question.id for i in train], [i.question.id for i in test],
         [len(i.prompt) for i in test], data.tokenizer.digest, "per-class-v2"]).encode()).hexdigest()[:16]
    relative = f"{data.rel}/leaks-{key}.json"
    path = Path(budget.root) / relative
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    started = time.perf_counter()
    from learnlab.village.stream import leak_reports

    reports = leak_reports([qa_example(i) for i in train], [qa_example(i) for i in test])
    report = combine_leak_reports({name: r.as_dict() for name, r in reports.items()})
    report["seconds"] = time.perf_counter() - started
    report["excluded_choice_items"] = excluded
    log(f"step1 eval: leak report {report['status']} in {report['seconds']:.1f}s")
    _save_json(budget, relative, report, 5_000_000)
    return report


def audit_inputs(tokenizer: Tokenizer, sets: EvalSets) -> dict[str, Any]:
    """Scan every evaluation input before any model sees it.

    Each input must end with its own question line cut just after
    [answer] (so nothing of the gold answer follows), and fit the model.
    Inputs that already show this question's answer, because the same
    question was asked and answered earlier in the visit, are counted; they
    are scored but kept out of every gated number.
    """
    answer_id = tokenizer.token_to_id(ANSWER_TAG)
    report: dict[str, Any] = {}
    for name in ("heldout", "heldout_long_range", "heldin", "probe", "pairs"):
        items = getattr(sets, name)
        for item in items:
            tail = tokenizer.encode(item.question.prompt_line)
            if item.prompt[-1] != answer_id or item.prompt[-len(tail):] != tail:
                raise AssertionError(f"evaluation input for {item.question.id} does not end with its own "
                                     "question line cut at [answer]")
        report[name] = {"inputs": len(items),
                        "answer_already_in_input": sum(item.repeat_in_context for item in items),
                        "asked_before_with_other_answer": sum(item.changed_since_asked for item in items),
                        "plan_questions_checked_by_oracle": sum(item.question.id in sets.plans for item in items)}
    report["signatures"] = dict(sets.signature_source)
    return report


def gated(results: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Results whose input does not already show the answer (repeats are reported, never gated)."""
    return [r for r in results if not r["repeat_in_context"]]


def gate_metrics(results: Sequence[Mapping[str, Any]], pairs: Mapping[str, Any],
                 leaks: Mapping[str, Any], points: int, stall: Optional[float]) -> dict[str, Any]:
    def count(select: Callable[[Mapping[str, Any]], bool]) -> dict[str, int]:
        chosen = [r for r in results if select(r)]
        return {"hits": sum(bool(r["correct"]) for r in chosen), "n": len(chosen)}

    return {
        "heldout_visible": count(lambda r: True),
        "unseen_templates": count(lambda r: r["template"] == "unseen"),
        "unseen_styles": count(lambda r: r["style_status"] == "unseen"),
        "heldout_rule_families": count(lambda r: r["heldout_family"]),
        "pairs": {"hits": pairs["hits"], "n": pairs["n"], "chance": pairs.get("chance")},
        "leak_status": leaks.get("status", "insufficient"),
        "leak_detail": [f"{name} {d['accuracy']:.1%} vs null {d['null']:.1%}"
                        for name, d in sorted((leaks.get("detectors") or {}).items()) if d.get("leaking")],
        "forgetting_points": points, "world_stall_fraction": stall,
    }


def run_warnings(data: StepData, sets: EvalSets, scored: Mapping[str, Sequence[Mapping[str, Any]]],
                 world: Mapping[str, Any], name_audit: Optional[Mapping[str, Any]] = None) -> list[str]:
    """Things that weaken the numbers without being gate criteria."""
    warnings = []
    info = data.tokenizer_info
    if info.get("provisional"):
        warnings.append(f"village rendered fallback patterns ({info.get('village_patterns')}); the tokenizer "
                        "is provisional and the held-out template axis uses hand-written fallbacks")
    if info.get("patterns_mismatch"):
        warnings.append(f"tokenizer was fitted on patterns {info.get('village_patterns')!r}, "
                        "not the ones rendered now")
    if name_audit and name_audit.get("warning"):
        warnings.append(name_audit["warning"])
    heldout = scored["heldout"]
    lost = [r for r in heldout if r["evidence_kept"] is False]
    if lost:
        warnings.append(f"{len(lost)}/{len(heldout)} visible held-out questions lost evidence lines to the "
                        "context cut; raise --seq-len")
    repeats = sum(bool(r["repeat_in_context"]) for r in heldout)
    if repeats:
        warnings.append(f"{repeats}/{len(heldout)} visible held-out questions were already asked and answered "
                        "(same answer) earlier in their input; they are reported apart and left out of the gate")
    text_only = sorted(name for name, how in sets.signature_source.items() if how != "oracle")
    if data.oracle and text_only:
        warnings.append(f"no oracle index for {', '.join(text_only)}: repeated questions there are found by "
                        "wording only, which misses reworded and teacher-wrapped repeats")
    plans = [r for name in ("heldout", "pairs") for r in scored[name] if r["qtype"] == "Q12"]
    unchecked = sum(not r["plan_checked"] for r in plans)
    if unchecked:
        warnings.append(f"{unchecked}/{len(plans)} plan questions (Q12) are graded by exact match only; "
                        "the oracle's check_plan needs the replayed world")
    if world.get("epochs", 0) > 1:
        warnings.append(f"train data reused for {world['epochs']:.1f} epochs (pre-generated shards)")
    if world.get("epochs", 0) < 1 and scored["heldin"]:
        warnings.append(f"only {world.get('epochs', 0):.2f} epochs trained: some held-in questions may "
                        "come from text not yet trained on")
    return warnings


def core_config(size: str, vocab_size: int, context: int) -> CoreConfig:
    if size in TEST_SIZES:
        d_model, layers, heads = TEST_SIZES[size]
        return CoreConfig(vocab_size, context, d_model, layers, heads)
    return CoreConfig.preset(size, vocab_size, context)


def run_step1(budget: Any, *, size: str = "4M", device: str = "cpu", seconds: float = 60.0,
              visits: Any = "small", eval_every: int = 0, seed: int = 0, workers: int = 1,
              seq_len: int = 768, batch: int = 32, lr: Optional[float] = None,
              warmup: Optional[int] = None, eval_limit: Optional[int] = None, max_new: int = 32,
              eval_batch: int = 64, points: int = 6, writer: Optional[Writer] = None,
              stream_root: str = STREAM_ROOT, tokenizer_path: str = TOKENIZER_PATH,
              tokenizer_manifest: str = TOKENIZER_MANIFEST, english_glob: str = ENGLISH_GLOB,
              save: bool = True, environment: Optional[dict[str, Any]] = None, log: Log = print,
              on_log: Optional[Callable[[dict[str, Any]], None]] = None) -> dict[str, Any]:
    """Build data if missing, train the core for `seconds`, evaluate, gate, and save the report.

    `seconds` bounds everything after the data is ready: eval-set building,
    training with periodic evaluations, the final evaluation and saving. The
    final evaluation's time is reserved from the step-0 evaluation's cost.
    """
    if not 0 < seconds <= MAX_SECONDS:
        raise ValueError(f"seconds must be in (0, {MAX_SECONDS}]")
    if size not in SIZES and size not in TEST_SIZES:
        raise ValueError(f"unknown size {size!r}")
    data = build_data(budget, visits=visits, seed=seed, workers=workers, writer=writer,
                      stream_root=stream_root, tokenizer_path=tokenizer_path,
                      tokenizer_manifest=tokenizer_manifest, english_glob=english_glob, log=log)
    name_audit = name_token_audit(data.tokenizer)
    if name_audit and name_audit["warning"]:
        log(f"step1 tokenizer: WARNING {name_audit['warning']}")
    run_started = time.perf_counter()
    torch.manual_seed(seed)
    cuda = device == "cuda"
    if eval_limit is None:
        eval_limit = 2000 if cuda else 60
    tokenizer = data.tokenizer
    sets = build_eval_sets(data, seq_len=seq_len, max_new=max_new, heldout_limit=eval_limit,
                           heldin_limit=max(50, eval_limit // 2), probe_limit=max(50, eval_limit // 4),
                           subset=max(20, eval_limit // 6), seed=seed,
                           lm_rows_limit=32 if cuda else 4)
    config_core = core_config(size, tokenizer.vocab_size, seq_len)
    lr = lr if lr is not None else DEFAULT_LR.get(size, 3e-4)
    warmup = warmup if warmup is not None else (100 if cuda else 10)
    train_config = TrainConfig(batch=batch, seq_len=seq_len, lr=lr, warmup_steps=warmup)
    model = Core(config_core)
    trainer = Trainer(model, train_config, device)
    stream = stream_for(data, chunk=batch * seq_len, seed=seed, align=(seq_len, tokenizer.token_to_id("<eos>")))
    kwargs = dict(tokenizer=tokenizer, max_new=max_new, batch_size=eval_batch, plans=sets.plans)
    per_item = trainer.evaluate(lambda m: decode_cost(
        m, [*sets.heldout, *sets.heldin, *sets.probe], max_new=max_new, batch_size=eval_batch))
    fitted = fit_eval_sets(sets, per_item, seconds, points, seed)
    log("step1 eval sets: " + json.dumps(sets.counts())
        + f" (worst case {per_item * 1000:.1f} ms/item; scale final {fitted['final_scale']:.2f}, "
        f"points {fitted['point_scale']:.2f})")
    input_audit = audit_inputs(tokenizer, sets)
    log("step1 eval inputs: " + json.dumps({name: entry for name, entry in input_audit.items()
                                             if name in ("heldout", "pairs")}))
    leaks = cached_leak_report(budget, data, [i for i in sets.heldin if not i.repeat_in_context],
                               [i for i in sets.heldout if not i.repeat_in_context], log)

    def point(model: nn.Module) -> dict[str, Any]:
        started = time.perf_counter()
        probe = gated(score_items(model, items=sets.probe, **kwargs))
        heldin = gated(score_items(model, items=sets.heldin_subset, **kwargs))
        heldout = gated(score_items(model, items=sets.heldout_subset, **kwargs))
        visible = [r for r in probe if r["visible"]]
        return {
            "probe": cell(sum(r["correct"] for r in probe), len(probe)),
            "probe_visible": cell(sum(r["correct"] for r in visible), len(visible)),
            "probe_long_range": cell(sum(r["correct"] for r in probe if not r["visible"]),
                                     len(probe) - len(visible)),
            "train_heldin": cell(sum(r["correct"] for r in heldin), len(heldin)),
            "validation": cell(sum(r["correct"] for r in heldout), len(heldout)),
            "probe_lm_loss": lm_loss_of(model, sets.probe_rows),
            "heldout_world_lm_loss": lm_loss_of(model, sets.world_rows),
            "eval_seconds": time.perf_counter() - started,
        }

    points_log: list[dict[str, Any]] = []

    def record(result: dict[str, Any]) -> None:
        result.update(step=trainer.step, tokens=trainer.tokens,
                      elapsed=time.perf_counter() - run_started)
        points_log.append(result)
        log(f"step1 eval @ step {trainer.step}: probe {result['probe']['accuracy']}, "
            f"held-in {result['train_heldin']['accuracy']}, held-out {result['validation']['accuracy']}, "
            f"probe loss {result['probe_lm_loss']}")

    record(trainer.evaluate(point))
    reserve = min(0.35 * seconds, 4.5 + 1.2 * fitted["worst_case_final_seconds"])  # + saving
    train_budget = seconds - (time.perf_counter() - run_started) - reserve
    train_totals = {"steps": 0, "tokens": 0, "seconds": 0.0, "stop": "max_seconds",
                    "peak_gpu_reserved_bytes": None, "final_loss": None}
    status, error = "completed", None
    loop_started = time.perf_counter()
    try:
        while True:
            remaining = train_budget - (time.perf_counter() - loop_started)
            if remaining <= 0.5:
                break
            if eval_every:
                segment = dict(max_tokens=eval_every * batch * seq_len, max_seconds=remaining)
            else:
                segment = dict(max_seconds=min(remaining, max(1.0, train_budget / points)))
            result = trainer.train(stream, on_log=on_log, **segment)
            for key in ("steps", "tokens", "seconds"):
                train_totals[key] += result[key]
            train_totals.update(stop=result["stop"], final_loss=result["final_loss"] or
                                train_totals["final_loss"],
                                peak_gpu_reserved_bytes=result["peak_gpu_reserved_bytes"])
            if result["steps"] == 0:
                break
            record(trainer.evaluate(point))
            if result["stop"] == "stream ended":
                break
    except MemoryGuardError as guard:
        status, error = "aborted", str(guard)
        train_totals["peak_gpu_reserved_bytes"] = guard.peak
    train_totals["tokens_per_s"] = train_totals["tokens"] / max(train_totals["seconds"], 1e-9)
    train_totals["stall_seconds"] = stream.stall_seconds
    stall = stream.stall_seconds / train_totals["seconds"] if train_totals["seconds"] > 0 else None

    def final(model: nn.Module) -> dict[str, list[dict[str, Any]]]:
        return {"heldout": score_items(model, items=sets.heldout, **kwargs),
                "heldout_long_range": score_items(model, items=sets.heldout_long_range, **kwargs),
                "heldin": score_items(model, items=sets.heldin, **kwargs),
                "probe": score_items(model, items=sets.probe, **kwargs),
                "pairs": score_items(model, items=sets.pairs, **kwargs)}

    final_started = time.perf_counter()
    scored = trainer.evaluate(final)
    final_seconds = time.perf_counter() - final_started
    examples = {item.question.id: qa_example(item) for item in (*sets.heldout, *sets.pairs)}
    # Repeats (the input already shows the answer) are reported but never gated;
    # a twin pair with a repeated member leaves the pair test.
    gated_heldout = gated(scored["heldout"])
    repeats = [r for r in scored["heldout"] if r["repeat_in_context"]]
    pairs = pair_summary(gated_heldout + gated(scored["pairs"]), examples)
    heldout_summary = summarize(gated_heldout)
    heldin_summary = summarize(gated(scored["heldin"]))
    plan_results = [r for name in ("heldout", "pairs") for r in gated(scored[name]) if r["qtype"] == "Q12"]
    plan_grading = {
        "checker": "learnlab.village.oracle.check_plan" if sets.plans else None,
        "plan_questions": len(plan_results),
        "checked_by_oracle": sum(r["plan_checked"] for r in plan_results),
        "right_exact": sum(r["exact"] for r in plan_results),
        "right_other_working_plan": sum(r["correct"] and not r["exact"] for r in plan_results),
    }
    gap = None
    if heldout_summary["overall"]["n"] and heldin_summary["overall"]["n"]:
        gap = heldin_summary["overall"]["accuracy"] - heldout_summary["overall"]["accuracy"]
    forgetting = forgetting_summary(points_log, data.tokens["probe_tokens"])
    world_rate = None
    train_split = data.splits["train"]
    gen_seconds = train_split.get("generate_seconds", 0.0) + data.tokens.get("encode_seconds", 0.0)
    if gen_seconds > 0:
        world_rate = (data.tokens["tokens"] + data.tokens["probe_tokens"]) / gen_seconds
    learner_rate = train_totals["tokens_per_s"] if train_totals["tokens"] else None
    world = {
        "stall_seconds": stream.stall_seconds, "stall_fraction": stall,
        "aligned_visits": stream.visits, "truncated_visits": stream.truncated_visits,
        "pregenerated": True, "train_tokens": data.tokens["tokens"],
        "probe_tokens": data.tokens["probe_tokens"],
        "epochs": stream.epochs(trainer.tokens),
        "live_world_tokens_per_s": world_rate, "live_workers": train_split.get("workers"),
        "learner_tokens_per_s": learner_rate,
        "live_supply_ratio": (world_rate / learner_rate) if world_rate and learner_rate else None,
        "note": ("training reads pre-encoded shards, so the stall is the real slowdown; "
                 "live_supply_ratio < 1 means live generation at this worker count could not "
                 "keep up and the data were reused for `epochs` passes"),
    }
    metrics = gate_metrics(gated_heldout, pairs, leaks, len(points_log), stall)
    gate = step1_gate(metrics)
    warnings = run_warnings(data, sets, scored, world, name_audit)
    ns, pid = time.time_ns(), os.getpid()
    stem = f"artifacts/{MODEL_NAME}-step1-{size}-{ns}-{pid}"
    config = {
        "model": MODEL_NAME, "step": 1, "core": asdict(config_core), "train": asdict(train_config),
        "tokenizer": data.tokenizer_info, "data": {"dir": data.rel, "tag": data.tag},
        "seed": seed, "max_new": max_new,
    }
    report: dict[str, Any] = {
        "command": "step1", "model": MODEL_NAME, "size": size, "device": device,
        "parameters": model.num_parameters(), "status": status, "error": error,
        "limits": {"seconds": seconds, "train_budget_seconds": train_budget,
                   "final_eval_reserve_seconds": reserve},
        "config": config, "data": data.summary(), "eval_sets": sets.counts(), "eval_fit": fitted,
        "input_audit": input_audit, "name_token_audit": name_audit,
        "train": train_totals, "world": world, "evaluations": points_log,
        "final": {
            "heldout_visible": heldout_summary,
            "heldout_repeats": summarize(repeats),
            "heldout_long_range": summarize(scored["heldout_long_range"]),
            "train_heldin": heldin_summary, "probe": summarize(gated(scored["probe"])),
            "generalisation_gap": gap, "counterfactual_pairs": pairs,
            "counterfactual_set": summarize(gated(scored["pairs"])),
            "name_gap": name_gap(gated(scored["heldin"]), gated_heldout),
            "plan_grading": plan_grading,
            "seconds": final_seconds,
        },
        "forgetting_baseline": forgetting, "leaks": leaks, "gate_metrics": metrics, "gate": gate,
        "warnings": warnings,
        "predictions": [{key: r[key] for key in ("id", "split", "qtype", "answer", "prediction", "correct",
                                                 "exact", "plan_checked", "repeat_in_context")}
                        for r in scored["heldout"][:4000]],
        "history": trainer.history, "environment": environment,
    }
    if save:
        if status == "completed":
            from learnlab.ckpt import save_checkpoint

            save_checkpoint(budget, stem + ".ckpt", model=trainer.model, config=config,
                            optimizer=trainer.optimizer, trainer_state=trainer.state_dict())
            report["checkpoint"] = stem + ".ckpt"
        report["artifact"] = stem + ".json"
    report["elapsed_seconds"] = time.perf_counter() - run_started
    if save:
        budget.save_json(report["artifact"], _jsonable(report), 60_000_000)
    return report


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_jsonable(v) for v in value)
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return repr(value)


def _num(value: Any, spec: str = ".3f") -> str:
    return "n/a" if value is None else format(value, spec)


def _pct(entry: Optional[Mapping[str, Any]]) -> str:
    if not entry or not entry.get("n"):
        return "n/a (n=0)"
    low, high = entry["wilson95"]
    return f"{entry['accuracy']:.1%} [{low:.1%}, {high:.1%}] n={entry['n']}"


def format_summary(report: Mapping[str, Any]) -> str:
    """A readable multi-line summary of a Step 1 report."""
    final, train, world = report["final"], report["train"], report["world"]
    held = final["heldout_visible"]
    stall = world["stall_fraction"]
    lines = [
        f"PREMONITION step 1 ({report['size']}, {report['parameters']:,} params, {report['device']}) "
        f"status={report['status']}",
        f"data {report['data']['tag']}: {report['data']['train_tokens']:,} train tokens; "
        f"tokenizer {report['config']['tokenizer']['sha256'][:12]} "
        f"({report['config']['tokenizer']['vocab_size']} ids"
        f"{', PROVISIONAL' if report['config']['tokenizer'].get('provisional') else ''})",
        f"train: {train['steps']} steps, {train['tokens']:,} tokens, {train['seconds']:.1f}s, "
        f"{train['tokens_per_s']:,.0f} tok/s, loss {_num(train['final_loss'])}, epochs {world['epochs']:.2f}, "
        f"stall {'n/a' if stall is None else format(stall, '.2%')}",
        f"held-out visible: {_pct(held['overall'])}",
    ]
    for split, entry in held["by_split"].items():
        lines.append(f"  {split}: {_pct(entry)}")
    for axis in ("by_qtype", "by_depth", "by_rule_family", "by_knowable", "by_template",
                 "by_style_status", "by_truncated"):
        parts = [f"{key}={entry['accuracy']:.0%}/{entry['n']}" for key, entry in held[axis].items()
                 if entry["n"]]
        lines.append(f"  {axis[3:]}: " + ", ".join(parts))
    if "heldout_repeats" in final:
        lines.append(f"held-out repeats (answer already in the input; not gated): "
                     f"{_pct(final['heldout_repeats']['overall'])}")
    plans = final.get("plan_grading")
    if plans:
        lines.append(f"plans (Q12, gated sets): {plans['plan_questions']} questions, "
                     f"{plans['checked_by_oracle']} graded by {plans['checker'] or 'exact match only'}; "
                     f"right {plans['right_exact']} exact + {plans['right_other_working_plan']} other working plans")
    lines.append(f"held-out long-range (not gated): {_pct(final['heldout_long_range']['overall'])}")
    lines.append(f"train held-in: {_pct(final['train_heldin']['overall'])}; generalisation gap "
                 f"{_num(final['generalisation_gap'])}")
    pairs = final["counterfactual_pairs"]
    lines.append(f"counterfactual pairs: {pairs['hits']}/{pairs['n']} both right, chance "
                 f"{_num(pairs['chance'])}; twin-linked questions {_pct(final['counterfactual_set']['overall'])}")
    gap = final["name_gap"]
    lines.append(f"name gap: {_num(gap['gap']) if gap['measurable'] else 'not measurable'} "
                 f"(seen {_pct(gap['seen_names'])}; fresh {_pct(gap['fresh_names'])})")
    forgetting = report["forgetting_baseline"]
    lines.append(f"forgetting baseline: {forgetting['points']} points; visible probe acc peak "
                 f"{_num(forgetting.get('probe_accuracy_peak'))} final "
                 f"{_num(forgetting.get('probe_accuracy_final'))}; probe loss best "
                 f"{_num(forgetting.get('probe_lm_loss_best'))} final {_num(forgetting.get('probe_lm_loss_final'))}")
    leaks = report["leaks"]
    lines.append(f"leaks: {leaks.get('status')} (leaking: {leaks.get('leaking_detectors', [])})")
    for warning in report.get("warnings", []):
        lines.append(f"WARNING: {warning}")
    lines.append(f"GATE: {report['gate']['status']}")
    for criterion in report["gate"]["criteria"]:
        lines.append(f"  {criterion['status']:<12} {criterion['criterion']}: {criterion['reason']}")
    if report.get("artifact"):
        lines.append(f"report -> {report['artifact']}")
    if report.get("checkpoint"):
        lines.append(f"checkpoint -> {report['checkpoint']}")
    return "\n".join(lines)


__all__ = [
    "EvalItem", "EvalSets", "MODEL_NAME", "Question", "ShardFormatError", "StepData",
    "TOKENIZER_PATH", "TokenStream", "VISIT_PRESETS", "answer_text", "audit_inputs", "base_qtype",
    "build_data", "build_eval_sets", "build_items", "build_oracle", "build_tokenizer", "capture_asks",
    "encode_visit", "exact_match", "format_summary", "gated", "greedy_decode", "last_logits",
    "load_oracle", "name_token_audit", "next_version", "parse_question_line", "plan_works", "read_questions",
    "read_visits",
    "replay_questions", "run_step1", "sample_questions", "score_items", "shard_files", "step1_gate",
    "summarize", "tokenizer_corpus",
]
