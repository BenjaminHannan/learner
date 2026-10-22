"""Stage 0 of the decoder_reader_kv A/B (artifacts/claude-rkv-20261017/RUN-CARD.md section 12).

The far-fact toy at the toy gate's own settings (`train_toy("D", steps=1500, lr=1e-3, warmup_steps=100)`),
control vs `decoder_reader_kv=True`, seeds 0-2, CPU, $0. Per run: held-out toy accuracy (own retrieval and
gold cards), steps and FLOPs, and the guard counts on the same held-out set. Writes one JSON per run and
STAGE0.json with the gate reading against the marks fixed in the card.

    python scripts/premonition_reader_kv_stage0.py --out artifacts/claude-rkv-20261017/stage0
    python scripts/premonition_reader_kv_stage0.py --out /tmp/smoke --steps 10 --seeds 0   # smoke only
"""
from __future__ import annotations

import argparse
import itertools
import json
import platform
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import premonition_reader_kv_guard as guard  # noqa: E402
from premonition.config import MiniConfig  # noqa: E402
from premonition.model import PremonitionMini  # noqa: E402
from premonition.toy import ToySpec, toy_set, toy_stream  # noqa: E402
from premonition.train import (MiniTrainer, budget_for_steps, label_free, mini_train_config,  # noqa: E402
                               validation_hook)

STEPS, LR, WARMUP, SEEDS = 1500, 1e-3, 100, (0, 1, 2)
EVAL_BATCHES, VISITS = 4, 16          # train_toy's defaults: its held-out set is toy_set(spec, 4, 16, seed + 1000)
ABOVE_CHANCE = 0.05                   # the toy gate's own band (tests/test_premonition_train.py ToyGateTest)
STEP_MATCH = 0.0                      # Addendum A: paired arms must train IDENTICAL step counts
ARMS = {"control": False, "treated": True}


def train_arm(seed: int, flag: bool, steps: int, matched: Optional[tuple] = None) -> dict:
    """`premonition.train.train_toy("D", ...)` step for step, except that with `matched` = (fit, budget) of the
    control arm the run counts FLOPs with the control's fit and stops at the control's budget (Addendum A).

    Counted FLOPs per step are fit(tokens, planned loops); both depend only on the data and on the curriculum
    plan, which depends only on counted FLOPs / budget. With the control's fit and budget the treated arm
    therefore takes the same steps through the same phases. It still runs its own `calibrate` first, so its
    trainer generator (teacher distractors) is drawn exactly as the control's. Its own fit is kept for its
    true FLOPs."""
    spec = ToySpec()
    torch.manual_seed(seed)
    model = PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64,
                                              decoder_reader_kv=flag))
    trainer = MiniTrainer(model, mini_train_config(lr=LR, warmup_steps=WARMUP, log_every=25, eval_every=0),
                          "cpu", flop_budget=1.0, seed=seed)
    stream = (label_free(b) for b in toy_stream(spec, VISITS, seed))
    head = [next(stream) for _ in range(2)]
    own_fit = trainer.calibrate(head)
    own_budget = budget_for_steps(trainer, head, steps)
    trainer.flop_budget = own_budget
    if matched is not None:
        trainer.fit, trainer.flop_budget = matched
    held_out = [label_free(b) for b in toy_set(spec, EVAL_BATCHES, VISITS, seed + 1000)]
    phases: list[tuple[int, str]] = []
    plan = trainer.plan

    def recorded():                                       # read-only: the phase every training step uses
        current = plan()
        phases.append((trainer.step, current.phase))
        return current

    trainer.plan = recorded
    try:
        report = trainer.train(itertools.chain(head, stream))
    finally:
        del trainer.plan
    validation = trainer.evaluate(validation_hook(held_out))
    return {"trainer": trainer, "train": report, "validation": validation, "chance": spec.chance,
            "parameters": model.num_parameters(), "own_fit": own_fit, "own_budget": own_budget,
            "phases": phases}


def run(seed: int, flag: bool, steps: int, matched: Optional[tuple] = None) -> tuple[dict, tuple]:
    started = time.time()
    report = train_arm(seed, flag, steps, matched)
    model = report["trainer"].model.eval()
    held_out = [label_free(b) for b in toy_set(ToySpec(), EVAL_BATCHES, VISITS, seed + 1000)]
    parts = [guard.guard_counts(model, batch) for batch in held_out]
    answers = SimpleNamespace(loops=torch.cat([p[0].loops for p in parts]),
                              halt_prob=torch.cat([p[0].halt_prob for p in parts]))
    counts = guard.summarize(answers, *(torch.cat([p[i] for p in parts]) for i in (1, 2, 3)))
    validation = report["validation"]
    train = report["train"]
    trainer = report["trainer"]
    row = {"seed": seed, "decoder_reader_kv": flag, "parameters": report["parameters"], "chance": report["chance"],
            "steps": train["steps"], "flops": train["flops"], "flop_budget": train["flop_budget"],
            "matched_to_control": matched is not None, "own_fit": {"a": report["own_fit"].a, "b": report["own_fit"].b},
            "own_budget_for_steps": report["own_budget"],
            "own_cost_vs_counted": report["own_budget"] / train["flop_budget"],     # treated's true FLOPs / counted
            "phases": report["phases"],
            "stop": train["stop"], "train_seconds": train["seconds"], "wall_seconds": time.time() - started,
            "final_losses": train.get("final"),
            "accuracy": validation["accuracy"], "accuracy_gold_cards": validation.get("accuracy_gold_cards"),
            "validate": {k: validation.get(k) for k in ("questions", "asked_rate", "loops_mean", "halt_rate",
                                                         "gold_recall_at_4", "gold_any_at_4")},
            "guard": counts}
    return row, (trainer.fit, trainer.flop_budget)


def gate(rows: list[dict], seeds: tuple[int, ...]) -> dict:
    """The card's stage 0 reading (section 12): marks fixed before any run."""
    by = {(r["seed"], r["decoder_reader_kv"]): r for r in rows}
    chance = rows[0]["chance"]
    control = [by[(s, False)]["guard"] for s in seeds]
    treated = [by[(s, True)]["guard"] for s in seeds]
    control_cards = sum(c["cards_per_question"] for c in control) / len(control)
    need = 2 if len(seeds) == 3 else len(seeds)                      # family rule: 2 of 3
    above = {arm: sum(by[(s, flag)]["accuracy"] > chance + ABOVE_CHANCE for s in seeds)
             for arm, flag in ARMS.items()}
    steps = [{"seed": s, "control": by[(s, False)]["steps"], "treated": by[(s, True)]["steps"],
              "matched": abs(by[(s, True)]["steps"] - by[(s, False)]["steps"])
              <= STEP_MATCH * by[(s, False)]["steps"]
              and [tuple(x) for x in by[(s, True)]["phases"]] == [tuple(x) for x in by[(s, False)]["phases"]]}
             for s in seeds]
    marks = {"G1_control_fetches": control_cards > 0,
             "G2_an_arm_above_chance": any(n >= need for n in above.values()),
             "V1_steps_matched": all(s["matched"] for s in steps)}
    if not marks["V1_steps_matched"]:
        reading = "INVALID: paired arms did not train matched step counts"
    elif marks["G1_control_fetches"] and marks["G2_an_arm_above_chance"]:
        reading = "PASS: stages 1+2 may book (with the review passed and the card sealed)"
    else:
        reading = "FAIL: no GPU spend; the village A/B could not produce a gain that counts"
    return {"reading": reading, "marks": marks, "chance": chance, "above_chance_threshold": chance + ABOVE_CHANCE,
            "seeds_above_chance": above, "seeds_needed": need, "control_cards_per_question": control_cards,
            "steps": steps,
            "paired_accuracy_difference": [by[(s, True)]["accuracy"] - by[(s, False)]["accuracy"] for s in seeds],
            "guard_on_toy_report_only": guard.guard_verdict(control, treated) if control_cards > 0 else None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", required=True)
    parser.add_argument("--steps", type=int, default=STEPS)
    parser.add_argument("--seeds", default=",".join(map(str, SEEDS)))
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    seeds = tuple(int(s) for s in args.seeds.split(","))
    meta = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "torch": torch.__version__,
            "python": platform.python_version(), "machine": platform.machine(), "threads": torch.get_num_threads(),
            "steps": args.steps, "seeds": seeds, "lr": LR, "warmup_steps": WARMUP}
    (out / "META.json").write_text(json.dumps(meta, indent=1))
    rows = []
    for seed in seeds:
        matched = None                                   # control first; treated reuses its fit and budget
        for arm, flag in ARMS.items():
            row, counted = run(seed, flag, args.steps, matched)
            matched = counted if matched is None else matched
            (out / f"{arm}-s{seed}.json").write_text(json.dumps(row, indent=1, default=float))
            rows.append(row)
            print(f"{arm} s{seed}: steps {row['steps']} acc {row['accuracy']:.3f} gold {row['accuracy_gold_cards']} "
                  f"cards/q {row['guard']['cards_per_question']:.2f} asks/q {row['guard']['asks_per_question']:.2f} "
                  f"({row['wall_seconds']:.0f}s)", flush=True)
    result = {"meta": meta, "rows": rows, "gate": gate(rows, seeds),
              "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (out / "STAGE0.json").write_text(json.dumps(result, indent=1, default=float))
    print(json.dumps(result["gate"], indent=1, default=float))


if __name__ == "__main__":
    main()
