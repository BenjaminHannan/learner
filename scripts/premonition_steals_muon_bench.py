"""Steal 8 benchmark: Muon against AdamW on CPU (design/steals-2026-10-17/SPEC.md section 8).

Part A trains the tiny D (d = 32) on the far-fact toy with `train_toy`: the same seeds, the same steps and the same
batches for every arm; AdamW at lr 3e-3 (train_toy's default), Muon at 3e-3 (the recipe: the update is RMS-matched
to AdamW, so the same lr) and Muon at 2e-2 (Muon is often run higher). It records loss against wall-clock seconds
(training time only: calibration, build and evaluation are left out), the loss at equal wall-clock by linear
interpolation, and the time spent inside `optimizer.step`. Part B times 20 optimizer steps of each optimizer on the
full d = 128 D with a synthetic batch (the gradients of one backward pass, reused).

    OMP_NUM_THREADS=1 python3 -B scripts/premonition_steals_muon_bench.py [--steps 60] [--seeds 0 1]
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable, Iterator

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from premonition import train as ptrain                      # noqa: E402
from premonition.config import VOCAB_V2, MiniConfig          # noqa: E402
from premonition.model import PremonitionMini                # noqa: E402
from premonition.muon import MuonAdamW                       # noqa: E402
from tests.test_premonition_model import synthetic_batch     # noqa: E402

OUT = ROOT / "artifacts" / "claude-steals-20261017" / "muon-bench.json"
ARMS = {"adamw-3e-3": ("adamw", 3e-3), "muon-3e-3": ("muon", 3e-3), "muon-2e-2": ("muon", 2e-2)}


@contextmanager
def timed_steps(cls: type) -> Iterator[list[float]]:
    """Seconds of every `cls.step` call made inside the block."""
    spent: list[float] = []
    original = cls.step

    def step(self: Any, *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        result = original(self, *args, **kwargs)
        spent.append(time.perf_counter() - started)
        return result

    cls.step = step
    try:
        yield spent
    finally:
        cls.step = original


def run_arm(optimizer: str, lr: float, seed: int, steps: int, log_every: int) -> dict[str, Any]:
    cls = MuonAdamW if optimizer == "muon" else torch.optim.AdamW
    with timed_steps(cls) as spent:
        out = ptrain.train_toy(steps=steps, seed=seed, lr=lr, log_every=log_every, optimizer=optimizer)
    points, clock, previous = [], 0.0, 0
    for record in out["history"]:
        if "loss" not in record:
            continue
        clock += (record["tokens"] - previous) / record["tokens_per_s"]      # the window's training seconds
        previous = record["tokens"]
        points.append({"step": record["step"], "seconds": clock, "loss": record["loss"]})
    return {"optimizer": optimizer, "lr": lr, "seed": seed, "steps": out["train"]["steps"], "points": points,
            "final_loss": points[-1]["loss"], "train_seconds": out["train"]["seconds"],
            "optimizer_step_seconds_mean": sum(spent) / len(spent), "optimizer_steps_timed": len(spent),
            "validation": {k: v for k, v in out["validation"].items() if isinstance(v, (int, float))}}


def interpolate(points: list[dict[str, Any]], seconds: float) -> float | None:
    """Loss at `seconds` of training, linear between logged windows (None before the first one)."""
    if seconds < points[0]["seconds"]:
        return None
    for a, b in zip(points, points[1:]):
        if a["seconds"] <= seconds <= b["seconds"]:
            return a["loss"] + (b["loss"] - a["loss"]) * (seconds - a["seconds"]) / max(b["seconds"] - a["seconds"], 1e-12)
    return points[-1]["loss"]


def equal_wall_clock(runs: dict[str, dict[str, Any]], fractions=(0.25, 0.5, 0.75, 1.0)) -> dict[str, Any]:
    """Loss of every arm at fractions of the shortest arm's total training seconds."""
    horizon = min(run["points"][-1]["seconds"] for run in runs.values())
    return {f"{fraction:.2f}": {"seconds": fraction * horizon,
                                **{name: interpolate(run["points"], fraction * horizon) for name, run in runs.items()}}
            for fraction in fractions}


def full_width_timing(steps: int = 20, trials: int = 3) -> dict[str, Any]:
    """`steps` optimizer steps of each optimizer on the full D with one synthetic batch's gradients."""
    config = MiniConfig.preset("D", vocab_size=VOCAB_V2)
    batch = synthetic_batch(visits=2, lines=40, seed=0, vocab=VOCAB_V2)
    result: dict[str, Any] = {"parameters": None, "steps": steps, "trials": trials}
    for name, (optimizer, lr) in ARMS.items():
        torch.manual_seed(0)
        model = PremonitionMini(config)
        result["parameters"] = model.num_parameters()
        trainer = ptrain.MiniTrainer(model, ptrain.mini_train_config(lr=lr), "cpu", flop_budget=1.0, seed=0,
                                     optimizer=optimizer)
        model.train()
        for _ in range(2):                                                        # the second pass is timed
            model.zero_grad(set_to_none=True)
            started = time.perf_counter()
            model(batch, mode="teacher", generator=torch.Generator().manual_seed(0))["loss"].backward()
            fwd_bwd = time.perf_counter() - started
        trainer.optimizer.step()                                                  # warm the state buffers
        runs = []
        for _ in range(trials):
            started = time.perf_counter()
            for _ in range(steps):
                trainer.optimizer.step()
            runs.append((time.perf_counter() - started) / steps)
        result[name] = {"optimizer_step_seconds": min(runs), "all_trials": runs, "forward_backward_seconds": fwd_bwd}
    base = result["adamw-3e-3"]["optimizer_step_seconds"]
    for name in ARMS:
        result[name]["step_time_vs_adamw"] = result[name]["optimizer_step_seconds"] / base
        result[name]["overhead_seconds"] = result[name]["optimizer_step_seconds"] - base
        result[name]["share_of_train_step"] = result[name]["optimizer_step_seconds"] / (
            result[name]["optimizer_step_seconds"] + result[name]["forward_backward_seconds"])
    return result


def table(rows: list[list[str]]) -> str:
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    return "\n".join("  ".join(cell.ljust(width) for cell, width in zip(row, widths)) for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--steps", type=int, default=60)
    parser.add_argument("--log-every", type=int, default=5)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    torch.set_num_threads(1)
    started = time.perf_counter()
    report: dict[str, Any] = {"steps": args.steps, "log_every": args.log_every, "seeds": args.seeds,
                              "threads": torch.get_num_threads(), "arms": {n: {"optimizer": o, "lr": lr}
                                                                           for n, (o, lr) in ARMS.items()},
                              "toy": {}, "equal_wall_clock": {}}
    for seed in args.seeds:
        runs = {}
        for name, (optimizer, lr) in ARMS.items():                                  # interleaved: same machine state
            runs[name] = run_arm(optimizer, lr, seed, args.steps, args.log_every)
            print(f"seed {seed} {name}: final {runs[name]['final_loss']:.3f}  "
                  f"{runs[name]['train_seconds']:.1f}s", flush=True)
        report["toy"][str(seed)] = runs
        report["equal_wall_clock"][str(seed)] = equal_wall_clock(runs)
    report["full_width"] = full_width_timing()
    report["total_seconds"] = time.perf_counter() - started
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1))

    print(f"\nTiny D on the far-fact toy, {args.steps} steps (loss = mean of the last {args.log_every}-step window)")
    rows = [["seed", "arm", "final", "train s", "opt-step ms", "loss @25%", "@50%", "@75%", "@100% of equal clock"]]
    for seed in args.seeds:
        wall = report["equal_wall_clock"][str(seed)]
        for name, run in report["toy"][str(seed)].items():
            at = [wall[k][name] for k in ("0.25", "0.50", "0.75", "1.00")]
            rows.append([str(seed), name, f"{run['final_loss']:.3f}", f"{run['train_seconds']:.1f}",
                         f"{1e3 * run['optimizer_step_seconds_mean']:.2f}"]
                        + ["-" if x is None else f"{x:.3f}" for x in at])
    print(table(rows))
    print("\nFull d = 128 D (%s parameters), optimizer step on one synthetic batch's gradients" %
          f"{report['full_width']['parameters']:,}")
    rows = [["arm", "step ms", "vs adamw", "overhead ms", "fwd+bwd ms", "step share"]]
    for name in ARMS:
        row = report["full_width"][name]
        rows.append([name, f"{1e3 * row['optimizer_step_seconds']:.1f}", f"{row['step_time_vs_adamw']:.2f}x",
                     f"{1e3 * row['overhead_seconds']:.1f}", f"{1e3 * row['forward_backward_seconds']:.0f}",
                     f"{100 * row['share_of_train_step']:.1f}%"])
    print(table(rows))
    print(f"\nwrote {args.out}  ({report['total_seconds']:.0f}s)")


if __name__ == "__main__":
    main()
