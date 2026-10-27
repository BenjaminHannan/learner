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


PEAK_MEM_GB_MAX = 14.0  # T4 has 15 GB; K2 in fp16 is ~10.1 GB (5.06B params incl. 1.28B untied embeddings)


def pilot_health(st, on_cuda):
    """The pilot must prove the night actually trained, not only that it ran: finite losses, few skipped steps, and memory under the T4 limit."""
    import math
    bad = []
    for k in ("sft_loss", "anchor_kl"):
        if st.get(k) is None or not math.isfinite(st[k]):
            bad.append(f"{k}={st.get(k)}")
    if st.get("skipped_steps", 0) > 0.2 * max(1, st.get("opt_steps", 1)):
        bad.append(f"skipped_steps={st.get('skipped_steps')}/{st.get('opt_steps')}")
    if on_cuda and (st.get("peak_mem_gb") is None or st["peak_mem_gb"] >= PEAK_MEM_GB_MAX):
        bad.append(f"peak_mem_gb={st.get('peak_mem_gb')} (limit {PEAK_MEM_GB_MAX})")
    if bad:
        raise AssertionError("pilot health check failed: " + "; ".join(bad))
    return {k: st.get(k) for k in ("sft_loss", "dpo_loss", "anchor_kl", "skipped_steps", "opt_steps", "peak_mem_gb", "loss_scale", "seconds", "units_total")}


def pilot_projection(night_seconds, n_arms=3, n_nights_=5, eval_seconds=0.0, seeds_parallel=True, units=None, max_units=None):
    """Timing pilot (prereg): if one night takes more than 9 minutes the world must shrink equally in every arm.
    night_seconds is the measured night 1; with `units` (its actual token-pass units) and `max_units` (the largest planned night) it is scaled up to the biggest night."""
    cap = 9 * 60
    if units and max_units:
        night_seconds = night_seconds * max(1.0, max_units / units)
    per_lane = n_arms * (n_nights_ * night_seconds + eval_seconds)
    return {"night_seconds": round(night_seconds, 1), "within_9_min": night_seconds <= cap, "suggested_night_scale": round(min(1.0, cap / max(night_seconds, 1e-9)), 3),
            "eval_seconds": round(eval_seconds, 1), "lane_hours_projected": round(per_lane / 3600, 2), "total_gpu_hours_projected": round(per_lane * 2 / 3600, 2)}
