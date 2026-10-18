"""Run card R1, stage 0 (design/steals-2026-10-17/REPORT.md): Muon against AdamW on the far-fact toy, CPU, $0.

Arms (each differs from A0 only in the optimizer with its lr): A0 AdamW 3e-3, A1 Muon 3e-3 (recipe), A2 Muon 2e-2.
Seeds 0, 1, 2. Each arm is `train.toy_setup("D", steps=1500, seed=s, lr=..., optimizer=...)`, the registered
`train_toy` setup: at a seed the model is bit-identical across arms, and every arm trains the same FLOP budget on the
same batches. Within a seed the three arms are interleaved in chunks of `--eval-every` steps (A0, A1, A2, A0, ...;
the order rotates across seeds), so drift in machine speed hits every arm.

Primary readout: held-out loss (teacher mode, fixed loops, the 4 held-out toy batches, fixed distractor seeds), after
every chunk under no_grad, evaluation time off the clock; interpolated at T* = the shorter arm's training seconds.
Bar (card section 5): mean(d) - 2 SD(d)/sqrt(3) > 0, d_s > 0 in >= 2 of 3 seeds, mean(d) >= 3% of A0's loss at T*.
Guard (section 6): Ak's held-out accuracy more than 3 points below A0's in >= 2 of 3 seeds voids a pass.

    OMP_NUM_THREADS=1 python3 -B scripts/premonition_steals_r1_stage0.py --out artifacts/claude-steals-20261017/r1-stage0
"""
from __future__ import annotations

import argparse
import itertools
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

ARMS = {"A0": ("adamw", 3e-3), "A1": ("muon", 3e-3), "A2": ("muon", 2e-2)}
CARD_SEEDS = (0, 1, 2)
EVAL_LOOPS = 4
MIN_EFFECT = 0.03                     # relative, for the loss readout (Q42)
GUARD_POINTS = 0.03


@torch.no_grad()
def held_out_loss(model, batches: list) -> float:
    """Mean teacher-mode loss over fixed batches, fixed loop count and distractor seeds (no curriculum, no noise)."""
    was = model.training
    model.eval()
    losses = [float(model(b, mode="teacher", loops=EVAL_LOOPS, generator=torch.Generator().manual_seed(1234 + i))["loss"])
              for i, b in enumerate(batches)]
    model.train(was)
    return statistics.fmean(losses)


class Arm:
    """One arm of one seed, trained a chunk at a time."""

    def __init__(self, arm: str, seed: int, steps: int, eval_every: int, visits: int) -> None:
        self.arm, self.seed = arm, seed
        self.optimizer, self.lr = ARMS[arm]
        self.trainer, head, stream, self.held_out, _ = ptrain.toy_setup(
            "D", steps=steps, visits=visits, seed=seed, lr=self.lr, log_every=eval_every, optimizer=self.optimizer)
        self.source = itertools.chain(head, stream)
        self.eval_every = eval_every
        self.optimizer_seconds = 0.0
        step = self.trainer.optimizer.step

        def timed(*args, **kwargs):
            started = time.perf_counter()
            out = step(*args, **kwargs)
            self.optimizer_seconds += time.perf_counter() - started
            return out

        self.trainer.optimizer.step = timed
        self.clock = 0.0
        self.curve = [(0.0, 0, held_out_loss(self.trainer.model, self.held_out))]
        self.done = False
        self.finite = True

    def chunk(self) -> None:
        report = self.trainer.train(self.source, max_steps=self.eval_every)
        self.clock += report["seconds"]
        loss = held_out_loss(self.trainer.model, self.held_out)
        self.curve.append((self.clock, self.trainer.step, loss))
        self.finite &= math.isfinite(loss)
        self.done = report["stop"] != "max_steps" or not self.finite

    def result(self, settings: dict) -> dict:
        trainer = self.trainer
        validation = trainer.evaluate(ptrain.validation_hook(self.held_out))
        last = [r for r in trainer.history if "eval" not in r][-1]
        return {"arm": self.arm, "seed": self.seed, "optimizer": self.optimizer, "lr": self.lr, "settings": settings,
                "steps": trainer.step, "train_seconds": self.clock,
                "optimizer_ms_per_step": 1000 * self.optimizer_seconds / max(trainer.step, 1),
                "train_s_per_step": self.clock / max(trainer.step, 1), "curve": self.curve, "finite": self.finite,
                "final_losses": {k: last.get(k) for k in ("loss", "lm", "ask", "ans", "halt")},
                "validation": {k: validation.get(k) for k in (
                    "accuracy", "accuracy_gold_cards", "gold_recall_at_4", "random_recall_at_4", "asked_rate",
                    "loops_mean", "halt_rate", "questions")}}


def run_seed(seed: int, order: list[str], settings: dict, log) -> list[dict]:
    arms = [Arm(arm, seed, settings["steps"], settings["eval_every"], settings["visits"]) for arm in order]
    while not all(a.done for a in arms):
        for a in arms:
            if not a.done:
                a.chunk()
        log(f"  s{seed} " + "  ".join(f"{a.arm} step {a.trainer.step:5d} {a.clock:7.1f}s loss {a.curve[-1][2]:.4f}"
                                      for a in arms))
    return [a.result(settings) for a in arms]


def loss_at(curve: list, seconds: float) -> float:
    """Held-out loss linearly interpolated at `seconds` of training (clamped to the curve's ends)."""
    for (t0, _, l0), (t1, _, l1) in zip(curve, curve[1:]):
        if t0 <= seconds <= t1:
            return l0 if t1 == t0 else l0 + (l1 - l0) * (seconds - t0) / (t1 - t0)
    return curve[-1][2]


def score(runs: list[dict]) -> dict:
    by = {(r["arm"], r["seed"]): r for r in runs}
    seeds = sorted({r["seed"] for r in runs})
    if tuple(seeds) != CARD_SEEDS:
        return {"verdict": f"NOT SCORED: the card registers seeds {CARD_SEEDS}, these runs have {tuple(seeds)}"}
    out = {}
    for arm in ("A1", "A2"):
        rows, ds, base_losses, guard_hits, untrained = [], [], [], 0, False
        for seed in seeds:
            a0, ak = by[("A0", seed)], by[(arm, seed)]
            untrained |= not (a0["finite"] and ak["finite"])
            t_star = min(a0["train_seconds"], ak["train_seconds"])
            l0, lk = loss_at(a0["curve"], t_star), loss_at(ak["curve"], t_star)
            acc_gap = ak["validation"]["accuracy"] - a0["validation"]["accuracy"]
            guard_hits += acc_gap < -GUARD_POINTS
            ds.append(l0 - lk)
            base_losses.append(l0)
            rows.append({"seed": seed, "t_star": t_star, "loss_A0": l0, f"loss_{arm}": lk, "d": l0 - lk,
                         "final_loss_A0": a0["curve"][-1][2], f"final_loss_{arm}": ak["curve"][-1][2],
                         "accuracy_A0": a0["validation"]["accuracy"], f"accuracy_{arm}": ak["validation"]["accuracy"],
                         "accuracy_gap_points": 100 * acc_gap})
        mean, sd = statistics.fmean(ds), statistics.stdev(ds)
        se = sd / math.sqrt(len(ds))
        positive = sum(d > 0 for d in ds)
        effect = mean / statistics.fmean(base_losses)
        bar = mean - 2 * se > 0 and positive >= 2 and effect >= MIN_EFFECT
        if untrained:
            verdict = "DID NOT TRAIN"
        elif bar and guard_hits < 2:
            verdict = "PASS"
        elif bar:
            verdict = "NOT COUNTED (guard: accuracy more than 3 points below A0 in 2 of 3 seeds)"
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
    parser.add_argument("--seeds", type=int, nargs="+", default=list(CARD_SEEDS))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    settings = {"steps": args.steps, "eval_every": args.eval_every, "visits": args.visits, "torch": torch.__version__}
    args.out.mkdir(parents=True, exist_ok=True)
    log_file = (args.out / "log.txt").open("a")

    def log(line: str) -> None:
        print(line, flush=True)
        log_file.write(line + "\n")
        log_file.flush()

    log(f"R1 stage 0 start {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {platform.machine()} "
        f"threads {torch.get_num_threads()} settings {settings}")
    runs, names = [], list(ARMS)
    for k, seed in enumerate(args.seeds):
        order = names[k % 3:] + names[:k % 3]                   # rotate the arm order across seeds
        paths = [args.out / f"{arm}-s{seed}.json" for arm in order]
        if all(p.exists() for p in paths):
            saved = [json.loads(p.read_text()) for p in paths]
            if any(s.get("settings") != settings for s in saved):
                raise SystemExit(f"{args.out} holds seed {seed} runs with other settings; use a new --out")
            runs += saved
            log(f"s{seed}: reusing {', '.join(p.name for p in paths)}")
            continue
        log(f"s{seed}: arms in order {order}")
        for result, path in zip(run_seed(seed, order, settings, log), paths):
            path.write_text(json.dumps(result, indent=1))
            runs.append(result)
    verdicts = score(runs)
    (args.out / "result.json").write_text(json.dumps({"settings": settings, "score": verdicts, "runs": [
        {k: v for k, v in r.items() if k != "curve"} for r in runs]}, indent=1))
    for arm, s in verdicts.items():
        if isinstance(s, str):
            log(s)
            continue
        log(f"{arm} vs A0: mean d {s['mean_d']:+.4f} (2SE band {s['lower']:+.4f}..{s['upper']:+.4f}), "
            f"{s['seeds_positive']}/3 seeds positive, relative {s['relative_effect']:+.2%}, "
            f"guard seeds below {s['guard_seeds_below']} -> {s['verdict']}")
    log(f"R1 stage 0 end {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")


if __name__ == "__main__":
    main()
