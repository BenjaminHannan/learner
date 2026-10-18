"""Span cards SC-1, Stage 0 (design/span-cards/03-funding-bid.md, ruling Q22): measure before spending.

DRAFT (Q129): must not run until the coordinator's review of this script passes.

On one GPU box, in this order, each step printed as a `STAGE0 {json}` line (the box's log is the only channel
back, so partial results survive a stop):
1. data: fresh label-free v2 caches from the step-1 simulator (seed 0): `--train-visits` train and
   `--valid-visits` validation visits, the premonition-tok-v2-fallback tokenizer, a fitted name detector;
   N = `span_cards.tokens_per_line(train cache)` at this size.
2. timing: seconds per training step for LINE (`MiniTrainer`) and SPAN (`SpanTrainer`, loaded from LINE's
   weights) in gold, teacher and own (p_own 0.75) mode on the same real batches (max_tokens 55,000, max_visits
   48), after warm-up, plus tracked own-mode steps, with the FLOP fit; and train_d's validation hook per arm.
   Then the Stage 1 projection: steps per mode from F = 3.15e16 and the curriculum shares, 3 parents (LINE, 5%
   of F) + Cell A (LINE and SPAN x 3 seeds x 95%), each with its tracked steps and validations.
3. smoke: a fresh SPAN model through the whole curriculum in about 200 SpanTrainer steps; losses must be finite,
   the own phase reached and the stop the FLOP budget (checked at the end, after the final branch check, so a
   failure there still gets its branch readout).
4. branch: `branch_gate` / `branch_check` (their docstrings have the pass conditions, `line_aligned == 1` among
   them; the strict check runs on CPU) on 64 DEV visits,
   with SPAN loaded from the LINE model as trained by the timing steps. The same check runs as a pre-flight on
   fresh weights right after the data step, before anything else is paid for. A failed check stops the run
   (run card §3: the pairing is broken) with exit status 1.
`STAGE0-DONE ok` (or `failed`, after an `error` line) ends the log. Nothing is saved but the log; the box is
destroyed after it is read.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import platform
import sys
import time
import traceback
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from learnlab.step0 import jsonable                                          # noqa: E402
from learnlab.step1 import stop_ids                                          # noqa: E402
from learnlab.tokenizer import Tokenizer                                     # noqa: E402
from learnlab.train import reserved_bytes                                    # noqa: E402
from learnlab.village.shards import write_shards                             # noqa: E402
from premonition import data as pdata, preprocess, span_cards                # noqa: E402
from premonition.config import MiniConfig                                     # noqa: E402
from premonition.model import PremonitionMini                                 # noqa: E402
from premonition.train import (MiniTrainer, Plan, budget_for_steps, mini_train_config, planned_loops,  # noqa: E402
                               validation_hook)

F_BUDGET = 3.15e16                       # design/06 §4 (A's v2 budget run), the bid's F
SHARES = {"gold": 0.05, "teacher": 0.25, "own": 0.70}   # Curriculum(): gold to 5%, teacher to 30%, own after
PLANS = {"gold": Plan("gold", "gold", 0.0), "teacher": Plan("teacher", "teacher", 0.0),
         "own": Plan("own", "own", 0.75)}
STARTED = time.perf_counter()


def emit(step: str, **values) -> None:
    record = jsonable({"step": step, "t": round(time.perf_counter() - STARTED, 1), **values})   # strict JSON
    print("STAGE0 " + json.dumps(record, allow_nan=False), flush=True)


def sync(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize()


def build(work: Path, split: str, visits: int, workers: int) -> None:
    write_shards(split, visits, work, workers, seed=0, verbose=False)


def time_steps(trainer: MiniTrainer, batches, plan: Plan, warm: int, timed: int, track: bool = False) -> dict:
    device = trainer.device
    config = trainer.model.config
    by_index = {}
    for i, batch in enumerate(batches[:warm + timed]):
        loops = planned_loops(batch, plan.mode, config)
        sync(device)
        start = time.perf_counter()
        out = trainer._train_step(batch, plan, loops, track=track)
        loss = float(out["loss"])
        sync(device)
        if not math.isfinite(loss):
            raise FloatingPointError(f"{plan.mode} loss {loss}")
        if i >= warm:
            by_index[i] = time.perf_counter() - start
    seconds = sorted(by_index.values())
    return {"tracked": track, "mean": sum(seconds) / len(seconds), "median": seconds[len(seconds) // 2],
            "max": seconds[-1], "n": len(seconds), "by_index": by_index}


def time_arm(arm: str, trainer: MiniTrainer, batches, args, device) -> dict:
    """Seconds per untracked step in every mode, plus tracked own-mode steps on the same batch indices as the timed own
    steps (train_d tracks every 50th step: hooks, InsertLog, card statistics); `tracked_extra` is the mean per-batch
    difference (raw, possibly negative from timing noise; the projection charges max(0, it)). Peak allocated and
    reserved GPU memory (train_d's guard checks reserved against `memory_limit_bytes`). Each result is emitted as it
    comes."""
    out = {}
    runs = [(mode, plan, args.warm, args.timed, False) for mode, plan in PLANS.items()]
    runs.append(("own_tracked", PLANS["own"], args.warm, args.timed, True))
    for name, plan, warm, timed, track in runs:
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats()
        out[name] = time_steps(trainer, batches, plan, warm, timed, track)
        if device.type == "cuda":
            out[name]["peak_gb"] = torch.cuda.max_memory_allocated() / 1e9
        out[name]["reserved_gb"] = reserved_bytes(device) / 1e9
        emit("timing", arm=arm, mode=name, **out[name])
    tracked, plain = out["own_tracked"]["by_index"], out["own"]["by_index"]
    out["tracked_extra"] = sum(tracked[i] - plain[i] for i in tracked) / len(tracked)
    return out


def release(trainer: MiniTrainer, device) -> None:
    """Free a timing trainer's gradients and optimizer state (its model stays) and return the cached blocks."""
    trainer.model.zero_grad(set_to_none=True)
    trainer.optimizer.state.clear()
    if device.type == "cuda":
        torch.cuda.empty_cache()


def time_validation(trainer: MiniTrainer, dev, tokenizer, device) -> float:
    """Seconds of train_d's validation hook (stop ids, under `Trainer.evaluate`'s read_only guard) over `dev`,
    after a one-batch warm-up."""
    stop = sorted(stop_ids(tokenizer)[0])
    trainer.evaluate(validation_hook(dev[:1], tokenizer=tokenizer, stop=stop))
    sync(device)
    started = time.perf_counter()
    trainer.evaluate(validation_hook(dev, tokenizer=tokenizer, stop=stop))
    sync(device)
    return time.perf_counter() - started


GATE_KEYS = frozenset({"writer.gate.weight", "writer.gate.bias", "writer.newline_weight"})
TOLERANCE = 1e-4          # float error between the two pool codes: card keys (unit length), card values (relative
                          # to their largest magnitude, at least 1)
ANSWER_FIELDS = ("tokens", "lengths", "loops", "first_top", "fetched")
ANSWER_REASONS = ("answers (natural)", "answers (eager)")


HALT_RTOL = 1e-3          # halt probabilities: relative to min(p, 1 - p), i.e. to the odds
HALT_ULPS = 4             # ... but never tighter than a few float32 ulps of p (halt_prob is a float32 sigmoid)


def halt_close(a: torch.Tensor, b: torch.Tensor) -> tuple[torch.Tensor, float]:
    """(per-entry bool, largest relative gap): |a - b| <= max(HALT_RTOL * min(p, 1 - p), HALT_ULPS * eps32 * p).
    Relative to the smaller tail, so a shift near saturation (p 6e-6 -> 1.2e-4) is caught, while a one-ulp float32
    difference near p = 1 is not counted."""
    a, b = a.double(), b.double()
    gap = (a - b).abs()
    tail = torch.minimum(a, 1 - a).clamp_min(0)
    allowed = torch.maximum(HALT_RTOL * tail, HALT_ULPS * torch.finfo(torch.float32).eps * a.abs())
    close = (gap <= allowed) | (a == b)
    rel = torch.where(close, torch.zeros_like(gap), gap / allowed.clamp_min(1e-300)).nan_to_num(math.inf)
    return close, float(rel.max()) if rel.numel() else 0.0


def compare_answers(line: PremonitionMini, span: span_cards.SpanCardMini, batches) -> dict:
    """`answer()` of both models on every batch: questions compared, questions whose answer differs (an exact field:
    tokens, lengths, loops, first_top, fetched; or `halt_prob` outside `halt_close`), the largest halt gap in units
    of its allowance (0 when all close), real (non-NULL) cards LINE fetched, and the questions that fetched at least
    one real card."""
    questions = differing = fetched = covered = 0
    halt_diff = 0.0
    for batch in batches:
        with torch.no_grad():
            a, b = line.answer(batch), span.answer(batch)
        count = a.tokens.shape[0]
        if not count:
            continue
        differ = torch.zeros(count, dtype=torch.bool, device=a.tokens.device)
        for name in ANSWER_FIELDS:
            x, y = getattr(a, name), getattr(b, name)
            differ |= torch.ones_like(differ) if x.shape != y.shape else (x != y).reshape(count, -1).any(1)
        if a.halt_prob.shape != b.halt_prob.shape:
            halt_diff = math.inf
            differ |= True
        else:
            close, gap = halt_close(a.halt_prob, b.halt_prob)
            halt_diff = max(halt_diff, gap)
            differ |= ~close.reshape(count, -1).all(1)
        real = a.fetched[:, :-1]
        questions += count
        differing += int(differ.sum())
        fetched += int(real.sum())
        covered += int(real.any(1).sum())
    return {"questions": questions, "differing": differing, "max_halt_rel_diff": halt_diff,
            "identical": differing == 0, "cards_fetched": fetched,
            "questions_fetching": covered}


def eager_copy(model: PremonitionMini) -> PremonitionMini:
    """A copy that always ASKs and never HALTs (the unit tests' `eager`): every question fetches on every loop, so
    the exact answer fields cover the card path. (HALT is saturated here, so `halt_prob` carries no card signal; the
    card contents themselves are compared directly by `branch_check`.)"""
    model = copy.deepcopy(model)
    with torch.no_grad():
        model.heads.ask.bias.fill_(20.0)
        model.heads.halt.bias.fill_(-20.0)
    return model


def load_from_line(span: span_cards.SpanCardMini, line: PremonitionMini) -> tuple[list, list]:
    """SPAN takes every LINE weight and a fresh gate (the branch point); returns (missing, unexpected) keys."""
    missing, unexpected = span.load_state_dict(line.state_dict(), strict=False)
    span.writer.init_gate()
    return sorted(missing), list(unexpected)


def branch_check(line: PremonitionMini, span: span_cards.SpanCardMini, batches, device) -> dict:
    """SPAN loaded from LINE (gate re-initialised) against LINE on `batches` (DEV, already on `device`). Passes iff:
    only the gate's three weights are missing from the load and nothing is unexpected; there are cards and SPAN
    writes exactly the parent's (`valid == card_end`) with keys and values within `TOLERANCE` (finite; values
    relative to their scale); `answer()` is identical (exact fields; halt probabilities by `halt_close`) with the
    natural weights AND with an eager copy of both (always ASK, never HALT), which must fetch cards (so the identity
    covers the card path); and `card_economy.line_aligned == 1`. Both models end in eval mode. `reasons` names every
    failed condition."""
    missing, unexpected = load_from_line(span, line)
    span.eval()
    line.eval()
    cards, valid_ok, key_diff, value_diff, value_scale = 0, True, 0.0, 0.0, 1.0
    for batch in batches:
        with torch.no_grad():
            plain = line.build_store(line.read(batch), batch)
            spans = span.build_store(span.read(batch), batch)
        bi, ei = torch.nonzero(spans.valid, as_tuple=True)
        cards += int(bi.numel())
        valid_ok &= bool(torch.equal(spans.valid, batch.card_end))
        if bi.numel():
            li = batch.line_of[bi, ei]
            key_diff = max(key_diff, float((spans.keys[bi, ei] - plain.keys[bi, li]).abs().nan_to_num(math.inf).max()))
            value_diff = max(value_diff, float((spans.values[bi, ei].float() - plain.values[bi, li].float())
                                               .abs().nan_to_num(math.inf).max()))
            value_scale = max(value_scale, float(plain.values[bi, li].float().abs().max()))
    natural = compare_answers(line, span, batches)
    eager = compare_answers(eager_copy(line), eager_copy(span), batches)
    economy = span_cards.card_economy(span, batches, device=device)
    layout = {name: economy[name] for name in ("layout", "cards", "line_aligned", "merged", "split_lines",
                                               "newline_precision", "newline_recall", "asked_rate", "fetches_per_q")}
    weights_ok = set(missing) == GATE_KEYS and not unexpected
    aligned = economy["line_aligned"] == 1.0
    reasons = [name for name, ok in (
        ("weights", weights_ok), ("no cards", cards > 0), ("valid != card_end", valid_ok),
        ("card keys or values", key_diff <= TOLERANCE and value_diff <= TOLERANCE * value_scale),
        ("answers (natural)", natural["identical"]), ("answers (eager)", eager["identical"]),
        ("eager fetched no card", eager["cards_fetched"] > 0), ("line_aligned != 1", aligned)) if not ok]
    return {"passed": not reasons, "reasons": reasons, "device": str(device), "line_aligned_is_1": aligned,
            "cards": cards, "max_key_diff": key_diff, "max_value_diff": value_diff,
            "value_scale": value_scale, "natural": natural,
            "eager": eager, "missing": missing, "unexpected": unexpected, "economy": layout}


GPU_FLIP_SHARE = 0.01      # GPU answer differences allowed per pass (near-ties), as a share of the questions


def branch_gate(line: PremonitionMini, span: span_cards.SpanCardMini, batches, device) -> dict:
    """The branch-point check as a gate; `reasons` names every failed condition. The STRICT check (every condition,
    exact answers) runs on CPU: there the two pool codes give bit-identical cards (key and value differences are
    logged, so a box where they are not is visible), and an answer difference means a broken pairing. On a GPU the
    same check also runs: its structural conditions must hold, and its answer differences, which a float near-tie
    can cause there without any pairing fault (LINE and SPAN reach their keys through different matmul shapes), may
    touch at most `GPU_FLIP_SHARE` of the questions (at least one) in each pass. Both models end in eval mode on
    `device`, SPAN loaded from LINE."""
    cpu = torch.device("cpu")
    line.zero_grad(set_to_none=True)                                  # the copies need no gradients
    span.zero_grad(set_to_none=True)
    if device.type == "cpu":
        strict = branch_check(line, span, batches, cpu)
    else:
        strict = branch_check(copy.deepcopy(line).to(cpu), copy.deepcopy(span).to(cpu), [b.to(cpu) for b in batches],
                              cpu)
    out = {"strict_cpu": strict}
    reasons = [f"cpu: {r}" for r in strict["reasons"]]
    aligned = strict["line_aligned_is_1"]
    if device.type != "cpu":
        gpu = branch_check(line, span, batches, device)
        out["gpu"] = gpu
        flips = {k: gpu[k]["differing"] for k in ("natural", "eager")}
        out["gpu_answer_differences"] = flips
        reasons += [f"gpu: {r}" for r in gpu["reasons"] if r not in ANSWER_REASONS]
        reasons += [f"gpu: {k} answers differ on {n} of {gpu[k]['questions']} questions (beyond near-ties)"
                    for k, n in flips.items() if n > max(1, GPU_FLIP_SHARE * gpu[k]["questions"])]
        aligned &= gpu["line_aligned_is_1"]
    out.update(passed=not reasons, reasons=reasons, line_aligned_is_1=aligned)
    return out


def mode_costs(trainer: MiniTrainer, batches) -> dict:
    """Fitted FLOPs per batch in each mode, as the trainer charges them against F."""
    return {mode: sum(trainer.batch_cost(b, plan)[0] for b in batches) / len(batches) for mode, plan in PLANS.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default="/tmp/stage0")
    parser.add_argument("--train-visits", type=int, default=3000)
    parser.add_argument("--valid-visits", type=int, default=256)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--size", default="full")
    parser.add_argument("--max-tokens", type=int, default=55_000)
    parser.add_argument("--max-visits", type=int, default=48)
    parser.add_argument("--warm", type=int, default=2)
    parser.add_argument("--timed", type=int, default=8)
    parser.add_argument("--smoke-steps", type=int, default=200)
    parser.add_argument("--smoke-seconds", type=float, default=900.0,
                        help="floor of the smoke's time cap (raised to 3x the measured SPAN step time)")
    parser.add_argument("--branch-visits", type=int, default=64)
    parser.add_argument("--dph", type=float, default=0.0, help="the box's $/hour, for the projection")
    args = parser.parse_args()
    if args.timed < 1 or args.warm < 0 or args.smoke_steps < 1 or args.branch_visits < 1:
        parser.error("--timed, --smoke-steps and --branch-visits must be at least 1, --warm at least 0")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    emit("env", torch=torch.__version__, cuda=torch.version.cuda, device=str(device),
         gpu=torch.cuda.get_device_name(0) if device.type == "cuda" else None, python=platform.python_version(),
         args=vars(args), source_sha256=span_cards.source_digest())

    # 1. data
    work = Path(args.work)
    started = time.perf_counter()
    build(work, "train", args.train_visits, args.workers)
    build(work, "validation", args.valid_visits, args.workers)
    generated = time.perf_counter() - started
    tokenizer = Tokenizer.load(ROOT / "data/tokenizer/premonition-tok-v2-fallback.json")
    detector = pdata.fit_detector(work / "train", workers=args.workers)
    train_cache = pdata.build_cache(work / "train", tokenizer, detector, workers=args.workers,
                                    regime=preprocess.LABEL_FREE)
    valid_cache = pdata.build_cache(work / "validation", tokenizer, detector, workers=args.workers,
                                    regime=preprocess.LABEL_FREE)
    n_target = span_cards.tokens_per_line(train_cache)
    newline = tokenizer.encode("\n")
    emit("data", train_visits=len(train_cache), valid_visits=len(valid_cache), tokens=train_cache.info["tokens"],
         questions=train_cache.info["questions"], generate_s=round(generated, 1),
         total_s=round(time.perf_counter() - started, 1), N=n_target, newline_ids=newline,
         tokenizer_sha256=tokenizer.digest, detector=detector.digest, stats=train_cache.info["stats"])
    if newline != [23]:
        raise SystemExit(f"newline id {newline} is not 23: SpanConfig.newline_id would be wrong")

    stream = pdata.batches(train_cache, args.max_tokens, seed=0, epochs=None, max_visits=args.max_visits)
    batches = [next(stream).to(device) for _ in range(args.warm + args.timed)]
    emit("batches", tokens=[int(b.tokens.numel()) for b in batches], questions=[int(b.q_visit.shape[0]) for b in batches])
    groups = pdata.length_batches(valid_cache.lengths.tolist(), args.max_tokens, max_visits=args.max_visits)
    dev = [pdata.collate(valid_cache, g).to(device) for g in groups]
    branch_visits = min(args.branch_visits, len(valid_cache))         # the first DEV visits
    branch_batches = [pdata.collate(valid_cache, g).to(device) for g in pdata.length_batches(
        valid_cache.lengths[:branch_visits].tolist(), args.max_tokens, max_visits=args.max_visits)]

    # pre-flight: the branch-point check on fresh weights (the LINE model timed below), before any timing is paid for
    torch.manual_seed(0)
    config = MiniConfig.preset("D", args.size, vocab_size=tokenizer.vocab_size)
    span_config = span_cards.SpanConfig(enabled=True, tokens_per_card=n_target, newline_id=23)
    line = PremonitionMini(config).to(device)
    check = branch_gate(line, span_cards.build_model(config, span_config).to(device), branch_batches, device)
    emit("preflight", visits=branch_visits, **check)
    if not check["passed"]:
        raise SystemExit(f"pre-flight branch-point check failed ({check['reasons']}): the pairing is broken (run card §3)")
    line.train()

    # 2. timing
    timing: dict = {"params": line.num_parameters()}
    huge = 1e30
    line_trainer = MiniTrainer(line, mini_train_config(lr=1e-3, warmup_steps=100), device, flop_budget=huge, seed=0)
    fit = line_trainer.calibrate(batches[:4])
    timing["fit"] = {"a": fit.a, "b": fit.b, "worst": fit.worst}
    costs = mode_costs(line_trainer, batches)
    timing["flops_per_step"] = costs
    timing["line"] = time_arm("LINE", line_trainer, batches, args, device)
    timing["validate_s_line"] = time_validation(line_trainer, dev, tokenizer, device)
    release(line_trainer, device)                                     # SPAN's memory is then measured alone
    del line_trainer
    torch.manual_seed(0)
    span = span_cards.build_model(config, span_config)
    missing, unexpected = load_from_line(span, line)                  # LINE as timed: the branch state
    emit("span_load", missing=missing, unexpected=unexpected)
    if set(missing) != GATE_KEYS or unexpected:
        raise SystemExit("SPAN did not load LINE's weights (only the gate may be missing): timing would be invalid")
    span_trainer = span_cards.SpanTrainer(span, mini_train_config(lr=1e-3, warmup_steps=100), device,
                                          flop_budget=huge, seed=0, fit=fit)
    timing["span"] = time_arm("SPAN", span_trainer, batches, args, device)
    timing["validate_s_span"] = time_validation(span_trainer, dev, tokenizer, device)
    release(span_trainer, device)
    del span_trainer
    timing["validate_visits"] = len(valid_cache)
    # train_d collates each batch on the CPU and copies it to the device inside its loop: time that per batch.
    data_stream = pdata.batches(train_cache, args.max_tokens, seed=2, epochs=None, max_visits=args.max_visits)
    next(data_stream).to(device)                                      # untimed: the per-epoch shuffle and bucketing
    sync(device)
    started = time.perf_counter()
    for _ in range(args.timed):
        next(data_stream).to(device)
    sync(device)
    timing["data_s_per_batch"] = (time.perf_counter() - started) / args.timed
    limit = mini_train_config().memory_limit_bytes / 1e9
    reserved = max((r.get("reserved_gb", 0.0) for arm in ("line", "span") for r in timing[arm].values()
                    if isinstance(r, dict)), default=0.0)
    timing["memory"] = {"max_reserved_gb": reserved, "guard_limit_gb": limit, "within_guard": reserved <= limit}

    # Stage 1 projection: steps per mode = share x F / FLOPs per step (the trainer stops on the FLOP budget).
    # train_d tracks every `log_every` = 50th step and validates `eval_visits` = 256 DEV visits every 1,000 steps.
    steps = {mode: SHARES[mode] * F_BUDGET / costs[mode] for mode in SHARES}

    def hours(arm: str, modes: list) -> dict:
        t = timing[arm]
        train = sum(steps[m] * t[m]["mean"] for m in modes)
        # own-mode tracking cost applied to every mode (an approximation: tracked steps are 2% of the steps)
        tracked = sum(steps[m] for m in modes) / 50 * max(0.0, t["tracked_extra"])
        data = sum(steps[m] for m in modes) * timing["data_s_per_batch"]
        evals = sum(steps[m] for m in modes) / 1000 * timing[f"validate_s_{arm}"] * 256 / max(len(valid_cache), 1)
        return {"train": train / 3600, "tracked_extra": tracked / 3600, "data": data / 3600, "evals": evals / 3600,
                "total": (train + tracked + data + evals) / 3600}

    parent, line_arm, span_arm = hours("line", ["gold"]), hours("line", ["teacher", "own"]), \
        hours("span", ["teacher", "own"])
    gpu_hours = 3 * parent["total"] + 3 * (line_arm["total"] + span_arm["total"])
    overhead = {m: timing["span"][m]["mean"] / timing["line"][m]["mean"] - 1 for m in PLANS}
    projection = {"memory": timing["memory"], "steps": steps, "steps_total": sum(steps.values()),
                  "hours_parent": parent,
                  "hours_line_arm_95": line_arm, "hours_span_arm_95": span_arm, "stage1_gpu_hours": gpu_hours,
                  "span_overhead": overhead, "dph": args.dph,
                  "stage1_dollars": gpu_hours * args.dph if args.dph else None}
    emit("projection", **projection, timing=timing)

    # 3. smoke: a fresh SPAN model through the whole curriculum. The timing trainers were freed (optimizer state and
    # gradients); LINE and SPAN stay, parameters only, for the final branch check. An exception here is recorded, not
    # raised, so the branch readout still comes; the run then ends failed.
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()
    smoke_step = max(timing["span"][m]["mean"] for m in PLANS) + max(0.0, timing["span"]["tracked_extra"]) \
        + timing["data_s_per_batch"]
    max_seconds = max(args.smoke_seconds, 3.0 * args.smoke_steps * smoke_step)   # the box watchdog bounds the money
    smoke_result: dict = {"max_seconds": max_seconds}
    trainer = smoke = None
    try:
        torch.manual_seed(1)
        smoke = span_cards.build_model(config, span_config)
        trainer = span_cards.SpanTrainer(smoke, mini_train_config(lr=1e-3, warmup_steps=20, log_every=10), device,
                                         flop_budget=1.0, seed=1, fit=fit)
        trainer.flop_budget = budget_for_steps(trainer, batches, args.smoke_steps)
        smoke_stream = pdata.batches(train_cache, args.max_tokens, seed=1, epochs=None, max_visits=args.max_visits)
        started = time.perf_counter()
        report = trainer.train(smoke_stream, max_seconds=max_seconds, max_steps=2 * args.smoke_steps)
        took = time.perf_counter() - started
        finite = all(math.isfinite(float(v)) for r in trainer.history for k, v in r.items()
                     if k in ("loss", "lm", "ask", "ans", "halt") and isinstance(v, (int, float)))
        finite &= all(math.isfinite(v) for r in trainer.span_log for k, v in r.items()
                      if k != "step" and isinstance(v, float))
        phases = sorted({r.get("phase") for r in trainer.history if r.get("phase")})
        stop = str(report.get("stop"))
        smoke_result.update(
            passed=finite and trainer.step > 0 and "own" in phases and stop.startswith("flop budget"),
            steps=trainer.step, seconds=round(took, 1), sec_per_step=took / max(trainer.step, 1), finite=finite,
            stop=stop, flops_share=trainer.flops / trainer.flop_budget, logged_phases=phases,
            reserved_gb=(report.get("peak_gpu_reserved_bytes") or 0) / 1e9,
            last=trainer.history[-1] if trainer.history else None, span_log_last=trainer.span_log[-1:] or None)
    except Exception as error:                            # noqa: BLE001 - recorded; the run ends failed below
        smoke_result.update(passed=False, error=repr(error), trace=traceback.format_exc()[-2000:])
    finally:
        del trainer, smoke                                # free the smoke's model and state before the branch check
        if device.type == "cuda":
            torch.cuda.empty_cache()
    emit("smoke", **smoke_result)

    # 4. branch-point check (LINE as trained by the timing steps; SPAN loaded from it). Last, so that a failure
    # here costs no other measurement; a failure still stops the run with a failed status.
    check = branch_gate(line, span, branch_batches, device)
    emit("branch", visits=branch_visits, **check)
    if not check["passed"]:
        raise SystemExit(f"branch-point check failed ({check['reasons']}): the pairing is broken (run card §3)")
    if not smoke_result["passed"]:
        raise SystemExit("smoke failed: an error, a non-finite loss or gate statistic, no step, the own phase never "
                         "reached, or a stop other than the FLOP budget")


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:                       # noqa: BLE001 - the log is the only channel back
        emit("error", error=repr(error), trace=traceback.format_exc()[-4000:])
        print("STAGE0-DONE failed", flush=True)
        sys.exit(1)
    print("STAGE0-DONE ok", flush=True)
