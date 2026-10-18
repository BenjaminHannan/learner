"""Span cards SC-1, Stage 1 (design/span-cards/02-run-card.md; booked by the coordinator after Stage 0).

One GPU box per seed s runs `box --seed s`, in this order (every result is printed as `S1 <kind> <i>/<n> <json chunk>`
lines of at most 450 characters, because the box's log is the only channel back and its API cuts lines at 500):

1. data: the standard step-1 village build (`learnlab.step1.build_data`, preset `--visits`, data seed 0), the name
   detector and the label-free v2 caches with the sealed tokenizer `premonition-tok-v2-fallback` (train,
   validation); their sha256 and N = `span_cards.tokens_per_line(train cache)` (the sealed addendum takes them).
2. memory pre-flight (the coordinator's Stage 1 condition): for each rung of `LADDER` (max_tokens, max_visits), a
   clean child process per arm (LINE, SPAN, and SPAN with 33% more cards than lines) trains gold, teacher and own
   steps (own tracked) on the heaviest batches of a Stage 1 epoch (by padded tokens, questions and lines), runs the
   validation hook and `card_economy`, and reports peak reserved GPU memory. A rung fits iff every child stays at
   or below the memory guard minus `MARGIN_GB`; the first fitting rung is proposed. No rung fits: the box stops.
3. go: the box waits for `stage1-go.json` (the public repo, `--go-url`; or `--go-file`) and runs only if it is a
   JSON object with `"go": true`, `seeds` listing this seed, and exactly this box's `script_sha256`, `code_sha256`
   (every module, `code_files`), `train_cache_sha256`, `validation_cache_sha256`, `N` and `flop_budget`, plus a
   rung `max_tokens`/`max_visits` on the ladder and no larger than the one this box measured as fitting. Anything
   else is logged as `go_refused` and waited on; `"go": false` with this script's hash and seed stops the box. The
   seal addendum is filed in the repo before the go file.
4. parent P_s: LINE from scratch, seed s, through the gold phase (the first 5% of F; F = 3.15e16), as `train_d`
   trains (calibration head of 4 batches, validation hook on 256 DEV visits every 1,000 steps).
5. branch-point check (run card §3): `span_stage0.branch_gate` on 64 DEV visits (strict on CPU, structural on GPU,
   `line_aligned == 1`). A failure stops the seed: the pairing is broken.
6. arms LINE and SPAN from P_s: each restores P_s's weights, optimizer state (SPAN: mapped by parameter name; the
   three gate weights start fresh), trainer state (step, FLOPs, generator) and the same data stream position, is
   charged by its own FLOP fit (calibrated on the same 4 head batches; RNG states restored afterwards), and trains
   to F. `card_economy` on 200 DEV visits at the branch and at the end.
7. readout per model (P_s, LINE, SPAN): the train report, DEV accuracy on the whole validation split (overall,
   near, far, multi_hop) with per-question correctness (for the paired G2 test), the card economy (G1, G3, G5,
   P3), and the checkpoint's path and sha256 (checkpoints stay on the box's disk; weights are never pushed).
`S1-DONE ok` (or `failed` after an `error` record) ends the log; usage errors exit 2 before it starts.
"""
from __future__ import annotations

import argparse
import base64
import copy
from dataclasses import asdict
import hashlib
import io
import itertools
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import time
import traceback
import types
from typing import Any, Iterator, Optional
import urllib.request

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from learnlab import ckpt, step1                                              # noqa: E402
from learnlab.step0 import jsonable                                           # noqa: E402
from learnlab.tokenizer import Tokenizer                                      # noqa: E402
from memorylab.storage import Budget                                          # noqa: E402
from premonition import data as pdata, preprocess, span_cards                 # noqa: E402
from premonition.config import MiniConfig                                     # noqa: E402
from premonition.model import PremonitionMini                                 # noqa: E402
from premonition.train import (MiniTrainer, Plan, _slice_tags_for, checkpoint_config, judge,  # noqa: E402
                               mini_train_config, planned_loops, save_mini_checkpoint, validation_hook)
from scripts import span_stage0                                               # noqa: E402

TOKENIZER = "data/tokenizer/premonition-tok-v2-fallback.json"   # the sealed tokenizer (run card §3)
F_BUDGET = 3.15e16                       # design/06 §4, the bid's F
LADDER = ((55_000, 48), (48_000, 42), (40_000, 35), (32_000, 28))   # rung 0 is the sealed recipe
MARGIN_GB = 1.0                          # a rung fits iff every peak reserved <= guard - MARGIN_GB
STRESS_EVERY = 33                        # SPAN stress: an extra cut every 33 tokens (about 1.33x the cards)
HEAD = 4                                 # calibration batches (train_d)
EVAL_VISITS, ECONOMY_VISITS, BRANCH_VISITS = 256, 200, 64
REQUIRED_SLICES = ("overall", "near", "far", "multi_hop")   # run card §5 (E2 DEV); each must hold questions
CHUNK = 450
CHILD_TIMEOUT = 1800                     # seconds for one pre-flight child (a hang is a fault, not a measurement)
STARTED = time.perf_counter()
CODE_PACKAGES = ("premonition", "learnlab", "memorylab")   # every .py file in these, plus the two scripts
CODE_SCRIPTS = ("scripts/span_stage0.py", "scripts/span_stage1.py")
RUN_ID = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


# ----------------------------------------------------------------------------- the log protocol
def emit(kind: str, record: Any) -> None:
    """One record as `S1 <kind> <i>/<n> <chunk>` lines, every line at most CHUNK + a short prefix."""
    text = json.dumps(jsonable({"t": round(time.perf_counter() - STARTED, 1), **record}), allow_nan=False,
                      separators=(",", ":"))
    parts = [text[i:i + CHUNK] for i in range(0, len(text), CHUNK)] or [""]
    for i, part in enumerate(parts):
        print(f"S1 {kind} {i + 1}/{len(parts)} {part}", flush=True)


def decode(lines: Iterator[str]) -> list[tuple[str, dict]]:
    """The records of a box log, in order: (kind, record). Incomplete records are skipped."""
    out, pending = [], {}
    for line in lines:
        if not line.startswith("S1 "):
            continue
        fields = line.rstrip("\n").split(" ", 3)
        if len(fields) < 4:
            continue                                      # a cut line: its record stays incomplete and is skipped
        _, kind, position, chunk = fields
        try:
            index, total = (int(x) for x in position.split("/"))
        except ValueError:
            continue
        if index == 1:
            pending[kind] = (total, [])
        if kind not in pending or pending[kind][0] != total or len(pending[kind][1]) != index - 1:
            pending.pop(kind, None)                       # a gap or another record's chunk: drop the record
            continue
        pending[kind][1].append(chunk)
        if index == total:
            try:
                out.append((kind, json.loads("".join(pending.pop(kind)[1]))))
            except ValueError:
                continue                                  # a garbled record is skipped, not fatal
    return out


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def bits(values: list[bool]) -> str:
    """Booleans packed 8 per byte, base64 (the per-question correctness of a DEV evaluation)."""
    packed = bytearray((len(values) + 7) // 8)
    for i, value in enumerate(values):
        if value:
            packed[i // 8] |= 1 << (i % 8)
    return base64.b64encode(bytes(packed)).decode()


def unbits(text: str, count: int) -> list[bool]:
    packed = base64.b64decode(text)
    return [bool(packed[i // 8] >> (i % 8) & 1) for i in range(count)]


# ----------------------------------------------------------------------------- data
def build(args: argparse.Namespace) -> dict:
    """The step-1 build and the label-free caches (idempotent: both are loaded when already on disk)."""
    budget = Budget(ROOT)
    log = lambda message: None                                         # noqa: E731 - the build's own log is long
    started = time.perf_counter()
    data = step1.build_data(budget, visits=args.visits, seed=0, workers=args.workers, log=log)
    tokenizer = Tokenizer.load(ROOT / TOKENIZER)
    detector = pdata.name_detector(budget, data.rel, workers=args.workers, log=log)
    caches, files = {}, {}
    for split in ("train", "validation"):
        caches[split] = pdata.load_or_build(budget, data.rel, split, tokenizer, detector, workers=args.workers,
                                            regime=preprocess.LABEL_FREE, log=log)
        files[split] = ROOT / pdata.cache_relative(data.rel, split, tokenizer, detector, preprocess.LABEL_FREE)
    return {"budget": budget, "data_rel": data.rel, "tag": data.tag, "tokenizer": tokenizer, "detector": detector,
            "caches": caches, "files": files, "seconds": time.perf_counter() - started}


def data_record(built: dict) -> dict:
    train = built["caches"]["train"]
    return {"data_rel": built["data_rel"], "tag": built["tag"], "seconds": round(built["seconds"], 1),
            "tokenizer_sha256": built["tokenizer"].digest, "detector_sha256": built["detector"].digest,
            "train_cache": {"file": str(built["files"]["train"].relative_to(ROOT)),
                            "sha256": sha256(built["files"]["train"])},
            "validation_cache": {"file": str(built["files"]["validation"].relative_to(ROOT)),
                                 "sha256": sha256(built["files"]["validation"])},
            "visits": {s: len(c) for s, c in built["caches"].items()},
            "questions": {s: c.info["questions"] for s, c in built["caches"].items()},
            "tokens": {s: c.info["tokens"] for s, c in built["caches"].items()},
            "N": span_cards.tokens_per_line(train), "newline_ids": built["tokenizer"].encode("\n")}


def dev_batches(cache: pdata.VisitCache, visits: int, max_tokens: int, max_visits: int, tags=None) -> list:
    chosen = list(range(min(visits, len(cache))))
    groups = pdata.length_batches(cache.lengths[chosen].tolist(), max_tokens, max_visits=max_visits)
    return [pdata.collate(cache, [chosen[i] for i in g], slices=tags) for g in groups]


def slice_tags(built: dict, visits: int):
    from premonition import exp1
    data = exp1.open_data(ROOT, built["data_rel"], TOKENIZER)
    cache = built["caches"]["validation"]
    return _slice_tags_for(data, "validation", cache, list(range(min(visits, len(cache)))))


# ----------------------------------------------------------------------------- models and trainers
def train_config():
    return mini_train_config(lr=1e-3, warmup_steps=100, log_every=50, eval_every=1000)     # train_d's


def span_config(n_target: float) -> span_cards.SpanConfig:
    return span_cards.SpanConfig(enabled=True, max_span=64, newline_prior=8.0, base_logit=-4.0, w_rate=0.03,
                                 newline_id=23, tokens_per_card=n_target)                   # run card §3


def model_config(tokenizer: Tokenizer, size: str) -> MiniConfig:
    return MiniConfig.preset("D", size, vocab_size=tokenizer.vocab_size)


def optimizer_names(model: torch.nn.Module, optimizer: torch.optim.Optimizer) -> list[str]:
    """Parameter names in the order of the optimizer's own param groups (its state_dict indexes them so)."""
    names = {id(p): n for n, p in model.named_parameters()}
    return [names[id(p)] for group in optimizer.param_groups for p in group["params"]]


def branch_state(parent: dict, trainer: MiniTrainer) -> dict:
    """`trainer`'s optimizer state taken from the parent's, matched by parameter name (new parameters: none)."""
    by_name = dict(zip(parent["names"], range(len(parent["names"]))))
    state = trainer.optimizer.state_dict()
    old = parent["optimizer"]
    shapes = dict(trainer.model.named_parameters())
    mapped = {}
    for index, name in enumerate(optimizer_names(trainer.model, trainer.optimizer)):
        if name in by_name and by_name[name] in old["state"]:
            entry = copy.deepcopy(old["state"][by_name[name]])
            if entry["exp_avg"].shape != shapes[name].shape:
                raise ValueError(f"optimizer state for {name} has shape {tuple(entry['exp_avg'].shape)}, "
                                 f"the parameter {tuple(shapes[name].shape)}")
            mapped[index] = entry
    for group, previous in zip(state["param_groups"], old["param_groups"]):
        for key, value in previous.items():
            if key != "params":
                group[key] = value
    return {"state": mapped, "param_groups": state["param_groups"]}


def restore(trainer: MiniTrainer, parent: dict) -> None:
    trainer.optimizer.load_state_dict(branch_state(parent, trainer))
    trainer.load_state_dict(copy.deepcopy(parent["trainer"]))
    ckpt.set_rng_state(copy.deepcopy(parent["rng"]))


def calibrate_keeping_rng(trainer: MiniTrainer, head: list):
    """`calibrate` on the head batches, with the trainer's generator and the global RNG put back afterwards."""
    generator, rng = trainer.generator.get_state(), ckpt.rng_state()
    fit = trainer.calibrate(head)
    trainer.generator.set_state(generator)
    ckpt.set_rng_state(rng)
    return fit


def stream_from(cache, args, seed: int, skip: int) -> Iterator:
    stream = pdata.batches(cache, args.max_tokens, seed=seed, epochs=None, max_visits=args.max_visits)
    for _ in range(skip):
        next(stream)
    return stream


def gold_only(trainer: MiniTrainer, stream: Iterator) -> Iterator:
    """The stream while the trainer's plan is in the gold phase: the parent stops exactly at the branch point. The
    parent trains the stream's batches in order, so the arms resume at batch `trainer.step` of a fresh stream."""
    for batch in stream:
        if trainer.plan().phase != "gold":
            return
        yield batch


# ----------------------------------------------------------------------------- evaluation
@torch.no_grad()
def dev_eval(model: PremonitionMini, cache: pdata.VisitCache, tags, tokenizer: Tokenizer, stop: list, args) -> dict:
    """Own-retrieval exact match on the whole validation split: accuracy overall and per slice, and the per-question
    correctness in the cache's question order (packed bits; the `slices` record holds the masks in the same order),
    for the paired G2 tests."""
    model.eval()
    device = next(model.parameters()).device
    correct: dict[str, bool] = {}
    slices: dict[str, list[int]] = {}
    for batch in pdata.batches(cache, args.max_tokens, seed=None, max_visits=args.max_visits, slices=tags):
        batch = batch.to(device)
        if not batch.q_visit.shape[0]:
            continue
        answers = model.answer(batch, stop=stop)
        hit, _ = judge(answers, batch, tokenizer=tokenizer, stop=stop, eos=model.config.eos_id)
        for q, qid in enumerate(batch.question_ids):
            correct[qid] = bool(hit[q])
        for name, tag in (batch.slices or {}).items():
            entry = slices.setdefault(name, [0, 0])
            tag = tag.cpu()
            entry[0] += int(torch.tensor(hit)[tag].sum())
            entry[1] += int(tag.sum())
    order = [qid for qid in cache.question_ids if qid in correct]
    if order != list(cache.question_ids):             # the bits must align with the slice masks (cache order)
        raise RuntimeError(f"dev_eval scored {len(order)} of {len(cache.question_ids)} validation questions")
    return {"questions": len(order), "accuracy": sum(correct[q] for q in order) / max(len(order), 1),
            "slices": {k: {"n": v[1], "accuracy": v[0] / v[1] if v[1] else None} for k, v in sorted(slices.items())},
            "ids_sha256": hashlib.sha256("\n".join(order).encode()).hexdigest(),
            "correct_bits": bits([correct[q] for q in order])}


def economy(model: PremonitionMini, batches: list, device) -> dict:
    report = span_cards.card_economy(model, batches, device=device)
    keep = ("layout", "cards", "cards_per_visit", "tokens_per_card", "line_aligned", "merged", "split_lines",
            "newline_precision", "newline_recall", "ents_overflow", "gold_cards_per_told_q", "gold_card_tokens",
            "gold_missing", "asked_rate", "fetches_per_q", "null_share", "first_ask_recall", "full_gold_fetched",
            "questions", "told")
    return {k: report[k] for k in keep}


def save(built: dict, trainer: MiniTrainer, name: str, args, extra: dict) -> dict:
    relative = f"artifacts/span-stage1/{RUN_ID}/seed{args.seed}/{name}"
    config = checkpoint_config(trainer, contender=extra.pop("contender"),
                               tokenizer={"path": TOKENIZER, "sha256": built["tokenizer"].digest},
                               detector=built["detector"].digest, data={"dir": built["data_rel"], "tag": built["tag"]},
                               extra=extra, preprocess_identity=preprocess.identity(preprocess.LABEL_FREE))
    path = save_mini_checkpoint(built["budget"], relative, trainer, config)
    return {"path": relative, "state_sha256": sha256(path / "state.pt"), "config_sha256": sha256(path / "config.json")}


def train_report(report: dict) -> dict:
    keep = ("steps", "tokens", "seconds", "stop", "flops", "flops_total", "flop_budget", "flops_share", "budget_ok",
            "loop_mismatches", "phases", "final", "peak_gpu_reserved_bytes", "fit")
    return {k: report.get(k) for k in keep}


def progress(arm: str, seed: int):
    def on_log(record: dict) -> None:
        if "eval" in record:
            ev = record["eval"]
            emit("eval", {"seed": seed, "arm": arm, "step": record["step"], "share": round(record["flops_share"], 4),
                          "accuracy": ev.get("accuracy"), "far": (ev.get("slices") or {}).get("far"),
                          "asked_rate": ev.get("asked_rate"), "recall4": ev.get("gold_recall_at_4")})
        elif record["step"] % 1000 == 0:
            emit("progress", {"seed": seed, "arm": arm, "step": record["step"],
                              "share": round(record["flops_share"], 4), "phase": record["phase"],
                              "loss": record.get("loss"), "acc": record.get("answer_acc")})
    return on_log


# ----------------------------------------------------------------------------- memory pre-flight
def packed(order: list[int], lengths: list[int], max_tokens: int, max_visits: int) -> list[int]:
    """The visits of `order`, taken greedily while the batch stays within max_tokens padded and max_visits."""
    group: list[int] = []
    for v in order:
        trial = group + [v]
        if len(trial) <= max_visits and len(trial) * max(lengths[u] for u in trial) <= max_tokens:
            group = trial
    return group


def heaviest(cache, max_tokens: int, max_visits: int, seed: int) -> list[list[int]]:
    """Batches that bound every epoch's: the 3 heaviest of the first epoch's grouping by padded tokens, questions
    and lines, plus adversarial groups packed (within max_tokens and max_visits) from the visits with the most
    questions, the most lines, and the most questions per token, which no later regrouping can exceed by much."""
    groups = pdata.length_batches(cache.lengths.tolist(), max_tokens, rng=random.Random(seed), max_visits=max_visits)
    lengths, lines = cache.lengths.tolist(), cache.line_counts.tolist()
    questions = [len(cache.questions_of(v)) for v in range(len(cache))]
    keys = (lambda g: len(g) * max(lengths[v] for v in g), lambda g: sum(questions[v] for v in g),
            lambda g: sum(lines[v] for v in g))
    chosen: list[list[int]] = []
    for key in keys:
        for group in sorted(groups, key=key, reverse=True)[:3]:
            if group not in chosen:
                chosen.append(group)
    visits = range(len(cache))
    for score in (lambda v: questions[v], lambda v: lines[v], lambda v: questions[v] / max(lengths[v], 1)):
        group = packed(sorted(visits, key=score, reverse=True), lengths, max_tokens, max_visits)
        if group and group not in chosen:
            chosen.append(group)
    return chosen


OOM_SIGNS = ("out of memory", "CUBLAS_STATUS_ALLOC_FAILED", "CUDNN_STATUS_ALLOC_FAILED")


def is_oom(error: BaseException) -> bool:
    """A GPU memory exhaustion, whether raised as OutOfMemoryError or as a library's RuntimeError."""
    return isinstance(error, torch.cuda.OutOfMemoryError) or any(sign in str(error) for sign in OOM_SIGNS)


def preflight_arm(args: argparse.Namespace) -> None:
    """Child process: peak reserved GPU memory of one arm at one rung (printed as one `PREFLIGHT {json}` line).
    Running out of GPU memory is a measurement (`oom`: true); any other failure is an error (non-zero exit)."""
    try:
        measure_arm(args)
    except RuntimeError as error:                         # OutOfMemoryError is a RuntimeError too
        if not is_oom(error):
            raise
        record = {"arm": args.arm, "max_tokens": args.max_tokens, "max_visits": args.max_visits, "oom": True,
                  "error": repr(error)[:300], "peak_reserved_gb": None}
        print("PREFLIGHT " + json.dumps(record), flush=True)


def measure_arm(args: argparse.Namespace) -> None:
    built = build(args)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cache = built["caches"]["train"]
    tokenizer = built["tokenizer"]
    config = model_config(tokenizer, args.size)
    torch.manual_seed(args.seed)
    line = PremonitionMini(config)
    if args.arm == "LINE":
        model, trainer_class = line, MiniTrainer
    else:
        model = span_cards.build_model(config, span_config(span_cards.tokens_per_line(cache)))
        span_stage0.load_from_line(model, line)
        trainer_class = span_cards.SpanTrainer
        if args.arm == "SPAN-stress":
            def cut(_module, _inputs, out):
                positions = torch.arange(out.shape[1], device=out.device).view(1, -1, 1)
                return out + 20.0 * (positions % STRESS_EVERY == STRESS_EVERY - 1).to(out.dtype)
            model.writer.gate.register_forward_hook(cut)
    trainer = trainer_class(model, train_config(), device, flop_budget=F_BUDGET, seed=args.seed)
    groups = heaviest(cache, args.max_tokens, args.max_visits, args.seed)
    batches = [pdata.collate(cache, g) for g in groups]
    # no FLOP calibration here: _train_step does not use the fit, and the real run calibrates (fp32) on ordinary
    # head batches before it resets the peak, which Stage 0 ran at full size
    if device.type == "cuda":
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    steps = 0
    # every step tracked: the real run tracks every 50th step in every phase (hooks, InsertLog), the heavier case
    modes = (("gold", Plan("gold", "gold", 0.0), True), ("teacher", Plan("teacher", "teacher", 0.0), True),
             ("own", Plan("own", "own", 0.75), True))
    for mode, plan, track in modes:
        for batch in batches:
            out = trainer._train_step(batch, plan, planned_loops(batch, plan.mode, config), track)
            if not math.isfinite(float(out["loss"])):
                raise FloatingPointError(f"{args.arm} {mode} loss {float(out['loss'])}")
            steps += 1
    dev = dev_batches(built["caches"]["validation"], EVAL_VISITS, args.max_tokens, args.max_visits)
    stop = sorted(step1.stop_ids(tokenizer)[0])
    trainer.evaluate(validation_hook(dev, tokenizer=tokenizer, stop=stop))
    report = economy(model, dev_batches(built["caches"]["validation"], ECONOMY_VISITS, args.max_tokens,
                                        args.max_visits), device)
    peak = torch.cuda.max_memory_reserved() / 1e9 if device.type == "cuda" else 0.0
    print("PREFLIGHT " + json.dumps(jsonable({
        "arm": args.arm, "max_tokens": args.max_tokens, "max_visits": args.max_visits, "steps": steps,
        "batches": [{"visits": len(g), "padded": int(b.tokens.numel()), "questions": int(b.q_visit.shape[0])}
                    for g, b in zip(groups, batches)],
        "oom": False, "peak_reserved_gb": peak, "peak_allocated_gb": torch.cuda.max_memory_allocated() / 1e9
        if device.type == "cuda" else 0.0, "tokens_per_card": report["tokens_per_card"]["mean"],
        "line_aligned": report["line_aligned"]}), allow_nan=False), flush=True)


def as_text(value) -> str:
    """A subprocess output as text: TimeoutExpired carries bytes even when the run asked for text."""
    return (value.decode(errors="replace") if isinstance(value, bytes) else value) or ""


def preflight(args: argparse.Namespace) -> dict:
    """Every rung in order, a clean child per arm, until one rung fits every arm; the record of all measured."""
    guard = train_config().memory_limit_bytes / 1e9
    limit = guard - MARGIN_GB
    rungs = []
    for max_tokens, max_visits in LADDER:
        children = []
        for arm in ("LINE", "SPAN", "SPAN-stress"):
            command = [sys.executable, str(Path(__file__).resolve()), "preflight-arm", "--arm", arm,
                       "--seed", str(args.seed), "--visits", args.visits, "--size", args.size,
                       "--workers", str(args.workers), "--max-tokens", str(max_tokens), "--max-visits", str(max_visits)]
            try:
                run = subprocess.run(command, capture_output=True, text=True, timeout=CHILD_TIMEOUT)
            except subprocess.TimeoutExpired as expired:
                out, err = as_text(expired.stdout), as_text(expired.stderr)
                run = types.SimpleNamespace(returncode="timeout", stdout=out,
                                            stderr=f"no result after {CHILD_TIMEOUT} s; stderr: {err[-1200:]}; "
                                                   f"stdout: {out[-800:]}")
            found = [l for l in run.stdout.splitlines() if l.startswith("PREFLIGHT ")]
            if run.returncode or not found:                   # not a memory measurement: a fault, so stop
                emit("preflight_error", {"arm": arm, "max_tokens": max_tokens, "max_visits": max_visits,
                                         "returncode": run.returncode, "stderr": (run.stderr or run.stdout)[-2500:]})
                # (a timeout's message carries the child's own stderr and stdout tails)
                raise SystemExit(f"memory pre-flight child {arm} failed for a reason other than memory")
            child = json.loads(found[-1][len("PREFLIGHT "):])
            children.append(child)
            if child["oom"] or child["peak_reserved_gb"] > limit:
                break                                         # this rung does not fit: the next arms need not run
        peaks = [math.inf if c["oom"] else c["peak_reserved_gb"] for c in children]
        peak = max(peaks)
        rung = {"max_tokens": max_tokens, "max_visits": max_visits, "peak_reserved_gb": peak,
                "fits": len(children) == 3 and peak <= limit, "children": children}
        rungs.append(rung)
        emit("preflight_rung", rung)
        if rung["fits"]:
            break
    chosen = next((r for r in rungs if r["fits"]), None)
    return {"guard_gb": guard, "margin_gb": MARGIN_GB, "limit_gb": limit,
            "chosen": None if chosen is None else {"max_tokens": chosen["max_tokens"],
                                                   "max_visits": chosen["max_visits"]},
            "rungs": [{k: r[k] for k in ("max_tokens", "max_visits", "peak_reserved_gb", "fits")} for r in rungs]}


# ----------------------------------------------------------------------------- the go file
def read_go(args: argparse.Namespace) -> Optional[dict]:
    try:
        if args.go_file:
            return json.loads(Path(args.go_file).read_text())
        request = urllib.request.Request(f"{args.go_url}?t={int(time.time())}", headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except Exception:                                   # noqa: BLE001 - not there yet, or unreadable: wait
        return None


def wait_for_go(args: argparse.Namespace, expected: dict, fitted: tuple) -> dict:
    """The go record once it names exactly this box's script, caches, N and a rung no larger than `fitted` (the
    rung this box's pre-flight measured as fitting); every mismatch is logged as a refusal and waited on."""
    deadline = time.time() + args.go_wait_hours * 3600
    reported = None
    while time.time() < deadline:
        go = read_go(args)
        if go is not None and not isinstance(go, dict):
            go = {"go": None, "malformed": True}
        if go is not None and go != reported:
            reported = go
            if go.get("go") is False and go.get("script_sha256") == expected.get("script_sha256") \
                    and isinstance(go.get("seeds"), list) and args.seed in go["seeds"]:
                raise SystemExit("the go file says stop")    # a stop for this script and seed (a stale one is not)
            wrong = [k for k, v in expected.items() if go.get(k) != v]
            if not isinstance(go.get("seeds"), list) or args.seed not in go["seeds"]:
                wrong.append("seeds")
            bad_rung = [k for k in ("max_tokens", "max_visits") if not isinstance(go.get(k), int)]
            wrong += bad_rung
            if not bad_rung and not rung_allowed((go["max_tokens"], go["max_visits"]), fitted):
                wrong.append("rung")                          # off the ladder, or larger than this box's fit
            if go.get("go") is True and not wrong:
                return go
            emit("go_refused", {"seed": args.seed, "mismatch": wrong, "go": go.get("go")})
        time.sleep(args.go_poll_seconds)
    raise SystemExit("no valid go file before the deadline")


# ----------------------------------------------------------------------------- one seed
def run_seed(args: argparse.Namespace, built: dict, tags: dict, go: dict) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    args.max_tokens, args.max_visits = go["max_tokens"], go["max_visits"]
    tokenizer, train_cache, valid_cache = built["tokenizer"], built["caches"]["train"], built["caches"]["validation"]
    config = model_config(tokenizer, args.size)
    n_target = go["N"]
    stop = sorted(step1.stop_ids(tokenizer)[0])
    all_tags = tags                                                   # masks over every question: any subset uses them
    hook = validation_hook(dev_batches(valid_cache, EVAL_VISITS, args.max_tokens, args.max_visits, all_tags),
                           tokenizer=tokenizer, stop=stop)
    economy_batches = dev_batches(valid_cache, ECONOMY_VISITS, args.max_tokens, args.max_visits)
    flop_budget = args.flop_budget

    # parent P_s: train_d's start, stopped at the end of the gold phase
    torch.manual_seed(args.seed)
    parent_model = PremonitionMini(config)
    trainer = MiniTrainer(parent_model, train_config(), device, flop_budget=flop_budget, seed=args.seed)
    stream = pdata.batches(train_cache, args.max_tokens, seed=args.seed, epochs=None, max_visits=args.max_visits)
    head = [next(stream) for _ in range(HEAD)]
    fit = trainer.calibrate(head)
    if device.type == "cuda":                             # calibration (fp32) is not training: the guard starts here
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    report = trainer.train(gold_only(trainer, itertools.chain(head, stream)), evaluate=hook,
                           on_log=progress("P", args.seed))
    consumed = trainer.step                            # batches trained, in stream order (a discarded one is not)
    emit("parent", {"seed": args.seed, "train": train_report(report), "batches_consumed": consumed,
                    "fit": {"a": fit.a, "b": fit.b, "worst": fit.worst}})
    to_cpu = lambda tree: torch.utils._pytree.tree_map(                               # noqa: E731
        lambda x: x.detach().cpu().clone() if torch.is_tensor(x) else copy.deepcopy(x), tree)
    parent = {"model": to_cpu(parent_model.state_dict()),        # on the CPU: the arms' GPU holds only their own run
              "optimizer": to_cpu(trainer.optimizer.state_dict()),
              "trainer": copy.deepcopy(trainer.state_dict()), "rng": ckpt.rng_state(),
              "names": optimizer_names(parent_model, trainer.optimizer), "consumed": consumed}
    emit("parent_ckpt", {"seed": args.seed, **save(built, trainer, "parent", args, {           # saved before any
        "contender": "D", "stage1": {"role": "parent", "batches_consumed": consumed}})})        # evaluation can fail
    emit("parent_dev", {"seed": args.seed, "dev": dev_eval(parent_model, valid_cache, all_tags, tokenizer, stop, args)})
    parent_economy = economy(parent_model, economy_batches, device)
    del trainer

    # branch-point check (run card §3)
    probe = span_cards.build_model(config, span_config(n_target)).to(device)
    branch_batches = [b.to(device) for b in dev_batches(valid_cache, BRANCH_VISITS, args.max_tokens, args.max_visits)]
    branch = span_stage0.branch_gate(parent_model.to(device), probe, branch_batches, device)
    strict = branch["strict_cpu"]
    emit("branch", {"seed": args.seed, "passed": branch["passed"], "reasons": branch["reasons"],
                    "line_aligned_is_1": branch["line_aligned_is_1"], "cards": strict["cards"],
                    "cpu_key_diff": strict["max_key_diff"], "cpu_value_diff": strict["max_value_diff"],
                    "natural": strict["natural"], "eager": strict["eager"],
                    "gpu_flips": branch.get("gpu_answer_differences"),
                    "gpu_key_diff": branch.get("gpu", {}).get("max_key_diff")})
    if not branch["passed"]:
        raise SystemExit(f"branch-point check failed ({branch['reasons']}): the pairing is broken (run card §3)")
    del probe, branch_batches

    # the arms
    parent_model.load_state_dict(parent["model"], strict=True)
    parent_model.cpu()                                    # only read by the SPAN load below
    for arm in ("LINE", "SPAN"):
        if device.type == "cuda":
            torch.cuda.empty_cache()                          # free the previous arm (the peak is reset below)
        torch.manual_seed(args.seed)
        if arm == "LINE":
            model = PremonitionMini(config)
            model.load_state_dict(parent["model"], strict=True)
            trainer = MiniTrainer(model, train_config(), device, flop_budget=flop_budget, seed=args.seed)
        else:
            model = span_cards.build_model(config, span_config(n_target))
            missing, unexpected = span_stage0.load_from_line(model, parent_model)
            if set(missing) != span_stage0.GATE_KEYS or unexpected:
                raise SystemExit(f"SPAN did not load P_s (missing {missing}, unexpected {unexpected})")
            trainer = span_cards.SpanTrainer(model, train_config(), device, flop_budget=flop_budget, seed=args.seed)
        restore(trainer, parent)
        arm_fit = calibrate_keeping_rng(trainer, head)
        if device.type == "cuda":                             # as for the parent: calibration (fp32) is not training,
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
        at_branch = parent_economy if arm == "LINE" else economy(model, economy_batches, device)
        emit("arm_start", {"seed": args.seed, "arm": arm, "step": trainer.step, "share": trainer.flops / flop_budget,
                           "fit": {"a": arm_fit.a, "b": arm_fit.b, "worst": arm_fit.worst}, "economy": at_branch})
        stream = stream_from(train_cache, args, args.seed, parent["consumed"])
        report = trainer.train(stream, evaluate=hook, on_log=progress(arm, args.seed))
        emit("arm_train", {"seed": args.seed, "arm": arm, "train": train_report(report),
                           "span_log_last": getattr(trainer, "span_log", [])[-3:]})
        extra = {"contender": "D" if arm == "LINE" else span_cards.VARIANT,
                 "stage1": {"role": arm, "parent_batches": parent["consumed"]}}
        if arm == "SPAN":
            extra["span"] = asdict(model.span)
        emit("arm_ckpt", {"seed": args.seed, "arm": arm, **save(built, trainer, arm.lower(), args, extra)})   # first
        dev = dev_eval(model, valid_cache, all_tags, tokenizer, stop, args)
        emit("arm_dev", {"seed": args.seed, "arm": arm, "dev": dev})
        emit("arm_economy", {"seed": args.seed, "arm": arm, "economy": economy(model, economy_batches, device)})
        del trainer, model


# ----------------------------------------------------------------------------- entry points
def script_sha256() -> str:
    return sha256(Path(__file__).resolve())


def rung_allowed(rung: tuple, fitted: tuple) -> bool:
    """A go file may name the rung this box measured as fitting or a smaller one of the ladder, never a larger."""
    return rung in LADDER and fitted in LADDER and LADDER.index(rung) >= LADDER.index(fitted)


def code_files() -> list[str]:
    """Every Python file of `CODE_PACKAGES` (recursively) plus `CODE_SCRIPTS`, sorted, relative to the root."""
    files = {str(path.relative_to(ROOT)) for package in CODE_PACKAGES for path in (ROOT / package).rglob("*.py")
             if "__pycache__" not in path.parts}
    return sorted(files | set(CODE_SCRIPTS))


def code_sha256() -> str:
    """One digest over every file of `code_files()`: the whole code the run imports, not a hand-kept list."""
    return hashlib.sha256("".join(f"{name}:{sha256(ROOT / name)}\n" for name in code_files()).encode()).hexdigest()


def box(args: argparse.Namespace) -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    emit("env", {"seed": args.seed, "torch": torch.__version__, "cuda": torch.version.cuda, "device": device,
                 "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
                 "python": platform.python_version(), "script_sha256": script_sha256(), "code_sha256": code_sha256(),
                 "span_cards_sha256": span_cards.source_digest(), "args": vars(args)})
    built = build(args)
    record = data_record(built)
    emit("data", {"seed": args.seed, **record})
    if record["newline_ids"] != [23]:
        raise SystemExit(f"newline id {record['newline_ids']} is not 23: SpanConfig.newline_id would be wrong")
    tags = slice_tags(built, len(built["caches"]["validation"]))      # needed for G2: fail before paying more
    counts = {name: int(tag.sum()) for name, tag in (tags or {}).items()}
    valid = built["caches"]["validation"]
    emit("slices", {"seed": args.seed, "counts": counts, "questions": len(valid.question_ids),
                    "ids_sha256": hashlib.sha256("\n".join(valid.question_ids).encode()).hexdigest(),
                    "masks": {name: bits(tag.tolist()) for name, tag in (tags or {}).items()}})
    absent = [name for name in REQUIRED_SLICES if not counts.get(name)]
    if absent:
        raise SystemExit(f"DEV slices {absent} are missing or empty: the readout (G2 needs far) would be incomplete")
    memory = preflight(args)
    emit("preflight", {"seed": args.seed, **memory})
    if memory["chosen"] is None:
        raise SystemExit("no batch configuration fits both arms inside the memory guard: stop and report")
    expected = {"script_sha256": script_sha256(), "code_sha256": code_sha256(),
                "train_cache_sha256": record["train_cache"]["sha256"],
                "validation_cache_sha256": record["validation_cache"]["sha256"], "N": record["N"],
                "flop_budget": args.flop_budget}
    fitted = (memory["chosen"]["max_tokens"], memory["chosen"]["max_visits"])
    go = wait_for_go(args, expected, fitted)                      # refuses a rung larger than `fitted`
    emit("go", {"seed": args.seed, "max_tokens": go["max_tokens"], "max_visits": go["max_visits"]})
    run_seed(args, built, tags, go)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("box", "data", "preflight-arm"))
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--visits", default="large")
    parser.add_argument("--size", default="full")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--flop-budget", type=float, default=F_BUDGET)
    parser.add_argument("--max-tokens", type=int, default=LADDER[0][0])
    parser.add_argument("--max-visits", type=int, default=LADDER[0][1])
    parser.add_argument("--arm", choices=("LINE", "SPAN", "SPAN-stress"), default="LINE")
    parser.add_argument("--go-url", default="https://raw.githubusercontent.com/BenjaminHannan/learner/"
                                            "span-cards-solve/design/span-cards/stage1-go.json")
    parser.add_argument("--go-file", default=None)
    parser.add_argument("--go-poll-seconds", type=float, default=120.0)
    parser.add_argument("--go-wait-hours", type=float, default=3.0)
    args = parser.parse_args(argv)
    if args.seed < 0 or args.workers < 1 or args.flop_budget <= 0 or args.max_tokens < 1 or args.max_visits < 1:
        parser.error("--seed >= 0, --workers >= 1, --flop-budget > 0, --max-tokens and --max-visits >= 1")
    return args


def main(args: argparse.Namespace) -> None:
    if args.command == "preflight-arm":
        preflight_arm(args)
    elif args.command == "data":
        emit("data", {"seed": args.seed, **data_record(build(args))})
    else:
        box(args)


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.command == "preflight-arm":
        main(arguments)                                   # a child: its exit status and stderr carry failures
        sys.exit(0)
    try:
        main(arguments)
    except BaseException as error:                        # noqa: BLE001 - the log is the only channel back
        emit("error", {"seed": arguments.seed, "error": repr(error), "trace": traceback.format_exc()[-3000:]})
        print("S1-DONE failed", flush=True)
        sys.exit(1)
    print("S1-DONE ok", flush=True)
