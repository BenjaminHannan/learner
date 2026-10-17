"""Parameter and per-step cost of each frontier steal, one flag at a time (design/steals-2026-10-17).

For D at d = 128 (vocab v1) on synthetic visits, per flag:
- parameters, and the delta from D;
- counted training FLOPs of one step in each mode (`flops.measure_mini`, FlopCounterMode: matmuls and
  attention only, so elementwise work such as gates, norms and hashing is not counted);
- CPU wall-clock of one training step (forward + backward), median of `--repeats`, in each mode.

CPU timings at one thread are a rough guide to relative cost, not GPU throughput.

    OMP_NUM_THREADS=1 python3 -B scripts/premonition_steals_costs.py --out artifacts/claude-steals-20261017/costs.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
import time

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from premonition.config import STEAL_FLAGS, VOCAB_V1, MiniConfig  # noqa: E402
from premonition.flops import measure_mini  # noqa: E402
from premonition.model import PremonitionMini  # noqa: E402
from tests.test_premonition_model import synthetic_batch  # noqa: E402

MODES = (("gold", 0.0), ("teacher", 0.0), ("own", 0.5))


def settings() -> dict[str, dict]:
    runs = {"D (all off)": {}}
    runs.update({name: {name: True} for name in STEAL_FLAGS})
    runs["qk_clip"] = {"qk_clip": 5.0}
    runs["D again (noise)"] = {}      # the all-off model timed a second time: the timing noise floor
    return runs


def measure(flags: dict, batch, repeats: int) -> dict:
    torch.manual_seed(0)
    model = PremonitionMini(MiniConfig.preset("D", vocab_size=VOCAB_V1, **flags))
    out = {"parameters": model.num_parameters(), "breakdown": model.parameter_breakdown(), "modes": {}}
    for mode, p_own in MODES:
        sample = measure_mini(model, batch, mode=mode, p_own=p_own,
                              generator=torch.Generator().manual_seed(0))
        times = []
        for _ in range(repeats):
            model.zero_grad(set_to_none=True)
            started = time.perf_counter()
            result = model(batch, mode=mode, p_own=p_own, generator=torch.Generator().manual_seed(0))
            result["loss"].backward()
            times.append(time.perf_counter() - started)
        out["modes"][mode] = {"flops": sample.flops, "question_loops": sample.question_loops,
                              "seconds_median": statistics.median(times)}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--visits", type=int, default=4)
    parser.add_argument("--lines", type=int, default=40)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    torch.set_num_threads(1)
    batch = synthetic_batch(visits=args.visits, lines=args.lines, seed=21, vocab=VOCAB_V1)
    results = {label: measure(flags, batch, args.repeats) for label, flags in settings().items()}
    base = results["D (all off)"]
    print(f"{'flag':<16}{'params':>11}{'delta':>9}" + "".join(f"{m + ' FLOPs':>15}{m + ' s':>10}" for m, _ in MODES))
    for label, row in results.items():
        line = f"{label:<16}{row['parameters']:>11,}{row['parameters'] - base['parameters']:>+9,}"
        for mode, _ in MODES:
            here, ref = row["modes"][mode], base["modes"][mode]
            line += f"{here['flops'] / ref['flops'] - 1:>+14.2%} {here['seconds_median'] / ref['seconds_median'] - 1:>+9.1%}"
        print(line)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        payload = {"batch": {"visits": args.visits, "lines": args.lines, "tokens": int(batch.tokens.numel()),
                             "questions": int(batch.q_visit.shape[0])},
                   "threads": torch.get_num_threads(), "torch": torch.__version__, "results": results}
        args.out.write_text(json.dumps(payload, indent=1))


if __name__ == "__main__":
    main()
