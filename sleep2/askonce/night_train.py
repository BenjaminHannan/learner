"""Step 9: train one arm for N nights (adapter carried night to night) on the frozen night files, with the ledger gate:
the next night is refused if the planned token-passes of the arms differ by more than 5%, or the actual units drift from the plan."""
import json
import time

from . import compute_ledger as CL
from .config import LEDGER_TOL, LR, jl_read, jload, n_nights, night_opt_steps
from .train_core import LoRATrainer


def gate(plan, n):
    """Planned per-arm totals for night n must be within tolerance (also asserted when the files were built)."""
    CL.assert_equal(plan["nights"][str(n)]["per_arm"], plan["tol"], f"(gate, night {n})")


def train_arm(trainer: LoRATrainer, arm, nightdata_dir, anchors, log=print, max_nights=None, on_night=None):
    plan = jload(nightdata_dir / "plan.json")
    n_opt = plan.get("n_opt_steps") or night_opt_steps()  # the plan's value (the ledger counted one anchor sequence per step)
    out = []
    for n in range(1, (max_nights or n_nights()) + 1):
        gate(plan, n)
        items = jl_read(nightdata_dir / "nights" / arm / f"night{n}.jsonl")
        st = trainer.run_night(items, anchors, n_opt, LR, n, log)
        planned = plan["nights"][str(n)]["per_arm"][arm]["total"]
        st["planned_units"] = planned
        st["units_drift"] = round(abs(st["units_total"] - planned) / max(1, planned), 4)
        if st["units_drift"] > LEDGER_TOL:
            raise AssertionError(f"{arm} night {n}: actual units {st['units_total']} vs planned {planned} (drift {st['units_drift']})")
        out.append(st)
        if on_night:
            on_night(st)
    return out


def pilot_projection(night_seconds, n_arms=3, n_nights_=5, eval_seconds=0.0, seeds_parallel=True):
    """Timing pilot (prereg): if one night takes more than 9 minutes the world must shrink equally in every arm."""
    cap = 9 * 60
    per_lane = n_arms * (n_nights_ * night_seconds + eval_seconds)
    return {"night_seconds": round(night_seconds, 1), "within_9_min": night_seconds <= cap, "suggested_night_scale": round(min(1.0, cap / max(night_seconds, 1e-9)), 3),
            "lane_hours_projected": round(per_lane / 3600, 2), "total_gpu_hours_projected": round(per_lane * 2 / 3600, 2)}
