"""Experiment 1 evaluation and verdict (design/06 §6): every contender scored on the same questions.

Build step 1 covers `learnlab.core.Core` checkpoints (A, B12, B28; E once its text is pointerized):

1. Data. `open_data` opens an existing step-1 data build read-only (it never generates): the
   split directories, the tokenizer (checked against the checkpoint's digest) and the train
   split's seen templates, styles and rule families.
2. Items and tags. ALL questions of a directory (validation for development, test once for the
   verdict; `<split>-long` for far-long) are cut at A's window (`slices.CUT_MAX_LEN`) and tagged
   by `slices.tag_questions`; village directories are replayed first for the changed tag, and a
   directory without an oracle index (far-long) takes its repeat signatures and plan worlds from
   that replay.
3. Scoring. Step 1's `score_items` (greedy decoding, exact match, plans acted out) inside
   `readonly.read_only`, so any state change is a `ReadOnlyViolation`.
4. Report. Per-slice cells with Wilson intervals, per depth, stale answers, the exclusions
   (repeats, leak-flagged classes) apart, the step-1-comparable visible cell, and every item's
   correctness keyed by question id so contenders can be paired later.
5. Verdict. `decide` applies the §6 table as a pure function of per-item correctness and the
   decision slices; `verdict` feeds it from saved reports.

Inputs and identity (design/06 §9.1, §9.8, §11). Evaluation is label-free by default: A's canonical
prompts and the near/far cut are built over `premonition.preprocess.visible_line` (no earlier answer or
feedback), and every input is audited for it. "with-labels" is a reported diagnostic. Every report records
its regime and an identity block (`premonition.identity.report_identity`: preprocessing digest, tokenizer,
model and checkpoint digests, purpose, and whether it is primary). A checkpoint is scored only after the
fail-closed checks of `premonition.identity` (tokenizer digest always checked, even with an override path;
vocabulary, model configuration, preprocessing). `verdict` refuses mixed regimes, reports without a regime
(legacy/unknown), with-labels or gold-evidence reports and non-primary reports; its outcome is the §6
decision table on label-free items, not a full §9/§10 verdict (`identity.SCOPE`).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence, Union

import torch
from torch import nn

from learnlab import step1
from learnlab.ckpt import load_checkpoint, read_config
from learnlab.core import Core, CoreConfig
from learnlab.metrics import paired_greater_pvalue
from learnlab.policy import ALPHA, MIN_EFFECT, MIN_ITEMS
from learnlab.readonly import read_only
from learnlab.step1 import ANSWER_TAG, EvalItem, Question
from learnlab.tokenizer import Tokenizer

from premonition import identity, preprocess, slices
from premonition.identity import CheckpointIncompatible, VerdictRefused
from premonition.preprocess import LABEL_FREE, WITH_LABELS
from premonition.slices import CUT_MAX_LEN, DECISION_SLICES, MAX_NEW, SliceTags

TARGET_ITEMS = 400                  # design/06 §6 item 2: the target per decision cell (MIN_ITEMS is the floor)
LEAD = 0.10                         # Pass 2: D must lead each baseline by at least this much
WIPE_NEAR_SHARE = 0.9               # Pass 4: W-full near accuracy >= this share of D's unwiped near
PASS2_SLICES = ("far", "multi_hop")
PASS2_BASELINES = ("A", "C", "E")
B_CONTENDERS = ("B12", "B28")
WIPE_FULL = "D/W-full"              # results key of D evaluated with the W-full wipe
CONTENDERS = ("A", "B12", "B28", "C", "D", "D-noask", "D-noptr", "E")
HELDIN_SOURCE = "train-heldin"

Log = Callable[[str], None]
Scorer = Callable[..., list[dict[str, Any]]]


# ----------------------------------------------------------------- data


@dataclass
class EvalData:
    """An existing step-1 data build, opened read-only."""

    root: Path                          # absolute data directory (<project>/<rel>)
    rel: str
    tokenizer: Tokenizer
    tokenizer_path: str
    seen: dict[str, set[str]]           # train templates, styles and rule families
    _oracle: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def tag(self) -> str:
        return Path(self.rel).name

    def split_dir(self, directory: str) -> Path:
        return self.root / directory

    def has(self, directory: str) -> bool:
        return (self.split_dir(directory) / "COMPLETE.json").is_file()

    def oracle(self, directory: str) -> tuple[dict[str, str], dict[str, tuple[Any, str, str]], list[str]]:
        found = self._oracle.get(directory)
        if found is None:
            found = self._oracle[directory] = step1.load_oracle(self.split_dir(directory))
        return found


def open_data(project: Union[str, Path], data_rel: str, tokenizer_path: str, *,
              tokenizer_sha: Optional[str] = None) -> EvalData:
    """Open `<project>/<data_rel>` (a finished step-1 build) and its tokenizer; never writes."""
    project = Path(project)
    root = project / data_rel
    marker = root / "train" / "COMPLETE.json"
    if not marker.is_file():
        raise FileNotFoundError(f"{marker} is missing: {data_rel} is not a finished step-1 data build")
    train = json.loads(marker.read_text(encoding="utf-8"))
    tokenizer = Tokenizer.load(project / tokenizer_path)
    if tokenizer_sha is not None and tokenizer.digest != tokenizer_sha:
        raise ValueError(f"{tokenizer_path} has sha256 {tokenizer.digest[:12]}, the checkpoint was trained with "
                         f"{tokenizer_sha[:12]}")
    seen = {"templates": set(train.get("templates", ())), "styles": set(train.get("styles", ())),
            "rule_families": set(train.get("rule_families", ()))}
    return EvalData(root=root, rel=data_rel, tokenizer=tokenizer, tokenizer_path=tokenizer_path, seen=seen)


def split_of(directory: str) -> str:
    """"validation-long" -> "validation"; "test" -> "test"."""
    return directory.split("-")[0]


def split_questions(data: EvalData, directory: str, split: Optional[str] = None,
                    signatures: Optional[Mapping[str, str]] = None) -> list[Question]:
    """Every question of a directory, with repeat signatures (default: its oracle index)."""
    split = split or split_of(directory)
    if signatures is None:
        signatures = data.oracle(directory)[0]
    out: list[Question] = []
    for text, meta in step1.shard_files(data.split_dir(directory)):
        out.extend(step1.read_questions(text, meta, split, signatures))
    return out


def _probe_visits(data: EvalData) -> int:
    manifest = data.root / f"tokens-{data.tokenizer.digest[:16]}" / "MANIFEST.json"
    if not manifest.is_file():
        return 0
    return sum(entry["visits"] for entry in json.loads(manifest.read_text(encoding="utf-8"))["probe_files"])


def heldin_questions(data: EvalData, limit: int, seed: int = 0) -> list[Question]:
    """A deterministic sample of trained-on questions (probe visits left out), as step 1 draws them."""
    if limit <= 0:
        return []
    signatures, _, indexed = data.oracle("train")
    files = step1.shard_files(data.split_dir("train"))
    if indexed:
        files = [pair for pair in files if pair[0].stem in indexed] or files[:1]
    probe = _probe_visits(data)
    out: list[Question] = []
    for index, (text, meta) in enumerate(files):
        out.extend(q for q in step1.read_questions(text, meta, "train", signatures) if index > 0 or q.visit >= probe)
        if len(out) >= 3 * limit:
            break
    return step1.sample_questions(out, limit, seed)


# ----------------------------------------------------------------- model and scoring


def load_core(checkpoint: Union[str, Path], device: str = "cpu") -> tuple[Core, dict[str, Any]]:
    """A `Core` rebuilt from a step-1 style checkpoint (config["core"]), in eval mode, RNG untouched."""
    config = read_config(checkpoint)
    model = Core(CoreConfig(**config["core"]))
    load_checkpoint(checkpoint, model, map_location=device, restore_rng=False)
    return model.to(device).eval(), config


def audit_items(tokenizer: Tokenizer, items: Sequence[EvalItem], *, max_len: int = CUT_MAX_LEN,
                regime: str = LABEL_FREE) -> dict[str, int]:
    """Every input ends with its own question line cut just after [answer] and fits A's cut.

    Nothing of the gold answer follows [answer]; an input that already shows the answer (a
    repeat) is counted here and kept out of the decision cells by its tags. Label-free inputs
    also hold no [feedback] and no text after any earlier [answer] (`preprocess.audit_ids`).
    """
    answer_id = tokenizer.token_to_id(ANSWER_TAG)
    for item in items:
        tail = tokenizer.encode(item.question.prompt_line)
        if item.prompt[-1] != answer_id or item.prompt[-len(tail):] != tail or len(item.prompt) > max_len:
            raise AssertionError(f"evaluation input for {item.question.id} does not end with its own question "
                                 f"line cut at {ANSWER_TAG} within {max_len} tokens")
        preprocess.audit_ids(item.prompt, tokenizer, regime)
    return {"inputs": len(items), "regime": regime,
            "answer_already_in_input": sum(item.repeat_in_context for item in items),
            "truncated": sum(item.truncated for item in items)}


def score_read_only(model: nn.Module, tokenizer: Tokenizer, items: Sequence[EvalItem], *, max_new: int = MAX_NEW,
                    batch_size: int = 64, plans: Optional[Mapping[str, tuple[Any, str, str]]] = None,
                    scorer: Scorer = step1.score_items) -> list[dict[str, Any]]:
    """`scorer` (step 1's `score_items`) under `read_only`: any state change raises ReadOnlyViolation."""
    context = getattr(getattr(model, "config", None), "context", None)
    longest = max((len(item.prompt) for item in items), default=0)
    if context is not None and longest + max_new > context:
        raise ValueError(f"inputs of {longest} tokens + {max_new} new exceed the model's context {context}")
    with torch.no_grad(), read_only(model):
        return scorer(model, tokenizer, items, max_new=max_new, batch_size=batch_size, plans=plans)


def attach(results: Sequence[Mapping[str, Any]], tags: Mapping[str, SliceTags]) -> list[dict[str, Any]]:
    """Scored results with their tags: source, slices, decision flag, exclusions, changed and stale."""
    rows = []
    for result in results:
        tag = tags[result["id"]]
        rows.append({**result, "source": tag.source, "bank": tag.bank, "slices": list(tag.slices()),
                     "decision": tag.decision, "exclusions": list(tag.exclusions), "changed": tag.changed,
                     "older_answers": list(tag.older_answers), "names": list(tag.names),
                     "stale": slices.is_stale(tag, str(result.get("prediction", "")))})
    return rows


# ----------------------------------------------------------------- report


def _cell(rows: Sequence[Mapping[str, Any]], *, min_items: int = MIN_ITEMS,
          target: int = TARGET_ITEMS) -> dict[str, Any]:
    n = len(rows)
    return {**step1.cell(sum(bool(r["correct"]) for r in rows), n), "enough": n >= min_items,
            "target_met": n >= target}


def slice_report(rows: Sequence[Mapping[str, Any]], *, min_items: int = MIN_ITEMS,
                 target: int = TARGET_ITEMS) -> dict[str, Any]:
    """Cells (accuracy, Wilson 95%, n) for every slice of one directory's tagged rows."""
    members: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        for name in row["slices"]:
            members[name].append(row)
    cells = {name: _cell(chosen, min_items=min_items, target=target) for name, chosen in sorted(members.items())}
    empty = _cell([], min_items=min_items, target=target)
    decision = {name: cells.get(name, empty) for name in DECISION_SLICES}
    changed = [r for r in rows if r["decision"] and r.get("changed") is True]
    stale = sum(bool(r["stale"]) for r in changed)
    gated = step1.gated(rows)
    visible = [r for r in gated if r["visible"]]
    return {
        "items": len(rows),
        "decision_items": sum(bool(r["decision"]) for r in rows),
        "decision_cells": decision,
        "decision_cells_ok": all(cell["enough"] for cell in decision.values()),
        "cells": cells,
        "per_depth": {str(d): cells.get(f"depth_{d}", empty) for d in slices.DEPTHS},
        "stale": {**step1.cell(stale, len(changed)),
                  "note": "accuracy here = share of changed decision items answered with an older answer"},
        "changed_unknown": sum(bool(r["decision"]) and r.get("changed") is None for r in rows),
        "excluded": {name.split(":", 1)[1]: cells[name] for name in cells if name.startswith("excluded:")},
        "step1_comparable": {**step1.cell(sum(bool(r["correct"]) for r in visible), len(visible)),
                             "note": "step 1's headline: visible questions minus repeats under A's cut"},
        "step1_summary": step1.summarize(gated),
    }


def evaluate_directory(model: nn.Module, data: EvalData, directory: str, *, max_new: int = MAX_NEW,
                       batch_size: int = 64, replay: bool = True, workers: int = 1,
                       names: Optional[Iterable[str]] = None, questions: Optional[Sequence[Question]] = None,
                       source: Optional[str] = None, scorer: Scorer = step1.score_items,
                       regime: str = LABEL_FREE, log: Log = print) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """(tagged rows, directory report) for every question of `directory`, items cut in `regime`.

    Given `questions` (a sample of the directory's), those are scored instead and nothing is
    replayed; `source` names the item set in the tags (default: the directory). The scorer
    receives A's canonical items of the regime (label-free prompts by default).
    """
    started = time.perf_counter()
    split = split_of(directory)
    source = source or directory
    signatures, plans, _ = data.oracle(directory)
    replays, replay_info = None, {"replayed": False, "generator": None}
    if replay and questions is None:
        generator = slices.shard_generator(data.split_dir(directory))
        replay_info["generator"] = generator
        if generator in slices.GENERATOR_DAYS:
            replays = slices.replay_split(data.split_dir(directory), split, days=slices.GENERATOR_DAYS[generator],
                                          workers=workers, log=log)
            replay_info.update(replayed=True, questions=len(replays),
                               changed=sum(r.changed for r in replays.values()),
                               ask_errors=sum(r.errors for r in replays.values()))
            if not signatures:      # far-long has no oracle index: its replay gives the exact signatures
                signatures = {qid: r.signature for qid, r in replays.items()}
            if not plans:
                plans = {qid: r.plan for qid, r in replays.items() if r.plan is not None}
    if questions is None:
        questions = split_questions(data, directory, split, signatures)
    items, tags = slices.tag_questions(data.tokenizer, questions, seen=data.seen, source=source,
                                       replays=replays, names=names, regime=regime)
    audit = audit_items(data.tokenizer, items, regime=regime)
    results = score_read_only(model, data.tokenizer, items, max_new=max_new, batch_size=batch_size,
                              plans=plans, scorer=scorer)
    rows = attach(results, tags)
    info = {"directory": directory, "source": source, "split": split, "regime": regime,
            "signatures": "oracle" if signatures else "text",
            "plan_worlds": len(plans), "replay": replay_info, "input_audit": audit,
            "summary": slice_report(rows), "seconds": time.perf_counter() - started}
    return rows, info


_ITEM_KEYS = ("id", "correct", "exact", "prediction", "answer", "decision", "slices", "stale")


def default_purpose(regime: str, purpose: Optional[str]) -> str:
    """Primary for label-free scoring unless said otherwise; with-labels and gold-evidence are diagnostics."""
    if purpose is not None:
        return identity.check_purpose(purpose)
    return "primary" if regime in preprocess.VERDICT_REGIMES else "diagnostic"


def core_checks(config: Mapping[str, Any], tokenizer: Tokenizer, contender: str, *, entity_ids: bool = False,
                inputs: str = "plain") -> list[str]:
    """`identity.checkpoint_problems` for a `Core` checkpoint scored as `contender`."""
    from premonition import contenders
    core = config.get("core")
    problems: list[str] = []
    recorded_inputs = config.get("inputs", contenders.contender(config.get("contender", "A")).inputs)
    if recorded_inputs != inputs:
        problems.append(f"inputs: a checkpoint trained on {recorded_inputs} inputs cannot be scored with "
                        f"{inputs} inputs")
    expected = None
    if core is not None:
        spec = contenders.contender(contender)
        d_model, layers, heads = spec.shape
        expected = {"d_model": d_model, "n_layers": layers, "n_heads": heads, "context": slices.SEQ_LEN}
    return problems + identity.checkpoint_problems(
        config, tokenizer, model_vocab=None if core is None else int(core["vocab_size"]), entity_ids=entity_ids,
        expected_shape=expected, shape=core)


def evaluate_checkpoint(project: Union[str, Path], checkpoint: Union[str, Path], *, contender: str = "A",
                        split: str = "validation", directories: Optional[Sequence[str]] = None,
                        data_rel: Optional[str] = None, tokenizer_path: Optional[str] = None,
                        device: str = "cpu", max_new: int = MAX_NEW, batch_size: int = 64,
                        replay: bool = True, workers: int = 1, heldin: int = 0,
                        names: Optional[Iterable[str]] = None, seed: int = 0, regime: str = LABEL_FREE,
                        purpose: Optional[str] = None, log: Log = print) -> dict[str, Any]:
    """Score a plain-input `Core` checkpoint on every question of `split` (and `<split>-long` if built).

    Label-free by default (design/06 §9.1): A's canonical prompts over visible lines. `regime="with-labels"`
    is the older convention, a diagnostic. Data and tokenizer default to the ones recorded in the checkpoint's
    config; the tokenizer's digest must match the checkpoint's even when `tokenizer_path` overrides the path.
    `purpose` (default: "primary" for label-free) decides which checks may fail (`identity.admit`);
    CheckpointIncompatible is raised before any scoring otherwise. `heldin` > 0 also scores that many
    trained-on questions for the seen-name side of the name gap.
    """
    preprocess.check_regime(regime)
    purpose = default_purpose(regime, purpose)
    project = Path(project)
    path = Path(checkpoint) if Path(checkpoint).is_absolute() else project / checkpoint
    config = read_config(path)
    tokenizer_info = config.get("tokenizer") or {}
    if tokenizer_path is None and not tokenizer_info.get("path"):
        raise CheckpointIncompatible(f"{checkpoint} records no tokenizer path; pass tokenizer_path")
    data = open_data(project, data_rel or config["data"]["dir"], tokenizer_path or tokenizer_info["path"])
    problems = identity.admit(core_checks(config, data.tokenizer, contender), data.tokenizer, regime=regime,
                              purpose=purpose)
    model, config = load_core(path, device)
    if directories is None:
        directories = [split] + ([slices.long_name(split)] if data.has(slices.long_name(split)) else [])
    names = None if names is None else list(names)
    reports: dict[str, Any] = {}
    items: dict[str, list[dict[str, Any]]] = {}
    fresh: list[Mapping[str, Any]] = []
    for directory in directories:
        rows, info = evaluate_directory(model, data, directory, max_new=max_new, batch_size=batch_size,
                                        replay=replay, workers=workers, names=names, regime=regime, log=log)
        reports[directory] = info
        items[directory] = [{key: row[key] for key in _ITEM_KEYS} for row in rows]
        if directory == split:
            fresh = [r for r in rows if "fresh_names" in r["slices"]]
        cell = info["summary"]["decision_cells"]
        log(f"premonition exp1 {contender} [{regime}] {directory}: " + ", ".join(
            f"{name} {_pct(cell[name])}" for name in DECISION_SLICES))
    name_gap: dict[str, Any] = {"fresh_names": _cell(fresh)}
    if heldin > 0:
        rows, info = evaluate_directory(model, data, "train", max_new=max_new, batch_size=batch_size,
                                        replay=False, names=names, questions=heldin_questions(data, heldin, seed),
                                        source=HELDIN_SOURCE, regime=regime, log=log)
        reports[HELDIN_SOURCE] = info
        seen = [r for r in rows if "seen_names" in r["slices"]]
        name_gap["seen_names"] = _cell(seen)
        if seen and fresh:
            name_gap["gap"] = name_gap["seen_names"]["accuracy"] - name_gap["fresh_names"]["accuracy"]
    return {
        "command": "premonition eval", "experiment": 1, "contender": contender, "wipe": None, "regime": regime,
        "identity": identity.report_identity(
            regime=regime, purpose=purpose, tokenizer=data.tokenizer, tokenizer_path=data.tokenizer_path,
            model_kind="core", model_config=config.get("core") or {}, parameters=model.num_parameters(),
            checkpoint=path, checkpoint_config=config, data_tag=data.tag, problems=problems),
        "checkpoint": str(checkpoint), "parameters": model.num_parameters(), "device": device,
        "config": config, "data": {"dir": data.rel, "tag": data.tag},
        "tokenizer": {"path": data.tokenizer_path, "sha256": data.tokenizer.digest},
        "cut": {"seq_len": slices.SEQ_LEN, "max_new": max_new, "max_len": CUT_MAX_LEN},
        "split": split, "directories": reports, "name_gap": name_gap, "items": items,
    }


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted(jsonable(v) for v in value)
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return repr(value)


def save_report(budget: Any, report: Mapping[str, Any]) -> str:
    """Write the report under artifacts/ (never overwriting); returns its relative path."""
    wipe = f"-w{report['wipe']}" if report.get("wipe") else ""
    relative = (f"artifacts/premonition-exp1-{report['contender']}{wipe}-{report['split']}-"
                f"{time.time_ns()}-{os.getpid()}.json")
    budget.save_json(relative, jsonable(report), 60_000_000)
    return relative


def _pct(entry: Optional[Mapping[str, Any]]) -> str:
    if not entry or not entry.get("n"):
        return "n/a (n=0)"
    low, high = entry["wilson95"]
    return f"{entry['accuracy']:.1%} [{low:.1%}, {high:.1%}] n={entry['n']}"


def format_report(report: Mapping[str, Any]) -> str:
    """A readable summary of an evaluation report."""
    ident = report.get("identity") or {}
    lines = [f"PREMONITION exp1 eval: {report['contender']}{' W-' + report['wipe'] if report.get('wipe') else ''} "
             f"({report['parameters']:,} params) on {report['data']['tag']}, tokenizer "
             f"{report['tokenizer']['sha256'][:12]}, cut {report['cut']['max_len']}",
             f"regime {identity.report_regime(report)}, purpose {ident.get('purpose', 'unknown')}, "
             f"primary {ident.get('primary', False)}"
             + (f" ({'; '.join(ident['problems'])})" if ident.get("problems") else "")]
    for directory, info in report["directories"].items():
        summary = info["summary"]
        lines.append(f"{directory}: {summary['items']} items, {summary['decision_items']} in decisions "
                     f"(cells ok: {summary['decision_cells_ok']}); step-1 comparable "
                     f"{_pct(summary['step1_comparable'])}")
        for name in DECISION_SLICES:
            lines.append(f"  {name}: {_pct(summary['decision_cells'][name])}")
        for name in ("changed", "fresh_names", "reworded", "not_told", "far_long"):
            if name in summary["cells"]:
                lines.append(f"  {name}: {_pct(summary['cells'][name])}")
        lines.append("  depth: " + ", ".join(f"{d}={c['accuracy']:.0%}/{c['n']}"
                                             for d, c in summary["per_depth"].items() if c["n"]))
        lines.append(f"  stale: {summary['stale']['hits']}/{summary['stale']['n']} changed items")
        lines.append("  excluded: " + ", ".join(f"{k} {_pct(v)}" for k, v in summary["excluded"].items()))
    return "\n".join(lines)


# ----------------------------------------------------------------- paired decisions


def paired(a: Mapping[str, bool], b: Mapping[str, bool], ids: Optional[Iterable[str]] = None, *,
           margin: float = 0.0, alpha: float = ALPHA) -> dict[str, Any]:
    """Is contender `a` better than `b` + `margin` on the same question ids? (one-sided, paired)

    `a` and `b` map question id -> correct. Items are `ids` (default: all of `a`) that both scored.
    p comes from `metrics.paired_greater_pvalue` (exact McNemar at margin 0, else sign-flip permutation).
    The result's "a" and "b" are the two accuracies on those items; "a_only"/"b_only" the discordant counts.
    """
    chosen = set(a) if ids is None else set(ids)
    common = sorted(chosen & set(a) & set(b))
    out: dict[str, Any] = {"n": len(common), "margin": margin}
    if not common:
        return {**out, "a": None, "b": None, "difference": None, "p_value": None, "significant": False}
    xa = [float(bool(a[i])) for i in common]
    xb = [float(bool(b[i])) for i in common]
    p = paired_greater_pvalue(xa, xb, margin=margin)
    acc_a, acc_b = sum(xa) / len(xa), sum(xb) / len(xb)
    return {**out, "a": acc_a, "b": acc_b, "difference": acc_a - acc_b, "p_value": p, "significant": p < alpha,
            "a_only": sum(x > y for x, y in zip(xa, xb)), "b_only": sum(y > x for x, y in zip(xa, xb))}


def _members(slices_of: Mapping[str, Iterable[str]]) -> dict[str, set[str]]:
    members: dict[str, set[str]] = defaultdict(set)
    for qid, names in slices_of.items():
        for name in names:
            members[name].add(qid)
    return members


def _combine(statuses: Sequence[str]) -> str:
    if "FAIL" in statuses:
        return "FAIL"
    return "PASS" if statuses and all(s == "PASS" for s in statuses) else "INSUFFICIENT"


def decide(results: Mapping[str, Mapping[str, bool]], slices_of: Mapping[str, Iterable[str]], *,
           alpha: float = ALPHA, min_items: int = MIN_ITEMS, margin: float = MIN_EFFECT, lead: float = LEAD,
           wipe_share: float = WIPE_NEAR_SHARE) -> dict[str, Any]:
    """The design/06 §6 decision table, as a pure function.

    `results`: contender -> {question id -> correct}; keys "A", "B12", "B28", "C", "D", "E" and
    WIPE_FULL (D under the W-full wipe). `slices_of`: question id -> slice names for the decision
    items only (`slices.decision_slices`; "overall", "near", "far", "far_deep", "multi_hop").
    Every comparison is paired on the items of the slice that both contenders scored, and needs
    `min_items` of them. Pass 1: near, D >= A and not p(A > D + margin) < alpha. Pass 2: far and
    multi-hop separately, D leads A, C and E by >= `lead`, each with p(D > X + margin) < alpha.
    Pass 3: overall, the better B is not significantly above D + margin. Pass 4 (point estimates):
    W-full far <= A's far + margin, W-full near >= `wipe_share` x D's near. Kill: far with depth
    >= 2, D not significantly above C (margin 0). Verdict: KILL, else FAIL if any pass fails,
    PASS if all pass and the kill test ran, else INSUFFICIENT.
    """
    members = _members(slices_of)

    def items(name: str, *who: str) -> tuple[Optional[list[str]], Optional[str]]:
        missing = [w for w in who if w not in results]
        if missing:
            return None, f"no results for {', '.join(missing)}"
        common = members[name].intersection(*(set(results[w]) for w in who))
        if len(common) < max(1, min_items):
            return None, f"{name}: n={len(common)} < {min_items} items"
        return sorted(common), None

    def accuracy(who: str, ids: Sequence[str]) -> float:
        return sum(bool(results[who][i]) for i in ids) / len(ids)

    def compare(name: str, a: str, b: str, *, test_margin: float) -> dict[str, Any]:
        ids, why = items(name, a, b)
        if ids is None:
            return {"slice": name, "contender": a, "versus": b, "status": "INSUFFICIENT", "reason": why}
        return {"slice": name, "contender": a, "versus": b,
                **paired(results[a], results[b], ids, margin=test_margin, alpha=alpha)}

    passes = []
    # Pass 1 -- near: D is not worse than A.
    entry = compare("near", "A", "D", test_margin=margin)
    if "status" not in entry:
        ok = entry["b"] >= entry["a"] and entry["p_value"] >= alpha
        entry.update(status="PASS" if ok else "FAIL",
                     reason=f"D {entry['b']:.3f} vs A {entry['a']:.3f}; p(A > D + {margin}) = {entry['p_value']:.3g}")
    passes.append({"rule": "pass1_near", "what": "near: D >= A, and A not better by the margin",
                   "status": entry["status"], "reason": entry["reason"], "comparisons": [entry]})
    # Pass 2 -- far and multi-hop: D beats A, C and E by the lead, significantly at the margin.
    comparisons = []
    for name in PASS2_SLICES:
        for baseline in PASS2_BASELINES:
            entry = compare(name, "D", baseline, test_margin=margin)
            if "status" not in entry:
                ok = entry["difference"] >= lead and entry["p_value"] < alpha
                entry.update(status="PASS" if ok else "FAIL",
                             reason=f"{name}: D {entry['a']:.3f} vs {baseline} {entry['b']:.3f} "
                                    f"(lead {entry['difference']:+.3f}, needs {lead}); "
                                    f"p(D > {baseline} + {margin}) = {entry['p_value']:.3g}")
            comparisons.append(entry)
    status = _combine([c["status"] for c in comparisons])
    passes.append({"rule": "pass2_far_multi_hop", "what": f"far and multi-hop: D beats A, C, E by >= {lead}",
                   "status": status, "reason": "; ".join(c["reason"] for c in comparisons if c["status"] != "PASS")
                   or "all six comparisons pass", "comparisons": comparisons})
    # Pass 3 -- overall: the better B is not significantly better than D.
    present = [b for b in B_CONTENDERS if b in results]
    if not present:
        entry = {"slice": "overall", "contender": "B", "versus": "D", "status": "INSUFFICIENT",
                 "reason": "no results for B12 or B28"}
    else:
        def overall(b: str) -> float:
            ids = members["overall"] & set(results[b])
            return accuracy(b, sorted(ids)) if ids else -1.0

        better = max(present, key=overall)
        entry = compare("overall", better, "D", test_margin=margin)
        if "status" not in entry:
            ok = entry["p_value"] >= alpha
            entry.update(status="PASS" if ok else "FAIL",
                         reason=f"{better} {entry['a']:.3f} vs D {entry['b']:.3f}; "
                                f"p({better} > D + {margin}) = {entry['p_value']:.3g}")
        entry["better_b"] = better
    passes.append({"rule": "pass3_overall", "what": "overall: the better B not significantly better than D",
                   "status": entry["status"], "reason": entry["reason"], "comparisons": [entry]})
    # Pass 4 -- W-full: the wiped D loses its far advantage but keeps its near accuracy.
    checks = []
    ids, why = items("far", WIPE_FULL, "A")
    if ids is None:
        checks.append({"slice": "far", "status": "INSUFFICIENT", "reason": why})
    else:
        wiped, base = accuracy(WIPE_FULL, ids), accuracy("A", ids)
        checks.append({"slice": "far", "n": len(ids), "wiped": wiped, "A": base,
                       "status": "PASS" if wiped <= base + margin else "FAIL",
                       "reason": f"W-full far {wiped:.3f} vs A {base:.3f} + {margin}"})
    ids, why = items("near", WIPE_FULL, "D")
    if ids is None:
        checks.append({"slice": "near", "status": "INSUFFICIENT", "reason": why})
    else:
        wiped, whole = accuracy(WIPE_FULL, ids), accuracy("D", ids)
        checks.append({"slice": "near", "n": len(ids), "wiped": wiped, "D": whole,
                       "status": "PASS" if wiped >= wipe_share * whole else "FAIL",
                       "reason": f"W-full near {wiped:.3f} vs {wipe_share} x D's {whole:.3f}"})
    passes.append({"rule": "pass4_wipe_full", "what": "W-full: far <= A + margin, near >= 90% of unwiped D",
                   "status": _combine([c["status"] for c in checks]),
                   "reason": "; ".join(c["reason"] for c in checks), "comparisons": checks})
    # Kill -- far with depth >= 2: D not significantly above C.
    entry = compare("far_deep", "D", "C", test_margin=0.0)
    if "status" not in entry:
        killed = entry["p_value"] >= alpha
        entry.update(status="KILL" if killed else "SURVIVES",
                     reason=f"far depth>=2: D {entry['a']:.3f} vs C {entry['b']:.3f}; "
                            f"p(D > C) = {entry['p_value']:.3g}")
    kill = {"rule": "kill_far_deep", "what": "far with depth >= 2: D significantly above C",
            "status": entry["status"], "reason": entry["reason"], "comparisons": [entry]}
    statuses = [p["status"] for p in passes]
    if kill["status"] == "KILL":
        verdict = "KILL"
    elif "FAIL" in statuses:
        verdict = "FAIL"
    elif all(s == "PASS" for s in statuses) and kill["status"] == "SURVIVES":
        verdict = "PASS"
    else:
        verdict = "INSUFFICIENT"
    reasons = [f"{p['rule']}: {p['status']} ({p['reason']})" for p in [*passes, kill]
               if p["status"] not in ("PASS", "SURVIVES")]
    return {"verdict": verdict, "passes": passes, "kill": kill, "reasons": reasons,
            "settings": {"alpha": alpha, "min_items": min_items, "margin": margin, "lead": lead,
                         "wipe_share": wipe_share},
            "cells": {name: len(members[name]) for name in DECISION_SLICES}}


def results_key(report: Mapping[str, Any]) -> str:
    """The `decide` key of a report: its contender, or WIPE_FULL for D under the W-full wipe."""
    contender, wipe = report["contender"], report.get("wipe")
    if not wipe:
        return contender
    return WIPE_FULL if contender == "D" and wipe == "full" else f"{contender}/W-{wipe}"


def verdict(reports: Sequence[Mapping[str, Any]], *, directory: Optional[str] = None, allow_fixture: bool = False,
            **options: Any) -> dict[str, Any]:
    """`decide` over saved evaluation reports (all on the same split, data, tokenizer and regime).

    Refused (VerdictRefused) unless every report is a primary label-free report with today's preprocessing
    identity (`identity.verdict_problems`): mixed regimes, a report without a regime (legacy/unknown),
    with-labels or gold-evidence reports and non-primary reports never produce a verdict. With
    `allow_fixture`, reports that are ALL unit-test fixtures run the mechanics, marked as such. The outcome
    is the design/06 §6 decision table on label-free items, NOT a full §9/§10 verdict ("scope").
    """
    if not reports:
        raise ValueError("verdict needs at least one report")
    scope = identity.guard_verdict(reports, allow_fixture=allow_fixture)
    directory = directory or reports[0]["split"]
    digests = {r["tokenizer"]["sha256"] for r in reports}
    tags = {r["data"]["tag"] for r in reports}
    if len(digests) > 1 or len(tags) > 1:
        raise ValueError(f"reports differ in tokenizer {sorted(digests)} or data {sorted(tags)}; tags and pairs "
                         "need one of each")
    results: dict[str, dict[str, bool]] = {}
    slices_of: dict[str, list[str]] = {}
    for report in reports:
        rows = report["items"][directory]
        key = results_key(report)
        if key in results:
            raise ValueError(f"two reports for {key}")
        results[key] = {r["id"]: bool(r["correct"]) for r in rows}
        mine = {r["id"]: sorted(r["slices"]) for r in rows if r["decision"]}
        clash = [qid for qid in mine.keys() & slices_of.keys() if mine[qid] != slices_of[qid]]
        if clash:
            raise ValueError(f"{key}'s report tags {len(clash)} items differently (e.g. {clash[0]})")
        slices_of.update(mine)
    decision = decide(results, slices_of, **options)
    decision.update(directory=directory, contenders=sorted(results), **scope)
    return decision


__all__ = [
    "B_CONTENDERS", "CONTENDERS", "CheckpointIncompatible", "EvalData", "LEAD", "TARGET_ITEMS", "VerdictRefused",
    "WIPE_FULL", "WIPE_NEAR_SHARE", "attach", "audit_items", "core_checks", "decide", "default_purpose",
    "evaluate_checkpoint", "evaluate_directory", "format_report", "heldin_questions", "jsonable", "load_core",
    "open_data", "paired", "results_key", "save_report", "score_read_only", "slice_report", "split_of",
    "split_questions", "verdict",
]
