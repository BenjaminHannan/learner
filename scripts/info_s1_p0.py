"""S1-P0 (design/info-constraints/REPORT.md, S1): is "7.4% even with gold cards" a card-ring eviction artifact?

$0 CPU probe, ruled E3 (2026-10-18). Main @ 73b8e0224, every module untouched; this script only trains the same tiny
D that `claude/steals-8:scripts/premonition_steals_qk_diagnostic.py` trained (`premonition.train.train_toy`, far-fact
toy, ToySpec() defaults, 380 requested steps, 16 visits, max 1200 s, 2 threads) and then evaluates it several ways
on the same held-out set `train_toy` validates on (`toy_set(spec, 4, visits, seed + 1000)`, label-free).

Conditions (greedy decode, exact match, as `train.validate`):
  own        `model.answer` as shipped (up to 8 loops, ASK when the logit > 0, HALT at p > 0.5)
  own_L4     the same with max_loops = 4 (1 + 3 x 4 = 13 <= 16 card rows: nothing can be evicted)
  gold       `train.answer_with_gold` as shipped: the recorded condition (gold preloaded, then the model's own ASKs)
  gold_L4    the same with max_loops = 4 (no eviction possible)
  gold_noask_L{1,2,4,8}  gold preloaded, then NO further fetch, for 1/2/4/8 think loops (no eviction; the L8 row
             also separates eviction from 8 loops of Think on the card rows)
  nocards_L1 no card at all, one think loop: the card-removal control (added after the first run, see REPORT)
Every condition records its insertions (`train.InsertLog`) and `train.card_stats` (overflowed questions, questions
whose gold card was overwritten before decoding).

Decision line, fixed before any run (REPORT S1-P0): if gold_L4 or gold_noask_L8 lifts gold-card accuracy above 25%
while gold stays near 7.4%, eviction is shown to mask the answer path and S1 builds first. If every gold condition
stays at chance (6.25%), the Think wash (N14) is the binding cause and S2 goes first. Chance = 1 / 16 values.

    python3 -B scripts/info_s1_p0.py --seed 0 [--out artifacts/claude-infoconstraints-20261018/s1-p0-seed0.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any, Optional

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from premonition import train as ptrain                                    # noqa: E402
from premonition.model import Answers, PremonitionMini                      # noqa: E402
from premonition.toy import ToySpec, toy_set                                 # noqa: E402

OUT_DIR = Path("artifacts/claude-infoconstraints-20261018")


@torch.no_grad()
def gold_no_ask(model: PremonitionMini, batch, loops: int, preload_gold: bool = True) -> Answers:
    """`train.answer_with_gold` with every post-preload fetch suppressed and a fixed loop count (HALT ignored)."""
    config = model.config
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    count = batch.q_visit.shape[0]
    everyone = torch.arange(count)
    mentions = model._mentions(batch)
    episode = model._start(batch, hidden, store, mentions)
    gold, _, _ = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
    width = min(gold.shape[1], batch.gold_lines.shape[1] + 1, config.card_rows)
    preload = torch.where(gold, torch.arange(gold.shape[1]),
                          torch.full_like(gold, -1, dtype=torch.long)).topk(width, 1).values
    if preload_gold:
        model._insert(episode, store, everyone, preload)
    halt_prob = torch.zeros(count)
    for step in range(loops):
        _, halt, _, _ = model._step(episode, everyone, step, store)
        halt_prob = torch.sigmoid(halt)
    tokens, lengths = model._greedy(batch, episode, mentions, None)
    return Answers(tokens, lengths, torch.full((count,), loops, dtype=torch.long),
                   torch.full((count, config.top_k), -1, dtype=torch.long), episode.fetched, halt_prob)


def evaluate(model: PremonitionMini, batches: list, name: str, run, offset: int) -> dict[str, Any]:
    """Accuracy, loops, halts and summed `card_stats` of one condition over the held-out batches."""
    config = model.config
    correct = questions = loops = halted = inserted = 0
    cards: dict[str, Any] = {}
    predictions: dict[str, int] = {}
    for batch in batches:
        with ptrain.InsertLog(model) as log:
            answers = run(batch)
        hit, texts = ptrain.judge(answers, batch, eos=config.eos_id)
        for text in texts:
            predictions[text] = predictions.get(text, 0) + 1
        inserted += sum(int((picked >= 0).sum()) for _, picked in log.calls)
        correct += sum(hit)
        questions += len(hit)
        loops += int(answers.loops.sum())
        halted += int((answers.halt_prob > 0.5).sum())
        ptrain._add(cards, ptrain.card_stats(log.calls, batch, answers.loops, config.card_rows, offset=offset))
    return {"condition": name, "questions": questions, "accuracy": correct / max(questions, 1),
            "loops_mean": loops / max(questions, 1), "halt_rate": halted / max(questions, 1),
            "inserts_per_question": inserted / max(questions, 1), "distinct_predictions": len(predictions),
            "top_prediction_share": max(predictions.values(), default=0) / max(questions, 1),
            "cards": ptrain.summarize_cards(cards), "raw": cards}


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--steps", type=int, default=380)
    parser.add_argument("--visits", type=int, default=16)
    parser.add_argument("--max-seconds", type=float, default=1200.0)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    torch.set_num_threads(args.threads)
    spec = ToySpec()
    started = time.perf_counter()
    trained = ptrain.train_toy("D", spec=spec, steps=args.steps, visits=args.visits, seed=args.seed,
                               eval_batches=4, log_every=50, max_seconds=args.max_seconds)
    seconds = time.perf_counter() - started
    model = trained["trainer"].model
    model.eval()
    held_out = [ptrain.label_free(b) for b in toy_set(spec, 4, args.visits, args.seed + 1000)]
    conditions = [
        ("own", lambda b: model.answer(b), 1),
        ("own_L4", lambda b: model.answer(b, max_loops=4), 1),
        ("gold", lambda b: ptrain.answer_with_gold(model, b), 0),
        ("gold_L4", lambda b: ptrain.answer_with_gold(model, b, max_loops=4), 0),
    ] + [(f"gold_noask_L{n}", (lambda n: lambda b: gold_no_ask(model, b, n))(n), 0) for n in (1, 2, 4, 8)] + [
        ("nocards_L1", lambda b: gold_no_ask(model, b, 1, preload_gold=False), 0)]
    rows = [evaluate(model, held_out, name, run, offset) for name, run, offset in conditions]
    validation = trained["validation"]
    result = {
        "probe": "S1-P0", "seed": args.seed, "torch": torch.__version__, "spec": spec.__dict__,
        "chance": trained["chance"], "train_seconds": seconds, "steps_run": trained["trainer"].step,
        "train_toy_validation": {k: validation.get(k) for k in (
            "accuracy", "accuracy_gold_cards", "gold_recall_at_4", "asked_rate", "loops_mean", "halt_rate")},
        "conditions": rows,
    }
    for row in rows:
        c = row["cards"]
        print(f"seed {args.seed} {row['condition']:<15} acc {row['accuracy']:.4f} loops {row['loops_mean']:.2f} "
              f"halt {row['halt_rate']:.2f} inserts/q {row['inserts_per_question']:.2f} "
              f"distinct {row['distinct_predictions']} top {row['top_prediction_share']:.2f} overflow_q {c['fifo_overflow_questions']} "
              f"gold_evicted_q {c['fifo_gold_evicted_questions']} / {row['questions']}", flush=True)
    out = args.out or OUT_DIR / f"s1-p0-seed{args.seed}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1))
    print(f"wrote {out} ({seconds:.0f} s training)")


if __name__ == "__main__":
    main()
