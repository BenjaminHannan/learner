"""Slice tags for Experiment 1 (design/06 §6 "Evaluation changes", items 1-8).

Every question gets one set of tags, keyed by its question id, computed once from the data and
the v2 tokenizer and applied to every contender, so paired comparisons always cover the same items:

1. near / far: knowable questions whose evidence lines all survive A's cut (`step1.build_items`
   at max_len 768 - 32 = 736), or not. Step 1's `visible` (2,048 characters, 40 records) is not
   the model's window and is not used here.
3. multi-hop: knowable with depth 2-5 (depths 4-5 are untrained for every contender); also per depth.
4. changed: the visit is replayed with the scheduler (`generate_visit`, spied on like
   `step1.capture_asks`) and `oracle.ask` is called for the question after every earlier step;
   the question is changed when an earlier knowable answer differs from the one it was given.
   Those older answers are kept, so a prediction equal to one of them is "stale".
5. fresh names: held-out answers containing a detected person or village name (for now, a
   capitalised word in `names.all_names()`; `premonition.pointer` will own the detector). Names are
   split whole between train and held-out villages, so every held-out name is fresh; held-in train
   answers with a name are the "seen" side.
6. reworded (unseen template or teacher style) and not told (reported, never gated).
7. far-long: `long_visit` (four days per visit) generates `<split>-long` directories through
   `step1.generate_split(..., extra={"generator": LONG_GENERATOR})`. `step1.build_oracle` replays
   without `days`, so these splits get no oracle index; the replay here passes `days` and supplies
   their exact repeat signatures and plan worlds instead.
8. exclusions, reported apart and kept out of every decision cell: step 1's repeats under A's cut
   (`step1.gated`), repeats anywhere earlier in the visit (D reads the whole visit, so an earlier
   asking with the same answer is in its input even when A's window has lost it), and the
   leak-flagged answer classes, who-has (`q.who_has`) and box contents (`q.in_container`).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from functools import lru_cache
import json
import multiprocessing
from pathlib import Path
import re
import time
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from learnlab import step1
from learnlab.leaks import normalize
from learnlab.step1 import ANSWER_TAG, QUESTION_TAG, EvalItem, Question, ShardFormatError
from learnlab.tokenizer import Tokenizer

SEQ_LEN = 768                       # every contender's context (design/06 §0)
MAX_NEW = 32                        # answer tokens decoded
CUT_MAX_LEN = SEQ_LEN - MAX_NEW     # A's cut: the canonical near/far boundary for every contender
MULTI_HOP = (2, 5)                  # inclusive depth range of the multi-hop decision cell
DEPTHS = range(1, 7)                # scheduler.MAX_DEPTH of the held-out splits is 6
LEAK_CLASSES = {"q.who_has": "who_has", "q.in_container": "box_contents"}
DECISION_SLICES = ("overall", "near", "far", "far_deep", "multi_hop")
PLAIN_GENERATOR = "learnlab.village.shards:world_visit"
LONG_GENERATOR = "premonition.slices:long_visit"
LONG_DAYS = 4
LONG_SEED_OFFSET = 700_000_000      # long visits never share a seed with plain (0..) or pair (5e8..) visits
GENERATOR_DAYS: dict[str, Optional[int]] = {PLAIN_GENERATOR: None, LONG_GENERATOR: LONG_DAYS}
REPLAY_CHUNK = 32                   # visits per replay task
_NAME_WORD = re.compile(r"\b[A-Z][a-z]+\b")
_REGISTRY: dict[str, Any] = {}

Log = Callable[[str], None]


# ----------------------------------------------------------------- tags


@dataclass(frozen=True)
class SliceTags:
    """What one question is, for slicing; identical for every contender."""

    id: str
    source: str                         # the directory it came from: "validation", "test-long", "train", ...
    split: str
    qtype: str
    bank: Optional[str]
    depth: Optional[int]
    knowable: Optional[bool]
    evidence_kept: Optional[bool]       # under A's cut; None when the question has no evidence lines
    repeat: bool                        # step 1's repeat_in_context under A's cut (`step1.gated` drops it)
    repeat_in_visit: bool               # asked earlier in the visit with the same answer, in or out of A's window
    reworded: bool                      # unseen template or unseen teacher style
    names: tuple[str, ...]              # names detected in the canonical answer
    changed: Optional[bool]             # None: the visit was not replayed
    older_answers: tuple[str, ...] = ()  # earlier knowable answers that differ from the final one
    long: bool = False                  # from a `<split>-long` directory

    @property
    def near(self) -> bool:
        return self.knowable is True and self.evidence_kept is True

    @property
    def far(self) -> bool:
        return self.knowable is True and self.evidence_kept is False

    @property
    def multi_hop(self) -> bool:
        return self.knowable is True and self.depth is not None and MULTI_HOP[0] <= self.depth <= MULTI_HOP[1]

    @property
    def not_told(self) -> bool:
        return self.knowable is False

    @property
    def fresh_name(self) -> bool:
        return self.split != "train" and bool(self.names)

    @property
    def seen_name(self) -> bool:
        return self.split == "train" and bool(self.names)

    @property
    def leak_class(self) -> Optional[str]:
        return LEAK_CLASSES.get(self.bank or "")

    @property
    def exclusions(self) -> tuple[str, ...]:
        """Why the question is kept out of the decision cells (empty: it is in them)."""
        out = []
        if self.repeat:
            out.append("repeat")
        if self.repeat_in_visit:
            out.append("repeat_in_visit")
        if self.leak_class:
            out.append(f"leak:{self.leak_class}")
        return tuple(out)

    @property
    def decision(self) -> bool:
        return not self.exclusions

    def slices(self) -> tuple[str, ...]:
        """Every slice the question is counted in.

        A decision item is in "overall" and its content slices; an excluded item only in
        "excluded" and "excluded:<reason>" (one per reason), so no cell mixes the two.
        """
        if not self.decision:
            return ("excluded",) + tuple(f"excluded:{reason}" for reason in self.exclusions)
        out = ["overall"]
        if self.near:
            out.append("near")
        if self.far:
            out.append("far")
            if self.depth is not None and self.depth >= 2:
                out.append("far_deep")      # the kill cell: far with depth >= 2
            if self.long:
                out.append("far_long")
        if self.multi_hop:
            out.append("multi_hop")
        if self.knowable and self.depth is not None:
            out.append(f"depth_{self.depth}")
        if self.knowable and self.evidence_kept is None:
            out.append("knowable_no_evidence")
        if self.changed is True:
            out.append("changed")
        elif self.changed is False:
            out.append("unchanged")
        if self.fresh_name:
            out.append("fresh_names")
        if self.seen_name:
            out.append("seen_names")
        if self.reworded:
            out.append("reworded")
        if self.not_told:
            out.append("not_told")
        return tuple(out)

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "slices": list(self.slices()), "decision": self.decision,
                "exclusions": list(self.exclusions)}


@lru_cache(maxsize=1)
def village_names() -> frozenset[str]:
    """Every person and village name the simulator can draw, in any split."""
    from learnlab.village.names import all_names

    return frozenset(all_names())


def detect_names(text: str, names: Optional[Iterable[str]] = None) -> tuple[str, ...]:
    """Capitalised words of `text` that are names (default: the village's name pools), in order."""
    pool = village_names() if names is None else frozenset(names)
    return tuple(dict.fromkeys(word for word in _NAME_WORD.findall(text) if word in pool))


def canonical_items(tokenizer: Tokenizer, questions: Sequence[Question], *, seen: Mapping[str, set[str]],
                    max_len: int = CUT_MAX_LEN) -> list[EvalItem]:
    """A's inputs: step 1's `build_items` at A's cut. Their `evidence_kept` defines near and far."""
    return step1.build_items(tokenizer, questions, max_len=max_len, seen=seen)


def window_start(item: EvalItem) -> int:
    """Shard line number where A's window begins (the question's own line when nothing was kept).

    Lines of the visit before it are what A cannot see: plain lookup's candidates (design/06 §5).
    """
    q = item.question
    return q.context[-item.kept_lines][0] if item.kept_lines else q.line


def _repeat_in_visit(q: Question) -> bool:
    """An earlier asking anywhere in the visit showed this very answer (by signature, or same text)."""
    gold = normalize(q.answer)
    if any(normalize(answer) == gold for _, answer in q.earlier):
        return True
    target = normalize(f"{QUESTION_TAG} {q.question} {ANSWER_TAG} {q.answer}")
    return any(normalize(line).startswith(target) for _, line in q.context if line.startswith(QUESTION_TAG))


def tag_questions(tokenizer: Tokenizer, questions: Sequence[Question], *, seen: Mapping[str, set[str]],
                  source: str, replays: Optional[Mapping[str, "Replayed"]] = None,
                  names: Optional[Iterable[str]] = None, max_len: int = CUT_MAX_LEN
                  ) -> tuple[list[EvalItem], dict[str, SliceTags]]:
    """(A's evaluation items, question id -> tags) for the questions of one directory.

    With `replays` (from `replay_split`), every question must have been replayed with the
    shard's own answer; anything else means the shards do not come from this simulator.
    """
    pool = None if names is None else frozenset(names)
    items = canonical_items(tokenizer, questions, seen=seen, max_len=max_len)
    tags: dict[str, SliceTags] = {}
    for item in items:
        q = item.question
        replay = None
        if replays is not None:
            replay = replays.get(q.id)
            if replay is None or replay.answer != q.answer:
                raise ShardFormatError(f"replaying question {q.id} does not reproduce its record "
                                       f"({None if replay is None else replay.answer!r} vs {q.answer!r})")
        tags[q.id] = SliceTags(
            id=q.id, source=source, split=q.split, qtype=q.qtype, bank=q.bank, depth=q.depth,
            knowable=q.knowable, evidence_kept=item.evidence_kept, repeat=item.repeat_in_context,
            repeat_in_visit=_repeat_in_visit(q),
            reworded=item.template == "unseen" or item.style_status == "unseen",
            names=detect_names(q.answer, pool),
            changed=None if replay is None else replay.changed,
            older_answers=() if replay is None else replay.older,
            long=source.endswith("-long"))
    return items, tags


def is_stale(tags: SliceTags, prediction: str) -> bool:
    """The prediction is an answer this question had earlier in the visit, but no longer has."""
    said = normalize(prediction)
    return bool(said) and any(normalize(answer) == said for answer in tags.older_answers)


def decision_slices(tags: Mapping[str, SliceTags]) -> dict[str, tuple[str, ...]]:
    """Question id -> slice names, for the decision rules: decision items of plain (not -long) splits."""
    return {qid: tag.slices() for qid, tag in tags.items() if tag.decision and not tag.long}


# ----------------------------------------------------------------- changed-fact replay


@dataclass(frozen=True)
class Replayed:
    """One question as the replayed scheduler asked it, and what it would have answered earlier."""

    id: str
    answer: str                         # the answer when it was asked (checked against the shard)
    older: tuple[str, ...]              # knowable answers at earlier steps that differ from `answer`, sorted
    signature: str                      # `step1.question_signature` of its (bank, slots)
    plan: Optional[tuple[Any, str, str]]  # (world when asked, person, object) for answerable plan questions
    states: int                         # earlier steps at which the question was askable
    errors: int                         # earlier steps at which `ask` raised (reported; expected 0)

    @property
    def changed(self) -> bool:
        return bool(self.older)


def _refers(world: Any, slots: Mapping[str, Any]) -> bool:
    """`_Visit._do_ask`'s precondition: the question (and a hypothetical's action) names existing things."""
    action = slots.get("action")
    return world.refers(slots) and not (action and not world.refers(action["slots"]))


def replay_changes(generate: Callable[[], Any]) -> dict[str, Replayed]:
    """Question id -> `Replayed` for the one visit `generate()` simulates (it must be deterministic).

    Pass 1 records every question the scheduler asks. Pass 2 re-runs the visit with
    `_Visit.run` spied on: after every completed script step that ends before a question's
    line, `oracle.ask(obs, world, bank, slots)` is called for it. Steps, not single records,
    because one action emits several records and between them the world is ahead of the
    observer (ask's truth check would fire); questions are asked at step boundaries too. Pass 2
    must ask the same questions with the same answers, which checks that the extra `ask` calls
    left the simulation untouched.
    """
    from learnlab.village import scheduler
    from learnlab.village.oracle import ask

    first: list[tuple[Any, dict[str, Any], Any]] = []
    with step1.capture_asks(first):
        generate()
    asked = [(str(r["id"]), r["bank"], r["slots"], int(r["line"]), str(r["answer"])) for _, r, _ in first]
    answers: dict[str, set[str]] = defaultdict(set)
    states: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    original = scheduler._Visit.run

    def spy(self: Any, step: dict[str, Any]) -> bool:
        done = original(self, step)
        if done:
            end = len(self.records)
            for qid, bank, slots, line, _ in asked:
                if end > line or not _refers(self.world, slots):
                    continue
                try:
                    answer = ask(self.obs, self.world, bank, slots)
                except (AssertionError, KeyError, ValueError, TypeError, IndexError):
                    errors[qid] += 1
                    continue
                if answer is not None:
                    states[qid] += 1
                    if answer.knowable:
                        answers[qid].add(str(answer.answer))
        return done

    second: list[tuple[Any, dict[str, Any], Any]] = []
    scheduler._Visit.run = spy
    try:
        with step1.capture_asks(second):
            generate()
    finally:
        scheduler._Visit.run = original
    if [(str(r["id"]), str(r["answer"])) for _, r, _ in second] != [(a[0], a[4]) for a in asked]:
        raise RuntimeError("replaying the visit with extra oracle.ask calls changed it")
    out = {}
    for (qid, bank, slots, _, final), (_, record, world) in zip(asked, first):
        plan = None
        if bank == step1.PLAN_BANK and record.get("knowable", True) and world is not None:
            plan = (world, slots["person"], slots["object"])
        out[qid] = Replayed(id=qid, answer=final, older=tuple(sorted(answers[qid] - {final})),
                            signature=step1.question_signature(bank, slots), plan=plan,
                            states=states[qid], errors=errors[qid])
    return out


def village_registry() -> Any:
    """The registry `write_shards` renders with: default patterns plus the world's rule families."""
    registry = _REGISTRY.get("registry")
    if registry is None:
        from learnlab.village.render import PatternSource, village_registry as make
        from learnlab.village.shards import FAMILIES
        from learnlab.village.stream import load_callable

        registry = _REGISTRY["registry"] = make(PatternSource.load(), load_callable(FAMILIES)())
    return registry


def replay_visit(split: str, visit_id: str, *, days: Optional[int] = None,
                 registry: Optional[Any] = None) -> dict[str, Replayed]:
    """`replay_changes` for a standalone visit "<split>-<seed>" (plain or long; not a "-cf" sibling)."""
    from learnlab.village.scheduler import generate_visit

    match = re.fullmatch(rf"{re.escape(split)}-(\d+)", visit_id)
    if match is None:
        raise ShardFormatError(f"cannot replay visit {visit_id!r}: not a standalone {split} visit id")
    seed = int(match.group(1))
    registry = registry if registry is not None else village_registry()
    return replay_changes(lambda: generate_visit(split, seed, registry=registry, days=days))


def _replay_task(task: tuple[str, Optional[int], Sequence[str]]) -> dict[str, Replayed]:
    split, days, visit_ids = task
    out: dict[str, Replayed] = {}
    for visit_id in visit_ids:
        out.update(replay_visit(split, visit_id, days=days))
    return out


def shard_generator(split_dir: Path) -> Optional[str]:
    """The visit generator `write_shards` recorded for a directory; None if unknown or mixed.

    Only `write_shards` writes a manifest.json, so a directory made by another writer (the unit
    tests' fake village) has none and is never replayed.
    """
    found = {json.loads(path.read_text(encoding="utf-8")).get("generator")
             for path in Path(split_dir).rglob("manifest.json")}
    return found.pop() if len(found) == 1 else None


def replay_split(split_dir: Path, split: str, *, days: Optional[int] = None, workers: int = 1,
                 log: Log = print) -> dict[str, Replayed]:
    """Replay every visit of a directory (parallel over `workers` spawned processes)."""
    ids = [str(row["id"]) for _, meta in step1.shard_files(Path(split_dir))
           for row in step1.read_records(meta, "visit")]
    tasks = [(split, days, ids[start:start + REPLAY_CHUNK]) for start in range(0, len(ids), REPLAY_CHUNK)]
    started = time.perf_counter()
    if workers > 1 and len(tasks) > 1:
        with step1.spawn_safe_main():
            context = multiprocessing.get_context("spawn")
            with context.Pool(min(workers, len(tasks))) as pool:
                parts = pool.map(_replay_task, tasks)
    else:
        parts = [_replay_task(task) for task in tasks]
    out: dict[str, Replayed] = {}
    for part in parts:
        out.update(part)
    changed = sum(r.changed for r in out.values())
    log(f"premonition slices: replayed {len(ids)} visits of {Path(split_dir).name} ({len(out)} questions, "
        f"{changed} changed, {sum(r.errors for r in out.values())} ask errors) in "
        f"{time.perf_counter() - started:.1f}s")
    return out


# ----------------------------------------------------------------- far-long split


def long_visit(split: str, index: int, *, seed: int, registry: Any) -> dict[str, Any]:
    """A `write_shards` generator: standalone visits of LONG_DAYS days (plain ones have 1-2).

    Seeds are offset by LONG_SEED_OFFSET, so the ids ("<split>-<seed>") never collide with plain
    or pair visits and `replay_visit(..., days=LONG_DAYS)` reproduces them.
    """
    from learnlab.village.scheduler import generate_visit

    return generate_visit(split, seed * 1_000_000_000 + LONG_SEED_OFFSET + index, registry=registry,
                          days=LONG_DAYS)


def long_name(split: str) -> str:
    return f"{split}-long"


def generate_long_split(budget: Any, data_rel: str, split: str, visits: int, *, seed: int, workers: int,
                        log: Log = print, writer: Optional[step1.Writer] = None) -> dict[str, Any]:
    """Generate (once) `<data_rel>/<split>-long/` with `long_visit` through `step1.generate_split`."""
    if split not in step1.HELDOUT:
        raise ValueError(f"far-long splits are held-out only, not {split!r}")
    return step1.generate_split(budget, data_rel, split, visits, seed=seed, workers=workers,
                                writer=writer or step1.default_writer(), log=log, name=long_name(split),
                                extra={"generator": LONG_GENERATOR})


__all__ = [
    "CUT_MAX_LEN", "DECISION_SLICES", "GENERATOR_DAYS", "LEAK_CLASSES", "LONG_DAYS", "LONG_GENERATOR",
    "MAX_NEW", "MULTI_HOP", "Replayed", "SEQ_LEN", "SliceTags", "canonical_items", "decision_slices",
    "detect_names", "generate_long_split", "is_stale", "long_name", "long_visit", "replay_changes",
    "replay_split", "replay_visit", "shard_generator", "tag_questions", "village_names", "village_registry",
    "window_start",
]
