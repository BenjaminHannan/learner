#!/usr/bin/env python3
"""Corrected CPU-vs-GPU smoke for the MoE test (ADDENDUM-1.md). The sealed driver is not edited.

The sealed smoke's cpu_state() returns v.detach().cpu(), which for a tensor already on the CPU is the live
parameter itself, not a copy, so the CPU half's 'start_state' moved with training and the update checks divided by
zero (update_rel_diff_all = Infinity, same_start false). This runs the sealed smoke unchanged except that the
state snapshots are clones. Same SMOKE_MARKS. Writes SMOKE2-gpu.json and prints the checks on short lines.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_moe_deep_run as R  # noqa: E402

R.cpu_state = lambda net: {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}

if __name__ == "__main__":
    c = R.smoke_phase("cpu", 4)
    g = R.smoke_phase("cuda", 4)
    res = R.compare(c, g)
    res.update({"marks_fixed_in_advance": R.SMOKE_MARKS, "utc": R.utc(), "run_meta": R.meta("cuda"),
                "note": "ADDENDUM-1 corrected smoke (cloned snapshots)"})
    R.B.dump(R.ART / "SMOKE2-gpu.json", res)
    for k in ("PASS", "checks", "update_rel_diff_all", "worst_tensor", "update_rel_diff_worst_tensor",
              "update_rel_diff_all_after_3_sleep_steps", "route_agreement_min", "logit_max_abs_diff",
              "stop_prob_max_abs_diff", "start_state_identical"):
        print("SMOKE2", k, json.dumps(res[k]), flush=True)
    print("SMOKE2-DONE", flush=True)
