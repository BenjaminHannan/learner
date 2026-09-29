Starting the history practice build — checking for existing runs first.
No existing hist practice run — only unrelated jobs. I'll launch the full driver script in the background next.
The driver failed: I launched it with zsh, which doesn't word-split `$PY`, so the `uv run` command wasn't found. Relaunching with bash:
Close — histw1 at step 10000/12000, hist at 9000/12000. One final wait for the tail:
Job complete. REPORT (counts only):

Versions: python 3.12.14, torch 2.14.0.

Selftest lines verbatim:
- `baseline F_eq (higher read): [51.21, 51.67] plain: [34.04, 32.62]`
- `SELFTEST-marks ok`
- `loop_params_same_init: ok`
- `extra_weights: ok {'stored': 1744414, 'loop_stored': 1645726, 'extra': 98688, 'window': 8}`
- `starts_as_loop: ok`
- `ring_capped: ok [1, 2, 3, 4, 5, 6, 7, 8, 8, 8, 8, 8]`
- `control_window1: ok`
- `read_changes_output_when_on: ok`
- `grads_reach_read: ok`
- `forward_shapes: ok`
- `SELFTEST ok`
- Harness selftest printed 4 support lines verbatim (2 plugins x 2 seeds): seed 0 `support_unique_layouts 16384, support_panel_overlap 0, sha256 3efe54c5…cabe2d`, seed 1 `...sha256 ad4a726c…b462677e`, panel_layouts dev {7:24, 9:300, 11:300}, holdout {7:48, 9:300, 11:300} each. Driver window: start 2026-09-29 07:20:10 UTC, end 10:38:24 UTC.

Wall time per run (train_seconds): hist-s0 11504 s, hist-s1 11710 s, histw1-s0 10600 s, histw1-s1 10759 s.

Four source.json lines:
- `{"seed": 0, "plugin": "claude_dir_hist_net", "weights": 1744414, "fixed_depth": 8, "old": {"grids5": 200, "sums4": 200}, "v1_pass": true, "nonzero_all": true, "train_seconds": 11504}`
- `{"seed": 1, "plugin": "claude_dir_hist_net", "weights": 1744414, "fixed_depth": 8, "old": {"grids5": 200, "sums4": 200}, "v1_pass": true, "nonzero_all": true, "train_seconds": 11710}`
- `{"seed": 0, "plugin": "claude_dir_hist_net_w1", "weights": 1744414, "fixed_depth": 8, "old": {"grids5": 200, "sums4": 200}, "v1_pass": true, "nonzero_all": false, "train_seconds": 10600}`
- `{"seed": 1, "plugin": "claude_dir_hist_net_w1", "weights": 1744414, "fixed_depth": 8, "old": {"grids5": 200, "sums4": 200}, "v1_pass": true, "nonzero_all": false, "train_seconds": 10759}`

STOP RULE (2) TRIGGERED: `gradient_check.nonzero_all` is false for histw1 seed 0 and histw1 seed 1 (v1_pass true for all four; hist seeds 0/1 fully pass). Reporting and STOPPING — no maze run. Old-task counts held at 200 of 200 for sums4 and grids5 on all four sources.

Files staged in worktree (additive only, no commit): `artifacts/claude-dir-hist-20260929/runs/` (4x source.json + 4x practice logs), `checkpoints-sha256.txt`, `selftest.log`, `selftest-marks.log`, `harness-selftest.log`. The .pt checkpoints remain only in `$HOME/premonition-hist`, never pushed.
