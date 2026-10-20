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
import json
import platform
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import premonition_reader_kv_guard as guard  # noqa: E402
from premonition.toy import ToySpec, toy_set  # noqa: E402
from premonition.train import label_free, train_toy  # noqa: E402

STEPS, LR, WARMUP, SEEDS = 1500, 1e-3, 100, (0, 1, 2)
EVAL_BATCHES, VISITS = 4, 16          # train_toy's defaults: its held-out set is toy_set(spec, 4, 16, seed + 1000)
ABOVE_CHANCE = 0.05                   # the toy gate's own band (tests/test_premonition_train.py ToyGateTest)
STEP_MATCH = 0.02                     # paired arms must train within 2% of each other's step count
ARMS = {"control": False, "treated": True}


def run(seed: int, flag: bool, steps: int) -> dict:
    started = time.time()
    report = train_toy("D", steps=steps, lr=LR, warmup_steps=WARMUP, seed=seed,
                       config_overrides={"decoder_reader_kv": flag})
    model = report["trainer"].model.eval()
    held_out = [label_free(b) for b in toy_set(ToySpec(), EVAL_BATCHES, VISITS, seed + 1000)]
    parts = [guard.guard_counts(model, batch) for batch in held_out]
    answers = SimpleNamespace(loops=torch.cat([p[0].loops for p in parts]),
                              halt_prob=torch.cat([p[0].halt_prob for p in parts]))
    counts = guard.summarize(answers, *(torch.cat([p[i] for p in parts]) for i in (1, 2, 3)))
    validation = report["validation"]
    train = report["train"]
    return {"seed": seed, "decoder_reader_kv": flag, "parameters": report["parameters"], "chance": report["chance"],
            "steps": train["steps"], "flops": train["flops"], "flop_budget": train["flop_budget"],
            "stop": train["stop"], "train_seconds": train["seconds"], "wall_seconds": time.time() - started,
            "final_losses": train.get("final"),
            "accuracy": validation["accuracy"], "accuracy_gold_cards": validation.get("accuracy_gold_cards"),
            "validate": {k: validation.get(k) for k in ("questions", "asked_rate", "loops_mean", "halt_rate",
                                                         "gold_recall_at_4", "gold_any_at_4")},
            "guard": counts}


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
              <= STEP_MATCH * by[(s, False)]["steps"]} for s in seeds]
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
        for arm, flag in ARMS.items():
            path = out / f"{arm}-s{seed}.json"
            if path.exists():
                row = json.loads(path.read_text())
            else:
                row = run(seed, flag, args.steps)
                path.write_text(json.dumps(row, indent=1, default=float))
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
