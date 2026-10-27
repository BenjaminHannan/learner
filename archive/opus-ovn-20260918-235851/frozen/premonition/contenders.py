"""Experiment 1's `Core`-based contenders A, B12, B28, C and E: FLOP-budgeted training and evaluation.

design/06 §0, §4, §5 and §9. Every contender is a `learnlab.core.Core` trained by `learnlab.train.Trainer`
on its own stream:

| name | Core (d x layers x heads) | lr   | inputs |
|------|---------------------------|------|--------|
| A    | "4M" preset 256 x 4 x 4   | 1e-3 | step 1's stream (`step1.stream_for`), prompts as `step1.build_items` |
| B12  | 384 x 6 x 6               | 6e-4 | as A |
| B28  | "28M" preset 512 x 8 x 8  | 6e-4 | as A |
| C    | as A                      | 1e-3 | plain lookup (`premonition.lookup`): recalled lines, <bos>, window |
| E    | as A, vocab + 16 entities | 1e-3 | D's pointerizer: names -> ENT ids, numbered per visit (shuffled in training) |

Training (`train_contender`) stops at a budget: F training FLOPs (design/06 §4), or T tokens for the
token-matched runs (§9.7). FLOPs are what `premonition.flops` counts (`FlopCounterMode`, dense attention,
backward recompute): one step of a `Core` has fixed shapes, so it is measured once on the CPU (one row,
scaled by the batch; every counted op is linear in the batch) and the run takes round(F / step) steps. A
budget that no whole number of steps meets within `policy.BUDGET_TOLERANCE` is refused before training.
The run logs FLOPs, tokens and seconds, saves a step-1 style checkpoint (`learnlab.ckpt`; its config
carries everything evaluation needs: contender, core, tokenizer, data and, for C the BM25 table, for E the
name detector's path and digest) and a JSON report under artifacts/.

Evaluation (`evaluate_contender`) is `premonition.exp1.evaluate_checkpoint` with the contender's own
scorer passed to `exp1.evaluate_directory` (exp1 only knows plain `Core` prompts): the same questions,
tags, read-only scoring and report layout, so `exp1.verdict` pairs these reports with any other. The
canonical items exp1 passes in fix the question set and the tags; each scorer rebuilds its model input
from the item's question:

- plain (A, B): the 736-token window over the regime's visible lines (`lookup.plain_input`); in the
  label-free regime (§9.1, the default) that equals exp1's canonical label-free prompt, which is checked.
- lookup (C): `lookup.lookup_input`, plus gold recall@8 on the canonical far questions.
- pointer (E): the visit up to the question pointerized with identity numbering (first mention = ENT0,
  as D evaluates), cut at whole lines to fill 736 tokens (E's own window: a name is one token here, so
  it may hold more lines than A's), then the question up to "[answer]". The name table binds only what
  the input shows (never the answer); the decoded ids are detokenised with it, so an ENT id becomes the
  name's exact spelling and an unbound ENT id a placeholder that never matches.

Inputs follow `premonition.preprocess` (the path D shares): label-free inputs are audited
(`preprocess.audit_ids`), reports carry the regime and an identity block, and `evaluate_contender` refuses
to score a checkpoint that fails `premonition.identity`'s checks for the requested purpose. Training
checkpoints record `preprocess.identity("with-labels")`: Core training streams keep answers as LM targets.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from functools import lru_cache
import json
import os
from pathlib import Path
import random
import time
from typing import Any, Callable, Iterable, Iterator, Mapping, Optional, Sequence, Union

import torch
from torch import nn

from learnlab import step1
from learnlab.core import SIZES, Core, CoreConfig
from learnlab.policy import BUDGET_TOLERANCE
from learnlab.step1 import ANSWER_TAG, EvalItem, Question
from learnlab.tokenizer import Tokenizer
from learnlab.train import MemoryGuardError, TrainConfig, Trainer

from premonition import exp1, flops, identity, lookup, preprocess, slices
from premonition.batch import N_ENT, NameTable
from premonition.lookup import Bm25, LineIds, Window, cut_window
from premonition.pointer import Binder, NameDetector, answer_text, pointerize, random_order
from premonition.preprocess import LABEL_FREE, WITH_LABELS
from premonition.slices import CUT_MAX_LEN, MAX_NEW, SEQ_LEN

MODEL_NAME = "premonition-exp1"
Log = Callable[[str], None]


@dataclass(frozen=True)
class Contender:
    name: str
    shape: tuple[int, int, int]     # d_model, layers, heads
    lr: float
    inputs: str                     # "plain" | "lookup" | "pointer"


CONTENDERS: dict[str, Contender] = {
    "A": Contender("A", SIZES["4M"], 1e-3, "plain"),
    "B12": Contender("B12", (384, 6, 6), 6e-4, "plain"),
    "B28": Contender("B28", SIZES["28M"], 6e-4, "plain"),
    "C": Contender("C", SIZES["4M"], 1e-3, "lookup"),
    "E": Contender("E", SIZES["4M"], 1e-3, "pointer"),
}


class BudgetError(ValueError):
    """No whole number of training steps lands within the tolerance of the budget."""


def contender(name: str) -> Contender:
    if name not in CONTENDERS:
        raise ValueError(f"unknown contender {name!r}; choose from {sorted(CONTENDERS)}")
    return CONTENDERS[name]


def core_config(name: str, vocab_size: int, *, context: int = SEQ_LEN, size: Optional[str] = None) -> CoreConfig:
    """The contender's `Core` (E adds the N_ENT entity ids to the vocabulary); `size` overrides its shape
    ("tiny" = step 1's unit-test size, or a `core.SIZES` preset)."""
    spec = contender(name)
    if size is None:
        d_model, layers, heads = spec.shape
    elif size in step1.TEST_SIZES:
        d_model, layers, heads = step1.TEST_SIZES[size]
    elif size in SIZES:
        d_model, layers, heads = SIZES[size]
    else:
        raise ValueError(f"unknown size {size!r}")
    vocab = vocab_size + (N_ENT if spec.inputs == "pointer" else 0)
    return CoreConfig(vocab, context, d_model, layers, heads)


# ----------------------------------------------------------------- FLOPs and budgets


@lru_cache(maxsize=32)
def _row_flops(config: CoreConfig, seq_len: int) -> int:
    with torch.random.fork_rng(devices=[]):
        model = Core(config)
    return flops.measure_core(model, torch.zeros(1, seq_len + 1, dtype=torch.long))


def step_flops(config: CoreConfig, batch: int, seq_len: int) -> int:
    """Counted training FLOPs (forward + backward) of one [batch, seq_len] step of `Core(config)`.

    Measured with `flops.measure_core` on one row of a fresh CPU model (the caller's RNG is untouched)
    and multiplied by `batch`: the counter's matmul and attention formulas are all linear in the batch.
    """
    return batch * _row_flops(config, seq_len)


@dataclass(frozen=True)
class BudgetPlan:
    kind: str                   # "flops" | "tokens"
    target: float               # F (FLOPs) or T (tokens)
    steps: int
    step_flops: int
    step_tokens: int
    tolerance: float

    @property
    def flops(self) -> int:
        return self.steps * self.step_flops

    @property
    def tokens(self) -> int:
        return self.steps * self.step_tokens

    def error(self, steps: int) -> float:
        """Relative distance from the target after `steps` steps."""
        done = steps * (self.step_flops if self.kind == "flops" else self.step_tokens)
        return (done - self.target) / self.target


def plan_budget(step_flops_: int, step_tokens: int, *, flops_budget: Optional[float] = None,
                tokens_budget: Optional[float] = None, tolerance: float = BUDGET_TOLERANCE) -> BudgetPlan:
    """Steps that land nearest the FLOP (or token) budget; BudgetError if even those miss by > tolerance."""
    if (flops_budget is None) == (tokens_budget is None):
        raise ValueError("give exactly one of a FLOP budget or a token budget")
    kind, target, unit = (("flops", float(flops_budget), step_flops_) if flops_budget is not None
                          else ("tokens", float(tokens_budget), step_tokens))
    if target <= 0:
        raise ValueError("the budget must be positive")
    steps = max(1, int(target / unit + 0.5))
    plan = BudgetPlan(kind, target, steps, step_flops_, step_tokens, tolerance)
    if abs(plan.error(steps)) > tolerance:
        raise BudgetError(f"{steps} step(s) of {unit:,} {kind} give {steps * unit:,}, more than {tolerance:.0%} "
                          f"from the budget {target:,.0f}; use a smaller batch")
    return plan


def budget_from_report(report: Union[str, Path, Mapping[str, Any]]) -> dict[str, Any]:
    """F and T of a finished run: a `train_contender` report, or a step-1 report (`run_step1`; its FLOPs
    are its steps x the counted step FLOPs of its core, batch and sequence length)."""
    if not isinstance(report, Mapping):
        report = json.loads(Path(report).read_text(encoding="utf-8"))
    config = report.get("config") or {}
    tokenizer = (config.get("tokenizer") or {}).get("sha256")
    if report.get("command") == "premonition train":
        return {"flops": float(report["flops"]["achieved"]), "tokens": int(report["train"]["tokens"]),
                "source": report.get("artifact"), "contender": report.get("contender"), "tokenizer_sha256": tokenizer}
    if report.get("command") == "step1":
        core, train = CoreConfig(**config["core"]), config["train"]
        steps = int(report["train"]["steps"])
        per_step = step_flops(core, int(train["batch"]), int(train["seq_len"]))
        return {"flops": float(steps * per_step), "tokens": int(report["train"]["tokens"]),
                "source": report.get("artifact"), "contender": "A", "tokenizer_sha256": tokenizer,
                "steps": steps, "step_flops": per_step}
    raise ValueError(f"not a training report: command {report.get('command')!r}")


# ----------------------------------------------------------------- E: names as pointers


class PointerStream:
    """E's endless training stream: the pointerized train visits (`premonition.data.VisitCache`), each
    renumbered by a fresh random entity order and followed by <eos> as in step 1's token files. Every
    epoch visits them in a new shuffled order."""

    def __init__(self, cache: Any, eos: int, *, seed: int = 0) -> None:
        if len(cache) == 0:
            raise ValueError("an empty visit cache")
        self.cache, self.seed = cache, seed
        self.eos = torch.tensor([eos], dtype=torch.long)
        self.visits = 0
        self.yielded = 0
        self._items = self._generate()

    def _generate(self) -> Iterator[torch.Tensor]:
        base = self.cache.vocab_size
        lookup_ids = torch.arange(base + N_ENT)
        epoch = 0
        while True:
            order = list(range(len(self.cache)))
            random.Random(f"{self.seed}:visits:{epoch}").shuffle(order)
            rng = random.Random(f"{self.seed}:entities:{epoch}")
            for index in order:
                lookup_ids[base:] = base + torch.tensor(random_order(rng))
                yield torch.cat((lookup_ids[self.cache.visit_tokens(index)], self.eos))
            epoch += 1

    def __iter__(self) -> PointerStream:
        return self

    def __next__(self) -> torch.Tensor:
        item = next(self._items)
        self.visits += 1
        self.yielded += item.numel()
        return item

    def summary(self) -> dict[str, Any]:
        return {"visits_yielded": self.visits, "epochs": self.visits / len(self.cache), "tokens_yielded": self.yielded,
                "cache_visits": len(self.cache), "cache_tokens": int(self.cache.tokens.numel())}


@dataclass(frozen=True)
class PointerInput:
    ids: list[int]              # pointerized input ending with "[answer]"
    table: NameTable            # entity -> spelling, bound from the visit's lines before the answer only
    window: Window


def pointer_input(question: Question, tokenizer: Tokenizer, detector: NameDetector, *, max_len: int = CUT_MAX_LEN,
                  labels: Optional[bool] = None, regime: Optional[str] = None,
                  cache: Optional[dict[str, list[int]]] = None) -> PointerInput:
    """E's input: the visit before the question pointerized in first-mention order over its visible lines
    (label-free unless `labels` / `regime` say otherwise), cut at whole lines to fill `max_len` with the
    question line up to "[answer]"."""
    regime = preprocess.regime_of(labels, regime)
    binder = Binder()
    pieces = [pointerize(preprocess.visible_line(line, regime) + "\n", tokenizer, detector, binder=binder,
                         cache=cache)[0] for _, line in question.context]
    tail = pointerize(question.prompt_line, tokenizer, detector, binder=binder, cache=cache)[0]
    if tail[-1] != tokenizer.token_to_id(ANSWER_TAG):
        raise AssertionError(f"prompt for {question.id} does not end with {ANSWER_TAG}")
    window = cut_window([n for n, _ in question.context], pieces, max_len - len(tail),
                        tokenizer.token_to_id("<eos>"), question.line)
    ids = window.ids + tail
    if len(ids) > max_len:
        raise AssertionError(f"E input for {question.id} has {len(ids)} tokens (max {max_len})")
    return PointerInput(ids=ids, table=binder.table, window=window)


def entity_answer(ids: Iterable[int], table: NameTable, tokenizer: Tokenizer) -> str:
    """The answer decoded ids spell, entities written as their exact spellings; an entity the table does
    not hold becomes "<entK>", which matches no answer (`preprocess.prediction_text`)."""
    return preprocess.prediction_text(ids, table, tokenizer)[0]


def load_detector(project: Union[str, Path], config: Mapping[str, Any]) -> NameDetector:
    """The name detector an E checkpoint was trained with (refitted from the train split if the file is gone)."""
    info = config["pointer"]
    path = Path(project) / info["detector"]
    if path.is_file():
        detector = NameDetector.load(path)
    else:
        from premonition.data import fit_detector
        detector = fit_detector(Path(project) / config["data"]["dir"] / "train")
    if detector.digest != info["sha256"]:
        raise ValueError(f"name detector {detector.digest[:12]} is not the one E was trained with "
                         f"({info['sha256'][:12]})")
    return detector


# ----------------------------------------------------------------- scoring


def result_row(item: EvalItem, prediction: str, plans: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """`step1.score_items`' result for one item and prediction (same keys, same scoring)."""
    q = item.question
    exact = step1.exact_match(prediction, q.answer)
    plan = (plans or {}).get(q.id) if q.qtype == "Q12" else None
    return {
        "id": q.id, "split": q.split, "qtype": q.qtype, "depth": q.depth,
        "visible": q.visible, "knowable": q.knowable, "rule_families": list(q.rule_families),
        "heldout_family": item.heldout_family, "template": item.template,
        "style": q.style, "style_status": item.style_status, "name_answer": item.name_answer,
        "truncated": item.truncated, "evidence_kept": item.evidence_kept,
        "repeat_in_context": item.repeat_in_context, "changed_since_asked": item.changed_since_asked,
        "twin": q.twin, "answer": q.answer, "prediction": prediction,
        "exact": exact, "plan_checked": plan is not None,
        "correct": exact or (plan is not None and bool(prediction) and step1.plan_works(plan, prediction)),
    }


def _lengths(inputs: Sequence[Sequence[int]]) -> dict[str, Any]:
    sizes = [len(ids) for ids in inputs]
    return {"inputs": len(sizes), "max_tokens": max(sizes, default=0),
            "mean_tokens": sum(sizes) / len(sizes) if sizes else None}


class ContenderScorer:
    """The `scorer` hook of `exp1.evaluate_directory` for one contender's inputs.

    Called with exp1's canonical items (A's cut in the same regime); rebuilds each input from the item's
    question and scores it like `step1.score_items`. Label-free inputs are audited before decoding.
    Each call's input diagnostics go to `calls`.
    """

    def __init__(self, inputs: str, *, labels: Optional[bool] = None, regime: Optional[str] = None,
                 bm25: Optional[Bm25] = None, detector: Optional[NameDetector] = None,
                 max_len: int = CUT_MAX_LEN) -> None:
        if inputs not in ("plain", "lookup", "pointer"):
            raise ValueError(f"unknown inputs {inputs!r}")
        if inputs == "lookup" and bm25 is None:
            raise ValueError("the lookup scorer needs the BM25 table")
        if inputs == "pointer" and detector is None:
            raise ValueError("the pointer scorer needs the name detector")
        self.regime = preprocess.regime_of(labels, regime)
        if self.regime == preprocess.GOLD_EVIDENCE:
            raise ValueError("gold-evidence inputs are built by the solvability diagnostic, not this scorer")
        self.labels = self.regime == WITH_LABELS
        self.inputs, self.bm25, self.detector, self.max_len = inputs, bm25, detector, max_len
        self.calls: list[dict[str, Any]] = []

    def __call__(self, model: nn.Module, tokenizer: Tokenizer, items: Sequence[EvalItem], *, max_new: int,
                 batch_size: int, plans: Optional[Mapping[str, Any]] = None) -> list[dict[str, Any]]:
        options = dict(max_new=max_new, batch_size=batch_size, plans=plans)
        info: dict[str, Any] = {"kind": self.inputs, "labels": self.labels, "regime": self.regime,
                                "max_len": self.max_len, "preprocess": preprocess.identity(self.regime)}
        if self.inputs == "pointer":
            rows = self._pointer(model, tokenizer, items, info, **options)
        else:
            lines = LineIds(tokenizer, regime=self.regime)
            if self.inputs == "plain":
                rebuilt = [replace(item, prompt=lookup.plain_input(item.question, lines, max_len=self.max_len)[0])
                           for item in items]
                info["prompts"] = "the regime's A window (lookup.plain_input)"
                info["equal_to_canonical"] = sum(new.prompt == old.prompt for new, old in zip(rebuilt, items))
            else:
                entries = [lookup.lookup_input(item.question, lines, self.bm25, max_len=self.max_len)
                           for item in items]
                rebuilt = [replace(item, prompt=entry.ids) for item, entry in zip(items, entries)]
                far = [entry for item, entry in zip(items, entries)
                       if item.question.knowable is True and item.evidence_kept is False]
                info["recall"] = lookup.recall_report(far)
                info["with_recall"] = sum(bool(e.recall.lines) for e in entries)
                info["gap_lines"] = sum(len(e.gap_lines) for e in entries)
                info["bm25_sha256"] = self.bm25.digest
            for item in rebuilt:
                preprocess.audit_ids(item.prompt, tokenizer, self.regime)
            info.update(_lengths([item.prompt for item in rebuilt]))
            rows = step1.score_items(model, tokenizer, rebuilt, **options)
        self.calls.append(info)
        return rows

    def _pointer(self, model: nn.Module, tokenizer: Tokenizer, items: Sequence[EvalItem], info: dict[str, Any], *,
                 max_new: int, batch_size: int, plans: Optional[Mapping[str, Any]]) -> list[dict[str, Any]]:
        cache: dict[str, list[int]] = {}
        inputs = [pointer_input(item.question, tokenizer, self.detector, max_len=self.max_len, regime=self.regime,
                                cache=cache) for item in items]
        for entry in inputs:
            preprocess.audit_ids(entry.ids, tokenizer, self.regime)
        stops, _ = step1.stop_ids(tokenizer)
        generated = step1.greedy_decode(model, [entry.ids for entry in inputs], max_new=max_new, stop=stops,
                                        batch_size=batch_size, pad_id=tokenizer.token_to_id("<pad>"))
        base = tokenizer.vocab_size
        rows = []
        unbound = entity_outputs = unknown = 0
        for item, entry, ids in zip(items, inputs, generated):
            text, wrong_entity = preprocess.prediction_text(ids, entry.table, tokenizer)
            rows.append(result_row(item, text, plans))
            names = self.detector.names(item.question.answer)
            unbound += any(name not in entry.table.spellings.values() for name in names)
            entity_outputs += any(i >= base for i in ids)
            unknown += wrong_entity
        info.update(_lengths([entry.ids for entry in inputs]), detector_sha256=self.detector.digest,
                    answers_with_unbound_name=unbound, predictions_with_entity=entity_outputs,
                    predictions_with_unbound_entity=unknown)
        return rows


def scorer_for(config: Mapping[str, Any], project: Union[str, Path], *, labels: Optional[bool] = None,
               regime: Optional[str] = None) -> ContenderScorer:
    """The scorer a checkpoint's config calls for (a config without "contender" is a step-1 A checkpoint)."""
    inputs = contender(config.get("contender", "A")).inputs
    regime = preprocess.regime_of(labels, regime)
    if inputs == "lookup":
        return ContenderScorer(inputs, regime=regime, bm25=Bm25.from_dict(config["lookup"]["bm25"]))
    if inputs == "pointer":
        return ContenderScorer(inputs, regime=regime, detector=load_detector(project, config))
    return ContenderScorer(inputs, regime=regime)


def evaluate_contender(project: Union[str, Path], checkpoint: Union[str, Path], *, split: str = "validation",
                       directories: Optional[Sequence[str]] = None, data_rel: Optional[str] = None,
                       tokenizer_path: Optional[str] = None, device: str = "cpu", max_new: int = MAX_NEW,
                       batch_size: int = 64, replay: bool = True, workers: int = 1, heldin: int = 0,
                       names: Optional[Iterable[str]] = None, seed: int = 0, labels: Optional[bool] = None,
                       regime: Optional[str] = None, purpose: Optional[str] = None,
                       contender_name: Optional[str] = None, log: Log = print) -> dict[str, Any]:
    """`exp1.evaluate_checkpoint` for any contender checkpoint, with its own inputs (see the module doc).

    The contender is the checkpoint's own ("A" for a step-1 checkpoint) unless `contender_name` says
    otherwise (a step-1 28M checkpoint scored as "B28"). The report has exp1's layout (so `exp1.verdict`,
    `format_report` and `save_report` take it) plus "inputs": the scorer's settings and, per directory,
    its diagnostics (C: gold recall@8 on far questions). The regime is label-free unless `regime` (or the
    older `labels=True`) says "with-labels", a diagnostic that never enters a verdict. `purpose` (default:
    "primary" for label-free) selects the checkpoint checks that must pass (`identity.admit`); the
    tokenizer digest is checked even when `tokenizer_path` overrides the path.
    """
    regime = preprocess.regime_of(labels, regime)
    purpose = exp1.default_purpose(regime, purpose)
    project = Path(project)
    path = Path(checkpoint) if Path(checkpoint).is_absolute() else project / checkpoint
    from learnlab.ckpt import read_config

    config = read_config(path)
    name = contender_name or config.get("contender", "A")
    if contender(name).inputs != contender(config.get("contender", "A")).inputs:
        raise ValueError(f"a {config.get('contender', 'A')} checkpoint cannot be scored with {name}'s inputs")
    tokenizer_info = config.get("tokenizer") or {}
    if tokenizer_path is None and not tokenizer_info.get("path"):
        raise identity.CheckpointIncompatible(f"{checkpoint} records no tokenizer path; pass tokenizer_path")
    data = exp1.open_data(project, data_rel or config["data"]["dir"], tokenizer_path or tokenizer_info["path"])
    spec = contender(name)
    problems = identity.admit(
        exp1.core_checks(config, data.tokenizer, name, entity_ids=spec.inputs == "pointer", inputs=spec.inputs),
        data.tokenizer, regime=regime, purpose=purpose)
    model, config = exp1.load_core(path, device)
    scorer = scorer_for(config, project, regime=regime)
    if directories is None:
        directories = [split] + ([slices.long_name(split)] if data.has(slices.long_name(split)) else [])
    names = None if names is None else list(names)
    reports: dict[str, Any] = {}
    items: dict[str, list[dict[str, Any]]] = {}
    diagnostics: dict[str, Any] = {}
    fresh: list[Mapping[str, Any]] = []
    for directory in directories:
        rows, info = exp1.evaluate_directory(model, data, directory, max_new=max_new, batch_size=batch_size,
                                             replay=replay, workers=workers, names=names, scorer=scorer,
                                             regime=regime, log=log)
        reports[directory] = info
        diagnostics[directory] = scorer.calls.pop()
        items[directory] = [{key: row[key] for key in exp1._ITEM_KEYS} for row in rows]
        if directory == split:
            fresh = [r for r in rows if "fresh_names" in r["slices"]]
        cell = info["summary"]["decision_cells"]
        log(f"premonition exp1 {name} [{regime}] {directory}: " + ", ".join(
            f"{slice_name} {exp1._pct(cell[slice_name])}" for slice_name in slices.DECISION_SLICES))
        recall = diagnostics[directory].get("recall")
        if recall:
            log(f"premonition exp1 {name} {directory}: gold recall@8 on far questions "
                f"{recall['recall_at_8']} ({recall['targets']} targets, {recall['far_questions']} questions)")
    name_gap: dict[str, Any] = {"fresh_names": exp1._cell(fresh)}
    if heldin > 0:
        rows, info = exp1.evaluate_directory(model, data, "train", max_new=max_new, batch_size=batch_size,
                                             replay=False, names=names,
                                             questions=exp1.heldin_questions(data, heldin, seed),
                                             source=exp1.HELDIN_SOURCE, scorer=scorer, regime=regime, log=log)
        reports[exp1.HELDIN_SOURCE] = info
        diagnostics[exp1.HELDIN_SOURCE] = scorer.calls.pop()
        seen = [r for r in rows if "seen_names" in r["slices"]]
        name_gap["seen_names"] = exp1._cell(seen)
        if seen and fresh:
            name_gap["gap"] = name_gap["seen_names"]["accuracy"] - name_gap["fresh_names"]["accuracy"]
    return {
        "command": "premonition eval", "experiment": 1, "contender": name, "wipe": None, "regime": regime,
        "identity": identity.report_identity(
            regime=regime, purpose=purpose, tokenizer=data.tokenizer, tokenizer_path=data.tokenizer_path,
            model_kind="core", model_config=config.get("core") or {}, parameters=model.num_parameters(),
            checkpoint=path, checkpoint_config=config, data_tag=data.tag, problems=problems),
        "checkpoint": str(checkpoint), "parameters": model.num_parameters(), "device": device,
        "config": config, "data": {"dir": data.rel, "tag": data.tag},
        "tokenizer": {"path": data.tokenizer_path, "sha256": data.tokenizer.digest},
        "cut": {"seq_len": slices.SEQ_LEN, "max_new": max_new, "max_len": CUT_MAX_LEN},
        "inputs": {"kind": scorer.inputs, "labels": scorer.labels, "regime": regime,
                   "per_directory": diagnostics},
        "split": split, "directories": reports, "name_gap": name_gap, "items": items,
    }


# ----------------------------------------------------------------- training


def _stream(name: str, budget: Any, data: Any, *, batch: int, seq_len: int, seed: int, workers: int,
            log: Log) -> tuple[Iterator[Any], Callable[[], dict[str, Any]], Callable[[], None], dict[str, Any]]:
    """(stream, summary(), close(), checkpoint-config additions) for the contender's inputs."""
    inputs = contender(name).inputs
    tokenizer: Tokenizer = data.tokenizer
    if inputs == "plain":
        stream = step1.stream_for(data, chunk=batch * seq_len, seed=seed)
        return stream, lambda: {"kind": "plain", "epochs": stream.epochs(stream.yielded),
                                "stall_seconds": stream.stall_seconds}, lambda: None, {}
    if inputs == "lookup":
        if seq_len != SEQ_LEN:
            raise ValueError(f"C's rows are {SEQ_LEN} tokens (design/06 §5), not {seq_len}")
        bm25 = lookup.train_bm25(budget, data.rel, log=log)
        stream = lookup.LookupStream(data, bm25, seed=seed, seq_len=seq_len, max_len=CUT_MAX_LEN, workers=workers)
        extra = {"lookup": {"bm25": bm25.to_dict(), "top_k": lookup.TOP_K, "recall_tokens": lookup.RECALL_TOKENS,
                            "separator": lookup.SEPARATOR, "max_len": CUT_MAX_LEN}}
        return stream, lambda: {"kind": "lookup", **stream.summary()}, stream.close, extra
    from premonition import data as pdata

    detector = pdata.name_detector(budget, data.rel, workers=max(1, workers), log=log)
    cache = pdata.load_or_build(budget, data.rel, "train", tokenizer, detector, split="train",
                                workers=max(1, workers), log=log)
    stream = PointerStream(cache, tokenizer.token_to_id("<eos>"), seed=seed)
    extra = {"pointer": {"detector": f"{data.rel}/{pdata.DETECTOR_FILE}", "sha256": detector.digest,
                         "entities": N_ENT, "cache": pdata.cache_relative(data.rel, "train", tokenizer, detector),
                         "cache_stats": cache.info.get("stats", {})}}
    return stream, lambda: {"kind": "pointer", **stream.summary()}, lambda: None, extra


def train_contender(budget: Any, data: Any, name: str, *, flops_budget: Optional[float] = None,
                    tokens_budget: Optional[float] = None, device: str = "cpu", batch: int = 32,
                    seq_len: int = SEQ_LEN, lr: Optional[float] = None, warmup: Optional[int] = None, seed: int = 0,
                    size: Optional[str] = None, workers: int = 0, max_seconds: Optional[float] = None,
                    log_every: int = 50, save: bool = True, environment: Optional[dict[str, Any]] = None,
                    log: Log = print, on_log: Optional[Callable[[dict[str, Any]], None]] = None) -> dict[str, Any]:
    """Train contender `name` ("A", "B12", "B28", "C", "E") on `data` (a `step1.StepData`) to a budget.

    Give `flops_budget` (F, design/06 §4) or `tokens_budget` (T, the token-matched runs of §9.7). The run
    takes the whole number of steps nearest the budget (BudgetError before training if that misses by
    more than `policy.BUDGET_TOLERANCE`); `max_seconds` is only a safety stop (the report then says the
    budget was not met). Saves `artifacts/premonition-exp1-<name>-<ns>-<pid>.ckpt` and `.json` (the
    report) through `budget` when `save`. Evaluate the checkpoint with `evaluate_contender`.
    """
    spec = contender(name)
    tokenizer: Tokenizer = data.tokenizer
    config = core_config(name, tokenizer.vocab_size, context=seq_len, size=size)
    per_step = step_flops(config, batch, seq_len)
    plan = plan_budget(per_step, batch * seq_len, flops_budget=flops_budget, tokens_budget=tokens_budget)
    lr = lr if lr is not None else spec.lr
    warmup = warmup if warmup is not None else (100 if device == "cuda" else 10)
    train_config = TrainConfig(batch=batch, seq_len=seq_len, lr=lr, warmup_steps=warmup, log_every=log_every)
    torch.manual_seed(seed)
    model = Core(config)
    trainer = Trainer(model, train_config, device)
    log(f"premonition train {name}: {model.num_parameters():,} params, {per_step / (batch * seq_len) / 1e6:.2f} "
        f"MFLOP/token counted, {plan.steps:,} steps of {batch}x{seq_len} for the {plan.kind} budget "
        f"{plan.target:.4g} ({plan.flops:.4g} FLOPs, {plan.tokens:,} tokens)")
    stream, summary, close, extra = _stream(name, budget, data, batch=batch, seq_len=seq_len, seed=seed,
                                            workers=workers, log=log)
    started = time.perf_counter()

    def logged(record: dict[str, Any]) -> None:
        record["flops"] = record["step"] * per_step
        record["budget_fraction"] = record["step"] / plan.steps
        record["elapsed"] = time.perf_counter() - started
        if on_log is not None:
            on_log(record)

    status, error = "completed", None
    result: dict[str, Any] = {}
    try:
        result = trainer.train(stream, max_tokens=plan.tokens, max_seconds=max_seconds, on_log=logged)
    except MemoryGuardError as guard:
        status, error = "aborted", str(guard)
        result = {"steps": trainer.step, "tokens": trainer.tokens, "peak_gpu_reserved_bytes": guard.peak,
                  "stop": "memory guard", "seconds": time.perf_counter() - started}
    finally:
        close()
    achieved = trainer.step * per_step
    relative = plan.error(trainer.step)
    within = abs(relative) <= plan.tolerance
    if status == "completed" and not within:
        status = "budget not met"
    hand = flops.core_flops_per_token(config, seq_len)
    flop_info = {
        "convention": "premonition.flops (FlopCounterMode, dense attention, backward recompute)",
        "per_step": per_step, "per_token": per_step / (batch * seq_len), "hand_per_token": hand,
        "counter_over_hand": per_step / (batch * seq_len) / hand,
        "spec_formula_per_token": flops.spec_core_flops_per_token(
            config, sum(p.numel() for p in model.blocks.parameters()), seq_len),
        "budget_kind": plan.kind, "target": plan.target, "planned_steps": plan.steps, "achieved": achieved,
        "relative_error": relative, "tolerance": plan.tolerance, "within_tolerance": within,
    }
    seconds = float(result.get("seconds") or time.perf_counter() - started)
    train_info = {**result, "flops": achieved, "flops_per_second": achieved / max(seconds, 1e-9)}
    ckpt_config = {
        "model": MODEL_NAME, "experiment": 1, "contender": name, "inputs": spec.inputs,
        "preprocess": preprocess.identity(WITH_LABELS),      # Core training streams keep answers (§9.1)
        "core": asdict(config), "train": asdict(train_config), "tokenizer": data.tokenizer_info,
        "data": {"dir": data.rel, "tag": data.tag}, "seed": seed, "max_new": MAX_NEW,
        "flops": {k: flop_info[k] for k in ("per_step", "per_token", "budget_kind", "target", "achieved")},
        **extra,
    }
    report: dict[str, Any] = {
        "command": "premonition train", "experiment": 1, "contender": name, "status": status, "error": error,
        "parameters": model.num_parameters(), "device": device, "size": size,
        "config": ckpt_config, "flops": flop_info, "train": train_info, "stream": summary(),
        "history": trainer.history, "environment": environment,
    }
    if save:
        stem = f"artifacts/{MODEL_NAME}-{name}-{time.time_ns()}-{os.getpid()}"
        if status != "aborted":
            from learnlab.ckpt import save_checkpoint

            save_checkpoint(budget, stem + ".ckpt", model=trainer.model, config=ckpt_config,
                            optimizer=trainer.optimizer, trainer_state=trainer.state_dict())
            report["checkpoint"] = stem + ".ckpt"
        report["artifact"] = stem + ".json"
        budget.save_json(report["artifact"], exp1.jsonable(report), 60_000_000)
    log(f"premonition train {name}: {status}; {trainer.step:,} steps, {trainer.tokens:,} tokens, "
        f"{achieved:.4g} FLOPs ({relative:+.2%} of the budget) in {seconds:.1f}s")
    return report


__all__ = [
    "BudgetError", "BudgetPlan", "CONTENDERS", "Contender", "ContenderScorer", "MODEL_NAME", "PointerInput",
    "PointerStream", "budget_from_report", "contender", "core_config", "entity_answer", "evaluate_contender",
    "load_detector", "plan_budget", "pointer_input", "result_row", "scorer_for", "step_flops", "train_contender",
]
