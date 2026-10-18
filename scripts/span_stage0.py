"""Span cards SC-1, Stage 0 (design/span-cards/03-funding-bid.md, ruling Q22): measure before spending.

On one GPU box, in this order, each step printed as a `STAGE0 {json}` line (the box's log is the only channel
back, so partial results survive a stop):
1. data: fresh label-free v2 caches from the step-1 simulator (seed 0): `--train-visits` train and
   `--valid-visits` validation visits, the premonition-tok-v2-fallback tokenizer, a fitted name detector;
   N = `span_cards.tokens_per_line(train cache)` at this size.
2. timing: seconds per training step for LINE (`MiniTrainer`) and SPAN (`SpanTrainer`, loaded from LINE's
   weights) in gold, teacher and own (p_own 0.75) mode on the same real batches (max_tokens 55,000, max_visits
   48), after warm-up, with the FLOP fit; and one validation pass. Then the Stage 1 projection: steps per mode
   from F = 3.15e16 and the curriculum shares, 3 parents (LINE, 5% of F) + Cell A (LINE and SPAN x 3 seeds x 95%).
3. branch: SPAN loaded from the (briefly trained) LINE model must give identical `answer()` on 64 DEV visits.
4. smoke: a fresh SPAN model through the whole curriculum in about 200 SpanTrainer steps; losses must be finite.
`STAGE0-DONE` ends the log. Nothing is saved but the log; the box is destroyed after it is read.
"""
from __future__ import annotations

import argparse
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

from learnlab.tokenizer import Tokenizer                                     # noqa: E402
from learnlab.village.shards import write_shards                             # noqa: E402
from premonition import data as pdata, preprocess, span_cards                # noqa: E402
from premonition.config import MiniConfig                                     # noqa: E402
from premonition.model import PremonitionMini                                 # noqa: E402
from premonition.train import (MiniTrainer, Plan, budget_for_steps, mini_train_config, planned_loops,  # noqa: E402
                               validate)

F_BUDGET = 3.15e16                       # design/06 §4 (A's v2 budget run), the bid's F
SHARES = {"gold": 0.05, "teacher": 0.25, "own": 0.70}   # Curriculum(): gold to 5%, teacher to 30%, own after
PLANS = {"gold": Plan("gold", "gold", 0.0), "teacher": Plan("teacher", "teacher", 0.0),
         "own": Plan("own", "own", 0.75)}
STARTED = time.perf_counter()


def emit(step: str, **values) -> None:
    print("STAGE0 " + json.dumps({"step": step, "t": round(time.perf_counter() - STARTED, 1), **values},
                                 default=str), flush=True)


def sync(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize()


def build(work: Path, split: str, visits: int, workers: int) -> None:
    write_shards(split, visits, work, workers, seed=0, verbose=False)


def time_steps(trainer: MiniTrainer, batches, plan: Plan, warm: int, timed: int) -> dict:
    device = trainer.device
    config = trainer.model.config
    seconds = []
    for i, batch in enumerate(batches[:warm + timed]):
        loops = planned_loops(batch, plan.mode, config)
        sync(device)
        start = time.perf_counter()
        out = trainer._train_step(batch, plan, loops, track=False)
        loss = float(out["loss"])
        sync(device)
        if not math.isfinite(loss):
            raise FloatingPointError(f"{plan.mode} loss {loss}")
        if i >= warm:
            seconds.append(time.perf_counter() - start)
    seconds.sort()
    return {"mean": sum(seconds) / len(seconds), "median": seconds[len(seconds) // 2], "max": seconds[-1],
            "n": len(seconds)}


def mode_costs(trainer: MiniTrainer, batches) -> dict:
    config = trainer.model.config
    return {mode: sum(trainer.fit(b.tokens.numel(), int(planned_loops(b, plan.mode, config).sum()))
                      for b in batches) / len(batches) for mode, plan in PLANS.items()}


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
    parser.add_argument("--smoke-seconds", type=float, default=900.0)
    parser.add_argument("--branch-visits", type=int, default=64)
    parser.add_argument("--dph", type=float, default=0.0, help="the box's $/hour, for the projection")
    args = parser.parse_args()
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

    # 2. timing
    torch.manual_seed(0)
    config = MiniConfig.preset("D", args.size, vocab_size=tokenizer.vocab_size)
    line = PremonitionMini(config)
    span_config = span_cards.SpanConfig(enabled=True, tokens_per_card=n_target, newline_id=23)
    timing: dict = {"params": line.num_parameters()}
    huge = 1e30
    line_trainer = MiniTrainer(line, mini_train_config(lr=1e-3, warmup_steps=100), device, flop_budget=huge, seed=0)
    fit = line_trainer.calibrate(batches[:4])
    timing["fit"] = {"a": fit.a, "b": fit.b, "worst": fit.worst}
    costs = mode_costs(line_trainer, batches)
    timing["flops_per_step"] = costs
    for mode, plan in PLANS.items():
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats()
        timing[f"line_{mode}"] = time_steps(line_trainer, batches, plan, args.warm, args.timed)
        if device.type == "cuda":
            timing[f"line_{mode}"]["peak_gb"] = torch.cuda.max_memory_allocated() / 1e9
        emit("timing", arm="LINE", mode=mode, **timing[f"line_{mode}"])
    branch_state = {k: v.detach().clone() for k, v in line.state_dict().items()}
    torch.manual_seed(0)
    span = span_cards.build_model(config, span_config)
    missing, unexpected = span.load_state_dict(branch_state, strict=False)
    span.writer.init_gate()
    span_trainer = span_cards.SpanTrainer(span, mini_train_config(lr=1e-3, warmup_steps=100), device,
                                          flop_budget=huge, seed=0, fit=fit)
    for mode, plan in PLANS.items():
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats()
        timing[f"span_{mode}"] = time_steps(span_trainer, batches, plan, args.warm, args.timed)
        if device.type == "cuda":
            timing[f"span_{mode}"]["peak_gb"] = torch.cuda.max_memory_allocated() / 1e9
        emit("timing", arm="SPAN", mode=mode, **timing[f"span_{mode}"])
    line.eval()
    sync(device)
    started = time.perf_counter()
    validate(line, dev)
    sync(device)
    timing["validate_256_s"] = time.perf_counter() - started
    line.train()

    # Stage 1 projection: steps per mode = share x F / FLOPs per step (the trainer stops on the FLOP budget).
    steps = {mode: SHARES[mode] * F_BUDGET / costs[mode] for mode in SHARES}
    sec = lambda arm, modes: sum(steps[m] * timing[f"{arm}_{m}"]["mean"] for m in modes)
    parent = sec("line", ["gold"])
    line_rest = sec("line", ["teacher", "own"])
    span_rest = sec("span", ["teacher", "own"])
    evals = sum(steps.values()) / 1000 * timing["validate_256_s"]          # train_d: eval every 1000 steps
    seconds = 3 * parent + 3 * (line_rest + span_rest) + 6 * evals
    overhead = {m: timing[f"span_{m}"]["mean"] / timing[f"line_{m}"]["mean"] - 1 for m in PLANS}
    projection = {"steps": steps, "steps_total": sum(steps.values()), "hours_parent": parent / 3600,
                  "hours_line_95": line_rest / 3600, "hours_span_95": span_rest / 3600,
                  "hours_evals_per_run": evals / 3600, "stage1_gpu_hours": seconds / 3600,
                  "span_overhead": overhead, "dph": args.dph,
                  "stage1_dollars": seconds / 3600 * args.dph if args.dph else None}
    emit("projection", **projection, timing=timing)

    # 3. branch-point identity (LINE as trained for the timing steps; SPAN loaded from it)
    span.eval()
    line.eval()
    same, compared, key_diff = True, 0, 0.0
    chosen = list(range(min(args.branch_visits, len(valid_cache))))
    for group in pdata.length_batches(valid_cache.lengths[chosen].tolist(), args.max_tokens, max_visits=args.max_visits):
        batch = pdata.collate(valid_cache, [chosen[i] for i in group]).to(device)
        span.load_state_dict(line.state_dict(), strict=False)
        span.writer.init_gate()
        with torch.no_grad():
            a, b = line.answer(batch), span.answer(batch)
            plain = line.build_store(line.read(batch), batch)
            spans = span.build_store(span.read(batch), batch)
            bi, ei = torch.nonzero(spans.valid, as_tuple=True)
            key_diff = max(key_diff, float((spans.keys[bi, ei] - plain.keys[bi, batch.line_of[bi, ei]]).abs().max()))
        for name in ("tokens", "lengths", "loops", "first_top", "fetched"):
            same &= bool(torch.equal(getattr(a, name), getattr(b, name)))
        same &= bool(torch.equal(spans.valid, batch.card_end))
        compared += int(batch.q_visit.shape[0])
    emit("branch", identical=same, questions=compared, visits=len(chosen), max_key_diff=key_diff,
         gate_missing=sorted(missing), unexpected=unexpected)

    # 4. smoke: a fresh SPAN model through the whole curriculum
    torch.manual_seed(1)
    smoke = span_cards.build_model(config, span_config)
    trainer = span_cards.SpanTrainer(smoke, mini_train_config(lr=1e-3, warmup_steps=20, log_every=10), device,
                                     flop_budget=1.0, seed=1, fit=fit)
    trainer.flop_budget = budget_for_steps(trainer, batches, args.smoke_steps)
    smoke_stream = pdata.batches(train_cache, args.max_tokens, seed=1, epochs=None, max_visits=args.max_visits)
    started = time.perf_counter()
    report = trainer.train(smoke_stream, max_seconds=args.smoke_seconds, max_steps=int(args.smoke_steps * 1.2))
    took = time.perf_counter() - started
    finite = all(math.isfinite(float(v)) for r in trainer.history for k, v in r.items()
                 if k in ("loss", "lm", "ask", "ans", "halt") and isinstance(v, (int, float)))
    finite &= all(math.isfinite(v) for r in trainer.span_log for k, v in r.items()
                  if k != "step" and isinstance(v, float))
    phases = sorted({r.get("phase") for r in trainer.history if r.get("phase")})
    emit("smoke", steps=trainer.step, seconds=round(took, 1), sec_per_step=took / max(trainer.step, 1),
         finite=finite, flops_share=trainer.flops / trainer.flop_budget, phases=phases,
         last=trainer.history[-1] if trainer.history else None, span_log_last=trainer.span_log[-1:] or None,
         keys=sorted(report))


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:                       # noqa: BLE001 - the log is the only channel back
        emit("error", error=repr(error), trace=traceback.format_exc()[-4000:])
    print("STAGE0-DONE", flush=True)
