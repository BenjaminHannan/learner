start 2026-09-28 23:49:48 UTC
19:49  up 23 mins, 2 users, load averages: 41.26 51.78 60.59
/dev/disk3s1s1       460   12       106    11%  484014 1115750240    0%   /
seal: 17 of 17 files OK
seed 0: qualified source.json matches its sealed sha256; source.pt sha256 d5f09b1dfbc65e4e018081be71305e7440468d869114f2205e2565a3e646a085
seed 1: qualified source.json matches its sealed sha256; source.pt sha256 6cc51ee871a383668b365f63c80e9d9599a4c11faab08fed7e46747f7fb15673
{"selftest": "ok", "baseline_S1_rungs": [0, 1], "baseline_F_eq_dev": [51.21, 51.67], "noise": {"F_eq": {"sd_two_run_diff_points": 3.33, "bar_rounded_up_to_half": 7.0}, "F_few": {"sd_two_run_diff_points": 4.17, "bar_rounded_up_to_half": 8.5}}}
{"selftest": "ok", "weights": 1645726, "stop_weight": 0.5, "first_update_loss": 5.341154098510742, "practice_loss_same_rounds": 5.341154098510742, "updates_per_batch": 4}
PARTIAL: artifacts/claude-dir-h12-stop-20260928/eq-runs/h12-pre-s0 exists without adapt.json (the harness has no resume); delete that folder and start again
rc=7
