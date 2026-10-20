"""S2 Stage 0 (design/info-constraints/S2-STAGE0-CARD.md): plain D vs D + `decoder_raw_cards`, m02 protocol.

$0 CPU (ruling E3). Far-fact toy v16, gold mode (every gold card preloaded), 2 think loops, answer loss only,
800 steps, AdamW as m02 (`scripts/premonition_m02_answer_path.py`). Scored once at the end on the 1,024-question
test split: greedy with the gold card, greedy with no card, and the distinct-answer counts the card's VOID rule
reads. The marks are in the card; `summarize` applies them verbatim.

    python3 -B scripts/info_s2_stage0.py run --arm control --seed 0
    python3 -B scripts/info_s2_stage0.py summarize
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
import sys
import time

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from learnlab.core import IGNORE_INDEX                                      # noqa: E402
from premonition.config import MiniConfig                                   # noqa: E402
from premonition.model import PremonitionMini                               # noqa: E402
from premonition.toy import ToySpec, toy_set, toy_stream                     # noqa: E402
from premonition.train import label_free                                    # noqa: E402

OUT = Path("artifacts/claude-infoconstraints-20261018/s2-stage0")
TRAIN_SEED, TEST_SEED, VISITS, TEST_BATCHES = 101, 303, 16, 16
STEPS, LOOPS, LR, WARMUP = 800, 2, 1e-3, 100
CHANCE = 1 / 16


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [0.0, 1.0]
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(centre - half, 4), round(centre + half, 4)]


@torch.no_grad()
def greedy(model: PremonitionMini, batch, *, card: bool) -> tuple[list[bool], list[tuple[int, ...]]]:
    """m02 `greedy_correct`: gold card preloaded (or none), LOOPS think passes, no fetches."""
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    mentions = model._mentions(batch)
    episode = model._start(batch, hidden, store, mentions)
    count = batch.q_visit.shape[0]
    device = hidden.device
    everyone = torch.arange(count, device=device)
    if card:
        gold, _, missing = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
        if int(missing.sum()):
            raise RuntimeError("gold card missing")
        width = min(gold.shape[1], batch.gold_lines.shape[1] + 1, model.config.card_rows)
        preload = torch.where(gold, torch.arange(gold.shape[1], device=device),
                              torch.full_like(gold, -1, dtype=torch.long)).topk(width, 1).values
        model._insert(episode, store, everyone, preload)
    for step in range(LOOPS):
        model._step(episode, everyone, step, store)
    tokens, lengths = model._greedy(batch, episode, mentions, None)
    ok, said = [], []
    for q in range(count):
        target = batch.answer[q][batch.answer[q] != IGNORE_INDEX].tolist()
        mine = tokens[q, :int(lengths[q])].tolist()
        ok.append(mine == target)
        said.append(tuple(mine))
    return ok, said


def score(model: PremonitionMini, batches: list, *, card: bool) -> dict:
    was = model.training
    model.eval()
    ok, said = [], []
    for batch in batches:
        a, b = greedy(model, batch, card=card)
        ok += a
        said += b
    model.train(was)
    k, n = sum(ok), len(ok)
    first = sum(b.q_visit.shape[0] for b in batches[:4])
    return {"correct": k, "n": n, "acc": k / n, "wilson95": wilson(k, n),
            "distinct_256": len(set(said[:first])), "distinct_1024": len(set(said)), "first_n": first}


def cmd_run(args) -> None:
    torch.set_num_threads(args.threads)
    spec = ToySpec()
    torch.manual_seed(args.seed)
    config = MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64,
                               decoder_raw_cards=args.arm == "treated")
    model = PremonitionMini(config)
    params = list(model.parameters())
    optimizer = torch.optim.AdamW(
        [{"params": [p for p in params if p.dim() >= 2], "weight_decay": 0.1},
         {"params": [p for p in params if p.dim() < 2], "weight_decay": 0.0}],
        lr=LR, betas=(0.9, 0.99), eps=1e-8)
    stream = (label_free(b) for b in toy_stream(spec, VISITS, TRAIN_SEED))
    history, finite, started = [], True, time.perf_counter()
    for step in range(STEPS):
        for group in optimizer.param_groups:
            group["lr"] = LR * min(1.0, (step + 1) / WARMUP)
        batch = next(stream)
        loss = model.forward(batch, mode="gold", loops=LOOPS, weights={"ans": 1.0})["ans"]
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        finite &= all(p.grad is None or bool(torch.isfinite(p.grad).all()) for p in params)
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        optimizer.step()
        if (step + 1) % 100 == 0 or step == 0:
            history.append({"step": step + 1, "loss": round(float(loss.detach()), 4),
                            "seconds": round(time.perf_counter() - started, 1)})
            print(json.dumps(history[-1]), flush=True)
    seconds = time.perf_counter() - started
    test = [label_free(b) for b in toy_set(spec, TEST_BATCHES, VISITS, TEST_SEED)]
    result = {"arm": args.arm, "seed": args.seed, "steps_run": STEPS, "finite": finite, "seconds": seconds,
              "torch": torch.__version__, "parameters": model.num_parameters(), "config": config.variant,
              "decoder_raw_cards": config.decoder_raw_cards, "history": history,
              "with_card": score(model, test, card=True), "no_card": score(model, test, card=False)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{args.arm}-seed{args.seed}.json").write_text(json.dumps(result, indent=1))
    w, r = result["with_card"], result["no_card"]
    print(f"{args.arm} seed {args.seed}: acc {w['acc']:.4f} ({w['correct']}/{w['n']}) distinct_256 "
          f"{w['distinct_256']} distinct_1024 {w['distinct_1024']} | no card {r['acc']:.4f} "
          f"distinct_256 {r['distinct_256']} | {seconds:.0f} s, finite {finite}")


def cmd_summarize(args) -> None:
    """Apply the card's §4-§6 marks verbatim."""
    rows = {}
    for seed in (0, 1, 2):
        pair = {}
        for arm in ("control", "treated"):
            path = OUT / f"{arm}-seed{seed}.json"
            if path.exists():
                pair[arm] = json.loads(path.read_text())
        if len(pair) == 2:
            rows[seed] = pair
    cells = []
    for seed, pair in sorted(rows.items()):
        c, t = pair["control"], pair["treated"]
        cells.append({"seed": seed, "void": c["with_card"]["distinct_256"] == 1,
                      "control_acc": c["with_card"]["acc"], "treated_acc": t["with_card"]["acc"],
                      "d": t["with_card"]["acc"] - c["with_card"]["acc"],
                      "control_distinct_256": c["with_card"]["distinct_256"],
                      "treated_distinct_256": t["with_card"]["distinct_256"],
                      "control_removed": c["no_card"]["acc"], "treated_removed": t["no_card"]["acc"],
                      "finite_and_complete": all(x["finite"] and x["steps_run"] == STEPS for x in (c, t))})
    valid = [x for x in cells if not x["void"]]
    n = len(valid)
    verdict, why = "INCONCLUSIVE", []
    if len(cells) == 3 and n == 0:
        verdict, why = "VOID", ["every control cell gave one distinct answer over 256 questions"]
    elif n >= 2:
        d = [x["d"] for x in valid]
        mean = statistics.fmean(d)
        bound = mean - 2 * statistics.stdev(d) / math.sqrt(n)
        passes = {
            "treated_acc_ge_50_every_valid_seed": all(x["treated_acc"] >= 0.5 for x in valid),
            "d_positive_every_valid_seed": all(x["d"] > 0 for x in valid),
            "mean_minus_2se_positive": bound > 0,
            "card_use_guard_removed_le_9.25pct": all(x["treated_removed"] <= CHANCE + 0.03 for x in valid),
            "treated_distinct_256_gt_1": all(x["treated_distinct_256"] > 1 for x in valid),
            "finite_and_complete": all(x["finite_and_complete"] for x in valid)}
        fail = sum(x["treated_acc"] < 0.25 for x in valid) >= 2 or mean <= 0.03
        verdict = "PASS" if all(passes.values()) else ("FAIL" if fail else "INCONCLUSIVE")
        wrong = sum(abs(x["d"]) <= 0.03 for x in valid) >= 2 or not passes["card_use_guard_removed_le_9.25pct"]
        why = [{"mean_d": mean, "mean_minus_2se": bound, "marks": passes, "fail_rule": fail,
                "proves_S2_wrong_rule": wrong}]
    else:
        why = [f"{n} valid seed(s) of {len(cells)} complete pairs; the card needs n >= 2"]
    summary = {"verdict": verdict, "valid_seeds": n, "cells": cells, "detail": why}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--arm", choices=("control", "treated"), required=True)
    run.add_argument("--seed", type=int, required=True)
    run.add_argument("--threads", type=int, default=1)
    sub.add_parser("summarize")
    args = parser.parse_args()
    {"run": cmd_run, "summarize": cmd_summarize}[args.cmd](args)


if __name__ == "__main__":
    main()
