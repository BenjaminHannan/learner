"""Run card R1, stage 0 (design/steals-2026-10-17/REPORT.md): Muon against AdamW on the far-fact toy, CPU, $0.

Arms (each differs from A0 only in the optimizer with its lr): A0 AdamW 3e-3, A1 Muon 3e-3 (recipe), A2 Muon 2e-2.
Seeds 0-2, tiny D, `steps` batches' FLOP budget each (the model is bit-identical across arms at a seed, so every
arm trains the same steps on the same batches). Arm order rotates across seeds so machine drift hits every arm.

Primary readout: held-out loss (teacher mode, fixed loops, 4 fixed held-out toy batches, fixed distractor seed) every
`--eval-every` steps under no_grad, evaluation time off the clock; interpolated at T* = the shorter arm's training
seconds. Bar (card section 5): mean(d) - 2 SD(d)/sqrt(n) > 0, d_s > 0 in >= 2 of 3 seeds, mean(d) >= 3% of A0's
loss at T*. Guard (section 6): Ak's held-out accuracy more than 3 points below A0's in >= 2 of 3 seeds voids a pass.

    OMP_NUM_THREADS=1 python3 -B scripts/premonition_steals_r1_stage0.py --out artifacts/claude-steals-20261017/r1-stage0
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import platform
import statistics
import sys
import time

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from premonition import train as ptrain                                     # noqa: E402
from premonition.config import MiniConfig                                    # noqa: E402
from premonition.model import PremonitionMini                                 # noqa: E402
from premonition.toy import ToySpec, toy_set, toy_stream                      # noqa: E402

ARMS = {"A0": ("adamw", 3e-3), "A1": ("muon", 3e-3), "A2": ("muon", 2e-2)}
EVAL_LOOPS = 4
MIN_EFFECT = 0.03                     # relative, for the loss readout (Q42)
GUARD_POINTS = 0.03


@torch.no_grad()
def held_out_loss(model: PremonitionMini, batches: list) -> float:
    """Mean teacher-mode loss over fixed batches, fixed loop count and distractor seed (no curriculum, no noise)."""
    was = model.training
    model.eval()
    losses = [float(model(b, mode="teacher", loops=EVAL_LOOPS, generator=torch.Generator().manual_seed(1234 + i))["loss"])
              for i, b in enumerate(batches)]
    model.train(was)
    return statistics.fmean(losses)


def run(arm: str, seed: int, steps: int, eval_every: int, visits: int, log) -> dict:
    optimizer, lr = ARMS[arm]
    spec = ToySpec()
    torch.manual_seed(seed)
    model = PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64))
    trainer = ptrain.MiniTrainer(model, ptrain.mini_train_config(lr=lr, warmup_steps=20, log_every=eval_every),
                                 "cpu", flop_budget=1.0, seed=seed, optimizer=optimizer)
    stream = (ptrain.label_free(b) for b in toy_stream(spec, visits, seed))
    head = [next(stream) for _ in range(2)]
    trainer.calibrate(head)
    trainer.flop_budget = ptrain.budget_for_steps(trainer, head, steps)
    held_out = [ptrain.label_free(b) for b in toy_set(spec, 4, visits, seed + 1000)]
    optimizer_seconds = [0.0]
    step_fn = trainer.optimizer.step

    def timed_step(*args, **kwargs):
        started = time.perf_counter()
        out = step_fn(*args, **kwargs)
        optimizer_seconds[0] += time.perf_counter() - started
        return out

    trainer.optimizer.step = timed_step
    source = iter([*head, *stream])
    clock, curve = 0.0, [(0.0, 0, held_out_loss(model, held_out))]
    finite = True
    while True:
        report = trainer.train(source, max_steps=eval_every)
        clock += report["seconds"]
        loss = held_out_loss(model, held_out)
        curve.append((clock, trainer.step, loss))
        finite &= math.isfinite(loss)
        log(f"  {arm} s{seed} step {trainer.step:5d}  train {clock:7.1f}s  held-out loss {loss:.4f}")
        if report["stop"] != "max_steps" or not finite:
            break
    validation = trainer.evaluate(ptrain.validation_hook(held_out))
    last = [r for r in trainer.history if "eval" not in r][-1]
    return {"arm": arm, "seed": seed, "optimizer": optimizer, "lr": lr, "steps": trainer.step,
            "train_seconds": clock, "optimizer_ms_per_step": 1000 * optimizer_seconds[0] / max(trainer.step, 1),
            "train_s_per_step": clock / max(trainer.step, 1), "curve": curve, "finite": finite,
            "final_losses": {k: last.get(k) for k in ("loss", "lm", "ask", "ans", "halt")},
            "validation": {k: validation.get(k) for k in ("accuracy", "accuracy_gold_cards", "gold_recall_at_4",
                                                          "random_recall_at_4", "asked_rate", "loops_mean",
                                                          "halt_rate", "questions")}}


def loss_at(curve: list, seconds: float) -> float:
    """Held-out loss linearly interpolated at `seconds` of training (clamped to the curve's ends)."""
    for (t0, _, l0), (t1, _, l1) in zip(curve, curve[1:]):
        if t0 <= seconds <= t1:
            return l0 if t1 == t0 else l0 + (l1 - l0) * (seconds - t0) / (t1 - t0)
    return curve[-1][2]


def score(runs: list[dict]) -> dict:
    by = {(r["arm"], r["seed"]): r for r in runs}
    seeds = sorted({r["seed"] for r in runs})
    out = {}
    for arm in ("A1", "A2"):
        rows, ds, base_losses, guard_hits, untrained = [], [], [], 0, False
        for seed in seeds:
            a0, ak = by[("A0", seed)], by[(arm, seed)]
            untrained |= not (a0["finite"] and ak["finite"])
            t_star = min(a0["train_seconds"], ak["train_seconds"])
            l0, lk = loss_at(a0["curve"], t_star), loss_at(ak["curve"], t_star)
            d = l0 - lk
            acc_gap = ak["validation"]["accuracy"] - a0["validation"]["accuracy"]
            guard_hits += acc_gap < -GUARD_POINTS
            ds.append(d)
            base_losses.append(l0)
            rows.append({"seed": seed, "t_star": t_star, "loss_A0": l0, f"loss_{arm}": lk, "d": d,
                         "final_loss_A0": a0["curve"][-1][2], f"final_loss_{arm}": ak["curve"][-1][2],
                         "accuracy_gap_points": 100 * acc_gap})
        n = len(ds)
        mean = statistics.fmean(ds)
        sd = statistics.stdev(ds) if n > 1 else float("nan")
        se = sd / math.sqrt(n)
        positive = sum(d > 0 for d in ds)
        effect = mean / statistics.fmean(base_losses)
        bar = mean - 2 * se > 0 and positive >= 2 and effect >= MIN_EFFECT
        guard_ok = guard_hits < 2
        if untrained:
            verdict = "DID NOT TRAIN"
        elif bar and guard_ok:
            verdict = "PASS"
        elif bar:
            verdict = "NOT COUNTED (guard: accuracy fell more than 3 points in 2 of 3 seeds)"
        elif mean + 2 * se < 0:
            verdict = "PROVED WRONG"
        else:
            verdict = "NOT SHOWN"
        out[arm] = {"rows": rows, "mean_d": mean, "sd_d": sd, "lower": mean - 2 * se, "upper": mean + 2 * se,
                    "seeds_positive": positive, "relative_effect": effect, "bar": bar,
                    "guard_seeds_below": guard_hits, "verdict": verdict}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--eval-every", type=int, default=50)
    parser.add_argument("--visits", type=int, default=16)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    args.out.mkdir(parents=True, exist_ok=True)
    log_file = (args.out / "log.txt").open("a")

    def log(line: str) -> None:
        print(line, flush=True)
        log_file.write(line + "\n")
        log_file.flush()

    log(f"R1 stage 0 start {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} torch {torch.__version__} "
        f"{platform.machine()} threads {torch.get_num_threads()} steps {args.steps}")
    runs = []
    order = list(ARMS)
    for k, seed in enumerate(args.seeds):
        for arm in order[k % 3:] + order[:k % 3]:              # rotate the arm order across seeds
            path = args.out / f"{arm}-s{seed}.json"
            if path.exists():
                runs.append(json.loads(path.read_text()))
                log(f"{arm} s{seed}: reusing {path.name}")
                continue
            log(f"{arm} s{seed}: {ARMS[arm]}")
            result = run(arm, seed, args.steps, args.eval_every, args.visits, log)
            path.write_text(json.dumps(result, indent=1))
            runs.append(result)
    verdicts = score(runs)
    (args.out / "result.json").write_text(json.dumps({"runs": [{k: v for k, v in r.items() if k != "curve"}
                                                                for r in runs], "score": verdicts}, indent=1))
    for arm, s in verdicts.items():
        log(f"{arm} vs A0: mean d {s['mean_d']:+.4f} (2SE band {s['lower']:+.4f}..{s['upper']:+.4f}), "
            f"{s['seeds_positive']}/3 seeds positive, relative {s['relative_effect']:+.2%}, "
            f"guard seeds below {s['guard_seeds_below']} -> {s['verdict']}")
    log(f"R1 stage 0 end {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")


if __name__ == "__main__":
    main()
