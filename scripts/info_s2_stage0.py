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

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/claude-infoconstraints-20261018/s2-stage0"
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


def train_arm(args):
    """§2 training of one arm; returns (model, config, history, finite, seconds, steps_done)."""
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
    history, finite, started, steps_done = [], True, time.perf_counter(), 0
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
        steps_done = step + 1
        if (step + 1) % 100 == 0 or step == 0:
            history.append({"step": step + 1, "loss": round(float(loss.detach()), 4),
                            "seconds": round(time.perf_counter() - started, 1)})
            print(json.dumps(history[-1]), flush=True)
    return model, config, history, finite, time.perf_counter() - started, steps_done


def cmd_run(args) -> None:
    model, config, history, finite, seconds, steps_done = train_arm(args)
    spec = ToySpec()
    test = [label_free(b) for b in toy_set(spec, TEST_BATCHES, VISITS, TEST_SEED)]
    result = {"arm": args.arm, "seed": args.seed, "steps_run": steps_done, "finite": finite, "seconds": seconds,
              "torch": torch.__version__, "parameters": model.num_parameters(), "config": config.variant,
              "decoder_raw_cards": config.decoder_raw_cards, "history": history,
              "with_card": score(model, test, card=True), "no_card": score(model, test, card=False)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{args.arm}-seed{args.seed}.json").write_text(json.dumps(result, indent=1))
    w, r = result["with_card"], result["no_card"]
    print(f"{args.arm} seed {args.seed}: acc {w['acc']:.4f} ({w['correct']}/{w['n']}) distinct_256 "
          f"{w['distinct_256']} distinct_1024 {w['distinct_1024']} | no card {r['acc']:.4f} "
          f"distinct_256 {r['distinct_256']} | {seconds:.0f} s, finite {finite}")


@torch.no_grad()
def distract(model: PremonitionMini, batches: list, n: int) -> dict:
    """Card §10: gold card + n shuffled other fact cards of the visit (m02 `distractor_preload`, generator seed
    7000 + n), LOOPS think passes, greedy, exact match; plus m02's distractor-value count."""
    was = model.training
    model.eval()
    generator = torch.Generator().manual_seed(7000 + n)
    ok, said, other = [], [], 0
    for batch in batches:
        hidden = model.read(batch)
        store = model.build_store(hidden, batch)
        mentions = model._mentions(batch)
        episode = model._start(batch, hidden, store, mentions)
        gold, _, _ = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
        pool = store.eligible(batch.q_visit, batch.q_line) & ~gold
        pool[:, store.null] = False
        noise = torch.rand(pool.shape, generator=generator).masked_fill(~pool, -1.0)
        best, extra = noise.topk(n, 1)
        extra = extra.masked_fill(best < 0, -1)
        cards = torch.cat([batch.gold_lines[:, :1], extra], dim=1)
        cards = cards.gather(1, torch.rand(cards.shape, generator=generator).argsort(1))
        count = batch.q_visit.shape[0]
        everyone = torch.arange(count, device=hidden.device)
        model._insert(episode, store, everyone, cards)
        for step in range(LOOPS):
            model._step(episode, everyone, step, store)
        tokens, lengths = model._greedy(batch, episode, mentions, None)
        for q in range(count):
            target = batch.answer[q][batch.answer[q] != IGNORE_INDEX].tolist()
            mine = tokens[q, :int(lengths[q])].tolist()
            ok.append(mine == target)
            said.append(tuple(mine))
            v = int(batch.q_visit[q])
            values = {int(batch.tokens[v, int(batch.line_start[v, int(c)]) + 3]) for c in cards[q]
                      if int(c) >= 0 and int(c) != int(batch.gold_lines[q, 0])}
            first = int(tokens[q, 0])
            other += first in values and first != int(batch.answer[q, 0])
    model.train(was)
    k, total = sum(ok), len(ok)
    head = sum(b.q_visit.shape[0] for b in batches[:4])
    return {"n_distractors": n, "correct": k, "n": total, "acc": k / total, "wilson95": wilson(k, total),
            "predicts_distractor_value": other, "distinct_256": len(set(said[:head])),
            "distinct_1024": len(set(said)), "copy_a_random_card_rate": 1 / (1 + n)}


def cmd_distract(args) -> None:
    """Card §10: retrain one arm (§2, 1 thread), assert it reproduces its filed §9 score, then read n = 2."""
    filed = json.loads((OUT / f"{args.arm}-seed{args.seed}.json").read_text())["with_card"]
    model, config, history, finite, seconds, steps_done = train_arm(args)
    test = [label_free(b) for b in toy_set(ToySpec(), TEST_BATCHES, VISITS, TEST_SEED)]
    again = score(model, test, card=True)
    reproduced = all(again[f] == filed[f] for f in ("correct", "distinct_256", "distinct_1024"))
    result = {"arm": args.arm, "seed": args.seed, "threads": args.threads, "steps_run": steps_done,
              "finite": finite, "seconds": seconds, "reproduced_stage0": reproduced,
              "stage0_filed": {f: filed[f] for f in ("correct", "distinct_256", "distinct_1024")},
              "stage0_again": {f: again[f] for f in ("correct", "distinct_256", "distinct_1024")},
              "d2": distract(model, test, 2) if reproduced else None}
    out = OUT.parent / "s2-distract"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.arm}-seed{args.seed}.json").write_text(json.dumps(result, indent=1))
    d2 = result["d2"]
    print(f"{args.arm} seed {args.seed}: reproduced {reproduced}"
          + (f" | d2 acc {d2['acc']:.4f} ({d2['correct']}/{d2['n']}) distractor-value {d2['predicts_distractor_value']} "
             f"distinct_256 {d2['distinct_256']} distinct_1024 {d2['distinct_1024']}" if d2 else ""))


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
    missing = [f"{arm}-seed{seed}" for seed in (0, 1, 2) for arm in ("control", "treated")
               if not (OUT / f"{arm}-seed{seed}.json").exists()]
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
    if missing:                                    # mark 5 needs every run of the card: no verdict without them
        verdict, why = "INCOMPLETE", [f"missing runs: {missing}"]
    elif len(cells) == 3 and n == 0:
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
            "finite_and_complete": all(x["finite_and_complete"] for x in cells)}   # every run, VOID or not
        fail = sum(x["treated_acc"] < 0.25 for x in valid) >= 2 or mean <= 0.03
        wrong = sum(abs(x["d"]) <= 0.03 for x in valid) >= 2 or not passes["card_use_guard_removed_le_9.25pct"]
        # The card does not rank its rules; a firing FAIL or proves-wrong rule always blocks a PASS.
        verdict = ("FAIL" if fail or wrong else
                   "PASS" if all(passes.values()) else "INCONCLUSIVE")
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
    dis = sub.add_parser("distract")
    dis.add_argument("--arm", choices=("control", "treated"), required=True)
    dis.add_argument("--seed", type=int, required=True)
    dis.add_argument("--threads", type=int, default=1)
    args = parser.parse_args()
    {"run": cmd_run, "summarize": cmd_summarize, "distract": cmd_distract}[args.cmd](args)


if __name__ == "__main__":
    main()
